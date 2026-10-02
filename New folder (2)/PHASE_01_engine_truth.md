# Phase 1: Engine Truth

**Goal:** Real progress, correct final file path for every title, safe temp handling and cancel, and tests that use real yt-dlp output.
**Fixes:** B1, B2, B3, B4, B16. **Depends on:** nothing.
**Files:** `core/downloader.py`, `core/paths.py`, `core/proc.py`, `tests/`.

---

## Chunk 1.1: Contract test harness (do this first)

Tasks:
1. `tests/conftest.py`: fixture that creates a 30 MB `clip.mp4`, serves it with a local HTTP server on a free port, and yields the URL.
2. Helper `run_ytdlp(args)` that uses the same hidden runner the app uses.
3. First test reproduces the bugs: run the current command and assert that **no** progress lines appear (this test is expected to fail after the fix and is then inverted).

Done when: the harness runs on your PC with the app's own `yt-dlp.exe` and shows current behaviour.

---

## Chunk 1.2: Progress contract (fixes B1, B2)

Tasks:
1. Remove `--print after_move:filepath` from both command builders.
2. New progress template with your own marker, numeric fields and stream type:
   `download:YTPROG|%(progress.status)s|%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.eta)s|%(info.vcodec)s|%(info.acodec)s`
3. Post-process template for stages:
   `postprocess:YTPOST|%(progress.status)s|%(progress.postprocessor)s`
4. Parse numbers (not formatted strings). Percent = downloaded / (total or estimate). Missing values (`NA`) must not crash.
5. Stream type: `vcodec != none` means "Downloading video"; `vcodec == none` means "Downloading audio". Stage `Merger` means "Merging"; `ExtractAudio` means "Converting audio".
6. Overall percent: weight the streams by their sizes when known (otherwise 85/10/5 split), never go backwards, reach 100 only at success.
7. Format speed and ETA in the parser: `12.4 MB/s`, `01:20`.

Done when: contract test shows monotonic progress from 0 to 100 with speed and ETA, and stage names change correctly for a video+audio download and for an MP3 conversion.

---

## Chunk 1.3: Correct final path (fixes B3)

Tasks:
1. Add `--print-to-file after_move:filepath <appdata>\tmp\<job_id>.path`. yt-dlp writes this file in UTF-8.
2. After exit code 0, read the file (UTF-8), take the last non-empty line, and verify it exists.
3. Fallback if missing: search the output folder for files containing `[<video_id>]` in the name, newest first, ignoring `.part`, `.ytdl` and `.f123.` temp names.
4. If still nothing: report a friendly error and log everything. Never record an empty path.
5. Record the real size using `os.stat` on the verified path.
6. Remove the `endswith(".mkv")` stdout path guessing in `parse_line`.

Done when: contract tests pass for filenames with `｜ ： ⧸ é 日本語 😀`, including with `PYTHONIOENCODING=cp1252`.

---

## Chunk 1.4: Safe temp folder and cancel (fixes B4)

Tasks:
1. Add `TMP_DIR = %APPDATA%\YOuTUbE\tmp` in `paths.py`.
2. Add `-P temp:<TMP_DIR>` so partial files live in the app's own folder.
3. `cancel()` kills the process tree, then deletes only files inside `TMP_DIR` that belong to that job.
4. Delete `cleanup_temp_files(out_dir)` and every caller that scans the user's Downloads.
5. On startup, remove stale files in `TMP_DIR` older than 7 days.

Done when: a test places `foo.part` in the download folder, cancels a download, and `foo.part` is still there.

---

## Chunk 1.5: Command builders

Tasks:
1. `build_video_cmd(job)` and `build_audio_cmd(job)` take a job object (introduced in Phase 2) or a plain dict for now.
2. Remove the `container` argument. Video always `--merge-output-format mkv`.
3. Audio: always add `--embed-metadata`. Add `--embed-thumbnail` for MP3, M4A, FLAC and Opus, and make failures non-fatal (`--ignore-errors` is not enough; run the embed step as best effort and log it).
4. Output template: `%(title)s [%(id)s].%(ext)s` with `--windows-filenames` and `--trim-filenames 150` to avoid long-path failures.
5. Always: `--no-playlist --continue --newline --ffmpeg-location <bin>`.

Done when: command string tests assert exact output for video best, video 720p, audio best, audio MP3.

---

## Verification Gate: Phase 1

Evidence in `docs/verification/phase_1.md`.

### Automated
- [ ] Contract tests pass using real yt-dlp (progress, stages, path, special characters, cp1252 simulation).
- [ ] Command-builder tests pass.
- [ ] Cancel test proves unrelated `.part` files are untouched.
- [ ] Old fake-line tests replaced or kept only for the parser's error handling.
- [ ] Scan test: no `subprocess` outside `core/proc.py`.

### Manual (on your PC with real YouTube)
- [ ] Download the Hal Jordan video that failed before (`Bm4XryaNzYg`): the file exists, History would show the correct path and size.
- [ ] Download it as MP3: correct file and size.
- [ ] Progress bar moves smoothly with speed, ETA, stage names ("Downloading video", "Downloading audio", "Merging").
- [ ] Cancel mid-download: the app's temp files are gone, a dummy `x.part` in Downloads is untouched.

### No-terminal check (mandatory)
- [ ] Run video and MP3 downloads from the packaged or `pythonw` build. No window flashes, including during merge and conversion.

### Sign-off
- [ ] All ticked and evidence saved. Then start Phase 2.
