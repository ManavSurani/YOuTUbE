"""DownloadJob snapshot dataclass representing an immutable download task.

Created at the moment of Download or Add to queue from fetched VideoInfo.
Prevents any subsequent widget reading or UI race conditions (fixes B5).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.core.url_tools import clean_url, extract_video_id
from app.core.info_fetcher import VideoInfo


@dataclass(frozen=True)
class DownloadJob:
    job_id: str
    url: str
    video_id: str
    title: str
    channel: str
    duration_seconds: int
    thumbnail_url: str
    thumbnail_bytes: Optional[bytes]
    kind: str  # "video" or "audio"
    quality_label: str
    height: Optional[int]
    audio_format: Optional[str]
    output_dir: str
    created_at: str

    @classmethod
    def create(
        cls,
        info: VideoInfo,
        kind: str,
        quality_label: str,
        height: Optional[int] = None,
        audio_format: Optional[str] = None,
        output_dir: str = "",
        thumbnail_bytes: Optional[bytes] = None,
        video_id: Optional[str] = None,
    ) -> "DownloadJob":
        """Factory method to create an immutable snapshot from fetched metadata."""
        cleaned_url = clean_url(info.url) or info.url
        vid = video_id or extract_video_id(cleaned_url) or extract_video_id(info.url) or ""
        job_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        title = info.title.strip()
        if not title or title == info.url or title == cleaned_url:
            raise ValueError(f"Invalid job title '{title}'. Title must not be empty or equal to the URL.")

        return cls(
            job_id=job_id,
            url=cleaned_url,
            video_id=vid,
            title=title,
            channel=info.channel or "",
            duration_seconds=int(info.duration or 0),
            thumbnail_url=info.thumbnail_url or "",
            thumbnail_bytes=thumbnail_bytes,
            kind=kind.lower(),
            quality_label=quality_label,
            height=height,
            audio_format=audio_format.lower() if audio_format else None,
            output_dir=str(output_dir),
            created_at=created_at,
        )
