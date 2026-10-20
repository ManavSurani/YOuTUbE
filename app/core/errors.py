"""Plain-language error mapping for yt-dlp and tool failures."""

import re
from typing import Optional


def explain(raw_text: str, free_bytes: Optional[int] = None, needed_bytes: Optional[int] = None) -> str:
    """Map raw process or tool error output to a calm, plain-language explanation."""
    text = (raw_text or "").strip()
    text_lower = text.lower()

    # 0. Resume failure / multiple crash failure
    if "could not be resumed" in text_lower:
        return "The download could not be resumed. Press Retry."
    if "the app closed several times" in text_lower:
        return text

    # 1. Low disk space (explicit check or from error string)
    if (needed_bytes is not None and free_bytes is not None and free_bytes < needed_bytes) or (
        "no space left on device" in text_lower or "disk full" in text_lower or "not enough space" in text_lower
    ):
        bytes_val = needed_bytes if needed_bytes is not None else 1024 * 1024 * 1024
        gb = round(bytes_val / (1024**3), 1)
        if gb < 0.1:
            gb = 0.1
        return f"Not enough free space. Needs about {gb} GB."

    # 2. Invalid link
    if (
        "not a valid url" in text_lower
        or "unsupported url" in text_lower
        or "invalid url" in text_lower
        or "is not a valid youtube link" in text_lower
    ):
        return "Please paste a valid YouTube link."

    # 3. Copyright claim
    if "copyright" in text_lower:
        return "This video was removed because of a copyright claim."

    # 4. Live stream / premiere
    if "live event will begin" in text_lower or "is live" in text_lower or "premiere" in text_lower:
        return "This is a live stream or premiere that is not ready yet."

    # 5. HTTP Error 403
    if "http error 403" in text_lower or "403: forbidden" in text_lower or "403 forbidden" in text_lower:
        return "YouTube refused the download for now. Wait a minute and press Retry. If it keeps happening, update the tools."

    # 6. HTTP Error 429
    if "http error 429" in text_lower or "429: too many requests" in text_lower or "too many requests" in text_lower:
        return "YouTube says there were too many requests. Wait a few minutes and try again."

    # 7. HTTP Error 404
    if "http error 404" in text_lower or "404: not found" in text_lower or "404 not found" in text_lower:
        return "This video or file is no longer available."

    # 8. Permission error
    if "permissionerror" in text_lower or "permission denied" in text_lower:
        return "The app cannot write to the download folder. Choose another folder in Settings or close the program that uses the file."

    # 9. Merger / combination error
    if "[merger]" in text_lower or "invalid data found" in text_lower or "error parsing" in text_lower:
        return "The video and audio could not be combined. Press Retry. If it repeats, update the tools."

    # 10. Network / socket / connection interrupted
    if (
        "[errno 11001]" in text_lower
        or "getaddrinfo failed" in text_lower
        or "network is unreachable" in text_lower
        or "connection refused" in text_lower
        or "remotedisconnected" in text_lower
        or "urlerror" in text_lower
        or "timed out" in text_lower
        or "timeout" in text_lower
        or "incompleteread" in text_lower
        or "connection reset" in text_lower
        or "no internet" in text_lower
        or "winerror 10051" in text_lower
        or "winerror 10054" in text_lower
        or "winerror 10060" in text_lower
        or "unreachable" in text_lower
    ):
        return "The internet connection was interrupted. Check your connection and press Retry."

    # 11. Private / members-only
    if (
        "private video" in text_lower
        or "this video is private" in text_lower
        or "members-only" in text_lower
        or "members only" in text_lower
        or "join this channel to get access to members-only content" in text_lower
    ):
        return "This video is private or for members only."

    # 12. Age-restricted
    if (
        "sign in to confirm your age" in text_lower
        or "age-restricted" in text_lower
        or "age restricted" in text_lower
        or "sign in to view this video" in text_lower
    ):
        return "This video is age restricted and can't be downloaded without sign-in."

    # 13. Sign-in / bot check
    if (
        "confirm you’re not a bot" in text_lower
        or "confirm you're not a bot" in text_lower
        or "sign in to confirm you’re not a bot" in text_lower
        or "sign in to confirm you're not a bot" in text_lower
        or "bot verification" in text_lower
        or "bot check" in text_lower
        or "sign in if you've been granted access" in text_lower
    ):
        return "YouTube asked for verification. Try again later or update tools."

    # 14. Unavailable / removed
    if (
        "video unavailable" in text_lower
        or "this video is unavailable" in text_lower
        or "has been removed by the uploader" in text_lower
        or "this video has been removed" in text_lower
        or "not available in your country" in text_lower
        or "blocked in your country" in text_lower
    ):
        return "This video is not available."

    # 15. ffmpeg missing
    if (
        "ffmpeg not found" in text_lower
        or "ffprobe not found" in text_lower
        or "ffmpeg is not installed" in text_lower
        or "ffmpeg missing" in text_lower
    ):
        return "ffmpeg is missing. Please update or repair tools."

    # 16. Extraction error
    if (
        "unable to extract" in text_lower
        or "extractionerror" in text_lower
        or "regex_search" in text_lower
        or "jsinterp" in text_lower
        or "n challenge solving failed" in text_lower
    ):
        return "YouTube changed something. Please try again after the update."

    # 17. Fallback (calm and truthful without referencing non-existent buttons)
    return "Something went wrong. Open Settings and press Export log to see the details."
