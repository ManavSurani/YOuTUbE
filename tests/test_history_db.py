from pathlib import Path
import sqlite3
import pytest

from app.core.history_db import (
    init_db,
    add_item,
    update_item,
    list_items,
    get_item,
    delete_item,
    find_duplicate,
    maybe_backup_db,
    HistoryItem,
)


def test_init_db_and_version(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    assert not db_file.exists()
    init_db(db_file)
    assert db_file.exists()

    with sqlite3.connect(str(db_file)) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version;")
        ver = cursor.fetchone()[0]
        assert ver == 1


def test_migration_from_v0_schema(tmp_path: Path):
    """Test upgrading an existing v0 database to v1 adds new columns without losing rows."""
    db_file = tmp_path / "legacy.db"
    with sqlite3.connect(str(db_file)) as conn:
        conn.execute(
            """
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                type TEXT NOT NULL,
                quality TEXT NOT NULL,
                file_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                duration INTEGER NOT NULL,
                thumbnail_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO history (title, url, type, quality, file_path, size_bytes, duration)
            VALUES ('Legacy Video', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'video', '1080p', 'C:/v.mkv', 1000, 210)
            """
        )
        conn.commit()

    # Run init_db which triggers migration
    init_db(db_file)

    items = list_items(custom_path=db_file)
    assert len(items) == 1
    assert items[0].title == "Legacy Video"
    # Column video_id should be backfilled from url
    assert items[0].video_id == "dQw4w9WgXcQ"
    assert items[0].file_missing == 0


def test_add_item_validation(tmp_path: Path):
    db_file = tmp_path / "val_history.db"

    # Missing file_path must raise ValueError
    with pytest.raises(ValueError, match="file_path is empty"):
        add_item(HistoryItem(None, "Valid Title", "https://youtube.com/watch?v=11111111111", "video", "1080p", "", 1000, 60), db_file)

    # Title equals URL must raise ValueError
    url = "https://youtube.com/watch?v=11111111111"
    with pytest.raises(ValueError, match="title is invalid or equals URL"):
        add_item(HistoryItem(None, url, url, "video", "1080p", "C:/path.mkv", 1000, 60), db_file)

    # Empty title must raise ValueError
    with pytest.raises(ValueError, match="title is invalid or equals URL"):
        add_item(HistoryItem(None, "   ", url, "video", "1080p", "C:/path.mkv", 1000, 60), db_file)


def test_add_and_list_newest_first(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    item1 = HistoryItem(None, "Video One", "https://youtube.com/watch?v=11111111111", "video", "1080p", "C:/Downloads/1.mkv", 1000, 60)
    item2 = HistoryItem(None, "Audio Two", "https://youtube.com/watch?v=22222222222", "audio", "MP3", "C:/Downloads/2.mp3", 500, 120)
    item3 = HistoryItem(None, "Video Three", "https://youtube.com/watch?v=33333333333", "video", "4K", "C:/Downloads/3.mkv", 2000, 180)

    id1 = add_item(item1, db_file)
    id2 = add_item(item2, db_file)
    id3 = add_item(item3, db_file)

    items = list_items(custom_path=db_file)
    assert len(items) == 3
    assert items[0].id == id3
    assert items[1].id == id2
    assert items[2].id == id1


def test_find_duplicate_and_update(tmp_path: Path):
    db_file = tmp_path / "dup_history.db"
    item = HistoryItem(
        id=None,
        title="Sample Video",
        url="https://youtube.com/watch?v=testvid1234",
        type="video",
        quality="1080p",
        file_path="C:/v1.mkv",
        size_bytes=1000,
        duration=120,
        video_id="testvid1234",
    )
    row_id = add_item(item, db_file)

    dup = find_duplicate("testvid1234", "video", "1080p", custom_path=db_file)
    assert dup is not None
    assert dup.id == row_id

    # Update item
    dup.file_path = "C:/v2_updated.mkv"
    dup.size_bytes = 2500
    assert update_item(dup, custom_path=db_file) is True

    updated = get_item(row_id, custom_path=db_file)
    assert updated.file_path == "C:/v2_updated.mkv"
    assert updated.size_bytes == 2500


def test_daily_backup(tmp_path: Path):
    db_file = tmp_path / "history" / "history.db"
    db_file.parent.mkdir(parents=True)
    init_db(db_file)

    maybe_backup_db(db_file)
    backup_dir = db_file.parent / "backups"
    assert backup_dir.is_dir()
    backups = list(backup_dir.glob("history_*.bak"))
    assert len(backups) >= 1
