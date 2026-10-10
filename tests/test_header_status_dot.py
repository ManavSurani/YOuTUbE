"""Regression tests for AnimatedStatusDot _start_color fix (P3)."""

from PySide6.QtWidgets import QApplication
import pytest

from app.ui.header import AnimatedStatusDot


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_status_dot_paints_mid_animation_without_start_color_error():
    dot = AnimatedStatusDot()
    dot._progress = 0.5  # mid-animation: paintEvent now needs _start_color
    dot.grab()  # must not raise AttributeError


def test_status_dot_survives_online_offline_switches():
    dot = AnimatedStatusDot()
    dot.set_online(False)
    dot.grab()
    dot.set_online(True)
    dot.grab()
