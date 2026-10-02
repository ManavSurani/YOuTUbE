import json
from pathlib import Path
from typing import Any, Dict
from app.core.paths import SETTINGS_FILE, DEFAULT_DOWNLOADS, ensure_dirs
from app.core.logger import get_logger

DEFAULTS: Dict[str, Any] = {
    "download_dir": str(DEFAULT_DOWNLOADS),
    "theme": "dark",
    "container": "mkv",
    "auto_update": True,
    "shortcut_created": False,
    "last_tool_check": 0,
    "last_app_check": 0,
}


def get_default_settings() -> Dict[str, Any]:
    """Return a fresh copy of default settings."""
    return dict(DEFAULTS)


def load_settings(settings_path: Path | None = None) -> Dict[str, Any]:
    """Load settings from JSON file, falling back to defaults if missing or corrupt."""
    path = settings_path or SETTINGS_FILE
    settings = get_default_settings()

    if not path.exists():
        return settings

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                settings.update(data)
            else:
                logger = get_logger()
                logger.warning("Corrupt settings file format; resetting to defaults.")
    except Exception as exc:
        logger = get_logger()
        logger.warning(f"Failed to read settings file: {exc}; resetting to defaults.")

    return settings


import os


def save_settings(settings: Dict[str, Any], settings_path: Path | None = None) -> None:
    """Save settings dictionary to JSON file atomically."""
    path = settings_path or SETTINGS_FILE
    ensure_dirs()
    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception as exc:
        logger = get_logger()
        logger.error(f"Failed to save settings: {exc}")
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception as e:
                logger.debug(f"Failed to remove temp settings file: {e}")
