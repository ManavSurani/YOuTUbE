"""Safe desktop file and folder actions using Windows Shell APIs without console flashes."""

import ctypes
import os
from pathlib import Path
import sys
from typing import Tuple, Union

from app.core.logger import get_logger

logger = get_logger()


def build_select_command(path: Union[str, Path]) -> str:
    """Build the Explorer /select parameter string."""
    norm_path = Path(path).resolve()
    return f'/select,"{norm_path}"'


def open_folder(path: Union[str, Path]) -> Tuple[bool, str]:
    """Open folder in Windows Explorer with os.startfile."""
    if sys.platform != "win32":
        return False, "Not supported on this system"

    try:
        folder = Path(path).resolve()
        if not folder.exists() or not folder.is_dir():
            logger.warning(f"Cannot open folder: does not exist or not a directory: {folder}")
            return False, "Folder not found."

        os.startfile(str(folder))
        return True, ""
    except Exception as exc:
        logger.error(f"Failed to open folder '{path}': {exc}")
        return False, f"Could not open folder: {exc}"


def reveal_in_folder(path: Union[str, Path]) -> Tuple[bool, str]:
    """Ask Explorer to highlight the file selected using Windows ShellExecuteW."""
    if sys.platform != "win32":
        return False, "Not supported on this system"

    try:
        target = Path(path).resolve()
        if not target.exists():
            logger.warning(f"File to reveal does not exist: {target}, attempting parent folder")
            if target.parent.exists():
                return open_folder(target.parent)
            return False, "Folder not found."

        param = build_select_command(target)
        # SW_SHOWNORMAL = 1
        res = ctypes.windll.shell32.ShellExecuteW(None, "open", "explorer.exe", param, None, 1)
        if res <= 32:
            logger.warning(f"ShellExecuteW returned {res} when revealing {target}")
            # Fallback to opening folder directly
            if target.parent.exists():
                return open_folder(target.parent)
            return False, "Could not open folder in Explorer."

        return True, ""
    except Exception as exc:
        logger.error(f"Failed to reveal in folder '{path}': {exc}")
        try:
            target = Path(path).resolve()
            if target.parent.exists():
                return open_folder(target.parent)
        except Exception:
            pass
        return False, f"Could not open folder in Explorer: {exc}"


def open_file(path: Union[str, Path]) -> Tuple[bool, str]:
    """Open file with default system application, or fallback to folder reveal."""
    if sys.platform != "win32":
        return False, "Not supported on this system"

    try:
        target = Path(path).resolve()
        if not target.exists() or not target.is_file():
            logger.warning(f"Cannot play/open file: not found on disk: {target}")
            if target.parent.exists():
                open_folder(target.parent)
            return False, "File not found. You can use Locate file."

        try:
            os.startfile(str(target))
            return True, ""
        except OSError as os_err:
            logger.warning(f"os.startfile failed for '{target}': {os_err}")
            # Fallback order: reveal it, else parent
            reveal_ok, _ = reveal_in_folder(target)
            if not reveal_ok and target.parent.exists():
                open_folder(target.parent)
            return False, "No app is set to open this type of file."
        except Exception as exc:
            logger.error(f"Unexpected error opening file '{target}': {exc}")
            reveal_ok, _ = reveal_in_folder(target)
            if not reveal_ok and target.parent.exists():
                open_folder(target.parent)
            return False, f"Could not open file: {exc}"
    except Exception as exc:
        logger.error(f"Failed in open_file '{path}': {exc}")
        return False, "File not found. You can use Locate file."
