# Phase 9: Android (optional)

**Goal:** Audit the existing Android scaffold and decide whether to continue.
**Depends on:** Phase 8. Start only if the owner confirms.
**Existing code:** `android/` (Kotlin, Jetpack Compose, `DownloadService`, `HistoryDatabase`, `InfoFetcher`, `NetworkMonitor`, `MainScreen`, `MediaInfoCard`). Not reviewed in this plan.

---

## Chunk 9.1: Audit

Tasks:
1. Open the project in Android Studio, build, and record whether it compiles.
2. List what works, what is a stub, and what is missing against the Windows behaviour (Phases 1 to 6).
3. Confirm the engine approach (library that bundles yt-dlp and ffmpeg) and its update call.

## Chunk 9.2: Port the rules

Tasks:
1. Same flow and defaults as Windows: best quality with audio, real quality list, best original audio.
2. Foreground service with progress notification; shared queue; history that survives file deletion; thumbnails stored permanently.
3. Same design tokens (red and black), subtle animations.
4. Update check against `version.json`; APK download and install prompt; sign with one fixed keystore.

## Chunk 9.3: Release

Tasks:
1. Signed release APK; share through GitHub Releases. Google Play does not accept this type of app.
2. Document the "Install unknown apps" step for users.

---

## Verification Gate: Phase 9

### Automated
- [ ] Unit tests for URL tools, job snapshot, history, queue.

### Manual
- [ ] Download video and audio on a real phone; notification progress works; History correct; file deletion keeps the row; app update installs over the old version.

### No-terminal equivalent
- [ ] No visible shell or log screens; all errors are friendly messages.

### Sign-off
- [ ] All ticked.
