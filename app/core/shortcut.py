"""Automatic desktop shortcut creator running completely hidden via proc.py."""

import sys
from pathlib import Path
from typing import Optional
from app.version import APP_NAME
from app.core.proc import run_hidden
from app.core.settings import load_settings, save_settings
from app.core.logger import get_logger


def get_desktop_dir() -> Path:
    """Resolve the actual Desktop directory handling OneDrive redirection."""
    ps_cmd = "[Environment]::GetFolderPath('Desktop')"
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_cmd]
    code, out = run_hidden(cmd, timeout=5)
    if code == 0 and out.strip():
        return Path(out.strip())
    return Path.home() / "Desktop"


def create_desktop_shortcut(
    force: bool = False,
    custom_target: Optional[Path | str] = None,
    custom_icon: Optional[Path | str] = None,
) -> bool:
    """Create Desktop shortcut once on first run, skipped when running from source unless forced."""
    is_frozen = getattr(sys, "frozen", False)
    if not is_frozen and not force:
        return False

    settings = load_settings()
    if settings.get("shortcut_created", False) and not force:
        return False

    desktop_dir = get_desktop_dir()
    shortcut_path = desktop_dir / f"{APP_NAME}.lnk"

    if shortcut_path.exists() and not force:
        settings["shortcut_created"] = True
        save_settings(settings)
        return True

    target_exe = Path(custom_target) if custom_target else Path(sys.executable)
    
    if custom_icon:
        icon_path = Path(custom_icon)
    elif is_frozen and hasattr(sys, "_MEIPASS"):
        icon_path = Path(sys._MEIPASS) / "assets" / "icon.ico"
    else:
        icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.ico"

    ps_script = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = '{target_exe}'
    $Shortcut.IconLocation = '{icon_path},0'
    $Shortcut.Save()
    """

    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_script]
    code, out = run_hidden(cmd, timeout=10)

    if code == 0:
        settings["shortcut_created"] = True
        save_settings(settings)
        get_logger().info(f"Created desktop shortcut: {shortcut_path}")
        return True
    else:
        get_logger().error(f"Failed to create desktop shortcut: {out}")
        return False
