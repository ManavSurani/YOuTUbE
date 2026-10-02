# Phase 9 — Packaging and Installer

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Goal:** one `YouTube_Setup.exe` that installs without admin rights, downloads the tools with a normal progress bar, creates the Desktop and Start Menu shortcuts automatically, and never shows a terminal.
**Reads first:** `00_AGENT_BRIEF.md`, `02_DESIGN_SYSTEM.md`.

---

## Chunk 9.1 — Build the app folder

**Files you may touch (new):** `build/build_exe.bat`.

**Do**
- One command, windowed, one-folder, with the icon and bundled data:

```bat
pip install -r requirements.txt -r requirements-dev.txt
pyinstaller --noconsole --onedir --name YouTube --icon assets\icon.ico ^
  --paths . --add-data "app\tools.json;app" --add-data "assets;assets" app\main.py
```

- Use `--onedir`, not `--onefile` (faster start, fewer antivirus alarms).
- Do not bundle yt-dlp, ffmpeg or deno. They are downloaded.

**Verify**
- [ ] `dist\YouTube\YouTube.exe` starts on the build PC with **no console window**.
- [ ] Window, taskbar and title bar show the logo.
- [ ] On a PC **without Python installed** (or a clean VM), the folder runs.
- [ ] The app finds `tools.json` and `assets\icon.ico` inside the frozen build.

## Chunk 9.2 — Installer skeleton

**Files you may touch (new):** `installer/setup.iss`.

**Do**
- Wizard basics. Comments must be on their **own line** (Inno does not allow a comment after a value).

```ini
#define MyAppName "YouTube"
#define MyAppVersion "1.0.0"
#define MyAppExe "YouTube.exe"

[Setup]
AppId={{PUT-A-NEW-GUID-HERE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename=YouTube_Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
; no admin rights needed
PrivilegesRequired=lowest
; lets silent updates replace a running app
CloseApplications=yes
RestartApplications=yes

[Files]
Source: "..\dist\YouTube\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
```

- The Desktop shortcut has **no task checkbox**: it is always created automatically.
- Same `AppId` in every version (so updates upgrade in place). Generate the GUID once and never change it.
- Use the wizard images/icon from `assets/` only. No custom colourful wizard art.

**Verify**
- [ ] Compiles with `ISCC.exe` with no warnings.
- [ ] Installing creates `{localappdata}\Programs\YouTube`, a Start Menu entry and a Desktop shortcut with the red logo.
- [ ] Installing does not ask for administrator permission.
- [ ] Installing the same version twice does not create two entries in "Apps & features".

## Chunk 9.3 — Download tools during setup (hidden)

**Files you may touch:** `installer/setup.iss`.

**Do**
- Use Inno Setup 6.1+ **built-in download page** (`CreateDownloadPage`, `DownloadPage.Add`, `DownloadPage.Download`) on the "Preparing to install" step. Downloads: `yt-dlp.exe`, the ffmpeg zip, the deno zip, using the **same URLs as `app/tools.json`**.
- After files are copied (`ssPostInstall`): copy `yt-dlp.exe` to `{userappdata}\YouTube\bin\`; unzip the other two with Windows' built-in `tar.exe -xf` started with `Exec(..., SW_HIDE, ewWaitUntilTerminated, ...)`; move `ffmpeg.exe`, `ffprobe.exe`, `deno.exe` into `bin\`.
- **If any download or unzip fails, do not fail the install.** Continue; the app's first-run (Phase 5) finishes the job.
- Uninstall asks once: "Also remove history and settings?" Default answer: No. Tools in `bin\` are removed either way.

**Verify**
- [ ] Install with internet on: the wizard shows a normal progress bar, then `bin\` holds 4 working tools; first launch needs no download.
- [ ] Install with internet **off**: the install still finishes; first launch shows the Phase 5 message and recovers when online.
- [ ] No terminal or PowerShell window appears during setup (record the screen).
- [ ] Uninstall removes the app, shortcuts and tools; history stays unless the user said yes.

## Chunk 9.4 — Build script and signing

**Files you may touch (new):** `build/build_installer.bat`.

**Do**
- Script runs `build_exe.bat`, then `ISCC.exe installer\setup.iss`, then prints the SHA-256 of `Output\YouTube_Setup.exe`.
- Signing (recommended): sign `YouTube.exe` and `YouTube_Setup.exe` with `signtool` if a certificate exists; skip silently if not.

**Verify**
- [ ] One command produces `Output\YouTube_Setup.exe` and prints a SHA-256.
- [ ] Without a certificate the script still succeeds.
- [ ] With a certificate, file Properties → Digital Signatures lists the signature.

---

## Phase 9 verification (all must pass)

- [ ] All chunk Verify lists are checked.
- [ ] On a **clean Windows 10 and a clean Windows 11** machine: double-click `YouTube_Setup.exe` → Next → Install → app opens → desktop shortcut present → first download succeeds.
- [ ] The shortcut from the installer and the first-run shortcut logic do not create two shortcuts.
- [ ] No terminal visible at any step. No admin prompt.
- [ ] Only files from the chunk lists changed. User said "go on".
