import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.errors import explain


# ---------------------------------------------------------------------------
# Test the 14 Error Samples from Audit (Prompt Phase 6)
# ---------------------------------------------------------------------------

FOURTEEN_ERROR_SAMPLES = [
    # 1. Private video
    (
        "ERROR: [youtube] abc: Private video. Sign in if you've been granted access to this video",
        "This video is private or for members only.",
    ),
    # 2. Age-restricted
    (
        "ERROR: [youtube] abc: Sign in to confirm your age. This video may be inappropriate for some users.",
        "This video is age restricted and can't be downloaded without sign-in.",
    ),
    # 3. Bot check / verification
    (
        "ERROR: [youtube] abc: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication.",
        "YouTube asked for verification. Try again later or update tools.",
    ),
    # 4. Geo-blocked / Unavailable
    (
        "ERROR: [youtube] abc: Video unavailable. This video is not available in your country",
        "This video is not available.",
    ),
    # 5. DNS / Unreachable
    (
        "ERROR: [youtube] abc: Unable to download API page: <urlopen error [Errno 11001] getaddrinfo failed>",
        "The internet connection was interrupted. Check your connection and press Retry.",
    ),
    # 6. Disk full
    (
        "OSError: [Errno 28] No space left on device",
        "Not enough free space.",
    ),
    # 7. HTTP 403
    (
        "ERROR: [youtube] abc: HTTP Error 403: Forbidden",
        "YouTube refused the download for now. Wait a minute and press Retry. If it keeps happening, update the tools.",
    ),
    # 8. HTTP 429
    (
        "ERROR: [youtube] abc: HTTP Error 429: Too Many Requests",
        "YouTube says there were too many requests. Wait a few minutes and try again.",
    ),
    # 9. HTTP 404
    (
        "ERROR: [youtube] abc: HTTP Error 404: Not Found",
        "This video or file is no longer available.",
    ),
    # 10. WinError socket / Connection reset
    (
        "urllib.error.URLError: <urlopen error [WinError 10054] An existing connection was forcibly closed by the remote host>",
        "The internet connection was interrupted. Check your connection and press Retry.",
    ),
    # 11. Permission error
    (
        "PermissionError: [Errno 13] Permission denied: 'C:\\Downloads\\video.mkv'",
        "The app cannot write to the download folder. Choose another folder in Settings or close the program that uses the file.",
    ),
    # 12. Merger failure
    (
        "ERROR: [Merger] Error parsing file: Invalid data found when processing input",
        "The video and audio could not be combined. Press Retry. If it repeats, update the tools.",
    ),
    # 13. Copyright claim
    (
        "ERROR: [youtube] abc: This video has been removed due to a copyright claim by Warner Bros",
        "This video was removed because of a copyright claim.",
    ),
    # 14. Live stream / premiere
    (
        "ERROR: [youtube] abc: This live event will begin in 2 hours.",
        "This is a live stream or premiere that is not ready yet.",
    ),
]


@pytest.mark.parametrize("sample,expected", FOURTEEN_ERROR_SAMPLES)
def test_14_audit_error_samples(sample, expected):
    result = explain(sample)
    if "Not enough free space" in expected:
        assert expected in result
    else:
        assert result == expected


def test_network_error():
    sample = "ERROR: [youtube] abc: Unable to download API page: <urlopen error [Errno 11001] getaddrinfo failed>"
    assert explain(sample) == "The internet connection was interrupted. Check your connection and press Retry."

    sample2 = "urllib.error.URLError: <urlopen error [WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time>"
    assert explain(sample2) == "The internet connection was interrupted. Check your connection and press Retry."


def test_private_or_members_only():
    sample = "ERROR: [youtube] abc: Private video. Sign in if you've been granted access to this video"
    assert explain(sample) == "This video is private or for members only."

    sample_members = "ERROR: [youtube] abc: Join this channel to get access to members-only content"
    assert explain(sample_members) == "This video is private or for members only."


def test_age_restricted():
    sample = "ERROR: [youtube] abc: Sign in to confirm your age. This video may be inappropriate for some users."
    assert explain(sample) == "This video is age restricted and can't be downloaded without sign-in."


def test_unavailable_or_removed():
    sample = "ERROR: [youtube] abc: Video unavailable. This video has been removed by the uploader"
    assert explain(sample) == "This video is not available."

    sample2 = "ERROR: [youtube] abc: Video unavailable. This video is not available in your country"
    assert explain(sample2) == "This video is not available."


def test_sign_in_or_bot_check():
    sample = "ERROR: [youtube] abc: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication."
    assert explain(sample) == "YouTube asked for verification. Try again later or update tools."

    sample2 = "ERROR: [youtube] abc: Sign in to confirm you're not a bot."
    assert explain(sample2) == "YouTube asked for verification. Try again later or update tools."


def test_extraction_error():
    sample = "ERROR: [youtube] abc: Unable to extract video data; please report this issue on https://github.com/yt-dlp/yt-dlp/issues?q="
    assert explain(sample) == "YouTube changed something. Please try again after the update."

    sample2 = "ERROR: [youtube] abc: n challenge solving failed: Unable to extract n signature"
    assert explain(sample2) == "YouTube changed something. Please try again after the update."


def test_ffmpeg_missing():
    sample = "ERROR: Postprocessing: ffmpeg not found. Please install or provide the path using --ffmpeg-location"
    assert explain(sample) == "ffmpeg is missing. Please update or repair tools."


def test_low_disk_space():
    # Via error string
    sample = "OSError: [Errno 28] No space left on device"
    assert "Not enough free space" in explain(sample)

    # Via byte parameters
    assert explain("", free_bytes=1000, needed_bytes=2 * 1024**3) == "Not enough free space. Needs about 2.0 GB."


def test_invalid_link():
    sample = "ERROR: [generic] 'httpx://not_valid': is not a valid URL"
    assert explain(sample) == "Please paste a valid YouTube link."


def test_unknown_error_fallback():
    sample = "Some totally unknown trace at line 42 with weird cryptic message 0xDEADBEEF"
    assert explain(sample) == "Something went wrong. Open Settings and press Export log to see the details."

    # None and empty string
    assert explain("") == "Something went wrong. Open Settings and press Export log to see the details."
