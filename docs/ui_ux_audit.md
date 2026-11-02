# YOuTUbE: UI/UX Audit (v1.0.4)

Date: 2026-11-02 · Reviewer: senior UI/UX pass · Scope: every screen of the Windows app

**Hard limits from the owner:** keep the **colors** (palette in `app/ui/theme.py`) and the **logo** exactly as they are. Everything else is open: layout, spacing, type, motion, behaviour, and copy.

**Verification note:** screenshots were retaken after animations finished (450 ms). An earlier pass caught the status dot and checkbox mid-animation, so those two false findings were removed.

**Method:** I read all UI code (`app/ui/*`, `app/ui/kit/*`, about 6,000 lines). I then rendered the real app widgets in **dark and light mode** with sample data (sandbox app data, nothing real touched). The screenshots are in `docs/ui_audit/`.

---

## 1. Scorecard

| Area | Score | One-line verdict |
|---|---|---|
| Dark mode visuals | **6/10** | Clean and on-brand, but flat and loose: no surfaces, uneven edges, lots of dead space |
| **Light mode** | **2/10** | **Broken.** White text on white: titles, the app name, the active tab, and settings headings are invisible |
| Core flow (paste → fetch → download) | 7/10 | Works, but needs too many clicks and gives too little feedback before the download starts |
| Progress and queue | 6/10 | Accurate numbers now, but the queue rows are noisy and the count is misleading |
| History | 5/10 | Times are wrong (UTC), there is a horizontal scrollbar, rows are too airy, and actions are hidden |
| Settings | 5/10 | Too few useful options; no "System" theme; invisible headings in light mode |
| Motion and delight | 4/10 | Only a few small animations; nothing that rewards the user when a download finishes |
| Keyboard and accessibility | 4/10 | Focus rings exist on buttons and checkboxes, but there are no shortcuts, no drag & drop, and no clipboard help |
| Consistency (design system) | 4/10 | About 30 hard-coded colors and 7 font sizes, where the spec has 11 tokens and 4 sizes |

---

## 2. Top 12 problems (fix these first)

| # | Problem | Where | Impact |
|---|---|---|---|
| 1 | **Light mode is unusable.** 45 places hard-code `#FFFFFF` text, so titles, the brand name, the active tab, percent text, and settings headings disappear. Buttons, inputs, progress tracks, and thumbnail placeholders stay dark. | `header.py`, `video_tab.py`, `history_tab.py`, `settings_dialog.py`, `queue_widget.py`, `recent_list.py`, `kit/*` | Anyone who picks Light thinks the app is broken |
| 2 | **History shows UTC times.** `created_at` uses SQLite `CURRENT_TIMESTAMP` (UTC) and is printed raw, so in India every time is 5 h 30 m behind, and items look out of order. | `history_db.py` + `history_tab.format_date_str` | Wrong information, which hurts trust |
| 3 | **History has a horizontal scrollbar.** Long titles are not elided and a row can be wider than the window. | History tab | Looks unfinished |
| 4 | **Going offline opens a modal popup** ("Internet is off…") that blocks the window for a network blip. | `main_window._on_went_offline` | Interrupts work |
| 5 | **No size or format shown before downloading.** We now know the exact size (Plan 21), but the user only sees it after starting. | Video and Audio "ready" state | Users can't decide the quality by size |
| 6 | **The info card shows the previous video after an error.** "That doesn't look like a YouTube link" appears above the old video card. | Video tab | Confusing: which video is meant? |
| 7 | **"Up next (3)" counts failed items.** Two are waiting and one failed, but the label says 3 up next. | Queue | Misleading |
| 8 | **Waiting queue rows draw empty grey progress bars** (the failed row's bar is shorter). | Queue rows | Visual noise; looks like stuck downloads |
| 9 | **The Done state disappears after 1.2 s** with no "Open file" or "Show in folder" action. | Progress card | The happiest moment of the app is wasted |
| 10 | **The update banner has giant stretched buttons** (a filled blue "Update now" about 280 px wide) instead of the compact text buttons the spec asks for. | Update banner | Heavy and off-brand |
| 11 | **No keyboard flow:** no Ctrl+V auto-fetch, no Enter-to-download, no shortcuts. (Focus rings exist on buttons and checkboxes, but not on list rows.) | Whole app | Slow for power users |
| 12 | **Uneven left edges:** the input starts at 20 px, the info text at 195 px, the progress card at 20 px, and the recent and queue rows at 30 px. The scrollbar also pushes the Fetch button 7 px left when it appears. | Video and Audio tabs | Feels unaligned and "cheap" |

---

## 3. Findings by screen

Each finding lists **what is wrong → why it matters → the fix**.

### 3.1 Global and design system

| Finding | Fix |
|---|---|
| About **30 distinct hex colors** are used in widgets (`#888888`, `#333333`, `#1F1F1F`, `#65B8FF`, `#CCCCCC`, `#1A1A1A`, `#181818`, an orange `#FF8800`, and more). The design system defines 11 tokens. | One rule: **widgets never contain hex codes.** Every color comes from `DARK_TOKENS` / `LIGHT_TOKENS` through the stylesheet (`role` properties) or a `theme.color("text_muted")` helper. Map each stray grey to the nearest existing token. No new colors are needed. |
| Font sizes used: 11, 12, 13, 14, 15, 16, 18 px. The spec has 12, 13, 15, 18. | Snap to 4 sizes: **12** (meta), **13** (body), **15** (section title), **18** (video title). Remove 11 (too small on 1080p laptops), 14, and 16. |
| Spacing is mixed: margins of 20, 24, and 30 px; row heights of 72 and about 100 px. | Use the 4-px grid: page padding **16**, gaps **8 / 12 / 16 / 24**, list rows **64 px**. One left edge for everything. |
| Long titles wrap or overflow. | Elide with "…" in one line (`QFontMetrics.elidedText`) and show the full title as a tooltip. |
| Default window 800×600, min 760×520 (the spec says 760×560 / 640×480). | Default **880×640** (fits the queue plus recent list without scrolling). Min **640×480**. Remember the size and position between runs. |
| The theme only changes on Settings save, and hard-coded widget styles never update. | Theme switch = re-apply the stylesheet + `style().unpolish/polish` on top-level windows. With no hard-coded colors this becomes instant and complete. |
| No "System" theme option. | Add **System (default) / Dark / Light**. Follow Windows `AppsUseLightTheme` and listen for changes. |

### 3.2 Header

| Finding | Fix |
|---|---|
| The brand text "YOuTUbE" is white in light mode, so it's invisible. | Use the `text` token. |
| The active tab text is white in light mode (invisible). In dark mode the inactive tabs are fine. | Active = `text` + 2 px red underline (keep). Inactive = `text_muted`. Hover = `text`. |
| "Settings" is a bordered button with an icon **and** text. It's heavier than the tabs and pulls the eye. | Use an icon-only gear (32×32, `text_muted`, hover `surface_hover` circle) with the tooltip "Settings (Ctrl+,)". |
| The "Online" dot plus word is always shown, using space for good news nobody needs. | Show nothing when online. When offline, show an **"Offline"** pill (`error` dot + text). That way the status only appears when it matters. |
| The underline slide (150 ms) is good. | Keep it. Use the same easing (OutCubic) everywhere. |

### 3.3 Video tab: idle (first screen)

![](ui_audit/dark_02_video_idle.png)

| Finding | Fix |
|---|---|
| A big empty area under "Recently downloaded"; first-time users get no guidance. | **Empty state** (no history yet): a centered, text-only block (no artwork, per the spec). Line 1 "Paste a YouTube link to start", line 2 "Tip: press Ctrl+V anywhere". Muted text, no art (per spec). |
| A link copied before opening the app is ignored. | **Clipboard detect:** when the window gains focus and the clipboard holds a YouTube URL that differs from the last one, show a small chip under the input: "Use copied link: youtu.be/… [Fetch]". One click. |
| No drag & drop. | Accept dropped links and `.url` files on the window. Show a dashed `border` outline while dragging ("Drop link to fetch"). |
| Fetch needs a click. | Auto-fetch when a valid link is pasted (Ctrl+V or right-click paste), with a 300 ms debounce. Keep the Fetch button for typed links. |
| The placeholder "Paste a YouTube link" is fine. The Audio one, "…for audio extraction", is technical. | Audio: "Paste a YouTube link to save its audio". |
| The input has no clear (×) button. | Add an inline clear button that shows when there is text. Esc also clears. |

### 3.4 Video tab: ready (after Fetch)

![](ui_audit/dark_03_video_ready.png)

| Finding | Fix |
|---|---|
| The info card has no surface; the title floats at x=195 with no thumbnail when it is missing. | Card = `surface` fill, radius 8, padding 12. Thumbnail 160×90 (16:9) on the left, always present (a skeleton shimmer while loading, then a fade-in). Title 15 px semibold, 2 lines max; meta line 12 px muted: `Channel • 1:30:12`. |
| The quality dropdown shows only labels. | Show **size per option**: `1080p · 690 MB`, `720p · 410 MB`, `Audio only…`. The data is already in the `-J` formats (exact `filesize`). This is the most useful decision aid in the whole app. |
| "Add to queue" is hidden while idle and appears only during a download. The action row changes shape between states. | Always show **[Download] [Add to queue]**. "Add to queue" is a secondary button and works in both states (if idle, it just queues without starting). Same layout in every state means no jumping. |
| The Download button is at the left edge, under the dropdown. | Put the action row inside the card, right-aligned: `[quality ▾]  [Add to queue]  [Download]`. The red primary button is last, where the eye ends. |
| No destination shown. | One muted line in the card: "Saves to Downloads · Change". This avoids the "where did it go?" question. |

### 3.5 Video tab: downloading, done, error

![](ui_audit/dark_05_video_downloading.png)

| Finding | Fix |
|---|---|
| The progress card thumbnail is a grey placeholder even though the thumbnail is known. | Reuse the fetched thumbnail (it's already in `job.thumbnail_bytes`). |
| The bar is 6 px with a red fill, good. The 1.6 s "highlight" shimmer loops forever. | Keep the fill. Run the shimmer only while bytes are moving, and stop it during stalls, which gives an honest signal. |
| The stats line `8.4 MB/s • 302.3 MB / 690.1 MB • ETA 01:12` is good, but 11 px gray is hard to read. | 12 px. ETA as words: "about 1 min left". Speed is fine. |
| **No Pause.** Only Cancel, which loses progress. | Add **Pause / Resume** (the manager already pauses for offline, so reuse it). Cancel asks for confirmation only if more than 10% is done. |
| Cancel and Add to queue sit in the top action row, far from the progress they control. | Put the controls on the progress card itself: `[Pause] [Cancel]` as small icon buttons at the right of the title row. |
| **Done: the bar sits at 100% for 1.2 s, then the card collapses.** | Done state for 4 s (or until hover ends): the bar turns into a check pulse (scale 1.0→1.15→1.0, 300 ms). Text: "Saved · 688.2 MB" plus buttons **[Open] [Show in folder]**. Then collapse with a 200 ms height animation, and the new item slides into "Recently downloaded" at the top (highlighted with `surface_hover` for 1 s). |
| An error (invalid link) shows above the stale card. | On a new fetch attempt, **clear the old card first**. Errors appear **inside the input area**: red 1 px border on the input + the message under it in `error` color with a small icon. |
| Errors fade after 4 s and can't be copied. | Keep them until the input changes. Add "Copy details" for download failures (it already exists in the queue; reuse it). |

### 3.6 Queue ("Up next")

| Finding | Fix |
|---|---|
| The count includes failed items. | Two groups: **Up next (2)** and **Failed (1)** with "Retry all · Clear". |
| Waiting rows draw empty progress tracks. | No bar for waiting items; show "Waiting" text or the position "#2". Only the active download has a bar. |
| No reorder; only remove. | Drag handle to reorder, plus "Move to top" in the right-click menu. |
| Row icons (retry, copy, ×) are always visible, which is busy. | Show the actions on hover/focus (keep × always visible for touch). Make failed reason text wrap to 1 line with an ellipsis; the full text goes in a tooltip. |
| The failed text is red and crowded next to the icons. | Put the reason on the meta line: `Video • 1080p • Failed: This video is private.` |

### 3.7 Recently downloaded (Video and Audio tabs)

| Finding | Fix |
|---|---|
| Rows have no surface and the click target is unclear; the play and folder icons are always on. | Row = 64 px, hover `surface` fill, radius 8. Double-click = play. Icons are muted and become `text` on hover. Add a right-click menu: Play, Show in folder, Copy link, Re-download, Remove from history. |
| Test rows "Test • 7.0 B" are real junk entries. | Hide entries under 1 KB or with missing files (or show a "File missing" pill). Offer "Remove" inline. |
| "See all video history →" uses `#3EA6FF` (dark info color) even in light mode, which is low contrast on white. | Use the `info` token (light = `#065FD4`). |

### 3.8 Audio tab

| Finding | Fix |
|---|---|
| The same structure as Video, but the format choice is hidden until Fetch. | Show the format chips **MP3 · M4A · Opus · FLAC · Original** right away (remember the last choice). |
| No bitrate or size hint. | `MP3 · 320 kbps · ~41 MB` in the chip tooltip or the subline. |
| "Best original • 1.2 GB" for audio looks wrong to users. | Show the real codec: "Original (Opus)". If a size is far above the expected audio size, flag it in the log (a possible wrong format pick). |

### 3.9 History tab

![](ui_audit/dark_08_history.png)

| Finding | Fix |
|---|---|
| **UTC times** (Top 12 #2). | Store with `datetime('now','localtime')` **or** convert on display: `datetime.fromisoformat(s).replace(tzinfo=utc).astimezone()`. Show **relative** times: "Today, 9:51 AM", "Yesterday", "17 Oct". |
| **Horizontal scrollbar** (Top 12 #3). | Elide titles; `setHorizontalScrollBarPolicy(AlwaysOff)`; actions get a fixed width. |
| Rows are about 100 px apart with no surfaces; only the play icon shows, and 5 actions are hidden. | 64 px rows with hover surface. Show the most used actions on hover: **Play · Folder · ⋯ (more)**. The overflow menu holds Copy link, Re-download, Delete. |
| No grouping. | Section headers: **Today · Yesterday · This week · Earlier**. |
| The "All" filter chip is **red**, which breaks the "red is rare" rule. | Selected chip = `text` fill with `bg` text (an inverted neutral). Red stays only on Download, progress, tab underline, and logo. |
| "Clear all" sits right next to search; it's a destructive action placed like a filter. | Move it into a `⋯` menu at the right; keep the confirmation dialog. |
| Search has no clear button or result count. | `×` clear + "12 results" muted text. Search title **and** channel. |
| Deleting has a confirmation dialog for every row. | Delete instantly + **"Removed · Undo"** toast for 5 s (the Toast widget already exists). |
| Empty state text exists but uses hard-coded white. | Tokens. Add an "Open Video tab" text button. |

### 3.10 Settings

![](ui_audit/dark_10_settings.png)

| Finding | Fix |
|---|---|
| The checkbox looks right in dark mode, but its label is invisible in light mode. | Label in the `text` token. Optional: a **toggle** for on/off settings. |
| Section headings are white in light mode (invisible). The path field stays dark in light mode. | Tokens. |
| Only 3 real settings. | Add a **Downloads** section: default video quality, default audio format, "Ask where to save each time", "Open folder when done", filename style (Title / Title [id]). Add a **Behaviour** section: "Start with Windows", "Minimize to tray on close", "Show notification when done", "Auto-fetch pasted links", "Reduce motion". |
| Changes apply only on close (unclear). | Apply instantly and show a small "Saved" tick next to the changed row (fade out after 1 s). |
| "Check now" gives no inline result. | Inline status: "You're up to date (1.0.4)" / "Version 1.0.5 is available · Update". |
| About shows raw links. | "YOuTUbE 1.0.4 · Check for updates" and "Open-source licenses" (collapsible). Keep "Export log" under a **Help** section with "Open log folder". |

### 3.11 Splash

| Finding | Fix |
|---|---|
| The splash background is a lighter grey than the app (`#1E1E1E`-ish vs `#0F0F0F`), which flashes on the hand-off. | Use the `bg` token so the hand-off is seamless. In light theme use the light `bg`. |
| The progress bar jumps 10 → 80 → 90 → 100. | Animate the value between steps (200 ms). An indeterminate shimmer while checking for updates. |
| The update text is good ("Downloading update 1.0.4… 45%"). | Add the size: "Downloading update 1.0.4 · 18 of 36 MB". |

### 3.12 Update banner and offline

![](ui_audit/dark_09_banner_offline.png)

| Finding | Fix |
|---|---|
| Huge stretched buttons; filled blue "Update now" (blue is not an accent in the spec). | One 40 px row: `info` text "Version 1.0.5 is available" · text buttons **Update** (semibold) · **Later**. Show progress inline as a 2 px bar along the bottom of the row. |
| "Required update" locks the inputs with no explanation near them. | When locked, the input placeholder reads "Update required to download · Update now". |
| Going offline opens a modal **message box** ("Internet is off…"). | No modal. Show the header "Offline" pill + a thin muted line under the input: "You're offline. Downloads will resume automatically." Modals for network blips interrupt work. |

### 3.13 Windows integration (missing delight)

| Idea | Why it pleases users |
|---|---|
| **Taskbar progress** (green fill on the taskbar icon, via `ITaskbarList3`) | Users see progress while working in other apps, as Chrome and Edge do |
| **Toast notification with buttons** "Open" / "Show in folder" when done | One click to the file. Today the tray message has no actions |
| **Tray menu**: Show, Pause all, Resume all, Quit; tooltip "Downloading 2 of 3 · 46%" | Lets the app live quietly in the background |
| **Close to tray while downloading** (optional setting) | Prevents killing downloads by accident |
| **Jump list**: "Paste link from clipboard" | Fast start from the taskbar |

---

## 4. Light mode: what it should look like (same palette)

Light tokens already exist and are correct: `bg #FFFFFF`, `surface #F2F2F2`, `surface_hover #E5E5E5`, `border #E0E0E0`, `text #0F0F0F`, `text_muted #606060`, `info #065FD4`, `error #CC0000`, `accent #FF0000`. The problem is only that widgets ignore them.

| Element | Today (light) | Target (light) |
|---|---|---|
| Video titles, brand, headings | `#FFFFFF`, invisible | `text #0F0F0F` |
| Active tab label | invisible | `text`; inactive `text_muted` |
| Secondary buttons (Fetch, Cancel, Settings) | dark `#212121` fill | `surface #F2F2F2` fill, `border`, `text` |
| Progress track and queue tracks | black | `surface_hover #E5E5E5` track, red fill |
| Thumbnail placeholders | dark boxes | `surface` box with a `text_muted` play glyph |
| Path field (Settings) | dark | `surface` |
| Links ("See all", license links) | `#3EA6FF` (fails contrast on white: about 2.6:1) | `info #065FD4` (about 6.5:1) |
| Error text | `#FF4E45` (about 3.3:1) | `error #CC0000` (about 5.9:1) |
| Window title bar | stays dark | light caption (`apply_dark_title_bar(is_dark=False)` already exists; call it on every theme change) |

```
LIGHT (target)                                          DARK (target)
┌─────────────────────────────────────────────┐         ┌─────────────────────────────────────────────┐
│ ■ YOuTUbE   Video  Audio  History       ⚙  │ white   │ ■ YOuTUbE   Video  Audio  History       ⚙  │ #0F0F0F
│             ─────                           │         │             ─────  (red underline)          │
│ ┌───────────────────────────────────┐ ┌───┐ │         │ ┌───────────────────────────────────┐ ┌───┐ │
│ │ Paste a YouTube link        ×     │ │Get│ │ #F2F2F2 │ │ Paste a YouTube link        ×     │ │Get│ │ #212121
│ └───────────────────────────────────┘ └───┘ │         │ └───────────────────────────────────┘ └───┘ │
│ ┌─────────────────────────────────────────┐ │         │ ┌─────────────────────────────────────────┐ │
│ │ ▓▓▓▓▓▓▓  So Weak His Father Wanted…     │ │ surface │ │ ▓▓▓▓▓▓▓  So Weak His Father Wanted…     │ │ surface
│ │ ▓thumb▓  Recap Studio • 1:30:12         │ │         │ │ ▓thumb▓  Recap Studio • 1:30:12         │ │
│ │ ▓▓▓▓▓▓▓  Saves to Downloads · Change    │ │         │ │ ▓▓▓▓▓▓▓  Saves to Downloads · Change    │ │
│ │ [1080p · 690 MB ▾] [Add to queue][■DL■] │ │         │ │ [1080p · 690 MB ▾] [Add to queue][■DL■] │ │
│ └─────────────────────────────────────────┘ │         │ └─────────────────────────────────────────┘ │
│ Downloading  ▓▓▓▓▓▓▓▓▓░░░░░░░  46%   ⏸ ✕   │         │ Downloading  ▓▓▓▓▓▓▓▓▓░░░░░░░  46%   ⏸ ✕   │
│ 8.4 MB/s • 302 / 690 MB • about 1 min left  │         │ 8.4 MB/s • 302 / 690 MB • about 1 min left  │
│ Up next (2)                     Failed (1)  │         │ Up next (2)                     Failed (1)  │
│ Today                                        │         │ Today                                        │
│ ▓▓▓  Title…            1080p • 688 MB  ▶ 📁 │         │ ▓▓▓  Title…            1080p • 688 MB  ▶ 📁 │
└─────────────────────────────────────────────┘         └─────────────────────────────────────────────┘
```
(The ▶ 📁 marks stand for the existing line icons, not emoji.)

**Dark mode refinements (same palette):** use **elevation by surface**, not shadows. The page is `bg #0F0F0F`, cards and rows on hover are `surface #212121`, hover inside cards is `surface_hover #272727`, and dividers are `border #303030`. This alone fixes the "floating text" look without adding any color.

---

## 5. Motion and micro-interactions (customer delight)

**Note:** `02_DESIGN_SYSTEM.md §4` allows only 2 animations. The app already has more (tab underline, toast slide, checkbox, shimmer). I recommend **updating §4** to a small, consistent motion system. It should be subtle and fast, and honour "Reduce motion" (the setting and the Windows preference; `kit/anim.py` already checks the setting).

| Token | Value | Use |
|---|---|---|
| `fast` | 120 ms, OutCubic | Hover, press, focus ring |
| `base` | 180 ms, OutCubic | Show/hide, fade, tab underline |
| `slow` | 260 ms, OutCubic | Height expand/collapse, list insert |
| `celebrate` | 300 ms, OutBack (small overshoot) | Done check pulse only |

| Interaction | Animation |
|---|---|
| Button hover/press | Background color 120 ms; press scale 0.98 |
| Paste → fetch | The input border pulses `text_muted` once; the card **skeleton** (shimmer blocks for thumb, title, meta) appears instantly, then fades into the real content (180 ms) |
| Thumbnail load | 180 ms fade-in from the placeholder |
| Quality change | The size text cross-fades |
| Download start | The card collapses (260 ms) and the progress card grows from it, so the user sees "this became that" |
| Progress | The bar value animates smoothly between ticks (already partly there); the percent number counts up |
| Done | Check pulse (300 ms) + the row slides into Recently downloaded with a 1 s highlight |
| Queue add | The new row slides in from the top of the list (180 ms) |
| Remove / delete | Fade + height collapse (180 ms) + Undo toast |
| Error | Input shake 3 × 4 px (200 ms) + red border; no shake if reduce-motion is on |
| Tab switch | Underline slide (keep) + content cross-fade 120 ms |
| Theme switch | 180 ms cross-fade of the window (grab → fade overlay) |

---

## 6. Keyboard and accessibility

| Add | Detail |
|---|---|
| Shortcuts | **Ctrl+V** (anywhere: paste + fetch), **Enter** (fetch / download when ready), **Ctrl+1/2/3** tabs, **Ctrl+F** history search, **Ctrl+,** settings, **Space** pause/resume active, **Esc** clear input / close dialog |
| Focus ring | Buttons and checkboxes already draw an `info` focus ring. Extend it to list rows, chips, and icon buttons; a logical tab order (input → fetch → quality → download) |
| Screen readers | `setAccessibleName` on icon-only buttons (play, folder, retry, ×, gear) |
| Contrast | Dark passes. Light passes once the tokens are used (see §4). **Known limitation:** white on `#FF0000` is about 4.0:1. Keep the Download label **semibold 14 px** for readability (the color is fixed by the owner). |
| Hit targets | Icon buttons are at least 32×32 (most already are) |
| DPI | Test at 125% and 150% scaling (common on laptops); avoid fixed pixel widths for buttons that contain text (`Add to queue` is fixed at 110 px and clips in some languages) |

---

## 7. Copy (microcopy) fixes

| Today | Better |
|---|---|
| "Paste a YouTube link for audio extraction" | "Paste a YouTube link to save its audio" |
| "Done. Saved to Downloads." | "Saved to Downloads · 688.2 MB" + [Open] [Show in folder] |
| "Up next (3)" incl. failed | "Up next (2)" · "Failed (1)" |
| "Failed: This video is private." (red, crowded) | Meta line: "Failed · This video is private" |
| "Internet is off. You can still view your history." (modal) | Inline: "You're offline. Downloads will resume automatically." |
| "Version 1.0.5 is available." + "Update now"/"Later" | "Version 1.0.5 is available · **Update** · Later" |
| `2026-11-02 04:21` (UTC) | "Today, 9:51 AM" |
| "Best original" | "Original (Opus)" |
| "ETA 01:12" | "about 1 min left" (keep the exact value in a tooltip) |

---

## 8. Roadmap (suggested phases for a later plan)

| Phase | Content | Effort | Value |
|---|---|---|---|
| **P0 – Fix what's broken** | Tokens everywhere (light mode), UTC times, horizontal scroll + eliding, offline modal → inline, stale card on error, queue count, waiting bars, banner buttons, splash bg | 1–2 days | ⭐⭐⭐⭐⭐ |
| **P1 – Core flow upgrades** | Size per quality, always-visible Add to queue, card layout, Pause/Resume, Done state with Open/Show in folder, clipboard detect, auto-fetch on paste, drag & drop, shortcuts, focus rings | 2–3 days | ⭐⭐⭐⭐⭐ |
| **P2 – History and settings** | Relative dates + grouping, hover actions + ⋯ menu, Undo delete, search count, new settings (default quality/format, start with Windows, tray, notifications, System theme) | 2 days | ⭐⭐⭐⭐ |
| **P3 – Delight** | Motion system (§5), skeletons, done pulse, taskbar progress, actionable toast notifications, tray menu, jump list | 2–3 days | ⭐⭐⭐⭐ |

Each phase can follow the same rules as Plans 21–22: tests first, smallest change, light + dark screenshots at each gate, and no color or logo changes.
