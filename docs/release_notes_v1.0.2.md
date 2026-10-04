# Release Notes — YOuTUbE v1.0.2

**Release Date:** October 5, 2026  
**Installer:** `Output/YOuTUbE_Setup.exe`  
**SHA-256:** `cda03a2a0201ee61b391267d25fddf3f97dd6ac15fa4e84ad08f82200ce99aeb`

---

## What's New in v1.0.2

### Clean, Responsive Interface
- **Smooth State Flow:** Video and Audio tabs now cleanly transition between Idle, Fetching, Ready, and Downloading states without premature controls or missing buttons.
- **Accurate Download Progress:** Live progress card displays title, thumbnail, current stage, download percentage, speed, ETA, and file size.
- **Queue & Recently Downloaded:** Sequential download queue only appears when jobs are queued or need attention. Recently downloaded items list your last 5 downloads with direct Play and Open folder actions.
- **"See All" History:** Click "See all video history" or "See all audio history" to jump straight into your history filtered to that media type.

### Rock-Solid File and Folder Actions
- **Play & Open in Folder:** Playing downloaded files launches your system's default media player immediately. Opening a folder opens File Explorer and highlights the exact downloaded file without opening terminal windows.
- **Safe History Management:** Date and time are clearly displayed for all items. Clearing history or deleting files prompts with safe defaults to prevent accidental data loss.

### Polished Windows Look & Feel
- **Settings Dialog:** Rebuilt to fit cleanly without scrollbars on any screen scaling (100%, 125%, 150%). Features Windows 11 immersive dark title bar matching the app theme.
- **Consistent Icons & Arrows:** Outline gear icon in the header matches action buttons. All dropdown menus feature crisp downward indicator arrows in both Dark and Light themes.
- **Exit Confirmation:** Closing the app during an active download asks for confirmation so you never lose an in-progress download by mistake.

### Tool & Component Security
- **Publisher Verification:** Automatic setup now checks publisher cryptographic checksums for external tools (yt-dlp, ffmpeg, deno) before installation.
- **Offline Setup Support:** If an initial installation occurs without an active internet connection, setup completes cleanly and prompts when internet access is available.
