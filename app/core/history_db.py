"""SQLite history database for completed downloads."""

import sqlite3
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from app.core.paths import HISTORY_DB, THUMBS_DIR, ensure_dirs
from app.core.logger import get_logger


@dataclass
class HistoryItem:
    id: Optional[int]
    title: str
    url: str
    type: str  # "video" or "audio"
    quality: str
    file_path: str
    size_bytes: int
    duration: int
    thumbnail_path: Optional[str] = None
    created_at: Optional[str] = None


def get_db_path(custom_path: Optional[Path | str] = None) -> Path:
    if custom_path:
        return Path(custom_path)
    ensure_dirs()
    return HISTORY_DB


def get_connection(custom_path: Optional[Path | str] = None) -> sqlite3.Connection:
    path = get_db_path(custom_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(custom_path: Optional[Path | str] = None) -> None:
    """Create the history table if it doesn't already exist."""
    with get_connection(custom_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON history (created_at DESC);")
        conn.commit()


def add_item(item: HistoryItem, custom_path: Optional[Path | str] = None) -> int:
    """Insert a new history record and return its row ID."""
    init_db(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO history (title, url, type, quality, file_path, size_bytes, duration, thumbnail_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.title,
                item.url,
                item.type.lower(),
                item.quality,
                item.file_path,
                item.size_bytes,
                item.duration,
                item.thumbnail_path,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def list_items(
    type_filter: Optional[str] = None,
    search: str = "",
    custom_path: Optional[Path | str] = None,
) -> List[HistoryItem]:
    """Retrieve history records newest first with optional type and search filtering."""
    init_db(custom_path)
    with get_connection(custom_path) as conn:
        query = "SELECT id, title, url, type, quality, file_path, size_bytes, duration, thumbnail_path, created_at FROM history WHERE 1=1"
        params = []

        if type_filter and type_filter.lower() in ("video", "audio"):
            query += " AND type = ?"
            params.append(type_filter.lower())

        if search.strip():
            query += " AND (title LIKE ? OR url LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        query += " ORDER BY id DESC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            HistoryItem(
                id=row["id"],
                title=row["title"],
                url=row["url"],
                type=row["type"],
                quality=row["quality"],
                file_path=row["file_path"],
                size_bytes=row["size_bytes"],
                duration=row["duration"],
                thumbnail_path=row["thumbnail_path"],
                created_at=row["created_at"],
            )
            for row in rows
        ]


def get_item(item_id: int, custom_path: Optional[Path | str] = None) -> Optional[HistoryItem]:
    """Fetch a single history record by ID."""
    init_db(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, url, type, quality, file_path, size_bytes, duration, thumbnail_path, created_at FROM history WHERE id = ?",
            (item_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return HistoryItem(
            id=row["id"],
            title=row["title"],
            url=row["url"],
            type=row["type"],
            quality=row["quality"],
            file_path=row["file_path"],
            size_bytes=row["size_bytes"],
            duration=row["duration"],
            thumbnail_path=row["thumbnail_path"],
            created_at=row["created_at"],
        )


def delete_item(item_id: int, custom_path: Optional[Path | str] = None) -> bool:
    """Delete a history record by ID."""
    init_db(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0


def save_thumbnail_image(video_id: str, image_data: bytes) -> str:
    """Save thumbnail bytes into local thumbnails folder and return the file path."""
    ensure_dirs()
    thumb_path = THUMBS_DIR / f"{video_id}.jpg"
    try:
        thumb_path.write_bytes(image_data)
        return str(thumb_path)
    except Exception as exc:
        get_logger().error(f"Failed to save thumbnail image: {exc}")
        return ""
