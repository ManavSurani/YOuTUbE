import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from app.ui.main_window import MainWindow
from app.core.download_manager import get_download_manager
from app.core.jobs import DownloadJob
from app.ui.video_tab import TabState

vm = get_download_manager("video")
am = get_download_manager("audio")
vm._waiting_queue.clear()
vm._failed_jobs.clear()
vm._active_job = None

win = MainWindow()
win.resize(760, 680)
win.show()
app.processEvents()

t = time.time()
active_job = DownloadJob(
    job_id="vid_active",
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    video_id="dQw4w9WgXcQ",
    title="Rick Astley - Never Gonna Give You Up (Official Music Video)",
    channel="Rick Astley",
    duration_seconds=213,
    thumbnail_url="",
    thumbnail_bytes=b"",
    kind="video",
    quality_label="1080p",
    height=1080,
    audio_format=None,
    output_dir="C:/Downloads",
    created_at=t,
)
vm._active_job = active_job

job1 = DownloadJob(
    job_id="vid_queued_1",
    url="https://www.youtube.com/watch?v=kJQP7kiw5Fk",
    video_id="kJQP7kiw5Fk",
    title="Luis Fonsi - Despacito ft. Daddy Yankee",
    channel="Luis Fonsi",
    duration_seconds=282,
    thumbnail_url="",
    thumbnail_bytes=b"",
    kind="video",
    quality_label="4K",
    height=2160,
    audio_format=None,
    output_dir="C:/Downloads",
    created_at=t + 1,
)
job2 = DownloadJob(
    job_id="vid_queued_2",
    url="https://www.youtube.com/watch?v=JGwWNGJdvx8",
    video_id="JGwWNGJdvx8",
    title="Ed Sheeran - Shape of You (Official Music Video)",
    channel="Ed Sheeran",
    duration_seconds=263,
    thumbnail_url="",
    thumbnail_bytes=b"",
    kind="video",
    quality_label="720p",
    height=720,
    audio_format=None,
    output_dir="C:/Downloads",
    created_at=t + 2,
)
vm._waiting_queue.extend([job1, job2])

vtab = win.video_tab
vtab.set_state(TabState.DOWNLOADING)
vtab.progress_card.bind_job(active_job)
vtab.progress_card.set_progress(45.0, speed="3.2 MB/s", eta="00:42", stats="45 MB / 100 MB")

vm.queue_changed.emit()
app.processEvents()

pix = win.grab()
ok1 = pix.save("screenshot_phase_d_queue_cards.png")
ok2 = pix.save("docs/verification/screenshot_phase_d_queue_cards.png")
print("Saved 1:", ok1, "Saved 2:", ok2)

vm._waiting_queue.clear()
vm._active_job = None
win.tray_icon.hide()
win.close()
sys.exit(0)
