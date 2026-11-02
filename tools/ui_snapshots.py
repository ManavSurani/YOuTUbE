#!/usr/bin/env python3
"""Render every main screen in dark and light mode to PNGs for visual review.

Usage:
  python tools/ui_snapshots.py <label>      -> docs/ui_audit/snapshots/<label>/*.png (git-ignored)

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

from PySide6.QtCore import QEventLoop, Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QSystemTrayIcon  # noqa: E402

app = QApplication([])
QSystemTrayIcon.show = lambda self: None  # no real tray icon while rendering

import app.ui.splash as splash_mod  # noqa: E402
from app.core.app_updater import UpdateInfo  # noqa: E402
from app.core.download_manager import get_download_manager  # noqa: E402
from app.core.info_fetcher import VideoInfo  # noqa: E402
from app.core.jobs import DownloadJob  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402
from app.ui.settings_dialog import SettingsDialog  # noqa: E402
from app.ui.theme import build_qss  # noqa: E402
from app.ui.video_tab import TabState  # noqa: E402

INFO = VideoInfo(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    title="So Weak His Father Wanted Him DEAD, Then He Awakened ANCIENT Skills!",
    channel="Recap Studio", duration=5412, duration_str="1:30:12", thumbnail_url="",
    qualities=[("Best available (1080p)", None), ("1080p", 1080), ("720p", 720), ("480p", 480)],
    filesize_approx=0,
)


def _job(title: str) -> DownloadJob:
    info = VideoInfo(**{**INFO.__dict__, "title": title})
    return DownloadJob.create(info=info, kind="video", quality_label="1080p", height=1080,
                              output_dir="C:/Users/Jay/Downloads")


def _settle() -> None:
    loop = QEventLoop()
    QTimer.singleShot(450, loop.quit)  # let 150-300 ms animations finish
    loop.exec()


def _apply_theme(name: str) -> None:
    try:
        from app.ui.theme import ThemeManager
        ThemeManager.instance().apply(name)
    except ImportError:
        app.setStyleSheet(build_qss(name))


def render(out: Path) -> list:
    errors = []

    def snap(widget, name):
        try:
            _settle()
            widget.grab().save(str(out / f"{name}.png"))
        except Exception as exc:  # keep going so one broken screen does not hide the rest
            errors.append(f"{name}: {exc}")

    for theme in ("dark", "light"):
        _apply_theme(theme)

        splash_mod.SplashScreen._start_worker = lambda self, skip_app_update=False: None
        sp = splash_mod.SplashScreen()
        sp.status_label.setText("Checking for app update…")
        sp.progress_bar.setValue(35)
        sp.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        sp.show()
        snap(sp, f"{theme}_01_splash")
        sp.close()

        win = MainWindow()
        win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        win.resize(880, 760)
        win.show()
        vt = win.video_tab
        snap(win, f"{theme}_02_video_idle")

        vt._on_info_fetched(INFO)
        snap(win, f"{theme}_03_video_ready")

        vt.inline_msg.show_error("That doesn't look like a YouTube link.")
        snap(win, f"{theme}_04_video_error")
        vt.inline_msg.hide()
        vt._on_info_fetched(INFO)

        mgr = get_download_manager("video")
        active = _job(INFO.title)
        failed = _job("Private video test")
        mgr._active_job = active
        mgr._waiting_queue = [_job("Lo-fi beats to study and relax to — 3 hour mix"),
                              _job("How Rockets Work | Full Documentary")]
        mgr._failed_jobs = {failed.job_id: (failed, "This video is private.")}
        vt.set_state(TabState.DOWNLOADING)
        vt.progress_card.bind_job(active)
        vt.progress_card.set_stage("Downloading video")
        vt.progress_card.set_progress(46.0, "8.4 MB/s", "01:12", 317_000_000, 723_600_000)
        vt.queue_widget.refresh()
        snap(win, f"{theme}_05_video_downloading")

        vt.progress_card.show_done(out_dir="C:/Users/Jay/Downloads")
        snap(win, f"{theme}_06_video_done")
        mgr._active_job, mgr._waiting_queue, mgr._failed_jobs = None, [], {}
        vt.queue_widget.refresh()

        win.header.select_tab(1)
        snap(win, f"{theme}_07_audio")
        win.header.select_tab(2)
        snap(win, f"{theme}_08_history")
        win.header.select_tab(0)

        win.update_banner.show_update(UpdateInfo(status="available", latest_version="9.9.9",
                                                 installer_url="u", sha256="s"))
        win.header.set_online(False)
        snap(win, f"{theme}_09_banner_offline")

        dlg = SettingsDialog(win)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        dlg.show()
        snap(dlg, f"{theme}_10_settings")
        dlg.close()

        if hasattr(win.network_monitor, "stop"):
            win.network_monitor.stop()
        win.hide()
        win.deleteLater()
    return errors


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "latest"
    out = ROOT / "docs" / "ui_audit" / "snapshots" / label
    out.mkdir(parents=True, exist_ok=True)
    try:
        errors = render(out)
    finally:
        shutil.rmtree(_sandbox, ignore_errors=True)
    shots = sorted(p.name for p in out.glob("*.png"))
    print(f"{len(shots)} snapshots in {out}")
    for e in errors:
        print("ERROR", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
