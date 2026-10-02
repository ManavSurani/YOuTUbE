"""Automatic desktop shortcut creator using native Windows APIs and win32com."""

import ctypes
from ctypes import wintypes
import sys
import uuid
from pathlib import Path
from typing import Optional
from app.version import APP_NAME
from app.core.settings import load_settings, save_settings
from app.core.logger import get_logger

try:
    import win32com.client
except Exception as _import_exc:
    win32com = None

logger = get_logger()


def get_desktop_dir() -> Path:
    """Resolve the actual Desktop directory handling OneDrive redirection via Known Folder API."""
    try:
        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", wintypes.BYTE * 8),
            ]

            def __init__(self, guid_str: str):
                u = uuid.UUID(guid_str)
                self.Data1 = u.time_low
                self.Data2 = u.time_mid
                self.Data3 = u.time_hi_version
                self.Data4 = (wintypes.BYTE * 8)(*u.bytes[8:])

        # FOLDERID_Desktop: {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
        folder_id = GUID("{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}")
        sh_get_known_folder_path = ctypes.windll.shell32.SHGetKnownFolderPath
        sh_get_known_folder_path.argtypes = [
            ctypes.POINTER(GUID),
            wintypes.DWORD,
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.LPWSTR),
        ]
        sh_get_known_folder_path.restype = ctypes.c_long

        path_ptr = wintypes.LPWSTR()
        res = sh_get_known_folder_path(ctypes.byref(folder_id), 0, None, ctypes.byref(path_ptr))
        if res == 0 and path_ptr.value:
            desktop = Path(path_ptr.value)
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            if desktop.exists():
                return desktop
    except Exception as exc:
        logger.debug(f"Failed to query Known Folder Desktop: {exc}")

    # Fallback to standard User Profile Desktop
    return Path.home() / "Desktop"


def create_desktop_shortcut(
    force: bool = False,
    custom_target: Optional[Path | str] = None,
    custom_icon: Optional[Path | str] = None,
    desktop_dir_override: Optional[Path] = None,
) -> bool:
    """Create Desktop shortcut once on first run.

    Rules:
    1. If running from source in development and not force, skip.
    2. If settings['shortcut_created'] is True and not force:
       DO NOT recreate even if the shortcut was deleted by the user.
    3. If shortcut already exists (e.g. created by Inno Setup installer):
       Mark shortcut_created = True and return True.
    4. Otherwise, create the shortcut with win32com and mark shortcut_created = True.
    """
    is_frozen = getattr(sys, "frozen", False)
    if not is_frozen and not force:
        return False

    settings = load_settings()
    if settings.get("shortcut_created", False) and not force:
        logger.debug("Desktop shortcut already handled in prior session; skipping.")
        return False

    desktop_dir = desktop_dir_override if desktop_dir_override is not None else get_desktop_dir()
    shortcut_path = desktop_dir / f"{APP_NAME}.lnk"

    # Situation 1 & 3: Shortcut already exists (e.g. created by installer)
    if shortcut_path.exists() and not force:
        settings["shortcut_created"] = True
        save_settings(settings)
        logger.info(f"Existing desktop shortcut acknowledged: {shortcut_path}")
        return True

    target_exe = Path(custom_target) if custom_target else Path(sys.executable)

    if custom_icon:
        icon_path = Path(custom_icon)
    elif is_frozen and hasattr(sys, "_MEIPASS"):
        icon_path = Path(sys._MEIPASS) / "assets" / "icon.ico"
    else:
        icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.ico"

    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(shortcut_path))
        shortcut.TargetPath = str(target_exe)
        shortcut.WorkingDirectory = str(target_exe.parent)
        if icon_path.exists():
            shortcut.IconLocation = f"{icon_path},0"
        shortcut.Save()

        settings["shortcut_created"] = True
        save_settings(settings)
        logger.info(f"Created desktop shortcut via win32com: {shortcut_path}")
        return True
    except Exception as exc:
        logger.warning(f"Failed to create desktop shortcut with win32com: {exc}")
        return False

