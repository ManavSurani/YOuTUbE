"""Splash screen with quiet startup flow and offline setup handling."""

import socket
import sys
import time
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
)
from app.ui.kit import AnimatedButton
from app.ui.kit.anim import FAST
from app.ui.theme import tok
from app.version import APP_NAME, APP_VERSION
from app.core.app_updater import (
    UpdateDownloadWorker,
    check_for_update,
    launch_silent_installer,
    parse_version,
)
from app.core.paths import BIN_DIR
from app.core.settings import load_settings, save_settings
from app.core.tool_manager import missing_tools, install_tool, update_ytdlp
from app.core.shortcut import create_desktop_shortcut
from app.core.logger import get_logger


def check_internet(host: str = "youtube.com", port: int = 443, timeout: float = 3.0) -> bool:
    """Fast socket connection check for internet reachability."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False


class StartupWorker(QThread):
    """Background startup coordinator executing startup flow off the UI thread."""

    status = Signal(str)
    progress = Signal(int)
    offline_blocked = Signal()
    finished = Signal()
    update_found = Signal(object)  # UpdateInfo

    def __init__(self, parent=None, skip_app_update: bool = False) -> None:
        super().__init__(parent)
        self.skip_app_update = skip_app_update

    def _app_update_allowed(self) -> bool:
        """Only the installed app updates itself, never a source run (python -m app.main)."""
        return (
            getattr(sys, "frozen", False)
            and not self.skip_app_update
            and load_settings().get("auto_update", True)
        )

    def run(self) -> None:
        logger = get_logger()
        logger.info("Startup sequence initiated.")

        # 1. Check internet
        self.status.emit("Connecting…")
        self.progress.emit(10)
        is_online = check_internet()

        # 1b. Check for a new app version before anything else
        if is_online and self._app_update_allowed():
            self.status.emit("Checking for app update…")
            info = check_for_update(timeout=5.0)
            settings = load_settings()
            if info.status in ("available", "required"):
                # Loop guard: this version was already installed once and did not apply
                tried = settings.get("update_attempt_version", "")
                if not (tried == info.latest_version and parse_version(APP_VERSION) < parse_version(tried)):
                    self.update_found.emit(info)
                    return
            else:
                settings["last_app_check"] = int(time.time())
                save_settings(settings)

        # 2. Check tools
        missing = missing_tools()
        if missing:
            if not is_online:
                logger.warning("First-time setup blocked: missing tools and offline.")
                self.offline_blocked.emit()
                return

            total_missing = len(missing)
            for idx, tool_name in enumerate(missing):
                key = "yt-dlp" if "yt-dlp" in tool_name else ("ffmpeg" if "ffmpeg" in tool_name or "ffprobe" in tool_name else "deno")
                self.status.emit(f"Downloading components ({idx + 1}/{total_missing})…")
                install_tool(key, progress_cb=lambda p: self.progress.emit(20 + int(p * 0.6)))

        self.progress.emit(80)

        # 3. Check for 24h tool updates if online
        if is_online and not missing:
            settings = load_settings()
            last_check = settings.get("last_tool_check", 0)
            now = time.time()
            if now - last_check > 86400:  # 24 hours
                self.status.emit("Checking for tool updates…")
                update_ytdlp()
                settings["last_tool_check"] = int(now)
                save_settings(settings)

        self.progress.emit(90)

        # 4. Check Desktop shortcut creation (first run)
        create_desktop_shortcut()

        self.progress.emit(100)
        self.status.emit("Starting…")
        time.sleep(0.15)
        self.finished.emit()


class SplashScreen(QWidget):
    """Clean frameless splash screen with 150ms fade animations."""

    startup_completed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(360, 260)
        # Same background as the main window, so the hand-off does not flash
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"SplashScreen {{ background-color: {tok('bg')}; }}")
        self._setup_ui()
        self._start_worker()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 28, 24, 24)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Centered 96px logo
        self.logo_label = QLabel(self)
        self.logo_label.setFixedSize(96, 96)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if hasattr(sys, "_MEIPASS"):
            logo_path = Path(sys._MEIPASS) / "assets" / "logo_512.png"
        else:
            logo_path = Path(__file__).resolve().parent.parent.parent / "assets" / "logo_512.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(
                96, 96,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo_label.setPixmap(pix)
        layout.addWidget(self.logo_label, 0, Qt.AlignmentFlag.AlignCenter)

        # App title
        self.title_label = QLabel(APP_NAME, self)
        self.title_label.setProperty("role", "title")
        layout.addWidget(self.title_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Status text
        self.status_label = QLabel("Starting…", self)
        self.status_label.setProperty("role", "muted")
        layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignCenter)

        # 6px progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Retry button (visible only if first-run offline setup is blocked)
        self.retry_btn = AnimatedButton("Retry", role="secondary", parent=self)
        self.retry_btn.setFixedHeight(32)
        self.retry_btn.setVisible(False)
        self.retry_btn.clicked.connect(self._on_retry)
        layout.addWidget(self.retry_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def _start_worker(self, skip_app_update: bool = False) -> None:
        self.worker = StartupWorker(self, skip_app_update=skip_app_update)
        self.worker.status.connect(self.status_label.setText)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.offline_blocked.connect(self._on_offline_blocked)
        self.worker.update_found.connect(self._on_update_found)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_update_found(self, info) -> None:
        self._update_version = info.latest_version
        self.status_label.setText(f"Downloading update {info.latest_version}…")
        self.progress_bar.setValue(0)
        self.update_worker = UpdateDownloadWorker(info, parent=self)
        self.update_worker.progress.connect(self._on_update_progress)
        self.update_worker.finished.connect(self._on_update_downloaded)
        self.update_worker.failed.connect(self._on_update_failed)
        self.update_worker.start()

    def _on_update_progress(self, percent: float) -> None:
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(f"Downloading update {self._update_version}… {int(percent)}%")

    def _on_update_downloaded(self, installer_path: str) -> None:
        self.status_label.setText("Installing update…")
        settings = load_settings()
        settings["update_attempt_version"] = self._update_version
        save_settings(settings)
        if launch_silent_installer(installer_path):
            QApplication.quit()
            return
        self._on_update_failed("Failed to start installer.")

    def _on_update_failed(self, error_msg: str) -> None:
        # Any update problem: start normally, exactly as before
        get_logger().warning(f"Startup app update skipped: {error_msg}")
        self._start_worker(skip_app_update=True)

    def _on_offline_blocked(self) -> None:
        self.status_label.setText("Internet is required for first-time setup.")
        self.retry_btn.setVisible(True)

    def _on_retry(self) -> None:
        self.retry_btn.setVisible(False)
        self._start_worker()

    def _on_finished(self) -> None:
        # 150 ms fade-out animation
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(FAST)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self._finish_close)
        self.anim.start()

    def _finish_close(self) -> None:
        self.close()
        self.startup_completed.emit()
