"""Central DownloadManager orchestrating single-active download queue with persistence and offline handling.

Fixes B8 (prevents simultaneous overlapping downloads).
Maintains queue state, retries, and coordinates with HistoryService.
"""

import json
from pathlib import Path
import threading
from typing import Dict, List, Optional, Set, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from app.core.downloader import DownloadWorker, build_audio_cmd, build_video_cmd
from app.core.errors import explain
from app.core.history_service import save_from_job
from app.core.jobs import DownloadJob
from app.core.logger import get_logger
from app.core.paths import APP_DATA, DEFAULT_DOWNLOADS
from app.core.settings import load_settings


class DownloadManager(QObject):
    """Central singleton managing all downloads across Video and Audio tabs."""

    job_added = Signal(object)      # DownloadJob
    job_started = Signal(object)    # DownloadJob
    progress = Signal(object, float, str, str, int, int)  # job, pct, speed, eta, done, total
    stage = Signal(object, str)     # job, stage_text
    job_finished = Signal(object, str)  # job, final_path
    job_failed = Signal(object, str)    # job, friendly_reason
    job_cancelled = Signal(object)  # DownloadJob
    queue_changed = Signal()

    def __init__(self, kind: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.kind = kind.lower()
        self._waiting_queue: List[DownloadJob] = []
        self._active_job: Optional[DownloadJob] = None
        self._worker: Optional[DownloadWorker] = None
        self._failed_jobs: Dict[str, Tuple[DownloadJob, str]] = {}
        self._completed_jobs: List[Tuple[DownloadJob, str]] = []
        self._repaired_jobs: set = set()
        self._deferred_job_ids: Set[str] = set()
        self._is_offline = False
        self._is_shutting_down = False
        self._paused_worker = None
        self._resume_attempts = 0
        self._force_overwrite_job_ids: Set[str] = set()
        self._running_forced_job_ids: Set[str] = set()
        self._failed_forced_job_ids: Set[str] = set()
        self._active_job_last_pct: float = 0.0
        self._queue_file = APP_DATA / f"queue_{self.kind}.json"

        self._load_persisted_queue()

    def deferred_job_ids(self) -> Set[str]:
        """Return the set of job IDs that are currently deferred due to cross-lane same video_id conflict."""
        return set(self._deferred_job_ids)

    def _get_other_manager(self) -> Optional["DownloadManager"]:
        """Lazy lookup for the other lane manager without construction recursion."""
        other_kind = "audio" if self.kind == "video" else "video"
        return _managers.get(other_kind)

    def _wake_all_lanes(self) -> None:
        """Wake up both this lane and the other lane thread-safely."""
        if not self._is_offline:
            self._process_next()
        other = self._get_other_manager()
        if other and not other._is_offline:
            other._process_next()

    @property
    def active_job(self) -> Optional[DownloadJob]:
        return self._active_job

    @property
    def waiting_jobs(self) -> List[DownloadJob]:
        return list(self._waiting_queue)

    @property
    def failed_jobs(self) -> List[Tuple[DownloadJob, str]]:
        return list(self._failed_jobs.values())

    @property
    def completed_jobs(self) -> List[Tuple[DownloadJob, str]]:
        return list(self._completed_jobs)

    def enqueue(self, job: DownloadJob, force_overwrite: bool = False) -> None:
        """Add job to the queue and begin processing if idle."""
        if job.kind != self.kind:
            get_logger().warning(f"Rejected job {job.job_id}: kind mismatch ({job.kind} != {self.kind})")
            return

        # Double-check duplicate in queue
        if self._active_job and self._active_job.job_id == job.job_id:
            return
        if any(j.job_id == job.job_id for j in self._waiting_queue):
            return

        if force_overwrite:
            self._force_overwrite_job_ids.add(job.job_id)

        self._is_shutting_down = False
        self._waiting_queue.append(job)
        self._save_persisted_queue()
        self.job_added.emit(job)
        self.queue_changed.emit()

        if not self._active_job and not self._is_offline:
            self._process_next()

    def cancel_active(self) -> None:
        """Cancel currently downloading job."""
        if self._active_job:
            get_logger().info(f"Cancelling active download: {self._active_job.title}")
            job = self._active_job
            self._force_overwrite_job_ids.discard(job.job_id)
            self._running_forced_job_ids.discard(job.job_id)
            self._failed_forced_job_ids.discard(job.job_id)
            if self._worker:
                self._worker.cancel()
                self._worker = None
            self._active_job_last_pct = 0.0
            self._active_job = None
            self.job_cancelled.emit(job)
            self.queue_changed.emit()
            # Start next item after cancel and wake other lane
            self._wake_all_lanes()

    def cancel_job(self, job_id: str) -> None:
        """Cancel or remove a job by ID."""
        self._force_overwrite_job_ids.discard(job_id)
        self._running_forced_job_ids.discard(job_id)
        self._failed_forced_job_ids.discard(job_id)
        if self._active_job and self._active_job.job_id == job_id:
            self.cancel_active()
            return

        for i, job in enumerate(self._waiting_queue):
            if job.job_id == job_id:
                removed = self._waiting_queue.pop(i)
                self._deferred_job_ids.discard(job_id)
                self._save_persisted_queue()
                self.job_cancelled.emit(removed)
                self.queue_changed.emit()
                self._wake_all_lanes()
                return

        if job_id in self._failed_jobs:
            del self._failed_jobs[job_id]
            self.queue_changed.emit()

    def shutdown(self) -> None:
        """Stop running worker without starting next waiting job; keep waiting jobs persisted."""
        self._is_shutting_down = True
        self._force_overwrite_job_ids.clear()
        self._running_forced_job_ids.clear()
        self._failed_forced_job_ids.clear()
        if self._worker:
            try:
                self._worker.cancel()
            except Exception as exc:
                get_logger().debug(f"Worker cancel error during shutdown: {exc}")
        if self._active_job:
            self._active_job = None
            self.queue_changed.emit()
        self._save_persisted_queue()

    def retry_job(self, job_id: str) -> None:
        """Retry a previously failed job."""
        if job_id in self._failed_jobs:
            job, _ = self._failed_jobs.pop(job_id)
            was_forced = job_id in self._failed_forced_job_ids
            self._failed_forced_job_ids.discard(job_id)
            self.enqueue(job, force_overwrite=was_forced)

    def clear_finished(self) -> None:
        """Clear list of completed jobs."""
        self._completed_jobs.clear()
        self.queue_changed.emit()

    def start_restored_jobs(self) -> None:
        """Begin processing restored queue items if online and idle."""
        if not self._is_offline and not self._active_job and self._waiting_queue:
            self._process_next()

    def set_online(self, online: bool) -> None:
        """Pause or resume downloads based on network connectivity."""
        was_offline = self._is_offline
        self._is_offline = not online
        if not online:
            if not was_offline and self._active_job and self._worker:   # only on online -> offline
                get_logger().info("Network offline: pausing active download.")
                self._worker.pause()
                self._paused_worker = self._worker
            return
        if self._is_shutting_down:
            return                                   # never revive a closing lane
        if was_offline and (self._paused_worker is not None or (self._active_job and self._worker)):
            if self._paused_worker is None:
                self._paused_worker = self._worker
            self._resume_attempts = 0
            self._resume_active_job()                # offline -> online: resume exactly once
        else:
            self._process_next()                     # already online: only wake an idle lane

    def _resume_active_job(self) -> None:
        """Start a new worker for the paused job only after the old thread has really stopped."""
        old, job = self._paused_worker, self._active_job
        if old is None or job is None or self._is_offline or self._is_shutting_down:
            return
        is_running = old.isRunning() if hasattr(old, "isRunning") else False
        if is_running is True:
            self._resume_attempts += 1
            if self._resume_attempts <= 20:          # about 2 seconds, never blocks the UI
                QTimer.singleShot(100, self._resume_active_job)
            else:
                get_logger().warning("Old %s worker did not stop; resume skipped", self.kind)
            return
        self._resume_attempts = 0
        floor = self._active_job_last_pct
        self._paused_worker = None
        try:
            self._start_worker(job, floor_percent=floor)
        except TypeError:
            self._start_worker(job)

    def _process_next(self) -> None:
        """Start the next waiting job if one is available and not deferred."""
        if self._is_shutting_down or self._active_job or not self._waiting_queue or self._is_offline:
            return

        head = self._waiting_queue[0]
        other_mgr = self._get_other_manager()
        other_active = other_mgr.active_job if other_mgr else None

        if other_active and other_active.video_id and other_active.video_id == head.video_id:
            if head.job_id not in self._deferred_job_ids:
                self._deferred_job_ids.add(head.job_id)
                self.queue_changed.emit()
            return

        if head.job_id in self._deferred_job_ids:
            self._deferred_job_ids.discard(head.job_id)
            self.queue_changed.emit()

        job = self._waiting_queue.pop(0)
        self._save_persisted_queue()
        self._active_job = job
        self.job_started.emit(job)
        self.queue_changed.emit()
        self._start_worker(job)

    def _start_worker(self, job: DownloadJob, floor_percent: float = 0.0) -> None:
        settings = load_settings()
        out_dir = job.output_dir or settings.get("download_dir", str(DEFAULT_DOWNLOADS))

        force = job.job_id in self._force_overwrite_job_ids
        self._force_overwrite_job_ids.discard(job.job_id)
        if force:
            self._running_forced_job_ids.add(job.job_id)

        if job.kind == "audio":
            cmd = build_audio_cmd(
                url=job.url,
                fmt=job.audio_format or "best",
                out_dir=out_dir,
                job_id=job.job_id,
                force_overwrite=force,
            )
            is_dual = False
        else:
            cmd = build_video_cmd(
                url=job.url,
                height=job.height,
                out_dir=out_dir,
                job_id=job.job_id,
                force_overwrite=force,
            )
            is_dual = True

        self._worker = DownloadWorker(
            cmd=cmd,
            out_dir=out_dir,
            job_id=job.job_id,
            video_id=job.video_id,
            is_dual_stream=is_dual,
            duration_seconds=job.duration_seconds,
            floor_percent=floor_percent,
            parent=self,
        )
        self._worker.job_id = job.job_id

        self._worker.stage.connect(self._on_worker_stage)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

    def _on_worker_stage(self, a1, a2=None) -> None:
        if a2 is not None:
            job = a1
            stage_name = a2
        else:
            job = self._active_job
            stage_name = a1
        sender = self.sender()
        if sender is not None:
            if sender is not self._worker or getattr(sender, "job_id", None) != (self._active_job.job_id if self._active_job else None):
                return
        if self._active_job and job and self._active_job.job_id == job.job_id:
            self.stage.emit(job, stage_name)

    def _on_worker_progress(self, *args) -> None:
        if len(args) == 6:
            job, pct, speed, eta, done, total = args
        elif len(args) == 5:
            job = self._active_job
            pct, speed, eta, done, total = args
        else:
            return
        sender = self.sender()
        if sender is not None:
            if sender is not self._worker or getattr(sender, "job_id", None) != (self._active_job.job_id if self._active_job else None):
                return
        if self._active_job and job and self._active_job.job_id == job.job_id:
            self._active_job_last_pct = pct
            self.progress.emit(job, pct, speed, eta, done, total)

    def _on_worker_finished(self, a1, a2=None) -> None:
        if a2 is not None:
            job = a1
            final_path = a2
        else:
            job = self._active_job
            final_path = a1
        sender = self.sender()
        if sender is not None:
            if sender is not self._worker or getattr(sender, "job_id", None) != (self._active_job.job_id if self._active_job else None):
                get_logger().debug(f"Ignored finished signal from stale worker: {sender}")
                return
        if not self._active_job or not job or self._active_job.job_id != job.job_id:
            return
        if self._is_shutting_down:
            return

        get_logger().info(f"Download finished: {job.title} -> {final_path}")
        self._force_overwrite_job_ids.discard(job.job_id)
        self._running_forced_job_ids.discard(job.job_id)
        self._failed_forced_job_ids.discard(job.job_id)
        self._active_job_last_pct = 0.0
        self._worker = None
        self._active_job = None
        self._completed_jobs.append((job, final_path))

        # Save to history automatically via HistoryService (Phase 2)
        try:
            save_from_job(job, final_path)
        except Exception as exc:
            get_logger().error(f"Failed to record history for {job.title}: {exc}")

        self.job_finished.emit(job, final_path)
        self.queue_changed.emit()

        # Multi-path wake up both lanes
        self._wake_all_lanes()

    def _on_worker_failed(self, a1, a2=None) -> None:
        if a2 is not None:
            job = a1
            raw_error = a2
        else:
            job = self._active_job
            raw_error = a1
        sender = self.sender()
        if sender is not None:
            if sender is not self._worker or getattr(sender, "job_id", None) != (self._active_job.job_id if self._active_job else None):
                get_logger().debug(f"Ignored failed signal from stale worker: {sender}")
                return
        if not self._active_job or not job or self._active_job.job_id != job.job_id:
            return
        if self._is_shutting_down:
            return

        # Chunk 7.3 Task 3: Auto-repair on extraction failure
        err_lower = raw_error.lower()
        is_extraction = any(
            kw in err_lower
            for kw in (
                "unable to extract",
                "regex",
                "signature",
                "n challenge",
                "nsig",
                "extractor error",
            )
        )
        if is_extraction and job.job_id not in self._repaired_jobs and not self._is_offline:
            get_logger().info(f"Extraction failure detected for '{job.title}'. Running yt-dlp auto-repair...")
            self._repaired_jobs.add(job.job_id)
            from app.core.tool_manager import update_ytdlp
            if update_ytdlp():
                get_logger().info(f"yt-dlp auto-repaired successfully. Retrying '{job.title}'...")
                self._worker = None
                self._active_job = None
                self.stage.emit(job, "Retrying after tool update…")
                if job.job_id in self._running_forced_job_ids:
                    self._force_overwrite_job_ids.add(job.job_id)
                    self._running_forced_job_ids.discard(job.job_id)
                self._waiting_queue.insert(0, job)
                self._wake_all_lanes()
                return

        friendly_reason = explain(raw_error)
        get_logger().warning(f"Download failed for '{job.title}': {friendly_reason}")
        was_forced = job.job_id in self._running_forced_job_ids
        self._running_forced_job_ids.discard(job.job_id)
        self._force_overwrite_job_ids.discard(job.job_id)
        if was_forced:
            self._failed_forced_job_ids.add(job.job_id)

        self._active_job_last_pct = 0.0
        self._worker = None
        self._active_job = None
        self._failed_jobs[job.job_id] = (job, friendly_reason)

        self.job_failed.emit(job, friendly_reason)
        self.queue_changed.emit()

        # Multi-path wake up both lanes
        self._wake_all_lanes()

    def _save_persisted_queue(self) -> None:
        """Persist waiting jobs to queue.json."""
        try:
            data = [
                {
                    "job_id": j.job_id,
                    "url": j.url,
                    "video_id": j.video_id,
                    "title": j.title,
                    "channel": j.channel,
                    "duration_seconds": j.duration_seconds,
                    "thumbnail_url": j.thumbnail_url,
                    "kind": j.kind,
                    "quality_label": j.quality_label,
                    "height": j.height,
                    "audio_format": j.audio_format,
                    "output_dir": j.output_dir,
                    "created_at": j.created_at,
                }
                for j in self._waiting_queue
            ]
            self._queue_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            get_logger().debug(f"Failed to persist queue: {exc}")

    def _load_persisted_queue(self) -> None:
        """Restore waiting jobs from queue_<kind>.json."""
        if not self._queue_file.is_file():
            return
        try:
            raw = self._queue_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            for item in data:
                item_kind = item.get("kind", "video")
                if item_kind != self.kind:
                    get_logger().debug(f"Skipping item {item.get('job_id')} with kind {item_kind} in {self.kind} lane")
                    continue
                job = DownloadJob(
                    job_id=item["job_id"],
                    url=item["url"],
                    video_id=item["video_id"],
                    title=item["title"],
                    channel=item.get("channel", ""),
                    duration_seconds=int(item.get("duration_seconds", 0)),
                    thumbnail_url=item.get("thumbnail_url", ""),
                    thumbnail_bytes=None,
                    kind=item_kind,
                    quality_label=item.get("quality_label", "Best"),
                    height=item.get("height"),
                    audio_format=item.get("audio_format"),
                    output_dir=item.get("output_dir", ""),
                    created_at=item.get("created_at", ""),
                )
                self._waiting_queue.append(job)
            get_logger().info(f"Restored {len(self._waiting_queue)} queued downloads from queue_{self.kind}.json.")
        except Exception as exc:
            get_logger().debug(f"Failed to load persisted queue: {exc}")


_managers: Dict[str, DownloadManager] = {}
_migration_lock = threading.Lock()


def migrate_legacy_queue_if_needed(app_data_dir: Optional[Path] = None) -> None:
    """Migrate legacy queue.json to queue_video.json and queue_audio.json safely under threading.Lock."""
    with _migration_lock:
        target_dir = app_data_dir if app_data_dir is not None else APP_DATA
        legacy_file = target_dir / "queue.json"
        if not legacy_file.exists():
            return

        try:
            raw_text = legacy_file.read_text(encoding="utf-8").strip()
            if not raw_text:
                legacy_file.rename(target_dir / "queue.json.corrupt")
                get_logger().warning("Corrupt or empty queue.json detected; renamed to queue.json.corrupt")
                return

            items = json.loads(raw_text)
            if not isinstance(items, list):
                legacy_file.rename(target_dir / "queue.json.corrupt")
                get_logger().warning("Corrupt or empty queue.json detected; renamed to queue.json.corrupt")
                return

            video_items = []
            audio_items = []
            for item in items:
                if isinstance(item, dict) and item.get("kind") == "audio":
                    audio_items.append(item)
                else:
                    video_items.append(item)

            video_file = target_dir / "queue_video.json"
            audio_file = target_dir / "queue_audio.json"

            if not video_file.exists():
                video_file.write_text(json.dumps(video_items, indent=2), encoding="utf-8")
            if not audio_file.exists():
                audio_file.write_text(json.dumps(audio_items, indent=2), encoding="utf-8")

            legacy_file.rename(target_dir / "queue.json.bak")
            get_logger().info("Migrated legacy queue.json into queue_video.json and queue_audio.json (backed up as queue.json.bak)")
        except Exception as exc:
            try:
                legacy_file.rename(target_dir / "queue.json.corrupt")
            except Exception as rename_exc:
                get_logger().debug(f"Could not rename legacy file to corrupt: {rename_exc}")
            get_logger().warning(f"Corrupt or empty queue.json detected; renamed to queue.json.corrupt: {exc}")


def get_download_manager(kind: str) -> DownloadManager:
    """Return the shared singleton DownloadManager instance for the specified lane ('video' or 'audio')."""
    migrate_legacy_queue_if_needed()
    k = kind.lower()
    if k not in _managers:
        _managers[k] = DownloadManager(kind=k)
    return _managers[k]
