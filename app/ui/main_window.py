import sys
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
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
from app.core.network_monitor import NetworkMonitor
from app.core.settings import load_settings, save_settings
from app.ui.audio_tab import AudioTab
from app.ui.history_tab import HistoryTab
from app.ui.settings_dialog import SettingsDialog
from app.ui.video_tab import VideoTab
from app.version import APP_NAME, APP_VERSION


def get_asset_path(filename: str) -> Path:
    """Return path to asset file whether running from source or frozen binary."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "assets"
    else:
        base = Path(__file__).resolve().parents[2] / "assets"
    return base / filename


class StatusDot(QWidget):
    """An 8px circular status indicator dot."""

    def __init__(self, color_hex: str = "#2BA640", parent: QWidget | None = None):
        super().__init__(parent)
        self._color = QColor(color_hex)
        self.setFixedSize(8, 8)

    def set_color(self, color_hex: str) -> None:
        self._color = QColor(color_hex)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self._color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 8, 8)


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

        layout.addStretch(1)

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
            self.msg_label.setText(f"Version {info.latest_version} is required. Please update now.")
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
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(760, 560)
        self.setMinimumSize(640, 480)

        icon_path = get_asset_path("icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Update banner at the very top (hidden by default)
        self.update_banner = UpdateBanner(self)
        layout.addWidget(self.update_banner)

        self.tab_widget = QTabWidget(self)
        layout.addWidget(self.tab_widget)

        # Top-right status area
        self.status_container = QWidget(self)
        status_layout = QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(0, 0, 8, 0)
        status_layout.setSpacing(6)

        self.status_dot = StatusDot("#2BA640", self.status_container)
        self.status_label = QLabel("Online", self.status_container)
        self.status_label.setProperty("role", "success")

        status_layout.addWidget(self.status_dot)
        status_layout.addWidget(self.status_label)

        # Settings button
        self.settings_btn = QPushButton("Settings", self.status_container)
        self.settings_btn.setProperty("role", "secondary")
        self.settings_btn.setFixedHeight(28)
        self.settings_btn.clicked.connect(self._open_settings)
        status_layout.addWidget(self.settings_btn)

        status_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.tab_widget.setCornerWidget(self.status_container, Qt.Corner.TopRightCorner)

        # Tabs
        self.video_tab = VideoTab(self)
        self.video_tab.download_completed.connect(self._on_download_finished_notification)
        self.tab_widget.addTab(self.video_tab, "Video")

        self.audio_tab = AudioTab(self)
        self.audio_tab.download_completed.connect(self._on_download_finished_notification)
        self.tab_widget.addTab(self.audio_tab, "Audio")

        self.history_tab = HistoryTab(self)
        self.history_tab.redownload_requested.connect(self._on_redownload)
        self.tab_widget.addTab(self.history_tab, "History")

        # System tray icon for finish notifications
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = get_asset_path("icon.ico")
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

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()

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
        self.status_dot.set_color("#CC0000")
        self.status_label.setText("Offline")
        self.status_label.setProperty("role", "error")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

        self.video_tab.set_online(False)
        self.audio_tab.set_online(False)

        QMessageBox.information(
            self,
            APP_NAME,
            "Internet is off. You can still view your history.",
        )

    def _on_came_online(self) -> None:
        self.status_dot.set_color("#2BA640")
        self.status_label.setText("Online")
        self.status_label.setProperty("role", "success")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

        self.video_tab.set_online(True)
        self.audio_tab.set_online(True)

    def _on_redownload(self, url: str, item_type: str) -> None:
        if item_type.lower() == "audio":
            self.tab_widget.setCurrentIndex(1)
            self.audio_tab.url_input.setText(url)
            self.audio_tab.fetch_url()
        else:
            self.tab_widget.setCurrentIndex(0)
            self.video_tab.url_input.setText(url)
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
