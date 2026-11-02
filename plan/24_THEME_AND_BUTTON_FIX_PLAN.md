# Plan 24: Light/Dark Mode Re-Check + Cut-Off Buttons

## Goal

1. **Every** part of the app is readable and correct in **dark and light**, including menus, tooltips, dialogs, popups, message boxes, title bars and the splash screen, and it stays correct after a **live switch** in both directions.
2. "Same as Windows" really follows Windows, also while the app is open.
3. Theme switching stays instant (under 0.5 s).
4. The **Pause/Resume** button and all other icon buttons are drawn at their real size and are never cut off.

**Never changes:** palette values (`DARK_TOKENS` / `LIGHT_TOKENS`), logo, app behaviour outside the items below.

---

## Findings (audit 2026-11-02: every screen, dialog, menu and popup rendered in both themes, at 125 % scaling, plus a live dark → light switch)

| # | Finding | Evidence | Effect |
|---|---|---|---|
| **F1** | **Kit buttons are inflated by the app-wide button style.** `theme.py` → `QPushButton { padding: 6px 16px; min-height: 22px; border: 1px }` also applies to `AnimatedButton` / `IconButton`, which paint themselves. Every `IconButton` ends up **36 px tall** whatever size was asked for (28 or 32). | Pause button geometry `(x, 4, 28, 36)` inside a **36 px** header row → bottom at 39 px, **clipped by 4 px**. Queue ✕/retry/copy: 28 → 28×36. History/recent play/folder: 32 → 32×36. | **This is the "cut from below" bug** on Pause/Resume; other icon buttons are tall and off-center. |
| **F2** | **Menus are not themed.** No `QMenu` rule in the stylesheet: the History row "⋯" menu, the History "⋯" (Clear all) menu and the **tray menu** keep the native dark background (`#1e1e1e`) but take the theme's text colour. | Light mode: dark text on a dark menu, so the menus are **unreadable** (screenshots `light_15_row_menu`, `light_17_tray_menu`). Dark mode only looks right by luck. | Users can't read Copy link / Re-download / Delete / Clear all / Pause all / Quit in light mode. |
| **F3** | **Tooltips are not themed.** No `QToolTip` rule: tooltips are always dark grey `#3c3c3c` / `#d4d4d4`. | Same in both themes. | Inconsistent in light mode. |
| **F4** | **History shows a blank page right after switching to it.** The tab cross-fade starts at opacity 0 **before** History reloads its list synchronously, so the page stays fully transparent while the list loads. | Blank page (1 colour) 350 ms after switching; normal only after about 0.8 s. The longer the history, the longer it's blank. | The page looks empty or broken for a moment. |
| **F5** | **"Same as Windows" doesn't follow Windows live.** It's resolved only at start-up and when picked in Settings. | Qt 6.11 has `QStyleHints.colorSchemeChanged`, which isn't used. | Changing the Windows theme while the app is open doesn't update the app. |
| **F6** | **Dialog title bars aren't themed.** Only the main window and Settings call `apply_dark_title_bar`. The History delete / clear / warning dialogs and all `QMessageBox`es (8 call sites) keep the Windows default title bar and don't follow live switches. | Code: no title-bar call outside `main_window.py` / `settings_dialog.py`. | A light title bar on a dark dialog (and the reverse after a switch). |
| **F7** | **The Paused state shows stale numbers:** `8.4 MB/s • 302.3 MB / 689.5 MB • ETA --:--` while nothing downloads. | Screenshot `light_05_paused`. | Looks like it is still downloading. |
| **F8** | **Gap under the Done bar:** the empty stats line keeps its height. | Screenshots `*_06_done`. | Uneven spacing. |
| **F9** | **The snapshot tool misses menus, popups, dialogs, message boxes, the Paused state, Done with a real file, and live switches**, so F2, F4 and F6 slipped past the earlier gates. | `tools/ui_snapshots.py` renders 10 screens only. | Gaps in verification. |

Verified fine (no change needed): main screens, Settings, splash, quality dropdown popup, line-edit context menu (already token-styled), dialogs' content, live dark → light of the main window / History / Settings, theme switch time (0.25–0.4 s).

---

## Rules (binding)

| # | Rule |
|---|---|
| **R1** | Palette values and the logo are frozen. All colours come from tokens. |
| **R2** | Only the files listed per phase may change. Protected engine files (`downloader.py`, `download_manager.py`, `info_fetcher.py`, `history_db.py`, `history_service.py`, `app_updater.py`, `tool_manager.py`, `proc.py`, `jobs.py`, `url_tools.py`, `errors.py`, `thumbnails.py`, `network_monitor.py`) get **0** edits. |
| **R3** | Fix causes centrally: stylesheet rules in `theme.py`, one title-bar hook in `ThemeManager`. No per-widget colour patches and no copy-pasted styles. |
| **R4** | Smallest change per task. No layout redesigns, no new features, no refactors outside the task. |
| **R5** | Failing test first for each behaviour change. Visual polish is covered by the snapshot gate. |
| **R6** | Tests are add-only. If an old test blocks a task, stop and ask the owner. |
| **R7** | **Snapshot gate (done by Claude):** after each phase, run the extended `tools/ui_snapshots.py` (Phase 0). Open and check **every** image in both themes, including menus, dialogs, popups and the live-switch set. |
| **R8** | Known flaky/red tests are the same as before (scope test; `test_tab_looks` combobox/line-edit pair; single-instance test while the app is open). |
| **R9** | One commit per phase on `fix/ui-pass`. Push, merge and release only after the owner says yes. |
| **R10** | Loop: Phase 0 → 5 in order, each with its tests + full suite + snapshot gate + scope check + note (`docs/verification/plan24_phase<N>.md`). The owner sees only the final summary, unless a decision is needed. |

---

## Phase 0: Make the Audit Complete (tool only)

**Allowed:** `tools/ui_snapshots.py`, `tests/test_theme_polish.py` (new), `docs/verification/plan24_phase0.md`, this plan.

| Task | Do | Don't |
|---|---|---|
| 0.1 | Extend `tools/ui_snapshots.py` with: **Paused** state, **Done with a real file** (Open / Show in folder), copied-link chip, History search, **menus** (row ⋯, History ⋯, tray, line-edit context menu), **quality popup**, **tooltip** (forced via `QToolTip.showText`), **dialogs** (Settings, History delete / clear / warning, one `QMessageBox`), splash, and a **live-switch set** (start dark → switch light, and start light → switch dark, re-rendering main / History / Settings / one dialog). | Don't touch app code; keep the sandbox app data (never real data). |
| 0.2 | Add automatic checks to the tool output: (a) **clipping**: any visible child extending past its parent's rect (scroll contents excluded); (b) **menu/tooltip background** equals the theme `surface` token; (c) **icon buttons** have their requested size. Print a short findings list. | Don't use the pixel "contrast guess" from the audit (it gave false alarms); readability stays a test (`test_light_mode`) + visual review. |
| 0.3 | Record the baseline findings (should show F1, F2, F3) in the phase note. | — |

**Gate:** tool renders all states and menus in both themes; findings list matches F1–F3.

---

## Phase 1: Buttons at Their Real Size (fixes the cut-off Pause/Resume)

**Allowed:** `app/ui/theme.py` (stylesheet rule only), `app/ui/kit/buttons.py`, `app/ui/kit/progress_card.py`, `tests/test_theme_polish.py`, phase note.

| Task | Do | Don't |
|---|---|---|
| 1.1 | Mark kit buttons: `AnimatedButton` sets a dynamic property `kit="true"` (inherited by `IconButton`). In `build_qss` add `QPushButton[kit="true"] { padding: 0px; min-height: 0px; border: none; background: transparent; }`, so the global button style no longer resizes custom-painted buttons. | Don't change the global `QPushButton` rule (plain buttons in message boxes still need it). Don't change button colours or painting. |
| 1.2 | Progress card header: align the pause / Open / Show in folder buttons to the vertical centre of the row (`Qt.AlignVCenter`), so they line up with the title. | Don't change the row height or the title. |
| 1.3 | **Paused state:** `set_paused(True)` shows `Paused • 302.3 MB / 689.5 MB` (no stale speed, no ETA); resuming returns to the normal line on the next progress tick. | Don't change how sizes are computed. |
| 1.4 | **Done state:** hide the empty stats line, so there's no gap under the bar. | — |

**Tests (failing first):** every `IconButton(size=N)` is exactly N×N after polish in both themes; the progress-card pause button lies fully inside its header row; the paused stats text; the stats line is hidden at Done.
**Gate:** snapshot clipping list empty; Pause/Resume, queue ✕ / retry / copy and history icons look centred in both themes at 125 % and 150 %.

---

## Phase 2: Menus and Tooltips Follow the Theme

**Allowed:** `app/ui/theme.py` (stylesheet only), `tests/test_theme_polish.py`, phase note.

| Task | Do | Don't |
|---|---|---|
| 2.1 | Add `QMenu` rules to `build_qss`: background `surface`, text `text`, 1 px `border`, radius 8, item padding, `::item:selected` → `surface_hover`, `::item:disabled` → `text_muted`, `::separator` → `border`. This covers the History row ⋯, History ⋯, **tray menu**, and any future menu. | Don't style menus one by one; don't touch the line-edit context menu's own popup style (it already uses the same tokens). |
| 2.2 | Add a `QToolTip` rule: background `surface`, text `text`, 1 px `border`, small padding. | No new colours. |

**Tests:** a rendered `QMenu` (row menu and tray menu) has the `surface` background and readable text (contrast ≥ 4.5 from palette/stylesheet) in **both** themes and after a live switch; the stylesheet contains `QMenu` and `QToolTip` rules built from tokens.
**Gate:** menu, tray and tooltip snapshots readable in both themes.

---

## Phase 3: Window Chrome and "Same as Windows"

**Allowed:** `app/ui/theme.py` (`ThemeManager`), `app/ui/main_window.py` (reuse `apply_dark_title_bar`; remove now-duplicate calls only if the hook covers them), `app/ui/settings_dialog.py` (same), `app/main.py`, `tests/test_theme_polish.py`, phase note.

| Task | Do | Don't |
|---|---|---|
| 3.1 | **One title-bar hook:** `ThemeManager` installs an application event filter. On `Show` of any top-level window (main window, Settings, History dialogs, `QMessageBox`, splash), it applies the current theme's title bar. `apply()` re-applies it to all open top-level windows. | Don't add title-bar calls to each dialog. Don't change dialog layouts. |
| 3.2 | **Live "Same as Windows":** connect `QGuiApplication.styleHints().colorSchemeChanged`; when the saved theme is `system`, re-apply `resolve_theme("system")`. `windows_prefers_light()` prefers `styleHints().colorScheme()` and keeps the registry read as a fallback. | Don't change behaviour when Dark or Light is chosen explicitly. |
| 3.3 | Confirm switching stays instant: measure `apply()` with the main window + Settings open (target < 0.5 s). | No caching tricks unless the target is missed. |

**Tests:** showing a `QMessageBox` / History dialog calls the title-bar function with the current theme; `apply("light")` updates open dialogs; a simulated `colorSchemeChanged` with saved theme `system` switches the app, and with saved theme `dark` it doesn't.
**Gate:** dialog snapshots with the matching title bar (checked on the owner's PC in Phase 5, because offscreen renders don't include the title bar).

---

## Phase 4: History Never Blank on Switch

**Allowed:** `app/ui/main_window.py` (`_on_tab_changed` / `_fade_in_page`), `tests/test_theme_polish.py`, phase note.

| Task | Do | Don't |
|---|---|---|
| 4.1 | In `_on_tab_changed`, do the page's work first (History `refresh_items`, message resets), **then** start the cross-fade, so the fade runs on a page that is already filled. | Don't remove the fade; don't change History loading itself. |
| 4.2 | Safety: if the page is already covered by an effect from a previous fast switch, stop that fade and remove its effect before starting a new one. | — |

**Tests:** switching to History with 50 rows: within FAST + 100 ms the page is painted (effect gone or opacity ≥ 0.99); fast switching Video → Audio → History leaves no page with a leftover effect.
**Gate:** History snapshot right after the switch is filled in both themes.

---

## Phase 5: Full Verification and Release

1. Full suite (R8 known set only).
2. Extended snapshots in **dark, light, live dark→light and live light→dark**, at **100 %, 125 % and 150 %** scaling. Claude checks every image: text readable, no dark blocks in light, no light blocks in dark, menus/tooltips/dialogs themed, no clipping, icons centred.
3. Final note `docs/verification/plan24_final.md`: F1–F9 each marked fixed or explained.
4. Owner yes → merge to `main`, push, `python tools/release.py --notes "..."` (the app must be closed).
5. Owner's real-PC check: title bars of dialogs and message boxes in both themes; change the Windows theme while the app is open with "Same as Windows" selected; Pause/Resume button fully visible.

## Out of scope
- Palette or logo changes; new features; History loading speed; engine files.
- The earlier deferred items from Plan 23 (Add to queue always visible, Undo delete, close to tray, skeleton, list motion).
