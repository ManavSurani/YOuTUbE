import os
from pathlib import Path
from app.version import APP_NAME

_appdata_env = os.environ.get("APPDATA")
if _appdata_env:
    APP_DATA = Path(_appdata_env) / APP_NAME
else:
    APP_DATA = Path.home() / "AppData" / "Roaming" / APP_NAME

BIN_DIR = APP_DATA / "bin"
HISTORY_DB = APP_DATA / "history.db"
THUMBS_DIR = APP_DATA / "thumbnails"
SETTINGS_FILE = APP_DATA / "settings.json"
LOGS_DIR = APP_DATA / "logs"
LOG_FILE = LOGS_DIR / "app.log"
DEFAULT_DOWNLOADS = Path.home() / "Downloads"


def ensure_dirs() -> None:
    """Ensure all required application directories exist."""
    APP_DATA.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


ensure_dirs()
