"""Download command builder, progress parser, and download worker thread.

Phase 1 rewrite — fixes:
  B1: --print silenced yt-dlp; now removed; progress flows freely.
  B2: 'download:' was a type selector, not printed text; now using YTPROG| marker.
  B3: Piped stdout drops non-ASCII on Windows; now using --print-to-file (UTF-8).
  B4: cleanup_temp_files() scanned user Downloads; now only cleans app-owned TMP_DIR.
"""

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from PySide6.QtCore import QThread, Signal

from app.core.logger import get_logger
from app.core.paths import BIN_DIR, DEFAULT_DOWNLOADS, TMP_DIR
from app.core.proc import kill_tree, start_hidden

# ---------------------------------------------------------------------------
# Progress template — use YTPROG| marker so the parser can reliably find lines.
# 'download:' before the template is a type-selector consumed by yt-dlp itself
# and never printed; we use our own prefix instead (B2 fix).
# ---------------------------------------------------------------------------
_PROG_TEMPLATE = (
    "download:YTPROG"
    "|%(progress.status)s"
    "|%(progress.downloaded_bytes)s"
    "|%(progress.total_bytes)s"
    "|%(progress.total_bytes_estimate)s"
    "|%(progress.speed)s"
    "|%(progress.eta)s"
    "|%(info.vcodec)s"
    "|%(info.acodec)s"
)

_POST_TEMPLATE = (
    "postprocess:YTPOST"
    "|%(progress.status)s"
    "|%(progress.postprocessor)s"
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ProgressInfo:
    percent: float       # 0.0 – 100.0
    speed: str           # "12.4 MB/s" or ""
    eta: str             # "01:20" or ""
    done_bytes: int      # raw bytes downloaded
    total_bytes: int     # raw total bytes (may be estimate)
    stage: str           # "Downloading video" | "Downloading audio" | "Merging" | ...


@dataclass
class ParsedOutput:
    kind: str                           # "progress" | "stage" | "other"
    progress: Optional[ProgressInfo] = None
    stage: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_ytdlp_path() -> str:
    """Return path to bundled yt-dlp.exe if present, else fall back to 'yt-dlp'."""
    bin_exe = BIN_DIR / "yt-dlp.exe"
    if bin_exe.exists():
        return str(bin_exe)
    return "yt-dlp"


def _fmt_speed(bps) -> str:
    """Convert bytes/s (float or NA) to a human-readable string."""
    try:
        v = float(bps)
    except (TypeError, ValueError):
        return ""
    if v <= 0:
        return ""
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if v < 1024:
            return f"{v:.1f} {unit}"
        v /= 1024
    return f"{v:.1f} TB/s"


def _fmt_eta(seconds) -> str:
    """Convert seconds (float or NA) to MM:SS string."""
    try:
        s = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    if s < 0:
        return ""
    m, sec = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def _safe_int(value) -> int:
    try:
        v = int(float(value))
        return v if v > 0 else 0
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Command builders — Chunk 1.5
# ---------------------------------------------------------------------------

def build_video_cmd(
    url: str,
    height: Optional[int] = None,
    out_dir: Path | str = DEFAULT_DOWNLOADS,
    job_id: Optional[str] = None,
) -> List[str]:
    """Build yt-dlp command for video download (always MKV, no --print)."""
    path_file = TMP_DIR / f"{job_id or 'tmp'}.path"
    cmd = [
        get_ytdlp_path(),
        "--no-playlist",
        "--continue",
        "--newline",
        "--ffmpeg-location", str(BIN_DIR),
        # App-owned temp folder for .part files (B4 fix)
        "-P", f"temp:{TMP_DIR}",
        "-P", str(out_dir),
        # Output template: include video id so we can search by it (B3 fix)
        "-o", "%(title)s [%(id)s].%(ext)s",
        "--windows-filenames",
        "--trim-filenames", "150",
        # Real progress via our own marker (B1+B2 fix)
        "--progress-template", _PROG_TEMPLATE,
        "--progress-template", _POST_TEMPLATE,
        # Write final path to a UTF-8 file — never trust stdout for paths (B3 fix)
        "--print-to-file", f"after_move:filepath", str(path_file),
        "--merge-output-format", "mkv",
        "--embed-metadata",
    ]

    if height:
        cmd.extend(["-f", f"bv*[height<={height}]+ba/b[height<={height}]"])
    else:
        cmd.extend(["-f", "bv*+ba/b"])

    cmd.append(url)
    return cmd


def build_audio_cmd(
    url: str,
    fmt: str = "best",
    out_dir: Path | str = DEFAULT_DOWNLOADS,
    job_id: Optional[str] = None,
) -> List[str]:
    """Build yt-dlp command for audio download (always embeds metadata + cover)."""
    path_file = TMP_DIR / f"{job_id or 'tmp'}.path"
    cmd = [
        get_ytdlp_path(),
        "--no-playlist",
        "--continue",
        "--newline",
        "--ffmpeg-location", str(BIN_DIR),
        "-P", f"temp:{TMP_DIR}",
        "-P", str(out_dir),
        "-o", "%(title)s [%(id)s].%(ext)s",
        "--windows-filenames",
        "--trim-filenames", "150",
        "--progress-template", _PROG_TEMPLATE,
        "--progress-template", _POST_TEMPLATE,
        "--print-to-file", "after_move:filepath", str(path_file),
        "--embed-metadata",
    ]

    fmt_lower = fmt.lower()
    if fmt_lower in ("best", "best original", "original"):
        cmd.extend(["-f", "ba", "-x"])
    elif fmt_lower in ("mp3", "m4a", "flac", "opus"):
        cmd.extend(["-f", "ba", "-x", "--audio-format", fmt_lower, "--audio-quality", "0"])
        cmd.append("--embed-thumbnail")   # best-effort; failure is non-fatal
    else:
        cmd.extend(["-f", "ba", "-x", "--audio-format", fmt_lower])

    cmd.append(url)
    return cmd


# ---------------------------------------------------------------------------
# Progress parser — Chunk 1.2
# ---------------------------------------------------------------------------

def parse_line(line: str) -> ParsedOutput:
    """Parse one output line from yt-dlp.

    Progress lines contain 'YTPROG|' (our marker, never consumed by yt-dlp).
    Post-process lines contain 'YTPOST|'.
    Stage hints come from yt-dlp's own bracket tags e.g. [Merger].
    """
    clean = line.strip()

    # --- Progress line ---
    if "YTPROG|" in clean:
        idx = clean.index("YTPROG|")
        payload = clean[idx + len("YTPROG|"):]
        parts = payload.split("|")
        # Fields: 0=status | 1=downloaded | 2=total | 3=estimate | 4=speed | 5=eta | 6=vcodec | 7=acodec
        if len(parts) >= 6:
            dl   = _safe_int(parts[1])
            tot  = _safe_int(parts[2])
            est  = _safe_int(parts[3])
            total_used = tot if tot > 0 else est
            pct = (dl / total_used * 100.0) if total_used > 0 else 0.0
            pct = min(99.9, pct)

            vcodec = parts[6].strip() if len(parts) > 6 else ""
            acodec = parts[7].strip() if len(parts) > 7 else ""
            if vcodec and vcodec.lower() not in ("none", "na", ""):
                stage = "Downloading video"
            elif acodec and acodec.lower() not in ("none", "na", ""):
                stage = "Downloading audio"
            else:
                stage = "Downloading"

            return ParsedOutput(
                kind="progress",
                progress=ProgressInfo(
                    percent=pct,
                    speed=_fmt_speed(parts[4]),
                    eta=_fmt_eta(parts[5]),
                    done_bytes=dl,
                    total_bytes=total_used,
                    stage=stage,
                ),
            )

    # --- Post-process line ---
    if "YTPOST|" in clean:
        idx = clean.index("YTPOST|")
        payload = clean[idx + len("YTPOST|"):]
        parts = payload.split("|")
        pp = parts[2].strip() if len(parts) > 2 else (parts[-1].strip() if parts else "")
        if "Merger" in pp:
            return ParsedOutput(kind="stage", stage="Merging")
        if "ExtractAudio" in pp:
            return ParsedOutput(kind="stage", stage="Converting audio")
        if "EmbedThumbnail" in pp:
            return ParsedOutput(kind="stage", stage="Embedding thumbnail")
        if "FFmpegMetadata" in pp or "Metadata" in pp:
            return ParsedOutput(kind="stage", stage="Writing metadata")
        return ParsedOutput(kind="stage", stage=pp or "Processing")

    # --- Stage hints from yt-dlp bracket tags ---
    if "[Merger]" in clean:
        return ParsedOutput(kind="stage", stage="Merging")
    if "[ExtractAudio]" in clean:
        return ParsedOutput(kind="stage", stage="Converting audio")
    if "[EmbedThumbnail]" in clean:
        return ParsedOutput(kind="stage", stage="Embedding thumbnail")
    if "[Metadata]" in clean or "[FFmpegMetadata]" in clean:
        return ParsedOutput(kind="stage", stage="Writing metadata")

    return ParsedOutput(kind="other")


# ---------------------------------------------------------------------------
# Safe file-path resolver — Chunk 1.3
# ---------------------------------------------------------------------------

def resolve_final_path(
    path_file: Path,
    video_id: str,
    out_dir: Path,
) -> str:
    """
    Read the UTF-8 path file written by --print-to-file.
    Fallback: search out_dir for a file containing [video_id].
    Never returns an empty string if the file exists.
    """
    logger = get_logger()

    # Primary: read path file
    if path_file.exists():
        try:
            lines = path_file.read_text(encoding="utf-8").splitlines()
            candidate = next((l.strip() for l in reversed(lines) if l.strip()), "")
            if candidate and Path(candidate).is_file():
                logger.info(f"Path resolved from path file: {candidate}")
                return candidate
            logger.warning(f"Path file content not found on disk: {candidate!r}")
        except Exception as exc:
            logger.warning(f"Could not read path file {path_file}: {exc}")

    # Fallback: scan output directory for [video_id] in filename
    if video_id:
        try:
            candidates = sorted(
                [
                    f for f in out_dir.iterdir()
                    if f.is_file()
                    and f"[{video_id}]" in f.name
                    and not any(f.name.endswith(ext) for ext in (".part", ".ytdl", ".tmp"))
                ],
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                logger.info(f"Path resolved by scan: {candidates[0]}")
                return str(candidates[0])
        except Exception as exc:
            logger.warning(f"Scan fallback failed: {exc}")

    logger.error("Could not resolve final file path after download")
    return ""


# ---------------------------------------------------------------------------
# Download worker — fully rewritten for Phase 1
# ---------------------------------------------------------------------------

class DownloadWorker(QThread):
    """Worker thread running yt-dlp download process with live progress parsing."""

    stage    = Signal(str)
    progress = Signal(float, str, str, int, int)  # pct, speed, eta, done_bytes, total_bytes
    finished = Signal(str)   # final filepath
    failed   = Signal(str)   # friendly error text (raw for errors.explain())
    paused   = Signal()

    def __init__(
        self,
        cmd: Sequence[str],
        out_dir: Path | str = DEFAULT_DOWNLOADS,
        job_id: Optional[str] = None,
        video_id: str = "",
        is_dual_stream: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.cmd           = list(cmd)
        self.out_dir       = Path(out_dir)
        self.job_id        = job_id or str(uuid.uuid4())
        self.video_id      = video_id
        self.is_dual_stream = is_dual_stream
        self._proc         = None
        self._is_cancelled = False
        self._is_paused    = False
        self._max_percent  = 0.0
        self._raw_lines: List[str] = []
        # Path file written by --print-to-file (UTF-8, B3 fix)
        self._path_file    = TMP_DIR / f"{self.job_id}.path"

    def run(self) -> None:
        logger = get_logger()
        logger.info(f"Starting download [{self.job_id}]: {' '.join(self.cmd[:4])}...")
        self.stage.emit("Starting…")

        try:
            self._proc = start_hidden(self.cmd)
        except Exception as exc:
            logger.error(f"Failed to launch yt-dlp: {exc}")
            self.failed.emit(str(exc))
            return

        # Track stream type from latest progress line for stage naming
        _last_stream_stage = "Downloading"

        for line in self._proc.stdout:
            line_str = line.rstrip("\n\r")
            if not line_str.strip():
                continue

            logger.info(line_str)
            self._raw_lines.append(line_str)

            if self._is_cancelled or self._is_paused:
                break

            parsed = parse_line(line_str)

            if parsed.kind == "progress" and parsed.progress:
                p = parsed.progress
                _last_stream_stage = p.stage

                # Weighted scaling: 85% video stream, 10% audio stream, 5% post
                if self.is_dual_stream:
                    if p.stage == "Downloading video":
                        scaled = p.percent * 0.85
                    elif p.stage == "Downloading audio":
                        scaled = 85.0 + p.percent * 0.10
                    else:
                        scaled = p.percent
                else:
                    scaled = p.percent * 0.95   # leave room for post-processing

                overall = max(self._max_percent, scaled)
                self._max_percent = overall
                self.stage.emit(p.stage)
                self.progress.emit(overall, p.speed, p.eta, p.done_bytes, p.total_bytes)

            elif parsed.kind == "stage" and parsed.stage:
                self.stage.emit(parsed.stage)
                if parsed.stage == "Merging":
                    self._max_percent = max(self._max_percent, 95.0)
                    self.progress.emit(self._max_percent, "", "", 0, 0)

        self._proc.wait()
        returncode = self._proc.returncode

        if self._is_cancelled:
            self._cleanup_job_tmp()
            return

        if self._is_paused:
            self.stage.emit("Waiting for internet…")
            self.paused.emit()
            return

        if returncode == 0:
            self._max_percent = 100.0
            self.progress.emit(100.0, "", "", 0, 0)
            self.stage.emit("Done")

            final_path = resolve_final_path(self._path_file, self.video_id, self.out_dir)
            # Clean up the .path file itself
            try:
                self._path_file.unlink(missing_ok=True)
            except Exception:
                pass

            self.finished.emit(final_path)
        else:
            raw_err = "\n".join(self._raw_lines[-20:])
            logger.error(f"yt-dlp exited {returncode}: {raw_err[-500:]}")
            self.failed.emit(raw_err)

    def pause(self) -> None:
        """Pause download by terminating the process WITHOUT deleting .part files."""
        self._is_paused = True
        if self._proc:
            kill_tree(self._proc)

    def cancel(self) -> None:
        """Cancel the download, kill the process, and clean up job-owned temp files."""
        self._is_cancelled = True
        self._is_paused = False
        if self._proc:
            kill_tree(self._proc)
        self._cleanup_job_tmp()

    def _cleanup_job_tmp(self) -> None:
        """Remove only files in TMP_DIR that belong to this job (B4 fix).

        Never touches the user's Downloads folder.
        """
        logger = get_logger()
        try:
            for f in TMP_DIR.iterdir():
                if f.is_file() and (
                    self.job_id in f.name
                    or (self.video_id and self.video_id in f.name)
                    or f.suffix in (".part", ".ytdl", ".tmp")
                ):
                    try:
                        f.unlink(missing_ok=True)
                    except Exception as exc:
                        logger.warning(f"Could not delete tmp file {f}: {exc}")
        except Exception as exc:
            logger.warning(f"Temp cleanup failed: {exc}")
