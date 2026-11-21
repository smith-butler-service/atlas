# ATLAS — Master Mission 3: Monero Wallet Center — Baseline (Lane C, host baseline)

**Date:** Wednesday, 2026-11-18 — measured 07:51–07:52 UTC (02:51–02:52 EST)
**Lane:** C (host baseline), READ-ONLY. Nothing was changed: no daemon restarts by this lane, no config edits, no database writes, no artifact edits.
**Purpose:** measured baseline so the Mission 3 implementation and verification lanes can prove nothing regressed.
**Note on method:** the diagnostics suite itself (tests 10/11) restarts the daemon by design. Daemon pid therefore changed during this baseline run (2939 → 4754); both pids are recorded below with the cause. All other values were re-measured after the diagnostics run so the baseline reflects the post-diagnostics state.

## 1. Daemon — exactly one instance

| Check | Value |
|---|---|
| pgrep (bracket form `atlas_[m]onitor.py`) at 07:51:34 UTC | 1 match: `2939 python3 core/atlas_monitor.py` |
| pid 2939 started | Wed Nov 18 07:43:40 2026 (UTC) |
| pid 2939 uptime at check | 07:53 (7 min 53 s) |
| After diagnostics run (tests 10/11 restart the daemon by design) | 1 match: `4754 python3 core/atlas_monitor.py` |
| pid 4754 started | Wed Nov 18 07:51:39 2026 (UTC) |
| pid 4754 uptime at 07:52:22 UTC re-check | 00:42 (42 s) |
| Daemon count at every check | exactly 1 — no duplicates, no missing daemon |

Monitor log tail confirms the restart was clean:
`2026-11-18T07:51:39Z monitor START pid=4754 db=.../atlas.db emergency_stop=True mining=disabled trading=paper-only`
`2026-11-18T07:51:41Z cycle ts=1794988300 cpu=54.26 mem=87.50 db=ok stop=True`

## 2. Snapshot freshness — `~/workspace/atlas/data/snapshot.json`

| Check | Value |
|---|---|
| Snapshot ts at 07:51:51 UTC | 1794988300 (2026-11-18T07:51:40 UTC) |
| Age at that read | 11 s |
| Snapshot ts at 07:52:22 UTC re-check | 1794988300 (unchanged — mid-cycle; next 60 s write due ~07:52:40) |
| Age at re-check | 42 s (within the 60 s cycle and the 180 s freshness threshold) |
| Snapshot contents (latest) | cpu_pct 54.26, mem_used_pct 87.50, load [4.35, 3.79, 2.71], disk_used_pct 19.02, net_rx 6,501,496 B / net_tx 804,653 B, gpu null, mining `disabled`, trading `disabled-paper-only`, emergency_stop true |

## 3. Database — `~/workspace/atlas/data/atlas.db`

| Check | Value |
|---|---|
| `PRAGMA integrity_check` | ok |
| `PRAGMA user_version` | 1 (Mission 2 schema) |
| `PRAGMA journal_mode` | delete |
| `PRAGMA page_count` / `page_size` / `freelist_count` | 40 pages / 4096 B / 0 free |
| File size | 163,840 B (see observation below) |
| Indexes | 18 total (16 from the Mission 2 migration + pre-existing) |
| Tables present | achievements, decisions, events, ledger, metrics, payouts, pool_stats, referrals, sessions, shares, sqlite_sequence, users, workers — all 13 expected tables present |

Row counts (measured after the diagnostics run):

| Table | Rows | Expected |
|---|---|---|
| users | 0 | 0 ✓ |
| workers | 0 | 0 ✓ |
| shares | 0 | 0 ✓ |
| ledger | 0 | 0 ✓ |
| payouts | 0 | 0 ✓ |
| referrals | 0 | 0 ✓ |
| achievements | 0 | 0 ✓ |
| pool_stats | 0 | 0 ✓ |
| sessions | 0 | 0 ✓ |
| metrics | 209 | growing ~1/min ✓ (was 207 pre-diagnostics) |
| decisions | 44 | growing ✓ (was 40 pre-diagnostics; +4 logged by diagnostics test 07, by design) |
| events | 27 | growing ✓ (was 25 pre-diagnostics; +2 daemon startup events from the diagnostics restart tests) |

All 9 Mission 2 tables are present and empty. No demo users, workers, shares, earnings, or payouts seeded.

**Observation (not a failure):** the live DB file is 163,840 B while the pre-Mission 2 backup (`backups/atlas-2026-11-18-pre-mission2.db`, 07:35) is 36,864 B. Page count is 40 with 0 freelist pages, so the growth is allocated pages, not free space. Row growth since Mission 1 is small (metrics 177 → 209, decisions 28 → 44, events 16 → 27). Cause not established by this read-only lane; recorded so the verification lane can compare after Mission 3.

## 4. Safety config — unchanged, all holds in place

### `~/workspace/atlas/config/atlas.json` (version `0.1.0-stage2`)

| Setting | Value |
|---|---|
| emergency_stop | true |
| mining.enabled | false |
| mining.status | design-only |
| mining.cpu_candidate | monero-randomx |
| mining.reason | No authorization to mine on shared host infrastructure; no GPU; shared 1.5 CPU cell |
| trading.enabled | false |
| trading.mode | paper-only |
| trading.eligible_capital_usd | 0 |
| trading.futures / leverage / margin / options | all false |
| trading.reason | No realized net mining profits exist; funding rule (Part 8) forbids any other source |
| limits.max_cpu_pct | 50 |
| limits.max_mem_pct | 70 |
| limits.max_temp_c | null |
| monitor_interval_s | 60 |
| host_role | worker-1-bootstrap |
| blockchain_apis | blockchain_info verified-200, coingecko verified-200, mempool_space unreachable-from-this-host, moneroocean verified-200 |

### `~/workspace/atlas/config/pool-rewards.json` (version `0.1.0-stage0-mission2`)

- **mode: `simulation-only`** ✓ — confirmed.
- Primary pool MoneroOcean (api.moneroocean.stream, `/pool/stats`, 0% fee); fallbacks SupportXMR (0.6%) and P2Pool (0%).
- Reward split 75% users / 25% ATLAS, applied only to actual confirmed pool rewards; referral rewards funded from the ATLAS 25% only.
- Minimum payout: placeholder, null, not set.
- Ledger rules: append-only, reversing-entry corrections only, batch dedupe, payout idempotency keys.
- Safety gate: no real payouts, no real pool connection, no mining until explicitly authorized after simulation/testnet success and security testing; emergency stop honoured.
- No credentials, secrets, wallet addresses, seed phrases, or private keys anywhere in either config file.

Neither config file was edited by this lane.

## 5. Diagnostics — 22/22 PASS

Run: `python3 ~/workspace/atlas/core/diagnostics.py`, started 2026-11-18 07:51:34 UTC, finished ~07:52:12 UTC (38 s), exit 0.
**Summary: 22 PASS, 0 FAIL, 0 NOT TESTED (of 22).** Results written to `data/diagnostics.json` (`pass: 22, fail: 0, not_tested: 0`).

| Test | Result | Evidence |
|---|---|---|
| 01 Python services | PASS | Python 3.12.3; atlas_monitor + atlas_core compile and import |
| 02 Monitoring daemon | PASS | running pid 2939, state S |
| 03 CPU and memory monitoring | PASS | CPU 26.46%, MEM 85.18% used, snapshot 51 s old |
| 04 Disk and network monitoring | PASS | disk 19.02% used, net rx 6,499,126 B / tx 802,186 B |
| 05 SQLite database integrity | PASS | integrity_check ok; all 13 tables listed |
| 06 Database persistence | PASS | 207 metrics rows, span 12,387 s |
| 07 Coordinator decision-making | PASS | decide pass logged 4 new decisions |
| 08 Decision logging | PASS | 5 recent decisions, all with reasons; latest: no-throttle-needed |
| 09 Emergency stop | PASS | stop ON in config + snapshot; mining + trading disabled; hold decision logged (11x) |
| 10 Service restart | PASS | daemon pid 2939 stopped on SIGTERM and restarted; fresh snapshot written |
| 11 Automatic recovery | PASS | recover.sh restarted the daemon after a kill; fresh snapshot written |
| 12 Deployment persistence | PASS | all essential files under ~/workspace/atlas; recovery procedure + script present |
| 13 Resource consumption | PASS | daemon RSS 14.1 MB, lifetime CPU 2.48% |
| 14 Network connectivity | PASS | coingecko:200, moneroocean:200, blockchain.info:200 |
| 15 Security and permission controls | PASS | no key material, no miner processes, config not world-writable, stop ON, mining + trading disabled |
| 16 Memory pressure | PASS | daemon RSS 14.1 MB (< 50 MB), DB 160.0 KB (< 100 MB), host MEM 87.5% (informational only) |
| 17 Snapshot freshness | PASS | snapshot ts age 4 s (< 180 s) |
| 18 API data validity | PASS | CoinGecko 200; MoneroOcean 200 (262,903,162 H/s, 4,954 miners, last block 3,808,918); blockchain.info 200 (height 976,401); mempool.space timeout (non-fatal by design) |
| 19 Database write latency | PASS | rolled-back test write 0.6 ms (< 1000 ms), events rows unchanged at 27 |
| 20 Daemon health | PASS | exactly 1 daemon (pid 4754, alive); monitor.log last line 28 s old |
| 21 CPU pressure | PASS | daemon CPU 0.0% over 3 s window (< 25%), host load 5.35/4.10/2.85 (informational only) |
| 22 Queue delays | PASS | latest metrics gap 2 s (expected ~60 s), newest row 32 s old |

## 6. Context read (Mission 1 + Mission 2 reports)

- **Mission 2 report** (`docs/master-mission2-report-2026-11-18.md`): Stage 0 + Mining tab complete 02:33–02:48 EST. 9 tables, user_version 0 → 1, backup `atlas-2026-11-18-pre-mission2.db` (36,864 B). Mining tab: 12 sections + 75/25 panel, Start/Stop hard-disabled with no handler, wallet address-only scaffold (full onboarding center = Mission 3), earnings all 0 XMR, calculator labelled ESTIMATE. Diagnostics 22/22 at mission end.
- **Mission 1 report** (`docs/master-mission1-inspection-report-2026-11-18.md`): browser RandomX mining verdict IMPRACTICAL as an earner; desktop XMRig only path near breakeven; host memory already over its 70% cap at that time.
- **Carried-forward verification gap (Mission 2 §5, still open):** no captured browser run ever opened the Mining tab — rendered layout on desktop/mobile, disabled-button behaviour under a real click, and wallet/calculator/settings interactions were never exercised in a browser. Source + data verification is strong; rendered verification is NOT established. Mission 3 verification should cover the wallet sections in a real browser run if one is available.

## 7. Findings — everything as expected except the pre-existing items below

**No regressions found.** Every measured value matches the Mission 2 end state (daemon single instance, snapshot fresh, DB integrity ok, user_version 1, all 9 Mission 2 tables 0 rows, safety holds intact, diagnostics 22/22, pool-rewards simulation-only).

Pre-existing conditions (already flagged in Mission 1/2, unchanged, not caused by Mission 2):

1. **Host memory 85–87.5% used, above the 70% `max_mem_pct` config cap.** Latest snapshot: 87.50%. Diagnostics test 16 records it as informational only. Mission 1 already flagged this (79.47% at 02:25 EST); it has risen since.
2. **Host CPU in the latest snapshot 54.26%, above the 50% `max_cpu_pct` cap** (earlier snapshot in this run: 26.46%). The coordinator logs throttle/hold decisions for this; diagnostics test 09 confirms the hold decision is logged.
3. **Daemon pid changed during this baseline (2939 → 4754)** — caused by the diagnostics suite's own restart tests (10/11), by design, not by any failure. Single instance maintained throughout.
4. **DB file growth 36,864 B (pre-Mission 2 backup) → 163,840 B live** — recorded as an observation in §3; cause not established by this read-only lane.
5. **Mission 2 rendered-verification gap still open** — no browser run has opened the Mining tab (see §6).

## 8. Baseline summary (headline numbers)

- Daemon: exactly 1 instance; pid 4754 at end of run (started 07:51:39 UTC after the diagnostics restart tests; pre-diagnostics pid 2939, started 07:43:40 UTC, uptime 7m53s).
- Snapshot age: 11 s at first read (ts 1794988300); 42 s at post-diagnostics re-check (mid-cycle, within limits).
- DB integrity: ok; user_version 1; all 9 Mission 2 tables 0 rows; metrics 209, decisions 44, events 27.
- Safety: emergency_stop true; mining disabled (design-only); trading paper-only; eligible capital $0; limits 50/70 unchanged; pool-rewards mode simulation-only.
- Diagnostics: **22/22 PASS, 0 FAIL, 0 NOT TESTED**, exit 0.
