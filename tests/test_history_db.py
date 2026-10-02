from pathlib import Path
from app.core.history_db import (
    init_db,
    add_item,
    list_items,
    get_item,
    delete_item,
    HistoryItem,
)


def test_init_db(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    assert not db_file.exists()
    init_db(db_file)
    assert db_file.exists()


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
    # Check newest first
    assert items[0].id == id3
    assert items[1].id == id2
    assert items[2].id == id1


def test_filter_by_type_and_search(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    add_item(HistoryItem(None, "Python Tutorial", "https://youtube.com/watch?v=11111111111", "video", "1080p", "path1", 100, 10), db_file)
    add_item(HistoryItem(None, "Relaxing Music", "https://youtube.com/watch?v=22222222222", "audio", "MP3", "path2", 200, 20), db_file)
    add_item(HistoryItem(None, "Advanced Python", "https://youtube.com/watch?v=33333333333", "video", "720p", "path3", 300, 30), db_file)

    videos = list_items(type_filter="video", custom_path=db_file)
    assert len(videos) == 2
    assert all(v.type == "video" for v in videos)

    audios = list_items(type_filter="audio", custom_path=db_file)
    assert len(audios) == 1
    assert audios[0].title == "Relaxing Music"

    search_py = list_items(search="python", custom_path=db_file)
    assert len(search_py) == 2


def test_delete_item(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    id1 = add_item(HistoryItem(None, "A", "urlA", "video", "720p", "pA", 100, 10), db_file)
    id2 = add_item(HistoryItem(None, "B", "urlB", "audio", "MP3", "pB", 200, 20), db_file)

    assert delete_item(id1, db_file) is True
    remaining = list_items(custom_path=db_file)
    assert len(remaining) == 1
    assert remaining[0].id == id2
    assert get_item(id1, db_file) is None
