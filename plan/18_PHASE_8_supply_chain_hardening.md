# Phase 8 Plan: Supply Chain and Small Hardening

## Goals
Satisfy autonomous requirements **T1**, **T2**, **T3**, **T4**:
- **T1**: Tool downloads are verified or rejected (fail closed where a checksum source exists; 3 retries with backoff 1s, 2s, 4s). Never run `--version` on unverified binaries.
- **T2**: Installer (`installer/setup.iss`) no longer runs unverified tool downloads; keeps shortcuts and setup skeleton; the app downloads and verifies tools on first run.
- **T3**: `requirements.txt` (and `requirements-dev.txt` if present) pins exact versions.
- **T4**: `thumbnails.py` bounds thumbnail download size to at most 5 MB (`resp.read(5_000_001)`).

---

## Chunk 8.1: Tool Manager Checksum Verification (`app/core/tool_manager.py`)
- Inspect `install_tool()` in `app/core/tool_manager.py`.
- If a tool specifies `sha256_url` in `tools.json`:
  - Attempt to fetch the SHA-256 checksum with up to 3 retries (1s, 2s, 4s).
  - If checksum is unavailable or mismatch:
    - Delete temporary download.
    - Keep existing binary in `bin/` (if any).
    - Log error and emit `"Could not verify the download. Try again later."`
    - Do NOT run `--version` on unverified files.
  - If tool has no checksum source: keep existing behavior (log warning).
- Tests in `tests/test_tool_manager.py`:
  - Update `test_install_tool_checksum_missing_installs_with_warning` to assert fail-closed rejection when checksum URL fails after 3 retries.
  - Record in `docs/verification/test_changes.md`.

---

## Chunk 8.2: Installer Hardening (`installer/setup.iss`)
- In `installer/setup.iss`:
  - Remove unverified `DownloadPage` tool downloading and extraction code for yt-dlp, ffmpeg, and deno.
  - Retain application setup, file installation, Start Menu / Desktop shortcut creation, and uninstall config.
  - Check if `ISCC.exe` is installed on system. If found, compile setup to verify syntax. If not, record UNTESTED in log.

---

## Chunk 8.3: Thumbnail Size Cap (`app/core/thumbnails.py`)
- In `app/core/thumbnails.py`:
  - In `download_thumbnail(url)`:
    - Read at most 5 MB: `data = resp.read(5_000_001)`.
    - If `len(data) > 5_000_000`: discard and return `None`.
- Tests in `tests/test_thumbnails.py`:
  - Add `test_thumbnail_download_size_capped_at_5mb`.

---

## Chunk 8.4: Pinned Requirements (`requirements.txt`)
- Run `pip freeze` to get installed versions of PySide6, send2trash, pywin32, etc.
- Pin exact versions in `requirements.txt` (and `requirements-dev.txt`).
- Validate with `python -m pip install --dry-run -r requirements.txt`.

---

## Chunk 8.5: Verification of Phase 8
- Run test suite for tool manager, thumbnails, and requirements.
- Update `docs/verification/requirements_matrix.md` rows T1, T2, T3, T4.
- Update `docs/verification/autonomy_log.md` and commit.
