# Progress Log Evidence & Analysis (Chunk 1)

## 1. Overview
Investigation of `%APPDATA%\YOuTUbE\logs\app.log` (and archives `app.log.1`, `app.log.2`) on Windows to establish empirical baselines for progress parsing, size accounting, and error handling.

---

## 2. Real Progress Output Sample (Last 40 YTPROG Lines)

```text
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71155833|97370030|NA|2317487.9420334543|11|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71164025|97370030|NA|3395946.9421748985|7|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71180409|97370030|NA|5745155.822049622|4|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71213177|97370030|NA|9680271.166571265|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71278713|97370030|NA|12590850.990074327|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71409785|97370030|NA|11457919.15636181|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|71671929|97370030|NA|11171772.832463745|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|72196217|97370030|NA|11333712.203925494|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|73244793|97370030|NA|11404826.218875991|2|none|opus
2026-10-12 04:33:40 [INFO] youtube_app: YTPROG|downloading|75341945|97370030|NA|11547164.944092283|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|79536249|97370030|NA|11479972.459069975|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81364456|97370030|NA|11425477.19230436|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81365480|97370030|NA|1019697.8385565053|15|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81367528|97370030|NA|1542178.5622980252|10|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81371624|97370030|NA|2385714.257419457|6|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81379816|97370030|NA|4056192.7494805767|3|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81396200|97370030|NA|6600762.786971395|2|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81428968|97370030|NA|11005569.822175222|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81494504|97370030|NA|13536688.090135252|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81625576|97370030|NA|10987987.443867007|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|81887720|97370030|NA|11089807.171400419|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|82412008|97370030|NA|11226420.485180492|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|83460584|97370030|NA|11466480.842779616|1|none|opus
2026-10-12 04:33:41 [INFO] youtube_app: YTPROG|downloading|85557736|97370030|NA|11462345.088014515|1|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|89752040|97370030|NA|11503742.181211991|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91691144|97370030|NA|11471960.12295657|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91692168|97370030|NA|689954.5857028113|8|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91694216|97370030|NA|990917.6257786665|5|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91698312|97370030|NA|1743693.949193829|3|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91706504|97370030|NA|2851651.444759207|1|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91722888|97370030|NA|4943158.944718767|1|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91755656|97370030|NA|7693572.352800682|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91821192|97370030|NA|10743551.369718933|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|91952264|97370030|NA|9711347.708131976|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|92214408|97370030|NA|11326519.145250272|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|92738696|97370030|NA|11166192.387062343|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|93787272|97370030|NA|11298231.661363967|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|95884424|97370030|NA|11374530.85080569|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|downloading|97370030|97370030|NA|11417610.752642773|0|none|opus
2026-10-12 04:33:42 [INFO] youtube_app: YTPROG|finished|97370030|97370030|NA|10392636.424171438|NA|none|opus
```

---

## 3. Real Error Output Sample (Last 15 ERROR Lines)

```text
2026-10-12 04:32:54 [INFO] youtube_app: ERROR: unable to download video data: HTTP Error 403: Forbidden
2026-10-12 04:32:54 [ERROR] youtube_app: yt-dlp exited 1: [youtube] Extracting URL: https://www.youtube.com/watch?v=6F5RWSiSxcI
ERROR: unable to download video data: HTTP Error 403: Forbidden
```

---

## 4. Quantitative Findings

| Metric | Active `app.log` | Archive `app.log.1` | Archive `app.log.2` | Total | Notes |
|---|---|---|---|---|---|
| Total `YTPROG` Lines | 1,686 | 7,581 | 26 | 9,293 | Recorded from real yt-dlp execution |
| Lines with `NA` in `downloaded` | 0 | 0 | 0 | 0 | yt-dlp always emits integer for `downloaded_bytes` |
| Lines with `total == NA` & `estimate <= downloaded` | 0 | 0 | 6 | 6 | Occurs in small initial fragments (e.g. `712` bytes) |
| First Lines of Download Session | `downloading` | `downloading` | `downloading` | - | Small chunk (e.g. 1024 B), speed/eta `NA` |
| Finished Stream Lines | `finished` | `finished` | `finished` | - | Final stream byte total, `eta=NA` or `0` |

---

## 5. Investigation of Problem P4 (144p HTTP 403 Forbidden)

1. **Sequence of Events:**
   - Video `6F5RWSiSxcI` was downloaded at `2160p` (4K) successfully at `04:31:33` – `04:32:49`.
   - At `04:32:49`, queue started job `3c911825-1044-401b-938b-7a91e55e4988` for the same video at `144p` (`format 394+251`).
   - At `04:32:54` (5 seconds later), yt-dlp received:  
     `ERROR: unable to download video data: HTTP Error 403: Forbidden`
2. **Repetition:** Appeared **once** in the log for this video.
3. **Start Type:** First start of the queued job, not a manual retry.
4. **Diagnosis:** Likely, unproven: YouTube rate-limiting / player API token expiration during rapid sequential format extraction for the same video ID.
5. **Fallback:** `app/core/errors.py` line 109 fell through to `"Something went wrong. Copy the details and try again."`
