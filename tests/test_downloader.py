from app.core.downloader import (
    build_video_cmd,
    build_audio_cmd,
    parse_line,
    ParsedOutput,
    DownloadWorker,
)


def test_build_video_cmd_best():
    cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", container="mkv")
    assert "-f" in cmd
    idx = cmd.index("-f")
    assert cmd[idx + 1] == "bv*+ba/b"
    assert "--merge-output-format" in cmd
    assert "mkv" in cmd
    assert "--no-playlist" in cmd
    assert "--newline" in cmd
    assert "--ffmpeg-location" in cmd


def test_build_video_cmd_height():
    cmd = build_video_cmd("https://www.youtube.com/watch?v=abc12345678", height=1080, container="mp4")
    assert "-f" in cmd
    idx = cmd.index("-f")
    assert cmd[idx + 1] == "bv*[height<=1080]+ba/b[height<=1080]"
    assert "--merge-output-format" in cmd
    assert "mp4" in cmd


def test_build_audio_cmd_best_original():
    cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt="best")
    assert "-f" in cmd
    idx = cmd.index("-f")
    assert cmd[idx + 1] == "ba"
    assert "-x" in cmd


def test_build_audio_cmd_mp3():
    cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt="mp3")
    assert "-f" in cmd
    assert "-x" in cmd
    assert "--audio-format" in cmd
    idx = cmd.index("--audio-format")
    assert cmd[idx + 1] == "mp3"
    assert "--audio-quality" in cmd
    idx_q = cmd.index("--audio-quality")
    assert cmd[idx_q + 1] == "0"


def test_build_audio_cmd_flac():
    cmd = build_audio_cmd("https://www.youtube.com/watch?v=abc12345678", fmt="flac")
    assert "-f" in cmd
    assert "-x" in cmd
    assert "--audio-format" in cmd
    idx = cmd.index("--audio-format")
    assert cmd[idx + 1] == "flac"


def test_parse_line_progress():
    line = "download:  52.4%|  4.82MiB/s|00:08|15.20MiB|29.01MiB"
    res = parse_line(line)
    assert res.kind == "progress"
    assert res.progress is not None
    assert res.progress.percent == 52.4
    assert res.progress.speed == "4.82MiB/s"
    assert res.progress.eta == "00:08"
    assert res.progress.done_str == "15.20MiB"
    assert res.progress.total_str == "29.01MiB"


def test_parse_line_merger():
    line = "[Merger] Merging formats into 'video.mkv'"
    res = parse_line(line)
    assert res.kind == "stage"
    assert res.stage == "Merging"


def test_parse_line_extract_audio():
    line = "[ExtractAudio] Destination: song.mp3"
    res = parse_line(line)
    assert res.kind == "stage"
    assert res.stage == "Converting audio"


def test_parse_line_garbage():
    line = "some random warning [download] 100% of 10.00KiB in 00:00:00"
    res = parse_line(line)
    assert res.kind in ("other", "progress", "stage")


def test_download_worker_signals():
    worker = DownloadWorker(["dummy_cmd"])
    assert hasattr(worker, "stage")
    assert hasattr(worker, "progress")
    assert hasattr(worker, "finished")
    assert hasattr(worker, "failed")
    assert hasattr(worker, "paused")
    assert hasattr(worker, "pause")


def test_cleanup_temp_files(tmp_path):
    from app.core.downloader import cleanup_temp_files
    part_file = tmp_path / "video.mkv.part"
    part_file.write_text("partial")
    ytdl_file = tmp_path / "video.mkv.ytdl"
    ytdl_file.write_text("meta")
    other_file = tmp_path / "video.mkv"
    other_file.write_text("complete")

    cleanup_temp_files(tmp_path)
    assert not part_file.exists()
    assert not ytdl_file.exists()
    assert other_file.exists()

