import json
import os
import shutil
import time
from pathlib import Path
from app.version import APP_NAME

_appdata_env = os.environ.get("APPDATA")
if _appdata_env:
    APP_DATA = Path(_appdata_env) / APP_NAME
else:
    APP_DATA = Path.home() / "AppData" / "Roaming" / APP_NAME

BIN_DIR       = APP_DATA / "bin"
TMP_DIR       = APP_DATA / "tmp"          # Phase 1: app-owned temp, never user Downloads
HISTORY_DIR   = APP_DATA / "history"
HISTORY_DB    = HISTORY_DIR / "history.db"
THUMBS_DIR    = HISTORY_DIR / "thumbs"
SETTINGS_FILE = APP_DATA / "settings.json"
LOGS_DIR      = APP_DATA / "logs"
LOG_FILE      = LOGS_DIR / "app.log"
APP_LOG_FILE  = LOG_FILE
DEFAULT_DOWNLOADS = Path.home() / "Downloads"


def job_tmp_dir(job_id: str) -> Path:
    """Return a dedicated subfolder in TMP_DIR for this job."""
    short = (job_id or "tmp").replace("-", "")[:12]
    return TMP_DIR / short


def ensure_dirs() -> None:
    """Ensure all required application directories exist."""
    APP_DATA.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def purge_stale_tmp(max_age_days: int = 7) -> None:
    """Remove files and subdirectories in TMP_DIR older than max_age_days (called at startup).

    Preserves any folder matching an active job in queue_video.json or queue_audio.json.
    """
    cutoff = time.time() - max_age_days * 86400

    # Collect protected folder names from persisted queues
    protected_names = set()
    for queue_filename in ("queue_video.json", "queue_audio.json"):
        q_file = APP_DATA / queue_filename
        if q_file.exists():
            try:
                raw = q_file.read_text(encoding="utf-8").strip()
                if raw:
                    items = json.loads(raw)
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                jid = item.get("job_id") or item.get("id") or ""
                                if jid:
                                    protected_names.add(jid)
                                    protected_names.add(jid.replace("-", "")[:12])
            except Exception as exc:
                from app.core.logger import get_logger
                get_logger().debug(f"Could not read {q_file} during purge: {exc}")

    try:
        if not TMP_DIR.exists():
            return
        for entry in TMP_DIR.iterdir():
            if entry.name in protected_names:
                continue

            try:
                stat = entry.stat()
                if stat.st_mtime < cutoff:
                    if entry.is_dir():
                        shutil.rmtree(entry, ignore_errors=True)
                    else:
                        entry.unlink(missing_ok=True)
            except Exception as exc:
                from app.core.logger import get_logger
                get_logger().debug(f"Failed to purge stale tmp entry {entry}: {exc}")
    except Exception as exc:
        from app.core.logger import get_logger
        get_logger().debug(f"Error purging stale tmp dir: {exc}")


ensure_dirs()
