# YOuTUbE

A fast, quiet, minimalist Windows desktop and Android application for downloading high quality videos and audio from YouTube.

Designed strictly around the official YouTube dark and light aesthetics: zero clutter, zero terminal windows, flat UI, and reliable background operation.

---

## Features

- **Highest Quality Video Downloads:** Automatically merges the best available video stream (up to 4K / 8K AV1 / VP9) with high-bitrate audio into clean `.mkv` or `.mp4` files.
- **Audio Extraction:** Download audio in its original format or convert seamlessly to MP3, M4A, Opus, WAV, or FLAC with cover art and ID3 metadata.
- **Sequential Download Queue:** Paste multiple links and queue them up to download in order. Skip, remove, or cancel queued items individually.
- **Offline History Database:** Built-in SQLite database tracks all past downloads with thumbnails, metadata, and local file status. Play files, open containing folders, or re-download with a single click.
- **Quiet & Resilient Network Handling:** Live connection indicator pauses active downloads gracefully when internet drops, preserving `.part` files and resuming automatically on reconnection.
- **Self-Maintaining Tools:** Handles required binaries (`yt-dlp`, `ffmpeg`, `ffprobe`, `deno`) in `%APPDATA%\YOuTUbE\bin\` with automated daily updates and rollback protection.
- **Zero-Terminal Rule:** All subprocesses and background utilities run hidden with `CREATE_NO_WINDOW` and `SW_HIDE`. No terminal or command prompt flashes ever appear.
- **Cross-Platform:** Available as a Windows Desktop application and as a standalone Android app (Kotlin + Jetpack Compose).

---

## Downloads & Installation

### Windows Desktop (10 / 11 64-bit)
- **Installer:** `Output/YOuTUbE_Setup.exe` (~35.4 MB)
- **SHA-256 Checksum:** `b50ddb23efac5e8da670f452b3d4dc58fb1cb69d4f2c4f3b2aa11acb4caa3403`
- **Installation:** Run `YOuTUbE_Setup.exe`. Installs to `%LOCALAPPDATA%\Programs\YOuTUbE` with 0 administrator elevation prompts and automatically creates Start Menu and Desktop shortcuts.

### Android (Android 8.0+)
- **APK Package:** `Output/YOuTUbE.apk` (~135.2 MB)
- **SHA-256 Checksum:** `A661171D82FCF76828EF4274550D7B9EFEB25A78E79684D0DB56D9306E3D2E30`
- **Installation:** Transfer `YOuTUbE.apk` to your Android device, open it, and allow installation from unknown apps. Works with Android share sheet: share any video from the YouTube app directly into YOuTUbE!

---

## Building from Source

### Windows Application
```bash
# Clone the repository
git clone https://github.com/Jay/YOuTUbE.git
cd YOuTUbE

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run in development mode
python -m app.main

# Run test suite
pytest

# Build standalone folder & installer
build\build_installer.bat
```

### Android Application
```bash
cd android

# Build debug APK
gradlew.bat assembleDebug

# Build signed release APK
gradlew.bat assembleRelease
```
The output APK is generated at `android/app/build/outputs/apk/release/app-release.apk` (and mirrored to `Output/YOuTUbE.apk`).

---

## Open-Source Credits & Attribution

This software is built upon the following open-source tools:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — YouTube extraction and streaming engine.
- **[youtubedl-android](https://github.com/yausername/youtubedl-android)** — Android port of yt-dlp, FFmpeg, and Python runtime.
- **[FFmpeg & FFprobe](https://ffmpeg.org)** — Audio/video stream demuxing, merging, and conversion.
- **[Deno](https://deno.com)** — Fast, secure JavaScript engine for extraction challenges.
- **[PySide6](https://pypi.org/project/PySide6/)** — Qt 6 Python framework for native Windows GUI.
- **[Jetpack Compose](https://developer.android.com/jetpack/compose)** — Modern declarative UI toolkit for Android.

---

## License

This project is licensed under the MIT License.
