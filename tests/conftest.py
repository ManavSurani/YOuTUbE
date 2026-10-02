"""
Contract test harness for Phase 1.
Creates a real 30-second clip.mp4, serves it with a local HTTP server,
and exposes fixtures used by the progress/path contract tests.
"""

import os
import shutil
import socket
import subprocess
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

APPDATA = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
YTDLP = str(Path(APPDATA) / "YOuTUbE" / "bin" / "yt-dlp.exe")
FFMPEG = str(Path(APPDATA) / "YOuTUbE" / "bin" / "ffmpeg.exe")

CREATE_NO_WINDOW = 0x08000000


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_clip(dest: Path, duration: int = 5) -> None:
    """Create a short silent mp4 using the bundled ffmpeg (no audio track so
    yt-dlp treats it as a single-stream download — keeps tests fast)."""
    cmd = [
        FFMPEG,
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size=320x240:rate=10",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        str(dest),
    ]
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
        check=True,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ytdlp_path():
    """Path to the bundled yt-dlp.exe."""
    p = Path(YTDLP)
    if not p.exists():
        pytest.skip(f"yt-dlp not found at {YTDLP}")
    return str(p)


@pytest.fixture(scope="session")
def ffmpeg_path():
    """Path to the bundled ffmpeg.exe."""
    p = Path(FFMPEG)
    if not p.exists():
        pytest.skip(f"ffmpeg not found at {FFMPEG}")
    return str(p)


@pytest.fixture(scope="session")
def clip_server(tmp_path_factory, ffmpeg_path):
    """
    Yields the URL of a local HTTP file server serving a short .mp4 clip.
    The clip is created once per test session.
    """
    serve_dir = tmp_path_factory.mktemp("serve")
    clip = serve_dir / "clip.mp4"
    _make_clip(clip)

    port = _free_port()

    class _Silent(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve_dir), **kwargs)

    server = HTTPServer(("127.0.0.1", port), _Silent)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Small delay so the server is ready
    time.sleep(0.2)

    yield f"http://127.0.0.1:{port}/clip.mp4"

    server.shutdown()


@pytest.fixture()
def tmp_download(tmp_path):
    """A temporary download directory for each test."""
    d = tmp_path / "downloads"
    d.mkdir()
    return d


@pytest.fixture()
def tmp_appdata(tmp_path, monkeypatch):
    """Redirect TMP_DIR to a temp folder so tests don't touch real app data."""
    tmp_dir = tmp_path / "app_tmp"
    tmp_dir.mkdir()
    monkeypatch.setattr("app.core.paths.TMP_DIR", tmp_dir)
    return tmp_dir
