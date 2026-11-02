"""Main application window using custom Header and QStackedWidget.

Fixes:
  B10: Replaces QTabWidget corner widget with 52px Header (Settings button is never clipped).
  B14: Enables DwmSetWindowAttribute immersive dark title bar on Windows 10/11.
Centers content in maximum ~1100px width with 760x520 minimum window dimensions.
"""

from pathlib import Path
import time
from typing import Optional

from PySide6.QtCore import QEvent, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
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
from app.core.download_manager import get_download_manager
from app.core.file_actions import reveal_in_folder
from app.core.logger import get_logger
from app.core.network_monitor import NetworkMonitor
from app.core.settings import load_settings, save_settings
from app.core.url_tools import clean_url, is_youtube_url
from app.ui.audio_tab import AudioTab
from app.ui.header import Header, get_asset_path
from app.ui.kit.anim import FAST, is_animations_enabled
from app.ui.history_tab import HistoryTab
from app.ui.settings_dialog import SettingsDialog
from app.ui.theme import ThemeManager, apply_dark_title_bar, current_theme, tok
from app.ui.video_tab import VideoTab
from app.version import APP_NAME, APP_VERSION


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
        self._restyle()
        ThemeManager.instance().changed.connect(self._restyle)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        self.msg_label = QLabel(self)
        layout.addWidget(self.msg_label)
        layout.addStretch(1)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedSize(160, 4)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.update_btn = QPushButton("Update now", self)
        self.update_btn.setObjectName("updateBtn")
        self.update_btn.clicked.connect(self._on_update_clicked)
        layout.addWidget(self.update_btn)

        self.later_btn = QPushButton("Later", self)
        self.later_btn.setObjectName("laterBtn")
        self.later_btn.clicked.connect(self._on_later_clicked)
        layout.addWidget(self.later_btn)

    def _restyle(self, *_) -> None:
        self.setStyleSheet(
            f"UpdateBanner {{ background-color: {tok('surface')}; border-radius: 8px; }} "
            f"QLabel {{ color: {tok('info')}; font-size: 13px; font-weight: 500; }} "
            "QPushButton { font-size: 13px; padding: 4px 8px; border: none; } "
            f"QPushButton#updateBtn {{ background: transparent; color: {tok('info')}; font-weight: 600; }} "
            f"QPushButton#laterBtn {{ background: transparent; color: {tok('text_muted')}; font-weight: 500; }} "
            "QPushButton:hover { text-decoration: underline; }"
        )

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
        self._page_fade: Optional[QPropertyAnimation] = None
        self._fade_page = None
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
        self.video_tab.recent_list.see_all_clicked.connect(self._on_see_all_history)
        self.stacked_widget.addWidget(self.video_tab)

        self.audio_tab = AudioTab(self)
        self.audio_tab.download_completed.connect(self._on_download_finished_notification)
        self.audio_tab.recent_list.see_all_clicked.connect(self._on_see_all_history)
        self.stacked_widget.addWidget(self.audio_tab)

        self.history_tab = HistoryTab(self)
        self.history_tab.redownload_requested.connect(self._on_redownload)
        self.stacked_widget.addWidget(self.history_tab)

        for tab in (self.video_tab, self.audio_tab):
            tab.info_card.change_folder_requested.connect(self._open_settings)

        # System tray icon for finish notifications
        self.tray_icon = QSystemTrayIcon(self)
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        tray_menu = QMenu(self)
        tray_menu.addAction("Show", self._show_from_tray)
        tray_menu.addSeparator()
        tray_menu.addAction("Pause all", lambda: self._set_all_paused(True))
        tray_menu.addAction("Resume all", lambda: self._set_all_paused(False))
        tray_menu.addSeparator()
        tray_menu.addAction("Quit", self.close)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip(APP_NAME)
        self.tray_icon.activated.connect(
            lambda reason: self._show_from_tray() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self._last_finished_path = ""
        self.tray_icon.messageClicked.connect(
            lambda: reveal_in_folder(self._last_finished_path) if self._last_finished_path else None)
        for kind in ("video", "audio"):
            mgr = get_download_manager(kind)
            mgr.progress.connect(lambda _job, pct, *_rest: self._update_tray_tooltip(pct))
            mgr.job_finished.connect(self._on_job_finished_for_tray)
        self.tray_icon.show()

        # Network monitor
        self.network_monitor = NetworkMonitor(parent=self)
        self.network_monitor.went_offline.connect(self._on_went_offline)
        self.network_monitor.came_online.connect(self._on_came_online)
        self.network_monitor.start()

        # Update check worker
        self._update_worker: Optional[UpdateCheckWorker] = None
        self._check_for_updates()

        ThemeManager.instance().changed.connect(self._apply_title_bar)

        self.setAcceptDrops(True)
        self._setup_shortcuts()

    # -- Links from outside: clipboard, drag & drop, keyboard ------------------------

    def _current_download_tab(self):
        """Tab that receives a link: Audio when it is open, otherwise Video."""
        return self.audio_tab if self.header._current_tab == 1 else self.video_tab

    def _setup_shortcuts(self) -> None:
        bindings = (
            ("Ctrl+1", lambda: self.header.select_tab(0)),
            ("Ctrl+2", lambda: self.header.select_tab(1)),
            ("Ctrl+3", lambda: self.header.select_tab(2)),
            ("Ctrl+F", self._focus_history_search),
            ("Ctrl+,", self._open_settings),
            ("Ctrl+V", self._paste_link),
            ("Esc", lambda: self._current_download_tab().url_input.clear()),
            ("Space", self._space_pressed),
        )
        for key, slot in bindings:
            QShortcut(QKeySequence(key), self, activated=slot)

    def _focus_history_search(self) -> None:
        self.header.select_tab(2)
        self.history_tab.search_input.setFocus()

    def _paste_link(self) -> None:
        """Ctrl+V outside a text box: put the copied text in the link box (a valid link fetches at once)."""
        if self.header._current_tab == 2:
            self.header.select_tab(0)
        self._current_download_tab().url_input.setText(QApplication.clipboard().text().strip())

    def _space_pressed(self) -> None:
        # Keep Space working on focused buttons and dropdowns; otherwise pause / resume
        focused = QApplication.focusWidget()
        if isinstance(focused, QAbstractButton):
            focused.click()
        elif isinstance(focused, QComboBox):
            focused.showPopup()
        else:
            self._current_download_tab().toggle_pause()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
            self._check_clipboard()

    def _check_clipboard(self) -> None:
        if self.header._current_tab == 2:
            return
        text = QApplication.clipboard().text()
        if text:
            self._current_download_tab().offer_clipboard_link(text)

    @staticmethod
    def _link_from_mime(mime) -> str:
        candidates = [u.toString() for u in mime.urls()] if mime.hasUrls() else []
        if mime.hasText():
            candidates.append(mime.text())
        for text in candidates:
            cleaned = clean_url(text.strip())
            if cleaned and is_youtube_url(cleaned):
                return cleaned
        return ""

    def dragEnterEvent(self, event) -> None:
        if self._link_from_mime(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        link = self._link_from_mime(event.mimeData())
        if not link:
            return
        if self.header._current_tab == 2:
            self.header.select_tab(0)
        self._current_download_tab().url_input.setText(link)
        event.acceptProposedAction()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Apply dark title bar (B14 fix)
        self._apply_title_bar()

        if not getattr(self, "_restored_started", False):
            self._restored_started = True
            self._init_network_and_restored_jobs()

    def _apply_title_bar(self, *_) -> None:
        try:
            apply_dark_title_bar(int(self.winId()), is_dark=(current_theme() != "light"))
        except Exception as exc:
            get_logger().debug(f"Title bar theming skipped: {exc}")

    def _init_network_and_restored_jobs(self) -> None:
        """Initialize online state for both lanes and start restored jobs if online."""
        is_online = self.network_monitor.is_online() if hasattr(self, "network_monitor") else True
        v_mgr = get_download_manager("video")
        a_mgr = get_download_manager("audio")
        v_mgr.set_online(is_online)
        a_mgr.set_online(is_online)
        if is_online:
            v_mgr.start_restored_jobs()
            a_mgr.start_restored_jobs()
        else:
            self.video_tab.set_online(False)
            self.audio_tab.set_online(False)

    def _on_see_all_history(self, kind: str) -> None:
        self.header.select_tab(2)
        self.history_tab.show_filter(kind)

    def _on_tab_changed(self, index: int) -> None:
        self.stacked_widget.setCurrentIndex(index)
        if hasattr(self.video_tab, "reset_messages"):
            self.video_tab.reset_messages()
        if hasattr(self.audio_tab, "reset_messages"):
            self.audio_tab.reset_messages()
        # Refresh history tab if switched to history
        if index == 2 and hasattr(self.history_tab, "refresh_items"):
            self.history_tab.refresh_items()
        # Fade only after the page is built, so it never sits blank while loading
        self._fade_in_page(self.stacked_widget.currentWidget())

    def _fade_in_page(self, page) -> None:
        """Short cross-fade for the newly shown tab; the effect is removed when done."""
        if self._page_fade is not None:
            # A fast switch: finish the previous fade so no page is left covered
            self._page_fade.stop()
            self._fade_page.setGraphicsEffect(None)
        self._page_fade = None
        if page is None or not is_animations_enabled():
            return
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        fade = QPropertyAnimation(effect, b"opacity", self)
        fade.setDuration(FAST)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.finished.connect(lambda: page.setGraphicsEffect(None))
        fade.start()
        self._page_fade, self._fade_page = fade, page

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()
        # Re-apply title bar in case theme changed
        settings = load_settings()
        is_dark = settings.get("theme", "dark").lower() != "light"
        apply_dark_title_bar(int(self.winId()), is_dark=is_dark)

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _set_all_paused(self, paused: bool) -> None:
        for kind, tab in (("video", self.video_tab), ("audio", self.audio_tab)):
            if tab._job_running() and get_download_manager(kind).is_paused != paused:
                tab.toggle_pause()

    def _update_tray_tooltip(self, percent: float) -> None:
        self.tray_icon.setToolTip(f"{APP_NAME} · Downloading {int(percent)}%")

    def _on_job_finished_for_tray(self, _job, final_path: str) -> None:
        self._last_finished_path = final_path or ""
        self.tray_icon.setToolTip(APP_NAME)

    def _on_download_finished_notification(self, title: str) -> None:
        if not load_settings().get("notify_when_done", True):
            return
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
        get_download_manager("video").set_online(False)
        get_download_manager("audio").set_online(False)

    def _on_came_online(self) -> None:
        self.header.set_online(True)
        self.video_tab.set_online(True)
        self.audio_tab.set_online(True)
        get_download_manager("video").set_online(True)
        get_download_manager("audio").set_online(True)

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
        v_mgr = get_download_manager("video")
        a_mgr = get_download_manager("audio")
        v_active = v_mgr.active_job is not None
        a_active = a_mgr.active_job is not None

        if v_active or a_active:
            settings = load_settings()
            if settings.get("confirm_exit_on_download", True):
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle(APP_NAME)
                msg_box.setText("A download is running. Quit now? It will continue the next time you open the app.")
                quit_btn = msg_box.addButton("Quit", QMessageBox.ButtonRole.AcceptRole)
                keep_btn = msg_box.addButton("Keep downloading", QMessageBox.ButtonRole.RejectRole)
                msg_box.setDefaultButton(keep_btn)
                msg_box.exec()
                if msg_box.clickedButton() != quit_btn:
                    event.ignore()
                    return

            v_worker = getattr(v_mgr, "_worker", None)
            a_worker = getattr(a_mgr, "_worker", None)

            # (1) Call shutdown() on both lanes first (non-blocking)
            v_mgr.shutdown()
            a_mgr.shutdown()

            # (2) Wait for both workers with ONE shared 2-second deadline in total
            deadline = time.monotonic() + 2.0
            for worker in (v_worker, a_worker):
                if worker and hasattr(worker, "wait"):
                    remaining_s = max(0.0, deadline - time.monotonic())
                    timeout_ms = int(remaining_s * 1000)
                    stopped = worker.wait(timeout_ms)
                    if stopped is False or (hasattr(worker, "isRunning") and worker.isRunning()):
                        get_logger().warning(f"Worker did not stop within deadline: {worker}")
        else:
            v_mgr.shutdown()
            a_mgr.shutdown()

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
        event.accept()
        super().closeEvent(event)
