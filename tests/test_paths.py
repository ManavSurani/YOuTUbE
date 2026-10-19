"""Tests for app.core.paths functions, specifically job_tmp_dir and purge_stale_tmp."""

import json
import os
import time
from pathlib import Path

import app.core.paths as paths_mod
from app.core.paths import job_tmp_dir, purge_stale_tmp


def test_job_tmp_dir_deterministic():
    d1 = job_tmp_dir("job-123-abc")
    d2 = job_tmp_dir("job-123-abc")
    assert d1 == d2
    assert d1.parent == paths_mod.TMP_DIR
    assert len(d1.name) <= 12


def test_purge_stale_tmp_deletes_old_and_preserves_young(tmp_path, monkeypatch):
    fake_app_data = tmp_path / "AppData"
    fake_tmp = fake_app_data / "tmp"
    fake_tmp.mkdir(parents=True)
    monkeypatch.setattr(paths_mod, "APP_DATA", fake_app_data)
    monkeypatch.setattr(paths_mod, "TMP_DIR", fake_tmp)

    now = time.time()
    old_time = now - (8 * 86400)
    young_time = now - (2 * 86400)

    # 1. Old empty dir
    old_empty = fake_tmp / "old_empty"
    old_empty.mkdir()
    os.utime(old_empty, (old_time, old_time))

    # 2. Old dir with part file
    old_with_part = fake_tmp / "old_with_part"
    old_with_part.mkdir()
    part_file = old_with_part / "vid.mp4.part"
    part_file.write_text("data")
    os.utime(part_file, (old_time, old_time))
    os.utime(old_with_part, (old_time, old_time))

    # 3. Old loose file
    old_file = fake_tmp / "stale.path"
    old_file.write_text("path")
    os.utime(old_file, (old_time, old_time))

    # 4. Young dir with part file
    young_dir = fake_tmp / "young_dir"
    young_dir.mkdir()
    young_part = young_dir / "vid2.mp4.part"
    young_part.write_text("data2")
    os.utime(young_part, (young_time, young_time))
    os.utime(young_dir, (young_time, young_time))

    purge_stale_tmp(max_age_days=7)

    assert not old_empty.exists(), "Old empty directory must be purged"
    assert not old_with_part.exists(), "Old directory with part file must be purged"
    assert not old_file.exists(), "Old loose file must be purged"
    assert young_dir.exists(), "Young directory must be preserved"
    assert young_part.exists(), "Young part file must be preserved"


def test_purge_stale_tmp_preserves_queued_jobs_even_if_old(tmp_path, monkeypatch):
    fake_app_data = tmp_path / "AppData"
    fake_tmp = fake_app_data / "tmp"
    fake_tmp.mkdir(parents=True)
    monkeypatch.setattr(paths_mod, "APP_DATA", fake_app_data)
    monkeypatch.setattr(paths_mod, "TMP_DIR", fake_tmp)

    # Setup queue_video.json and queue_audio.json with active jobs
    video_job_id = "v-job-77777777"
    audio_job_id = "a-job-88888888"
    (fake_app_data / "queue_video.json").write_text(
        json.dumps([{"job_id": video_job_id, "url": "https://youtu.be/1"}]),
        encoding="utf-8",
    )
    (fake_app_data / "queue_audio.json").write_text(
        json.dumps([{"job_id": audio_job_id, "url": "https://youtu.be/2"}]),
        encoding="utf-8",
    )

    now = time.time()
    old_time = now - (10 * 86400)

    # Folders matching job_tmp_dir for queued jobs
    v_dir = paths_mod.job_tmp_dir(video_job_id)
    v_dir.mkdir(parents=True)
    v_part = v_dir / "vid.mp4.part"
    v_part.write_text("video partial")
    os.utime(v_part, (old_time, old_time))
    os.utime(v_dir, (old_time, old_time))

    a_dir = paths_mod.job_tmp_dir(audio_job_id)
    a_dir.mkdir(parents=True)
    a_part = a_dir / "aud.webm.part"
    a_part.write_text("audio partial")
    os.utime(a_part, (old_time, old_time))
    os.utime(a_dir, (old_time, old_time))

    # An old unqueued job folder
    unqueued_dir = fake_tmp / "unqueued123"
    unqueued_dir.mkdir(parents=True)
    u_part = unqueued_dir / "unq.mp4.part"
    u_part.write_text("unqueued partial")
    os.utime(u_part, (old_time, old_time))
    os.utime(unqueued_dir, (old_time, old_time))

    purge_stale_tmp(max_age_days=7)

    # Queued jobs' folders must be preserved even though they are 10 days old
    assert v_dir.exists(), "Video queued job temp dir must be preserved"
    assert v_part.exists()
    assert a_dir.exists(), "Audio queued job temp dir must be preserved"
    assert a_part.exists()

    # Unqueued old dir must be deleted
    assert not unqueued_dir.exists(), "Unqueued old dir must be purged"
