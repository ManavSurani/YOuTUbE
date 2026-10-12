"""Unit tests for Phase 3 UI Kit components and Header."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication
import pytest

from app.ui.header import Header, create_gear_icon
from app.ui.kit import (
    AnimatedButton,
    AnimatedCheckBox,
    InlineMessage,
    ProgressCard,
    ThumbLabel,
    Toast,
)


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_animated_button_roles_and_states():
    btn = AnimatedButton("Download", role="primary")
    assert btn.role == "primary"
    assert btn.height() == 36

    # Test loading state
    btn.set_loading(True)
    assert not btn.isEnabled()
    assert btn._is_loading is True

    btn.set_loading(False)
    assert btn.isEnabled()
    assert btn._is_loading is False

    # Test flash success
    btn.flash_success(duration_ms=500)
    assert btn._is_success is True


def test_animated_checkbox_toggle():
    cb = AnimatedCheckBox("Include audio track")
    assert not cb.isChecked()
    assert cb.check_progress == 0.0

    cb.setChecked(True)
    assert cb.isChecked()
    assert cb.check_progress == 1.0

    cb.setChecked(False)
    assert not cb.isChecked()
    assert cb.check_progress == 0.0


def test_inline_message_lifecycle():
    msg = InlineMessage()
    assert not msg.isVisible()

    msg.show_error("Could not fetch info", auto_hide_ms=0)
    assert msg.isVisible()
    assert "Could not fetch info" in msg.text()

    msg.clear()
    assert not msg.isVisible()
    assert msg.text() == ""


def test_toast_creation():
    toast = Toast("File moved to Recycle Bin", action_text="Undo")
    assert toast.height() == 48


def test_header_tab_switching():
    header = Header()
    assert header.height() == 52

    received_tabs = []
    header.tab_changed.connect(lambda idx: received_tabs.append(idx))

    # Switch to Audio tab (index 1)
    header.select_tab(1)
    assert 1 in received_tabs
    assert header._current_tab == 1

    # Switch to History tab (index 2)
    header.select_tab(2)
    assert 2 in received_tabs
    assert header._current_tab == 2

    # Network status update
    header.set_online(False)
    assert header.status_label.text() == "Offline"
    header.set_online(True)
    assert header.status_label.text() == "Online"


def test_thumb_label_fallback():
    label = ThumbLabel(video_id="nonexistent11", is_audio=False)
    pix = label.pixmap()
    assert pix is not None
    assert not pix.isNull()
    assert pix.width() == 64
    assert pix.height() == 36


def test_progress_card_updates():
    card = ProgressCard()
    card.set_stage("Downloading video")
    assert card.stage_label.text() == "Downloading video"

    card.set_progress(55.0, speed="10 MB/s", eta="00:30", stats="50 / 100 MB")
    assert card.progress_bar.value() == 55
    assert card.percent_label.text() == "55%"
    assert "10 MB/s" in card.stats_label.text()


def test_progress_card_collapses_after_done():
    card = ProgressCard()
    card.show_done(out_dir="C:/Downloads")
    assert card.progress_bar.value() == 100
    assert card.isVisible()

    assert hasattr(card, "_collapse_timer")
    assert card._collapse_timer.isActive()

    card._collapse_timer.timeout.emit()
    assert not card.isVisible()
    assert card._active_job is None


def test_progress_card_bind_new_job_cancels_collapse_timer():
    card = ProgressCard()
    card.show_done(out_dir="C:/Downloads")
    assert hasattr(card, "_collapse_timer")
    assert card._collapse_timer.isActive()

    from app.core.info_fetcher import VideoInfo
    from app.core.jobs import DownloadJob
    info = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="New Song",
        channel="Channel",
        duration=120,
        duration_str="2:00",
        thumbnail_url="",
        qualities=[("1080p", 1000)],
        filesize_approx=1000,
    )
    job = DownloadJob.create(info=info, kind="video", quality_label="1080p", output_dir="C:/Downloads")
    card.bind_job(job)

    assert not card._collapse_timer.isActive()
    assert card.isVisible()
    assert card.title_lbl.text() == "New Song"


def test_gear_icon_outline_not_null_and_non_empty():
    from app.ui.header import create_gear_icon
    for sz in (16, 32):
        icon = create_gear_icon(size=sz)
        assert not icon.isNull()
        pix = icon.pixmap(sz, sz)
        assert not pix.isNull()
        img = pix.toImage()
        assert not img.isNull()
        # Pixmap is not empty
        has_colored_pixels = any(
            img.pixelColor(x, y).alpha() > 0
            for y in range(sz)
            for x in range(sz)
        )
        assert has_colored_pixels

    # Verify outline style: at size 32, annular region between hole (r~5) and teeth (r~10) is hollow
    icon32 = create_gear_icon(size=32)
    img32 = icon32.pixmap(32, 32).toImage()
    # At (16 + 7, 16) = (23, 16), in the old spoke implementation this was right on a spoke line.
    # In an outline gear with separate center hole and cog perimeter, the annular ring is hollow.
    assert img32.pixelColor(23, 16).alpha() == 0


def test_progress_card_new_job_increasing():
    # 1. A new job (after bind_job): 0 -> 0 -> small values -> increasing values shows increasing values as before.
    from app.core.jobs import DownloadJob

    card = ProgressCard()
    job = DownloadJob(
        job_id="job_inc",
        url="https://youtube.com/watch?v=12345678901",
        video_id="12345678901",
        title="Test Inc",
        channel="Channel",
        duration_seconds=60,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind="video",
        quality_label="1080p",
        height=1080,
        audio_format=None,
        output_dir="",
        created_at="2026-10-12T00:00:00",
    )
    card.bind_job(job)
    assert card.progress_bar.value() == 0
    assert card.percent_label.text() == "0%"

    # (downloaded=0, estimate=0) - invented: startup zeros
    card.set_progress(0.0)
    assert card.progress_bar.value() == 0
    assert card.percent_label.text() == "0%"

    # (downloaded=0, estimate=104857600) - invented: initial estimate before dl
    card.set_progress(0.0)
    assert card.progress_bar.value() == 0
    assert card.percent_label.text() == "0%"

    # (downloaded=524288, estimate=104857600) -> 0.5% (scaled 0.42%) - invented: small initial chunk
    card.set_progress(0.42)
    assert card.progress_bar.value() == 0  # int(0.42) == 0
    assert card.percent_label.text() == "0%"

    # (downloaded=5242880, estimate=104857600) -> 5.0% (scaled 4.25%) - invented: small chunk
    card.set_progress(4.25)
    assert card.progress_bar.value() == 4
    assert card.percent_label.text() == "4%"

    # (downloaded=20971520, estimate=104857600) -> 20.0% (scaled 17.0%) - invented: progressive chunk
    card.set_progress(17.0)
    assert card.progress_bar.value() == 17
    assert card.percent_label.text() == "17%"

    # (downloaded=62914560, estimate=104857600) -> 60.0% (scaled 51.0%) - invented: progressive chunk
    card.set_progress(51.0)
    assert card.progress_bar.value() == 51
    assert card.percent_label.text() == "51%"


def test_progress_card_spike_and_self_correction():
    # 2. Early spike then self-correction: 0 -> 80.4 -> 0.53 -> 0.11 shows 80, then 0 (int of 0.53), then 0.
    # Assert the bar AND the percent label follow the lower values.
    card = ProgressCard()
    # (downloaded=0, estimate=0) - invented: starting reading
    card.set_progress(0.0)
    assert card.progress_bar.value() == 0
    assert card.percent_label.text() == "0%"

    # (downloaded=712, estimate=712) -> 80.4% - from audit report: Trigger B fragment spike
    card.set_progress(80.4)
    assert card.progress_bar.value() == 80
    assert card.percent_label.text() == "80%"

    # (downloaded=1148846, estimate=220200960) -> 0.53% - from app.log.2 / audit report: early fragment estimate correction
    card.set_progress(0.53)
    assert card.progress_bar.value() == 0
    assert card.percent_label.text() == "0%"

    # (downloaded=276480, estimate=1492528128) -> 0.11% - from app.log.2 / audit report: multi-GB stream estimate correction
    card.set_progress(0.11)
    assert card.progress_bar.value() == 0
    assert card.percent_label.text() == "0%"


def test_progress_card_resume_noise_keeps_progress():
    # 3. Resume noise: 40 -> set_progress(0.0, "", "", 0, 0) keeps the bar at 40.
    card = ProgressCard()
    # (downloaded=40000000, estimate=100000000) -> 40.0% - invented: progress before offline pause
    card.set_progress(40.0, speed="5.2 MB/s", eta="00:15", done_bytes=40000000, total_bytes=100000000)
    assert card.progress_bar.value() == 40
    assert card.percent_label.text() == "40%"

    # (downloaded=0, estimate=0) -> 0.0% - from app.log.1: early startup noise / empty emit on resume
    card.set_progress(0.0, "", "", 0, 0)
    assert card.progress_bar.value() == 40
    assert card.percent_label.text() == "40%"


def test_progress_card_normal_increasing_sequence():
    # 4. Normal increasing sequence 1, 20, 40, 60, 100 shows increasing values.
    card = ProgressCard()
    # (downloaded=1048576, estimate=104857600) -> 1.0% - invented: 1% progress
    card.set_progress(1.0)
    assert card.progress_bar.value() == 1
    assert card.percent_label.text() == "1%"

    # (downloaded=20971520, estimate=104857600) -> 20.0% - invented: 20% progress
    card.set_progress(20.0)
    assert card.progress_bar.value() == 20
    assert card.percent_label.text() == "20%"

    # (downloaded=41943040, estimate=104857600) -> 40.0% - invented: 40% progress
    card.set_progress(40.0)
    assert card.progress_bar.value() == 40
    assert card.percent_label.text() == "40%"

    # (downloaded=62914560, estimate=104857600) -> 60.0% - invented: 60% progress
    card.set_progress(60.0)
    assert card.progress_bar.value() == 60
    assert card.percent_label.text() == "60%"

    # (downloaded=104857600, total=104857600) -> 100.0% - real from app.log.1: 100% completion
    card.set_progress(100.0)
    assert card.progress_bar.value() == 100
    assert card.percent_label.text() == "100%"


def test_resume_dual_stream_in_audio_stage_progress_drop(monkeypatch):
    """Simulates a dual-stream job resumed in the audio stage:
    1. Card was at 85% before.
    2. A new worker starts with floor_percent=85.0, video stream skipped by yt-dlp, first audio line has 10 KB of ~97 MB.
    3. With floor_percent=85.0, emitted percent stays at 85.0%, preserving 85% on card.
    """
    card = ProgressCard()
    # Before resume: video completed, card at 85%
    card.set_progress(85.0, speed="5 MB/s", eta="00:10", done_bytes=425000000, total_bytes=500000000)
    assert card.progress_bar.value() == 85
    assert card.percent_label.text() == "85%"

    # New worker receives first audio line with 10 KB of 97,370,030 B
    lines = [
        "[download] YTPROG|downloading|10000|97370030|NA|5000000|20|none|opus\n"
    ]

    class FakeProc:
        def __init__(self, out):
            self.stdout = out
            self.returncode = 0
        def wait(self): pass

    monkeypatch.setattr("app.core.downloader.start_hidden", lambda cmd: FakeProc(lines))

    from app.core.downloader import DownloadWorker
    # Manager passes floor_percent=85.0 when resuming
    worker = DownloadWorker(["dummy"], is_dual_stream=True, job_id="test-resume-audio", duration_seconds=0, floor_percent=85.0)
    emitted = []
    worker.progress.connect(lambda pct, spd, eta, done, tot: emitted.append((pct, spd, eta, done, tot)))
    worker.run()

    # First emitted audio reading is held at floor 85.0%
    first_pct, spd, eta, done, tot = emitted[0]
    assert first_pct >= 85.0, f"Expected >= 85.0%, got {first_pct}%"

    card.set_progress(first_pct, speed=spd, eta=eta, done_bytes=done, total_bytes=tot)

    # Bar value and label preserved at 85%
    assert card.progress_bar.value() == 85
    assert card.percent_label.text() == "85%"


def test_progress_card_sticky_numbers_survive_empty_update():
    card = ProgressCard()
    # Initial good update: 50 MB / 100 MB at 10 MB/s, ETA 00:30
    card.set_progress(50.0, speed="10 MB/s", eta="00:30", done_bytes=52428800, total_bytes=104857600)
    assert card.stats_label.text() == "10 MB/s • 50.0 MB / 100.0 MB • ETA 00:30"

    # Empty update arrives (e.g. sporadic yt-dlp pulse or intermediate step)
    card.set_progress(50.0, speed="", eta="", done_bytes=0, total_bytes=0)
    # Sticky numbers must survive
    assert card.stats_label.text() == "10 MB/s • 50.0 MB / 100.0 MB • ETA 00:30"


def test_progress_card_total_smaller_than_done_shows_done_slash_done():
    card = ProgressCard()
    # total_bytes (40 MB) is smaller than done_bytes (50 MB)
    card.set_progress(90.0, speed="5 MB/s", eta="00:05", done_bytes=52428800, total_bytes=41943040)
    # Expected: max(total, done) makes total 50 MB -> "50.0 MB / 50.0 MB"
    assert "50.0 MB / 50.0 MB" in card.stats_label.text()


def test_progress_card_stage_change_preserves_numbers():
    card = ProgressCard()
    card.set_progress(50.0, speed="10 MB/s", eta="00:30", done_bytes=52428800, total_bytes=104857600)
    text_before = card.stats_label.text()
    assert text_before == "10 MB/s • 50.0 MB / 100.0 MB • ETA 00:30"

    card.set_stage("Downloading audio")
    assert card.stage_label.text() == "Downloading audio"
    # stats_label must not be reset or cleared on stage change
    assert card.stats_label.text() == text_before
    assert card._last_done == 52428800
    assert card._last_total == 104857600
    assert card._last_speed == "10 MB/s"


def test_progress_card_three_slots_always_present():
    card = ProgressCard()
    card.set_progress(0.0)
    # With no readings yet, all three slots are present with placeholders
    assert card.stats_label.text() == "-- MB/s • calculating… • ETA --:--"

    # Partial reading: only speed
    card.set_progress(0.0, speed="2.5 MB/s")
    assert card.stats_label.text() == "2.5 MB/s • calculating… • ETA --:--"

    # Partial reading: stats override
    card.set_progress(10.0, stats="10 / 100 MB")
    assert card.stats_label.text() == "2.5 MB/s • 10 / 100 MB • ETA --:--"


def test_progress_card_reset_clears_sticky_state():
    card = ProgressCard()
    card.set_progress(50.0, speed="10 MB/s", eta="00:30", done_bytes=52428800, total_bytes=104857600)
    assert card._last_done == 52428800
    assert card._last_total == 104857600
    assert card._last_speed == "10 MB/s"
    assert card._last_eta == "00:30"

    card.reset()
    assert card._last_done == 0
    assert card._last_total == 0
    assert card._last_speed == ""
    assert card._last_eta == ""
    assert card.stats_label.text() == ""

    # Also test bind_job resets sticky state
    card.set_progress(50.0, speed="10 MB/s", eta="00:30", done_bytes=52428800, total_bytes=104857600)
    from app.core.jobs import DownloadJob
    job = DownloadJob(
        job_id="job_reset",
        url="https://youtube.com/watch?v=12345678901",
        video_id="12345678901",
        title="Test Reset",
        channel="Channel",
        duration_seconds=60,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind="video",
        quality_label="1080p",
        height=1080,
        audio_format=None,
        output_dir="",
        created_at="2026-10-12T00:00:00",
    )
    card.bind_job(job)
    assert card._last_done == 0
    assert card._last_total == 0
    assert card._last_speed == ""
    assert card._last_eta == ""
    assert card.stats_label.text() == ""


def test_progress_card_explicit_stats_overrides_byte_totals():
    card = ProgressCard()
    card.set_progress(50.0, speed="5 MB/s", eta="00:10", done_bytes=50000000, total_bytes=100000000, stats="Custom / String")
    assert card.stats_label.text() == "5 MB/s • Custom / String • ETA 00:10"


def test_animated_checkbox_size_hint_reserves_ring_margin():
    cb_empty = AnimatedCheckBox("")
    assert cb_empty.sizeHint().width() == 24
    assert cb_empty.sizeHint().height() == 24

    cb_text = AnimatedCheckBox("Include audio track")
    text_w = cb_text.fontMetrics().horizontalAdvance("Include audio track")
    assert cb_text.sizeHint().width() == 24 + 8 + text_w
    assert cb_text.sizeHint().height() == 24


def test_animated_checkbox_focus_ring_unclipped_dark_and_light():
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QApplication
    from app.ui.theme import build_qss

    app = QApplication.instance() or QApplication([])
    for w in app.topLevelWidgets():
        if hasattr(w, "close"):
            w.close()
    app.processEvents()

    for theme_name in ("dark", "light"):
        app.setStyleSheet(build_qss(theme_name))
        win = QDialog()
        layout = QVBoxLayout(win)
        cb = AnimatedCheckBox("Include audio track", win)
        layout.addWidget(cb)
        win.show()
        win.activateWindow()
        cb.setFocus()
        app.processEvents()

        assert cb.hasFocus() is True
        img = cb.grab().toImage()

        # Ring pixels in column 1 (x=1) must contain the full vertical line segment (at least 10 px)
        # and match the drawn blue color #3EA6FF
        col1_blue_y = [
            y for y in range(img.height())
            if img.pixelColor(1, y).blue() > 200 and img.pixelColor(1, y).red() < 100
        ]
        assert len(col1_blue_y) >= 10, f"Theme {theme_name}: expected >= 10 ring pixels in col 1, got {len(col1_blue_y)}"
        assert any(img.pixelColor(1, y).name().upper() == "#3EA6FF" for y in range(img.height())), (
            f"Theme {theme_name}: expected #3EA6FF in column 1"
        )
        win.close()
        app.processEvents()


def test_animated_checkbox_clicking_text_toggles():
    from PySide6.QtTest import QTest
    from PySide6.QtCore import QPoint

    cb = AnimatedCheckBox("Include audio track")
    cb.resize(cb.sizeHint())
    cb.show()
    assert not cb.isChecked()

    # Click on the text portion (near right side)
    text_click_pos = QPoint(cb.width() - 5, cb.height() // 2)
    QTest.mouseClick(cb, Qt.MouseButton.LeftButton, pos=text_click_pos)
    assert cb.isChecked()

    QTest.mouseClick(cb, Qt.MouseButton.LeftButton, pos=text_click_pos)
    assert not cb.isChecked()








