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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.app_updater import UpdateCheckWorker, UpdateInfo
from app.core.file_actions import open_folder
from app.core.logger import get_logger
from app.core.paths import APP_LOG_FILE, DEFAULT_DOWNLOADS
from app.core.settings import load_settings, save_settings
from app.core.shortcut import set_start_with_windows
from app.ui.kit import AnimatedButton, AnimatedCheckBox
from app.ui.theme import ThemeManager, resolve_theme, tok
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
        self.setMinimumWidth(820)  # two columns

        self._settings = load_settings()
        self._saved_download_dir = self._settings.get("download_dir", str(DEFAULT_DOWNLOADS))
        self._update_worker: Optional[UpdateCheckWorker] = None
        self._latest_update_info: Optional[UpdateInfo] = None

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._dividers = []
        self._low_space = False
        self._setup_ui()
        self._load_values()
        ThemeManager.instance().changed.connect(self._restyle)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.setFocus()
        self._apply_dark_title_bar()

    def _apply_dark_title_bar(self, is_dark: Optional[bool] = None) -> None:
        if is_dark is None:
            is_dark = resolve_theme(self._settings.get("theme", "dark")) == "dark"
        try:
            from app.ui.main_window import apply_dark_title_bar
            apply_dark_title_bar(int(self.winId()), is_dark=is_dark)
        except Exception as exc:
            get_logger().debug(f"Title bar update skipped: {exc}")

    def _setup_ui(self) -> None:
        # Two columns keep every option visible without scrolling on 768-px-high screens
        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 24)
        outer.setSpacing(32)
        left_col, right_col = QVBoxLayout(), QVBoxLayout()
        for col in (left_col, right_col):
            col.setSpacing(16)
            outer.addLayout(col, 1)
        layout = left_col

        # -------------------------------------------------------------
        # Section 1: Download Folder
        # -------------------------------------------------------------
        folder_header = QLabel("Download folder", self)
        folder_header.setProperty("role", "section")
        layout.addWidget(folder_header)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        # Read-only path box (no focus, no cursor)
        self.folder_input = QLineEdit(self)
        self.folder_input.setReadOnly(True)
        self.folder_input.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.folder_input.setCursor(Qt.CursorShape.ArrowCursor)
        self.folder_input.setFixedHeight(36)
        folder_row.addWidget(self.folder_input, 1)

        self.browse_btn = AnimatedButton("Browse…", role="secondary", parent=self)
        self.browse_btn.setFixedWidth(85)
        self.browse_btn.setFixedHeight(36)
        self.browse_btn.clicked.connect(self._on_browse)
        folder_row.addWidget(self.browse_btn)

        # Save button appears only when folder changes
        self.save_folder_btn = AnimatedButton("Save", role="primary", parent=self)
        self.save_folder_btn.setFixedWidth(75)
        self.save_folder_btn.setFixedHeight(36)
        self.save_folder_btn.setVisible(False)
        self.save_folder_btn.clicked.connect(self._on_save_folder)
        folder_row.addWidget(self.save_folder_btn)

        layout.addLayout(folder_row)

        # Folder helper row (Free space + Open download folder link)
        helper_row = QHBoxLayout()
        helper_row.setContentsMargins(2, 0, 2, 0)

        self.free_space_label = QLabel(self)
        helper_row.addWidget(self.free_space_label)

        helper_row.addStretch(1)

        self.open_folder_link = QPushButton("Open download folder", self)
        self.open_folder_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_link.clicked.connect(self._on_open_download_folder)
        helper_row.addWidget(self.open_folder_link)

        layout.addLayout(helper_row)

        layout.addWidget(self._create_divider(self))

        # -------------------------------------------------------------
        # Section 2: Appearance (instant switch and persist)
        # -------------------------------------------------------------
        theme_header = QLabel("Appearance", self)
        theme_header.setProperty("role", "section")
        layout.addWidget(theme_header)

        self.theme_combo = QComboBox(self)
        self.theme_combo.setFixedHeight(36)
        self.theme_combo.addItem("Same as Windows", "system")
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        layout.addWidget(self.theme_combo)

        self.reduce_motion_check = AnimatedCheckBox("Reduce motion", parent=self)
        self.reduce_motion_check.toggled.connect(lambda on: self._save_option("animations_enabled", not on))
        layout.addWidget(self.reduce_motion_check)

        layout.addWidget(self._create_divider(self))

        # -------------------------------------------------------------
        # Section: Downloads (defaults for new downloads)
        # -------------------------------------------------------------
        downloads_header = QLabel("Downloads", self)
        downloads_header.setProperty("role", "section")
        layout.addWidget(downloads_header)

        from app.ui.audio_tab import AudioTab  # same format list as the Audio tab
        self.default_quality_combo = QComboBox(self)
        self.default_quality_combo.setFixedHeight(36)
        for label, key in (("Best available", "best"), ("2160p", "2160p"), ("1440p", "1440p"), ("1080p", "1080p"),
                           ("720p", "720p"), ("480p", "480p"), ("360p", "360p")):
            self.default_quality_combo.addItem(label, key)
        self.default_audio_combo = QComboBox(self)
        self.default_audio_combo.setFixedHeight(36)
        for label, key in AudioTab.AUDIO_FORMATS:
            self.default_audio_combo.addItem(label, key)
        for caption, combo in (("Video quality", self.default_quality_combo), ("Audio format", self.default_audio_combo)):
            row = QHBoxLayout()
            row_label = QLabel(caption, self)
            row_label.setProperty("role", "muted")
            row_label.setFixedWidth(96)
            row.addWidget(row_label)
            row.addWidget(combo, 1)
            layout.addLayout(row)
        self.default_quality_combo.currentIndexChanged.connect(
            lambda _: self._save_option("default_video_quality", self.default_quality_combo.currentData()))
        self.default_audio_combo.currentIndexChanged.connect(
            lambda _: self._save_option("default_audio_format", self.default_audio_combo.currentData()))

        self.open_folder_check = AnimatedCheckBox("Open the folder when a download finishes", parent=self)
        self.open_folder_check.toggled.connect(lambda on: self._save_option("open_folder_when_done", on))
        layout.addWidget(self.open_folder_check)
        layout.addStretch(1)

        # -------------------------------------------------------------
        # Right column. Section: Behaviour
        # -------------------------------------------------------------
        layout = right_col
        behaviour_header = QLabel("Behaviour", self)
        behaviour_header.setProperty("role", "section")
        layout.addWidget(behaviour_header)

        self.start_windows_check = AnimatedCheckBox("Start with Windows", parent=self)
        self.start_windows_check.toggled.connect(self._on_start_windows_toggled)
        layout.addWidget(self.start_windows_check)

        self.notify_check = AnimatedCheckBox("Notify me when a download finishes", parent=self)
        self.notify_check.toggled.connect(lambda on: self._save_option("notify_when_done", on))
        layout.addWidget(self.notify_check)

        self.auto_fetch_check = AnimatedCheckBox("Fetch pasted links automatically", parent=self)
        self.auto_fetch_check.toggled.connect(lambda on: self._save_option("auto_fetch_links", on))
        layout.addWidget(self.auto_fetch_check)

        layout.addWidget(self._create_divider(self))

        # -------------------------------------------------------------
        # Section 3: Updates
        # -------------------------------------------------------------
        update_header = QLabel("Updates", self)
        update_header.setProperty("role", "section")
        layout.addWidget(update_header)

        self.auto_update_check = AnimatedCheckBox("Check for updates automatically", parent=self)
        self.auto_update_check.toggled.connect(self._on_auto_update_toggled)
        layout.addWidget(self.auto_update_check)

        update_action_row = QHBoxLayout()
        update_action_row.setSpacing(10)

        self.check_now_btn = AnimatedButton("Check now", role="secondary", parent=self)
        self.check_now_btn.setFixedHeight(36)
        self.check_now_btn.setFixedWidth(100)
        self.check_now_btn.clicked.connect(self._on_check_updates_now)
        update_action_row.addWidget(self.check_now_btn)

        self.install_update_btn = AnimatedButton("Install update", role="primary", parent=self)
        self.install_update_btn.setFixedHeight(36)
        self.install_update_btn.setVisible(False)
        self.install_update_btn.clicked.connect(self._on_install_update)
        update_action_row.addWidget(self.install_update_btn)

        self.update_status_label = QLabel(self)
        self.update_status_label.setProperty("role", "meta")
        update_action_row.addWidget(self.update_status_label, 1)

        layout.addLayout(update_action_row)

        layout.addWidget(self._create_divider(self))

        # -------------------------------------------------------------
        # Section 4: About & Support
        # -------------------------------------------------------------
        about_header = QLabel(f"About {APP_NAME}", self)
        about_header.setProperty("role", "section")
        layout.addWidget(about_header)

        version_label = QLabel(f"Version {APP_VERSION}", self)
        version_label.setProperty("role", "meta")
        layout.addWidget(version_label)

        self.credits_label = QLabel(self)
        self.credits_label.setOpenExternalLinks(True)
        layout.addWidget(self.credits_label)

        about_actions_row = QHBoxLayout()
        about_actions_row.setSpacing(10)

        self.export_log_btn = AnimatedButton("Export log", role="secondary", parent=self)
        self.export_log_btn.setFixedHeight(34)
        self.export_log_btn.setToolTip("Export application log file for diagnostics")
        self.export_log_btn.clicked.connect(self._on_export_log)
        about_actions_row.addWidget(self.export_log_btn)

        self.open_log_btn = AnimatedButton("Open log folder", role="secondary", parent=self)
        self.open_log_btn.setFixedHeight(34)
        self.open_log_btn.clicked.connect(lambda: open_folder(APP_LOG_FILE.parent))
        about_actions_row.addWidget(self.open_log_btn)

        about_actions_row.addStretch(1)
        layout.addLayout(about_actions_row)
        layout.addStretch(1)

        self._restyle()
        self.adjustSize()
        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            max_h = screen.availableGeometry().height() - 40
            if self.height() > max_h:
                self.resize(self.width(), max_h)

    def _style_free_space(self) -> None:
        color = tok("error" if self._low_space else "text_muted")
        self.free_space_label.setStyleSheet(f"font-size: 12px; color: {color};")

    def _restyle(self, *_) -> None:
        """Apply token colors to the widgets styled in code (runs on every theme change)."""
        self.folder_input.setStyleSheet(
            f"QLineEdit {{ background-color: {tok('surface')}; border: 1px solid {tok('border')}; "
            f"border-radius: 8px; padding: 0 10px; color: {tok('text')}; font-family: 'Segoe UI'; font-size: 12px; }}"
        )
        self.open_folder_link.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {tok('info')}; font-size: 12px; padding: 0; }} "
            "QPushButton:hover { text-decoration: underline; }"
        )
        self._style_free_space()
        for divider in self._dividers:
            divider.setStyleSheet(f"background-color: {tok('border')}; border: none;")
        link = f'style="color: {tok("info")};"'
        self.credits_label.setText(
            "Built with open-source tools:<br>"
            f'• <a {link} href="https://github.com/yt-dlp/yt-dlp">yt-dlp</a><br>'
            f'• <a {link} href="https://github.com/BtbN/FFmpeg-Builds">ffmpeg &amp; ffprobe (GPL build)</a>'
            f' — <a {link} href="https://github.com/FFmpeg/FFmpeg">source</a><br>'
            f'• <a {link} href="https://deno.com">deno</a><br>'
            f'• <a {link} href="https://github.com/arsenetar/send2trash">send2trash</a>'
        )
        self.credits_label.setStyleSheet(f"font-size: 12px; color: {tok('text_muted')}; line-height: 1.4;")

    def _create_divider(self, parent: QWidget) -> QFrame:
        divider = QFrame(parent)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        self._dividers.append(divider)
        return divider

    def _load_values(self) -> None:
        download_dir = self._settings.get("download_dir", str(DEFAULT_DOWNLOADS))
        self.folder_input.setText(download_dir)
        self._saved_download_dir = download_dir
        self._update_free_space_label(Path(download_dir))

        theme = self._settings.get("theme", "dark").lower()
        idx_t = self.theme_combo.findData(theme)
        if idx_t >= 0:
            blocked = self.theme_combo.blockSignals(True)  # loading must not re-apply the theme
            self.theme_combo.setCurrentIndex(idx_t)
            self.theme_combo.blockSignals(blocked)

        self.auto_update_check.setChecked(self._settings.get("auto_update", True))

        # New options: set quietly so loading does not write the settings file
        for widget, value in (
            (self.reduce_motion_check, not self._settings.get("animations_enabled", True)),
            (self.open_folder_check, self._settings.get("open_folder_when_done", False)),
            (self.start_windows_check, self._settings.get("start_with_windows", False)),
            (self.notify_check, self._settings.get("notify_when_done", True)),
            (self.auto_fetch_check, self._settings.get("auto_fetch_links", True)),
        ):
            blocked = widget.blockSignals(True)
            widget.setChecked(bool(value))
            widget.blockSignals(blocked)
        for combo, key in ((self.default_quality_combo, "default_video_quality"),
                           (self.default_audio_combo, "default_audio_format")):
            idx = combo.findData(self._settings.get(key, "best"))
            blocked = combo.blockSignals(True)
            combo.setCurrentIndex(max(0, idx))
            combo.blockSignals(blocked)

    def _save_option(self, key: str, value) -> None:
        self._settings[key] = value
        save_settings(self._settings)

    def _on_start_windows_toggled(self, enabled: bool) -> None:
        set_start_with_windows(enabled)
        self._save_option("start_with_windows", enabled)

    def _update_free_space_label(self, path: Path) -> None:
        try:
            target = path if path.is_dir() else path.parent
            if target.is_dir():
                usage = shutil.disk_usage(target)
                free_str = format_size(usage.free)
                if usage.free < 1024 * 1024 * 1024:
                    self.free_space_label.setText(f"Low disk space: {free_str} available")
                    self._low_space = True
                else:
                    self.free_space_label.setText(f"Free disk space: {free_str}")
                    self._low_space = False
                self._style_free_space()
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
            ok, msg = open_folder(target)
            if not ok and msg:
                QMessageBox.warning(self, "Open Folder Failed", msg)
        else:
            QMessageBox.warning(self, "Folder Missing", f"The download folder does not exist:\n{target}")

    def _on_theme_changed(self, index: int) -> None:
        chosen_theme = self.theme_combo.currentData()
        if chosen_theme in ("system", "dark", "light"):
            self._settings["theme"] = chosen_theme
            save_settings(self._settings)

            applied = resolve_theme(chosen_theme)
            ThemeManager.instance().apply(applied)

            # Apply dark title bar to self and parent window
            self._apply_dark_title_bar(is_dark=(applied == "dark"))
            parent_win = self.parent()
            if parent_win and hasattr(parent_win, "winId"):
                try:
                    from app.ui.main_window import apply_dark_title_bar
                    apply_dark_title_bar(int(parent_win.winId()), is_dark=(applied == "dark"))
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
