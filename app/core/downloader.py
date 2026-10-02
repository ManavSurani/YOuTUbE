"""Download command builder, progress parser, and download worker thread."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence
from PySide6.QtCore import QThread, Signal
from app.core.paths import BIN_DIR, DEFAULT_DOWNLOADS
from app.core.proc import start_hidden, kill_tree
from app.core.logger import get_logger

PROGRESS_TEMPLATE = "download:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress._downloaded_bytes_str)s|%(progress._total_bytes_str)s"


@dataclass
class ProgressInfo:
    percent: float
    speed: str
    eta: str
    done_str: str
    total_str: str


@dataclass
class ParsedOutput:
    kind: str  # "progress", "stage", "filepath", "other"
    progress: ProgressInfo | None = None
    stage: str | None = None
    filepath: str | None = None


def get_ytdlp_path() -> str:
    """Return path to bundled yt-dlp.exe if present, else fallback to 'yt-dlp'."""
    bin_exe = BIN_DIR / "yt-dlp.exe"
    if bin_exe.exists():
        return str(bin_exe)
    return "yt-dlp"


def build_video_cmd(
    url: str,
    height: int | None = None,
    container: str = "mkv",
    out_dir: Path | str = DEFAULT_DOWNLOADS,
) -> List[str]:
    """Build yt-dlp command for video download with merged audio."""
    cmd = [
        get_ytdlp_path(),
        "--no-playlist",
        "--newline",
        "--ffmpeg-location",
        str(BIN_DIR),
        "-P",
        str(out_dir),
        "--progress-template",
        PROGRESS_TEMPLATE,
        "--print",
        "after_move:filepath",
    ]

    if height:
        cmd.extend(["-f", f"bv*[height<={height}]+ba/b[height<={height}]"])
    else:
        cmd.extend(["-f", "bv*+ba/b"])

    cmd.extend(["--merge-output-format", container])
    cmd.append(url)
    return cmd


def build_audio_cmd(
    url: str,
    fmt: str = "best",
    out_dir: Path | str = DEFAULT_DOWNLOADS,
    embed_thumbnail: bool = False,
    embed_metadata: bool = False,
) -> List[str]:
    """Build yt-dlp command for audio download."""
    cmd = [
        get_ytdlp_path(),
        "--no-playlist",
        "--newline",
        "--ffmpeg-location",
        str(BIN_DIR),
        "-P",
        str(out_dir),
        "--progress-template",
        PROGRESS_TEMPLATE,
        "--print",
        "after_move:filepath",
    ]

    if embed_thumbnail:
        cmd.append("--embed-thumbnail")
    if embed_metadata:
        cmd.append("--embed-metadata")

    fmt_lower = fmt.lower()
    if fmt_lower in ("best", "best original", "original"):
        cmd.extend(["-f", "ba", "-x"])
    elif fmt_lower in ("mp3", "m4a"):
        cmd.extend(["-f", "ba", "-x", "--audio-format", fmt_lower, "--audio-quality", "0"])
    else:
        cmd.extend(["-f", "ba", "-x", "--audio-format", fmt_lower])

    cmd.append(url)
    return cmd


def parse_line(line: str) -> ParsedOutput:
    """Parse one line of stdout from yt-dlp without crashing on unexpected output."""
    clean = line.strip()

    if clean.startswith("download:"):
        payload = clean[len("download:"):].strip()
        parts = payload.split("|")
        if len(parts) >= 5:
            pct_str = parts[0].replace("%", "").strip()
            try:
                pct = float(pct_str)
            except ValueError:
                pct = 0.0
            return ParsedOutput(
                kind="progress",
                progress=ProgressInfo(
                    percent=pct,
                    speed=parts[1].strip(),
                    eta=parts[2].strip(),
                    done_str=parts[3].strip(),
                    total_str=parts[4].strip(),
                ),
            )

    if "[Merger]" in clean:
        return ParsedOutput(kind="stage", stage="Merging")

    if "[ExtractAudio]" in clean:
        return ParsedOutput(kind="stage", stage="Converting audio")

    # Check for after_move filepath output (path on disk)
    if clean and (clean.endswith(".mkv") or clean.endswith(".mp4") or clean.endswith(".webm") or
                  clean.endswith(".mp3") or clean.endswith(".m4a") or clean.endswith(".opus") or
                  clean.endswith(".wav") or clean.endswith(".flac")):
        if Path(clean).is_absolute():
            return ParsedOutput(kind="filepath", filepath=clean)

    return ParsedOutput(kind="other")


def cleanup_temp_files(out_dir: Path | str) -> None:
    """Remove leftover .part, .ytdl, and .temp files in destination directory."""
    try:
        p = Path(out_dir)
        for pattern in ["*.part", "*.ytdl", "*.temp"]:
            for file_path in p.glob(pattern):
                try:
                    file_path.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass


class DownloadWorker(QThread):
    """Worker thread running yt-dlp download process with live progress parsing."""

    stage = Signal(str)
    progress = Signal(float, str, str, str, str)  # overall_percent, speed, eta, done_str, total_str
    finished = Signal(str)  # filepath
    failed = Signal(str)  # raw_text
    paused = Signal()

    def __init__(
        self,
        cmd: Sequence[str],
        out_dir: Path | str = DEFAULT_DOWNLOADS,
        is_dual_stream: bool = True,
        initial_percent: float = 0.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.cmd = list(cmd)
        self.out_dir = Path(out_dir)
        self.is_dual_stream = is_dual_stream
        self._proc = None
        self._is_cancelled = False
        self._is_paused = False
        self._max_percent = max(0.0, initial_percent)
        self._current_stream = 1
        self._final_filepath = ""
        self._raw_lines: List[str] = []

    def run(self) -> None:
        logger = get_logger()
        logger.info(f"Starting download: {' '.join(self.cmd)}")
        self.stage.emit("Fetching info")

        try:
            self._proc = start_hidden(self.cmd)
        except Exception as exc:
            logger.error(f"Failed to launch download process: {exc}")
            self.failed.emit(str(exc))
            return

        for line in self._proc.stdout:
            line_str = line.strip()
            if not line_str:
                continue

            logger.info(line_str)
            self._raw_lines.append(line_str)

            # Detect stream switch
            if "[download] Destination:" in line_str:
                if self.is_dual_stream and self._current_stream == 1 and any(ext in line_str for ext in [".f", ".m4a", ".webm", ".opus"]):
                    if self._max_percent > 10.0:
                        self._current_stream = 2
                        self.stage.emit("Downloading audio")
                else:
                    self.stage.emit("Downloading video")

            parsed = parse_line(line_str)
            if parsed.kind == "stage" and parsed.stage:
                self.stage.emit(parsed.stage)
                if parsed.stage == "Merging":
                    self._max_percent = max(self._max_percent, 95.0)
                    self.progress.emit(self._max_percent, "", "", "", "")
            elif parsed.kind == "progress" and parsed.progress:
                p = parsed.progress
                if self.is_dual_stream:
                    if self._current_stream == 1:
                        scaled_pct = p.percent * 0.85
                    else:
                        scaled_pct = 85.0 + (p.percent * 0.10)
                else:
                    scaled_pct = p.percent

                overall_pct = max(self._max_percent, scaled_pct)
                self._max_percent = overall_pct
                self.progress.emit(overall_pct, p.speed, p.eta, p.done_str, p.total_str)
            elif parsed.kind == "filepath" and parsed.filepath:
                self._final_filepath = parsed.filepath

        self._proc.wait()
        returncode = self._proc.returncode

        if self._is_cancelled:
            self._cleanup_temp_files()
            return

        if self._is_paused:
            self.stage.emit("Waiting for internet…")
            self.paused.emit()
            return

        if returncode == 0:
            self._max_percent = 100.0
            self.progress.emit(100.0, "", "", "", "")
            self.stage.emit("Done")
            if not self._final_filepath:
                for l in reversed(self._raw_lines):
                    if Path(l).is_file():
                        self._final_filepath = l
                        break
            self.finished.emit(self._final_filepath)
        else:
            raw_err = "\n".join(self._raw_lines[-10:])
            self.failed.emit(raw_err)

    def pause(self) -> None:
        """Pause download by terminating process tree WITHOUT deleting .part files."""
        self._is_paused = True
        if self._proc:
            kill_tree(self._proc)

    def cancel(self) -> None:
        """Cancel the download, kill the process tree, and remove temporary files."""
        self._is_cancelled = True
        self._is_paused = False
        if self._proc:
            kill_tree(self._proc)
        self._cleanup_temp_files()

    def _cleanup_temp_files(self) -> None:
        """Remove leftover .part and .ytdl files."""
        cleanup_temp_files(self.out_dir)

