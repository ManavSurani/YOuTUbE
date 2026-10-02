# 02 — Design System

> ## Rules for this file (non-negotiable)
> 1. **Understand first.** Read `00_AGENT_BRIEF.md` and pass its comprehension check before writing any code. If anything is unclear, stop and ask.
> 2. **No unnecessary code.** Write only what the current chunk needs. No extra features, no unused helpers, no dead code, no "just in case" code, no TODO leftovers.
> 3. **Touch only the files the chunk lists.** Do not edit, rename, reformat or delete any other file. If another file seems to need a change, stop and ask first.
> 4. **Minimalist design.** Follow `02_DESIGN_SYSTEM.md` exactly: YouTube-style red / near-black / white, flat, no gradients, glows, shadows or emoji, nothing decorative.
> 5. **The user never sees a terminal.** Every external program starts through `app/core/proc.py` (hidden). No `print()`.
> 6. **Verify after every chunk.** Run the chunk's Verify list; do not start the next chunk until every box is checked. Each phase ends with a Phase verification that must pass before the next phase.

**Feel:** quiet, flat, fast. It should look like a small native utility made by someone who cares, not like a template. If a design choice is not on this page, do not add it.

## 1. Colours (match YouTube's palette)

| Token | Dark (default) | Light | Used for |
|---|---|---|---|
| `bg` | `#0F0F0F` | `#FFFFFF` | Window background |
| `surface` | `#212121` | `#F2F2F2` | Inputs, list rows, dropdowns |
| `surface_hover` | `#272727` | `#E5E5E5` | Hover on surface |
| `border` | `#303030` | `#E0E0E0` | 1 px lines |
| `text` | `#F1F1F1` | `#0F0F0F` | Main text |
| `text_muted` | `#AAAAAA` | `#606060` | Secondary text, labels |
| `accent` | `#FF0000` | `#FF0000` | Primary button, progress fill, active-tab underline |
| `accent_hover` | `#CC0000` | `#CC0000` | Hover on accent |
| `info` | `#3EA6FF` | `#065FD4` | Links, "update available" text |
| `success` | `#2BA640` | `#2BA640` | "Online" dot, done |
| `error` | `#FF4E45` | `#CC0000` | "Offline" dot, error text |

**Red is rare.** Red may appear only on: the Download button, the progress fill, the active tab underline, and the logo. Everything else is neutral grey/white.

## 2. Type, spacing, shape

- Font: **Segoe UI** (already on Windows, nothing to bundle). Sizes: 12 (small), 13 (body), 15 (section title), 18 (video title). Weights: regular and semibold only.
- Spacing on a 4-px grid: 4, 8, 12, 16, 24. Window padding 16.
- Corner radius: **8** for buttons, inputs, thumbnails. Nothing else is rounded.
- Borders: 1 px `border`. **No shadows.**
- Window: 760 × 560 default, 640 × 480 minimum.

## 3. Components

| Component | Look |
|---|---|
| Tabs | Text only. Active tab: `text` colour + 2 px `accent` underline. Inactive: `text_muted`. |
| Link box | `surface` fill, 1 px `border`, radius 8, height 36. Focus: border becomes `text_muted`. |
| Primary button (Download) | `accent` fill, white semibold text, radius 8, height 36. |
| Secondary button (Cancel, Fetch) | `surface` fill, `text`, radius 8. |
| Dropdown | Same as the link box. |
| Progress bar | 6 px tall, `surface` track, `accent` fill, radius 3, no text inside the bar. Percent is plain text next to it. |
| History row | `surface` fill, 72 px tall, 64×36 thumbnail, title (semibold) + one muted line (`type • quality • size • date`). Actions appear on hover as text buttons. |
| Status dot | 8 px circle + word: `Online` (success) / `Offline` (error). Top right. |
| Update banner | One thin row at the top, `surface` fill, `info` text, two text buttons. |
| Popup | Standard Qt message box, short sentence, one button. |

## 4. Motion

Only two animations are allowed: the progress fill moves smoothly, and the splash fades in/out (150 ms). Nothing bounces, glows, pulses or slides.

## 5. Copy

Short, plain, no exclamation marks, no emoji. Examples: "Paste a YouTube link", "Downloading video…", "Done. Saved to Downloads.", "No internet connection."

## 6. Never do this (AI-slop list)

- No gradients, glass/blur effects, glows, drop shadows, neon or purple/blue accents.
- No emoji or decorative icons. If an icon is truly needed, use a simple one-colour line icon in `text_muted`.
- No cards inside cards, no big hero banners, no marketing text, no "welcome" screens.
- No extra colours beyond the table above.
- No tooltips on everything, no animated loaders other than the progress bar.

## 7. Logo

Files are supplied in `assets/`: `logo.svg` (source), `logo_512.png`, `icon.ico` (16 to 256 px).

- Concept: a **red rounded tile** with a **white download arrow** over a tray line. The arrow head is a downward triangle, a quiet nod to a play button without copying YouTube's mark.
- Red `#FF0000`, white `#FFFFFF`. Nothing else. No text inside the logo.
- Used for: window icon, taskbar, desktop shortcut, Start Menu, installer wizard, uninstaller, splash (centred, 96 px).
- Do not redraw, recolour, add effects or stretch it. Use the supplied files.
