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


def test_apply_dark_title_bar_calls_dwm_and_win11_caption_color():
    from unittest.mock import MagicMock, patch
    import sys
    from app.ui.main_window import apply_dark_title_bar

    # Mock dwmapi
    mock_dwm = MagicMock()
    mock_dwm.DwmSetWindowAttribute.return_value = 0

    # 1. On Windows 11 build (e.g. 22000), should call attr 20 (or 19) AND attr 35 (caption) & 36 (text)
    win11_version = MagicMock(major=10, minor=0, build=22000)
    with patch("ctypes.windll.dwmapi", mock_dwm), \
         patch.object(sys, "getwindowsversion", return_value=win11_version):
        apply_dark_title_bar(1234, is_dark=True)
        attrs_called = [call.args[1].value for call in mock_dwm.DwmSetWindowAttribute.call_args_list]
        assert 20 in attrs_called
        assert 35 in attrs_called
        assert 36 in attrs_called

    # 2. On Windows 10 older build (e.g. 19044), should NOT call attr 35 or 36
    mock_dwm.reset_mock()
    win10_version = MagicMock(major=10, minor=0, build=19044)
    with patch("ctypes.windll.dwmapi", mock_dwm), \
         patch.object(sys, "getwindowsversion", return_value=win10_version):
        apply_dark_title_bar(1234, is_dark=True)
        attrs_called = [call.args[1].value for call in mock_dwm.DwmSetWindowAttribute.call_args_list]
        assert 20 in attrs_called
        assert 35 not in attrs_called
        assert 36 not in attrs_called

    # 3. Never raises even if DwmSetWindowAttribute raises an exception
    mock_dwm.side_effect = RuntimeError("DWM not available")
    apply_dark_title_bar(1234, is_dark=True)  # should not raise


def test_combobox_down_arrow_rule_in_both_themes():
    import re
    from pathlib import Path
    from app.ui.theme import build_qss

    for theme in ("dark", "light"):
        qss = build_qss(theme)
        assert "QComboBox::down-arrow" in qss
        # Match image: url(<path>);
        match = re.search(r"QComboBox::down-arrow\s*\{[^}]*image:\s*url\(([^)]+)\);", qss)
        assert match is not None, f"QComboBox::down-arrow rule missing or malformed for theme {theme}"
        arrow_path = match.group(1).strip("'\"")
        assert Path(arrow_path).exists(), f"Arrow image path does not exist: {arrow_path}"



