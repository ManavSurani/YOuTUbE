from pathlib import Path
from PySide6.QtGui import QGuiApplication, QPixmap
import pytest

from app.core.history_db import HistoryItem, add_item, init_db
from app.core.thumbnails import (
    create_fallback_pixmap,
    delete_thumbnail_if_unreferenced,
    get_rounded_pixmap,
    save_thumbnail,
)


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    yield app


def test_thumbnail_saving_and_pixmap(tmp_path: Path, monkeypatch):
    import app.core.thumbnails as thumb_mod
    monkeypatch.setattr(thumb_mod, "THUMBS_DIR", tmp_path)

    fake_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 50  # minimal jpeg header
    path_str = save_thumbnail("abc12345678", fake_bytes)
    assert path_str != ""
    assert Path(path_str).is_file()

    # Pixmap generation
    pix = get_rounded_pixmap("abc12345678", size=(64, 36), is_audio=False)
    assert isinstance(pix, QPixmap)
    assert pix.width() == 64
    assert pix.height() == 36


def test_fallback_pixmap_no_letters():
    """Verify fallback returns neutral icon without letters."""
    pix_video = create_fallback_pixmap(size=(64, 36), is_audio=False)
    assert not pix_video.isNull()
    assert pix_video.width() == 64
    assert pix_video.height() == 36

    pix_audio = create_fallback_pixmap(size=(64, 36), is_audio=True)
    assert not pix_audio.isNull()


def test_thumbnail_shared_reference_retention(tmp_path: Path, monkeypatch):
    """B6 fix: when two history rows share the same video_id (video and audio),
    deleting one must NOT delete the thumbnail. Deleting both removes it."""
    import app.core.thumbnails as thumb_mod
    monkeypatch.setattr(thumb_mod, "THUMBS_DIR", tmp_path)

    db_path = tmp_path / "test_ref.db"
    init_db(db_path)

    # Save thumbnail
    thumb_path = save_thumbnail("shared_vid", b"fake_img")
    assert Path(thumb_path).exists()

    # Add two items referencing the same video_id
    id1 = add_item(HistoryItem(None, "Video Version", "https://youtube.com/watch?v=shared_vid", "video", "1080p", "C:/v.mkv", 1000, 60, video_id="shared_vid"), db_path)
    id2 = add_item(HistoryItem(None, "Audio Version", "https://youtube.com/watch?v=shared_vid", "audio", "MP3", "C:/a.mp3", 500, 60, video_id="shared_vid"), db_path)

    # Delete first item from DB
    from app.core.history_db import delete_item
    delete_item(id1, db_path)

    # Try unreferenced cleanup - should RETAIN because id2 still references shared_vid
    deleted = delete_thumbnail_if_unreferenced("shared_vid", db_path=db_path)
    assert deleted is False
    assert Path(thumb_path).exists()

    # Delete second item from DB
    delete_item(id2, db_path)

    # Now unreferenced cleanup should delete the thumbnail
    deleted_now = delete_thumbnail_if_unreferenced("shared_vid", db_path=db_path)
    assert deleted_now is True
    assert not Path(thumb_path).exists()
