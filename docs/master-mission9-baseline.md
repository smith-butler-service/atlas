# ATLAS Master Mission 9 — Baseline (Lane B, read-only)

- **Lane:** B (baseline) — read-only verification; nothing edited, no code written, no config/DB change, no daemon restart initiated by this lane (the authorised diagnostics run restarts the daemon by design, tests 10/11).
- **Baseline window:** 2026-11-19 02:06:23–02:37:24 UTC (2026-11-18 21:06:23–21:37:24 EST).
- **Workspace:** `~/workspace/atlas/` (core/, data/, logs/, docs/, config/, backups/).
- **Overall verdict: PASS (baseline usable) — NOT all-green.** Safety-critical items are all green (daemon exactly 1 at every check, DB integrity ok, `user_version` 3, emergency stop ON, mining/trading disabled, no miners, no key material, ledger 0, rewards simulation-only, both configs byte-identical to the Mission 7 and Mission 8 baselines). The two diagnostics FAILs (tests 14/18, flappy endpoints) are the same signature as M7/M8 and are proven transient by independent all-200 curls later in the window, per the M6/M7/M8 precedent. CoinGecko flapped differently this time (429 rate-limit on first attempt, 200 on retry). New facts in this baseline: a refresh-button failure observed again at 01:53 UTC (pre-window, ~13 min before baseline start); an `uptime` reading that implies a ~01:27 UTC boot but is contradicted by continuous daemon metrics (see §10 anomaly 3 — no third VM restart asserted); the artifact build id and Mining-tab order could not be verified from this lane (no artifact tools, see §7).

## 1. Daemon

| Check | Time (UTC) | Measured value |
|---|---|---|
| Daemon at baseline start | 02:06:23 | exactly **1 pid: 6920** (PPID 1, elapsed 13:27, state S, %CPU 0.0, %MEM 0.1, **RSS 9,984 KB**, VSZ 19,904 KB, `python3 core/atlas_monitor.py`) |
| `pgrep -c -f 'atlas_[m]onitor.py'` | 02:06 | **1** (bracket form, no self-match artefact) |
| Daemon during my diagnostics run | 02:06:44–02:06:46 | Restarted by design (tests 10/11): 6920 → 9733 → **9757** (`logs/recover.log`: `02:06:46 restarted atlas_monitor pid 9757`). Expected churn, not a failure. |
| Daemon at baseline end | 02:36:13 / 02:37:24 | exactly **1 pid: 9757** (PPID 1, elapsed 29:26 at 02:36:13, **RSS 9,648 KB**, VSZ 19,908 KB). No restart between the diagnostics run and baseline end (`recover.log` 02:07:45–02:32:40 all `no-op daemon already running pid 9757`). |

- Startup events in the DB corroborate every restart since the M8 baseline end (see §3/§10 anomaly 4): 16 new `startup` events, ids 107–122. Seven are paired diagnostics-run restarts (test 10 + test 11, ~2 s apart); two are single recover.sh restarts (23:47:44, 01:27:44) with no logged cause.
- Note on timing: my diagnostics run ended 02:08:25 UTC, but the next command in this lane executed at 02:36:13 UTC (runtime delay, not a lane decision). The post-diagnostics state read below is therefore ~28 min after the run, and its deltas include ~28 min of live daemon/coordinator activity. Nothing about the run itself changed in that gap — the on-disk `data/diagnostics.json` is still my run (ts 1795054105, 23/25).

## 2. Snapshot (`data/snapshot.json`)

Pre-diagnostics read, 02:06:23 UTC (file mtime 02:05:59 UTC, 383 bytes):

```json
{"ts": 1795053959, "cpu_pct": 37.79, "mem_total_kb": 8124900, "mem_avail_kb": 1238688, "mem_used_pct": 84.75, "load": [0.97, 3.08, 2.88], "disk_total": 161043427328, "disk_used": 30781296640, "disk_free": 130040442880, "disk_used_pct": 19.11, "net_rx_bytes": 409120, "net_tx_bytes": 999380, "gpu": null, "mining": "disabled", "trading": "disabled-paper-only", "emergency_stop": true}
```

- `ts` 1795053959 = 02:05:59 UTC, **age ~24 s** at read. CPU 37.79% (within the 50% cap), MEM 84.75% used (above the 70% cap), load 0.97/3.08/2.88, disk 19.11% used.
- `mining: "disabled"`, `trading: "disabled-paper-only"`, `emergency_stop: true`, `gpu: null`.
- Monitor log cycles every ~60 s, all `db=ok stop=True` (e.g. `2026-11-19T02:05:59Z cycle ts=1795053959 cpu=37.79 mem=84.75 db=ok stop=True`).

End-of-baseline read, 02:37:24 UTC: `ts` 1795055812 (= 02:36:52 UTC, **age ~32 s**), CPU 58.86%, **MEM 91.96%** (avail 652,952 KB), load [7.34, 4.7, 3.78], disk 19.12%, same safety fields. Host MEM stayed above the 70% cap for the whole window (84.75%–91.96% observed; 90.39%–90.59% in the 02:01–02:04 cycles).

## 3. DB (`data/atlas.db`, read-only `mode=ro`)

| Check | Pre-diagnostics (02:06) | Post-diagnostics (02:36–02:37) |
|---|---|---|
| `PRAGMA integrity_check` | `ok` | `ok` (re-checked 02:37:24) |
| `PRAGMA user_version` | **3** | **3** |
| Size | 356,352 B | **360,448 B** |
| users | 0 | 0 |
| workers | 0 | 0 |
| shares | 0 | 0 |
| sessions | 0 | 0 |
| pool_stats | 55 | **57** |
| decisions | 363 | **372** |
| events | 120 | **122** |
| metrics | 1338 | **1370** |
| ledger | 0 | 0 |
| reward_batches | 0 | 0 |
| reward_batch_shares | 0 | 0 |
| payouts | 0 | 0 |
| referrals | 0 | 0 |
| achievements | 0 | 0 |

- All 15 tables present, plus `sqlite_sequence`. All 122 events are kind `startup` (no other kinds exist in the table). No real mining activity anywhere: users, workers, shares, ledger, payouts, referrals, achievements, sessions all 0.
- **Deltas vs the M8 baseline end (22:30:31 UTC: pool_stats 43, decisions 305, events 106, metrics 1116):** +14 pool_stats, +67 decisions, +16 events, +254 metrics over ~4 h. All explained as coordinator passes (10-min cadence), diagnostics runs (test 07 logs 4 decisions each; tests 10/11 add 2 `startup` events each), and daemon cycles (~1 metric/min). No Mission 9 build writes exist yet — this lane ran before any build lane work.
- **Deltas inside this window (02:06 → 02:37):** +2 pool_stats (polls at ~02:11 and ~02:21/02:31 — latest row 57 recorded 02:20:56), +9 decisions (4 from my diagnostics test 07 + coordinator passes), +2 events (my run's tests 10/11), +32 metrics (~31 min of daemon cycles, matching the 02:08→02:36 gap noted in §1).
- Latest `pool_stats` row 57: `MoneroOcean, recorded_at 1795054856 (= 02:20:56 UTC), hashrate 274,815,104 H/s, miners 4911, block_height 3809429, network_hashrate null, block_reward_piconero 600,000,000,000, pool_fee_bps 0`.
- Latest decision at 02:06, id 363: `coordinator, coordinator-pass-complete, ts 1795053653, "coordinator pass complete: pool poll skipped (not due); 0 expired session(s) closed; 0 activation(s) checked, 0 activated; 0 worker(s), 0 pool share(s) accepted, 0 local-test share(s) accepted"`. Decision 362: `scheduler, throttle-background-work, "CPU 53.28% over 50% cap", ts 1795053173`. Decision 361: `trading, stay-paper-only, "eligible capital $0; funding rule forbids any other source"`.
- Latest metrics row (02:37:24): ts 1795055812, CPU 58.86, MEM 91.96, load 7.34/4.7/3.78, disk 19.12, net rx 9,335,205 / tx 1,972,564. Metrics span at close: first ts 1794975856, last 1795055812, 1,370 rows.
- Max metrics gap in the last ~6 h (proper ts-ordered check, not rowid): **282 s at ts 1795039362 (~21:59 UTC)** — the known M8 VM restart. Next largest: 145 s (~23:47 UTC) and 102 s. No gap anywhere near 01:27 UTC (see §10 anomaly 3).

## 4. Diagnostics — MY RUN 23/25 PASS (25-test suite); on-disk pre-run file 25/25 PASS (another lane's 01:52 run)

- **My run:** `python3 core/diagnostics.py`, 02:06:44–02:08:25 UTC (~101 s), output preserved verbatim in `/tmp/m9-diag-run1.txt`. **Summary: `23 PASS, 2 FAIL, 0 NOT TESTED (of 25)`.** Run exactly once, as instructed; test 10 PASSED, so no re-run.
- **Pre-baseline file** (`data/diagnostics.json` at baseline start, ts 1795053189 = 01:53:09 UTC, 5,046 bytes): **25/25 PASS** — a run by another lane at 01:52:52 UTC (logged in `logs/refresh-attempts.log`: `2026-11-19T01:52:52Z diagnostics PASS 25/25 0 FAIL (daemon restarted by diagnostics tests 10/11 as designed; new pid=6920)`). Its test 02 saw pid 1714, test 06 saw 1323 metrics rows / span 77312 s, test 09 hold logged 53x, test 19 write 0.4 ms with events unchanged at 120, test 20 saw pid 6920 alive, test 14 `coingecko:200, moneroocean:200, blockchain.info:200`, test 18 all four endpoints 200 (incl. mempool.space, height 976515).
- **On-disk file at baseline end** (ts 1795054105 = 02:08:25 UTC, 5,225 bytes): **my run, 23/25** — this lane's run overwrote the file, as designed.

| Test | My run (25-test suite) | Detail (verbatim, my run) |
|---|---|---|
| 01 Python services | PASS | Python 3.12.3; atlas_monitor + atlas_core compile and import |
| 02 Monitoring daemon | PASS | running pid 6920, state S |
| 03 CPU and memory monitoring | PASS | CPU 37.79%, MEM 84.75% used, snapshot 45s old |
| 04 Disk and network monitoring | PASS | disk 19.11% used, net rx 409120 B / tx 999380 B |
| 05 SQLite database integrity | PASS | integrity_check ok; tables [achievements, decisions, events, ledger, metrics, payouts, pool_stats, referrals, reward_batch_shares, reward_batches, sessions, shares, sqlite_sequence, users, workers] |
| 06 Database persistence | PASS | 1338 metrics rows, span 78103s, DB at /home/hatch/workspace/atlas/data/atlas.db |
| 07 Coordinator decision-making | PASS | decide pass logged 4 new decisions |
| 08 Decision logging | PASS | 5 recent decisions, all with reasons; latest: no-throttle-needed |
| 09 Emergency stop | PASS | stop ON in config + snapshot; mining + trading disabled; hold decision logged (54x) |
| 10 Service restart | PASS | daemon pid 6920 stopped on SIGTERM and restarted; fresh snapshot written |
| 11 Automatic recovery | PASS | recover.sh restarted the daemon after a kill; fresh snapshot written |
| 12 Deployment persistence | PASS | all essential files under ~/workspace/atlas; recovery procedure + script present; processes do not survive VM replacement by platform design — restore is via recover.sh (see docs/recovery.md) |
| 13 Resource consumption | PASS | daemon RSS 14.2 MB, lifetime CPU 1.99% |
| **14 Network connectivity** | **FAIL** | `coingecko:200, moneroocean:ERR TimeoutError, blockchain.info:ERR TimeoutError` |
| 15 Security and permission controls | PASS | no key material, no miner processes, config not world-writable, emergency stop ON, mining + trading disabled |
| 16 Memory pressure | PASS | daemon RSS 10.0 MB (< 50 MB), DB 348.0 KB (< 100 MB), host MEM 86.74% (informational only) |
| 17 Snapshot freshness | PASS | data/snapshot.json ts age 23s (< 180 s) |
| **18 API data validity** | **FAIL** | `primary endpoint(s) failed: moneroocean, blockchain.info \| coingecko: HTTP 200, gecko_says='(V3) To the Moon!' \| moneroocean: HTTP None (TimeoutError: The read operation timed out) after retry \| blockchain.info: HTTP None (TimeoutError: The read operation timed out) after retry \| mempool.space: HTTP None (TimeoutError: The read operation timed out) after retry (non-fatal)` |
| 19 Database write latency | PASS | rolled-back test write 0.5 ms (< 1000 ms), events rows unchanged at 122 |
| 20 Daemon health | PASS | exactly 1 daemon (pid 9757, alive); monitor.log last line 32s old: 2026-11-19T02:07:48Z cycle ts=1795054068 cpu=51.09 mem=82.32 db=ok stop=True |
| 21 CPU pressure | PASS | daemon CPU 0.0% over 3 s window (< 25%), host load 1.40/2.29/2.60 (informational only) |
| 22 Queue delays | PASS | latest metrics gap 60s (expected ~60 s), newest row 35s old |
| 23 Reward ledger hash chain | PASS | verify_chain: PASS; 0 entries, 0 settled batch(es), 0 correction(s); ledger empty — chain trivially valid, 0 entries |
| 24 Dashboard export | PASS | dashboard.json fresh (1s old), hashrate not-measured, estimate null; host-verified totals match live DB: 0 ledger entries, 0 settled batch(es), 0 user / 0 ATLAS piconero |
| 25 Admin export | PASS | admin.json fresh (1s old), hashrate not-measured, estimate null; earnings block == dashboard earnings; host-verified totals match live DB: 0 ledger entries, 0 settled batch(es); security counts match live SQL: 0 suspicious, 0 invalid, 0 duplicate, 0 abuse, 0 auth failures, 0 payout anomalies; no token_hash/token_salt/wallet field in file |

- The two FAILs are the same flappy-endpoint timeouts as M7/M8 (tests 14/18). They are **proven transient in this window**: my independent curls at 02:36:21–02:36:39 returned 200 on MoneroOcean, blockchain.info, and mempool.space (see §6), and the pre-baseline 01:52 run passed 25/25 with all endpoints 200. The stall window was ~02:06–02:08; by 02:36 every endpoint answered.
- `core/diagnostics.py` is unchanged since M8 (37,974 B, mtime 2026-11-18 22:26:10 UTC — the 25-test suite); `core/atlas_admin.py` unchanged (31,180 B, mtime 2026-11-18 22:25:09 UTC).

## 5. Configs / safety — UNCHANGED

`config/atlas.json` — mtime **2026-11-18 04:32:36 UTC**, 808 bytes, sha256 `46d3d12c1b907c048f2876755ce0d22a01316899d894561c6f86da67bfacab26` (**identical to the M7 and M8 baseline hashes**):

- `emergency_stop`: **true**
- `mining.enabled`: **false** — status `design-only`, reason "No authorization to mine on shared host infrastructure; no GPU; shared 1.5 CPU cell"; `cpu_candidate: "monero-randomx"`
- `trading.mode`: **paper-only**; `trading.enabled: false`; `eligible_capital_usd`: **0**; futures/leverage/margin/options all false; reason "No realized net mining profits exist; funding rule (Part 8) forbids any other source"
- `monitor_interval_s`: 60; `host_role`: `worker-1-bootstrap`; `version`: `0.1.0-stage2`; limits max_cpu_pct 50 / max_mem_pct 70; blockchain_apis: coingecko `verified-200`, moneroocean `verified-200`, blockchain_info `verified-200`, mempool_space `unreachable-from-this-host`.

`config/pool-rewards.json` — mtime **2026-11-18 07:35:40 UTC**, 2,788 bytes, sha256 `b01a22ad5d703765a84b3fd7daa1b3b624bdfc3b4b9ea0238d1da3e95ad13464` (**identical to the M7 and M8 baseline hashes**):

- `mode`: **simulation-only**; primary pool MoneroOcean, **0% fee** (`pool_fee_bps: 0`), `api_base https://api.moneroocean.stream`, stats endpoint `/pool/stats`
- Fallbacks: **SupportXMR 0.6% fee** (`pool_fee_bps: 60`); **P2Pool 0% fee** (`pool_fee_bps: 0`)
- `reward_split`: **75% users / 25% ATLAS**; referral funding from the ATLAS 25% only; integer piconero rounding; referral rate 500 bps (5%)
- `minimum_payout`: **unset — placeholder, not set** (`piconero: null`, `xmr: null`); "to be decided and authorized before any payout flow is activated"
- Safety: activation gate (no real payouts / pool connection / mining until explicitly authorized after simulation/testnet success and security testing); emergency stop honoured; "no wallet credentials, seed phrases, private keys, or wallet passwords are stored anywhere in this config or in ATLAS"

Both mtimes predate the Mission 7 baseline and every value matches the Mission 7/8 baseline records verbatim — **UNCHANGED**. Not edited by this lane.

Safety (measured 02:06–02:37):

- **Miner processes: NONE.** `ps aux | grep -iE 'xmrig|randomx|miner|cpuminer|ethminer'` returned nothing.
- **Pool-port connections: NONE.** `ss -tn` showed a single ESTAB connection to a proxy (`[fd8b:4f84:7d32:99::1]:3128`); no connections on 3333/4444/5555/7777/14444/10128/3334.
- **Key/seed/password files: NONE in the workspace.** `find` for `*seed*`, `*private*key*`, `*.pem`, `*.key`, `*password*`, `*secret*`, `*mnemonic*`, `*wallet*` returned no files.

## 6. Endpoints the profitability model needs (curl, 20 s timeout, first pass 02:36:21–02:36:39 UTC, one retry where noted)

| Endpoint | First attempt | Retry / note | Latency |
|---|---|---|---|
| `https://api.moneroocean.stream/pool/stats` | **200** (12,328 B), `hashRate 285,806,599.63 H/s, miners 4926, lastBlockFound 3809429` | — | 1.07 s |
| `https://api.moneroocean.stream/network/stats` | **200** (2,512 B), XMR difficulty 787,880,387,293, height 3,809,486, value 600,000,000,000 piconero | — | 1.32 s |
| `https://api.coingecko.com/api/v3/simple/price?ids=monero,kaspa,ravencoin,ergo&vs_currencies=usd` | **429** (0.58 s, `You've exceeded the Rate Limit`) | **200** on retry (0.71 s): XMR $500.37, KAS $0.0270543, RVN $0.00109849, ERG $0.204211 | 0.58 s / 0.71 s |
| `https://blockchain.info/q/latesthash` | **200** (64 B) | `getblockcount` separately 200: **976,517** | 0.97 s |
| `https://mempool.space/api/v1/fees/recommended` | **200** (74 B), `{"fastestFee":2,"halfHourFee":1,"hourFee":1,"economyFee":1,"minimumFee":1}` | — | 0.82 s |
| `https://kas.2miners.com/api/stats` | **200** (538 B), pool hashrate 3,901,807,593,178,702 H/s (3.90 PH/s), minersTotal 721; node networkhashps 310,650,740,280,559,680 H/s, difficulty 30,237,853,182,153,528, height 596,352,481, blockReward 194,454,365 sompi, avgBlockTime 0.1 | — | 1.38 s |
| `https://rvn.2miners.com/api/stats` | **200** (526 B), pool hashrate 235,847,032,570 H/s, minersTotal 1525; node networkhashps 499,881,718,678 H/s, difficulty 6919.8165, height 4,631,753, avgBlockTime 59.36, dagSize 6,249,510,272 | — | 1.48 s |
| `https://erg.2miners.com/api/stats` | **200** (562 B), pool hashrate 260,508,627,674 H/s, minersTotal 299; node networkhashps 556,950,517,420 H/s, difficulty 67,279,622,504,448, height 1,919,874, avgBlockTime 120.80 | Second fetch minutes later: pool hashrate 257,929,526,337 H/s (pool hashrate moves; network fields identical) | 1.43 s |
| `https://api.kaspa.org/info/hashrate` | **200** (30 B), `{"hashrate":301708.1722497074}` (TH/s → 301.71 PH/s at first fetch; 302,378.53 TH/s on the second fetch minutes later) | `/info/blockreward` also **200**: `{"blockreward":1.94454365}` | 0.97 s |

- **Reachable on this pass: 9/9** after the single CoinGecko retry (8/9 on first attempt). MoneroOcean `/api/stats` was **not probed** — it 404s per the task note; `/pool/stats` is the working endpoint and was used.
- **Interpretation, stated plainly:** flapping, not a settled outage — the evidence inside ~30 minutes points both ways: (a) my diagnostics run 02:06–02:08 records MoneroOcean + blockchain.info + mempool.space `TimeoutError` after retry; (b) the 01:52 run by another lane passed all endpoints 200; (c) my curls at 02:36:21–02:36:39 return 200 on all nine endpoints. CoinGecko's 429-then-200 is a rate-limit flap, distinct from the timeout flap on the other three. Do not treat any endpoint as settled down or up on one observation.
- DNS is not the cause (M8 established this; endpoints resolve and answer 200 minutes after timing out).

## 7. Artifact — NOT VERIFIED BY THIS LANE (no artifact tools available)

- **This subagent has no artifact tools** (no artifact namespace in its tool list), so the live build of slug `atlas-command-center` and the live Mining-tab section order could not be read directly. The only artifact-related binary on the host, `/opt/hatch/bin/builtin-artifacts`, writes only the two tutorial artifacts (`welcome-to-muse-tutorial`, `muse-town`) and cannot read `atlas-command-center` status.
- The last established build id is therefore still **M8's `d5e7be84-61ad-46de-9d31-b45710310ef4`** (from the Mission 8 report) — **not re-confirmed in this window**. A lane with artifact access must re-read the live artifact before treating the build id or the Mining-tab section order (Admin section directly below User dashboard) as current.
- The host side of the mirror is unchanged from M8 (§3/§8): batches/entries/totals all 0.

## 8. Data files

| File | mtime (UTC) | `exported_at` / freshness at check |
|---|---|---|
| `data/coordinator.json` (1,133 B) | 02:30:56 (at end read) | `exported_at` **1795055456** (= 02:30:56 UTC); ~6.5 min old at the 02:37:24 read. At baseline start it was 1795053653 (= 02:00:53 UTC, ~5.5 min old). Mode simulation-only; emergency_stop true; mining_enabled false; pool_connected false ("No pool connection authorized — read-only /pool/stats polling only"); workers total/active 0; shares pool_accepted 0; **hashrate status `not-measured`, measured_hps null** ("Gate 1 unmeasured — no probe measurement exists"); sessions_active 0; `last_decision_id` **363** (matches the live DB at that export); `last_coordinator_pass_at` 1795053653; pool_stats_latest 269,004,128 H/s, 4889 miners, height 3809429, block_reward 600,000,000,000 piconero, fee 0 bps. Exports refresh on the 10-minute coordinator pass, by design. |
| `data/rewards.json` (921 B) | 02:30:56 | `exported_at` **1795055456**. Mode simulation-only; emergency_stop true; split 75/25, referral 500 bps; **totals all 0** (user/referral/ATLAS/fees/payouts/reversals piconero 0; ledger_entries 0; batches open/settled/held 0); balances `{}`; batches `[]`; ledger `[]`; chain `{ok: true, entries: 0, batches: 0, "ledger empty — chain trivially valid, 0 entries"}`. |
| `data/dashboard.json` (1,873 B) | 02:30:56 | `exported_at` **1795055456**. Mode simulation-only; emergency_stop true; hashrate `not-measured`, current/average hps null ("Gate 1 unmeasured"); shares all 0; duration total_session_seconds 0, active_sessions 0; workers all 0; earnings estimated_piconero null ("Cannot estimate — hashrate not measured"), confirmed_piconero 0 ("SIMULATION ONLY — no pool rewards"); balances `{}`; lifetime totals all 0; payouts count 0, rows `[]`; efficiency acceptance_rate null ("Not measurable — no shares yet"); sync stale false. |
| `data/admin.json` (28,547 B) | 02:30:56 | `exported_at` **1795055456**. Mode simulation-only; emergency_stop true; scope: "Admin view — aggregates and operational data only. No login exists yet — this section is not access-controlled." Network: users 0, workers all 0, worker_rows `[]`, hashrate `not-measured` (Gate 1), shares all 0, monitoring_uptime 79,595 s ("0d 22h 6m", metrics_first_ts 1794975856, metrics_last_ts 1795053598, metrics_rows 1332 at the 02:00:53 export), **daemon_restarts_24h 122, daemon_restarts_all_time 122**, daemon_uptime null ("Daemon start time is not recorded"); mining: earnings estimated null / confirmed 0, all XMR figures 0 piconero, payouts_count 0, failed_payouts 0, batches 0/0/0; infrastructure/security/logs as in M8, all zeros. No `token_hash`/`token_salt`/`wallet` field (per test 25's own check, which passed on my run). |
| `data/diagnostics.json` (5,225 B) | 02:08:25 | `ts` **1795054105**; **23 PASS / 2 FAIL (of 25) — my run** (see §4). |
| `data/snapshot.json` (383 B) | 02:36:52 | `ts` **1795055812**; age ~32 s at 02:37:24 read (see §2). |
| `data/atlas.db` | 02:36:52 | 360,448 B (see §3). |

## 9. Live price / network snapshot for the model (baseline inputs — VERIFIED at fetch time, no profitability conclusions computed)

Fetched 2026-11-19 02:36:21–02:36:47 UTC (2026-11-18 21:36:21–21:36:47 EST). All figures below are **VERIFIED** (measured from a live API in this window, source + time shown). Derived figures are labelled DERIVED with the formula. The M2 comparison column is against `docs/mission2-obj4-findings.md` (fetched 2026-11-18 ~00:55–01:00 EST).

| Input | Value (this baseline) | Source | M2 value (2026-11-18) |
|---|---|---|---|
| XMR price | **$500.37 USD** | CoinGecko simple/price, retry fetch 02:36:39 UTC | $507.17 |
| Monero difficulty | **787,880,387,293** | MoneroOcean /network/stats, 02:36:39 UTC (top-level + key `18081`, identical) | 772,656,444,936 |
| Monero height | **3,809,486** (main_height same) | MoneroOcean /network/stats | 3,808,871 |
| Monero block value | **0.6 XMR** (600,000,000,000 piconero) | MoneroOcean /network/stats `value` | 0.6 XMR (last block 0.6045 incl. fees) |
| Monero network hashrate | **~6.566 GH/s — DERIVED** (difficulty / 120 s) | Computed from the verified difficulty above, same formula as M2 | 6.44 GH/s (derived the same way) |
| MoneroOcean pool hashrate / miners | **285,806,599.63 H/s / 4,926 miners** | MoneroOcean /pool/stats, 02:36:21 UTC | 266.5 MH/s / 4,926 miners |
| KAS price | **$0.0270543 USD** | CoinGecko simple/price, 02:36:39 UTC | $0.02727563 |
| Kaspa network hashrate | **310.65 PH/s** (2Miners node) vs **302.38 PH/s** (api.kaspa.org) — two live sources disagree by ~2.7%; record both, do not average silently | 2Miners kas api/stats + api.kaspa.org /info/hashrate, 02:36:21–02:36:47 UTC | 313.1 PH/s (kaspa.org) / 317.0 PH/s (2Miners) |
| Kaspa difficulty | **30,237,853,182,153,528** | 2Miners kas api/stats | 31,344,111,208,331,531 |
| Kaspa height | **596,352,481** | 2Miners kas api/stats (node height; api.kaspa.org height not fetched) | — |
| Kaspa block reward | **1.94454365 KAS** | api.kaspa.org /info/blockreward AND 2Miners blockReward 194,454,365 sompi — two sources agree | 1.94454365 KAS |
| Kaspa pool (2Miners) | **3.90 PH/s, 721 miners** | 2Miners kas api/stats | 3.96 PH/s, 714 miners |
| RVN price | **$0.00109849 USD** | CoinGecko simple/price, 02:36:39 UTC | $0.00110692 |
| Ravencoin network hashrate | **499.88 GH/s** (2Miners node networkhashps); cross-check **~497.3 GH/s — DERIVED** (MoneroOcean RVN difficulty 29,836,936,179,541 / 60 s) | 2Miners rvn api/stats + MoneroOcean /network/stats key `8766` | 533.9 GH/s (2Miners) / 551.6 GH/s (derived) |
| Ravencoin difficulty | **29,836,936,179,541** (MoneroOcean); 2Miners node reports `difficulty: 6919.8165` in different units — do not mix | MoneroOcean /network/stats key `8766` | 33,098,427,129,147 |
| Ravencoin height | **4,631,753** (2Miners and MoneroOcean agree) | 2Miners rvn api/stats; MoneroOcean key `8766` | 4,630,530 |
| Ravencoin block value | **1,250 RVN** (125,000,000,000 satoshi) | MoneroOcean /network/stats key `8766` `value` | 1,250.05 RVN |
| Ravencoin pool (2Miners) | **235.85 GH/s, 1,525 miners** | 2Miners rvn api/stats | 241.9 GH/s, 1,559 miners |
| ERG price | **$0.204211 USD** | CoinGecko simple/price, 02:36:39 UTC | $0.205371 |
| Ergo network hashrate | **556.95 GH/s** (2Miners node networkhashps) | 2Miners erg api/stats, 02:36:21 UTC | 713.2 GH/s (2Miners) / 693.4 GH/s (derived) |
| Ergo difficulty | **67,279,622,504,448** (2Miners and MoneroOcean key `9053` agree exactly) | 2Miners erg api/stats; MoneroOcean /network/stats | 69,338,556,006,400 |
| Ergo height | **1,919,874** | 2Miners erg api/stats; Ergo explorer blocks confirm | 1,919,265 |
| Ergo block reward | **3 ERG** (3,000,000,000 nanoERG) | Ergo explorer `api.ergoplatform.com/api/v1/blocks`, blocks 1,919,874 and 1,919,873 | 3 ERG |
| Ergo pool (2Miners) | **~258–261 GH/s, 299 miners** (two fetches minutes apart: 260,508,627,674 then 257,929,526,337) | 2Miners erg api/stats | 254.7 GH/s, 291 miners |
| Bitcoin height (context) | **976,517** | blockchain.info /q/getblockcount, 02:36:39 UTC | — |

- **No profitability conclusions are computed in this lane.** The build lane owns the model arithmetic; these are inputs only. Notable input movements vs M2 for the build lane to notice (not conclusions): XMR price −1.3%, XMR difficulty +2.0%, ERG network hashrate down from ~713 GH/s to ~557 GH/s (−22%), RVN network hashrate down from ~534 GH/s to ~500 GH/s, KAS two-source hashrate spread ~2.7% (310.65 vs 302.38 PH/s).
- **CARRIED-or-VERIFIED labelling:** every figure in this section is VERIFIED at the fetch time shown. Nothing in this section is carried from M2 — the M2 column is comparison only.

## 10. Anomalies (recorded, not smoothed)

1. **Endpoints flapping (diagnostics FAIL 14 + 18 in my run, confirmed all-200 by independent curls ~28 min later).** MoneroOcean, blockchain.info (and mempool.space) timed out in my run 02:06–02:08 while CoinGecko answered 200; the 01:52 run by another lane passed all endpoints 200; my curls at 02:36:21–02:36:39 returned 200 on all nine model endpoints. CoinGecko added a new flap shape this window: 429 rate-limit on first attempt, 200 on retry. Not a settled outage; not a config defect. Verifiers should re-probe before treating any endpoint as down.
2. **Refresh failure observed again — 01:53:00 / 01:54:41 UTC (pre-baseline, ~13 min before window start).** `logs/refresh-attempts.log`, verbatim:
   - `2026-11-19T01:53:00Z command_center FAIL button refreshatlasdata attempt1 state=started landedTs=null dashboard_ts=1795049732 (~57min stale)`
   - `2026-11-19T01:54:41Z command_center FAIL button refreshatlasdata attempt2(retry) state=started landedTs=null dashboard_ts=1795049732 still stale`
   - `2026-11-19T01:56:23Z command_center FIXED fallback ingestsnapshot snapshotId=65 ts=1795053357 dashboard_ts 1795049732 -> 1795053357 refresh_state=landed emergencyStop=true`
   Same pattern as M8 anomaly 5 (21:53:44 UTC) and M7. No refresh-failure entry during my baseline window 02:06–02:37; the host snapshot stayed fresh throughout (age 24–45 s). The carried issue is the dashboard-side refresh button, not the host snapshot.
3. **`uptime` reading contradicts continuous daemon metrics — NO third VM restart asserted.** `uptime` at 02:37:01 UTC read `up 1:10`, implying a boot ~01:27 UTC. Against that: (a) metrics rows are continuous through 01:20:00–01:33:20 UTC at ~60 s cadence (ts 1795051237 … 1795051965, max gap 67 s); (b) the largest metrics gap in the last ~6 h is 282 s at ~21:59 UTC — the known M8 VM restart, not 01:27; (c) no watchdog `FIXED`/`down` line exists for 01:27 (watchdog: `01:22:44 PASS daemon running pid 15178` → `01:27:52 PASS daemon pid 1714 running, snapshot.json fresh`); (d) the 01:27:44 event is a single recover.sh daemon restart (`recover: restarted atlas_monitor pid 1714`, startup event id 118 ts 1795051664), with no logged cause. The `uptime` figure most likely reflects the exec sandbox container rather than the host, but that is not proven. Recorded as a contradiction for verifiers: **do not cite a third VM restart on the strength of the uptime line alone.**
4. **Daemon churn continues: 16 startup events since the M8 baseline end; 122 restarts in 24 h / all-time.** Startup events ids 107–122 (all events in the table are kind `startup`): pairs 107/108 (22:50:50/52), 109/110 (22:52:44/46), 112/113 (23:53:03/05), 114/115 (00:52:54/56), 116/117 (00:55:29/31), 119/120 (01:52:53/56), 121/122 (02:06:44/46, my run) — each pair is one diagnostics run's tests 10 + 11. Singles 111 (23:47:44) and 118 (01:27:44) are recover.sh restarts with no preceding test-10 restart and no logged cause. `recover.log` "restarted" lines since M8 end: 22:50:52 pid 10039, 22:52:46 pid 10396, 23:47:43 pid 2026, 23:53:05 pid 2808, 00:52:56 pid 14541, 00:55:31 pid 15178, 01:27:44 pid 1714, 01:52:56 pid 6920, 02:06:46 pid 9757 — 9 lines vs 16 startup events; the difference is the 7 test-10 direct restarts, which log a startup event but no recover.sh line. `data/admin.json` reports `daemon_restarts_24h: 122, daemon_restarts_all_time: 122` (== the events total). The churn rate is unchanged in kind from M8; per-restart explanations exist for 14 of the 16 (diagnostics pairs), 2 remain unexplained.
5. **Pre-baseline diagnostics file was another lane's 25/25 run (01:52:52 UTC).** Not an anomaly in itself — recorded so verifiers do not mistake it for this lane's run. My run is 23/25 (FAILs 14/18); the on-disk file at baseline end is mine.
6. **Carried gaps (unchanged from Mission 8, NOT fixed by this lane):** rendered Mining-tab check not established (no artifact tools in this lane — now the fifth consecutive mission, M4–M8 plus this baseline); Gate 1 browser hashrate still unmeasured (no probe measurement exists); refresh-button failure carried (anomaly 2); stale "no miner yet" copy carried (two literal strings in `Mining.tsx` per the M4 verification — host cannot verify the rendered tab); M6 finding 1 latent (reward display self-contradiction: settled sim batch `sim-batch-test-1`, 1 XMR shown while the DB holds 0 batches/0 entries; needs a repair-authorized inspection); M6 finding 1's cause — hardcoded zero literals in `RewardAccounting.tsx` — still present per the M8 report; duration wiring unverified (0 sessions exist, so `total_session_seconds` 0 / `active_sessions` 0 is trivially consistent and the wiring is unexercised); host memory above the 70% cap (84.75%–91.96% observed this window); referral rate 5% (500 bps) still a design parameter to confirm before any real-mode settlement; minimum payout still null; `mempool.space` config status `unreachable-from-this-host` vs live 200 — config-recorded claim vs live measurement, labelled in the UI as "recorded claim, not a live measurement".

## 11. Regression rule for verifiers (post-baseline state)

After this baseline, the daemon must still be exactly 1 pid (currently **9757**, started 02:06:46 by recover.sh during my diagnostics run — do not assume pid 6920), DB integrity ok, `user_version` **3**, emergency_stop true, mining disabled, trading paper-only, configs sha256 `46d3d12c…` / `b01a22ad…` (see §5). Diagnostics: **MY run 23/25 against the 25-test suite** (FAILs 14 + 18 are the flappy-endpoint timeouts, verbatim in §4); the pre-baseline on-disk file was a different, earlier run: **25/25 at 01:53:09 UTC** (another lane). The only permitted new rows are the ones diagnostics runs, daemon cycles, and coordinator passes write (metrics/decisions/events/pool_stats); **ledger, reward_batches, reward_batch_shares, payouts, referrals, users, workers, shares, sessions, achievements must remain 0** unless Mission 9 build work explicitly writes labelled simulation rows and records the change. Price/network inputs for the model are §9, fetched 02:36:21–02:36:47 UTC — the build lane must re-fetch before any decision use; do not treat them as current after the window. The artifact build id and Mining-tab section order are **unverified in this baseline** (§7) and must be re-read by a lane with artifact access.
