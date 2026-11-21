# Mission 2 — Lane M2.1: Memory investigation findings

- **Investigated:** 2026-11-18 02:03–02:05 EST (07:03–07:05 UTC), read-only. No files edited, no process killed, no config changed, no restart.
- **Question:** why is host MEM% at 76.67% (01:52 EST reading) vs the 70% cap in `config/atlas.json` (`limits.max_mem_pct: 70`)?
- **Short answer: it is NOT ATLAS. It is shared-host memory pressure from other tenants, measured by a host-wide metric ATLAS cannot control.**

## 1. How the MEM% number is made

`core/atlas_monitor.py`, `mem()` reads host `/proc/meminfo` and computes `100 * (1 - MemAvailable / MemTotal)`. The dashboard MEM% is therefore **whole-host memory pressure**, not ATLAS's own usage. The 70% cap is applied to a number ATLAS does not control.

## 2. Live memory picture (measured 02:03 EST, `free -m` + `/proc/meminfo`)

| Measure | Value | Source |
|---|---|---|
| Host RAM total | 7,934 MB (8,124,900 kB) | `free -m` / `/proc/meminfo` MemTotal |
| Used | 6,728 MB | `free -m` |
| Free | 124–133 MB | `free -m` / MemFree 132,816 kB |
| Buff/cache | 1,478 MB | `free -m` |
| Available | 1,205 MB (MemAvailable 1,164,712 kB) | `free -m` / meminfo |
| MEM% now | **84.92%** (snapshot 07:03:50 UTC) | daemon snapshot.json |
| Swap used | ~383–399 MB of 1,024 MB; SwapCached ~177 MB; Zswap 68 MB | meminfo |
| Cell cap (this cell) | 6 GB (6,442,450,944 B); oomKills 0 | runtime resources |
| Kernel slab | ~326 MB | meminfo Slab |
| Page cache | ~1,266 MB | meminfo Cached |
| Anonymous pages | ~721 MB | meminfo AnonPages |

Swap is actively in use and MemFree is ~130 MB: the host is genuinely under memory pressure, not just holding reclaimable cache.

## 3. Biggest memory consumers (`ps aux --sort=-rss`, 02:03 EST)

| PID | Process | RSS | %MEM (host) | ATLAS? |
|---|---|---|---|---|
| 67 | `/opt/hatch/bin/hatch daemon` (platform runtime) | 480,960 KB = **470 MB** | 5.9% | No — host platform, do not touch |
| 11177 | `bun run .../skills/spaces/ts-runtime/dist/worker.js` | 43,480 KB = 42 MB | 0.5% | No — platform JS worker |
| 746 | `hatch-execd` (platform) | 11,772 KB = 11.5 MB | 0.1% | No |
| 9711 | `python3 core/atlas_monitor.py` (ATLAS daemon) | **10,816 KB = 10.6 MB** | 0.1% | **Yes — the only ATLAS process** |
| 1 | systemd | 5,076 KB | 0.0% | No |
| 17 | systemd-journald | 3,504 KB | 0.0% | No |

- **Visible RSS total (all processes in this container): 568,560 KB = 555 MB = 7.0% of host RAM.**
- The largest consumer is the platform `hatch` daemon (470 MB). It is host infrastructure, not ATLAS, and must not be killed or tuned by us.
- **~5.5 GB of host RAM is used by memory attributable to no visible process.** `ps` shows only ~10 processes; AnonPages (~721 MB) + cache (~1,266 MB) + slab (~326 MB) + free (~133 MB) account for only ~2.5 GB of 7.9 GB. The remainder belongs to other tenants/cells on the shared host whose processes are invisible from this container's PID namespace. This is the dominant cause of the high MEM%.

## 4. Python / Node.js processes

- Python: exactly one — the ATLAS daemon, pid 9711, RSS 10,816 KB.
- Node/Bun: exactly one — the platform bun worker, pid 11177, RSS 43,480 KB.
- No other python/node/bun processes exist. No miner, no trader, nothing else.

## 5. Daemon RSS — leak check

| Reading | RSS | When / pid | Source |
|---|---|---|---|
| ~13.2 MB | 23:32 EST | diagnostics run | prior report |
| ~14.1 MB | 00:47 EST | diagnostics run | prior report |
| 14.0 MB | 01:52 EST, pid 2193 | diagnostics test 13 | diagnostics.json |
| **10.6 MB** | 02:03 EST, pid 9711 | `/proc/9711/status` VmRSS | this investigation |

- VmPeak = VmSize = 19,804 KB for the current process; VmRSS 10,816 KB.
- **No leak trend.** RSS sits in a flat 10–14 MB band across four readings spanning ~2.5 h and multiple daemon lifetimes. The newest reading (10.6 MB) is the *lowest*.
- Caveat: the daemon was restarted 9 times in ~2.5 h (recover.log 04:31–06:52 UTC; 16 `startup` events in the events table), mostly by intentional diagnostics self-tests 10/11 (SIGTERM + recover.sh restart — e.g. the 01:52:48 EST restart to pid 9711). Frequent restarts reset RSS and shorten any single lifetime (current lifetime ~11 min at measurement), so a slow within-lifetime leak cannot be fully excluded from RSS alone — but four cross-lifetime readings show no upward drift, and the metrics table (host MEM% only) shows no correlation with daemon restarts.
- Scale check: the daemon is 0.13% of host RAM. Even 10× its size would move MEM% by ~1 point. **It cannot explain 76.67% vs 70%.**

## 6. Database memory usage

- File: `data/atlas.db`, **32,768 bytes** (8 pages × 4,096 B page size).
- `PRAGMA cache_size` = -2000 (2 MB default cache), `journal_mode` = delete, `freelist_count` = 0.
- The DB contributes nothing measurable to memory pressure. SQLite cache is capped at ~2 MB and the file is 32 KB.

## 7. Historical MEM% trend (metrics table, `data/atlas.db`)

- Rows: **156**, span 04:24:16–07:03:50 UTC = 23:24:16–02:03:50 EST (2 h 39 m), one row/minute.
- **Min 71.95%** (04:57:45 UTC), **max 93.64%** (04:32:41 UTC), **mean 83.95%**.
- **0 of 156 rows below 70%. 120 of 156 rows ≥ 80%. 21 of 156 rows ≥ 90%.**
- Hourly means: 04 UTC 84.19% (n=38), 05 UTC 82.64% (n=56), 06 UTC 84.96% (n=58), 07 UTC 85.33% (n=4). No hour averages below 70%.
- The 76.67% reading (06:52:49 UTC / 01:52 EST) was **near the low end** of the observed range, not a spike — the host was already at 75.69% the minute before and 79.14% the minute after.
- MEM% does **not** track ATLAS activity or load: hourly load1 means fell from 4.56 (04 UTC) to 2.34 (07 UTC) while MEM% stayed flat at ~83–85%. MEM% also does not dip after daemon restarts (9 restarts in the window, MEM% stayed 72–94% throughout).
- Conclusion: **the 70% cap was already breached before the earliest recorded metric.** This is a chronic host condition, not an ATLAS event.

## 8. Cause — stated with numbers

1. **Not ATLAS.** Daemon RSS 10.6 MB (0.13% of host RAM); DB 32 KB. ATLAS's total footprint is ~11 MB out of 7,934 MB.
2. **Not a leak.** Daemon RSS flat at 10–14 MB across 2.5 h and 4 readings; no process shows steady RSS growth (only one ATLAS process exists, and the platform processes are not ours to judge — hatch daemon 470 MB is the platform runtime itself).
3. **Shared-host pressure.** ~5.5 GB of host RAM is consumed by other tenants/cells invisible from this container, plus ~1.27 GB page cache and ~326 MB kernel slab. Host swap is in use (~400 MB), confirming real pressure.
4. **Metric scope mismatch.** The capped metric is host-wide (`/proc/meminfo`), so the 70% cap is unachievable by any ATLAS-side action while other tenants hold the memory.

## 9. Safest correction (PROPOSAL ONLY — not implemented)

Do **not** kill any process (the biggest consumer is platform infrastructure), do **not** raise the cap or edit `config/atlas.json` without user authorization, do **not** restart anything.

Recommended, in order:

1. **Re-scope the check (no host change, needs user approval):** treat the host MEM% breach as external/host-level, not an ATLAS failure. Change the monitored threshold to ATLAS's own footprint instead — e.g. alert if daemon RSS exceeds 50 MB (5× its observed 10–14 MB band) — which is something ATLAS can actually control. The host MEM% can stay visible on the dashboard as informational only.
2. **Record it:** log the 70% host-cap breach as caused by shared-host pressure, with this file as evidence, so later lanes do not chase it as an ATLAS defect.
3. **Only real fix for host MEM% (external, user decision):** more host RAM, a larger/dedicated cell, or the host operator reducing other tenants' load. Nothing on-host can lower it — ATLAS freeing its entire 11 MB would move MEM% by ~0.1 points.

## 10. Gemini advisory

Attempted twice via the Gemini API (`gemini-3.5-flash`, numbers-only prompt, no private data): both calls returned **HTTP 503 "model currently experiencing high demand"** — no advisory obtained, and no 429 occurred, so no Gemini stop applies. Every conclusion above was verified against my own measurements (ps, /proc/meminfo, /proc/9711/status, metrics-table queries, DB pragmas, logs), not against Gemini output.
