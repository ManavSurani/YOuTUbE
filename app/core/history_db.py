"""SQLite history database v2 with schema migrations, daily backups, and strict validation.

Ensures history data survives file moves/deletions and never saves broken rows (fixes B5, B6, B7, B15).
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
from typing import List, Optional

from app.core.logger import get_logger
from app.core.paths import APP_DATA, HISTORY_DB, HISTORY_DIR, THUMBS_DIR, ensure_dirs
from app.core.url_tools import extract_video_id


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
    video_id: Optional[str] = None
    channel: Optional[str] = None
    file_missing: int = 0
    source_job_id: Optional[str] = None


def get_db_path(custom_path: Optional[Path | str] = None) -> Path:
    if custom_path:
        return Path(custom_path)
    ensure_dirs()
    return HISTORY_DB


def maybe_migrate_v1_files() -> None:
    """Migrate legacy history.db and thumbnails to %APPDATA%/YOuTUbE/history/ if present."""
    logger = get_logger()
    old_db = APP_DATA / "history.db"
    new_db = HISTORY_DB

    if old_db.exists() and not new_db.exists():
        try:
            new_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_db, new_db)
            old_db.rename(APP_DATA / "history.db.bak")
            logger.info(f"Migrated legacy database from {old_db} to {new_db}")
        except Exception as exc:
            logger.warning(f"Failed to migrate legacy history.db: {exc}")

    old_thumbs = APP_DATA / "thumbnails"
    if old_thumbs.exists() and old_thumbs.is_dir():
        try:
            THUMBS_DIR.mkdir(parents=True, exist_ok=True)
            for f in old_thumbs.iterdir():
                if f.is_file() and not (THUMBS_DIR / f.name).exists():
                    shutil.copy2(f, THUMBS_DIR / f.name)
            logger.info("Migrated legacy thumbnails to history/thumbs/")
        except Exception as exc:
            logger.warning(f"Failed to migrate legacy thumbnails: {exc}")


def maybe_backup_db(db_path: Path) -> None:
    """Perform automatic daily backup of history database, retaining last 7 days."""
    if not db_path.exists():
        return
    logger = get_logger()
    try:
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        today_str = datetime.now().strftime("%Y%m%d")
        today_backup = backup_dir / f"history_{today_str}.bak"

        if not today_backup.exists():
            shutil.copy2(db_path, today_backup)
            logger.info(f"Created daily database backup: {today_backup.name}")

            # Retain only newest 7 backups
            backups = sorted(backup_dir.glob("history_*.bak"), key=lambda f: f.stat().st_mtime)
            while len(backups) > 7:
                oldest = backups.pop(0)
                oldest.unlink(missing_ok=True)
                logger.info(f"Purged expired backup: {oldest.name}")
    except Exception as exc:
        logger.warning(f"Daily database backup failed: {exc}")


def get_connection(custom_path: Optional[Path | str] = None) -> sqlite3.Connection:
    if custom_path is None:
        maybe_migrate_v1_files()
    path = get_db_path(custom_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(custom_path: Optional[Path | str] = None) -> None:
    """Initialize or migrate SQLite database schema with PRAGMA user_version."""
    db_path = get_db_path(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version;")
        ver_row = cursor.fetchone()
        version = ver_row[0] if ver_row else 0

        # Migration to version 1
        if version < 1:
            cursor.execute(
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    video_id TEXT,
                    channel TEXT,
                    file_missing INTEGER DEFAULT 0,
                    source_job_id TEXT
                )
                """
            )

            # Inspect existing columns in case table was created by older schema
            cursor.execute("PRAGMA table_info(history);")
            columns = {row["name"] for row in cursor.fetchall()}

            if "video_id" not in columns:
                cursor.execute("ALTER TABLE history ADD COLUMN video_id TEXT;")
            if "channel" not in columns:
                cursor.execute("ALTER TABLE history ADD COLUMN channel TEXT;")
            if "file_missing" not in columns:
                cursor.execute("ALTER TABLE history ADD COLUMN file_missing INTEGER DEFAULT 0;")
            if "source_job_id" not in columns:
                cursor.execute("ALTER TABLE history ADD COLUMN source_job_id TEXT;")

            # Backfill video_id for older rows
            cursor.execute("SELECT id, url, video_id FROM history WHERE video_id IS NULL OR video_id = '';")
            for row in cursor.fetchall():
                extracted = extract_video_id(row["url"])
                if extracted:
                    cursor.execute("UPDATE history SET video_id = ? WHERE id = ?;", (extracted, row["id"]))

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON history (created_at DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_video_id ON history (video_id);")
            cursor.execute("PRAGMA user_version = 1;")
            conn.commit()

    if custom_path is None:
        maybe_backup_db(db_path)


def add_item(item: HistoryItem, custom_path: Optional[Path | str] = None) -> int:
    """Insert a new history record after validating inputs. Raises ValueError on invalid data."""
    if not item.file_path or not item.file_path.strip():
        raise ValueError("Cannot save history item: file_path is empty.")

    clean_title = (item.title or "").strip()
    clean_url = (item.url or "").strip()
    if not clean_title or clean_title == clean_url:
        raise ValueError(f"Cannot save history item: title is invalid or equals URL ('{clean_title}').")

    init_db(custom_path)
    vid = item.video_id or extract_video_id(clean_url) or ""

    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO history (
                title, url, type, quality, file_path, size_bytes, duration,
                thumbnail_path, video_id, channel, file_missing, source_job_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_title,
                clean_url,
                item.type.lower(),
                item.quality,
                item.file_path,
                int(item.size_bytes or 0),
                int(item.duration or 0),
                item.thumbnail_path,
                vid,
                item.channel or "",
                int(item.file_missing or 0),
                item.source_job_id or "",
            ),
        )
        conn.commit()
        return cursor.lastrowid


def update_item(item: HistoryItem, custom_path: Optional[Path | str] = None) -> bool:
    """Update an existing record (used for duplicate downloads and relinking)."""
    if not item.id:
        return False
    init_db(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE history
            SET title = ?, url = ?, type = ?, quality = ?, file_path = ?,
                size_bytes = ?, duration = ?, thumbnail_path = ?, video_id = ?,
                channel = ?, file_missing = ?, source_job_id = ?,
                created_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                item.title,
                item.url,
                item.type.lower(),
                item.quality,
                item.file_path,
                int(item.size_bytes or 0),
                int(item.duration or 0),
                item.thumbnail_path,
                item.video_id,
                item.channel or "",
                int(item.file_missing or 0),
                item.source_job_id or "",
                item.id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def find_duplicate(
    video_id: str,
    kind: str,
    quality: str,
    custom_path: Optional[Path | str] = None,
) -> Optional[HistoryItem]:
    """Find existing row with same video_id, kind, and quality."""
    if not video_id:
        return None
    init_db(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, url, type, quality, file_path, size_bytes, duration,
                   thumbnail_path, created_at, video_id, channel, file_missing, source_job_id
            FROM history
            WHERE video_id = ? AND type = ? AND quality = ?
            ORDER BY id DESC LIMIT 1
            """,
            (video_id, kind.lower(), quality),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return _row_to_item(row)


def list_items(
    type_filter: Optional[str] = None,
    search: str = "",
    custom_path: Optional[Path | str] = None,
) -> List[HistoryItem]:
    """Retrieve history records newest first with optional filtering."""
    init_db(custom_path)
    with get_connection(custom_path) as conn:
        query = (
            "SELECT id, title, url, type, quality, file_path, size_bytes, duration, "
            "thumbnail_path, created_at, video_id, channel, file_missing, source_job_id "
            "FROM history WHERE 1=1"
        )
        params = []

        if type_filter and type_filter.lower() in ("video", "audio"):
            query += " AND type = ?"
            params.append(type_filter.lower())

        if search.strip():
            query += " AND (title LIKE ? OR url LIKE ? OR channel LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term, term])

        query += " ORDER BY id DESC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        return [_row_to_item(row) for row in cursor.fetchall()]


def get_item(item_id: int, custom_path: Optional[Path | str] = None) -> Optional[HistoryItem]:
    """Fetch a single history record by ID."""
    init_db(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, url, type, quality, file_path, size_bytes, duration,
                   thumbnail_path, created_at, video_id, channel, file_missing, source_job_id
            FROM history WHERE id = ?
            """,
            (item_id,),
        )
        row = cursor.fetchone()
        return _row_to_item(row) if row else None


def delete_item(item_id: int, custom_path: Optional[Path | str] = None) -> bool:
    """Delete a history record by ID."""
    init_db(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0


def clear_all(custom_path: Optional[Path | str] = None) -> int:
    """Remove all records from history database and return count removed."""
    init_db(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()
        return cursor.rowcount


def _row_to_item(row: sqlite3.Row) -> HistoryItem:
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
        video_id=row["video_id"],
        channel=row["channel"],
        file_missing=row["file_missing"],
        source_job_id=row["source_job_id"],
    )
