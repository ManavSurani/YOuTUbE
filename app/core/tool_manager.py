"""Tool manager for downloading, verifying, updating, and rolling back external binaries."""

import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional
from app.core.paths import BIN_DIR, ensure_dirs
from app.core.proc import run_hidden
from app.core.logger import get_logger

REQUIRED_TOOLS = ["yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe", "deno.exe"]


def get_tools_manifest() -> Dict:
    if hasattr(sys, "_MEIPASS"):
        manifest_path = Path(sys._MEIPASS) / "app" / "tools.json"
    else:
        manifest_path = Path(__file__).resolve().parent.parent / "tools.json"
    if not manifest_path.exists():
        manifest_path = Path(__file__).resolve().parent.parent / "tools.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            get_logger().debug(f"Failed to parse tools manifest at {manifest_path}: {exc}")
    return {}


def missing_tools(bin_dir: Optional[Path] = None) -> List[str]:
    """Return list of required tool executable filenames that do not exist."""
    target_dir = bin_dir or BIN_DIR
    return [t for t in REQUIRED_TOOLS if not (target_dir / t).is_file()]


def verify_tool(tool_name: str, bin_dir: Optional[Path] = None) -> bool:
    """Verify an installed tool runs --version cleanly."""
    target_dir = bin_dir or BIN_DIR
    exe_path = target_dir / tool_name
    if not exe_path.is_file():
        return False
    try:
        code, out = run_hidden([str(exe_path), "--version"], timeout=5)
        return code == 0 and len(out.strip()) > 0
    except Exception:
        return False


def install_tool(
    tool_key: str,
    progress_cb: Optional[Callable[[int], None]] = None,
    bin_dir: Optional[Path] = None,
) -> bool:
    """Download and extract a tool by its key ('yt-dlp', 'ffmpeg', 'deno')."""
    target_dir = bin_dir or BIN_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    manifest = get_tools_manifest()
    entry = manifest.get(tool_key)
    if not entry:
        return False

    url = entry["url"]
    file_type = entry.get("type", "exe")
    target_files = entry.get("target_files", [])

    temp_file = target_dir / f"{tool_key}.download.tmp"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(temp_file, "wb") as out:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 64 * 1024
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total_size > 0:
                    pct = int((downloaded / total_size) * 100)
                    progress_cb(pct)

        if file_type == "exe":
            target_path = target_dir / target_files[0]
            if temp_file.exists():
                shutil.move(str(temp_file), str(target_path))
        elif file_type == "zip":
            with zipfile.ZipFile(str(temp_file), "r") as zf:
                for member in zf.namelist():
                    member_name = Path(member).name.lower()
                    for tf in target_files:
                        if member_name == tf.lower():
                            dest_path = target_dir / tf
                            with zf.open(member) as source, open(dest_path, "wb") as target:
                                shutil.copyfileobj(source, target)
            temp_file.unlink(missing_ok=True)

        return all(verify_tool(tf, target_dir) for tf in target_files)

    except Exception as exc:
        get_logger().error(f"Failed to install tool {tool_key}: {exc}")
        temp_file.unlink(missing_ok=True)
        return False


def update_ytdlp(bin_dir: Optional[Path] = None) -> bool:
    """Safely update yt-dlp.exe with validation and rollback on failure."""
    target_dir = bin_dir or BIN_DIR
    current_exe = target_dir / "yt-dlp.exe"
    new_exe = target_dir / "yt-dlp.exe.new"
    bak_exe = target_dir / "yt-dlp.exe.bak"

    url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(new_exe, "wb") as out:
            shutil.copyfileobj(resp, out)

        # Validate downloaded binary
        code, out = run_hidden([str(new_exe), "--version"], timeout=5)
        if code != 0 or not out.strip():
            new_exe.unlink(missing_ok=True)
            get_logger().warning("Downloaded yt-dlp failed validation. Rolled back.")
            return False

        # Backup existing and replace
        if current_exe.exists():
            if bak_exe.exists():
                bak_exe.unlink(missing_ok=True)
            shutil.move(str(current_exe), str(bak_exe))

        shutil.move(str(new_exe), str(current_exe))
        get_logger().info("Successfully updated yt-dlp to latest release.")
        return True

    except Exception as exc:
        get_logger().error(f"yt-dlp update encountered an error: {exc}")
        new_exe.unlink(missing_ok=True)
        return False
