"""YouTube URL validation and cleaning."""

import re
from urllib.parse import parse_qs, urlparse

_ID_PATTERN = r"[a-zA-Z0-9_-]{11}"


def extract_video_id(url: str) -> str | None:
    """Extract 11-character video ID from various YouTube URL formats."""
    if not url:
        return None

    clean = url.strip()
    if not (clean.startswith("http://") or clean.startswith("https://")):
        clean = "https://" + clean

    try:
        parsed = urlparse(clean)
    except Exception:
        return None

    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    if netloc in ("youtube.com", "m.youtube.com"):
        if parsed.path.startswith("/watch"):
            qs = parse_qs(parsed.query)
            v = qs.get("v")
            if v and re.match(f"^{_ID_PATTERN}$", v[0]):
                return v[0]
        elif parsed.path.startswith("/shorts/"):
            parts = parsed.path.split("/")
            if len(parts) >= 3 and re.match(f"^{_ID_PATTERN}$", parts[2]):
                return parts[2]
        elif parsed.path.startswith("/embed/"):
            parts = parsed.path.split("/")
            if len(parts) >= 3 and re.match(f"^{_ID_PATTERN}$", parts[2]):
                return parts[2]
        elif parsed.path.startswith("/live/"):
            parts = parsed.path.split("/")
            if len(parts) >= 3 and re.match(f"^{_ID_PATTERN}$", parts[2]):
                return parts[2]
    elif netloc == "youtu.be":
        path = parsed.path.lstrip("/").split("/")[0]
        if re.match(f"^{_ID_PATTERN}$", path):
            return path

    return None


def is_youtube_url(text: str) -> bool:
    """Return True if text contains a valid YouTube video URL."""
    return extract_video_id(text) is not None


def clean_url(text: str) -> str | None:
    """Return clean standard URL https://www.youtube.com/watch?v=<ID>, or None if invalid."""
    vid = extract_video_id(text)
    if not vid:
        return None
    return f"https://www.youtube.com/watch?v={vid}"
