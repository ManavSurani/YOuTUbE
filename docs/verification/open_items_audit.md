# Open Items Audit & Resolution Report (M6, M3, M4, M11)

## 1. Summary of Items Audited

| Item | Description | Status | Evidence / Resolution |
|:---:|:---|:---:|:---|
| **M6** | Failed queue row shows friendly sentence without "Copy details" button | **CLOSED** | Added vector-styled `IconButton("copy", tooltip="Copy error details")` to `QueueRow` in `app/ui/queue_widget.py`. Copies raw `failure_reason` to `QApplication.clipboard()` and flashes green on success. Verified by `test_failed_queue_row_has_copy_details_button_and_copies_to_clipboard` in `tests/test_per_item_cards.py`. |
| **M4** | Two VIDEO jobs of same video with different quality write same name | **CLOSED** | Verified in `app/core/downloader.py:170`. The video output template explicitly includes `[%(height)sp]`: `%(title).180B [%(id)s] [%(height)sp].%(ext)s`. Verified by `test_video_output_template_has_height_and_capped_title` and `test_video_different_heights_use_different_formats` in `tests/test_downloader.py`. |
| **M11**| Dialogue text mismatch & corrupt queue file handling defects | **CLOSED** | All sub-items resolved across prior phases: (1) Exit confirmation text matches D2 exact wording (Phase 2), (2) Corrupt/empty modern queue files renamed to `.corrupt` or timestamped (Phase 3), (3) 2-restart limit for active jobs enforced (Phase 1), (4) 100ms resume polling with 3s force cancel and 10s failure (Phase 4), (5) 90s watchdog default with post-processing bypass (Phase 5). |
| **M3** | Logs contain unscrubbed URLs and Windows user paths | **OPEN** | Retained as OPEN for owner review. Live in-stream log filtering risks masking diagnostic errors or breaking regression tests inspecting raw error signatures. Recommended resolution: Implement an export-time redaction filter in the Settings "Export log" handler rather than mutating live log output. |

---

## 2. Detailed Findings

### M6: Failed Queue Row Copy Details Button
- **Audit Finding:** Previously, when a queued download failed, the card rendered the failure explanation label, but power users wanting to inspect the full yt-dlp error string had to navigate to Settings to export logs.
- **Resolution:** Updated `QueueRow` in `app/ui/queue_widget.py`. When `failure_reason` is present, an `IconButton("copy")` is created alongside Retry and Remove.
- **Verification:** `tests/test_per_item_cards.py::test_failed_queue_row_has_copy_details_button_and_copies_to_clipboard` passed.

### M4: Multi-Quality Filename Collision Protection
- **Audit Finding:** If a user enqueues a video at 1080p and subsequently enqueues the same video at 720p to the same directory, both must persist independently without clobbering or overwriting.
- **Resolution:** `build_video_cmd` includes `[%(height)sp]` in the output template. A 1080p download saves as `Title [id] [1080p].mkv` and a 720p download saves as `Title [id] [720p].mkv`.
- **Verification:** Unit tests confirm distinct format selectors and distinct output templates.

### M11: Identified Safety Defects
- **Audit Finding:** Earlier status report noted potential for zombie workers, infinite restore loops, or lost state on corrupt queue files.
- **Resolution:**
  - S1: `_handle_corrupt_queue_file` renames corrupt modern queue files to `.corrupt` / `.corrupt_<timestamp>`.
  - S2a: Active job restart count capped at 2. 3rd restore fails with exact D1 message.
  - S2b: Quit prompt dialog text updated to exact D2 wording.
  - S3: Resume polling at 100ms; force cancels at attempt 30 (~3s); fails at attempt 100 (~10s) with D3 message.
  - S4: Watchdog timeout default set to 90s, bypassing all post-processing stages.
- **Verification:** All associated unit tests pass.

### M3: Privacy & Scrubbing in Logging
- **Audit Finding:** Log records written by yt-dlp and download managers currently retain absolute filesystem paths (`C:\Users\<Username>\Downloads`) and YouTube URLs.
- **Technical Analysis:**
  - Masking paths at runtime via `RotatingFileHandler` regex filters could alter yt-dlp diagnostic outputs required when troubleshooting extraction errors.
  - Additionally, existing test suites (e.g. `test_download_lanes`, `test_download_manager`) use `caplog` to inspect log records directly. Mutating `record.msg` or `record.args` risks unintended regression in test assertions.
- **Owner Recommendation:** Keep M3 documented as **OPEN**. Implement path and token anonymization at the point of user export (`Export log` button in Settings) via a dedicated redaction pipeline, leaving local disk logs intact for debugging.
