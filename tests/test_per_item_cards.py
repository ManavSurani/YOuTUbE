from pathlib import Path
from typing import Optional
import pytest
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication

from app.core.download_manager import get_download_manager
from app.core.jobs import DownloadJob
from app.ui.queue_widget import QueueRow, QueueWidget


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def make_test_job(
    job_id: str = "job_1",
    kind: str = "video",
    video_id: str = "dQw4w9WgXcQ",
    title: str = "Test Video",
    quality_label: str = "1080p",
) -> DownloadJob:
    return DownloadJob(
        job_id=job_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        video_id=video_id,
        title=title,
        channel="Channel",
        duration_seconds=60,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind=kind,
        quality_label=quality_label,
        height=1080 if kind == "video" else None,
        audio_format="mp3" if kind == "audio" else None,
        output_dir="C:/downloads",
        created_at="2026-10-09T00:00:00Z",
    )


def test_queue_row_has_progress_bar(qapp):
    job = make_test_job(job_id="job_vid_1")
    row = QueueRow(job=job, can_remove=True)
    assert hasattr(row, "progress_bar")
    assert row.progress_bar is not None
    assert row.progress_bar.value() == 0
    assert row.progress_bar.height() == 6


def test_queue_row_deferred_status_text(qapp, monkeypatch):
    job = make_test_job(job_id="job_def_1", title="Deferred Video")
    manager = get_download_manager("video")
    monkeypatch.setattr(manager, "deferred_job_ids", lambda: {"job_def_1"})
    row = QueueRow(job=job)
    assert "Waiting for the same video to finish" in row.status_lbl.text()


def test_queue_row_failed_state(qapp):
    job = make_test_job(job_id="job_fail_1", title="Failed Video")
    # Test with custom reason
    row = QueueRow(job=(job, "Network connection lost"))
    assert row.status_lbl.text() == "Failed: Network connection lost"
    assert row.progress_bar.value() == 0
    assert row.retry_btn is not None
    assert row.remove_btn is not None

    # Test with empty reason -> fallback "Something went wrong"
    row_empty = QueueRow(job=(job, ""))
    assert row_empty.status_lbl.text() == "Failed: Something went wrong"


def test_queue_row_thumbnail_saved_shows_real_image(qapp, tmp_path: Path, monkeypatch):
    import app.core.thumbnails as thumb_mod
    monkeypatch.setattr(thumb_mod, "THUMBS_DIR", tmp_path)

    # 1. Create a job without saved thumbnail:
    job_placeholder = make_test_job(job_id="job_ph", video_id="ph111111111")
    row_ph = QueueRow(job=job_placeholder)
    ph_pix = row_ph.thumb.pixmap()
    assert ph_pix is not None
    assert not ph_pix.isNull()

    # 2. Create a job with saved thumbnail (Phase A.4):
    img = QImage(64, 36, QImage.Format.Format_ARGB32)
    img.fill(QColor(12, 34, 56))
    img.save(str(tmp_path / "real1111111.jpg"), "JPG")

    job_real = make_test_job(job_id="job_real", video_id="real1111111")
    row_real = QueueRow(job=job_real)
    real_pix = row_real.thumb.pixmap()
    assert real_pix is not None
    assert not real_pix.isNull()
    # The real pixmap should not equal the placeholder pixmap image bytes
    assert real_pix.toImage() != ph_pix.toImage()


def test_queue_row_thumbnail_not_saved_shows_placeholder(qapp, tmp_path: Path, monkeypatch):
    import app.core.thumbnails as thumb_mod
    monkeypatch.setattr(thumb_mod, "THUMBS_DIR", tmp_path)

    job = make_test_job(job_id="job_no_thumb", video_id="nothumb1111")
    # Displays placeholder without errors
    row = QueueRow(job=job)
    pix = row.thumb.pixmap()
    assert pix is not None
    assert not pix.isNull()


def test_queue_row_remove_action(qapp, monkeypatch):
    job = make_test_job(job_id="job_rem_1", title="Remove Video")
    manager = get_download_manager("video")
    cancelled_ids = []
    monkeypatch.setattr(manager, "cancel_job", lambda jid: cancelled_ids.append(jid))

    row = QueueRow(job=job, can_remove=True)
    assert row.remove_btn is not None
    row.remove_btn.click()
    assert cancelled_ids == ["job_rem_1"]


def test_queue_row_retry_action(qapp, monkeypatch):
    job = make_test_job(job_id="job_ret_1", title="Retry Video")
    manager = get_download_manager("video")
    retried_ids = []
    monkeypatch.setattr(manager, "retry_job", lambda jid: retried_ids.append(jid))

    row = QueueRow(job=(job, "some error"))
    assert row.retry_btn is not None
    row.retry_btn.click()
    assert retried_ids == ["job_ret_1"]


def test_queue_widget_single_signal_connection(qapp):
    qw = QueueWidget(kind="video")
    refresh_count = 0
    original_refresh = qw.refresh

    # Wrap to count subsequent calls
    def counting_refresh():
        nonlocal refresh_count
        refresh_count += 1
        original_refresh()

    # Reconnect queue_changed to counting_refresh for this test
    qw.manager.queue_changed.disconnect(qw.refresh)
    qw.refresh = counting_refresh
    qw.manager.queue_changed.connect(qw.refresh)

    # Call refresh() 5 times consecutively
    for _ in range(5):
        qw.refresh()
    assert refresh_count == 5

    # Reset counter
    refresh_count = 0
    # Emit 1 queue_changed signal -> assert refresh() is invoked exactly once
    qw.manager.queue_changed.emit()
    assert refresh_count == 1

    # Emit 50 progress signals -> assert 0 queue redraws occur
    job = make_test_job(job_id="dummy_running", kind="video")
    for _ in range(50):
        qw.manager.progress.emit(job, 50.0, "1 MB/s", "00:10", 500, 1000)
    assert refresh_count == 1


def test_strict_tab_isolation_video(qapp):
    video_manager = get_download_manager("video")
    audio_manager = get_download_manager("audio")
    video_manager._waiting_queue.clear()
    video_manager._failed_jobs.clear()
    audio_manager._waiting_queue.clear()
    audio_manager._failed_jobs.clear()

    video_qw = QueueWidget(kind="video")
    audio_job = make_test_job(job_id="audio_job_iso", kind="audio")
    audio_manager._waiting_queue.append(audio_job)
    audio_manager.queue_changed.emit()

    assert not video_qw.isVisible()
    video_qw.refresh()
    assert not video_qw.isVisible()


def test_strict_tab_isolation_audio(qapp):
    video_manager = get_download_manager("video")
    audio_manager = get_download_manager("audio")
    video_manager._waiting_queue.clear()
    video_manager._failed_jobs.clear()
    audio_manager._waiting_queue.clear()
    audio_manager._failed_jobs.clear()

    audio_qw = QueueWidget(kind="audio")
    video_job = make_test_job(job_id="video_job_iso", kind="video")
    video_manager._waiting_queue.append(video_job)
    video_manager.queue_changed.emit()

    assert not audio_qw.isVisible()
    audio_qw.refresh()
    assert not audio_qw.isVisible()


def test_queue_widget_ignores_wrong_kind_without_exception(qapp):
    qw = QueueWidget(kind="video")
    wrong_job = make_test_job(job_id="wrong_kind_job", kind="audio")
    qw.manager._waiting_queue = [wrong_job]
    qw.manager._failed_jobs = {}

    qw.refresh()
    assert not qw.isVisible()


def test_tab_scroll_bounds_with_many_queued_items(qapp):
    from PySide6.QtCore import Qt
    from app.ui.main_window import MainWindow

    video_manager = get_download_manager("video")
    audio_manager = get_download_manager("audio")
    video_manager._waiting_queue.clear()
    video_manager._failed_jobs.clear()
    audio_manager._waiting_queue.clear()
    audio_manager._failed_jobs.clear()

    win = MainWindow()
    win.resize(760, 560)
    win.show()
    QApplication.processEvents()

    initial_height = win.height()

    try:
        for i in range(15):
            job = make_test_job(job_id=f"scroll_vid_{i}", title=f"Video Item {i}")
            video_manager._waiting_queue.append(job)

        video_manager.queue_changed.emit()
        QApplication.processEvents()

        video_tab = win.video_tab
        assert video_tab.scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        # Force Qt to recalculate the container geometry so the scrollbar range updates.
        video_tab.scroll.widget().adjustSize()
        QApplication.processEvents()
        assert video_tab.scroll.verticalScrollBar().maximum() > 0
        assert win.height() == initial_height

        audio_tab = win.audio_tab
        assert audio_tab.scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    finally:
        video_manager._waiting_queue.clear()
        audio_manager._waiting_queue.clear()
        # Emit so QueueWidgets in this window and any future VideoTab/AudioTab
        # that connects to the singleton managers sees 0 items immediately.
        video_manager.queue_changed.emit()
        audio_manager.queue_changed.emit()
        QApplication.processEvents()
        win.tray_icon.hide()
        win.tray_icon.deleteLater()
        win.deleteLater()
        QApplication.processEvents()
