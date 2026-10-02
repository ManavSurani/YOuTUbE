from pathlib import Path
from unittest.mock import patch
import pytest

from app.core.history_db import get_item, list_items, init_db
from app.core.history_service import (
    clear_all,
    delete,
    refresh_file_status,
    relink,
    repair_existing_rows,
    save_from_job,
)
from app.core.info_fetcher import VideoInfo
from app.core.jobs import DownloadJob


@pytest.fixture
def sample_job():
    info = VideoInfo(
        url="https://www.youtube.com/watch?v=service1234",
        title="Service Test Title",
        channel="Test Channel",
        duration=180,
        duration_str="3:00",
        thumbnail_url="",
        qualities=[("1080p", 1080)],
        filesize_approx=10000000,
    )
    return DownloadJob.create(
        info=info,
        kind="video",
        quality_label="1080p",
        height=1080,
        thumbnail_bytes=b"sample_thumbnail_bytes",
    )


def test_save_from_job_and_duplicate(tmp_path: Path, sample_job):
    db_file = tmp_path / "service.db"
    init_db(db_file)

    # Create dummy download file on disk
    download_file = tmp_path / "Service Test Title [service1234].mkv"
    download_file.write_bytes(b"x" * 4096)

    # 1. First save
    item1 = save_from_job(sample_job, str(download_file), custom_db=db_file)
    assert item1.id is not None
    assert item1.size_bytes == 4096
    assert item1.title == "Service Test Title"
    assert item1.video_id == "service1234"

    # 2. Duplicate download (same video_id + kind + quality) with larger file size
    download_file.write_bytes(b"x" * 8192)
    item2 = save_from_job(sample_job, str(download_file), custom_db=db_file)
    assert item2.id == item1.id  # Same row updated!
    assert item2.size_bytes == 8192

    all_rows = list_items(custom_path=db_file)
    assert len(all_rows) == 1  # No duplicate rows created


def test_save_from_job_missing_file_raises(tmp_path: Path, sample_job):
    db_file = tmp_path / "service.db"
    init_db(db_file)
    with pytest.raises(FileNotFoundError):
        save_from_job(sample_job, str(tmp_path / "non_existent.mkv"), custom_db=db_file)


def test_delete_options_and_locked_file(tmp_path: Path, sample_job):
    db_file = tmp_path / "service.db"
    init_db(db_file)

    test_file = tmp_path / "sample.mkv"
    test_file.write_bytes(b"content")

    item = save_from_job(sample_job, str(test_file), custom_db=db_file)

    # 1. Delete with locked file error simulation
    with patch("send2trash.send2trash", side_effect=PermissionError("File locked")):
        ok, err = delete(item.id, delete_file=True, custom_db=db_file)
        assert ok is False
        assert "open in another program" in err
        # Row must still exist!
        assert get_item(item.id, custom_path=db_file) is not None
        assert test_file.exists()

    # 2. Normal delete without deleting file
    ok, err = delete(item.id, delete_file=False, custom_db=db_file)
    assert ok is True
    assert get_item(item.id, custom_path=db_file) is None
    assert test_file.exists()  # File kept on disk!


def test_relink_and_refresh_file_status(tmp_path: Path, sample_job):
    db_file = tmp_path / "service.db"
    init_db(db_file)

    file_a = tmp_path / "original.mkv"
    file_a.write_bytes(b"AAA")

    item = save_from_job(sample_job, str(file_a), custom_db=db_file)
    assert item.file_missing == 0

    # Delete original file
    file_a.unlink()

    # Refresh file status should mark file_missing = 1
    missing_count = refresh_file_status(custom_db=db_file)
    assert missing_count == 1
    reloaded = get_item(item.id, custom_path=db_file)
    assert reloaded.file_missing == 1

    # Relink to a new file
    file_b = tmp_path / "relocated.mkv"
    file_b.write_bytes(b"BBBBBB")

    ok, err = relink(item.id, str(file_b), custom_db=db_file)
    assert ok is True
    reloaded2 = get_item(item.id, custom_path=db_file)
    assert reloaded2.file_path == str(file_b.resolve())
    assert reloaded2.size_bytes == 6
    assert reloaded2.file_missing == 0


def test_repair_existing_rows(tmp_path: Path):
    db_file = tmp_path / "service.db"
    init_db(db_file)

    # Add row with 0 bytes and broken path (like from the user's screenshot)
    from app.core.history_db import add_item, HistoryItem
    broken_item = HistoryItem(
        id=None,
        title="Hal Jordan Reacts",
        url="https://www.youtube.com/watch?v=Bm4XryaNzYg",
        type="video",
        quality="1080p",
        file_path="C:/Downloads/non_existent.mkv",
        size_bytes=0,
        duration=1200,
        video_id="Bm4XryaNzYg",
        file_missing=1,
    )
    row_id = add_item(broken_item, custom_path=db_file)

    # Place real file in download folder with [Bm4XryaNzYg] in filename
    dl_dir = tmp_path / "Downloads"
    dl_dir.mkdir()
    real_file = dl_dir / "Hal Jordan Reacts [Bm4XryaNzYg].mkv"
    real_file.write_bytes(b"x" * 2048)

    repaired = repair_existing_rows(download_dir=dl_dir, custom_db=db_file)
    assert repaired == 1

    item_after = get_item(row_id, custom_path=db_file)
    assert item_after.file_path == str(real_file.resolve())
    assert item_after.size_bytes == 2048
    assert item_after.file_missing == 0
