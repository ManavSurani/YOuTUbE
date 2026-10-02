# Phase 11 — Android App (optional, only after Windows is released)

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** a separate Android app (`.apk`) with the same idea and the same look. It is a **separate project** (new repo/folder); do not touch the Windows project.
**Reads first:** `00_AGENT_BRIEF.md`, `02_DESIGN_SYSTEM.md` (same colours, same minimalism). The "no terminal" rule holds trivially, but the "no unnecessary code" and "touch only listed files" rules still apply.

Android cannot run `yt-dlp.exe`, so this app uses the `youtubedl-android` library (bundles yt-dlp, Python, ffmpeg). Check the library's current README for setup and the FFmpeg add-on before Chunk 11.2.

| Part | Choice |
|---|---|
| Language / UI | Kotlin + Jetpack Compose |
| Engine | `youtubedl-android` |
| Background | Foreground Service + progress notification |
| History | Room (SQLite) |
| Network | `ConnectivityManager` network callback |
| Save location | MediaStore (`Downloads/`, `Movies/`, `Music/`) |

---

## Chunk 11.1 — Project, theme, icon
**Files:** new Android project; theme file; adaptive icon built from `assets/logo.svg`.
**Verify**
- [ ] App opens an empty screen with the dark theme from the colour table and the red logo as launcher icon.
- [ ] App name comes from one string resource.

## Chunk 11.2 — Engine and info
**Files:** engine wrapper, info screen.
**Verify**
- [ ] Library initialises on first start; pasting a link shows title, thumbnail and a quality list built from real data.
- [ ] Link cleaning matches the Windows rules (`&list=`, `&t=` removed).

## Chunk 11.3 — Download service and progress
**Files:** foreground service, notification, progress screen.
**Verify**
- [ ] Video (best quality, audio merged) and audio (best original + MP3) download.
- [ ] Progress shows percent, speed, ETA; leaving the app keeps downloading with a notification; Cancel works.
- [ ] Files appear in the Gallery/Music app via MediaStore.

## Chunk 11.4 — History
**Files:** Room entities, history screen.
**Verify**
- [ ] Items saved, filter All/Video/Audio, play, delete, re-download; works offline.

## Chunk 11.5 — Network monitor
**Files:** network callback, UI lock.
**Verify**
- [ ] Airplane mode: link box locks, one message, History still works; download resumes when back.

## Chunk 11.6 — Updates
**Files:** update logic.
**Verify**
- [ ] yt-dlp updates at launch (at most once per 24 h) via the library's update call.
- [ ] App update: reads the same `version.json`, downloads the APK, checks SHA-256, prompts install.

## Chunk 11.7 — Sign and distribute
**Files:** signing config, release notes.
**Verify**
- [ ] Release APK signed with **one fixed keystore** (stored safely and backed up).
- [ ] Installing a newer APK over an older one works and keeps history.
- [ ] Shared by direct link (Google Play does not accept this kind of app); "Install unknown apps" steps written for users.

---

## Phase 11 verification (all must pass)
- [ ] All chunk Verify lists checked on a real phone (Android 10+) and one emulator.
- [ ] Design matches the Windows app. User said "release".
