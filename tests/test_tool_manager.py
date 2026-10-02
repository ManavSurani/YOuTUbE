from pathlib import Path
from app.core.tool_manager import (
    missing_tools,
    verify_tool,
    REQUIRED_TOOLS,
)


def test_missing_tools_empty_dir(tmp_path: Path):
    missing = missing_tools(tmp_path)
    assert len(missing) == len(REQUIRED_TOOLS)
    assert "yt-dlp.exe" in missing
    assert "ffmpeg.exe" in missing
    assert "ffprobe.exe" in missing
    assert "deno.exe" in missing


def test_missing_tools_partial(tmp_path: Path):
    (tmp_path / "yt-dlp.exe").write_text("dummy", encoding="utf-8")
    missing = missing_tools(tmp_path)
    assert len(missing) == 3
    assert "yt-dlp.exe" not in missing


def test_verify_tool_corrupt(tmp_path: Path):
    corrupt_exe = tmp_path / "yt-dlp.exe"
    corrupt_exe.write_text("corrupt_binary", encoding="utf-8")
    assert verify_tool("yt-dlp.exe", tmp_path) is False
