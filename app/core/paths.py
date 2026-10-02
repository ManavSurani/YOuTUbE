import os
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
DEFAULT_DOWNLOADS = Path.home() / "Downloads"


def ensure_dirs() -> None:
    """Ensure all required application directories exist."""
    APP_DATA.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def purge_stale_tmp(max_age_days: int = 7) -> None:
    """Remove files in TMP_DIR older than max_age_days (called at startup)."""
    cutoff = time.time() - max_age_days * 86400
    try:
        for f in TMP_DIR.iterdir():
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
            except Exception:
                pass
    except Exception:
        pass


ensure_dirs()
