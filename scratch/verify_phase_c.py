"""Real-PC Verification for Phase C (Dual Lanes)."""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.download_manager import DownloadManager, get_download_manager, migrate_legacy_queue_if_needed, _managers
from app.core.jobs import DownloadJob
from app.core.info_fetcher import VideoInfo
from app.core.paths import APP_DATA
from app.ui.main_window import MainWindow

print("=== Starting Real-PC Phase C Verification ===")

app = QApplication.instance() or QApplication(sys.argv)

results = {}

# 1. Legacy Migration Check
print("\n--- Check 1: Legacy Migration Check ---")
test_app_data = ROOT / "scratch" / "test_migration_appdata"
test_app_data.mkdir(parents=True, exist_ok=True)
dummy_queue = test_app_data / "queue.json"
dummy_items = [
    {
        "job_id": "v_mig",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video_id": "dQw4w9WgXcQ",
        "title": "Migrated Video",
        "kind": "video",
        "quality_label": "1080p",
    },
    {
        "job_id": "a_mig",
        "url": "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
        "video_id": "kJQP7kiw5Fk",
        "title": "Migrated Audio",
        "kind": "audio",
        "quality_label": "mp3",
    },
]
dummy_queue.write_text(json.dumps(dummy_items), encoding="utf-8")
migrate_legacy_queue_if_needed(test_app_data)

chk1_bak = (test_app_data / "queue.json.bak").exists()
chk1_v = (test_app_data / "queue_video.json").exists()
chk1_a = (test_app_data / "queue_audio.json").exists()
if chk1_bak and chk1_v and chk1_a:
    v_data = json.loads((test_app_data / "queue_video.json").read_text(encoding="utf-8"))
    a_data = json.loads((test_app_data / "queue_audio.json").read_text(encoding="utf-8"))
    chk1_ok = len(v_data) == 1 and v_data[0]["job_id"] == "v_mig" and len(a_data) == 1 and a_data[0]["job_id"] == "a_mig"
else:
    chk1_ok = False
results["Check 1: Legacy Migration"] = "PASS" if chk1_ok else "FAIL"
print(f"Check 1 Result: {results['Check 1: Legacy Migration']}")

# 2. Parallel Download UI Check & Screenshot
print("\n--- Check 2: Parallel Download & Screenshot Check ---")
with patch("app.ui.main_window.NetworkMonitor.start"), patch.object(MainWindow, "_check_for_updates"):
    win = MainWindow()
    if hasattr(win.header.status_dot, "_start_color") is False:
        win.header.status_dot._start_color = win.header.status_dot._color

    v_mgr = get_download_manager("video")
    a_mgr = get_download_manager("audio")
    v_mgr._waiting_queue.clear()
    a_mgr._waiting_queue.clear()
    v_mgr._active_job = None
    a_mgr._active_job = None
    v_mgr._deferred_job_ids.clear()
    a_mgr._deferred_job_ids.clear()
    v_mgr._is_offline = False
    a_mgr._is_offline = False

    # Create two parallel jobs with different 11-char video IDs
    job_v = DownloadJob.create(
        VideoInfo(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", title="Parallel Video 1080p", channel="Chan A", duration=180, duration_str="3:00", thumbnail_url="", qualities=[], filesize_approx=10000000),
        kind="video", quality_label="1080p",
    )
    job_a = DownloadJob.create(
        VideoInfo(url="https://www.youtube.com/watch?v=kJQP7kiw5Fk", title="Parallel Audio 320k", channel="Chan B", duration=210, duration_str="3:30", thumbnail_url="", qualities=[], filesize_approx=5000000),
        kind="audio", quality_label="MP3",
    )

    # Start both lanes
    v_mgr._start_worker = MagicMock()
    a_mgr._start_worker = MagicMock()

    v_mgr.enqueue(job_v)
    a_mgr.enqueue(job_a)

    chk2_parallel = (v_mgr.active_job is not None and a_mgr.active_job is not None)
    results["Check 2: Parallel Downloads"] = "PASS" if chk2_parallel else "FAIL"
    print(f"Check 2 Result: {results['Check 2: Parallel Downloads']} (video={v_mgr.active_job.title}, audio={a_mgr.active_job.title})")

    # Simulate progress on both cards
    win.video_tab.progress_card.bind_job(job_v)
    win.video_tab.progress_card.set_progress(45.5, "2.4 MB/s", "00:15", 4550000, 10000000)
    win.video_tab.progress_card.set_stage("Downloading video (1080p)…")

    win.audio_tab.progress_card.bind_job(job_a)
    win.audio_tab.progress_card.set_progress(78.2, "1.8 MB/s", "00:03", 3910000, 5000000)
    win.audio_tab.progress_card.set_stage("Extracting audio (MP3)…")

    # Render window and take screenshot
    win.resize(800, 600)
    win.show()
    app.processEvents()

    pixmap = win.grab()
    screenshot_path = ROOT / "screenshot_phase_c_parallel.png"
    pixmap.save(str(screenshot_path))
    print(f"Screenshot saved to: {screenshot_path}")

# 3. Same Video ID Deferral Check
print("\n--- Check 3: Same Video ID Deferral Check ---")
v_mgr._waiting_queue.clear()
a_mgr._waiting_queue.clear()
v_mgr._active_job = None
a_mgr._active_job = None
v_mgr._deferred_job_ids.clear()
a_mgr._deferred_job_ids.clear()

job_v_same = DownloadJob.create(
    VideoInfo(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", title="Shared Video", channel="C", duration=100, duration_str="1:40", thumbnail_url="", qualities=[], filesize_approx=0),
    kind="video", quality_label="1080p",
)
job_a_same = DownloadJob.create(
    VideoInfo(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", title="Shared Audio", channel="C", duration=100, duration_str="1:40", thumbnail_url="", qualities=[], filesize_approx=0),
    kind="audio", quality_label="MP3",
)

v_mgr._start_worker = MagicMock()
a_mgr._start_worker = MagicMock()

v_mgr.enqueue(job_v_same)
a_mgr.enqueue(job_a_same)

chk3_deferral = (v_mgr.active_job is not None and a_mgr.active_job is None and job_a_same.job_id in a_mgr.deferred_job_ids())
# Now finish video
v_mgr._active_job = None
v_mgr._wake_all_lanes()
chk3_woken = (a_mgr.active_job is not None and a_mgr.active_job.job_id == job_a_same.job_id)

results["Check 3: Same Video ID Deferral"] = "PASS" if (chk3_deferral and chk3_woken) else "FAIL"
print(f"Check 3 Result: {results['Check 3: Same Video ID Deferral']}")

# 4. Lane Queue Isolation Check
print("\n--- Check 4: Lane Queue Isolation Check ---")
v_mgr._waiting_queue.clear()
a_mgr._waiting_queue.clear()
v_mgr._active_job = None
a_mgr._active_job = None

v1 = DownloadJob.create(VideoInfo(url="https://youtube.com/watch?v=11111111111", title="V1", channel="C", duration=10, duration_str="0:10", thumbnail_url="", qualities=[], filesize_approx=0), kind="video", quality_label="1080p")
v2 = DownloadJob.create(VideoInfo(url="https://youtube.com/watch?v=22222222222", title="V2", channel="C", duration=10, duration_str="0:10", thumbnail_url="", qualities=[], filesize_approx=0), kind="video", quality_label="1080p")
a1 = DownloadJob.create(VideoInfo(url="https://youtube.com/watch?v=33333333333", title="A1", channel="C", duration=10, duration_str="0:10", thumbnail_url="", qualities=[], filesize_approx=0), kind="audio", quality_label="MP3")
a2 = DownloadJob.create(VideoInfo(url="https://youtube.com/watch?v=44444444444", title="A2", channel="C", duration=10, duration_str="0:10", thumbnail_url="", qualities=[], filesize_approx=0), kind="audio", quality_label="MP3")

v_mgr._waiting_queue.extend([v1, v2])
a_mgr._waiting_queue.extend([a1, a2])
v_mgr._save_persisted_queue()
a_mgr._save_persisted_queue()

# Instantiate fresh managers pointing to those files
v_test = DownloadManager(kind="video")
a_test = DownloadManager(kind="audio")
chk4_iso = (all(j.kind == "video" for j in v_test.waiting_jobs) and len(v_test.waiting_jobs) == 2 and
            all(j.kind == "audio" for j in a_test.waiting_jobs) and len(a_test.waiting_jobs) == 2)
results["Check 4: Lane Queue Isolation"] = "PASS" if chk4_iso else "FAIL"
print(f"Check 4 Result: {results['Check 4: Lane Queue Isolation']}")

# 5. Offline Pause/Resume Check
print("\n--- Check 5: Offline Pause/Resume Check ---")
worker_v = MagicMock()
worker_a = MagicMock()
v_mgr._active_job = v1
a_mgr._active_job = a1
v_mgr._worker = worker_v
a_mgr._worker = worker_a

with patch("PySide6.QtWidgets.QMessageBox.information"):
    win._on_went_offline()
chk5_paused = (worker_v.pause.called and worker_a.pause.called and v_mgr._is_offline and a_mgr._is_offline)

win._on_came_online()
chk5_resumed = (not v_mgr._is_offline and not a_mgr._is_offline)
results["Check 5: Offline Pause/Resume"] = "PASS" if (chk5_paused and chk5_resumed) else "FAIL"
print(f"Check 5 Result: {results['Check 5: Offline Pause/Resume']}")

# 6. Safe Close Check
print("\n--- Check 6: Safe Close Check ---")
v_mgr._active_job = v1
a_mgr._active_job = a1
worker_v = MagicMock()
worker_v.wait.return_value = True
worker_v.isRunning.return_value = False
worker_a = MagicMock()
worker_a.wait.return_value = True
worker_a.isRunning.return_value = False
v_mgr._worker = worker_v
a_mgr._worker = worker_a

from PySide6.QtGui import QCloseEvent
event = QCloseEvent()
t0 = time.monotonic()
def fake_exec(*args, **kwargs):
    box = win.findChild(QMessageBox)
    if box:
        for btn in box.buttons():
            if btn.text() == "Quit":
                box._mock_clicked = btn
                break

with patch("PySide6.QtWidgets.QMessageBox.exec", side_effect=fake_exec), \
     patch("PySide6.QtWidgets.QMessageBox.clickedButton", side_effect=lambda *a: getattr(win.findChild(QMessageBox), "_mock_clicked", None)):
    v_mgr.shutdown = MagicMock()
    a_mgr.shutdown = MagicMock()
    win.closeEvent(event)
duration = time.monotonic() - t0
chk6_close = (duration < 2.0 and event.isAccepted() and v_mgr.shutdown.called and a_mgr.shutdown.called)
results["Check 6: Safe Close"] = "PASS" if chk6_close else "FAIL"
print(f"Check 6 Result: {results['Check 6: Safe Close']} (duration={duration:.3f}s)")

# 7. Restored Queue Auto-Start Check
print("\n--- Check 7: Restored Queue Auto-Start Check ---")
v_mgr._waiting_queue = [v1, v2]
a_mgr._waiting_queue = [a1, a2]
v_mgr._active_job = None
a_mgr._active_job = None
v_mgr._is_offline = False
a_mgr._is_offline = False

v_mgr._start_worker = MagicMock()
a_mgr._start_worker = MagicMock()

v_mgr.start_restored_jobs()
a_mgr.start_restored_jobs()

chk7_autostart = (v_mgr.active_job is not None and v_mgr.active_job.job_id == v1.job_id and
                  a_mgr.active_job is not None and a_mgr.active_job.job_id == a1.job_id)
results["Check 7: Restored Queue Auto-Start"] = "PASS" if chk7_autostart else "FAIL"
print(f"Check 7 Result: {results['Check 7: Restored Queue Auto-Start']}")

# Clean up
v_mgr._waiting_queue.clear()
a_mgr._waiting_queue.clear()
v_mgr._save_persisted_queue()
a_mgr._save_persisted_queue()

if hasattr(win, "tray_icon") and win.tray_icon:
    win.tray_icon.hide()
    win.tray_icon.deleteLater()
win.deleteLater()
app.processEvents()

print("\n=== All Real-PC Checks Summary ===")
for chk, res in results.items():
    print(f"  {chk}: {res}")

all_pass = all(res == "PASS" for res in results.values())
print(f"\nFinal Real-PC Status: {'ALL PASS' if all_pass else 'FAILURES DETECTED'}")
sys.exit(0 if all_pass else 1)
