"""Permanent thumbnail store with rounded caching, fallback icons, and ref-count cleanup.

Ensures thumbnails never vanish when deleting sibling rows (fixes B6).
Replaces letter badges ('V' or 'A') with neutral play and music icons.
"""

from pathlib import Path
from typing import Optional, Tuple
import sqlite3
import urllib.request

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap, QPolygonF

from app.core.logger import get_logger
from app.core.paths import HISTORY_DB, THUMBS_DIR, ensure_dirs


def save_thumbnail(video_id: str, image_data: bytes) -> str:
    """Save thumbnail bytes to permanent store and return path."""
    if not video_id or not image_data:
        return ""
    ensure_dirs()
    thumb_path = THUMBS_DIR / f"{video_id}.jpg"
    try:
        thumb_path.write_bytes(image_data)
        return str(thumb_path)
    except Exception as exc:
        get_logger().error(f"Failed to save thumbnail for {video_id}: {exc}")
        return ""


def get_thumbnail_path(video_id: str) -> Optional[Path]:
    """Return Path to local thumbnail if it exists."""
    if not video_id:
        return None
    thumb_path = THUMBS_DIR / f"{video_id}.jpg"
    if thumb_path.is_file() and thumb_path.stat().st_size > 0:
        return thumb_path
    return None


def fetch_thumbnail_remote(video_id: str) -> Optional[str]:
    """Re-download missing thumbnail from YouTube CDN into local store."""
    if not video_id:
        return None
    url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    logger = get_logger()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = resp.read()
                return save_thumbnail(video_id, data)
    except Exception as exc:
        logger.debug(f"Could not re-fetch remote thumbnail for {video_id}: {exc}")
    return None


def create_fallback_pixmap(size: Tuple[int, int] = (64, 36), is_audio: bool = False, radius: int = 4) -> QPixmap:
    """Generate a clean neutral fallback icon. Never displays letters."""
    w, h = size
    pix = QPixmap(w, h)
    pix.fill(Qt.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    # Background card
    path = QPainterPath()
    path.addRoundedRect(0, 0, w, h, radius, radius)
    painter.fillPath(path, QColor("#212121"))

    # Icon styling
    icon_color = QColor("#AAAAAA")
    painter.setPen(Qt.NoPen)
    painter.setBrush(icon_color)

    cx, cy = w / 2.0, h / 2.0

    if not is_audio:
        # Video: Clean play triangle
        tri_size = min(w, h) * 0.32
        poly = QPolygonF([
            QPointF(cx - tri_size * 0.5, cy - tri_size * 0.6),
            QPointF(cx + tri_size * 0.7, cy),
            QPointF(cx - tri_size * 0.5, cy + tri_size * 0.6),
        ])
        painter.drawPolygon(poly)
    else:
        # Audio: Musical note
        note_r = min(w, h) * 0.12
        painter.drawEllipse(QPointF(cx - note_r, cy + note_r * 0.6), note_r, note_r * 0.8)
        painter.setPen(icon_color)
        painter.drawLine(int(cx), int(cy + note_r * 0.6), int(cx), int(cy - note_r * 1.4))
        painter.drawLine(int(cx), int(cy - note_r * 1.4), int(cx + note_r * 0.8), int(cy - note_r * 1.1))

    painter.end()
    return pix


def get_rounded_pixmap(
    video_id: str,
    size: Tuple[int, int] = (64, 36),
    is_audio: bool = False,
    radius: int = 4,
    allow_network: bool = False,
) -> QPixmap:
    """Return rounded QPixmap from store, or neutral fallback if missing."""
    w, h = size
    thumb_path = get_thumbnail_path(video_id)

    if not thumb_path and allow_network and video_id:
        new_path = fetch_thumbnail_remote(video_id)
        if new_path:
            thumb_path = Path(new_path)

    if not thumb_path:
        return create_fallback_pixmap(size, is_audio, radius)

    src = QPixmap(str(thumb_path))
    if src.isNull():
        return create_fallback_pixmap(size, is_audio, radius)

    # Scale and crop to exact aspect ratio
    scaled = src.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (scaled.width() - w) // 2)
    y = max(0, (scaled.height() - h) // 2)
    cropped = scaled.copy(x, y, w, h)

    # Clip to rounded rect
    dest = QPixmap(w, h)
    dest.fill(Qt.transparent)

    painter = QPainter(dest)
    painter.setRenderHint(QPainter.Antialiasing)
    clip_path = QPainterPath()
    clip_path.addRoundedRect(0, 0, w, h, radius, radius)
    painter.setClipPath(clip_path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()

    return dest


def delete_thumbnail_if_unreferenced(video_id: str, db_path: Optional[Path | str] = None) -> bool:
    """Delete thumbnail file only if no remaining history row references this video_id."""
    if not video_id:
        return False

    target_db = Path(db_path) if db_path else HISTORY_DB
    logger = get_logger()
    try:
        if target_db.exists():
            with sqlite3.connect(str(target_db)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM history WHERE video_id = ?", (video_id,))
                count = cursor.fetchone()[0]
                if count > 0:
                    logger.debug(f"Retaining thumbnail {video_id}: {count} rows still reference it.")
                    return False
    except Exception as exc:
        logger.warning(f"Error checking thumbnail references for {video_id}: {exc}")
        return False

    thumb_path = THUMBS_DIR / f"{video_id}.jpg"
    try:
        if thumb_path.exists():
            thumb_path.unlink(missing_ok=True)
            logger.info(f"Unreferenced thumbnail removed: {thumb_path}")
            return True
    except Exception as exc:
        logger.warning(f"Failed to delete thumbnail file {thumb_path}: {exc}")

    return False
