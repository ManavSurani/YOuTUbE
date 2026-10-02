from app.core.jobs import DownloadJob
from app.core.info_fetcher import VideoInfo
import pytest


def test_download_job_snapshot_immutability():
    info = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
        title="Never Gonna Give You Up",
        channel="Rick Astley",
        duration=212,
        duration_str="3:32",
        thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        qualities=[("1080p", 1080)],
        filesize_approx=50000000,
    )

    job = DownloadJob.create(
        info=info,
        kind="video",
        quality_label="1080p",
        height=1080,
        output_dir="C:/Downloads",
        thumbnail_bytes=b"fake_image_bytes",
    )

    assert job.video_id == "dQw4w9WgXcQ"
    assert job.title == "Never Gonna Give You Up"
    assert job.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert job.channel == "Rick Astley"
    assert job.duration_seconds == 212
    assert job.thumbnail_bytes == b"fake_image_bytes"
    assert job.quality_label == "1080p"
    assert job.kind == "video"

    # Mutating original info does not alter job
    info.title = "Changed Title"
    info.url = "https://other.com"
    assert job.title == "Never Gonna Give You Up"
    assert job.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_download_job_rejects_empty_or_url_title():
    info_empty = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="",
        channel="Rick",
        duration=100,
        duration_str="1:40",
        thumbnail_url="",
        qualities=[],
        filesize_approx=0,
    )
    with pytest.raises(ValueError):
        DownloadJob.create(info_empty, kind="video", quality_label="Best")

    info_url_title = VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        channel="Rick",
        duration=100,
        duration_str="1:40",
        thumbnail_url="",
        qualities=[],
        filesize_approx=0,
    )
    with pytest.raises(ValueError):
        DownloadJob.create(info_url_title, kind="video", quality_label="Best")
