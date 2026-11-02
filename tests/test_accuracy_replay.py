"""Automated replay test verifying download progress accuracy, monotonicity, and continuity.

Requirement A1:
- Total size is within 5% of true final size at 5%, 50%, and 95% milestones.
- Emitted percentage is strictly non-decreasing across all stream transitions.
- Audio stage smoothly progresses toward 99.9% without artificial freezes.
- Single combined stream formats uncap cleanly above 95%.
- Resumed jobs preserve initial_done_bytes and floor_percent.
"""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from app.core.downloader import DownloadWorker


TRUE_FINAL_BYTES = 20_040_000  # 18 MB video + 2.04 MB audio (120s duration)


class MockFixtureProcess:
    def __init__(self, fixture_lines):
        self.fixture_lines = fixture_lines
        self.returncode = 0

    @property
    def stdout(self):
        for line in self.fixture_lines:
            yield line

    def wait(self):
        return self.returncode


def test_dual_stream_fixture_replay_total_accuracy_and_monotonicity(monkeypatch, tmp_path):
    """Phase 6 / A1: Replay dual-stream fixture and verify 5% accuracy at 5/50/95% and strict monotonicity."""
    fixture_path = Path(__file__).parent / "fixtures" / "progress_dual.txt"
    assert fixture_path.is_file(), f"Fixture missing: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        fixture_lines = [l for l in f if not l.startswith("#")]

    proc = MockFixtureProcess(fixture_lines)
    monkeypatch.setattr("app.core.downloader.start_hidden", lambda cmd: proc)
    monkeypatch.setattr("app.core.downloader.kill_tree", lambda p: None)
    monkeypatch.setattr("app.core.downloader.resolve_final_path", lambda p, v, o: str(tmp_path / "final_output.mkv"))

    worker = DownloadWorker(
        ["dummy_cmd"],
        out_dir=tmp_path,
        duration_seconds=120,
        is_dual_stream=True,
    )

    emitted_progress = []
    worker.progress.connect(lambda pct, spd, eta, done, tot: emitted_progress.append((pct, spd, eta, done, tot)))

    stages = []
    worker.stage.connect(lambda s: stages.append(s))

    worker.run()

    assert len(emitted_progress) > 0, "No progress emitted during replay"

    # 1. Monotonicity check: percentage must never decrease
    percentages = [p[0] for p in emitted_progress]
    for i in range(1, len(percentages)):
        assert percentages[i] >= percentages[i - 1], (
            f"Monotonicity violation at step {i}: {percentages[i]} < {percentages[i - 1]}"
        )

    # 2. Check 5%, 50%, and 95% accuracy milestones
    # True final size is 20,040,000 bytes. Allowed error is 5% (+/- 1,002,000 bytes)
    tolerance = 0.05

    milestone_5 = [p for p in emitted_progress if p[3] == 1_002_000]
    assert len(milestone_5) >= 1, "5% milestone (done=1002000) not found in emits"
    tot_5 = milestone_5[0][4]
    rel_error_5 = abs(tot_5 - TRUE_FINAL_BYTES) / TRUE_FINAL_BYTES
    assert rel_error_5 <= tolerance, (
        f"Total at 5% ({tot_5}) deviated by {rel_error_5:.2%} (> {tolerance:.0%})"
    )

    milestone_50 = [p for p in emitted_progress if p[3] == 10_020_000]
    assert len(milestone_50) >= 1, "50% milestone (done=10020000) not found in emits"
    tot_50 = milestone_50[0][4]
    rel_error_50 = abs(tot_50 - TRUE_FINAL_BYTES) / TRUE_FINAL_BYTES
    assert rel_error_50 <= tolerance, (
        f"Total at 50% ({tot_50}) deviated by {rel_error_50:.2%} (> {tolerance:.0%})"
    )

    milestone_95 = [p for p in emitted_progress if p[3] == 19_038_000]
    assert len(milestone_95) >= 1, "95% milestone (done=19038000) not found in emits"
    tot_95 = milestone_95[0][4]
    rel_error_95 = abs(tot_95 - TRUE_FINAL_BYTES) / TRUE_FINAL_BYTES
    assert rel_error_95 <= tolerance, (
        f"Total at 95% ({tot_95}) deviated by {rel_error_95:.2%} (> {tolerance:.0%})"
    )

    # 3. Audio stage smoothness: verify progress rises steadily throughout audio download
    # Audio starts at 18M bytes done, ends at 20.04M bytes done
    audio_emits = [p for p in emitted_progress if 18_000_000 <= p[3] < 20_040_000]
    assert len(audio_emits) >= 3, "Insufficient audio stage emits"
    audio_pcts = [p[0] for p in audio_emits]
    # Check that audio progresses upward without freezing
    assert audio_pcts[-1] > audio_pcts[0], (
        f"Audio stage did not progress upward: {audio_pcts[0]} -> {audio_pcts[-1]}"
    )
    # Final emit must be 100%
    assert percentages[-1] == 100.0


def test_single_stream_fixture_replay_uncaps_above_95(monkeypatch, tmp_path):
    """Phase 6 / A1: Single stream combined format dynamically uncaps and reaches >= 99%."""
    single_stream_lines = [
        "[download] Destination: combined.mp4\n",
        "[download] YTPROG|downloading|100000|10000000|10000000|1000000|10|avc1.4d401e|mp4a.40.2\n",
        "[download] YTPROG|downloading|5000000|10000000|10000000|1500000|5|avc1.4d401e|mp4a.40.2\n",
        "[download] YTPROG|downloading|9800000|10000000|10000000|2000000|1|avc1.4d401e|mp4a.40.2\n",
        "[download] YTPROG|downloading|9950000|10000000|10000000|2000000|0|avc1.4d401e|mp4a.40.2\n",
        "[download] YTPROG|finished|10000000|10000000|10000000|NA|0|avc1.4d401e|mp4a.40.2\n",
        "[download] Done\n",
    ]

    proc = MockFixtureProcess(single_stream_lines)
    monkeypatch.setattr("app.core.downloader.start_hidden", lambda cmd: proc)
    monkeypatch.setattr("app.core.downloader.kill_tree", lambda p: None)
    monkeypatch.setattr("app.core.downloader.resolve_final_path", lambda p, v, o: str(tmp_path / "combined.mp4"))

    worker = DownloadWorker(
        ["dummy_cmd"],
        out_dir=tmp_path,
        duration_seconds=60,
        is_dual_stream=True,  # Initially marked dual-stream, must dynamically switch to single
    )

    emitted_pcts = []
    worker.progress.connect(lambda pct, spd, eta, done, tot: emitted_pcts.append(pct))

    worker.run()

    # Must uncap and reach >= 99.0% before 100% finish
    pre_finish_pcts = [p for p in emitted_pcts if p < 100.0]
    assert any(p >= 99.0 for p in pre_finish_pcts), (
        f"Single stream job was capped below 99%: max pre-finish was {max(pre_finish_pcts)}"
    )
    assert emitted_pcts[-1] == 100.0


def test_mid_stream_resume_preserves_bytes_and_floor(monkeypatch, tmp_path):
    """Phase 6 / A1: Mid-stream resume preserves initial_done_bytes and floor_percent monotonically."""
    resumed_lines = [
        "[download] Destination: resume.mp4\n",
        "[download] YTPROG|downloading|12000000|18000000|18000000|2000000|3|av01.0.05M.08|none\n",
        "[download] YTPROG|downloading|15000000|18000000|18000000|2500000|2|av01.0.05M.08|none\n",
        "[download] YTPROG|finished|18000000|18000000|18000000|NA|0|av01.0.05M.08|none\n",
        "[download] Done\n",
    ]

    proc = MockFixtureProcess(resumed_lines)
    monkeypatch.setattr("app.core.downloader.start_hidden", lambda cmd: proc)
    monkeypatch.setattr("app.core.downloader.kill_tree", lambda p: None)
    monkeypatch.setattr("app.core.downloader.resolve_final_path", lambda p, v, o: str(tmp_path / "resume.mp4"))

    initial_done = 10_020_000
    floor_pct = 50.0

    worker = DownloadWorker(
        ["dummy_cmd"],
        out_dir=tmp_path,
        duration_seconds=120,
        is_dual_stream=True,
        floor_percent=floor_pct,
        initial_done_bytes=initial_done,
    )

    emitted_records = []
    worker.progress.connect(lambda pct, spd, eta, done, tot: emitted_records.append((pct, done)))

    worker.run()

    for pct, done in emitted_records:
        assert pct >= floor_pct, f"Percent dropped below floor {floor_pct}: {pct}"
        assert done >= initial_done, f"Done bytes dropped below initial {initial_done}: {done}"


# ---------------------------------------------------------------------------
# Plan 21: exact stream sizes from the .sizes file
# ---------------------------------------------------------------------------

def _replay(monkeypatch, tmp_path, lines, sizes_text=None, **worker_kwargs):
    proc = MockFixtureProcess(lines)
    monkeypatch.setattr("app.core.downloader.start_hidden", lambda cmd: proc)
    monkeypatch.setattr("app.core.downloader.kill_tree", lambda p: None)
    monkeypatch.setattr("app.core.downloader.resolve_final_path", lambda p, v, o: str(tmp_path / "final_output.mkv"))
    worker = DownloadWorker(["dummy_cmd"], out_dir=tmp_path, is_dual_stream=True, **worker_kwargs)
    worker._sizes_file = tmp_path / "job.sizes"
    if sizes_text is not None:
        worker._sizes_file.write_text(sizes_text, encoding="utf-8")
    emitted = []
    worker.progress.connect(lambda pct, spd, eta, done, tot: emitted.append((pct, done, tot)))
    worker.run()
    return emitted


def _fixture_lines():
    fixture_path = Path(__file__).parent / "fixtures" / "progress_dual.txt"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return [l for l in f if not l.startswith("#")]


def test_exact_sizes_total_fixed_from_first_tick(monkeypatch, tmp_path):
    """Plan 21: with exact sizes, the total is the true download size from the first tick (no audio guess)."""
    emitted = _replay(monkeypatch, tmp_path, _fixture_lines(), "18000000|2040000\n", duration_seconds=7200)

    totals = [tot for _, _, tot in emitted if tot > 0]
    assert totals and all(t == TRUE_FINAL_BYTES for t in totals), f"Totals not fixed: {sorted(set(totals))}"
    pcts = [p for p, _, _ in emitted]
    assert all(b >= a for a, b in zip(pcts, pcts[1:]))
    assert max(done for _, done, _ in emitted) == TRUE_FINAL_BYTES


def test_no_sizes_file_keeps_old_totals(monkeypatch, tmp_path):
    """Plan 21: without a sizes file the old estimate path runs unchanged."""
    emitted = _replay(monkeypatch, tmp_path, _fixture_lines(), None, duration_seconds=7200)

    assert [tot for _, _, tot in emitted] == [140_400_000] * 10 + [20_040_000] * 8


_RESUMED_AUDIO_LINES = [
    "[download] Destination: tmp_audio.m4a\n",
    "[download] YTPROG|downloading|1000000|2040000|2040000|500000|2|none|opus\n",
    "[download] YTPROG|downloading|1600000|2040000|2040000|540000|1|none|opus\n",
    "[download] YTPROG|downloading|2040000|2040000|2040000|550000|0|none|opus\n",
    "[download] YTPROG|finished|2040000|2040000|2040000|NA|0|none|opus\n",
    "[Merger] Merging formats into 'final_output.mkv'\n",
]


@pytest.mark.parametrize("sizes_text", ["18000000|2040000\n", "18000000|2040000\n18000000|2040000\n"])
def test_resume_mid_audio_with_exact_sizes(monkeypatch, tmp_path, sizes_text):
    """Plan 21 Phase 2: resuming during audio must not count the partial audio twice."""
    emitted = _replay(
        monkeypatch, tmp_path, _RESUMED_AUDIO_LINES, sizes_text,
        duration_seconds=120, initial_done_bytes=19_000_000, floor_percent=96.0,
    )

    for pct, done, tot in emitted:
        assert tot == TRUE_FINAL_BYTES
        assert done <= tot, f"done {done} > total {tot}"
        assert pct >= 96.0
    pcts = [p for p, _, _ in emitted]
    assert all(b >= a for a, b in zip(pcts, pcts[1:]))
    assert emitted[-1][1] == TRUE_FINAL_BYTES


def test_streamed_video_hides_total(monkeypatch, tmp_path):
    """Streamed (HLS) video: no reliable total, so the UI gets total 0 (shows only downloaded bytes)."""
    emitted = _replay(monkeypatch, tmp_path, _fixture_lines(), "NA|2040000|m3u8_native\n", duration_seconds=120)
    assert emitted and all(tot == 0 for _, _, tot in emitted)
    pcts = [p for p, _, _ in emitted]
    assert all(b >= a for a, b in zip(pcts, pcts[1:])) and max(pcts) > 50  # the bar still moves

