# 00 — Agent Brief (READ THIS FIRST)

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

## Step 0 — Understand before you build

Do not write any code until you have done all of this:

1. Read, in order: `00_AGENT_BRIEF.md` (this file), `01_MASTER_PLAN.md`, `02_DESIGN_SYSTEM.md`, then the phase file you are about to work on.
2. Write a short summary **in your own words** (10 to 15 lines) that answers the 8 questions below.
3. Show it to the user and **wait for a "yes"**. If the user corrects you, fix the summary first.

| # | Question you must answer |
|---|---|
| 1 | What is this app, and who uses it? |
| 2 | What does the user see from the first click on the desktop icon to a finished download? |
| 3 | What does the user **never** see? |
| 4 | Which tools run behind the scenes, and where do they live on the PC? |
| 5 | What happens when the internet goes off? |
| 6 | How do the app and its tools stay up to date? |
| 7 | What does the design look like, and what must it never look like? |
| 8 | What is the order of phases, and what must pass before moving on? |

---

## What we are building

**YouTube** (display name, see note in `01_MASTER_PLAN.md`) is a small Windows desktop app. A person pastes a YouTube link and gets the video (best quality, audio included) or just the audio. That is all it does. It must feel like a normal, calm, finished program, not a developer tool.

## How the software works (plain words)

```
User pastes link
   → app cleans the link (keeps one video only)
   → app asks yt-dlp "what does this video offer?"   (hidden background process)
   → app shows title, thumbnail, and a quality list built from the real answer
   → user presses Download
   → app runs yt-dlp + ffmpeg in the background       (hidden background process)
   → app reads their progress lines and shows % / speed / ETA / stage
   → file is saved to Downloads and added to History (SQLite)
```

Three layers, never mixed:

| Layer | Folder | Rule |
|---|---|---|
| UI (what the user sees) | `app/ui/` | Draws things and reacts to clicks. No download logic, no database code. |
| Core (the work) | `app/core/` | Downloads, history, tools, updates, network. No widgets, no colours. |
| Worker threads | inside core, exposed as Qt signals | Core work runs off the UI thread. UI only receives signals. The UI never freezes. |

Tools (`yt-dlp`, `ffmpeg`, `ffprobe`, `deno`) are **separate files** kept in `%APPDATA%\YouTube\bin\`, so they can be updated without rebuilding the app. User data (history, settings, logs) lives beside them, so app updates never wipe it.

## First run, in the user's eyes

1. User runs `YouTube_Setup.exe`, clicks Next → Install. A desktop shortcut and Start Menu entry appear automatically.
2. Setup downloads the needed tools with a normal progress bar.
3. App opens with a short splash, then the main window.
4. If anything was missed (for example no internet during setup), the app finishes the job itself on first launch, and (re)creates the desktop shortcut **once** if it is missing.

## The "no terminal" rule (the user must never see a black window)

This is the most important rule of the project. Every one of these must be true:

- The app is built windowed (`--noconsole`). No `print()` anywhere; use the logger.
- **Every** external program (yt-dlp, ffmpeg, deno, PowerShell, the installer helper) is started through the single helper `app/core/proc.py`. It always sets `CREATE_NO_WINDOW`, `stdin=DEVNULL`, and a hidden `STARTUPINFO`. Nothing else in the project may import `subprocess`.
- PowerShell is always called with `-NoProfile -NonInteractive -WindowStyle Hidden`.
- The Inno Setup script runs any helper command with `SW_HIDE`.
- Errors are shown as plain sentences in the UI. Raw output goes to `logs\app.log`, never to a console.

Quick check anyone can run: `grep -rn "subprocess\|os.system\|print(" app/` must show hits **only** inside `app/core/proc.py` (and none for `print`).
*(A developer may use a terminal while developing. The rule is about the finished app on the user's PC.)*

## Working method (applies to every phase)

- Work **one chunk at a time**. Each chunk lists the exact files you may touch.
- After a chunk, run its **Verify** list. Do not start the next chunk until every box is checked.
- After the last chunk, run the **Phase verification**. Do not start the next phase until it passes and the user confirms.
- After each chunk, report to the user in this format:

```
Chunk X.Y done
Files changed: <list>
Verify: <each item → pass/fail>
Notes: <anything the user must know>
```

- If something in the plan is unclear or seems wrong, **stop and ask**. Do not guess and do not silently change the plan.
- If a chunk needs a file that is not on its list, stop and ask first.
