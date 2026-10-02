# YouTube Downloader: Build Plan

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

A complete, phase-by-phase plan for building the **YouTube** Windows app (and optional Android app) with an AI coding agent.

## Files

| File | Purpose |
|---|---|
| `00_AGENT_BRIEF.md` | **Agent reads this first.** What we build, how it works, the no-terminal rule, working method, comprehension check |
| `01_MASTER_PLAN.md` | Goals, tech stack, project layout, phase list, risks |
| `02_DESIGN_SYSTEM.md` | Colours, type, components, motion, "never do this" list, logo rules |
| `PHASE_01` … `PHASE_11` | One file per phase. Each is split into chunks; every chunk has a Verify list; every phase ends with a Phase verification |
| `assets/` | `logo.svg`, `logo_512.png`, `icon.ico` |

## Order of work

```
Phase 1  Foundation and Brand          Phase 7   App Updater
Phase 2  Download Engine               Phase 8   Polish, Errors, Settings
Phase 3  Video and Audio Tabs          Phase 9   Packaging and Installer
Phase 4  History                       Phase 10  Testing and Release
Phase 5  Tools, Splash, First Run      Phase 11  Android (optional)
Phase 6  Network Monitor
```

## How to start the agent

Put all these files in the project folder, then send the agent this message:

> Read `00_AGENT_BRIEF.md`, `01_MASTER_PLAN.md` and `02_DESIGN_SYSTEM.md` in full. Then write the 8-answer summary from Step 0 of the brief and wait for my "yes". After that, start `PHASE_01_Foundation_and_Brand.md`, one chunk at a time. After each chunk, run its Verify list and report. Do not start the next chunk or phase until I say go on.

## The rules (repeated at the top of every file)

Understand first · no unnecessary code · touch only the files a chunk lists · minimalist YouTube-matching design · the user never sees a terminal · verify after every chunk and every phase.
