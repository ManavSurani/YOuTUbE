"""VideoTab implementing state-machine control, shared DownloadManager, and clean flow.

Fixes:
  B8: Delegated to central DownloadManager (no simultaneous dual-downloads).
  B9: Quality dropdown disabled when idle; empty Download click shows friendly InlineMessage.
  B15: Uses real output directory name on completion.
"""

from enum import Enum, auto
from pathlib import Path
import shutil
from typing import Optional
import urllib.request

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMenu,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from app.ui.theme import DARK_TOKENS, LIGHT_TOKENS, ThemeManager, tok

from app.core.download_manager import DownloadManager, get_download_manager
from app.core.history_db import find_duplicate
from app.core.info_fetcher import InfoFetchWorker, VideoInfo
from app.core.jobs import DownloadJob
from app.core.logger import get_logger
from app.core.paths import DEFAULT_DOWNLOADS
from app.core.file_actions import reveal_in_folder
from app.core.settings import load_settings
from app.core.thumbnails import save_thumbnail
from app.core.url_tools import clean_url, extract_video_id, is_youtube_url
from app.ui.kit.anim import FAST, shake
from app.ui.kit import (
    AnimatedButton,
    InlineMessage,
    ProgressCard,
    ThumbLabel,
)
from app.ui.queue_widget import QueueWidget
from app.ui.recent_list import RecentList

_FETCH_CACHE: dict[str, VideoInfo] = {}
QUALITY_LABEL_ROLE = Qt.ItemDataRole.UserRole + 1  # clean quality label without the size suffix


def get_current_theme_tokens() -> dict[str, str]:
    app = QApplication.instance()
    if app:
        qss = app.styleSheet()
        if f"background-color: {DARK_TOKENS['bg']}" in qss:
            return DARK_TOKENS
        if f"background-color: {LIGHT_TOKENS['bg']}" in qss:
            return LIGHT_TOKENS
        if DARK_TOKENS["surface"] in qss:
            return DARK_TOKENS
        if LIGHT_TOKENS["surface"] in qss:
            return LIGHT_TOKENS
    settings = load_settings()
    theme = settings.get("theme", "dark").lower()
    return LIGHT_TOKENS if theme == "light" else DARK_TOKENS


def build_combo_popup_qss(tokens: dict[str, str]) -> str:
    return (
        f"QListView {{\n"
        f"    background-color: {tokens['surface']};\n"
        f"    border: 1px solid {tokens['border']};\n"
        f"    border-radius: 8px;\n"
        f"    padding: 4px;\n"
        f"    outline: none;\n"
        f"    selection-background-color: {tokens['surface_hover']};\n"
        f"    selection-color: {tokens['text']};\n"
        f"}}\n"
        f"QListView::item {{\n"
        f"    min-height: 32px;\n"
        f"    padding: 6px 12px;\n"
        f"    border-radius: 4px;\n"
        f"    color: {tokens['text']};\n"
        f"    background-color: transparent;\n"
        f"}}\n"
        f"QListView::item:hover {{\n"
        f"    background-color: {tokens['surface_hover']};\n"
        f"    color: {tokens['text']};\n"
        f"}}\n"
        f"QListView::item:selected {{\n"
        f"    background-color: {tokens['surface_hover']};\n"
        f"    color: {tokens['text']};\n"
        f"}}\n"
    )


def build_menu_popup_qss(tokens: dict[str, str]) -> str:
    return (
        f"QMenu {{\n"
        f"    background-color: {tokens['surface']};\n"
        f"    border: 1px solid {tokens['border']};\n"
        f"    border-radius: 8px;\n"
        f"    padding: 4px;\n"
        f"}}\n"
        f"QMenu::item {{\n"
        f"    min-height: 32px;\n"
        f"    padding: 6px 12px;\n"
        f"    border-radius: 4px;\n"
        f"    color: {tokens['text']};\n"
        f"    background-color: transparent;\n"
        f"}}\n"
        f"QMenu::item:hover {{\n"
        f"    background-color: {tokens['surface_hover']};\n"
        f"    color: {tokens['text']};\n"
        f"}}\n"
        f"QMenu::item:selected {{\n"
        f"    background-color: {tokens['surface_hover']};\n"
        f"    color: {tokens['text']};\n"
        f"}}\n"
        f"QMenu::item:disabled {{\n"
        f"    color: {tokens['text_muted']};\n"
        f"    background-color: transparent;\n"
        f"}}\n"
        f"QMenu::separator {{\n"
        f"    height: 1px;\n"
        f"    background-color: {tokens['border']};\n"
        f"    margin: 4px 6px;\n"
        f"}}\n"
    )


class _PopupContainerFilter(QObject):
    def __init__(self, combo: "AnimatedComboBox") -> None:
        super().__init__(combo)
        self._combo = combo

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Hide:
            if self._combo is not None:
                self._combo._on_container_hide()
        return super().eventFilter(obj, event)


class AnimatedComboBox(QComboBox):
    """QComboBox with smooth windowOpacity fade, styled QListView popup, and restored UI_AnimateCombo."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.view_widget = QListView(self)
        self.setView(self.view_widget)
        self.setMaxVisibleItems(8)

        self._container = self.view_widget.window()
        self._container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._container.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )

        self._filter = _PopupContainerFilter(self)
        self._container.installEventFilter(self._filter)

        self._anim = QPropertyAnimation(self._container, b"windowOpacity", self)
        self._anim.setDuration(FAST)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._update_popup_style()

    def _update_popup_style(self) -> None:
        tokens = get_current_theme_tokens()
        self.view_widget.setStyleSheet(build_combo_popup_qss(tokens))

    def _on_container_hide(self) -> None:
        self._anim.stop()
        if self._container is not None:
            self._container.setWindowOpacity(1.0)

    def showPopup(self) -> None:
        self._update_popup_style()
        self._anim.stop()
        self._container.setWindowOpacity(0.0)

        if self.width() > self.view_widget.minimumWidth():
            self.view_widget.setMinimumWidth(self.width())

        app = QApplication.instance()
        was = app.isEffectEnabled(Qt.UIEffect.UI_AnimateCombo) if app else False
        if app and was:
            app.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, False)

        try:
            super().showPopup()
        finally:
            if app and was:
                app.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, True)

        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def hidePopup(self) -> None:
        self._anim.stop()
        if self._container is not None:
            self._container.setWindowOpacity(1.0)
        super().hidePopup()


class AnimatedLineEdit(QLineEdit):
    """QLineEdit with 150 ms OutCubic windowOpacity fade on right-click context menu."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._anim = QPropertyAnimation(self)
        self._anim.setPropertyName(b"windowOpacity")
        self._anim.setDuration(FAST)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._current_menu: Optional[QMenu] = None

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = self.createStandardContextMenu()
        if not menu:
            return

        if self._current_menu is not None:
            try:
                self._current_menu.close()
            except Exception:
                pass

        menu.setWindowFlags(
            menu.windowFlags()
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        tokens = get_current_theme_tokens()
        menu.setStyleSheet(build_menu_popup_qss(tokens))

        self._current_menu = menu
        self._anim.stop()
        self._anim.setTargetObject(menu)
        menu.setWindowOpacity(0.0)

        def _on_hide() -> None:
            if self._anim.targetObject() == menu:
                self._anim.stop()
            try:
                menu.setWindowOpacity(1.0)
            except Exception:
                pass
            menu.deleteLater()
            if self._current_menu is menu:
                self._current_menu = None

        menu.aboutToHide.connect(_on_hide)

        pos = event.globalPos()
        if pos.x() < 0 and pos.y() < 0:
            pos = self.mapToGlobal(self.rect().center())

        app = QApplication.instance()
        was_fade = app.isEffectEnabled(Qt.UIEffect.UI_FadeMenu) if app else False
        was_anim = app.isEffectEnabled(Qt.UIEffect.UI_AnimateMenu) if app else False
        if app and was_fade:
            app.setEffectEnabled(Qt.UIEffect.UI_FadeMenu, False)
        if app and was_anim:
            app.setEffectEnabled(Qt.UIEffect.UI_AnimateMenu, False)

        try:
            menu.popup(pos)
        except Exception:
            menu.deleteLater()
            if self._current_menu is menu:
                self._current_menu = None
            raise
        finally:
            if app and was_fade:
                app.setEffectEnabled(Qt.UIEffect.UI_FadeMenu, True)
            if app and was_anim:
                app.setEffectEnabled(Qt.UIEffect.UI_AnimateMenu, True)

        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Menu or (
            event.key() == Qt.Key.Key_F10
            and bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        ):
            c_ev = QContextMenuEvent(
                QContextMenuEvent.Reason.Keyboard,
                self.rect().center(),
                self.mapToGlobal(self.rect().center()),
            )
            self.contextMenuEvent(c_ev)
            event.accept()
            return
        super().keyPressEvent(event)


class TabState(Enum):
    IDLE = auto()
    FETCHING = auto()
    READY = auto()
    DOWNLOADING = auto()
    DONE = auto()
    OFFLINE = auto()


class ThumbnailLoader(QThread):
    """Background loader for video thumbnail fetching raw image bytes."""

    loaded = Signal(bytes)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read(5_000_001)
                if len(data) > 5_000_000:
                    get_logger().warning('Thumbnail exceeded 5 MB cap; discarded.')
                    return
            self.loaded.emit(data)
        except Exception as exc:
            get_logger().debug(f"Thumbnail load failed: {exc}")


class MediaInfoCard(QWidget):
    """Fetched video details: 160x90 thumbnail, 2-line title, channel • duration, and save folder."""

    change_folder_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.thumb_bytes: Optional[bytes] = None
        self._thumb_loader: Optional[ThumbnailLoader] = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setVisible(False)
        self._setup_ui()
        self._restyle()
        ThemeManager.instance().changed.connect(self._restyle)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        self.thumb_label = ThumbLabel(size=(160, 90), radius=8, parent=self)
        layout.addWidget(self.thumb_label, 0, Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel(self)
        self.title_label.setTextFormat(Qt.TextFormat.PlainText)
        self.title_label.setWordWrap(True)
        self.title_label.setProperty("role", "section")
        text_layout.addWidget(self.title_label)

        self.meta_label = QLabel(self)
        self.meta_label.setTextFormat(Qt.TextFormat.PlainText)
        self.meta_label.setProperty("role", "meta")
        text_layout.addWidget(self.meta_label)

        self.dest_label = QLabel(self)
        self.dest_label.setTextFormat(Qt.TextFormat.RichText)
        self.dest_label.setProperty("role", "meta")
        self.dest_label.linkActivated.connect(lambda _: self.change_folder_requested.emit())
        text_layout.addWidget(self.dest_label)

        layout.addLayout(text_layout, 1)

    def _restyle(self, *_) -> None:
        self.setStyleSheet(f"MediaInfoCard {{ background-color: {tok('surface')}; border-radius: 8px; }}")
        self._update_dest()

    def _update_dest(self) -> None:
        folder = Path(load_settings().get("download_dir", str(DEFAULT_DOWNLOADS))).name or "Downloads"
        safe = folder.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.dest_label.setText(
            f'Saves to {safe} · <a href="change" style="color: {tok("info")}; text-decoration: none;">Change</a>'
        )

    def set_info(self, info: VideoInfo) -> None:
        self.title_label.setText(info.title)
        self.title_label.setToolTip(info.title)
        self.title_label.ensurePolished()
        self.title_label.setMaximumHeight(self.title_label.fontMetrics().lineSpacing() * 2 + 2)  # 2 lines max
        meta_parts = []
        if info.channel:
            meta_parts.append(info.channel)
        if info.duration_str:
            meta_parts.append(info.duration_str)
        self.meta_label.setText(" • ".join(meta_parts))
        self._update_dest()

        self.thumb_bytes = None
        self.thumb_label.update_thumbnail("")  # placeholder until the image arrives
        if info.thumbnail_url:
            self._thumb_loader = ThumbnailLoader(info.thumbnail_url, self)
            self._thumb_loader.loaded.connect(self._on_thumbnail_loaded)
            self._thumb_loader.start()

        self.setVisible(True)

    def _on_thumbnail_loaded(self, data: bytes) -> None:
        if self.thumb_label.set_image_bytes(data):
            self.thumb_bytes = data

    def clear(self) -> None:
        self.thumb_bytes = None
        self.thumb_label.update_thumbnail("")
        self.title_label.clear()
        self.meta_label.clear()
        self.setVisible(False)



class VideoTab(QWidget):
    """Video tab providing state-machine download controls, shared queue, and recent list."""

    download_completed = Signal(str)  # Emits downloaded video title

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._state = TabState.IDLE
        self._prev_state = TabState.IDLE
        self._current_info: Optional[VideoInfo] = None
        self._fetch_worker: Optional[InfoFetchWorker] = None
        self._active_workers: set[InfoFetchWorker] = set()
        self._fetch_seq = 0
        self._last_fetched_url = ""
        self._preselected_quality: Optional[str] = None

        # Test compatibility aliases
        self._is_downloading = False
        self._paused_for_offline = False
        self._input_error = False
        self._shake_anim = None

        self._setup_ui()
        self._wire_manager()
        self.set_state(TabState.IDLE)
        ThemeManager.instance().changed.connect(self._style_input_error)

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        if scroll.viewport():
            scroll.viewport().setStyleSheet("background: transparent;")
        self.scroll = scroll

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 16)

        # Keep the content width constant: reserve the scrollbar's width while it is hidden
        bar = scroll.verticalScrollBar()
        def _reserve_scrollbar(_lo: int, hi: int) -> None:
            layout.setContentsMargins(0, 8, 0 if hi > 0 else bar.sizeHint().width(), 16)
        bar.rangeChanged.connect(_reserve_scrollbar)
        _reserve_scrollbar(0, 0)
        layout.setSpacing(12)

        # 1. URL Input & Fetch Button
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.url_input = AnimatedLineEdit(container)
        self.url_input.setPlaceholderText("Paste a YouTube link")
        self.url_input.setFixedHeight(36)
        self.url_input.textChanged.connect(self._on_url_text_changed)
        self.url_input.returnPressed.connect(self._on_return_pressed)
        input_row.addWidget(self.url_input, 1)

        self.fetch_btn = AnimatedButton("Fetch", role="secondary", parent=container)
        self.fetch_btn.setFixedWidth(80)
        self.fetch_btn.clicked.connect(self.fetch_url)
        input_row.addWidget(self.fetch_btn)
        layout.addLayout(input_row)

        # Offer a link the user copied before switching to the app (one click to fetch)
        self.clip_chip = AnimatedButton("", role="ghost", parent=container)
        self.clip_chip.setVisible(False)
        self.clip_chip.clicked.connect(self._use_clipboard_link)
        layout.addWidget(self.clip_chip, 0, Qt.AlignmentFlag.AlignLeft)
        self._offered_link = ""

        # 2. Inline Message (4s auto-hide)
        self.inline_msg = InlineMessage(container)
        layout.addWidget(self.inline_msg)

        self.offline_note = QLabel("You're offline. Downloads will resume automatically.", container)
        self.offline_note.setProperty("role", "meta")
        self.offline_note.setVisible(False)
        layout.addWidget(self.offline_note)

        # 3. Fetched Media Info Card
        self.info_card = MediaInfoCard(container)
        layout.addWidget(self.info_card)

        # 4. Action Row (Quality Combo, Download, Add to Queue, Cancel)
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.quality_combo = AnimatedComboBox(container)
        self.quality_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.quality_combo.setFixedHeight(36)
        self.quality_combo.setMinimumWidth(160)
        actions_row.addWidget(self.quality_combo)

        self.download_btn = AnimatedButton("Download", role="primary", parent=container)
        self.download_btn.setFixedWidth(110)
        self.download_btn.clicked.connect(self.start_download)
        actions_row.addWidget(self.download_btn)

        self.queue_btn = AnimatedButton("Add to queue", role="secondary", parent=container)
        self.queue_btn.setFixedWidth(110)
        self.queue_btn.clicked.connect(self.add_to_queue)
        actions_row.addWidget(self.queue_btn)

        self.cancel_btn = AnimatedButton("Cancel", role="secondary", parent=container)
        self.cancel_btn.setFixedWidth(90)
        self.cancel_btn.clicked.connect(self.cancel_download)
        actions_row.addWidget(self.cancel_btn)

        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        # 5. Active Progress Card
        self.progress_card = ProgressCard(container)
        self.progress_card.pause_toggled.connect(self.toggle_pause)
        layout.addWidget(self.progress_card)

        # Backward compatibility aliases for existing tests
        self.stage_label = self.progress_card.stage_label
        self.progress_bar = self.progress_card.progress_bar
        self.percent_label = self.progress_card.percent_label
        self.stats_label = self.progress_card.stats_label

        # 6. Queue Widget (Dedicated to Video)
        self.queue_widget = QueueWidget(kind="video", parent=container)
        layout.addWidget(self.queue_widget)

        # 7. Recently Downloaded List
        self.recent_list = RecentList(kind="video", parent=container)
        layout.addWidget(self.recent_list)

        layout.addStretch(1)
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _wire_manager(self) -> None:
        manager = get_download_manager("video")
        manager.job_started.connect(self._on_manager_job_started)
        manager.progress.connect(self._on_manager_progress)
        manager.stage.connect(self._on_manager_stage)
        manager.job_finished.connect(self._on_manager_finished)
        manager.job_failed.connect(self._on_manager_failed)
        manager.job_cancelled.connect(self._on_manager_cancelled)

    def offer_clipboard_link(self, text: str) -> None:
        """Show 'Use copied link' once for a new YouTube link that is not already in the box."""
        cleaned = clean_url(text.strip()) if text else ""
        if not cleaned or not is_youtube_url(cleaned) or cleaned == self._offered_link:
            return
        if cleaned == clean_url(self.url_input.text().strip()):
            return
        self._offered_link = cleaned
        self.clip_chip.setText(f"Use copied link · {cleaned.split('://', 1)[-1][:48]}")
        self.clip_chip.setVisible(True)

    def _use_clipboard_link(self) -> None:
        self.clip_chip.setVisible(False)
        self.url_input.setText(self._offered_link)

    def _on_return_pressed(self) -> None:
        """Enter fetches a new link, or downloads when the shown video is ready."""
        cleaned = clean_url(self.url_input.text().strip())
        ready = self._current_info is not None and cleaned and cleaned == self._last_fetched_url
        if ready and self.download_btn.isVisibleTo(self) and self.download_btn.isEnabled():
            self.start_download()
        else:
            self.fetch_url()

    def toggle_pause(self) -> None:
        """Pause or resume this lane's active download (button on the progress card or Space)."""
        if not self._job_running():
            return
        manager = get_download_manager("video")
        if manager.is_paused:
            manager.resume_active()
            self.progress_card.set_paused(False)
            self.progress_card.set_stage("Resuming…")
        elif manager.pause_active():
            self.progress_card.set_paused(True)
            self.progress_card.set_stage("Paused")

    def _job_running(self) -> bool:
        job = get_download_manager("video").active_job
        return job is not None and getattr(job, "kind", "") == "video"

    def _has_waiting_job(self) -> bool:
        return bool(get_download_manager("video").waiting_jobs)

    def _apply_state_visibility(self, state: TabState) -> None:
        """Apply visibility and enablement according to the screen contract."""
        running = self._job_running()

        if state == TabState.IDLE:
            self.url_input.setEnabled(True)
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.set_loading(False)
            self.info_card.setVisible(False)
            self.quality_combo.setVisible(False)
            self.quality_combo.setEnabled(False)
            if running:
                self.download_btn.setVisible(False)
                self.download_btn.setEnabled(False)
                self.queue_btn.setVisible(True)
                self.queue_btn.setEnabled(True)
                self.cancel_btn.setVisible(True)
                self.cancel_btn.setEnabled(True)
                self.progress_card.setVisible(True)
            else:
                self.download_btn.setVisible(False)
                self.download_btn.setEnabled(False)
                self.queue_btn.setVisible(False)
                self.queue_btn.setEnabled(False)
                self.cancel_btn.setVisible(False)
                self.cancel_btn.setEnabled(False)
                self.progress_card.setVisible(False)

        elif state == TabState.FETCHING:
            self.url_input.setEnabled(False)
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.set_loading(True)
            self.info_card.setVisible(False)
            self.quality_combo.setVisible(False)
            self.quality_combo.setEnabled(False)
            if running:
                self.download_btn.setVisible(False)
                self.download_btn.setEnabled(False)
                self.queue_btn.setVisible(True)
                self.queue_btn.setEnabled(False)
                self.cancel_btn.setVisible(True)
                self.cancel_btn.setEnabled(True)
                self.progress_card.setVisible(True)
            else:
                self.download_btn.setVisible(False)
                self.download_btn.setEnabled(False)
                self.queue_btn.setVisible(False)
                self.queue_btn.setEnabled(False)
                self.cancel_btn.setVisible(False)
                self.cancel_btn.setEnabled(False)
                self.progress_card.setVisible(False)

        elif state == TabState.READY:
            self.url_input.setEnabled(True)
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.set_loading(False)
            self.info_card.setVisible(True)
            self.quality_combo.setVisible(True)
            self.quality_combo.setEnabled(True)
            if running:
                self.download_btn.setVisible(False)
                self.download_btn.setEnabled(False)
                self.queue_btn.setVisible(True)
                self.queue_btn.setEnabled(True)
                self.cancel_btn.setVisible(True)
                self.cancel_btn.setEnabled(True)
                self.progress_card.setVisible(True)
            else:
                self.download_btn.setVisible(True)
                self.download_btn.setEnabled(True)
                self.queue_btn.setVisible(False)
                self.queue_btn.setEnabled(True)
                self.cancel_btn.setVisible(False)
                self.cancel_btn.setEnabled(False)
                self.progress_card.setVisible(False)

        elif state == TabState.DOWNLOADING:
            self.url_input.setEnabled(True)
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.set_loading(False)
            self.progress_card.setVisible(True)
            self.cancel_btn.setVisible(True)
            self.cancel_btn.setEnabled(True)
            self.download_btn.setVisible(False)
            self.download_btn.setEnabled(False)

            has_new_link = self._current_info is not None
            self.info_card.setVisible(has_new_link)
            self.quality_combo.setVisible(has_new_link)
            self.quality_combo.setEnabled(has_new_link)
            has_bad_link = bool(self.url_input.text().strip()) and not has_new_link
            self.queue_btn.setVisible(True)
            self.queue_btn.setEnabled(False if has_bad_link else (True if running else has_new_link))

        elif state == TabState.OFFLINE:
            self.url_input.setEnabled(False)
            self.fetch_btn.set_loading(False)
            self.fetch_btn.setEnabled(False)
            self.quality_combo.setEnabled(False)
            self.download_btn.setEnabled(False)
            if running or self._prev_state == TabState.DOWNLOADING:
                self.progress_card.set_stage("Waiting for internet…")
                self.progress_card.setVisible(True)
                self.cancel_btn.setVisible(True)
                self.cancel_btn.setEnabled(True)
                self.queue_btn.setVisible(True)
                self.queue_btn.setEnabled(False)
                self.download_btn.setVisible(False)
            else:
                self.cancel_btn.setEnabled(False)
                self.queue_btn.setEnabled(False)

    def set_state(self, state: TabState) -> None:
        """Drive widget visibility and enablement based on TabState."""
        self._prev_state = self._state
        self._state = state
        self._is_downloading = (state == TabState.DOWNLOADING)
        self._apply_state_visibility(state)

    def set_online(self, online: bool) -> None:
        """Handle network status change."""
        self.offline_note.setVisible(not online)
        if not online:
            self._paused_for_offline = (self._state == TabState.DOWNLOADING)
            self.set_state(TabState.OFFLINE)
        else:
            self._paused_for_offline = False
            # Restore state before offline
            target_state = self._prev_state if self._prev_state != TabState.OFFLINE else (
                TabState.READY if self._current_info else TabState.IDLE
            )
            self.set_state(target_state)

    def _show_input_error(self, message: str) -> None:
        """Validation error: red input border and a message that stays until the text changes."""
        self._input_error = True
        self.inline_msg.show_error(message, auto_hide_ms=0)
        self._style_input_error()
        self._shake_anim = shake(self.url_input)

    def _clear_input_error(self) -> None:
        if self._input_error:
            self._input_error = False
            self.inline_msg.clear()
            self._style_input_error()

    def _style_input_error(self, *_) -> None:
        self.url_input.setStyleSheet(f"QLineEdit {{ border: 1px solid {tok('error')}; }}" if self._input_error else "")

    def reset_messages(self) -> None:
        """Clear any inline error or info message."""
        self._clear_input_error()
        self.inline_msg.clear()

    def _clear_inputs(self) -> None:
        """Clear URL input and info card without firing textChanged state resets."""
        self._fetch_seq += 1
        self.fetch_btn.set_loading(False)
        if self._fetch_worker is not None:
            try:
                self._fetch_worker.fetched.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                self._fetch_worker.failed.disconnect()
            except (RuntimeError, TypeError):
                pass

        blocked = self.url_input.blockSignals(True)
        try:
            self.url_input.clear()
            self._last_fetched_url = ""
        finally:
            self.url_input.blockSignals(blocked)

        self.info_card.clear()
        self._current_info = None
        if self._state == TabState.DOWNLOADING or self._job_running():
            self._apply_state_visibility(self._state)

    def _on_url_text_changed(self, text: str) -> None:
        self._clear_input_error()
        if text.strip():
            self.clip_chip.setVisible(False)
        clean = text.strip()
        auto_fetch = load_settings().get("auto_fetch_links", True)
        if clean and is_youtube_url(clean) and clean != self._last_fetched_url and auto_fetch:
            self.fetch_url()
        elif not clean:
            self._fetch_seq += 1
            self.fetch_btn.set_loading(False)
            self.info_card.clear()
            self._current_info = None
            if self._job_running() or self._state == TabState.DOWNLOADING:
                self._apply_state_visibility(self._state)
            else:
                self.set_state(TabState.IDLE)

    def fetch_url(self) -> None:
        """Fetch video metadata from YouTube via InfoFetchWorker."""
        raw_url = self.url_input.text().strip()
        cleaned = clean_url(raw_url)
        if not cleaned:
            # Drop the previous video's card so the error is not shown next to an old title
            self.info_card.clear()
            self._current_info = None
            if self._job_running() or self._state == TabState.DOWNLOADING:
                self._apply_state_visibility(self._state)
            else:
                self.set_state(TabState.IDLE)
            self._show_input_error("Please paste a valid YouTube link.")
            return

        # Cache check BEFORE state transition or showing any banner / spinner
        if cleaned in _FETCH_CACHE:
            if self._fetch_worker is not None:
                try:
                    self._fetch_worker.fetched.disconnect()
                except (RuntimeError, TypeError):
                    pass
                try:
                    self._fetch_worker.failed.disconnect()
                except (RuntimeError, TypeError):
                    pass
            self._fetch_seq += 1
            self._last_fetched_url = cleaned
            self.inline_msg.clear()
            self._on_info_fetched(_FETCH_CACHE[cleaned])
            return

        if self._fetch_worker is not None:
            try:
                self._fetch_worker.fetched.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                self._fetch_worker.failed.disconnect()
            except (RuntimeError, TypeError):
                pass

        self._fetch_seq += 1
        current_seq = self._fetch_seq
        self._last_fetched_url = cleaned
        self.set_state(TabState.FETCHING)
        self.inline_msg.show_info("Getting video info…", auto_hide_ms=0)

        worker = InfoFetchWorker(cleaned, parent=self)
        self._fetch_worker = worker
        self._active_workers.add(worker)
        if hasattr(worker, "finished"):
            worker.finished.connect(lambda: self._active_workers.discard(worker))

        def _handle_fetched(info: VideoInfo) -> None:
            if current_seq != self._fetch_seq:
                return
            _FETCH_CACHE[cleaned] = info
            self._on_info_fetched(info)

        def _handle_failed(err: str) -> None:
            if current_seq != self._fetch_seq:
                return
            self._on_info_failed(err)

        worker.fetched.connect(_handle_fetched)
        worker.failed.connect(_handle_failed)
        worker.start()

    def preselect_quality(self, quality: str) -> None:
        """Pre-select requested quality when video info is fetched."""
        self._preselected_quality = quality

    def _on_info_fetched(self, info: VideoInfo) -> None:
        self.inline_msg.clear()
        self._current_info = info
        self.info_card.set_info(info)

        # Populate quality dropdown (real resolutions descending, 'Best available' first).
        # The shown text may add an approximate size; the clean label is kept for the job.
        # Sizes form a right-aligned column: padded with thin spaces using the list's font metrics
        # (plain text, no custom item painting).
        self.quality_combo.clear()
        rows = []
        for label, height in info.qualities:
            size = info.quality_sizes.get(height, 0)
            rows.append((label, height, f"≈ {ProgressCard._fmt_bytes(size)}" if size else ""))
        fm = self.quality_combo.view().fontMetrics()
        thin = max(1, fm.horizontalAdvance("\u2009"))
        column_end = max((fm.horizontalAdvance(l) for l, _, _ in rows), default=0) + 6 * thin + max(
            (fm.horizontalAdvance(sz) for _, _, sz in rows), default=0)
        for label, height, size_text in rows:
            shown = label
            if size_text:
                count = max(2, round((column_end - fm.horizontalAdvance(label) - fm.horizontalAdvance(size_text)) / thin))
                # Thin spaces are fractional pixels wide: measure and nudge until the row ends on the column edge
                while count > 2 and fm.horizontalAdvance(label + "\u2009" * count + size_text) > column_end:
                    count -= 1
                while fm.horizontalAdvance(label + "\u2009" * (count + 1) + size_text) <= column_end:
                    count += 1
                shown = label + "\u2009" * count + size_text
            self.quality_combo.addItem(shown, height)
            self.quality_combo.setItemData(self.quality_combo.count() - 1, label, QUALITY_LABEL_ROLE)

        if self._preselected_quality:
            target = self._preselected_quality.strip().lower()
            for idx in range(self.quality_combo.count()):
                text = (self.quality_combo.itemData(idx, QUALITY_LABEL_ROLE) or self.quality_combo.itemText(idx)).lower()
                if target in text or text in target:
                    self.quality_combo.setCurrentIndex(idx)
                    break
            self._preselected_quality = None
        else:
            # Settings > Downloads > Video quality (falls back to Best when the video lacks that height)
            wanted = load_settings().get("default_video_quality", "best")
            for idx in range(self.quality_combo.count()):
                if self.quality_combo.itemData(idx, QUALITY_LABEL_ROLE) == wanted:
                    self.quality_combo.setCurrentIndex(idx)
                    break

        if self._job_running():
            self.set_state(TabState.DOWNLOADING)
        else:
            self.set_state(TabState.READY)

    def _on_info_failed(self, error_msg: str) -> None:
        self.inline_msg.show_error(error_msg)
        self.info_card.clear()
        self._current_info = None
        if self._job_running():
            self.set_state(TabState.DOWNLOADING)
        else:
            self.set_state(TabState.IDLE)

    def start_download(self) -> None:
        """Start downloading current video or confirm duplicate."""
        job = self._build_job()
        if not job:
            return

        manager = get_download_manager("video")
        active = manager.active_job
        if active and (active.video_id, active.kind, active.quality_label) == (job.video_id, job.kind, job.quality_label):
            self.inline_msg.show_info(f"'{job.title}' ({job.quality_label}) is already downloading.")
            return

        waiting = manager.waiting_jobs or []
        if any((w.video_id, w.kind, w.quality_label) == (job.video_id, job.kind, job.quality_label) for w in waiting):
            self.inline_msg.show_info(f"'{job.title}' ({job.quality_label}) is already in the queue.")
            return

        # Duplicate check (Chunk 4.3)
        dup = find_duplicate(job.video_id, job.kind, job.quality_label)
        force_overwrite = False
        if dup:
            reply = QMessageBox.question(
                self,
                "Already Downloaded",
                f"'{job.title}' ({job.quality_label}) has already been downloaded.\nDownload again and replace the existing file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            force_overwrite = True

        if job.thumbnail_bytes:
            save_thumbnail(job.video_id, job.thumbnail_bytes)

        if force_overwrite:
            manager.enqueue(job, force_overwrite=True)
        else:
            manager.enqueue(job)

        # Clear inputs for next paste
        self._clear_inputs()

    def add_to_queue(self) -> None:
        """Add current video to queue without interrupting active download."""
        if not self._current_info:
            self.inline_msg.show_info("Paste a YouTube link first, then press Add to queue.", auto_hide_ms=4000)
            return

        job = self._build_job()
        if not job:
            return

        manager = get_download_manager("video")
        active = manager.active_job
        if active and (active.video_id, active.kind, active.quality_label) == (job.video_id, job.kind, job.quality_label):
            self.inline_msg.show_info(f"'{job.title}' ({job.quality_label}) is already downloading.")
            return

        waiting = manager.waiting_jobs or []
        if any((w.video_id, w.kind, w.quality_label) == (job.video_id, job.kind, job.quality_label) for w in waiting):
            self.inline_msg.show_info(f"'{job.title}' ({job.quality_label}) is already in the queue.")
            return

        if job.thumbnail_bytes:
            save_thumbnail(job.video_id, job.thumbnail_bytes)

        manager.enqueue(job)

        self._clear_inputs()

    def cancel_download(self) -> None:
        """Cancel active download."""
        manager = get_download_manager("video")
        manager.cancel_active()
        self.progress_card.set_stage("Cancelled.")
        if self._current_info is not None:
            self.set_state(TabState.READY)
        else:
            self._clear_inputs()
            self.set_state(TabState.IDLE)

    def _build_job(self) -> Optional[DownloadJob]:
        raw_url = self.url_input.text().strip()
        cleaned = clean_url(raw_url)
        if not cleaned:
            self._show_input_error("Please paste a valid YouTube link.")
            return None

        settings = load_settings()
        out_dir = settings.get("download_dir", str(DEFAULT_DOWNLOADS))

        try:
            free_bytes = shutil.disk_usage(out_dir).free
            if free_bytes < 50 * 1024 * 1024:
                self.inline_msg.show_error("Not enough disk space in download folder.")
                return None
        except Exception as exc:
            get_logger().debug(f"Could not check disk usage: {exc}")

        chosen_height = self.quality_combo.currentData()
        quality_label = self.quality_combo.currentData(QUALITY_LABEL_ROLE) or self.quality_combo.currentText() or "Best"

        if not self._current_info:
            # Fallback: create temporary info if info card wasn't fetched
            self._current_info = VideoInfo(
                url=cleaned,
                title="YouTube Video",
                channel="",
                duration=0,
                duration_str="",
                thumbnail_url="",
                qualities=[("Best", None)],
                filesize_approx=0,
            )

        try:
            return DownloadJob.create(
                info=self._current_info,
                kind="video",
                quality_label=quality_label,
                height=chosen_height,
                output_dir=out_dir,
                thumbnail_bytes=self.info_card.thumb_bytes,
            )
        except Exception as exc:
            self.inline_msg.show_error(f"Cannot start download: {exc}")
            return None

    def _on_manager_job_started(self, job: DownloadJob) -> None:
        if job.kind == "video":
            self.progress_card.bind_job(job)
            self.set_state(TabState.DOWNLOADING)

    def _on_manager_progress(self, job: DownloadJob, pct: float, speed: str, eta: str, done: int, total: int) -> None:
        if job.kind == "video":
            self.progress_card.set_progress(pct, speed, eta, done, total)

    def _on_manager_stage(self, job: DownloadJob, stage_name: str) -> None:
        if job.kind == "video":
            self.progress_card.set_stage(stage_name)

    def _is_job_link(self, job: DownloadJob) -> bool:
        job_url = getattr(job, "url", None)
        if not isinstance(job_url, str) or not job_url.strip():
            return False
        cleaned_job = clean_url(job_url) or job_url.strip()
        current_input = clean_url(self.url_input.text().strip()) or self.url_input.text().strip()
        if current_input and current_input == cleaned_job:
            return True
        if self._current_info:
            current_info_url = clean_url(self._current_info.url) or self._current_info.url.strip()
            if current_info_url and current_info_url == cleaned_job:
                return True
        return False

    def _on_manager_finished(self, job: DownloadJob, final_path: str) -> None:
        if job.kind == "video":
            self.progress_card.show_done(out_dir=job.output_dir, final_path=final_path)
            if final_path and load_settings().get("open_folder_when_done", False):
                reveal_in_folder(final_path)
            self.recent_list.refresh()
            self.download_completed.emit(job.title)
            same_link = self._is_job_link(job)
            keep_link = (not same_link) and (self._current_info is not None or bool(self.url_input.text().strip()))
            if not keep_link:
                self._clear_inputs()
            if self._job_running() or self._has_waiting_job():
                self.set_state(TabState.DOWNLOADING)
            elif self._current_info is not None:
                self.set_state(TabState.READY)
            else:
                self.set_state(TabState.IDLE)

    def _on_manager_failed(self, job: DownloadJob, error_reason: str) -> None:
        if job.kind == "video":
            self.inline_msg.show_error(f"Download failed: {error_reason}")
            self.progress_card.reset()
            same_link = self._is_job_link(job)
            keep_link = (not same_link) and (self._current_info is not None or bool(self.url_input.text().strip()))
            if not keep_link:
                self._clear_inputs()
            if self._job_running() or self._has_waiting_job():
                self.set_state(TabState.DOWNLOADING)
            elif self._current_info is not None:
                self.set_state(TabState.READY)
            else:
                self.set_state(TabState.IDLE)

    def _on_manager_cancelled(self, job: DownloadJob) -> None:
        if job.kind == "video":
            self.progress_card.reset()
            same_link = self._is_job_link(job)
            keep_link = (not same_link) and (self._current_info is not None or bool(self.url_input.text().strip()))
            if not keep_link:
                self._clear_inputs()
            if self._job_running() or self._has_waiting_job():
                self.set_state(TabState.DOWNLOADING)
            elif self._current_info is not None:
                self.set_state(TabState.READY)
            else:
                self.set_state(TabState.IDLE)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.StyleChange:
            if hasattr(self, "quality_combo") and hasattr(self.quality_combo, "_update_popup_style"):
                self.quality_combo._update_popup_style()

