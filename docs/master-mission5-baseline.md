# ATLAS Master Mission 5 — Baseline (Lane B, read-only)

Checked 2026-11-18, 04:19–05:24 EST (09:19–10:24 UTC). All values measured this run, not carried forward.
No code, config, database, or artifact was edited. The diagnostics run restarts the daemon twice by design (tests 10/11).

## 1. Daemon
- **Exactly one real daemon.** Pre-diagnostics: pid **17976**, started Wed Nov 18 09:08:00 UTC, elapsed 11:27, RSS **9,568 KB**, VSZ 19,880 KB, `python3 core/atlas_monitor.py`, state running.
- Post-diagnostics (after the two by-design restarts): pid **5352**, elapsed 00:36, RSS **14,496 KB** (~14.2 MB, matches diagnostics test 13).
- Note: bare `pgrep atlas_monitor.py` (no `-f`) returns 0 — the pattern exceeds 15 chars. `pgrep -f` is required. Extra pids in `pgrep -f` output were my own shell commands containing the pattern string (self-match artifacts), not daemons.

## 2. Snapshot (`data/snapshot.json`)
- Pre-diagnostics (09:19:03 UTC): ts 1794993543, **age 3 s**. CPU **35.1%**, MEM **91.79%** used, load **[1.96, 2.21, 2.24]**, disk free **130,144,489,472 B (~130.2 GB)**, disk 19.05% used. mining: `disabled`, trading: `disabled-paper-only`, emergency_stop: `true`.
- Post-diagnostics (10:24:21 UTC): ts age **36.2 s** (within the 60 s write cycle), CPU **1.5%**, MEM **89.14%**, load **[0.75, 0.39, 0.41]**, disk free 130.2 GB, 19.02% used.
- **Flag (standing): host MEM% 89–92% is above the 70% cap.** The daemon itself uses only ~14 MB; the pressure is host-level, not daemon-level. Diagnostics test 16 records it as informational only.

## 3. Database (`data/atlas.db`)
- `PRAGMA integrity_check` → **ok** (checked twice, before and after diagnostics).
- `PRAGMA user_version` → **1**.
- Pre-diagnostics: **metrics 306, decisions 68, events 39**.
- Post-diagnostics: **metrics 373, decisions 76, events 44** — the increase is the diagnostics run itself (decide pass logged 4+ new decisions, restart/recovery logging). Expected side effect, not external activity.
- Stage 0 tables (all **0 rows** as expected): users 0, workers 0, shares 0, ledger 0, payouts 0, referrals 0, achievements 0, pool_stats 0, sessions 0.
- Tables present: achievements, decisions, events, ledger, metrics, payouts, pool_stats, referrals, sessions, shares, sqlite_sequence, users, workers.

## 4. Diagnostics
- `python3 core/diagnostics.py` run 2026-11-18 10:23:42 UTC → **22 PASS, 0 FAIL, 0 NOT TESTED (of 22)**. Exit 0. Results in `data/diagnostics.json`.
- Notable: test 14/18 confirm coingecko:200, moneroocean:200, blockchain.info:200; test 20 confirms exactly 1 daemon (pid 5352) after restarts; test 13/16 daemon RSS 14.2 MB, lifetime CPU 1.99%.

## 5. Safety (`config/atlas.json`, version `0.1.0-stage2`)
- `emergency_stop`: **true**
- `mining.enabled`: **false** (status `design-only`, reason: no authorization to mine on shared host infrastructure; no GPU; shared 1.5 CPU cell; cpu_candidate `monero-randomx`)
- `trading.mode`: **paper-only**, enabled false, futures/leverage/margin/options all false, `eligible_capital_usd`: **0**
- `limits`: max_cpu_pct **50**, max_mem_pct **70**, max_temp_c null ("Limits are immutable without user authorization")
- `monitor_interval_s`: 60; `host_role`: worker-1-bootstrap
- Recorded blockchain_apis labels in config: coingecko `verified-200`, moneroocean `verified-200`, blockchain_info `verified-200`, mempool_space `unreachable-from-this-host`

## 6. Endpoints (curl, 10 s timeout, measured this run)
| Endpoint | Result |
|---|---|
| CoinGecko `api/v3/ping` | **200**, 1.08 s, 34 B — `{"gecko_says":"(V3) To the Moon!"}` |
| MoneroOcean `/pool/stats` | **000 first attempt** (10.0 s timeout, 0 B), **200 on retry** — live JSON: hashRate 262,107,922 H/s, miners 4975, lastBlockFound 3808993. First 000 was transient; diagnostics test 14/18 independently got 200. |
| blockchain.info `/q/latesthash` | **200**, 1.08 s, 64 B — hash `00000000000000000001c84b951e83a3c6d27cdea414c066cd4c9001f477b918` (height 976412 per diagnostics test 18) |
| mempool.space `/api/blocks/tip/height` | **000** (10.0 s timeout, 0 B). Diagnostics test 18 independently: `TimeoutError: The read operation timed out` after retry (non-fatal). **DISPUTED — recorded as measured 000 this run, NOT asserted as settled either way.** (Reliability mission found it reachable 01:52 and 02:25 on 2026-11-18; it has returned 000 on recent checks including this one.) |

## 7. Miner / pool / key checks — all clean
- **No miner process running.** `pgrep -i xmrig|minerd|randomx|cpuminer|miner` and `ps aux` grep: no matches (only the searching shell itself).
- **No pool connection.** `ss -tnp` grep for pool ports (3333/4444/5555/7777/14444) and moneroocean/pool: none.
- **No key/seed files under `~/workspace/atlas/`.** `find` for `*seed*`, `*private*key*`, `*.pem`, `*.key`, `*mnemonic*`, `*wallet*`: zero files.
- Diagnostics test 15 independently confirms: no key material, no miner processes, config not world-writable, emergency stop ON, mining + trading disabled.

## Baseline verdict
Host is healthy and safe for Mission 5 build work: daemon alive (exactly one), snapshot fresh, DB intact with all 9 Stage 0 tables empty, diagnostics 22/22, safety gates all in the safe state, 3 of 4 endpoints 200 (MoneroOcean 200 after one transient 000), mempool.space 000 — disputed, not settled. No miner, no pool connection, no keys. Two standing flags carried forward, neither a stop condition: host MEM% 89–92% above the 70% cap, and mempool.space reachability unresolved.
