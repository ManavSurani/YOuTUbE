"""Tests for Phase 5 tab look and feel: transparency, alignment, progress bar, flat rows, animated buttons."""

from PySide6.QtCore import QPoint, QPropertyAnimation, Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
import pytest

from app.core.jobs import DownloadJob
from app.ui.kit.progress_card import ProgressCard
from app.ui.theme import build_qss, DARK_TOKENS
from app.ui.video_tab import VideoTab
from app.ui.audio_tab import AudioTab


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    app.setStyleSheet(build_qss("dark"))
    yield app


def _check_tab_background_transparency(TabClass):
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QScrollArea

    tab = TabClass()
    tab.resize(800, 600)

    # 1. Structure check: scroll area and inner container are transparent
    scroll = tab.findChild(QScrollArea)
    assert scroll is not None
    assert "background: transparent" in scroll.styleSheet()
    assert "background: transparent" in scroll.viewport().styleSheet()
    assert "background: transparent" in scroll.widget().styleSheet()

    # 2. Pixel test: empty area allows window background (#0F0F0F) to shine through
    img = QImage(800, 600, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(DARK_TOKENS["bg"]))
    tab.render(img, renderFlags=QWidget.RenderFlag.DrawChildren)
    color = img.pixelColor(700, 550).name().upper()
    assert color == DARK_TOKENS["bg"].upper()
    return color


def test_video_tab_background_matches_theme():
    _check_tab_background_transparency(VideoTab)


def test_audio_tab_background_matches_theme():
    _check_tab_background_transparency(AudioTab)


def test_progress_card_aligned_with_url_input():
    tab = VideoTab()
    tab.resize(800, 600)
    tab.progress_card.setVisible(True)
    tab.layout().activate()

    url_x = tab.url_input.mapTo(tab, QPoint(0, 0)).x()
    card_stage_x = tab.progress_card.stage_label.mapTo(tab, QPoint(0, 0)).x()
    assert card_stage_x == url_x


def test_progress_card_flat_no_background():
    card = ProgressCard()
    assert "#1A1A1A" not in card.styleSheet()


def test_progress_bar_height_is_10():
    card = ProgressCard()
    assert card.progress_bar.maximumHeight() == 10


def test_progress_card_animation_stops_when_hidden():
    card = ProgressCard()
    job = DownloadJob(
        job_id="test1",
        url="https://youtube.com/watch?v=12345678901",
        video_id="12345678901",
        title="Testing Animation",
        channel="Test Channel",
        duration_seconds=60,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind="video",
        quality_label="1080p",
        height=1080,
        audio_format=None,
        output_dir="",
        created_at="2026-10-04T00:00:00",
    )
    card.bind_job(job)
    assert hasattr(card, "highlight_anim")
    assert card.highlight_anim.state() == QPropertyAnimation.State.Running

    card.hide()
    assert card.highlight_anim.state() != QPropertyAnimation.State.Running


def test_recent_row_flat_and_uses_icon_buttons(tmp_path):
    from app.core.history_db import HistoryItem
    from app.ui.kit.buttons import IconButton
    from app.ui.recent_list import RecentRow
    from PySide6.QtWidgets import QPushButton

    dummy_file = tmp_path / "song.mp3"
    dummy_file.write_bytes(b"content")

    item = HistoryItem(
        id=1,
        title="Test Song",
        url="https://youtube.com/watch?v=12345678901",
        type="audio",
        quality="MP3",
        file_path=str(dummy_file),
        size_bytes=1024,
        file_missing=0,
    )

    row = RecentRow(item)

    # Flat style with hover highlight only
    assert "RecentRow:hover" in row.styleSheet()

    # Exactly two IconButtons
    icon_btns = row.findChildren(IconButton)
    assert len(icon_btns) == 2

    # No plain QPushButtons
    plain_btns = [b for b in row.findChildren(QPushButton) if type(b) is QPushButton]
    assert len(plain_btns) == 0


def test_scan_no_plain_qpushbutton():
    from pathlib import Path

    files = [
        Path("app/ui/queue_widget.py"),
        Path("app/ui/video_tab.py"),
        Path("app/ui/audio_tab.py"),
        Path("app/ui/recent_list.py"),
    ]
    # Allowed exceptions: explicitly listed link-style buttons
    allowed_exceptions = {
        "app/ui/recent_list.py": ["QPushButton(link_text, self)"],
    }

    violations = []
    for f in files:
        lines = f.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, 1):
            if "QPushButton(" in line:
                is_allowed = False
                for allowed in allowed_exceptions.get(f.as_posix(), []):
                    if allowed in line:
                        is_allowed = True
                        break
                if not is_allowed:
                    violations.append(f"{f.as_posix()}:{idx}: {line.strip()}")

    assert not violations, f"Found unexpected QPushButton usages: {violations}"

