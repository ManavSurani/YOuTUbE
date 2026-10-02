"""Information fetcher and quality list builder using yt-dlp metadata."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from PySide6.QtCore import QThread, Signal
from app.core.proc import run_hidden
from app.core.downloader import get_ytdlp_path
from app.core.paths import BIN_DIR
from app.core.logger import get_logger


@dataclass
class VideoInfo:
    url: str
    title: str
    channel: str
    duration: int
    duration_str: str
    thumbnail_url: str
    qualities: List[Tuple[str, Optional[int]]]
    filesize_approx: int


def format_duration(seconds: int | float | None) -> str:
    """Format duration in seconds into M:SS or H:MM:SS."""
    if not seconds or seconds < 0:
        return ""
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_quality_label(height: int) -> str:
    """Map resolution height to standard display label."""
    if height >= 4320:
        return "8K"
    if height >= 2160:
        return "4K"
    if height >= 1440:
        return "2K"
    return f"{height}p"


def build_quality_list(formats: List[Dict[str, Any]]) -> List[Tuple[str, Optional[int]]]:
    """Collect distinct video heights sorted descending with Best available first.
    
    Audio-only formats (no height or vcodec == 'none') are strictly ignored.
    """
    heights = set()
    for f in formats:
        if not isinstance(f, dict):
            continue
        vcodec = f.get("vcodec")
        if vcodec == "none":
            continue
        h = f.get("height")
        if isinstance(h, int) and h > 0:
            heights.add(h)

    sorted_heights = sorted(heights, reverse=True)
    if not sorted_heights:
        return [("Best available", None)]

    top_label = format_quality_label(sorted_heights[0])
    result = [(f"Best available ({top_label})", None)]
    for h in sorted_heights:
        result.append((format_quality_label(h), h))
    return result


def fetch_info(url: str, timeout: float = 30.0) -> VideoInfo:
    """Fetch video metadata and format list via yt-dlp -J with timeout."""
    logger = get_logger()
    ytdlp = get_ytdlp_path()
    cmd = [ytdlp, "-J", "--no-playlist"]

    deno_exe = BIN_DIR / "deno.exe"
    if deno_exe.exists():
        cmd.extend(["--js-runtimes", f"deno:{deno_exe}"])

    cmd.append(url)

    logger.info(f"Fetching info: {' '.join(cmd)}")
    exit_code, output = run_hidden(cmd, timeout=timeout)

    json_idx = output.find("{")
    if exit_code != 0 or json_idx == -1:
        logger.error(f"Failed to fetch video info: exit={exit_code}, err={output[:200]}")
        raise RuntimeError(output.strip() or "Failed to fetch video information.")

    try:
        data = json.loads(output[json_idx:])
    except Exception as exc:
        logger.error(f"Failed to parse yt-dlp JSON: {exc}")
        raise RuntimeError(f"Invalid metadata returned: {exc}")

    title = data.get("title") or "Untitled"
    channel = data.get("channel") or data.get("uploader") or ""
    duration = int(data.get("duration") or 0)
    duration_str = format_duration(duration)
    thumbnail_url = data.get("thumbnail") or ""
    formats = data.get("formats") or []
    qualities = build_quality_list(formats)
    filesize_approx = int(data.get("filesize_approx") or data.get("filesize") or 0)

    return VideoInfo(
        url=url,
        title=title,
        channel=channel,
        duration=duration,
        duration_str=duration_str,
        thumbnail_url=thumbnail_url,
        qualities=qualities,
        filesize_approx=filesize_approx,
    )


class InfoFetchWorker(QThread):
    """Background worker fetching video info without blocking the UI."""

    fetched = Signal(object)  # VideoInfo
    failed = Signal(str)      # raw error message

    def __init__(self, url: str, timeout: float = 30.0, parent=None):
        super().__init__(parent)
        self.url = url
        self.timeout = timeout

    def run(self) -> None:
        try:
            info = fetch_info(self.url, timeout=self.timeout)
            self.fetched.emit(info)
        except Exception as exc:
            self.failed.emit(str(exc))
