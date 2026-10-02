# Phase 8: QA and Release

**Goal:** A final full pass proving every requirement, then a safe release.
**Depends on:** Phases 1 to 7.

---

## Chunk 8.1: Regression suite

Tasks:
1. Run every earlier gate again in one go (`pytest`, contract tests, UI tests).
2. Add a **real-world test list** (run by hand on the PC, with videos you have the right to download): ASCII title, title with `| : /`, emoji title, non-English title, very long title, 4K video, 720p only, age-restricted (expect a friendly error), private (friendly error), a link with `&list=` and `&t=`.
3. Record results in a table in `docs/verification/phase_8.md`.

Done when: all rows pass or have an owner-approved note.

---

## Chunk 8.2: Stress and edge cases

Tasks:
1. Queue 10 items, cancel the 3rd, kill the app during the 5th, restart: the queue restores and History has no half-written rows.
2. Disk full (use a small test folder): friendly "not enough space" message.
3. Change the download folder mid-queue: running job finishes in the old folder, next jobs use the new one.
4. Rename or move the Downloads folder: History survives.
5. Run two app instances: the second focuses the first (single-instance guard).

Done when: each case behaves as written with no crash and no corrupted data.

---

## Chunk 8.3: Visual and UX review

Tasks:
1. Screenshot every state of every tab at 760 px, 1280 px and maximised, at 100%, 125% and 150% scaling.
2. Check hover, press, loading and success animations on every button type.
3. Confirm colours are unchanged versus the old build.

Done when: no clipped text, no overlap, no unstyled control.

---

## Chunk 8.4: Release

Tasks:
1. Bump version, update `version.json`, build, sign, compute SHA-256.
2. Publish a GitHub Release with the installer.
3. Test the update from the previous version on a clean PC.
4. Write short release notes.

Done when: a clean PC updates from the previous version to the new release automatically.

---

## Verification Gate: Phase 8

### Automated
- [ ] Full `pytest` passes. Contract tests pass with the shipped yt-dlp.

### Manual
- [ ] Every row of the real-world list passes.
- [ ] Every stress case passes.
- [ ] Visual review complete.
- [ ] Clean PC: install, shortcut, download video, download MP3, History, delete, update.

### No-terminal check (mandatory)
- [ ] Record a short screen capture of the full flow on the clean PC and confirm no console window appears at any moment. Save the file reference in the evidence.

### Sign-off
- [ ] All ticked. Tag the release.
