"""Main application window using custom Header and QStackedWidget.

Fixes:
  B10: Replaces QTabWidget corner widget with 52px Header (Settings button is never clipped).
  B14: Enables DwmSetWindowAttribute immersive dark title bar on Windows 10/11.
Centers content in maximum ~1100px width with 760x520 minimum window dimensions.
"""

import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import time
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from app.core.app_updater import (
    UpdateCheckWorker,
    UpdateDownloadWorker,
    UpdateInfo,
    launch_silent_installer,
    should_check_update,
)
from app.core.logger import get_logger
from app.core.network_monitor import NetworkMonitor
from app.core.settings import load_settings, save_settings
from app.ui.audio_tab import AudioTab
from app.ui.header import Header, get_asset_path
from app.ui.history_tab import HistoryTab
from app.ui.settings_dialog import SettingsDialog
from app.ui.video_tab import VideoTab
from app.version import APP_NAME, APP_VERSION


def apply_dark_title_bar(window_hwnd: int, is_dark: bool = True) -> None:
    """Set Windows title bar to immersive dark mode (Win10 20H1+ and Win11)."""
    try:
        dwm = ctypes.windll.dwmapi
        val = ctypes.c_int(1 if is_dark else 0)
        # 20 is DWMWA_USE_IMMERSIVE_DARK_MODE
        res = dwm.DwmSetWindowAttribute(
            wintypes.HWND(window_hwnd),
            ctypes.c_uint(20),
            ctypes.byref(val),
            ctypes.sizeof(val),
        )
        if res != 0:
            # 19 was used on earlier Windows 10 builds
            dwm.DwmSetWindowAttribute(
                wintypes.HWND(window_hwnd),
                ctypes.c_uint(19),
                ctypes.byref(val),
                ctypes.sizeof(val),
            )
    except Exception as exc:
        get_logger().debug(f"apply_dark_title_bar skipped/failed: {exc}")


class UpdateBanner(QWidget):
    """Notification banner displayed at top of window when an update is available or required."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._info: Optional[UpdateInfo] = None
        self._download_worker: Optional[UpdateDownloadWorker] = None
        self.setVisible(False)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedHeight(44)
        self.setStyleSheet(
            "UpdateBanner { background-color: #212121; border-radius: 8px; } "
            "QLabel { color: #3EA6FF; font-size: 13px; font-weight: 500; } "
            "QPushButton { font-size: 12px; font-weight: 500; padding: 4px 12px; border-radius: 6px; } "
            "QPushButton#updateBtn { background-color: #3EA6FF; color: #000000; border: none; } "
            "QPushButton#updateBtn:hover { background-color: #65B8FF; } "
            "QPushButton#laterBtn { background-color: transparent; color: #AAAAAA; border: 1px solid #333333; } "
            "QPushButton#laterBtn:hover { background-color: #2A2A2A; color: #FFFFFF; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        self.msg_label = QLabel(self)
        layout.addWidget(self.msg_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar, 1)

        self.update_btn = QPushButton("Update now", self)
        self.update_btn.setObjectName("updateBtn")
        self.update_btn.clicked.connect(self._on_update_clicked)
        layout.addWidget(self.update_btn)

        self.later_btn = QPushButton("Later", self)
        self.later_btn.setObjectName("laterBtn")
        self.later_btn.clicked.connect(self._on_later_clicked)
        layout.addWidget(self.later_btn)

    def show_update(self, info: UpdateInfo) -> None:
        self._info = info
        if info.status == "required":
            self.msg_label.setText(f"Version {info.latest_version} is required. Downloads are paused.")
            self.later_btn.setVisible(False)
        else:
            self.msg_label.setText(f"Version {info.latest_version} is available.")
            self.later_btn.setVisible(True)

        self.progress_bar.setVisible(False)
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Update now")
        self.setVisible(True)

    def _on_later_clicked(self) -> None:
        self.setVisible(False)

    def _on_update_clicked(self) -> None:
        if not self._info:
            return

        self.update_btn.setEnabled(False)
        self.later_btn.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.msg_label.setText(f"Downloading version {self._info.latest_version}…")

        self._download_worker = UpdateDownloadWorker(self._info, parent=self)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.stage.connect(self._on_download_stage)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.failed.connect(self._on_download_failed)
        self._download_worker.start()

    def _on_download_progress(self, percent: float) -> None:
        self.progress_bar.setValue(int(percent))
        if self._info:
            self.msg_label.setText(f"Downloading version {self._info.latest_version}… {int(percent)}%")

    def _on_download_stage(self, stage_text: str) -> None:
        self.msg_label.setText(stage_text)

    def _on_download_finished(self, installer_path: str) -> None:
        self.msg_label.setText("Installing update…")
        self.progress_bar.setVisible(False)
        success = launch_silent_installer(installer_path)
        if success:
            QApplication.quit()
        else:
            self.msg_label.setText("Failed to start installer.")
            self.update_btn.setText("Retry")
            self.update_btn.setEnabled(True)

    def _on_download_failed(self, error_msg: str) -> None:
        self.progress_bar.setVisible(False)
        self.msg_label.setText(error_msg)
        self.update_btn.setText("Retry")
        self.update_btn.setEnabled(True)
        if self._info and self._info.status != "required":
            self.later_btn.setVisible(True)


class MainWindow(QMainWindow):
    """Main application window with custom animated Header and centered layout."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(800, 600)
        self.setMinimumSize(760, 520)

        icon_path = get_asset_path("icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Custom Header (Full width, 52px height)
        self.header = Header(self)
        self.header.tab_changed.connect(self._on_tab_changed)
        self.header.settings_clicked.connect(self._open_settings)
        root_layout.addWidget(self.header)

        # Convenient aliases for tests and status management
        self.status_dot = self.header.status_dot
        self.status_label = self.header.status_label
        self.settings_btn = self.header.settings_btn

        # 2. Centered content wrapper (max width 1100 px)
        outer_content = QWidget(self)
        outer_layout = QHBoxLayout(outer_content)
        outer_layout.setContentsMargins(16, 8, 16, 16)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.content_container = QWidget(outer_content)
        self.content_container.setMaximumWidth(1100)
        inner_layout = QVBoxLayout(self.content_container)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(12)

        # Update banner
        self.update_banner = UpdateBanner(self.content_container)
        inner_layout.addWidget(self.update_banner)

        # 3. Stacked widget for tabs
        self.stacked_widget = QStackedWidget(self.content_container)
        inner_layout.addWidget(self.stacked_widget, 1)

        outer_layout.addWidget(self.content_container)
        root_layout.addWidget(outer_content, 1)

        # Initialize tab pages
        self.video_tab = VideoTab(self)
        self.video_tab.download_completed.connect(self._on_download_finished_notification)
        self.stacked_widget.addWidget(self.video_tab)

        self.audio_tab = AudioTab(self)
        self.audio_tab.download_completed.connect(self._on_download_finished_notification)
        self.stacked_widget.addWidget(self.audio_tab)

        self.history_tab = HistoryTab(self)
        self.history_tab.redownload_requested.connect(self._on_redownload)
        self.stacked_widget.addWidget(self.history_tab)

        # System tray icon for finish notifications
        self.tray_icon = QSystemTrayIcon(self)
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        self.tray_icon.show()

        # Network monitor
        self.network_monitor = NetworkMonitor(parent=self)
        self.network_monitor.went_offline.connect(self._on_went_offline)
        self.network_monitor.came_online.connect(self._on_came_online)
        self.network_monitor.start()

        # Update check worker
        self._update_worker: Optional[UpdateCheckWorker] = None
        self._check_for_updates()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Apply dark title bar (B14 fix)
        try:
            settings = load_settings()
            is_dark = settings.get("theme", "dark").lower() != "light"
            apply_dark_title_bar(int(self.winId()), is_dark=is_dark)
        except Exception as exc:
            get_logger().debug(f"Title bar theming skipped: {exc}")

    def _on_tab_changed(self, index: int) -> None:
        self.stacked_widget.setCurrentIndex(index)
        # Refresh history tab if switched to history
        if index == 2 and hasattr(self.history_tab, "refresh_items"):
            self.history_tab.refresh_items()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()
        # Re-apply title bar in case theme changed
        settings = load_settings()
        is_dark = settings.get("theme", "dark").lower() != "light"
        apply_dark_title_bar(int(self.winId()), is_dark=is_dark)

    def _on_download_finished_notification(self, title: str) -> None:
        if not self.isActiveWindow():
            self.tray_icon.showMessage(
                APP_NAME,
                "Download finished",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def _check_for_updates(self) -> None:
        settings = load_settings()
        if should_check_update(settings):
            self._update_worker = UpdateCheckWorker(parent=self)
            self._update_worker.checked.connect(self._on_update_checked)
            self._update_worker.start()

    def _on_update_checked(self, info: UpdateInfo) -> None:
        settings = load_settings()
        settings["last_app_check"] = int(time.time())
        save_settings(settings)

        self.apply_update_info(info)

    def apply_update_info(self, info: UpdateInfo) -> None:
        """Apply an update check outcome to the UI."""
        if info.status in ("available", "required"):
            self.update_banner.show_update(info)
            if info.status == "required":
                # Lock download controls; History stays fully usable
                self.video_tab.url_input.setEnabled(False)
                self.video_tab.fetch_btn.setEnabled(False)
                self.video_tab.download_btn.setEnabled(False)
                self.video_tab.quality_combo.setEnabled(False)
                self.audio_tab.url_input.setEnabled(False)
                self.audio_tab.fetch_btn.setEnabled(False)
                self.audio_tab.download_btn.setEnabled(False)
                self.audio_tab.format_combo.setEnabled(False)

    def _on_went_offline(self) -> None:
        self.header.set_online(False)
        self.video_tab.set_online(False)
        self.audio_tab.set_online(False)

        QMessageBox.information(
            self,
            APP_NAME,
            "Internet is off. You can still view your history.",
        )

    def _on_came_online(self) -> None:
        self.header.set_online(True)
        self.video_tab.set_online(True)
        self.audio_tab.set_online(True)

    def _on_redownload(self, url: str, item_type: str, quality: str = "") -> None:
        if item_type.lower() == "audio":
            self.header.select_tab(1)
            self.audio_tab.url_input.setText(url)
            if quality:
                self.audio_tab.preselect_quality(quality)
            self.audio_tab.fetch_url()
        else:
            self.header.select_tab(0)
            self.video_tab.url_input.setText(url)
            if quality:
                self.video_tab.preselect_quality(quality)
            self.video_tab.fetch_url()

    def closeEvent(self, event) -> None:
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.hide()
        if hasattr(self, "network_monitor"):
            self.network_monitor.stop()
            self.network_monitor.wait(500)
        if self._update_worker and self._update_worker.isRunning():
            self._update_worker.wait(500)
        if self.update_banner._download_worker and self.update_banner._download_worker.isRunning():
            self.update_banner._download_worker.cancel()
            self.update_banner._download_worker.wait(500)
        super().closeEvent(event)
