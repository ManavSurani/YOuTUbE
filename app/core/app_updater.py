"""Application updater module: manifest checks, SHA-256 verification, and silent install."""

import hashlib
import json
import re
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QThread, Signal

from app.core.logger import get_logger
from app.core.proc import start_hidden
from app.version import APP_NAME, APP_VERSION, UPDATE_MANIFEST_URL


def parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse version string into a tuple of integers for accurate numeric comparison."""
    clean = version_str.strip().lstrip("vV")
    parts = re.findall(r"\d+", clean)
    if not parts:
        return (0,)
    return tuple(int(p) for p in parts)


@dataclass
class UpdateInfo:
    """Parsed update manifest outcome."""

    status: str  # "none", "available", "required"
    latest_version: str = ""
    min_supported_version: str = ""
    release_date: str = ""
    installer_url: str = ""
    sha256: str = ""
    notes: List[str] = field(default_factory=list)
    force_update: bool = False


def check_manifest_dict(data: Dict[str, Any], current_version: str = APP_VERSION) -> UpdateInfo:
    """Evaluate raw manifest dictionary against current version."""
    logger = get_logger()

    latest = str(data.get("latest_version", "")).strip()
    installer_url = str(data.get("installer_url", "")).strip()
    sha256 = str(data.get("sha256", "")).strip().lower()
    min_supported = str(data.get("min_supported_version", "")).strip()
    force_update = bool(data.get("force_update", False))
    release_date = str(data.get("release_date", "")).strip()
    notes_raw = data.get("notes", [])
    notes = [str(n) for n in notes_raw] if isinstance(notes_raw, list) else []

    if not latest or not installer_url or not sha256:
        logger.warning("Manifest missing required fields (latest_version, installer_url, or sha256).")
        return UpdateInfo(status="none")

    curr_parsed = parse_version(current_version)
    latest_parsed = parse_version(latest)

    # 1. Check if update is strictly required
    if min_supported:
        min_parsed = parse_version(min_supported)
        if curr_parsed < min_parsed:
            return UpdateInfo(
                status="required",
                latest_version=latest,
                min_supported_version=min_supported,
                release_date=release_date,
                installer_url=installer_url,
                sha256=sha256,
                notes=notes,
                force_update=force_update,
            )

    if force_update and latest_parsed > curr_parsed:
        return UpdateInfo(
            status="required",
            latest_version=latest,
            min_supported_version=min_supported,
            release_date=release_date,
            installer_url=installer_url,
            sha256=sha256,
            notes=notes,
            force_update=force_update,
        )

    # 2. Check if update is available
    if latest_parsed > curr_parsed:
        return UpdateInfo(
            status="available",
            latest_version=latest,
            min_supported_version=min_supported,
            release_date=release_date,
            installer_url=installer_url,
            sha256=sha256,
            notes=notes,
            force_update=force_update,
        )

    # 3. Up to date or manifest older
    return UpdateInfo(status="none", latest_version=latest)


def check_for_update(
    manifest_url: Optional[str] = None,
    current_version: str = APP_VERSION,
    timeout: float = 10.0,
) -> UpdateInfo:
    """Fetch version.json and evaluate against current version."""
    url = manifest_url or UPDATE_MANIFEST_URL
    if not url:
        return UpdateInfo(status="none")

    logger = get_logger()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{current_version}"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            logger.warning("Manifest response is not a valid JSON object.")
            return UpdateInfo(status="none")
        return check_manifest_dict(payload, current_version=current_version)
    except Exception as exc:
        logger.warning(f"Failed to check for updates: {exc}")
        return UpdateInfo(status="none")


def should_check_update(settings: Dict[str, Any], now: Optional[float] = None) -> bool:
    """Check if 24 hours have elapsed since last check and auto_update is enabled."""
    if not settings.get("auto_update", True):
        return False
    last_check = settings.get("last_app_check", 0)
    current_time = now if now is not None else time.time()
    return (current_time - last_check) >= 86400


class UpdateCheckWorker(QThread):
    """Background worker for querying version manifest."""

    checked = Signal(object)  # UpdateInfo

    def __init__(
        self,
        manifest_url: Optional[str] = None,
        current_version: str = APP_VERSION,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.manifest_url = manifest_url
        self.current_version = current_version

    def run(self) -> None:
        result = check_for_update(self.manifest_url, self.current_version)
        self.checked.emit(result)


class UpdateDownloadWorker(QThread):
    """Worker thread downloading installer to %TEMP% and verifying SHA-256."""

    progress = Signal(float)  # 0 to 100
    stage = Signal(str)
    finished = Signal(str)  # Target installer path on success
    failed = Signal(str)  # Error message

    def __init__(self, update_info: UpdateInfo, parent=None) -> None:
        super().__init__(parent)
        self.info = update_info
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        logger = get_logger()
        temp_dir = Path(tempfile.gettempdir())
        target_path = temp_dir / f"{APP_NAME}_Setup_{self.info.latest_version}.exe"
        part_path = temp_dir / f"{APP_NAME}_Setup_{self.info.latest_version}.exe.part"

        self.stage.emit("Downloading update…")
        logger.info(f"Downloading update from {self.info.installer_url} to {target_path}")

        try:
            req = urllib.request.Request(
                self.info.installer_url,
                headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
            )
            hasher = hashlib.sha256()

            with urllib.request.urlopen(req, timeout=15.0) as resp:
                total_bytes = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024

                with open(part_path, "wb") as f:
                    while not self._is_cancelled:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)

                        if total_bytes > 0:
                            pct = min(100.0, (downloaded / total_bytes) * 100.0)
                            self.progress.emit(pct)

            if self._is_cancelled:
                part_path.unlink(missing_ok=True)
                logger.info("Update download cancelled.")
                return

            self.stage.emit("Verifying update…")
            actual_hash = hasher.hexdigest().lower()
            expected_hash = self.info.sha256.lower().strip()

            if actual_hash != expected_hash:
                part_path.unlink(missing_ok=True)
                logger.error(
                    f"Update verification failed! Expected {expected_hash}, computed {actual_hash}."
                )
                self.failed.emit("The update could not be verified.")
                return

            # Hash matches: move partial file to final target
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            part_path.replace(target_path)

            logger.info("Update download and SHA-256 verification successful.")
            self.stage.emit("Ready")
            self.finished.emit(str(target_path))

        except Exception as exc:
            part_path.unlink(missing_ok=True)
            logger.error(f"Failed to download update: {exc}")
            self.failed.emit("Download failed. Please check network connection.")


def launch_silent_installer(installer_path: Path | str) -> bool:
    """Launch installer silently without any visible console window."""
    path = Path(installer_path)
    if not path.is_file():
        get_logger().error(f"Installer not found at {path}")
        return False

    cmd = [
        str(path),
        "/SILENT",
        "/CLOSEAPPLICATIONS",
        "/RESTARTAPPLICATIONS",
    ]
    logger = get_logger()
    logger.info(f"Launching silent installer: {' '.join(cmd)}")
    try:
        start_hidden(cmd)
        return True
    except Exception as exc:
        logger.error(f"Failed to launch installer: {exc}")
        return False
