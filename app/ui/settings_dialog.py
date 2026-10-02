"""Settings dialog implementation adhering to the minimalist YouTube design system."""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.app_updater import UpdateCheckWorker, UpdateInfo
from app.core.settings import load_settings, save_settings
from app.ui.theme import build_qss
from app.version import APP_NAME, APP_VERSION


class SettingsDialog(QDialog):
    """Clean, focused settings dialog with live theme switching and tool credits."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Settings")
        self.setFixedSize(500, 620)
        self.setModal(True)

        self._settings = load_settings()
        self._update_worker: Optional[UpdateCheckWorker] = None
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # 1. Download folder section
        folder_header = QLabel("Download Folder", self)
        folder_header.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(folder_header)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self.folder_input = QLineEdit(self)
        self.folder_input.setFixedHeight(34)
        folder_row.addWidget(self.folder_input, 1)

        self.browse_btn = QPushButton("Browse…", self)
        self.browse_btn.setProperty("role", "secondary")
        self.browse_btn.setFixedHeight(34)
        self.browse_btn.clicked.connect(self._on_browse)
        folder_row.addWidget(self.browse_btn)
        layout.addLayout(folder_row)

        # 2. Container format section (MKV / MP4)
        container_header = QLabel("Preferred Video Container", self)
        container_header.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(container_header)

        self.container_combo = QComboBox(self)
        self.container_combo.setFixedHeight(34)
        self.container_combo.addItem("MKV (Recommended — supports all resolutions up to 8K)", "mkv")
        self.container_combo.addItem("MP4 (Standard compatibility)", "mp4")
        layout.addWidget(self.container_combo)

        self.container_note = QLabel(
            "Note: MP4 may limit the highest available resolution due to codec support.", self
        )
        self.container_note.setProperty("role", "muted")
        self.container_note.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.container_note)

        # 3. Theme section (Dark / Light)
        theme_header = QLabel("Appearance", self)
        theme_header.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(theme_header)

        self.theme_combo = QComboBox(self)
        self.theme_combo.setFixedHeight(34)
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        layout.addWidget(self.theme_combo)

        # 4. Updates section
        update_header = QLabel("Updates", self)
        update_header.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(update_header)

        update_row = QHBoxLayout()
        update_row.setSpacing(12)

        self.auto_update_check = QCheckBox("Check for updates automatically", self)
        update_row.addWidget(self.auto_update_check, 1)

        self.check_now_btn = QPushButton("Check now", self)
        self.check_now_btn.setProperty("role", "secondary")
        self.check_now_btn.setFixedHeight(32)
        self.check_now_btn.clicked.connect(self._on_check_updates_now)
        update_row.addWidget(self.check_now_btn)
        layout.addLayout(update_row)

        self.update_status_label = QLabel(self)
        self.update_status_label.setProperty("role", "muted")
        self.update_status_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.update_status_label)

        # Divider
        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setProperty("role", "divider")
        layout.addWidget(divider)

        # 5. About section
        about_header = QLabel(f"About {APP_NAME}", self)
        about_header.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(about_header)

        version_label = QLabel(f"Version {APP_VERSION}", self)
        version_label.setProperty("role", "muted")
        layout.addWidget(version_label)

        credits_label = QLabel(
            "Built with open-source tools:\n"
            "• yt-dlp (https://github.com/yt-dlp/yt-dlp)\n"
            "• ffmpeg & ffprobe (https://ffmpeg.org)\n"
            "• deno (https://deno.com)",
            self,
        )
        credits_label.setProperty("role", "muted")
        credits_label.setStyleSheet("font-size: 11px; line-height: 1.4;")
        layout.addWidget(credits_label)

        layout.addStretch(1)

        # Action buttons (Save & Close)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setProperty("role", "secondary")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save", self)
        self.save_btn.setProperty("role", "primary")
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        layout.addLayout(btn_row)

    def _load_values(self) -> None:
        self.folder_input.setText(self._settings.get("download_dir", ""))

        container = self._settings.get("container", "mkv").lower()
        idx_c = self.container_combo.findData(container)
        if idx_c >= 0:
            self.container_combo.setCurrentIndex(idx_c)

        theme = self._settings.get("theme", "dark").lower()
        idx_t = self.theme_combo.findData(theme)
        if idx_t >= 0:
            self.theme_combo.setCurrentIndex(idx_t)

        self.auto_update_check.setChecked(self._settings.get("auto_update", True))

    def _on_browse(self) -> None:
        current = self.folder_input.text().strip()
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select Download Directory",
            current if current and Path(current).is_dir() else str(Path.home()),
        )
        if selected:
            self.folder_input.setText(selected)

    def _on_theme_changed(self, index: int) -> None:
        chosen_theme = self.theme_combo.currentData()
        if chosen_theme in ("dark", "light"):
            app = QApplication.instance()
            if app:
                app.setStyleSheet(build_qss(chosen_theme))

    def _on_check_updates_now(self) -> None:
        self.check_now_btn.setEnabled(False)
        self.update_status_label.setText("Checking for updates…")

        self._update_worker = UpdateCheckWorker(parent=self)
        self._update_worker.checked.connect(self._on_checked_result)
        self._update_worker.start()

    def _on_checked_result(self, info: UpdateInfo) -> None:
        self.check_now_btn.setEnabled(True)
        if info.status in ("available", "required"):
            self.update_status_label.setText(f"Version {info.latest_version} is available!")
            parent_win = self.parent()
            if parent_win and hasattr(parent_win, "apply_update_info"):
                parent_win.apply_update_info(info)
        else:
            self.update_status_label.setText("You are using the latest version.")

    def _on_save(self) -> None:
        folder = self.folder_input.text().strip()
        if folder and Path(folder).is_dir():
            self._settings["download_dir"] = folder

        self._settings["container"] = self.container_combo.currentData()
        self._settings["theme"] = self.theme_combo.currentData()
        self._settings["auto_update"] = self.auto_update_check.isChecked()

        save_settings(self._settings)
        self.accept()
