# Phase 3: UI Kit and Animation System

**Goal:** One consistent, satisfying set of controls, a clean header, and a dark title bar, all in the existing red and black colours.
**Fixes:** B10, B11, B14. **Depends on:** Phase 2 (not strictly, but do it before the tab work).
**Files:** `ui/kit/*` (new), `ui/header.py` (new), `ui/theme.py`, `ui/main_window.py`.

---

## Chunk 3.1: Animation helpers

Tasks:
1. `ui/kit/anim.py`: helpers for 150 ms property animations (colour, position, opacity) using `QPropertyAnimation`; all easing `OutCubic`.
2. A single setting `animations_enabled` (default on) so animation can be switched off; also respect Windows "reduce animations" if detectable.

Done when: a demo window animates a colour and a slide with no UI lag.

---

## Chunk 3.2: Button system

Tasks:
1. `AnimatedButton` with roles `primary`, `secondary`, `ghost`, `icon`. Hover: brighten and soft glow. Press: scale down about 3%. Disabled: dimmed.
2. States: `set_loading(True)` shows a small spinner and blocks clicks. `flash_success()` shows a tick for about 1 second.
3. Same height everywhere (36 px) and consistent padding. Replace all `QPushButton` uses in tabs and settings.
4. Colours come only from `theme.py` tokens plus hover/pressed shades.

Done when: every button in the app reacts visibly to hover and press.

---

## Chunk 3.3: Checkbox and toggle

Tasks:
1. Custom checkbox drawn in code: rounded square, red fill when checked, white tick, 150 ms animation. Replaces the white-block style in `theme.py`.
2. Focus ring for keyboard users.

Done when: checked and unchecked states are clearly different in dark and light themes.

---

## Chunk 3.4: Header, tabs and Settings button

Tasks:
1. `ui/header.py`: a custom header with logo, tab buttons (Video, Audio, History), a **sliding red underline** that animates to the active tab, the Online/Offline badge, and a Settings button with a gear icon.
2. Stop using `QTabWidget.setCornerWidget`. Use a `QStackedWidget` for pages. This removes the clipped Settings button.
3. Online badge animates colour changes (green/red) and does not jump.

Done when: Settings button is fully visible at every window size, and the underline slides between tabs.

---

## Chunk 3.5: Dark title bar and layout width

Tasks:
1. On Windows 10 (20H1+) and 11 call `DwmSetWindowAttribute` with the immersive dark mode attribute (and Mica/accent off) so the title bar is dark in dark theme and light in light theme. Wrap in try/except and log.
2. Centre page content in a container with a max width of about 1100 px.
3. Minimum window size 760 × 520.

Done when: title bar matches the theme, and on a 1920 px screen the link box no longer stretches edge to edge.

---

## Chunk 3.6: Shared widgets

Tasks:
1. `ThumbLabel` (rounded, uses the thumbnail store, shows the fallback icon).
2. `Toast` (slides in bottom right, fades after 4 s, optional action button).
3. `InlineMessage` (error or info text that **auto-hides after 4 s** and is cleared when the tab changes).
4. `ProgressCard` skeleton (finished in Phase 4).

Done when: each widget has a small demo and unit test.

---

## Verification Gate: Phase 3

Evidence in `docs/verification/phase_3.md` (include screenshots).

### Automated
- [ ] `pytest-qt` tests: button states, loading, success flash, checkbox toggle, header tab switching, InlineMessage auto-hide, Toast lifetime.
- [ ] A test that fails if any `QPushButton(` is created outside the kit.

### Manual
- [ ] Hover and press on every button type feel responsive (no lag).
- [ ] Tab underline slides; Settings button never clipped (test at 760 px wide and maximised).
- [ ] Checkboxes visibly checked/unchecked.
- [ ] Title bar is dark in dark theme.
- [ ] Switch to light theme and back: everything stays readable.
- [ ] Colours unchanged versus the old build (compare screenshots).

### No-terminal check (mandatory)
- [ ] Launch the app from the shortcut or built exe: no console window.

### Sign-off
- [ ] All ticked and evidence saved. Then start Phase 4.
