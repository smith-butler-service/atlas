# ATLAS Master Mission 4 — Lane B Baseline (Host + Safety)

**Lane:** B — Host Baseline + Safety (read-only verification; nothing changed, nothing fixed, artifact untouched)
**Date:** 2026-11-18, measured 03:32–03:34 EST (08:32–08:34 UTC)
**Baseline context given at task start (03:31 EST):** daemon pid 11074; snapshot ts 1794990691, CPU 33.66%, MEM 88.76%, disk 19.04% used / 130.2 GB free; DB integrity ok, user_version 1, metrics 252 / decisions 52 / events 31; emergency_stop true, mining disabled (design-only), trading paper-only, eligible capital $0, limits 50/70.

All values below are measured in this lane unless marked as carried-forward context.

## 1. Daemon

| Check | Result |
|---|---|
| Processes matching `atlas_monitor.py` | Exactly **1** |
| PID at first check (03:32:53 EST) | **11074** — `python3 core/atlas_monitor.py`, state S |
| Uptime at first check | **12 min 25 s** (etime 12:25; ~12:35 by the end of the safety checks) |
| RSS / VSZ (pid 11074) | 10,260 KB / 19,880 KB |
| PID after diagnostics (tests 10/11 restart by design) | **13049**, uptime 00:39, RSS 14,528 KB / VSZ 19,880 KB |
| Unexpected resources held | None observed |

**Observation (not an anomaly, no action taken):** pid 11074 had only ~12 min uptime at 03:32 EST, i.e. it started ~03:20 EST. The coordination lane reported a different pid stable since 02:52:59 EST, so a daemon restart occurred between ~02:53 and ~03:20 EST; the cause was not established by this lane and was not investigated (read-only scope, daemon was alive and healthy). Diagnostics tests 10/11 then restarted it again by design (pid 13049). No recovery action was needed; `~/workspace/atlas/core/recover.sh` was **not** invoked.

## 2. Snapshot (`~/workspace/atlas/data/snapshot.json`)

**First read (03:32:58 EST, epoch 1794990778):**

| Field | Value |
|---|---|
| `ts` | 1794990751 |
| Age at read | **27 s** |
| `cpu_pct` | 21.12% |
| `mem_used_pct` | 90.43% (mem_total 8,124,900 KB; mem_avail 777,872 KB) |
| `load` | [1.04, 1.25, 2.23] |
| `disk_used_pct` | 19.04% (disk_free 130,154,971,136 B ≈ 130.2 GB) |
| `net_rx_bytes` / `net_tx_bytes` | 11,538,240 / 2,025,980 |
| `gpu` | null (no GPU) |
| `mining` | `"disabled"` |
| `trading` | `"disabled-paper-only"` |
| `emergency_stop` | **true** |

**Second read (post-diagnostics, 03:33:53 EST, epoch 1794990833):** ts 1794990795, age **38 s**, CPU 45.50%, MEM 91.80%, load [1.33, 1.26, 2.19], disk 19.04%, same safety flags (mining disabled, trading disabled-paper-only, emergency_stop true).

**Host memory note:** host MEM 88.76% → 90.43% → 91.80% across the window — above the 70% ATLAS limit, but this is shared-host pressure, not ATLAS: the daemon itself uses ~10–14 MB RSS. The ATLAS limit applies to ATLAS's own consumption, which is far inside it.

## 3. Database (`~/workspace/atlas/data/atlas.db`)

| Check | Result |
|---|---|
| `PRAGMA integrity_check` | **ok** |
| `PRAGMA user_version` | **1** |
| File size | **167,936 bytes (164 KB)** |
| metrics rows (first check) | 253 (context said 252 at 03:31 — +1 row written by the live daemon between checks) |
| decisions rows (first check) | 52 |
| events rows (first check) | 31 |
| Latest metrics row ts | 1794990751 (= snapshot ts at first check) |
| After diagnostics | metrics **255**, decisions **56**, events **33**, latest ts 1794990795 — growth is the diagnostics run itself (test 07 logged 4 new decisions; test 19 confirmed events rows unchanged by its rolled-back write) |

**Mission 2 Stage 0 tables — all 0 rows, as expected (empty scaffold, no live data):**

| Table | Rows |
|---|---|
| users | 0 |
| workers | 0 |
| shares | 0 |
| ledger | 0 |
| payouts | 0 |
| referrals | 0 |
| achievements | 0 |
| pool_stats | 0 |
| sessions | 0 |

## 4. Safety

### Config — `~/workspace/atlas/config/atlas.json`
- `emergency_stop`: **true**
- `mining.enabled`: **false** — status `"design-only"`, reason: "No authorization to mine on shared host infrastructure; no GPU; shared 1.5 CPU cell"
- `mining.cpu_candidate`: `"monero-randomx"`
- `trading.mode`: `"paper-only"`, `trading.enabled`: **false**, futures/margin/leverage/options all false
- `trading.eligible_capital_usd`: **0**
- `limits`: `max_cpu_pct` **50**, `max_mem_pct` **70**, `max_temp_c` null — unchanged, with note "Limits are immutable without user authorization"
- `blockchain_apis`: coingecko `verified-200`, moneroocean `verified-200`, blockchain_info `verified-200`, mempool_space `"unreachable-from-this-host"`
- `monitor_interval_s`: 60; `version`: `0.1.0-stage2`; `host_role`: `worker-1-bootstrap`

### Config — `~/workspace/atlas/config/pool-rewards.json`
- `mode`: **`simulation-only`**
- Primary pool MoneroOcean, 0% fee, stats endpoint `/pool/stats`; fallback pools SupportXMR (0.6%) and P2Pool (0%)
- Reward split 75% users / 25% ATLAS, applies to actual confirmed pool rewards only
- `minimum_payout`: placeholder, not set — to be decided and authorized before any payout flow
- Safety: activation gate (no real payouts, no real pool connection, no mining until explicitly authorized after simulation/testnet success and security testing); emergency stop honoured; "no wallet credentials, seed phrases, private keys, or wallet passwords are stored anywhere in this config or in ATLAS"

### Miner-process check
- Exact-name `pgrep -x` for `xmrig`, `minerd`, `cpuminer`, `xmrig-amd`, `xmrig-nvidia`: **none running**
- `ps aux` scan for miner/xmrig: no miner process. One incidental hit: `/opt/hatch/bin/browser-service` fetching a voltminer.net blog article ("randomx-in-a-browser-the-rounding-mode-bug") — a research URL fetch by another agent's browser task, **not** a miner process.

### Key / seed file check
- `find ~/workspace/atlas` for `*.pem`, `*.key`, `id_rsa*`, `*seed*`: **no files found**

**Safety verdict: PASS.** Emergency stop on, mining disabled (design-only), trading paper-only with $0 eligible capital, limits 50/70 unchanged, pool-rewards simulation-only, no miner running, no wallet/key/seed material anywhere under `~/workspace/atlas`.

## 5. Diagnostics

Single run of `python3 ~/workspace/atlas/core/diagnostics.py` (03:33:11 UTC), exit 0:

**22 PASS, 0 FAIL, 0 NOT TESTED (of 22).**

Notable test lines:
- Test 03: CPU 21.12%, MEM 90.43%, snapshot 40 s old
- Test 06: 253 metrics rows, span 14,895 s
- Test 09: stop ON in config + snapshot; mining + trading disabled; hold decision logged (14x)
- Test 10: daemon pid 11074 stopped on SIGTERM and restarted; fresh snapshot written
- Test 11: recover.sh restarted the daemon after a kill; fresh snapshot written
- Test 13: daemon RSS 14.2 MB, lifetime CPU 2.49%
- Test 14: coingecko:200, moneroocean:200, blockchain.info:200
- Test 15: no key material, no miner processes, config not world-writable, emergency stop ON
- Test 16: host MEM 91.8% (informational only)
- Test 18: mempool.space HTTP None (TimeoutError after retry, non-fatal); MoneroOcean hashRate 263,597,969 H/s, miners 4,961, lastBlockFound 3,808,943; blockchain.info height 976,405
- Test 20: exactly 1 daemon (pid 13049, alive) after the test restarts
- Test 22: latest metrics gap 2 s, newest row 32 s old

Tests 10/11 restart the daemon twice by design — that churn is expected, not a failure. Diagnostics was run **once**; not looped. Results file: `~/workspace/atlas/data/diagnostics.json`.

## 6. Endpoints (curl, 10 s timeout, measured by this lane)

| Endpoint | HTTP code | Time |
|---|---|---|
| CoinGecko `https://api.coingecko.com/api/v3/ping` | **200** | 0.42 s |
| MoneroOcean `https://api.moneroocean.stream/pool/stats` (NOT `/api/stats`, which 404s) | **200** | 1.32 s |
| blockchain.info `https://blockchain.info/q/getblockcount` | **200** | 0.69 s |
| mempool.space `https://mempool.space/api/blocks/tip/height` | **000** (timeout) | 10.00 s |
| mempool.space — retry | **000** (timeout) | 10.00 s |

**mempool.space — DISPUTED, not settled:** this lane measured 000 (connection timeout) on both attempts, and diagnostics test 18 also timed out on it after a retry. That is consistent with the coordination lane's 000 twice at ~03:07, but contradicts the reliability mission's reachable readings at 01:52 and 02:25 EST. The `atlas.json` config currently records it as `"unreachable-from-this-host"`. This lane asserts nothing either way — the measured result here is: **unreachable from this host at 03:34 EST (two timeouts + one diagnostics timeout)**. A later re-probe could still find it reachable; the dispute stands.

## 7. Known issue carried forward (NOT fixed, NOT attempted)

**Refresh failure (Mission 3 finding 1):** the dashboard snapshot goes stale and refresh fails at the platform spawn step; the 07:58 "Refresh complete" message was misleading (it re-ingested the stored 07:53 snapshot). The fix needs a separate repair authorization. This lane recorded it as a carried-forward known issue, attempted no repair, and invoked no refresh action. Note: the daemon's own 60 s monitor cycle continues to write fresh snapshots (27 s and 38 s old at this lane's reads), so the snapshot file itself is fresh — the failure is in the dashboard refresh/spawn path, not in snapshot generation.

## Summary

Baseline healthy: exactly one daemon (pid 11074 at first check, 13049 after the by-design diagnostics restarts), fresh snapshots (27–38 s old), DB integrity ok with Stage 0 tables all at 0 rows, diagnostics 22/22 PASS, CoinGecko / MoneroOcean / blockchain.info all 200, safety fully on (emergency stop true, mining disabled design-only, trading paper-only, $0 capital, limits 50/70, pool-rewards simulation-only, no miner, no keys/seeds). Anomalies/notes: host MEM 90–92% (shared-host pressure, daemon itself ~14 MB); mempool.space unreachable in this window (000 ×2 + diagnostics timeout) — still disputed, not settled; daemon pid 11074 had only ~12 min uptime at first check, indicating a restart between ~02:53 and ~03:20 EST of undetermined cause, with the daemon healthy thereafter.
