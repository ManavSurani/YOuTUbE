"""Central DownloadManager orchestrating single-active download queue with persistence and offline handling.

Fixes B8 (prevents simultaneous overlapping downloads).
Maintains queue state, retries, and coordinates with HistoryService.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

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

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._waiting_queue: List[DownloadJob] = []
        self._active_job: Optional[DownloadJob] = None
        self._worker: Optional[DownloadWorker] = None
        self._failed_jobs: Dict[str, Tuple[DownloadJob, str]] = {}
        self._completed_jobs: List[Tuple[DownloadJob, str]] = []
        self._is_offline = False
        self._queue_file = APP_DATA / "queue.json"

        self._load_persisted_queue()

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

    def enqueue(self, job: DownloadJob) -> None:
        """Add job to the queue and begin processing if idle."""
        # Double-check duplicate in queue
        if self._active_job and self._active_job.job_id == job.job_id:
            return
        if any(j.job_id == job.job_id for j in self._waiting_queue):
            return

        self._waiting_queue.append(job)
        self._save_persisted_queue()
        self.job_added.emit(job)
        self.queue_changed.emit()

        if not self._active_job and not self._is_offline:
            self._process_next()

    def cancel_active(self) -> None:
        """Cancel currently downloading job."""
        if self._active_job and self._worker:
            get_logger().info(f"Cancelling active download: {self._active_job.title}")
            job = self._active_job
            self._worker.cancel()
            self._worker = None
            self._active_job = None
            self.job_cancelled.emit(job)
            self.queue_changed.emit()
            # Start next item after cancel
            if not self._is_offline:
                self._process_next()

    def cancel_job(self, job_id: str) -> None:
        """Cancel or remove a job by ID."""
        if self._active_job and self._active_job.job_id == job_id:
            self.cancel_active()
            return

        for i, job in enumerate(self._waiting_queue):
            if job.job_id == job_id:
                removed = self._waiting_queue.pop(i)
                self._save_persisted_queue()
                self.job_cancelled.emit(removed)
                self.queue_changed.emit()
                return

        if job_id in self._failed_jobs:
            del self._failed_jobs[job_id]
            self.queue_changed.emit()

    def retry_job(self, job_id: str) -> None:
        """Retry a previously failed job."""
        if job_id in self._failed_jobs:
            job, _ = self._failed_jobs.pop(job_id)
            self.enqueue(job)

    def clear_finished(self) -> None:
        """Clear list of completed jobs."""
        self._completed_jobs.clear()
        self.queue_changed.emit()

    def set_online(self, online: bool) -> None:
        """Pause or resume downloads based on network connectivity."""
        self._is_offline = not online
        if not online:
            if self._worker and self._active_job:
                get_logger().info("Network offline: pausing active download.")
                self._worker.pause()
        else:
            if self._active_job and self._worker:
                get_logger().info("Network online: resuming active download.")
                # Worker is restarted for active job
                self._start_worker(self._active_job)
            elif not self._active_job and self._waiting_queue:
                self._process_next()

    def _process_next(self) -> None:
        """Start the next waiting job if one is available."""
        if self._active_job or not self._waiting_queue or self._is_offline:
            return

        job = self._waiting_queue.pop(0)
        self._save_persisted_queue()
        self._active_job = job
        self.job_started.emit(job)
        self.queue_changed.emit()
        self._start_worker(job)

    def _start_worker(self, job: DownloadJob) -> None:
        settings = load_settings()
        out_dir = job.output_dir or settings.get("download_dir", str(DEFAULT_DOWNLOADS))

        if job.kind == "audio":
            cmd = build_audio_cmd(
                url=job.url,
                fmt=job.audio_format or "best",
                out_dir=out_dir,
                job_id=job.job_id,
            )
            is_dual = False
        else:
            cmd = build_video_cmd(
                url=job.url,
                height=job.height,
                out_dir=out_dir,
                job_id=job.job_id,
            )
            is_dual = True

        self._worker = DownloadWorker(
            cmd=cmd,
            out_dir=out_dir,
            job_id=job.job_id,
            video_id=job.video_id,
            is_dual_stream=is_dual,
            parent=self,
        )

        self._worker.stage.connect(lambda st: self._on_worker_stage(job, st))
        self._worker.progress.connect(lambda pct, sp, eta, done, tot: self._on_worker_progress(job, pct, sp, eta, done, tot))
        self._worker.finished.connect(lambda path: self._on_worker_finished(job, path))
        self._worker.failed.connect(lambda err: self._on_worker_failed(job, err))
        self._worker.start()

    def _on_worker_stage(self, job: DownloadJob, stage_name: str) -> None:
        if self._active_job and self._active_job.job_id == job.job_id:
            self.stage.emit(job, stage_name)

    def _on_worker_progress(self, job: DownloadJob, pct: float, speed: str, eta: str, done: int, total: int) -> None:
        if self._active_job and self._active_job.job_id == job.job_id:
            self.progress.emit(job, pct, speed, eta, done, total)

    def _on_worker_finished(self, job: DownloadJob, final_path: str) -> None:
        if not self._active_job or self._active_job.job_id != job.job_id:
            return

        get_logger().info(f"Download finished: {job.title} -> {final_path}")
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

        # Start next waiting job
        if not self._is_offline:
            self._process_next()

    def _on_worker_failed(self, job: DownloadJob, raw_error: str) -> None:
        if not self._active_job or self._active_job.job_id != job.job_id:
            return

        friendly_reason = explain(raw_error)
        get_logger().warning(f"Download failed for '{job.title}': {friendly_reason}")

        self._worker = None
        self._active_job = None
        self._failed_jobs[job.job_id] = (job, friendly_reason)

        self.job_failed.emit(job, friendly_reason)
        self.queue_changed.emit()

        # Isolate failure: continue queue with next item
        if not self._is_offline:
            self._process_next()

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
        """Restore waiting jobs from queue.json."""
        if not self._queue_file.is_file():
            return
        try:
            raw = self._queue_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            for item in data:
                job = DownloadJob(
                    job_id=item["job_id"],
                    url=item["url"],
                    video_id=item["video_id"],
                    title=item["title"],
                    channel=item.get("channel", ""),
                    duration_seconds=int(item.get("duration_seconds", 0)),
                    thumbnail_url=item.get("thumbnail_url", ""),
                    thumbnail_bytes=None,
                    kind=item.get("kind", "video"),
                    quality_label=item.get("quality_label", "Best"),
                    height=item.get("height"),
                    audio_format=item.get("audio_format"),
                    output_dir=item.get("output_dir", ""),
                    created_at=item.get("created_at", ""),
                )
                self._waiting_queue.append(job)
            get_logger().info(f"Restored {len(self._waiting_queue)} queued downloads from queue.json.")
        except Exception as exc:
            get_logger().debug(f"Failed to load persisted queue: {exc}")


_manager_instance: Optional[DownloadManager] = None


def get_download_manager() -> DownloadManager:
    """Return the shared singleton DownloadManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = DownloadManager()
    return _manager_instance
