#!/usr/bin/env python3
"""Render every screen, dialog, menu and popup in dark and light mode to PNGs, plus automatic checks.

Usage:
  python tools/ui_snapshots.py <label>      -> docs/ui_audit/snapshots/<label>/*.png (git-ignored)

Covers: main screens and states (ready, error, downloading, paused, done with a file, copied-link chip,
audio, history + search, banner + offline), Settings and History dialogs, a message box, menus (History row,
History "more", tray, link-box context menu), the quality popup, a tooltip, the splash screen, and a live
theme switch in both directions. Checks printed at the end: clipped widgets, menu/tooltip backgrounds that
do not match the theme, and icon buttons that are not their requested size.

Uses a throwaway copy of the app data (history + settings only), so real data is never touched.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REAL_DATA = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "YOuTUbE"

# Sandbox app data before any app module is imported (paths.py reads APPDATA at import)
_sandbox = Path(tempfile.mkdtemp(prefix="yt_snap_"))
(_sandbox / "YOuTUbE").mkdir()
if (REAL_DATA / "history").is_dir():
    shutil.copytree(REAL_DATA / "history", _sandbox / "YOuTUbE" / "history")
_settings = {}
if (REAL_DATA / "settings.json").is_file():
    _settings = json.loads((REAL_DATA / "settings.json").read_text(encoding="utf-8"))
_settings["last_app_check"] = 10**12  # no update check during snapshots
(_sandbox / "YOuTUbE" / "settings.json").write_text(json.dumps(_settings), encoding="utf-8")
os.environ["APPDATA"] = str(_sandbox)
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QColor, QContextMenuEvent  # noqa: E402
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QMessageBox, QSystemTrayIcon,  # noqa: E402
                               QToolTip, QWidget)

app = QApplication([])
QSystemTrayIcon.show = lambda self: None  # no real tray icon while rendering

import app.ui.splash as splash_mod  # noqa: E402
from app.core.app_updater import UpdateInfo  # noqa: E402
from app.core.download_manager import get_download_manager  # noqa: E402
from app.core.history_db import HistoryItem  # noqa: E402
from app.core.info_fetcher import VideoInfo  # noqa: E402
from app.core.jobs import DownloadJob  # noqa: E402
from app.ui.history_tab import ClearAllDialog, HistoryDeleteDialog, HistoryRowWidget, HistoryWarningDialog  # noqa: E402
from app.ui.kit import IconButton  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402
from app.ui.settings_dialog import SettingsDialog  # noqa: E402
from app.ui.theme import ThemeManager, tok  # noqa: E402
from app.ui.video_tab import TabState  # noqa: E402

INFO = VideoInfo(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    title="So Weak His Father Wanted Him DEAD, Then He Awakened ANCIENT Skills!",
    channel="Recap Studio", duration=5412, duration_str="1:30:12", thumbnail_url="",
    qualities=[("Best available (1080p)", None), ("1080p", 1080), ("720p", 720), ("480p", 480)],
    filesize_approx=0, quality_sizes={720: 252_153_760, 480: 182_110_388},
)


def _job(title: str) -> DownloadJob:
    info = VideoInfo(**{**INFO.__dict__, "title": title})
    return DownloadJob.create(info=info, kind="video", quality_label="1080p", height=1080,
                              output_dir="C:/Users/Jay/Downloads")


def _settle(ms: int = 450) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)  # let 120-300 ms animations finish
    loop.exec()


class Snapper:
    def __init__(self, out: Path) -> None:
        self.out = out
        self.errors: list = []
        self.findings: list = []

    def snap(self, widget, name: str, check: bool = True) -> None:
        try:
            _settle()
            widget.grab().save(str(self.out / f"{name}.png"))
            if check:
                self._check(widget, name)
        except Exception as exc:  # keep going so one broken screen does not hide the rest
            self.errors.append(f"{name}: {exc}")

    def _check(self, top, name: str) -> None:
        for w in top.findChildren(QWidget):
            if not w.isVisibleTo(top) or w.width() <= 0 or w.height() <= 0:
                continue
            parent = w.parentWidget()
            if parent is None or isinstance(parent.parentWidget(), QAbstractScrollArea):
                continue  # scroll contents are bigger than their viewport on purpose
            g, r = w.geometry(), parent.rect()
            if g.bottom() > r.bottom() + 1 or g.right() > r.right() + 1:
                self.findings.append(f"{name}: clipped {type(w).__name__} {g.getRect()} in {type(parent).__name__} {r.size().toTuple()}")
            if isinstance(w, IconButton) and w.width() != w.height():
                self.findings.append(f"{name}: icon button '{w.icon_name}' is {w.width()}x{w.height()}, not square")

    def popup_bg(self, widget, name: str) -> None:
        """Grab a menu/tooltip and check its background is the theme surface colour."""
        _settle(250)
        img = widget.grab().toImage()
        img.save(str(self.out / f"{name}.png"))
        bg = img.pixelColor(img.width() // 2, min(3, img.height() - 1))
        want = QColor(tok("surface"))
        if max(abs(bg.red() - want.red()), abs(bg.green() - want.green()), abs(bg.blue() - want.blue())) > 24:
            self.findings.append(f"{name}: background {bg.name()} does not match theme surface {want.name()}")


def _show(widget, w=1000, h=820):
    widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    widget.resize(w, h)
    widget.show()
    return widget


def render_theme(s: Snapper, theme: str) -> None:
    ThemeManager.instance().apply(theme)
    p = f"{theme}_"

    splash_mod.SplashScreen._start_worker = lambda self, skip_app_update=False: None
    sp = _show(splash_mod.SplashScreen(), 360, 260)
    sp.status_label.setText("Checking for app update…")
    sp.progress_bar.setValue(35)
    s.snap(sp, p + "01_splash")
    sp.close()

    win = _show(MainWindow(), 1000, 820)
    vt = win.video_tab
    s.snap(win, p + "02_video_idle")
    vt._on_info_fetched(INFO)
    s.snap(win, p + "03_video_ready")
    vt.quality_combo.showPopup()
    s.popup_bg(vt.quality_combo.view().window(), p + "03b_quality_popup")
    vt.quality_combo.hidePopup()
    vt._show_input_error("Please paste a valid YouTube link.")
    s.snap(win, p + "04_video_error")
    vt.reset_messages()
    vt._on_info_fetched(INFO)

    vt.url_input.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Keyboard, QPoint(5, 5), QPoint(0, 0)))
    if vt.url_input._current_menu is not None:
        s.popup_bg(vt.url_input._current_menu, p + "04b_linkbox_menu")
        vt.url_input._current_menu.close()

    mgr = get_download_manager("video")
    active, failed = _job(INFO.title), _job("Private video test")
    mgr._active_job = active
    mgr._waiting_queue = [_job("Lo-fi beats to study and relax to — 3 hour mix")]
    mgr._failed_jobs = {failed.job_id: (failed, "This video is private.")}
    vt.set_state(TabState.DOWNLOADING)
    vt.progress_card.bind_job(active)
    vt.progress_card.set_stage("Downloading video")
    vt.progress_card.set_progress(46.0, "8.4 MB/s", "01:12", 317_000_000, 723_600_000)
    vt.queue_widget.refresh()
    s.snap(win, p + "05_video_downloading")
    vt.progress_card.set_paused(True)
    vt.progress_card.set_stage("Paused")
    s.snap(win, p + "05b_video_paused")
    vt.progress_card.set_paused(False)

    done_file = s.out / "_done.mkv"
    done_file.write_bytes(b"x" * 723_000)
    vt.progress_card.show_done(out_dir="C:/Users/Jay/Downloads", final_path=str(done_file))
    s.snap(win, p + "06_video_done")
    vt.offer_clipboard_link("https://www.youtube.com/watch?v=abcdefghijk")
    s.snap(win, p + "06b_clip_chip")
    mgr._active_job, mgr._waiting_queue, mgr._failed_jobs = None, [], {}
    vt.queue_widget.refresh()

    win.header.select_tab(1)
    s.snap(win, p + "07_audio")
    win.header.select_tab(2)
    s.snap(win, p + "08_history")
    win.history_tab.search_input.setText("e")
    s.snap(win, p + "08b_history_search")
    win.history_tab.search_input.setText("")

    item = HistoryItem(id=1, title="Some video", url=INFO.url, type="video", quality="1080p",
                       file_path=str(done_file), size_bytes=723_000, duration=60)
    row_menu = HistoryRowWidget(item).build_more_menu()
    row_menu.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    row_menu.popup(QPoint(0, 0))
    s.popup_bg(row_menu, p + "08c_history_row_menu")
    row_menu.close()
    more_menu = win.history_tab.build_more_menu()
    more_menu.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    more_menu.popup(QPoint(0, 0))
    s.popup_bg(more_menu, p + "08d_history_more_menu")
    more_menu.close()
    tray_menu = win.tray_icon.contextMenu()
    tray_menu.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    tray_menu.popup(QPoint(0, 0))
    s.popup_bg(tray_menu, p + "08e_tray_menu")
    tray_menu.close()
    win.header.select_tab(0)

    QToolTip.showText(QPoint(10, 10), "Pause (Space)", win)
    tip = next((w for w in QApplication.topLevelWidgets() if type(w).__name__ == "QTipLabel" and w.isVisible()), None)
    if tip is not None:
        s.popup_bg(tip, p + "08f_tooltip")
    QToolTip.hideText()

    win.update_banner.show_update(UpdateInfo(status="available", latest_version="9.9.9", installer_url="u", sha256="s"))
    win._on_went_offline()
    s.snap(win, p + "09_banner_offline")
    win._on_came_online()

    for name, dlg in (("10_settings", SettingsDialog(win)), ("11_delete_dialog", HistoryDeleteDialog(item, True, win)),
                      ("12_clear_dialog", ClearAllDialog(win)),
                      ("13_warning_dialog", HistoryWarningDialog("File missing", "The file was moved or deleted.", win))):
        _show(dlg, *dlg.size().toTuple())
        s.snap(dlg, p + name)
        dlg.close()
    box = QMessageBox(QMessageBox.Icon.Question, "YOuTUbE", "A download is still running. Quit anyway?",
                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, win)
    _show(box, *box.sizeHint().toTuple())
    s.snap(box, p + "14_message_box")
    box.close()

    win.network_monitor.stop()
    win.hide()
    win.deleteLater()


def render_live_switch(s: Snapper, start: str, end: str) -> None:
    """Open everything in one theme, switch live, and render again."""
    ThemeManager.instance().apply(start)
    win = _show(MainWindow(), 1000, 820)
    win.video_tab._on_info_fetched(INFO)
    dlg = _show(SettingsDialog(win), 820, 700)
    _settle()
    ThemeManager.instance().apply(end)
    p = f"live_{start}_to_{end}_"
    s.snap(win, p + "main")
    s.snap(dlg, p + "settings")
    dlg.close()
    win.header.select_tab(2)
    s.snap(win, p + "history")
    win.network_monitor.stop()
    win.hide()
    win.deleteLater()


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "latest"
    out = ROOT / "docs" / "ui_audit" / "snapshots" / label
    out.mkdir(parents=True, exist_ok=True)
    s = Snapper(out)
    try:
        for theme in ("dark", "light"):
            render_theme(s, theme)
        render_live_switch(s, "dark", "light")
        render_live_switch(s, "light", "dark")
    finally:
        shutil.rmtree(_sandbox, ignore_errors=True)
    shots = sorted(p.name for p in out.glob("*.png"))
    print(f"{len(shots)} snapshots in {out}")
    for f in sorted(set(s.findings)):
        print("FINDING", f)
    for e in s.errors:
        print("ERROR", e)
    return 1 if s.errors else 0


if __name__ == "__main__":
    sys.exit(main())
