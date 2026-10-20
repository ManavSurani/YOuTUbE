"""Tests for Phase 7: Plain Text for Labels that Show Web Data (SEC-01 mitigation)."""

import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.history_db import HistoryItem
from app.core.info_fetcher import VideoInfo
from app.core.jobs import DownloadJob
from app.ui.history_tab import HistoryRowWidget
from app.ui.kit.inline_message import InlineMessage
from app.ui.kit.progress_card import ProgressCard
from app.ui.queue_widget import QueueRow
from app.ui.recent_list import RecentRow
from app.ui.video_tab import MediaInfoCard

_app = QApplication.instance() or QApplication(sys.argv)

HOSTILE_PAYLOAD = '<b>x</b><img src="http://example.invalid/a.png">'


def test_media_info_card_plain_text():
    card = MediaInfoCard()
    info = VideoInfo(
        url="https://youtube.com/watch?v=hostile",
        title=HOSTILE_PAYLOAD,
        channel=HOSTILE_PAYLOAD,
        duration=120,
        duration_str="2:00",
        thumbnail_url="",
        qualities=[("1080p", 1080)],
        filesize_approx=1000000,
    )
    card.set_info(info)
    assert card.title_label.textFormat() == Qt.TextFormat.PlainText
    assert card.meta_label.textFormat() == Qt.TextFormat.PlainText
    assert card.title_label.text() == HOSTILE_PAYLOAD


def test_queue_row_plain_text():
    job = DownloadJob(
        job_id="test_q_1",
        url="https://youtube.com/watch?v=hostile",
        video_id="hostile",
        title=HOSTILE_PAYLOAD,
        channel=HOSTILE_PAYLOAD,
        duration_seconds=60,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind="video",
        quality_label="1080p",
        height=1080,
        audio_format=None,
        output_dir="",
        created_at="2026-10-01T12:00:00Z",
    )
    row = QueueRow(job=job, status_text=HOSTILE_PAYLOAD, status_color="#FFFFFF")
    assert row.title_lbl.textFormat() == Qt.TextFormat.PlainText
    assert row.status_lbl.textFormat() == Qt.TextFormat.PlainText
    assert row.meta_lbl.textFormat() == Qt.TextFormat.PlainText
    assert row.title_lbl.text() == HOSTILE_PAYLOAD
    assert row.status_lbl.text() == HOSTILE_PAYLOAD


def test_recent_row_plain_text():
    item = HistoryItem(
        id=1,
        title=HOSTILE_PAYLOAD,
        url="https://youtube.com/watch?v=hostile",
        type="video",
        quality="1080p",
        file_path="",
        size_bytes=1000,
        duration=60,
    )
    row = RecentRow(item=item)
    assert row.title_lbl.textFormat() == Qt.TextFormat.PlainText
    assert row.meta_lbl.textFormat() == Qt.TextFormat.PlainText
    assert row.title_lbl.text() == HOSTILE_PAYLOAD


def test_history_row_plain_text():
    item = HistoryItem(
        id=2,
        title=HOSTILE_PAYLOAD,
        url="https://youtube.com/watch?v=hostile",
        type="video",
        quality="1080p",
        file_path="",
        size_bytes=1000,
        duration=60,
        channel=HOSTILE_PAYLOAD,
    )
    row = HistoryRowWidget(item=item)
    assert row.title_label.textFormat() == Qt.TextFormat.PlainText
    assert row.title_label.text() == HOSTILE_PAYLOAD


def test_progress_card_plain_text():
    card = ProgressCard()
    job = DownloadJob(
        job_id="test_pc_1",
        url="https://youtube.com/watch?v=hostile",
        video_id="hostile",
        title=HOSTILE_PAYLOAD,
        channel=HOSTILE_PAYLOAD,
        duration_seconds=60,
        thumbnail_url="",
        thumbnail_bytes=None,
        kind="video",
        quality_label="1080p",
        height=1080,
        audio_format=None,
        output_dir="",
        created_at="2026-10-01T12:00:00Z",
    )
    card.bind_job(job)
    assert card.title_lbl.textFormat() == Qt.TextFormat.PlainText
    assert card.stage_label.textFormat() == Qt.TextFormat.PlainText
    assert card.percent_label.textFormat() == Qt.TextFormat.PlainText
    assert card.stats_label.textFormat() == Qt.TextFormat.PlainText
    assert card.title_lbl.text() == HOSTILE_PAYLOAD


def test_inline_message_plain_text():
    msg = InlineMessage()
    msg.show_error(HOSTILE_PAYLOAD)
    assert msg._label.textFormat() == Qt.TextFormat.PlainText
    assert msg._label.text() == HOSTILE_PAYLOAD

    msg.show_info(HOSTILE_PAYLOAD)
    assert msg._label.textFormat() == Qt.TextFormat.PlainText
    assert msg._label.text() == HOSTILE_PAYLOAD
