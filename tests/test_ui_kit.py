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
