"""High-level history service managing jobs, safe deletion, duplicate handling, and file relinking.

Ensures history integrity and handles file states without data loss (fixes B5, B6, B7, B15).
"""

from pathlib import Path
from typing import List, Optional, Tuple
import os
import send2trash

from app.core.jobs import DownloadJob
from app.core.history_db import (
    HistoryItem,
    add_item,
    delete_item,
    find_duplicate,
    get_item,
    list_items,
    update_item,
)
from app.core.logger import get_logger
from app.core.paths import DEFAULT_DOWNLOADS
from app.core.thumbnails import delete_thumbnail_if_unreferenced, save_thumbnail
from app.core.url_tools import extract_video_id


def save_from_job(job: DownloadJob, final_path: str, custom_db: Optional[Path | str] = None) -> HistoryItem:
    """Save completed download from an immutable DownloadJob snapshot.

    Verifies file on disk, saves thumbnail, applies duplicate rules, and stores record.
    """
    logger = get_logger()
    p = Path(final_path)

    if not p.is_file():
        raise FileNotFoundError(f"Cannot save history: downloaded file not found on disk at '{final_path}'")

    real_size = p.stat().st_size

    # Save thumbnail bytes if present
    thumb_path = None
    if job.thumbnail_bytes and job.video_id:
        thumb_path = save_thumbnail(job.video_id, job.thumbnail_bytes)

    # Check duplicate rule: same video_id + same kind + same quality
    dup = find_duplicate(job.video_id, job.kind, job.quality_label, custom_path=custom_db) if job.video_id else None

    if dup:
        logger.info(f"Duplicate download detected for {job.video_id} ({job.quality_label}). Updating existing row {dup.id}.")
        dup.title = job.title
        dup.url = job.url
        dup.channel = job.channel
        dup.duration = job.duration_seconds
        dup.file_path = str(p.resolve())
        dup.size_bytes = real_size
        dup.file_missing = 0
        dup.source_job_id = job.job_id
        if thumb_path:
            dup.thumbnail_path = thumb_path

        update_item(dup, custom_path=custom_db)
        return dup

    item = HistoryItem(
        id=None,
        title=job.title,
        url=job.url,
        type=job.kind,
        quality=job.quality_label,
        file_path=str(p.resolve()),
        size_bytes=real_size,
        duration=job.duration_seconds,
        thumbnail_path=thumb_path,
        video_id=job.video_id,
        channel=job.channel,
        file_missing=0,
        source_job_id=job.job_id,
    )
    new_id = add_item(item, custom_path=custom_db)
    item.id = new_id
    logger.info(f"Saved history row {new_id} for '{job.title}' ({job.quality_label})")
    return item


def delete(row_id: int, delete_file: bool = False, custom_db: Optional[Path | str] = None) -> Tuple[bool, str]:
    """Delete history record and optionally send the file to the Recycle Bin.

    If file is locked or cannot be deleted, keeps the row and returns clear reason.
    """
    logger = get_logger()
    item = get_item(row_id, custom_path=custom_db)
    if not item:
        return False, "History item not found."

    if delete_file and item.file_path:
        target_file = Path(item.file_path)
        if target_file.is_file():
            try:
                # Send to Recycle Bin safely (never permanently delete)
                send2trash.send2trash(str(target_file))
                logger.info(f"Sent file to Recycle Bin: {target_file}")
            except Exception as exc:
                err_msg = f"The file is open in another program or cannot be deleted ({exc})."
                logger.warning(f"Failed to recycle file for row {row_id}: {err_msg}")
                return False, err_msg

    # Delete row from DB
    deleted = delete_item(row_id, custom_path=custom_db)
    if not deleted:
        return False, "Failed to remove database record."

    # Remove thumbnail only if no other row uses it
    if item.video_id:
        delete_thumbnail_if_unreferenced(item.video_id, db_path=custom_db)

    return True, ""


def clear_all(delete_files: bool = False, custom_db: Optional[Path | str] = None) -> Tuple[int, List[str]]:
    """Delete all history records, optionally recycling files."""
    items = list_items(custom_path=custom_db)
    deleted_count = 0
    errors: List[str] = []

    for item in items:
        if item.id is None:
            continue
        ok, err = delete(item.id, delete_file=delete_files, custom_db=custom_db)
        if ok:
            deleted_count += 1
        else:
            errors.append(f"'{item.title}': {err}")

    return deleted_count, errors


def relink(row_id: int, new_path: str, custom_db: Optional[Path | str] = None) -> Tuple[bool, str]:
    """Relink a history item to a new file location ('Locate file')."""
    p = Path(new_path)
    if not p.is_file():
        return False, "Selected file does not exist on disk."

    item = get_item(row_id, custom_path=custom_db)
    if not item:
        return False, "History record not found."

    item.file_path = str(p.resolve())
    item.size_bytes = p.stat().st_size
    item.file_missing = 0
    update_item(item, custom_path=custom_db)
    get_logger().info(f"Relinked row {row_id} to '{new_path}'")
    return True, ""


def refresh_file_status(custom_db: Optional[Path | str] = None) -> int:
    """Verify file existence for all history rows and update cached file_missing flag."""
    items = list_items(custom_path=custom_db)
    missing_count = 0

    for item in items:
        if not item.id or not item.file_path:
            continue
        exists = Path(item.file_path).is_file()
        expected = 0 if exists else 1
        if expected == 1:
            missing_count += 1

        if item.file_missing != expected:
            item.file_missing = expected
            update_item(item, custom_path=custom_db)

    return missing_count


def repair_existing_rows(download_dir: Optional[Path | str] = None, custom_db: Optional[Path | str] = None) -> int:
    """One-time auto-repair for existing rows with missing files or 0 B sizes.

    Searches download folder for matches by [video_id] or title and updates records.
    """
    logger = get_logger()
    search_dir = Path(download_dir) if download_dir else DEFAULT_DOWNLOADS
    if not search_dir.is_dir():
        return 0

    items = list_items(custom_path=custom_db)
    repaired_count = 0

    for item in items:
        needs_repair = False
        target_path = Path(item.file_path) if item.file_path else None

        # Check if file is missing or 0 bytes
        if not target_path or not target_path.is_file() or item.size_bytes == 0:
            needs_repair = True

        if not needs_repair:
            continue

        vid = item.video_id or extract_video_id(item.url) or ""

        # Search for file containing [video_id] in download directory
        candidate = None
        if vid:
            for f in search_dir.iterdir():
                if f.is_file() and f"[{vid}]" in f.name and not any(f.name.endswith(ext) for ext in (".part", ".ytdl", ".tmp")):
                    candidate = f
                    break

        if candidate and candidate.is_file():
            item.file_path = str(candidate.resolve())
            item.size_bytes = candidate.stat().st_size
            item.file_missing = 0
            if vid and not item.video_id:
                item.video_id = vid
            update_item(item, custom_path=custom_db)
            repaired_count += 1
            logger.info(f"Repaired history row {item.id}: found matching file {candidate.name}")

    if repaired_count > 0:
        logger.info(f"Auto-repair completed: successfully restored {repaired_count} items.")

    return repaired_count
