# ATLAS Master Mission 10 — Baseline (Lane B, read-only)

- **Lane:** B (baseline) — read-only verification; nothing edited, no code written, no config/DB change, no daemon restart initiated by this lane (the authorised diagnostics run restarts the daemon by design, tests 10/11).
- **Baseline window:** 2026-11-19 03:02:42–03:04:46 UTC (2026-11-18 22:02:42–22:04:46 EST).
- **Workspace:** `~/workspace/atlas/` (core/, data/, logs/, docs/, config/, backups/).
- **Overall verdict: PASS (baseline usable) — NOT all-green.** Safety-critical items are all green (daemon exactly 1 at every check, DB integrity ok, `user_version` 3, emergency stop ON, mining/trading disabled, no miners, no key material, ledger 0, rewards simulation-only, both configs byte-identical to the Mission 7/8/9 baselines, diagnostics 26/26 PASS first run with no 14/18 flapping this window, endpoints 4/4 200 on first attempt). The NOT-all-green items are carried, not new: host memory 84–91% vs the 70% cap; the refresh-button failure re-observed ~5 min before the window (02:57:38Z); the mempool.space config claim (`unreachable-from-this-host`) still contradicting live 200s; the M9 live mirror mismatch not verifiable by this lane (no artifact tools); daemon churn 128 restarts in 24 h / all-time; the uptime-vs-metrics boot contradiction carried from M9.

## 1. Daemon

| Check | Time (UTC) | Measured value |
|---|---|---|
| Daemon at baseline start | 03:02:42 | exactly **1 pid: 20881** (PPID 1, etime 09:43, state S, %CPU 0.0, %MEM 0.1, **RSS 10,156 KB**, VSZ 19,904 KB, `python3 core/atlas_monitor.py`) |
| Daemon during my diagnostics run | 03:03:46–03:04:10 | Restarted by design (tests 10/11): 20881 → **23465** (`logs/recover.log`: `03:03:51 recover: restarted atlas_monitor pid 23465`; `logs/monitor.log`: `03:03:51 monitor START pid=23465 ... emergency_stop=True mining=disabled trading=paper-only`). Expected churn, not a failure. |
| Daemon at baseline close | 03:04:46 | exactly **1 pid: 23465**, alive; snapshot age 54 s (see §2). I did not restart the daemon at any point except via the authorised diagnostics run. |

- Note on `pgrep` counts: a bare `pgrep -c -f 'atlas_[m]onitor.py'` returned 2 once at window start because the counting shell command itself matched; `ps` and `pgrep -a -f 'python3 core/atlas_monitor.py'` (which excludes the shell wrapper) confirmed exactly 1 daemon pid at every check. Do not read the bare count as a second daemon.
- Pre-window restarts (from `logs/recover.log` + `logs/refresh-attempts.log`, all explained, none mine): 02:49:09 pid 19944; 02:53:04 pid 20881 (Lane E diagnostics tests 10/11); watchdog PASS lines for pid 9757 through 02:37:43, pid 19362 at 02:47:37, pid 19944 at 02:52:44. Startup events in the DB corroborate: ids 124 (02:32:23), 125/126 (02:49:07/09), 127/128 (02:53:02/04), 129/130 (03:03:51/52, my run). All kind `startup`, message `atlas_monitor started`.
- `data/admin.json` reports `daemon_restarts_24h: 128`, `daemon_restarts_all_time: 128` (exported 02:54:15 UTC; M8 reported 104, M9's Lane E run saw the count still climbing through diagnostics restarts).

## 2. Snapshot (`data/snapshot.json`)

Start read, 03:02:42 UTC (file mtime 03:02:06 UTC, 385 bytes):

```json
{"ts": 1795057326, "cpu_pct": 46.23, "mem_total_kb": 8124900, "mem_avail_kb": 1162356, "mem_used_pct": 85.69, "load": [2.77, 2.53, 3.0], "disk_total": 161043427328, "disk_used": 30812438528, "disk_free": 130009776128, "disk_used_pct": 19.13, "net_rx_bytes": 11155742, "net_tx_bytes": 2998826, "gpu": null, "mining": "disabled", "trading": "disabled-paper-only", "emergency_stop": true}
```

- `ts` 1795057326 = 03:02:06 UTC, **age 42 s** at read. CPU 46.23%, **MEM 85.69% used (above the 70% cap)**, load 2.77/2.53/3.0, disk 19.13% used.
- `mining: "disabled"`, `trading: "disabled-paper-only"`, `emergency_stop: true`, `gpu: null`.
- Mid-window read, ~03:03:06 UTC: `ts` 1795057386, **age 17 s**, CPU 57.38%, **MEM 84.38%**, load [2.83, 2.61, 3.0]. Post-diagnostics read, ~03:04:15 UTC: `ts` 1795057432, **age 25 s**, CPU 38.40%, **MEM 90.82%**. Close read, 03:04:46 UTC: same `ts` 1795057432, **age 54 s** — the next 60 s cycle had not yet written; still well under the 180 s freshness threshold.
- Monitor log cycles every ~60 s, all `db=ok stop=True` (e.g. `03:01:06Z cycle ts=1795057266 cpu=35.06 mem=87.71 db=ok stop=True`; `03:03:52Z cycle ts=1795057432 cpu=38.40 mem=90.82 db=ok stop=True`). MEM across the window's cycles: **84.38%–90.82%**.
- Host `free -m` at 03:04 UTC: total 7934 MB, used 7098, free 194, avail 835; swap 1023 MB, 428 used. `uptime`: **1:38** (boot ~01:26 UTC — see §9 anomaly 4).

## 3. DB (`data/atlas.db`, read-only `mode=ro`)

| Check | Pre-diagnostics (~03:03) | Post-diagnostics (~03:04:15) |
|---|---|---|
| `PRAGMA integrity_check` | `ok` | `ok` |
| `PRAGMA user_version` | **3** | **3** |
| Size | 364,544 B | 364,544 B (unchanged — no page growth across the window) |
| users | 0 | 0 |
| workers | 0 | 0 |
| shares | 0 | 0 |
| sessions | 0 | 0 |
| pool_stats | 59 | 59 |
| decisions | 390 | **394** |
| events | 128 | **130** |
| metrics | 1399 | **1402** |
| ledger | 0 | 0 |
| reward_batches | 0 | 0 |
| reward_batch_shares | 0 | 0 |
| payouts | 0 | 0 |
| referrals | 0 | 0 |
| achievements | 0 | 0 |
| mining_dashboard_host_totals | — (no such table in the host DB; see note) | — |

- All 15 host tables present, plus `sqlite_sequence`. **There is no `mining_dashboard_host_totals` table in the host DB** — it is an artifact mirror table only (the M9 report's mirror row counts live in the artifact, not here). The task's table list is therefore satisfied for the host by the 15 tables above; do not treat the absence as a missing-table defect.
- No real mining activity anywhere: users, workers, shares, ledger, payouts, referrals, achievements, sessions all 0.
- **Deltas are my diagnostics run only:** +4 decisions (test 07's decide-pass quartet), +2 events (tests 10/11 startup pair), +3 metrics (daemon cycles during the 24 s run). No other writer was active in the window.
- Latest decision at window start, id 390: `coordinator, coordinator-pass-complete, ts 1795057255, "coordinator pass complete: pool poll skipped (not due); 0 expired session(s) closed; 0 activation(s) checked, 0 activated; 0 worker(s), 0 pool share(s) accepted, 0 local-test share(s) accepted"`. Latest at close, id 394: `scheduler, throttle-background-work` (ts 1795057428). Decision 389: `scheduler, no-throttle-needed, "CPU 48.03% within cap"`. Decisions 386–388 are the standard hold quartet (`hold-all-live-activity`, `stay-disabled`, `stay-paper-only`).
- Latest `pool_stats` row 59: `MoneroOcean, recorded_at 1795056659 (= 02:50:59 UTC), hashrate 271,204,233 H/s, miners 4904, block_height 3809429, network_hashrate null, block_reward_piconero 600,000,000,000, pool_fee_bps 0`. Row 58: 1795056053, 282,034,550 H/s, 4914 miners, same height.
- Latest metrics row (03:03:06): `(1795057386, 57.38, 84.38, 2.83, 2.61, 3.0, 19.13, 11167163, 3048124)`.

## 4. Diagnostics — MY RUN 26/26 PASS (26-test suite); on-disk file is my run

- **My run:** `python3 core/diagnostics.py`, 03:03:46–03:04:10 UTC (**23.7 s**), output preserved verbatim in `/tmp/m10-diag-run1.txt`. **Summary: `26 PASS, 0 FAIL, 0 NOT TESTED (of 26)`.** Run exactly once, as instructed; test 10 PASSED, so no re-run.
- **Pre-baseline file** (`data/diagnostics.json` at baseline start, ts 1795056804 = 02:53:24 UTC, 5,398 bytes): **26/26 PASS** — Lane E's run (host_run_2026-11-19T02:53:01Z).
- **On-disk file at baseline close** (ts 1795057450 = 03:04:10 UTC, 5,404 bytes): **26/26 PASS** — my run, which overwrote it, as designed.

| Test | Result | Detail (verbatim, my run) |
|---|---|---|
| 01 Python services | PASS | Python 3.12.3; atlas_monitor + atlas_core compile and import |
| 02 Monitoring daemon | PASS | running pid 20881, state S |
| 03 CPU and memory monitoring | PASS | CPU 57.38%, MEM 84.38% used, snapshot 41s old |
| 04 Disk and network monitoring | PASS | disk 19.13% used, net rx 11167163 B / tx 3048124 B |
| 05 SQLite database integrity | PASS | integrity_check ok; tables [achievements, decisions, events, ledger, metrics, payouts, pool_stats, referrals, reward_batch_shares, reward_batches, sessions, shares, sqlite_sequence, users, workers] |
| 06 Database persistence | PASS | 1400 metrics rows, span 81530s, DB at /home/hatch/workspace/atlas/data/atlas.db |
| 07 Coordinator decision-making | PASS | decide pass logged 4 new decisions |
| 08 Decision logging | PASS | 5 recent decisions, all with reasons; latest: throttle-background-work |
| 09 Emergency stop | PASS | stop ON in config + snapshot; mining + trading disabled; hold decision logged (58x) |
| 10 Service restart | PASS | daemon pid 20881 stopped on SIGTERM and restarted; fresh snapshot written |
| 11 Automatic recovery | PASS | recover.sh restarted the daemon after a kill; fresh snapshot written |
| 12 Deployment persistence | PASS | all essential files under ~/workspace/atlas; recovery procedure + script present; processes do not survive VM replacement by platform design — restore is via recover.sh (see docs/recovery.md) |
| 13 Resource consumption | PASS | daemon RSS 14.1 MB, lifetime CPU 2.48% |
| **14 Network connectivity** | **PASS** | `coingecko:200, moneroocean:200, blockchain.info:200` |
| 15 Security and permission controls | PASS | no key material, no miner processes, config not world-writable, emergency stop ON, mining + trading disabled |
| 16 Memory pressure | PASS | daemon RSS 14.1 MB (< 50 MB), DB 356.0 KB (< 100 MB), host MEM 90.82% (informational only) |
| 17 Snapshot freshness | PASS | data/snapshot.json ts age 5s (< 180 s) |
| **18 API data validity** | **PASS** | `coingecko: HTTP 200, gecko_says='(V3) To the Moon!' \| moneroocean: HTTP 200, hashRate=277630606 H/s, miners=4906, lastBlockFound=3809429 \| blockchain.info: HTTP 200, height=976518 \| mempool.space: HTTP 200, height=976518` |
| 19 Database write latency | PASS | rolled-back test write 0.4 ms (< 1000 ms), events rows unchanged at 130 |
| 20 Daemon health | PASS | exactly 1 daemon (pid 23465, alive); monitor.log last line 8s old: 2026-11-19T03:03:52Z cycle ts=1795057432 cpu=38.40 mem=90.82 db=ok stop=True |
| 21 CPU pressure | PASS | daemon CPU 0.0% over 3 s window (< 25%), host load 1.88/2.37/2.89 (informational only) |
| 22 Queue delays | PASS | latest metrics gap 2s (expected ~60 s), newest row 11s old |
| 23 Reward ledger hash chain | PASS | verify_chain: PASS; 0 entries, 0 settled batch(es), 0 correction(s); ledger empty — chain trivially valid, 0 entries |
| 24 Dashboard export | PASS | dashboard.json fresh (0s old), hashrate not-measured, estimate null; host-verified totals match live DB: 0 ledger entries, 0 settled batch(es), 0 user / 0 ATLAS piconero |
| 25 Admin export | PASS | admin.json fresh (1s old), hashrate not-measured, estimate null; earnings block == dashboard earnings; host-verified totals match live DB: 0 ledger entries, 0 settled batch(es); security counts match live SQL: 0 suspicious, 0 invalid, 0 duplicate, 0 abuse, 0 auth failures, 0 payout anomalies; no token_hash/token_salt/wallet field in file |
| 26 Profitability export | PASS | profitability.json fresh (6s old), 81 figures re-derived from recorded inputs within rounding; XMR net XMR/day (Tier 2) 2.7e-05, breakeven 56.1 H/W; your-hardware null + verbatim reason; earnings block == dashboard earnings; no USD in panel; stale=False |

- **Tests 14/18 did NOT flap this run** — the first clean first-run pass since the M7/M8 flapping signature appeared. No retry curls were needed for the diagnostics verdict (independent curls in §6 also all-200 first attempt). This does not settle the endpoints as reliable; it is one clean observation after three flapping baselines.
- Test 22 note: latest metrics gap 2 s vs the expected ~60 s — daemon restarts write extra metrics rows close together (tests 10/11 restarts at 03:03:51/52). Informational; the test still passes on its newest-row-age rule.

## 5. Configs / safety — UNCHANGED

`config/atlas.json` — mtime **2026-11-18 04:32:36 UTC**, 808 bytes, sha256 `46d3d12c1b907c048f2876755ce0d22a01316899d894561c6f86da67bfacab26` (**identical to the M7/M8/M9 baseline hash**):

- `emergency_stop`: **true**
- `mining.enabled`: **false** — status `design-only`, reason "No authorization to mine on shared host infrastructure; no GPU; shared 1.5 CPU cell"; `cpu_candidate: "monero-randomx"`
- `trading.mode`: **paper-only**; `trading.enabled`: false; `eligible_capital_usd`: **0**; futures/leverage/margin/options all false; reason "No realized net mining profits exist; funding rule (Part 8) forbids any other source"
- `monitor_interval_s`: 60; `host_role`: `worker-1-bootstrap`; `version`: `0.1.0-stage2`; limits max_cpu_pct 50 / max_mem_pct 70; blockchain_apis: coingecko `verified-200`, moneroocean `verified-200`, blockchain_info `verified-200`, mempool_space `unreachable-from-this-host`.

`config/pool-rewards.json` — mtime **2026-11-18 07:35:40 UTC**, 2,788 bytes, sha256 `b01a22ad5d703765a84b3fd7daa1b3b624bdfc3b4b9ea0238d1da3e95ad13464` (**identical to the M7/M8/M9 baseline hash**):

- `mode`: **simulation-only**; primary pool MoneroOcean, 0% fee, `api_base https://api.moneroocean.stream`, stats endpoint `/pool/stats`
- `reward_split`: **75% users / 25% ATLAS**; referral funding from the ATLAS 25% only; integer piconero rounding
- `minimum_payout`: **unset — placeholder, not set** (`piconero: null`, `xmr: null`); "to be decided and authorized before any payout flow is activated"
- Safety: activation gate (no real payouts / pool connection / mining until explicitly authorized after simulation/testnet success and security testing); emergency stop honoured; "no wallet credentials, seed phrases, private keys, or wallet passwords are stored anywhere in this config or in ATLAS"
- Fallbacks: SupportXMR 0.6% fee, P2Pool 0% fee.

Both mtimes predate the Mission 7 baseline and every value matches the Mission 7/8/9 baseline records verbatim — **UNCHANGED**. Not edited by this lane.

Safety (measured 03:02–03:04):

- **Miner processes: NONE.** `ps aux | grep -iE 'xmrig|randomx|miner|cpuminer|ethminer'` returned nothing (exit 1).
- **Pool-port connections: NONE.** `ss -tn` showed an empty connection table (header only); no connections on 3333/4444/5555/7777/14444/10128/3334.
- **Key/seed/password files: NONE in the workspace.** `find` for `*seed*`, `*private*key*`, `*.pem`, `*.key`, `*password*`, `*secret*`, `*mnemonic*`, `*wallet*` returned no files. A content-pattern grep for `private_key|seed phrase|mnemonic|BEGIN ... PRIVATE KEY` matched only prose in `docs/*.md` reports and the `pool-rewards.json` sentence quoted above stating no secrets are stored — no secret content was opened or read, and no key material exists. Config files are `-rw-rw----` (not world-writable).

## 6. Endpoints (curl, 20 s timeout, 03:03:41 UTC — first attempt, no retry needed)

| Endpoint | Result | Latency |
|---|---|---|
| `https://api.coingecko.com/api/v3/ping` | **200**, body `{"gecko_says":"(V3) To the Moon!"}` (34 B) | 0.80 s |
| `https://api.moneroocean.stream/pool/stats` | **200** (12,246 B) | 4.50 s |
| `https://blockchain.info/q/latesthash` | **200** (64 B) | 1.59 s |
| `https://mempool.space/api/v1/fees/recommended` | **200** (74 B) | 0.91 s |

- **4/4 reachable on the first attempt.** No retry was needed, so no retry evidence exists this window. MoneroOcean was slow (4.50 s vs 1.29 s in M8) but answered 200; it is the endpoint closest to the diagnostics timeouts in M7/M8, so the slowness is worth watching.
- CoinGecko: no 429 this window (M9's new flap shape did not recur). `xmrPriceUsd` was not measured live by this lane (ping only).
- The 02:57:38Z refresh log (see §9 anomaly 1) independently records all four endpoints 200 at that time (`coingecko=200 moneroocean=200 blockchain.info=200 mempool.space=200`), so this window has two separate all-200 observations ~6 minutes apart.

## 7. Artifact mirror state — NOT VERIFIED BY THIS LANE (no artifact tools available)

- **This subagent has no artifact tools**, so the live build of slug `atlas-command-center`, the live `getMining` profitability block, and the M9 live `mismatch: true` state could not be re-read directly. The host side of the mirror is verified here: `data/profitability.json` fresh (age 13 s at the 03:04:15 read), `stale: false`, `not_computed: []`, and diagnostics test 26 re-derived 81 figures from recorded inputs within rounding (XMR net Tier 2 2.7e-05 XMR/day, breakeven 56.1 H/W). **A lane with artifact access must re-read the live artifact before treating the mirror mismatch as current or resolved.** The rendered Mining-tab check remains NOT established (7th consecutive mission).

## 8. Data files

| File | Size | mtime (UTC) | `exported_at` / freshness at check |
|---|---|---|---|
| `data/coordinator.json` (1,133 B) | 1,133 B | 03:00:00 | `exported_at` **1795057255** (= 02:54:15 UTC); age 148 s at the 03:03 read. Mode simulation-only; emergency_stop true; mining_enabled false; pool_connected false; workers 0; shares pool_accepted 0; **hashrate status `not-measured`, measured_hps null** ("Gate 1 unmeasured — no probe measurement exists"); sessions_active 0. |
| `data/rewards.json` (921 B) | 921 B | 03:00:00 | `exported_at` **1795057255**; age 148 s. Mode simulation-only; emergency_stop true; split 75/25; **totals all 0** (ledger_entries 0; batches open/settled/held 0); balances `{}`; batches `[]`; ledger `[]`; chain ok, 0 entries. |
| `data/dashboard.json` (1,873 B) | 1,873 B | 03:00:00 | `exported_at` **1795057255**; age 148 s at the 03:03 read, re-exported by my diagnostics run (test 24) at 03:04:10. Mode simulation-only; emergency_stop true; hashrate `not-measured`, current/average hps null; shares all 0; earnings estimated null, confirmed 0; payouts count 0. |
| `data/admin.json` (27,570 B → 27,414 B after my run) | 27,414 B | 03:04:10 | `exported_at` **1795057255** at the 03:03 read (age 148 s), re-exported by my diagnostics run (test 25). Mode simulation-only; emergency_stop true; `daemon_restarts_24h: 128`, `daemon_restarts_all_time: 128`; security counts all 0. |
| `data/profitability.json` (22,475 B → 22,482 B after my run) | 22,482 B | 03:04:10 | `exported_at` **1795057255** at the 03:03 read (age 148 s), re-exported by my diagnostics run (test 26) at 03:04:04 (`exported_at` 1795057444, age 13 s at the 03:04:15 read). `stale: false`, `not_computed: []`. |
| `data/diagnostics.json` (5,398 B → 5,404 B) | 5,404 B | 03:04:10 | `ts` **1795057450**; 26 PASS / 0 FAIL — my run (see §4). |
| `data/snapshot.json` (385 B) | 385 B | 03:03:52 | `ts` **1795057432**; age 25 s at the 03:04:15 read, 54 s at close (see §2). |
| `data/atlas.db` | 364,544 B | 03:02:06 | See §3. |
| `data/recover.lock` | 0 B | 03:02:44 | Touched by the 03:02:44 recover run (no-op, pid 20881). |

- All five exports share the coordinator-pass instant 1795057255 (02:54:15 UTC) at the window's start — the last coordinator pass before the window; the next pass was not due inside the ~2-minute window. The exports' 148 s age at read is the normal 10-minute-pass cadence, not staleness.

## 9. Anomalies (recorded, not smoothed)

1. **Refresh failure carried — freshest occurrence 02:57:38Z, ~5 minutes BEFORE this window.** `logs/refresh-attempts.log`: `2026-11-19T02:57:38Z command-center FIXED button refreshatlasdata failed twice (state=started landedTs=null snapshot stuck 1795055090 ~30min stale); fallback ingestsnapshot landed ts=1795056966 snapshotId=76 refresh_state=landed`. Same entry also records: `command-center-diagnostics FIXED stored diagnostics block was stale 23pass/2fail ts=1795054105; re-ingested fresh diagnostics 26pass/0fail ts=1795056804 via ingestsnapshot`. No refresh-failure entry during my window 03:02:42–03:04:46; the host snapshot stayed fresh throughout (age 17–54 s). The carried issue is the dashboard-side refresh button + background task, not the host snapshot. This is the third consecutive baseline series observing the failure (M8: 21:53:44Z; M9: 01:53:00/01:54:41Z; M10: 02:57:38Z).
2. **mempool.space flapping — NOT flapping this window, but the config contradiction stands.** Diagnostics test 18 returned mempool.space 200, my independent curl returned 200 in 0.91 s, and the 02:57:38Z refresh log records mempool.space 200 as well — three all-200 observations. The config still records `mempool_space: "unreachable-from-this-host"`, labelled in the UI as "recorded claim, not a live measurement". The config claim is stale as a live measurement; it is a recorded claim, not a live one. Do not treat the endpoint as settled up on this window alone — M7/M8 both saw timeouts from the same host.
3. **Host memory above the 70% cap — carried, unchanged in kind.** Snapshot MEM 84.38%–90.82% across the window (M8: 79.44%–95.25%; M9: 84–93%). `free -m`: 7,934 MB total, 7,098 used, 835 avail; swap 428/1,023 MB used. Daemon itself is tiny (RSS ~10–14 MB); the pressure is host-wide, not the daemon. CPU also spiked over its 50% cap in-cycle (57.38% at 03:03:06; decision 394 `throttle-background-work` logged at 03:03:48).
4. **Platform VM restart ~01:26 UTC, pre-window (third of the day) — uptime-vs-metrics contradiction carried from M9.** `uptime` at 03:04 UTC read 1:38 (boot ~01:26 UTC), while metrics span 81,530 s (~22.6 h continuous) and diagnostics test 06 reports the same span. M9 noted the identical contradiction (`uptime` 1:10 at 02:37 UTC implying a ~01:27 UTC boot, metrics continuous through 01:20–01:33 with max gap 67 s). Either the platform restarted the VM at ~01:26 UTC and the metrics DB survived it (platform-persisted volume), or `uptime` is container-scoped and the DB is host-scoped — NOT asserted either way; the cause is unlogged. M8 had a VM restart ~21:58 UTC the previous evening; this is a separate, later one.
5. **Daemon churn: 128 restarts in 24 h / all-time.** Up from M8's 104. Most restarts now have a logged cause (diagnostics tests 10/11 by Lane E at 02:49/02:53 and by this lane at 03:03:51, plus recover.sh no-ops), but the churn rate itself is unchanged in kind from M7/M8. Crash cause still not established.
6. **M9 live mirror mismatch (`mismatch: true`, ~100 details) — NOT re-verified by this lane.** No artifact tools in this lane; the live `getMining` block was not re-read. Host side only: export fresh, stale false, test 26 re-derivation passes. The four diagnosed causes (host rounding vs 1e-9 tolerance; GPU breakeven MH/W vs H/W; GPU null-vs-value scope; split-projection browser rows) are carried unchanged; the calibration fix still needs repair authorization and is NOT done here.
7. **Carried gaps (unchanged from Missions 7/8/9, NOT fixed by this lane):** rendered Mining-tab check not established (7th consecutive mission; no artifact tools in this lane); Gate 1 hashrate still unmeasured (no probe measurement exists — `dashboard.json`/`coordinator.json` both `not-measured`, measured_hps null); stale "no miner yet" copy carried; M6 finding 1 latent (hardcoded `0 XMR` literals in `RewardAccounting.tsx`); duration secondary check wiring unverified (0 sessions exist, so `total_session_seconds` 0 is trivially consistent and the wiring is unexercised); referral rate 5% (500 bps) still a design parameter to confirm before any real-mode settlement; minimum payout still null; SupportXMR URL unconfirmed; external hosting unknown; treasury never deposited. M9 findings 8 (refresh-task step-9 mapping stale vs the real export shape) and 9 (tariff-constant `fetchedAt` schema gap) are also carried — neither was repaired in this window.
8. **CoinGecko 429 (M9 finding 5) — NOT observed this window.** Ping 200 first attempt at 03:03:41 UTC; no rate-limit evidence. Keep watching; no action owed.

## 10. Scale baseline (for Mission 10 testing)

- **DB:** `data/atlas.db` 364,544 B (M8 close: 331,776 B; M9 Lane E close: ~356 KB per diagnostics test 16 — growth is metrics/decisions/events rows only).
- **Exports:** admin.json 27,414 B; profitability.json 22,482 B; diagnostics.json 5,404 B; dashboard.json 1,873 B; coordinator.json 1,133 B; rewards.json 921 B; snapshot.json 385 B.
- **Diagnostics suite runtime:** 23.7 s wall (03:03:46–03:04:10 UTC), 26 tests, 0.99 s user + 0.28 s sys CPU — the suite is I/O-wait dominated (endpoint calls), not CPU-bound.
- **Coordinator pass timing (observable from logs):** last pass before the window completed 02:54:15 UTC (decision 390, `coordinator-pass-complete`, ts 1795057255); the pass writes all five exports atomically at the same instant. No pass fell inside the ~2-minute window, so no pass duration was observable here; the 10-minute cadence is the standing interval.
- **Daemon footprint:** RSS 10,156 KB at start / 14.1 MB in diagnostics test 13; lifetime CPU 2.48%; snapshot cycle 60 s.
- **Host load at close:** load 1.46/2.25/2.84; MEM 90.82% (snapshot) / 89.5% used (`free -m`); disk 19.13% used, 130 GB free.

## 11. Regression rule for verifiers (post-baseline state)

After this baseline, the daemon must still be exactly 1 pid (currently **23465**, started 03:03:51 by my diagnostics run's tests 10/11 — do not assume pid 20881), DB integrity ok, `user_version` **3**, emergency_stop true, mining disabled, trading paper-only, configs sha256 `46d3d12c…` / `b01a22ad…` (see §5). Diagnostics: **MY run 26/26 PASS against the 26-test suite** (tests 14/18 PASS this run — no flapping observed; see §4); the on-disk `data/diagnostics.json` is my run (ts 1795057450). The only permitted new rows are the ones diagnostics runs, daemon cycles, and coordinator passes write (metrics/decisions/events/pool_stats); **ledger, reward_batches, reward_batch_shares, payouts, referrals, users, workers, shares, sessions, achievements must remain 0** unless Mission 10 test work explicitly writes labelled simulation rows and records the change. `data/profitability.json` is fresh (`exported_at` 1795057444 at close, `stale: false`) — verifiers should treat the M9 mirror-mismatch question as open until a lane with artifact access re-reads the live `getMining` block.
