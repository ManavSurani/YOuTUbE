# Phase 10 — Testing and Release

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** prove the whole product works on clean machines, then publish it. This phase changes no app code unless a test finds a bug; if it does, fix only that bug in the file that owns it and re-run the failed chunk's Verify list.
**Reads first:** `00_AGENT_BRIEF.md`.

---

## Chunk 10.1 — Clean install tests

**Files you may touch:** none (testing only).

**Verify**
- [ ] Fresh Windows 10 VM: no Python, no yt-dlp, no ffmpeg → install works, tools download, first download succeeds.
- [ ] Fresh Windows 11 VM: same.
- [ ] Desktop shortcut present after install and opens the app.
- [ ] Install → uninstall → reinstall leaves nothing broken.

## Chunk 10.2 — Offline and network cases

**Verify**
- [ ] Install with internet off: installer finishes; app says "Internet is required for first-time setup" and recovers when online.
- [ ] Wi-Fi off during a download: one popup, UI locks, download resumes when back.
- [ ] History opens, plays, filters and deletes while offline.

## Chunk 10.3 — Download matrix

**Verify**
- [ ] 4K video → one merged file with audio, plays.
- [ ] 720p selection → 720p with audio.
- [ ] Audio default keeps the original format; MP3 converts correctly.
- [ ] Link with `&list=` and `&t=` downloads only that video.
- [ ] Cancel mid-download leaves no `.part` file.
- [ ] Queue of 3 links finishes in order.

## Chunk 10.4 — Update tests

**Verify**
- [ ] Old yt-dlp is replaced automatically; a broken update rolls back.
- [ ] App update 1.0.0 → 1.1.0: banner, download, hash check, silent install, relaunch; history, settings and tools survive; no duplicate install.
- [ ] Corrupt update (wrong hash) is rejected and deleted.

## Chunk 10.5 — Security and look

**Verify**
- [ ] Windows SmartScreen and Defender behaviour checked on a clean machine; result written down (unsigned builds show "More info → Run anyway").
- [ ] Scan `YouTube_Setup.exe` on a multi-engine scanner; note any false positives and report them to the vendors.
- [ ] Final design review against `02_DESIGN_SYSTEM.md`, dark and light.
- [ ] `grep -rn "subprocess\|os.system\|print(" app/` → only `proc.py`.

## Chunk 10.6 — Publish

**Files you may touch:** `app/version.py` (version only), `README.md`.

**Do**
1. Set the final version; build with `build_installer.bat`.
2. Create GitHub Release `v1.0.0`; upload `YouTube_Setup.exe`.
3. Fill `version.json` (version, URL, SHA-256 from the build output) and publish it at `UPDATE_MANIFEST_URL`.
4. Credit yt-dlp, ffmpeg and deno in the README and the About line.

**Verify**
- [ ] Downloading the installer from the release page and installing works end to end.
- [ ] An existing 1.0.0 install, with a test 1.0.1 release, sees the banner within 24 h (or on forced check).

---

## Phase 10 verification (all must pass)

- [ ] Chunks 10.1 to 10.6 fully checked; a written test report exists (what was tested, on which Windows version, pass/fail).
- [ ] No open bugs from this phase. User said "release".
