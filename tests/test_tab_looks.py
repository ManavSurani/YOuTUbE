"""Tests for Phase 5 tab look and feel: transparency, alignment, progress bar, flat rows, animated buttons."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
import pytest

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


def _sample_tab_pixel(TabClass):
    parent = QWidget()
    parent.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    parent.setObjectName("centralWidget")
    parent.resize(800, 600)
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(0, 0, 0, 0)
    tab = TabClass(parent)
    layout.addWidget(tab)
    parent.show()
    QApplication.processEvents()

    pix = parent.grab()
    img = pix.toImage()
    # Sample in an empty area near bottom right
    color = img.pixelColor(700, 550).name().upper()
    return color


def test_video_tab_background_matches_theme():
    color = _sample_tab_pixel(VideoTab)
    assert color == DARK_TOKENS["bg"].upper()


def test_audio_tab_background_matches_theme():
    color = _sample_tab_pixel(AudioTab)
    assert color == DARK_TOKENS["bg"].upper()
