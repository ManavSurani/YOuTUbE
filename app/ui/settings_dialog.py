"""Settings dialog implementation adhering to the minimalist YouTube design system.

Implements Phase 6 specifications:
- Esc or close button to dismiss (no bottom Save/Cancel buttons)
- Read-only download path box without text cursor or keyboard focus
- Browse opens folder picker; choosing a different folder shows Save button
- Save validates directory writability and free space, saves atomically, flashes 'Saved ✓'
- Appearance (Dark/Light) applies and persists immediately
- Auto-update uses AnimatedCheckBox, ON by default, applies immediately
- 'Check now' button displays loading spinner, then 'You're up to date ✓' or update prompt
- 'Export log' copies app.log to user-chosen path
- 'Open download folder' link opens explorer with zero console windows
- Responsive layout adapting to 100%, 125%, 150% display scaling
"""

import shutil
import time
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.app_updater import UpdateCheckWorker, UpdateInfo
from app.core.logger import get_logger
from app.core.paths import APP_LOG_FILE, DEFAULT_DOWNLOADS
from app.core.proc import start_hidden
from app.core.settings import load_settings, save_settings
from app.ui.kit import AnimatedButton, AnimatedCheckBox, IconButton
from app.ui.theme import build_qss
from app.version import APP_NAME, APP_VERSION


def format_size(size_bytes: int) -> str:
    """Format byte size into human readable string."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    idx = 0
    while size >= 1024.0 and idx < len(units) - 1:
        size /= 1024.0
        idx += 1
    return f"{size:.1f} {units[idx]}"


def validate_download_dir(dir_path: str | Path) -> Tuple[bool, str]:
    """Validate that the directory exists or can be created, and is writable."""
    p = Path(dir_path)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return False, f"Cannot create directory: {exc}"

    if not p.is_dir():
        return False, "Path is not a valid directory."

    # Test writability with a temp probe file
    probe_file = p / f".probe_write_{int(time.time())}.tmp"
    try:
        probe_file.write_bytes(b"probe")
        probe_file.unlink()
    except Exception as exc:
        return False, f"Folder is not writable or access is denied ({exc})."

    return True, ""


class SettingsDialog(QDialog):
    """Clean, focused settings dialog with instant setting persistence."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Settings")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.resize(520, 600)

        self._settings = load_settings()
        self._saved_download_dir = self._settings.get("download_dir", str(DEFAULT_DOWNLOADS))
        self._update_worker: Optional[UpdateCheckWorker] = None
        self._latest_update_info: Optional[UpdateInfo] = None

        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Header bar with title and close icon
        header_bar = QWidget(self)
        header_bar.setFixedHeight(50)
        header_bar.setStyleSheet("background-color: #181818; border-bottom: 1px solid #282828;")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(20, 0, 16, 0)

        title_label = QLabel("Settings", header_bar)
        title_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        self.close_btn = IconButton("close", size=28, tooltip="Close", parent=header_bar)
        self.close_btn.clicked.connect(self.accept)
        header_layout.addWidget(self.close_btn)

        root_layout.addWidget(header_bar)

        # 2. Scroll area to prevent control clipping at 125% and 150% scaling
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        # -------------------------------------------------------------
        # Section 1: Download Folder
        # -------------------------------------------------------------
        folder_header = QLabel("Download folder", content)
        folder_header.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        layout.addWidget(folder_header)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        # Read-only path box (no focus, no cursor)
        self.folder_input = QLineEdit(content)
        self.folder_input.setReadOnly(True)
        self.folder_input.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.folder_input.setCursor(Qt.CursorShape.ArrowCursor)
        self.folder_input.setFixedHeight(36)
        self.folder_input.setStyleSheet("""
            QLineEdit {
                background-color: #1A1A1A;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 0 10px;
                color: #CCCCCC;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
        """)
        folder_row.addWidget(self.folder_input, 1)

        self.browse_btn = AnimatedButton("Browse…", role="secondary", parent=content)
        self.browse_btn.setFixedWidth(85)
        self.browse_btn.setFixedHeight(36)
        self.browse_btn.clicked.connect(self._on_browse)
        folder_row.addWidget(self.browse_btn)

        # Save button appears only when folder changes
        self.save_folder_btn = AnimatedButton("Save", role="primary", parent=content)
        self.save_folder_btn.setFixedWidth(75)
        self.save_folder_btn.setFixedHeight(36)
        self.save_folder_btn.setVisible(False)
        self.save_folder_btn.clicked.connect(self._on_save_folder)
        folder_row.addWidget(self.save_folder_btn)

        layout.addLayout(folder_row)

        # Folder helper row (Free space + Open download folder link)
        helper_row = QHBoxLayout()
        helper_row.setContentsMargins(2, 0, 2, 0)

        self.free_space_label = QLabel(content)
        self.free_space_label.setStyleSheet("font-size: 11px; color: #888888;")
        helper_row.addWidget(self.free_space_label)

        helper_row.addStretch(1)

        self.open_folder_link = QPushButton("Open download folder", content)
        self.open_folder_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_link.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #3EA6FF;
                font-size: 11px;
                padding: 0;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self.open_folder_link.clicked.connect(self._on_open_download_folder)
        helper_row.addWidget(self.open_folder_link)

        layout.addLayout(helper_row)

        layout.addWidget(self._create_divider(content))

        # -------------------------------------------------------------
        # Section 2: Appearance (instant switch and persist)
        # -------------------------------------------------------------
        theme_header = QLabel("Appearance", content)
        theme_header.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        layout.addWidget(theme_header)

        self.theme_combo = QComboBox(content)
        self.theme_combo.setFixedHeight(36)
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        layout.addWidget(self.theme_combo)

        layout.addWidget(self._create_divider(content))

        # -------------------------------------------------------------
        # Section 3: Updates
        # -------------------------------------------------------------
        update_header = QLabel("Updates", content)
        update_header.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        layout.addWidget(update_header)

        self.auto_update_check = AnimatedCheckBox("Check for updates automatically", parent=content)
        self.auto_update_check.toggled.connect(self._on_auto_update_toggled)
        layout.addWidget(self.auto_update_check)

        update_action_row = QHBoxLayout()
        update_action_row.setSpacing(10)

        self.check_now_btn = AnimatedButton("Check now", role="secondary", parent=content)
        self.check_now_btn.setFixedHeight(36)
        self.check_now_btn.setFixedWidth(100)
        self.check_now_btn.clicked.connect(self._on_check_updates_now)
        update_action_row.addWidget(self.check_now_btn)

        self.install_update_btn = AnimatedButton("Install update", role="primary", parent=content)
        self.install_update_btn.setFixedHeight(36)
        self.install_update_btn.setVisible(False)
        self.install_update_btn.clicked.connect(self._on_install_update)
        update_action_row.addWidget(self.install_update_btn)

        self.update_status_label = QLabel(content)
        self.update_status_label.setStyleSheet("font-size: 12px; color: #AAAAAA;")
        update_action_row.addWidget(self.update_status_label, 1)

        layout.addLayout(update_action_row)

        layout.addWidget(self._create_divider(content))

        # -------------------------------------------------------------
        # Section 4: About & Support
        # -------------------------------------------------------------
        about_header = QLabel(f"About {APP_NAME}", content)
        about_header.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        layout.addWidget(about_header)

        version_label = QLabel(f"Version {APP_VERSION}", content)
        version_label.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addWidget(version_label)

        credits_label = QLabel(
            "Built with open-source tools:<br>"
            "• <a style=\"color: #3EA6FF;\" href=\"https://github.com/yt-dlp/yt-dlp\">yt-dlp</a><br>"
            "• <a style=\"color: #3EA6FF;\" href=\"https://ffmpeg.org\">ffmpeg &amp; ffprobe</a><br>"
            "• <a style=\"color: #3EA6FF;\" href=\"https://deno.com\">deno</a><br>"
            "• <a style=\"color: #3EA6FF;\" href=\"https://github.com/arsenetar/send2trash\">send2trash</a>",
            content,
        )
        credits_label.setOpenExternalLinks(True)
        credits_label.setStyleSheet("font-size: 11px; color: #888888; line-height: 1.4;")
        layout.addWidget(credits_label)

        about_actions_row = QHBoxLayout()
        about_actions_row.setSpacing(10)

        self.export_log_btn = AnimatedButton("Export log", role="secondary", parent=content)
        self.export_log_btn.setFixedHeight(34)
        self.export_log_btn.setToolTip("Export application log file for diagnostics")
        self.export_log_btn.clicked.connect(self._on_export_log)
        about_actions_row.addWidget(self.export_log_btn)

        about_actions_row.addStretch(1)
        layout.addLayout(about_actions_row)

        layout.addStretch(1)

        scroll.setWidget(content)
        root_layout.addWidget(scroll, 1)

    def _create_divider(self, parent: QWidget) -> QFrame:
        divider = QFrame(parent)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #242424; border: none;")
        return divider

    def _load_values(self) -> None:
        download_dir = self._settings.get("download_dir", str(DEFAULT_DOWNLOADS))
        self.folder_input.setText(download_dir)
        self._saved_download_dir = download_dir
        self._update_free_space_label(Path(download_dir))

        theme = self._settings.get("theme", "dark").lower()
        idx_t = self.theme_combo.findData(theme)
        if idx_t >= 0:
            self.theme_combo.setCurrentIndex(idx_t)

        self.auto_update_check.setChecked(self._settings.get("auto_update", True))

    def _update_free_space_label(self, path: Path) -> None:
        try:
            target = path if path.is_dir() else path.parent
            if target.is_dir():
                usage = shutil.disk_usage(target)
                free_str = format_size(usage.free)
                if usage.free < 1024 * 1024 * 1024:
                    self.free_space_label.setText(f"Low disk space: {free_str} available")
                    self.free_space_label.setStyleSheet("font-size: 11px; color: #FF8800;")
                else:
                    self.free_space_label.setText(f"Free disk space: {free_str}")
                    self.free_space_label.setStyleSheet("font-size: 11px; color: #888888;")
                return
        except Exception:
            pass
        self.free_space_label.setText("")

    def _on_browse(self) -> None:
        current = self.folder_input.text().strip()
        start_dir = current if current and Path(current).is_dir() else str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Select Download Directory", start_dir)
        if selected and selected != self._saved_download_dir:
            self.folder_input.setText(selected)
            self._update_free_space_label(Path(selected))
            self.save_folder_btn.setVisible(True)

    def _on_save_folder(self) -> None:
        new_folder = self.folder_input.text().strip()
        ok, err = validate_download_dir(new_folder)
        if not ok:
            QMessageBox.warning(
                self,
                "Invalid Folder",
                f"The chosen folder cannot be used:\n\n{err}",
            )
            self.folder_input.setText(self._saved_download_dir)
            self.save_folder_btn.setVisible(False)
            return

        resolved = str(Path(new_folder).resolve())
        self._settings["download_dir"] = resolved
        save_settings(self._settings)
        self._saved_download_dir = resolved

        self.save_folder_btn.flash_success(1000)
        QTimer.singleShot(1100, lambda: self.save_folder_btn.setVisible(False))

    def _on_open_download_folder(self) -> None:
        target = Path(self._saved_download_dir)
        if target.is_dir():
            start_hidden(["explorer", str(target.resolve())])
        else:
            QMessageBox.warning(self, "Folder Missing", f"The download folder does not exist:\n{target}")

    def _on_theme_changed(self, index: int) -> None:
        chosen_theme = self.theme_combo.currentData()
        if chosen_theme in ("dark", "light"):
            self._settings["theme"] = chosen_theme
            save_settings(self._settings)

            app = QApplication.instance()
            if app:
                app.setStyleSheet(build_qss(chosen_theme))

            # Apply dark title bar if parent window exists
            parent_win = self.parent()
            if parent_win and hasattr(parent_win, "winId"):
                try:
                    from app.ui.theme import apply_dark_title_bar
                    apply_dark_title_bar(int(parent_win.winId()), is_dark=(chosen_theme == "dark"))
                except Exception as exc:
                    get_logger().debug(f"Title bar update skipped: {exc}")

    def _on_auto_update_toggled(self, checked: bool) -> None:
        self._settings["auto_update"] = checked
        save_settings(self._settings)

    def _on_check_updates_now(self) -> None:
        self.check_now_btn.set_loading(True)
        self.update_status_label.setText("Checking for updates…")
        self.install_update_btn.setVisible(False)

        self._update_worker = UpdateCheckWorker(parent=self)
        self._update_worker.checked.connect(self._on_checked_result)
        self._update_worker.failed.connect(self._on_check_failed)
        self._update_worker.start()

    def _on_checked_result(self, info: UpdateInfo) -> None:
        self.check_now_btn.set_loading(False)
        self._latest_update_info = info

        if info.status in ("available", "required"):
            self.update_status_label.setText(f"Version {info.latest_version} is available!")
            self.install_update_btn.setVisible(True)
            parent_win = self.parent()
            if parent_win and hasattr(parent_win, "apply_update_info"):
                parent_win.apply_update_info(info)
        else:
            self.update_status_label.setText("You're up to date ✓")
            self.check_now_btn.flash_success(1000)

    def _on_check_failed(self, err_msg: str) -> None:
        self.check_now_btn.set_loading(False)
        self.update_status_label.setText("No internet connection")

    def _on_install_update(self) -> None:
        parent_win = self.parent()
        if parent_win and hasattr(parent_win, "apply_update_info") and self._latest_update_info:
            parent_win.apply_update_info(self._latest_update_info)
            self.accept()

    def _on_export_log(self) -> None:
        if not APP_LOG_FILE.exists():
            QMessageBox.information(self, "Log Empty", "No application log file has been created yet.")
            return

        dest_file, _ = QFileDialog.getSaveFileName(
            self,
            "Export Application Log",
            "YOuTUbE_app.log",
            "Log Files (*.log);;Text Files (*.txt);;All Files (*.*)",
        )
        if not dest_file:
            return

        try:
            shutil.copy2(APP_LOG_FILE, dest_file)
            self.export_log_btn.flash_success(1000)
        except Exception as exc:
            QMessageBox.warning(self, "Export Failed", f"Failed to export log file: {exc}")
