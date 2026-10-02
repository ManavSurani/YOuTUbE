r"""Real-world test matrix for Chunk 8.1.

Validates the 10 real-world scenarios:
1. ASCII title
2. Title with illegal Windows chars (| : / \ * ? " < >)
3. Emoji title (UTF-8 preservation)
4. Non-English title (Japanese, Hindi, Arabic, Cyrillic)
5. Very long title (> 150 chars, trimmed)
6. 4K video (dual stream format selector and weighted scaling)
7. 720p only video format
8. Age-restricted video error explanation
9. Private video error explanation
10. Link with &list= and &t= stripped to clean single video URL
"""

from pathlib import Path
import pytest

from app.core.url_tools import clean_url, is_youtube_url, extract_video_id
from app.core.downloader import build_video_cmd, build_audio_cmd, resolve_final_path, parse_line
from app.core.errors import explain


def test_scenario_1_ascii_title():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert is_youtube_url(url)
    cmd = build_video_cmd(url, height=1080)
    assert "--windows-filenames" in cmd
    assert "--trim-filenames" in cmd
    assert cmd[cmd.index("--trim-filenames") + 1] == "150"


def test_scenario_2_illegal_windows_characters(tmp_path: Path):
    """Illegal characters like | : / are sanitized by yt-dlp and resolve_final_path finds file."""
    # When yt-dlp processes "Title: Part 1 | /Test", windows-filenames replaces them
    vid = "abc12345678"
    sanitized_file = tmp_path / f"Title - Part 1 _ _Test [{vid}].mkv"
    sanitized_file.write_bytes(b"content")

    path_file = tmp_path / "job.path"
    path_file.write_text(str(sanitized_file) + "\n", encoding="utf-8")

    resolved = resolve_final_path(path_file, vid, tmp_path)
    assert resolved == str(sanitized_file)


def test_scenario_3_emoji_title(tmp_path: Path):
    """Emoji titles preserved via UTF-8 without ANSI code-page mojibake."""
    vid = "emoji123456"
    emoji_file = tmp_path / f"🎵 Great Music 🔥 Beats [{vid}].mkv"
    emoji_file.write_bytes(b"content")

    path_file = tmp_path / "job.path"
    path_file.write_text(str(emoji_file) + "\n", encoding="utf-8")

    resolved = resolve_final_path(path_file, vid, tmp_path)
    assert resolved == str(emoji_file)
    assert "🎵" in resolved
    assert "🔥" in resolved


def test_scenario_4_non_english_multilingual(tmp_path: Path):
    """Multilingual titles (Japanese, Hindi, Arabic, Cyrillic) resolve cleanly."""
    vid = "multi123456"
    target_file = tmp_path / f"日本語タイトル - हिन्दी - بالعربية - Русский [{vid}].mkv"
    target_file.write_bytes(b"content")

    path_file = tmp_path / "job.path"
    path_file.write_text(str(target_file) + "\n", encoding="utf-8")

    resolved = resolve_final_path(path_file, vid, tmp_path)
    assert resolved == str(target_file)
    assert "日本語" in resolved
    assert "हिन्दी" in resolved


def test_scenario_5_very_long_title(tmp_path: Path):
    """Long titles are trimmed to 150 chars via --trim-filenames to prevent MAX_PATH error."""
    url = "https://www.youtube.com/watch?v=longtitle123"
    cmd = build_video_cmd(url)
    assert "--trim-filenames" in cmd
    idx = cmd.index("--trim-filenames")
    assert cmd[idx + 1] == "150"

    # Scanner fallback also handles long titles
    vid = "longtitle123"
    long_prefix = "A" * 140
    long_file = tmp_path / f"{long_prefix} [{vid}].mkv"
    long_file.write_bytes(b"data")

    # Scanner finds it by [vid]
    resolved = resolve_final_path(tmp_path / "missing.path", vid, tmp_path)
    assert resolved == str(long_file)


def test_scenario_6_4k_video_dual_stream():
    """4K quality selector uses height<=2160 and merge-output-format mkv."""
    url = "https://www.youtube.com/watch?v=4kvideo1234"
    cmd = build_video_cmd(url, height=2160)
    assert "-f" in cmd
    idx = cmd.index("-f")
    assert "height<=2160" in cmd[idx + 1]
    assert "--merge-output-format" in cmd
    assert cmd[cmd.index("--merge-output-format") + 1] == "mkv"


def test_scenario_7_720p_video():
    """720p selector restricts streams to 720."""
    url = "https://www.youtube.com/watch?v=720pvideo12"
    cmd = build_video_cmd(url, height=720)
    idx = cmd.index("-f")
    assert "height<=720" in cmd[idx + 1]


def test_scenario_8_age_restricted_error():
    """Age restriction returns clear, friendly explanation."""
    raw = "ERROR: [youtube] 12345: Sign in to confirm your age. This video may be inappropriate for some users."
    msg = explain(raw)
    assert "age restricted" in msg.lower()
    assert "sign-in" in msg.lower()


def test_scenario_9_private_video_error():
    """Private / members-only videos return friendly explanation."""
    raw = "ERROR: [youtube] priv123: Private video. Sign in if you've been granted access to this video"
    msg = explain(raw)
    assert "private" in msg.lower() or "members-only" in msg.lower()


def test_scenario_10_clean_url_strips_playlist_and_timestamp():
    """URL with &list= and &t= is sanitized to pure single watch link."""
    dirty = "https://www.youtube.com/watch?v=abcdefghijk&list=PL1234567890&index=4&t=120s"
    clean = clean_url(dirty)
    assert clean == "https://www.youtube.com/watch?v=abcdefghijk"
    assert "list=" not in clean
    assert "t=" not in clean
    assert "index=" not in clean
