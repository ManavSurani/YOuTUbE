import json
from pathlib import Path
import pytest
from app.core.info_fetcher import (
    build_quality_list,
    format_quality_label,
    format_duration,
    fetch_info,
    VideoInfo,
)


def test_format_quality_label():
    assert format_quality_label(4320) == "8K"
    assert format_quality_label(2160) == "4K"
    assert format_quality_label(1440) == "2K"
    assert format_quality_label(1080) == "1080p"
    assert format_quality_label(720) == "720p"
    assert format_quality_label(360) == "360p"


def test_format_duration():
    assert format_duration(65) == "1:05"
    assert format_duration(3665) == "1:01:05"
    assert format_duration(0) == ""


def test_build_quality_list_with_8k():
    formats = [
        {"height": 720, "vcodec": "avc1"},
        {"height": 1080, "vcodec": "avc1"},
        {"height": 4320, "vcodec": "vp9"},
        {"height": 2160, "vcodec": "vp9"},
        {"vcodec": "none", "acodec": "opus"},  # audio-only format
    ]
    qualities = build_quality_list(formats)
    # Check "Best available (8K)" is first
    assert qualities[0] == ("Best available (8K)", None)
    labels = [q[0] for q in qualities]
    assert labels == ["Best available (8K)", "8K", "4K", "1080p", "720p"]
    # Verify no audio-only / None height entries in subsequent items
    heights = [q[1] for q in qualities[1:]]
    assert heights == [4320, 2160, 1080, 720]


def test_build_quality_list_audio_only():
    formats = [
        {"vcodec": "none", "acodec": "opus"},
        {"vcodec": "none", "acodec": "mp4a"},
    ]
    qualities = build_quality_list(formats)
    assert qualities == [("Best available", None)]


def test_build_quality_list_from_sample_info():
    sample_path = Path("tests/sample_info.json")
    if sample_path.exists():
        data = json.loads(sample_path.read_text(encoding="utf-8"))
        formats = data.get("formats", [])
        qualities = build_quality_list(formats)
        assert len(qualities) >= 1
        assert qualities[0][0].startswith("Best available")


def test_fetch_info_timeout_or_invalid():
    with pytest.raises(RuntimeError):
        fetch_info("https://www.youtube.com/watch?v=invalid_id_9999", timeout=5.0)
