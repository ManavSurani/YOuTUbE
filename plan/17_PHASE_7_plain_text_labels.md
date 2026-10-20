# Phase 7 Plan: Plain Text for Labels that Show Web Data

## Goals
Satisfy autonomous requirement **U1**:
- Labels that show web data (titles, channels, queue statuses, failure reasons, history rows, info card, inline messages) are strictly configured with `setTextFormat(Qt.TextFormat.PlainText)` to prevent rich text/HTML injection (SEC-01).
- Labels that intentionally show rich text for fixed developer content (e.g. Links in About dialog) are NOT touched.
- Test-First methodology (Rule R2): write unit tests building each widget with a hostile payload `'<b>x</b><img src="http://example.invalid/a.png">'` and assert `textFormat() == Qt.TextFormat.PlainText` and `text()` equals the raw string.

---

## Chunk 7.1: Unit Tests for Plain Text Format (`tests/test_ui_plain_text.py`)
- Test real instances of widgets:
  1. `MediaInfoCard` (in `video_tab.py` / `audio_tab.py`): title label, channel/meta label.
  2. `QueueWidget` (row items in `queue_widget.py`): title label, status label.
  3. `RecentList` (in `recent_list.py`): title labels.
  4. `HistoryTab` (in `history_tab.py`): item row title and channel labels.
  5. `ProgressCard` (in `app/ui/kit/progress_card.py`): title label, stage label, error label.
  6. `InlineMessage` (in `app/ui/kit/inline_message.py`): message label.
- Assert that for every label displaying dynamic content, `textFormat() == Qt.TextFormat.PlainText`.

---

## Chunk 7.2: Implementation in UI Files
- Set `setTextFormat(Qt.TextFormat.PlainText)` on labels in:
  1. `app/ui/queue_widget.py` (title label, status label)
  2. `app/ui/video_tab.py` (MediaInfoCard title & channel, stage label, error label)
  3. `app/ui/audio_tab.py` (MediaInfoCard title & channel, stage label, error label)
  4. `app/ui/history_tab.py` (HistoryRow title & channel)
  5. `app/ui/recent_list.py` (RecentItemWidget title)
  6. `app/ui/kit/progress_card.py` (title label, stage label, status label)
  7. `app/ui/kit/inline_message.py` (message label)

---

## Chunk 7.3: Verification of Phase 7
- Run `python -m pytest tests/test_ui_plain_text.py`.
- Run full test suite.
- Update `docs/verification/requirements_matrix.md` row U1 to PASS.
- Update `docs/verification/autonomy_log.md` and commit.
