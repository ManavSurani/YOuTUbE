# Plan 23: UI/UX Overhaul (Same Colors, Same Logo) + Repo Hygiene

Source of findings: `docs/ui_ux_audit.md` (verified with settled screenshots).

## Goal

Make the app look and feel like a polished native utility in **both dark and light mode**, fix every verified UI/UX bug, add the customer-pleasing features from the audit, and keep the GitHub repo clean (nothing unnecessary or secret is pushed).

**Never changes:** the palette values in `app/ui/theme.py` (`DARK_TOKENS`, `LIGHT_TOKENS`) and the logo files in `assets/`.

---

## Findings this plan is built on (checked in code)

| # | Fact | Consequence for the plan |
|---|---|---|
| **F1** | **`android/app/release.keystore` is tracked and pushed to the public repo since 2026-10-02**, and `android/app/build.gradle.kts` contains `storePassword = "youtube123"` / `keyPassword = "youtube123"`. | Anyone can sign APKs as this app. Phase 0 stops tracking it and moves the secrets out. Key rotation is an **owner decision** (Task 0.4). |
| **F2** | `.gitignore` misses `android/.kotlin/`, keystores (`*.keystore`, `*.jks`), IDE folders, `.env`, coverage output, Claude local settings, and generated UI snapshots. | Phase 0 adds them. |
| **F3** | 45 hard-coded `#FFFFFF` and about 30 distinct hex colors live in widgets. The kit buttons paint **dark-only** `QColor`s (`kit/buttons.py` lines 145–176, 290–303). | Light mode can only work after a token layer exists (Phase 1), then all screens switch to it (Phase 2). |
| **F4** | Existing tests lock some colors: `test_recent_list.py:149` expects `#AAAAAA` in a meta label (dark `text_muted`), `test_network_monitor.py:189/200` expects the status dot `#CC0000` offline / `#2BA640` online, and `test_ui_kit.py:542` expects a `#3EA6FF` focus ring in **both** themes. | The token helper must return **the same hex strings in dark mode**. The focus ring stays `#3EA6FF` in both themes (as a fixed `focus` token). No existing test is edited. |
| **F5** | History `created_at` = SQLite `CURRENT_TIMESTAMP` (UTC), shown raw → 5 h 30 m off in India. | Convert at display time (Phase 3). The DB schema is untouched. |
| **F6** | `DownloadManager` has no public pause/resume. The offline path already pauses and resumes (`set_online`, `_paused_worker`, `_resume_active_job`). | Pause/Resume reuses that path through two small public methods (Phase 4, scoped exception). |
| **F7** | The `-J` info has an exact `filesize` for about half of the formats and `filesize_approx` for the rest (`tests/sample_info.json`: 6 + 6 of 12 video-only). | Quality sizes are shown as `690 MB` when exact and `≈ 690 MB` when approximate (Phase 4). |
| **F8** | `02_DESIGN_SYSTEM.md §4` allows only 2 animations, but the app already has more, and the owner asked for better motion. | The motion rules in the design doc are updated in Phase 6 (the doc only, not the colors). |
| **F9** | Tests: about 555, all green except the known `test_check_scope.py::test_scope_checker_final` and timing flakes in `test_tab_looks.py` / `test_ui_kit.py` paste test. | Baseline in Phase 0. |

---

## Rules for Claude (binding for this plan)

| # | Rule |
|---|---|
| **R1** | **Colors and logo are frozen.** No new color values anywhere. Every color in widgets comes from the theme tokens. The only new token *names* allowed are aliases of colors already used: `focus` = `#3EA6FF` (both themes, F4) and `status_offline` = `#CC0000` (both themes, F4). |
| **R2** | **Only the files listed for the current phase may change.** Every other file shows 0 lines changed. Protected engine files (`downloader.py`, `proc.py`, `jobs.py`, `history_db.py`, `history_service.py`, `app_updater.py`, `tool_manager.py`, `url_tools.py`, `errors.py`, `thumbnails.py`, `network_monitor.py`) are **never** edited in this plan. Exceptions are listed per phase, with their exact scope. |
| **R3** | **Build on what exists.** Reuse the kit widgets (`AnimatedButton`, `IconButton`, `Toast`, `InlineMessage`, `ProgressCard`, `ThumbLabel`, `AnimatedCheckBox`), `kit/anim.py`, `theme.build_qss`, `apply_dark_title_bar`, `shortcut.py`, and the manager's offline pause path. Do not create a second version of something that exists. |
| **R4** | **Smallest change per task.** No refactors, renames, or "while I'm here" edits outside the task. No dead code, no unused helpers, no TODOs. |
| **R5** | **Failing test first** for every behaviour change: write the test, see it fail for the right reason, then change the code. Pure visual polish (spacing, sizes) is checked by the snapshot gate instead (R7). |
| **R6** | **Tests are add-only.** Never delete, weaken, or rewrite an existing test or assertion. If one blocks a task, **stop and ask the owner**. |
| **R7** | **Snapshot gate (done by Claude, not the owner):** at the end of every phase, run `python tools/ui_snapshots.py <phase>`. It renders all screens in **dark and light** into `docs/ui_audit/snapshots/<phase>/` (git-ignored). Claude must open and check every image itself: no invisible text, no dark blocks in light mode, no overflow, edges aligned. Findings are written down in the phase note. |
| **R8** | **Copy rules (design doc §5):** short, plain, no exclamation marks, no emoji in the app. |
| **R9** | **Motion rules (after Phase 6):** only the motion tokens `fast` 120 ms / `base` 180 ms / `slow` 260 ms / `celebrate` 300 ms; every animation goes through `kit/anim.py`, so "Reduce motion" turns it off. |
| **R10** | **Nothing unnecessary goes to GitHub.** No screenshots, snapshots, logs, builds, keystores, secrets, IDE files, or scratch files are ever committed. Before every commit: `git status --porcelain` must list only files from the phase's Allowed list. |
| **R11** | **Outward actions need the owner's "yes" at that moment:** push, merge to `main`, GitHub release, history rewrite, keystore rotation. Approval of this plan is not approval for these. |
| **R12** | **Commits:** one commit per phase, after its gate passes, on branch `fix/ui-pass`. The message names the phase. Claude commits; pushing waits for R11. |
| **R13** | **Loop rule:** after approval, run Phase 0 → 7 in order. Each phase = tasks → its tests → full suite → snapshot gate (R7) → scope check → phase note → commit. Gate passes → go straight to the next phase. Stop only if (a) a gate fails and the fix would break R1–R12, (b) an existing test must change (R6), or (c) an owner decision or R11 action is next. **The owner does not review screenshots or per-phase results:** Claude takes and checks every snapshot itself (R7) and sends **only one final result** at the end (Phase 7), plus the decision questions above when they come up. |
| **R14** | **Known red tests:** `test_check_scope.py::test_scope_checker_final` (old) and the timing flakes (re-run in isolation 3×; a flake that passes 3/3 alone counts as green). Close the YOuTUbE app before test runs (single-instance test). |

**Phase notes:** one short file per phase, `docs/verification/plan23_phase<N>.md`, with test counts, the snapshot review, and the scope list. These are the only docs added besides this plan.

---

## Phase 0: Baseline, `.gitignore`, Secrets Out, Snapshot Tool

**Allowed files:** `.gitignore`, `android/app/build.gradle.kts` (signing block only), `tools/ui_snapshots.py` (new), `tests/test_repo_hygiene.py` (new), `docs/verification/plan23_phase0.md`, this plan, `docs/ui_ux_audit.md`. Plus `git rm --cached android/app/release.keystore` (the file stays on disk).

### Task 0.1: Baseline
`git status --porcelain` · `pytest -q` → record the counts in the phase note.

### Task 0.2: `.gitignore` additions (append, keep the existing lines)
```gitignore
# Android local / secrets
android/.kotlin/
*.keystore
*.jks
android/keystore.properties

# IDE / tools
.idea/
.vscode/
*.iml
.claude/settings.local.json

# Env and secrets
.env
.env.*

# Test / coverage output
.coverage
htmlcov/
coverage.xml

# Download leftovers
*.part
*.ytdl

# Generated UI snapshots and audit images (local review only)
docs/ui_audit/
```
`docs/ui_ux_audit.md` stays tracked (text only). The audit images stay local.

### Task 0.3: Stop tracking the keystore and its passwords (F1)
1. `git rm --cached android/app/release.keystore` (the file stays on disk for local signing).
2. `build.gradle.kts`: read `storeFile`, `storePassword`, `keyAlias`, and `keyPassword` from `android/keystore.properties` (git-ignored). If that file is missing, the release build falls back to unsigned (debug still works). No password text remains in tracked files.
3. Create `android/keystore.properties` locally with the current values, so the owner's builds keep working (not committed).

### Task 0.4: Owner decision (stop and ask, R11)
The old key and password are already public, and removing them from future commits does not undo that. Options:
- **A (recommended): rotate the key with APK Signature Scheme v3 lineage** (`apksigner rotate`). Existing Android installs keep updating, and new builds use a new private key.
- **B:** a new key without lineage. Existing Android users must uninstall and reinstall.
- **C:** keep the old key (not safe).
- Optional: rewrite git history to purge the file. This needs a force-push, and it doesn't un-leak the key, so it's only worth doing together with A or B.

The plan continues with Phase 1 while the owner decides. The rotation itself is done only after a yes.

### Task 0.5: Snapshot tool `tools/ui_snapshots.py`
A cleaned-up version of the audit script. It uses a **sandbox `APPDATA`** (copies only `history/` and `settings.json`, and never touches real data), renders 10 screens × 2 themes after animations settle (450 ms wait), and writes PNGs to `docs/ui_audit/snapshots/<label>/`. Screens: splash, video idle/ready/error/downloading/done, audio, history, banner+offline, settings.

### Task 0.6: Tests (`tests/test_repo_hygiene.py`)
| Test | Checks |
|---|---|
| `test_no_keystore_tracked` | `git ls-files` has no `*.keystore` / `*.jks` |
| `test_no_signing_password_in_tracked_files` | no tracked file contains `storePassword = "` with a literal value |
| `test_gitignore_covers_generated_paths` | `git check-ignore` matches `android/.kotlin/x`, `docs/ui_audit/x.png`, `.vscode/x`, `x.part`, `android/keystore.properties` |

**Phase 0 gate:** new tests green, full suite = baseline + new, `git status` shows only allowed files, the snapshot tool produces 20 PNGs, **owner asked about Task 0.4**.

---

## Phase 1: Theme Foundation (kit widgets)

**Allowed files:** `app/ui/theme.py`, `app/ui/kit/buttons.py`, `app/ui/kit/checkbox.py`, `app/ui/kit/inline_message.py`, `app/ui/kit/toast.py`, `app/ui/kit/progress_card.py`, `app/ui/kit/thumb_label.py`, `app/ui/kit/__init__.py`, `tests/test_theme_tokens.py` (new), phase note.

### Task 1.1: Token API in `theme.py` (no value changes, R1)
- Add `"focus": "#3EA6FF"` and `"status_offline": "#CC0000"` to **both** token dicts (aliases of colors already used, F4).
- `current_theme()`, `tok(name) -> str` (current theme's hex), `qcolor(name) -> QColor`.
- `ThemeManager` (a QObject singleton) with `changed = Signal(str)` and `apply(name)`. It sets the app stylesheet with `build_qss(name)`, stores the current theme, emits `changed`, and re-polishes top-level windows.
- `build_qss` gains the type scale (12/13/15/18) and role selectors: `QLabel[role="title"]` 18 semibold, `[role="section"]` 15 semibold, `[role="meta"]` 12 `text_muted`, `[role="link"]` `info`.

### Task 1.2: Kit widgets use tokens
- `buttons.py`: map every painted color to tokens. Secondary = `surface` / `surface_hover` / `surface_pressed` + `border`, text `text`. Primary = `accent` / `accent_hover` / `accent_pressed` + white text. Ghost = transparent / `surface_hover`, text `text_muted`→`text`. Danger = `error`. Focus ring = `focus`. Disabled = `surface` + `text_muted`. Repaint on `ThemeManager.changed`.
- `checkbox.py`, `inline_message.py`, `toast.py`, `progress_card.py`, `thumb_label.py`: same idea. `ProgressCard` title → `role="title"` style at 13 semibold; stats → `meta`; track `surface_hover` in light, `surface` in dark (via token).
- In dark mode, every string a test checks stays identical (F4).

### Task 1.3: Tests (`tests/test_theme_tokens.py`)
| Test | Checks |
|---|---|
| `test_token_values_unchanged` | every key that existed in DARK/LIGHT before this plan keeps its exact value |
| `test_tok_follows_theme` | `apply("light")` → `tok("text") == "#0F0F0F"`; `apply("dark")` → `"#F1F1F1"` |
| `test_kit_has_no_hex_literals` | AST scan of `app/ui/kit/*.py`: no `#RRGGBB` string literals |
| `test_buttons_paint_light_surface` | render a secondary `AnimatedButton` in light → the center pixel is `#F2F2F2` and the text pixels are dark |
| `test_theme_change_repaints_buttons` | switch dark→light → the button repaints (pixel changes) without re-creating it |

**Phase 1 gate:** green + snapshots: kit widgets correct in both themes.

---

## Phase 2: All Screens on Tokens + Type Scale (fixes light mode)

**Allowed files:** `app/ui/header.py`, `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/ui/queue_widget.py`, `app/ui/recent_list.py`, `app/ui/history_tab.py`, `app/ui/settings_dialog.py`, `app/ui/main_window.py` (styles + `apply_dark_title_bar` on theme change only), `app/ui/splash.py` (background token only), `app/main.py` (use `ThemeManager.apply` instead of `setStyleSheet`), `tests/test_light_mode.py` (new), phase note.

### Task 2.1: Replace every hard-coded color with tokens / roles
File by file, in order: header → video/audio → queue → recent → history → settings → main window banner → splash. Widgets whose style is set in code re-apply it on `ThemeManager.changed`. The splash uses `bg` (no flash on the hand-off).

### Task 2.2: Type scale
Snap all font sizes to 12 / 13 / 15 / 18 (remove 11, 14, 16) through roles.

### Task 2.3: Live theme switch
Settings → Appearance applies instantly through `ThemeManager.apply` and calls `apply_dark_title_bar(is_dark)` on all top-level windows.

### Task 2.4: Tests (`tests/test_light_mode.py`)
| Test | Checks |
|---|---|
| `test_ui_has_no_hex_literals` | AST scan of `app/ui/*.py` (except `theme.py`): no `#RRGGBB` literals |
| `test_light_labels_readable[screen]` | for each screen (video ready, downloading, history, settings) in light: every visible `QLabel` foreground has contrast ≥ 3.0 against `#FFFFFF` (≥ 4.5 for `title`/body roles) |
| `test_light_no_dark_blocks` | rendering the video tab in light: no button/input center pixel darker than `#BBBBBB` except the primary (red) button |
| `test_theme_switch_live` | dark→light→dark with the window open: labels follow (no restart) |
| `test_font_sizes_on_scale` | no `font-size` outside {12,13,15,18} in `app/ui` |

**Phase 2 gate:** green + **light snapshots fully readable** (all 10 screens), dark snapshots unchanged or better.

---

## Phase 3: Fix What's Broken (P0 bugs)

**Allowed files:** `app/ui/history_tab.py`, `app/ui/recent_list.py`, `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/ui/queue_widget.py`, `app/ui/main_window.py` (banner + offline handling), `app/ui/header.py`, matching test files (new tests only: `tests/test_p0_fixes.py`), phase note.

| Task | Fix | Test (failing first) |
|---|---|---|
| 3.1 | **Local time + relative dates** (F5): `format_date_str` treats stored values as UTC → `astimezone()` → "Today, 9:51 AM" / "Yesterday, 6:10 PM" / "17 Oct" / "17 Oct 2025" | UTC `2026-11-02 04:21:00` on an IST clock → "Today, 9:51 AM"; yesterday → "Yesterday, …" |
| 3.2 | **Elide long titles** (one line + tooltip) in history, recent, queue, progress card, and info card; history scroll area `AlwaysOff` horizontal | 300-char title → the row width ≤ the viewport; `horizontalScrollBar().maximum() == 0` |
| 3.3 | **Offline: no modal.** Remove the `QMessageBox` in `_on_went_offline`; show the header "Offline" pill + an inline muted line under the input: "You're offline. Downloads will resume automatically." | going offline creates no `QMessageBox`; the inline line becomes visible; back online hides it |
| 3.4 | **Header status:** hide the dot and word when online; show the "Offline" pill when offline (the dot stays `status_offline`, F4) | online → hidden; offline → visible with `#CC0000` dot |
| 3.5 | **Clear the stale card** when a new fetch starts or the link is invalid | after an invalid-link error, `info_card` is hidden |
| 3.6 | **Errors at the input:** red border + message under the input, kept until the text changes (no 4 s fade for validation errors) | the error stays after 5 s; typing clears it |
| 3.7 | **Queue groups:** "Up next (N)" counts waiting only; a separate "Failed (M)" header with "Retry all · Clear" | 2 waiting + 1 failed → labels "Up next (2)" and "Failed (1)" |
| 3.8 | **No progress bar on waiting rows**; the failed reason moves to the meta line | waiting row has no visible `QProgressBar`; failed meta contains "Failed · …" |
| 3.9 | **Update banner compact:** 40 px row, `info` text, text buttons "Update" / "Later", 2 px progress along the bottom | banner height ≤ 44; buttons are text-style (no filled background) |
| 3.10 | **One left edge** (16 px page padding everywhere) and **no layout shift** when the scrollbar appears (reserve its width) | the x of input, card, progress card, and list rows is equal; the Fetch x is the same with and without a scrollbar |
| 3.11 | **Junk rows:** recent/history rows under 1 KB show a "File missing / incomplete" pill and a Remove action | a 7-byte item shows the pill |
| 3.12 | **Copy fixes** (audit §7): audio placeholder, "Original (Opus)", "Saved to Downloads · 688.2 MB" | label texts match |

**Phase 3 gate:** green + snapshots (history has no h-scroll and local times; no modal; queue groups).

---

## Phase 4: Core Flow Upgrades

**Allowed files:** `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/ui/kit/progress_card.py`, `app/ui/main_window.py` (shortcuts, drop target), `app/ui/kit/buttons.py` (only if a new button style is needed), **`app/core/download_manager.py` (exception: add `pause_active()` / `resume_active()` that call the existing offline pause/resume path; nothing else)**, **`app/core/info_fetcher.py` (exception: add `quality_sizes` to `VideoInfo` computed from the existing `formats` list; nothing else)**, `tests/test_core_flow.py` (new), phase note.

| Task | Change | Test |
|---|---|---|
| 4.1 | **Size per quality** (F7): for each height, best video-only format at or below that height (highest `tbr`) + best audio (highest `abr`); exact `filesize` if both are present, else `filesize_approx` with "≈". The dropdown shows `1080p · 690 MB` / `720p · ≈ 410 MB`. | `sample_info.json` → expected labels; missing sizes → label without size (no crash) |
| 4.2 | **Info card layout:** `surface` card, 160×90 thumbnail (skeleton until loaded), 2-line elided title, meta line, "Saves to Downloads · Change" (opens the folder picker = existing Settings path), action row inside the card right-aligned: `[quality ▾] [Add to queue] [Download]` | widget order and visibility per state |
| 4.3 | **"Add to queue" always visible** in Ready (idle and downloading); when idle it queues without starting | idle + Add to queue → the job is in `waiting_jobs`, nothing starts |
| 4.4 | **Pause / Resume** (F6) as small icon buttons on the progress card; Cancel asks for confirmation when ≥ 10% is done | pause → the manager has a paused worker and the stage says "Paused"; resume continues from the floor percent |
| 4.5 | **Done state:** 4 s (extended while hovered), "Saved · 688.2 MB", buttons **[Open] [Show in folder]** (reuse `file_actions.py`), then collapse | done shows both buttons; clicking Open calls the file action with the path |
| 4.6 | **Clipboard detect:** on window focus, if the clipboard has a new YouTube URL → chip "Use copied link · Fetch" under the input (validated by the existing `url_tools`) | URL in clipboard + focus → chip visible; same URL twice → chip not shown again |
| 4.7 | **Auto-fetch on paste** (300 ms debounce) when the pasted text is a valid link | paste → `fetch_url` called once |
| 4.8 | **Drag & drop** links / `.url` files onto the window; dashed `border` outline while dragging | simulated drop → `url_input` text set + fetch |
| 4.9 | **Shortcuts:** Ctrl+V (paste+fetch), Enter (fetch / download when ready), Ctrl+1/2/3 tabs, Ctrl+F history search, Ctrl+, settings, Space pause/resume, Esc clear | each `QShortcut` triggers its action |
| 4.10 | **Thumbnail in the progress card** from `job.thumbnail_bytes` | bound job with bytes → the thumb pixmap is not null |

**Phase 4 gate:** green + snapshots (new card, sizes in the dropdown, done buttons).

---

## Phase 5: History and Settings

**Allowed files:** `app/ui/history_tab.py`, `app/ui/settings_dialog.py`, `app/ui/kit/toast.py`, `app/core/settings.py` (new default keys only), `app/core/shortcut.py` (exception: add start-with-Windows on/off using the existing shortcut helper, into the user Startup folder), `app/ui/main_window.py` (close-to-tray + tray menu), `tests/test_history_settings.py` (new), phase note.

| Task | Change | Test |
|---|---|---|
| 5.1 | **Date groups:** Today · Yesterday · This week · Earlier | items across 4 days → 4 headers in order |
| 5.2 | **Rows:** 64 px, hover `surface`, actions on hover **Play · Folder · ⋯** (the menu has Copy link, Re-download, Delete); double-click = play; right-click = the same menu | hover shows 3 buttons; the menu has 3 actions |
| 5.3 | **Undo delete:** delete removes the row with an animation + toast "Removed · Undo" for 5 s; the DB delete happens when the toast expires (the existing delete function, unchanged) | Undo inside 5 s → the item stays in the DB |
| 5.4 | **Search:** clear button, "N results", matches title **and** channel | query "recap" counts the right rows |
| 5.5 | **Selected chip neutral** (`text` fill, `bg` text); red no longer used for chips | the selected chip background is not `accent` |
| 5.6 | **"Clear all" into a ⋯ menu** (the confirmation dialog stays) | the button is not in the filter row |
| 5.7 | **Settings sections:** Downloads (default video quality, default audio format, open folder when done), Appearance (**System**/Dark/Light, Reduce motion), Behaviour (start with Windows, close to tray while downloading, notify when done, auto-fetch pasted links), Updates (inline "You're up to date (1.0.x)"), Help (Export log, Open log folder, licenses collapsed). Changes apply instantly with a small "Saved" tick. | each setting persists to `settings.json`; System follows the `AppsUseLightTheme` registry value |
| 5.8 | **Tray:** menu Show · Pause all · Resume all · Quit; tooltip "Downloading 1 of 3 · 46%"; clicking the finished notification opens the folder | menu has 4 actions; tooltip updates on progress |

**Phase 5 gate:** green + snapshots (history groups, settings sections in both themes).

---

## Phase 6: Motion and Delight

**Allowed files:** `app/ui/kit/anim.py`, `app/ui/kit/*.py` (animation hooks only), `app/ui/video_tab.py`, `app/ui/audio_tab.py`, `app/ui/queue_widget.py`, `app/ui/recent_list.py`, `app/ui/history_tab.py`, `app/ui/header.py`, `app/ui/splash.py`, `02_DESIGN_SYSTEM.md` (§4 Motion and §6 wording only, F8), `tests/test_motion.py` (new), phase note.

| Task | Change | Test |
|---|---|---|
| 6.1 | **Motion tokens** in `anim.py` (`FAST=120`, `BASE=180`, `SLOW=260`, `CELEBRATE=300`); all existing animations moved onto them; Reduce motion → instant | all `create_animation` durations ∈ the tokens; with reduce motion, the end state is applied with no animation object |
| 6.2 | **Skeleton** for the info card while fetching; content fade-in 180 ms; thumbnail fade-in | fetch start → skeleton visible; info → skeleton hidden |
| 6.3 | **Card → progress morph:** the info card collapses (260 ms) while the progress card expands | both animations created with SLOW |
| 6.4 | **Smooth progress:** bar value and percent animate between ticks (≤ 180 ms); the shimmer runs only while bytes move | stall → shimmer stops |
| 6.5 | **Done pulse:** a check mark scales 1.0→1.15→1.0 (300 ms, OutBack) + the new row slides into Recently downloaded with a 1 s `surface_hover` highlight | done triggers a CELEBRATE animation |
| 6.6 | **List motion:** queue add slides in, remove fades+collapses (180 ms) | add/remove create BASE animations |
| 6.7 | **Error shake** of the input (3 × 4 px, 200 ms); none with reduce motion | invalid link → a shake animation exists; reduce motion → none |
| 6.8 | **Tab content cross-fade** 120 ms + the existing underline slide | tab change creates a FAST opacity animation |
| 6.9 | **Splash progress** animates between steps (200 ms) | value animation between 10→80 |
| 6.10 | Update `02_DESIGN_SYSTEM.md` §4 with the motion tokens and the list above; §6 keeps "no bounce/glow" except the single done pulse | (doc) |

**Phase 6 gate:** green + snapshots + a short screen recording is **not** required; Claude checks the animation durations via tests and spot-checks screens mid-animation.

---

## Phase 7: Final Verification and Release

**Allowed files:** `docs/verification/plan23_final.md`, `README.md` (screenshots section text only, no images committed).

1. Full suite: baseline + all new tests green (R14 rules for flakes).
2. Snapshots for all screens in both themes; a final visual review written in the note (before/after list against `docs/ui_ux_audit.md` §2 Top 12, each marked fixed / changed / deferred with a reason).
3. Scope: `git diff --stat main...fix/ui-pass` lists only files allowed across phases; `git ls-files` has no images under `docs/ui_audit/`, no keystore, no secrets (the hygiene tests prove it).
4. DPI check: run the snapshot tool with `QT_SCALE_FACTOR=1.25` and `1.5`; no clipped text.
5. **Owner yes (R11):** merge `fix/ui-pass` → `main`, push, then `python tools/release.py --notes "New look: light mode, faster flow, history and settings upgrades"`. The installed app updates itself on the next start (Plan 22).
6. Real-PC check by the owner: paste, auto-fetch, sizes, download, pause/resume, done buttons, history times, theme switch live, tray menu.

**Phase 7 gate:** one final summary with the note link and the release URL.

---

## Owner decision points (Claude stops and asks)

| When | Decision |
|---|---|
| Phase 0, Task 0.4 | Keystore: rotate (A, recommended) / new key (B) / keep (C); history purge yes/no |
| Any phase | An existing test blocks a task (R6) |
| Phase 7 | Merge, push, release (R11) |

## Out of scope

- Any palette value or logo change.
- Android app UI (only its signing config is touched, in Phase 0).
- Engine behaviour (download logic, formats picked, history schema).
- Windows taskbar progress via COM (`ITaskbarList3`): there is no Qt 6 API for it; it can be a later plan if wanted.
- Actionable Windows toast buttons (they need WinRT packages); the tray notification click is used instead.
