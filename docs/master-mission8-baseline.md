# ATLAS Master Mission 8 — Baseline (Lane B, read-only)

- **Lane:** B (baseline) — read-only verification; nothing edited, no code written, no config/DB change, no daemon restart initiated by this lane (the authorised diagnostics run restarts the daemon by design, tests 10/11; further restarts during the window are other lanes' diagnostics runs and recover.sh).
- **Baseline window:** 2026-11-18 22:22:08–22:30:31 UTC (17:22:08–17:30:31 EST).
- **Workspace:** `~/workspace/atlas/` (core/, data/, logs/, docs/, config/, backups/).
- **Overall verdict: PASS (baseline usable) — NOT all-green.** Safety-critical items are all green (daemon exactly 1 at every check, DB integrity ok, `user_version` 3, emergency stop ON, mining/trading disabled, no miners, no key material, ledger 0, rewards simulation-only, both configs byte-identical to the Mission 7 baseline). The two diagnostics FAILs (tests 14/18, flappy endpoints) are proven transient by independent all-200 curls minutes later, per the Mission 6/7 precedent. Three new facts land in this baseline: a second platform VM restart (~21:58 UTC, pre-window), the Mission 8 admin export appearing mid-baseline (see §9 anomaly 3), and a third concurrent diagnostics run starting at the window's end.

## 1. Daemon

| Check | Time (UTC) | Measured value |
|---|---|---|
| Daemon at baseline start | 22:22:08 | exactly **1 pid: 2084** (PPID 1, started 22:02:41, elapsed 19:27, state S, %CPU 0.0, %MEM 0.1, **RSS 10,732 KB**, VSZ 19,904 KB, `python3 core/atlas_monitor.py`) |
| `pgrep -c -f 'atlas_[m]onitor.py'` | 22:22 | **1** (bracket form, no self-match artefact) |
| Daemon during my diagnostics run | 22:22:37–22:24:22 | Restarted by design (tests 10/11): 2084 → 4525 → 4555 (`logs/recover.log`: `22:22:42 no-op daemon already running pid 4525`, `22:22:44 restarted atlas_monitor pid 4555`). Expected churn, not a failure. |
| Daemon during concurrent lane's diagnostics run | 22:26:49 | 4555 → **5212** (`recover.log`: `22:26:49 restarted atlas_monitor pid 5212`; `22:27:41 no-op daemon already running pid 5212`). Another lane's diagnostics tests 10/11, not mine. |
| Daemon at baseline end | 22:30:31 | exactly **1 pid: 5773** (PPID 1, started 22:30:28, elapsed 00:03, **RSS 14,580 KB**). Restarted by `recover.sh` at 22:30:28. DB deltas 22:29→22:30:31 (+4 decisions, +2 startup events, +3 metrics) match a third diagnostics run's tests 07 + 10/11 in flight at the window's end; its trigger was not yet logged at write time. I did not restart the daemon at any point. |

- Pre-window restarts (from `logs/recover.log` + `logs/refresh-attempts.log`, all explained, none mine): 20:02:41 pid 1963; 20:52:53/55 pid 6192 (diagnostics self-test, "diagnostics self-test restarted daemon from pid 1963, 50min uptime"); 21:22:39 pid 1735 (diagnostics self-test); 21:52:57/59 pid 4143 (diagnostics tests 10/11, 21:53 run 24/24 PASS); 22:02:41 pid 2084 (post-VM-restart recovery, see §9 anomaly 2).
- Startup events in the DB corroborate every restart: ids 93/94 (19:53:03 / 20:02:41), 95/96 (20:52:53/55), 97 (21:22:39), 98/99 (21:52:57/59), 100 (22:02:41), 101/102 (22:22:44/45, my run), 103/104 (22:26:49/50, concurrent run), 105/106 (22:30:28/29, third run). All kind `startup`, message `atlas_monitor started`.

## 2. Snapshot (`data/snapshot.json`)

Pre-diagnostics read, 22:22:08 UTC (file mtime 22:21:48 UTC, 381 bytes):

```json
{"ts": 1795040508, "cpu_pct": 53.88, "mem_total_kb": 8124900, "mem_avail_kb": 1670724, "mem_used_pct": 79.44, "load": [3.46, 2.74, 1.73], "disk_total": 161043427328, "disk_used": 30513143808, "disk_free": 130305761280, "disk_used_pct": 18.95, "net_rx_bytes": 59379, "net_tx_bytes": 66116, "gpu": null, "mining": "disabled", "trading": "disabled-paper-only", "emergency_stop": true}
```

- `ts` 1795040508 = 22:21:48 UTC, **age 20 s** at read. CPU 53.88% (above the 50% cap — decision 297 `throttle-background-work`, "CPU 53.88% over 50% cap"), MEM 79.44% used (above the 70% cap), load 3.46/2.74/1.73, disk 18.95% used.
- `mining: "disabled"`, `trading: "disabled-paper-only"`, `emergency_stop: true`, `gpu: null`.
- Monitor log cycles every ~60 s, all `db=ok stop=True` (e.g. `2026-11-18T22:21:48Z cycle ts=1795040508 cpu=53.88 mem=79.44 db=ok stop=True`). MEM across the window's cycles: 78.65%–95.25% (e.g. 22:17:46 cpu=59.89 mem=95.25; 22:19:47 cpu=74.25 mem=93.23).

Post-diagnostics read, 22:29:28 UTC: `ts` 1795040931 (= 22:28:51 UTC, **age 37 s**), CPU 30.92%, **MEM 86.64%** (avail 1,085,356 KB), load [2.62, 3.19, 2.34], disk 18.94%, same safety fields. Final read, 22:30:31 UTC: `ts` 1795041029 (**age 2 s**), CPU 58.65%, **MEM 90.1%**. Host `free -m` at 22:29: total 7934 MB, used 6988, avail 946; load average 2.68/3.12/2.35; swap 1023 MB, 378 used. (The `df` overlay root, 7.5G/1%, is the container root, not the snapshot disk; snapshot disk 18.94% is the host figure, as in M7.)

## 3. DB (`data/atlas.db`, read-only `mode=ro`)

| Check | Pre-diagnostics (22:22) | Post-diagnostics (22:29) | Baseline end (22:30:31) |
|---|---|---|---|
| `PRAGMA integrity_check` | `ok` | `ok` | `ok` (re-checked 22:30:31) |
| `PRAGMA user_version` | **3** | **3** | **3** |
| Size / pages | 327,680 B, 80 pages × 4096 | 327,680 B | **331,776 B** |
| users | 0 | 0 | 0 |
| workers | 0 | 0 | 0 |
| shares | 0 | 0 | 0 |
| sessions | 0 | 0 | 0 |
| pool_stats | 43 | 43 | 43 |
| decisions | 293 | **301** | **305** |
| events | 100 | **104** | **106** |
| metrics | 1104 | **1113** | **1116** |
| ledger | 0 | 0 | 0 |
| reward_batches | 0 | 0 | 0 |
| reward_batch_shares | 0 | 0 | 0 |
| payouts | 0 | 0 | 0 |
| referrals | 0 | 0 | 0 |
| achievements | 0 | 0 | 0 |

- All 15 tables present, plus `sqlite_sequence`. No real mining activity anywhere: users, workers, shares, ledger, payouts, referrals, achievements, sessions all 0.
- **Deltas are diagnostics runs + live daemon/coordinator activity, not Mission 8 build writes:** my run's test 07 logs 4 decisions; each diagnostics run's tests 10/11 add 2 `startup` events; metrics grow ~1/min from daemon cycles; pool_stats unchanged at 43 (latest poll 22:21:09, next due ~22:31).
- Latest `pool_stats` row 43: `MoneroOcean, recorded_at 1795040469 (= 22:21:09 UTC), hashrate 259,064,041 H/s, miners 4916, block_height 3809325, network_hashrate null, block_reward_piconero 600,000,000,000, pool_fee_bps 0`.
- Latest decision at 22:29, id 301: `scheduler, no-throttle-needed, "CPU 41.52% within cap", ts 1795040807`. Decision 293 (pre-diagnostics latest): `coordinator, coordinator-pass-complete, ts 1795040470, "coordinator pass complete: pool poll ok; 0 expired session(s) closed; 0 activation(s) checked, 0 activated; 0 worker(s), 0 pool share(s) accepted, 0 local-test share(s) accepted"`. Decision 292: `pool-stats-polled, "MoneroOcean /pool/stats: hashrate 259064041 H/s, miners 4916, height 3809325"`.
- Latest metrics row (22:29): `(1795040931, 30.92, 86.64, 2.62, 3.19, 2.34, 18.94, 187944, 301281)`, 60 s cadence.

## 4. Diagnostics — MY RUN 22/24 PASS (24-test suite); on-disk file now 23/25 PASS (25-test suite, concurrent lane)

- **My run:** `python3 core/diagnostics.py`, 22:22:37–22:24:22 UTC (~106 s), output preserved verbatim in `/tmp/m8-diag-run1.txt`. **Summary: `22 PASS, 2 FAIL, 0 NOT TESTED (of 24)`.** Run exactly once, as instructed; test 10 PASSED, so no re-run.
- **Pre-baseline file** (`data/diagnostics.json` at baseline start, ts 1795038790 = 21:53:10 UTC, 4,609 bytes): **24/24 PASS** — the 21:53 run by another lane.
- **On-disk file at baseline end** (ts 1795040907 = 22:28:27 UTC, 5,225 bytes): **23 PASS / 2 FAIL (of 25)** — a concurrent lane's run that overwrote the file after mine. Same FAILs (14 + 18, verbatim below); new test 25 "Admin export" PASS. Its test 02 saw pid 4555, test 06 saw 1109 metrics rows / span 64890 s, test 09 hold logged 46x, test 19 write 0.4 ms with events unchanged at 104, test 20 saw pid 5212 alive.

| Test | My run (24-test suite) | Detail (verbatim, my run) |
|---|---|---|
| 01 Python services | PASS | Python 3.12.3; atlas_monitor + atlas_core compile and import |
| 02 Monitoring daemon | PASS | running pid 2084, state S |
| 03 CPU and memory monitoring | PASS | CPU 53.88%, MEM 79.44% used, snapshot 50s old |
| 04 Disk and network monitoring | PASS | disk 18.95% used, net rx 59379 B / tx 66116 B |
| 05 SQLite database integrity | PASS | integrity_check ok; tables [achievements, decisions, events, ledger, metrics, payouts, pool_stats, referrals, reward_batch_shares, reward_batches, sessions, shares, sqlite_sequence, users, workers] |
| 06 Database persistence | PASS | 1104 metrics rows, span 64652s, DB at /home/hatch/workspace/atlas/data/atlas.db |
| 07 Coordinator decision-making | PASS | decide pass logged 4 new decisions |
| 08 Decision logging | PASS | 5 recent decisions, all with reasons; latest: throttle-background-work |
| 09 Emergency stop | PASS | stop ON in config + snapshot; mining + trading disabled; hold decision logged (45x) |
| 10 Service restart | PASS | daemon pid 2084 stopped on SIGTERM and restarted; fresh snapshot written |
| 11 Automatic recovery | PASS | recover.sh restarted the daemon after a kill; fresh snapshot written |
| 12 Deployment persistence | PASS | all essential files under ~/workspace/atlas; recovery procedure + script present; processes do not survive VM replacement by platform design — restore is via recover.sh (see docs/recovery.md) |
| 13 Resource consumption | PASS | daemon RSS 14.1 MB, lifetime CPU 2.39% |
| **14 Network connectivity** | **FAIL** | `coingecko:200, moneroocean:ERR TimeoutError, blockchain.info:ERR TimeoutError` |
| 15 Security and permission controls | PASS | no key material, no miner processes, config not world-writable, emergency stop ON, mining + trading disabled |
| 16 Memory pressure | PASS | daemon RSS 14.1 MB (< 50 MB), DB 320.0 KB (< 100 MB), host MEM 86.7% (informational only) |
| 17 Snapshot freshness | PASS | data/snapshot.json ts age 25s (< 180 s) |
| **18 API data validity** | **FAIL** | `primary endpoint(s) failed: moneroocean, blockchain.info \| coingecko: HTTP 200, gecko_says='(V3) To the Moon!' \| moneroocean: HTTP None (TimeoutError: The read operation timed out) after retry \| blockchain.info: HTTP None (TimeoutError: The read operation timed out) after retry \| mempool.space: HTTP None (TimeoutError: The read operation timed out) after retry (non-fatal)` |
| 19 Database write latency | PASS | rolled-back test write 4.4 ms (< 1000 ms), events rows unchanged at 102 |
| 20 Daemon health | PASS | exactly 1 daemon (pid 4555, alive); monitor.log last line 33s old: 2026-11-18T22:23:46Z cycle ts=1795040626 cpu=51.72 mem=82.89 db=ok stop=True |
| 21 CPU pressure | PASS | daemon CPU 0.0% over 3 s window (< 25%), host load 3.41/2.99/1.99 (informational only) |
| 22 Queue delays | PASS | latest metrics gap 61s (expected ~60 s), newest row 36s old |
| 23 Reward ledger hash chain | PASS | verify_chain: PASS; 0 entries, 0 settled batch(es), 0 correction(s); ledger empty — chain trivially valid, 0 entries |
| 24 Dashboard export | PASS | dashboard.json fresh (0s old), hashrate not-measured, estimate null; host-verified totals match live DB: 0 ledger entries, 0 settled batch(es), 0 user / 0 ATLAS piconero |
| 25 Admin export | — (not in my suite) | Concurrent run only: PASS — `admin.json fresh (0s old), hashrate not-measured, estimate null; earnings block == dashboard earnings; host-verified totals match live DB: 0 ledger entries, 0 settled batch(es); security counts match live SQL: 0 suspicious, 0 invalid, 0 duplicate, 0 abuse, 0 auth failures, 0 payout anomalies; no token_hash/token_salt/wallet field in file` |

- The two FAILs are the same flappy-endpoint timeouts as M7 (tests 14/18). They are **proven transient in this window**: my independent curls ~5 minutes later returned 200 on all four endpoints including mempool.space (see §6). The concurrent run's diagnostics.json embeds the same FAIL text because it ran ~22:26–22:28, still inside the stall window.
- **Suite changed mid-baseline by another Mission 8 lane:** `core/diagnostics.py` 30,681 B (mtime 17:57:05 UTC, the M7 version) → **37,974 B (mtime 22:26:10 UTC)**; the suite grew 24 → 25 tests (new `t25_admin_export`, which shells out to `python3 core/atlas_admin.py export`). New file `core/atlas_admin.py`, 31,180 B, mtime 22:25:09 UTC — it did not exist in the `core/` listing at 22:21. The 22/24 result is therefore against the *24-test* suite and the on-disk 23/25 against the *25-test* suite — do not compare either to M7's 22/24 as a regression or an improvement without noting the suite change.

## 5. Configs / safety — UNCHANGED

`config/atlas.json` — mtime **2026-11-18 04:32:36 UTC**, 808 bytes, sha256 `46d3d12c1b907c048f2876755ce0d22a01316899d894561c6f86da67bfacab26` (**identical to the M7 baseline hash**):

- `emergency_stop`: **true**
- `mining.enabled`: **false** — status `design-only`, reason "No authorization to mine on shared host infrastructure; no GPU; shared 1.5 CPU cell"; `cpu_candidate: "monero-randomx"`
- `trading.mode`: **paper-only**; `trading.enabled: false`; `eligible_capital_usd`: **0**; futures/leverage/margin/options all false; reason "No realized net mining profits exist; funding rule (Part 8) forbids any other source"
- `monitor_interval_s`: 60; `host_role`: `worker-1-bootstrap`; `version`: `0.1.0-stage2`; limits max_cpu_pct 50 / max_mem_pct 70; blockchain_apis: coingecko `verified-200`, moneroocean `verified-200`, blockchain_info `verified-200`, mempool_space `unreachable-from-this-host`.

`config/pool-rewards.json` — mtime **2026-11-18 07:35:40 UTC**, 2,788 bytes, sha256 `b01a22ad5d703765a84b3fd7daa1b3b624bdfc3b4b9ea0238d1da3e95ad13464` (**identical to the M7 baseline hash**):

- `mode`: **simulation-only**; primary pool MoneroOcean, 0% fee, `api_base https://api.moneroocean.stream`, stats endpoint `/pool/stats`
- `reward_split`: **75% users / 25% ATLAS**; referral funding from the ATLAS 25% only; integer piconero rounding
- `minimum_payout`: **unset — placeholder, not set** (`piconero: null`, `xmr: null`); "to be decided and authorized before any payout flow is activated"
- Safety: activation gate (no real payouts / pool connection / mining until explicitly authorized after simulation/testnet success and security testing); emergency stop honoured; "no wallet credentials, seed phrases, private keys, or wallet passwords are stored anywhere in this config or in ATLAS"
- Fallbacks: SupportXMR 0.6% fee, P2Pool 0% fee.

Both mtimes predate the Mission 7 baseline and every value matches the Mission 7 baseline record verbatim — **UNCHANGED**. Not edited by this lane. `docs/master-mission8-design.md` (46,719 B, mtime 22:21 UTC) was already present at baseline start.

Safety (measured 22:22–22:30):

- **Miner processes: NONE.** `ps aux | grep -iE 'xmrig|randomx|miner|cpuminer|ethminer'` returned nothing.
- **Pool-port connections: NONE.** `ss -tn` showed an empty connection table (header only); no connections on 3333/4444/5555/7777/14444/10128/3334.
- **Key/seed/password files: NONE in the workspace.** `find` for `*seed*`, `*private*key*`, `*.pem`, `*.key`, `*password*`, `*secret*`, `*mnemonic*`, `*wallet*` returned no files.

## 6. Endpoints (curl, 20 s timeout, 22:29:28–22:29:32 UTC)

| Endpoint | Result | Latency |
|---|---|---|
| `https://api.coingecko.com/api/v3/ping` | **200**, body `{"gecko_says":"(V3) To the Moon!"}` (34 B) | 0.86 s |
| `https://api.moneroocean.stream/pool/stats` | **200** (12,225 B), `hashRate 261,423,325.23 H/s, miners 4904, lastBlockFound 3809325` | 1.29 s |
| `https://blockchain.info/q/latesthash` | **200** (64 B), `00000000000000000001199a1f9fa4bbf98cfa1f07cdde38fe99d7b5113ebba7` | 0.94 s |
| `https://mempool.space/api/v1/fees/recommended` | **200** (74 B), `{"fastestFee":1,"halfHourFee":1,"hourFee":1,"economyFee":1,"minimumFee":1}` | 0.64 s |

- DNS is NOT the cause: Cloudflare DoH resolves `api.moneroocean.stream` → 104.21.39.74, 172.67.143.168 (`Status: 0`).
- **Interpretation, stated plainly:** this is flapping, not a settled outage — the evidence inside ~7 minutes points both ways: (a) my diagnostics run ~22:23 records MoneroOcean + blockchain.info `TimeoutError` after retry; (b) the concurrent lane's run ~22:27 records the identical timeouts; (c) my curls at 22:29:28–22:29:32 return 200 on all four, with MoneroOcean live at 261,423,325 H/s / 4904 miners; (d) the coordinator's last successful poll was 22:21:09 (pool_stats row 43, 259,064,041 H/s, 4916 miners). **mempool.space is now observed reachable (200)** — the first 200 in this baseline series (M7 curls: 000; config still says `unreachable-from-this-host`). That config claim is stale as a live measurement, though it was a recorded claim, not a live one; the admin export says the same ("recorded claim, not a live measurement"). Do not treat any endpoint as settled down or up on one observation.
- `xmrPriceUsd`: not measured live by this lane (CoinGecko ping only returns `gecko_says`).

## 7. Artifact mirror state — NOT VERIFIED BY THIS LANE (no artifact tools available)

- **This subagent has no artifact tools** (no artifact namespace in its tool list), so the live build of slug `atlas-command-center` and the live `getMining` summary could not be read directly. The host side of the mirror (batches/entries/totals all 0, §3/§8) is unchanged from M7. **A lane with artifact access must re-read the live artifact before treating the mirror as current**, and must now also check whether the new admin export (§8) is ingested/rendered. The Mission 6 known gap is carried: the rendered reward display is self-contradictory (shows settled sim batch `sim-batch-test-1`, 1 XMR) while the isolated DB holds 0 batches/0 entries — fix still needs a repair-authorized inspection, NOT authorized in this lane.

## 8. Data files

| File | mtime (UTC) | `exported_at` / freshness at check |
|---|---|---|
| `data/coordinator.json` (1,133 B) | 22:21:11 | `exported_at` **1795040471** (= 22:21:11 UTC); ~8 min old at the 22:29 read. Mode simulation-only; emergency_stop true; mining_enabled false; pool_connected false ("No pool connection authorized — read-only /pool/stats polling only"); workers total/active 0; shares pool_accepted 0; **hashrate status `not-measured`, measured_hps null** ("Gate 1 unmeasured — no probe measurement exists"); sessions_active 0; `last_decision_id` **293**; `last_coordinator_pass_at` 1795040470; pool_stats_latest 259,064,041 H/s, 4916 miners, height 3809325, block_reward 600,000,000,000 piconero, fee 0 bps. Note: `last_decision_id` 293 lags the live DB (301 at 22:29, 305 at 22:30:31) — the export refreshes only on the 10-minute coordinator pass, by design (M6 carried item 6). |
| `data/rewards.json` (921 B) | 22:21:11 | `exported_at` **1795040471**. Mode simulation-only; emergency_stop true; split 75/25, referral 500 bps; **totals all 0** (user/referral/ATLAS/fees/payouts/reversals piconero 0; ledger_entries 0; batches open/settled/held 0); balances `{}`; batches `[]`; ledger `[]`; chain `{ok: true, entries: 0, batches: 0, "ledger empty — chain trivially valid, 0 entries"}`. |
| `data/dashboard.json` (1,873 B) | 22:28:27 | `exported_at` **1795040907** — re-exported by the concurrent lane's diagnostics run (test 24). Mode simulation-only; emergency_stop true; hashrate `not-measured`, current/average hps null ("Gate 1 unmeasured"); shares all 0; duration total_session_seconds 0, active_sessions 0; workers all 0; earnings estimated_piconero null ("Cannot estimate — hashrate not measured"), confirmed_piconero 0 ("SIMULATION ONLY — no pool rewards"); balances `{}`; lifetime totals all 0; payouts count 0, rows `[]`; efficiency acceptance_rate null ("Not measurable — no shares yet"); sync block `stale: false`; host_verified_totals: ledger_entries 0, batches_settled 0, user/ATLAS rewards 0. |
| `data/admin.json` (28,259 B) | **22:28:27 — NEW, did not exist at baseline start** | `exported_at` **1795040907**. Created mid-baseline by another Mission 8 lane (`core/atlas_admin.py`, §4). Mode simulation-only; emergency_stop true; scope: "Admin view — aggregates and operational data only. No login exists yet — this section is not access-controlled." Sections, verbatim key facts: **network** — users 0, workers all 0, worker_rows `[]`, hashrate `not-measured` (Gate 1), shares all 0, monitoring_uptime 65014 s ("0d 18h 3m", metrics_first_ts 1794975856, metrics_last_ts 1795040870, metrics_rows 1112), **daemon_restarts_24h 104, daemon_restarts_all_time 104**, daemon_uptime null ("Daemon start time is not recorded"); **mining** — earnings estimated null / confirmed 0, xmr_mined/pending/user_allocations/referral/atlas_revenue/pool_fees/payout_volume all 0 piconero, payouts_count 0, failed_payouts 0, batches 0/0/0, balances `{}`, lifetime totals all 0, host_verified_totals all 0; **infrastructure** — resources latest_ts 1795040870: cpu 50.64, mem_used_pct 85.68, disk_used_pct 18.94, load 4.26/3.54/2.39, net rx 181469 / tx 295707, stale false, memory_note **"Above the 70% cap"**; db_health integrity_check ok, user_version 3, table_counts {users 0, workers 0, shares 0, sessions 0, ledger 0, reward_batches 0, payouts 0, pool_stats 43, decisions 301, events 104, metrics 1112}; queues null ("No queue system exists — the coordinator runs synchronously in the 10-minute pass"); connectivity pool_stats_latest row 43, diagnostics_ts 1795040662 with test 14/18 FAIL text verbatim from MY diagnostics run, endpoints {coingecko 200/200, moneroocean ERR/None, blockchain.info ERR/None, mempool.space None}, blockchain_apis "recorded claim, not a live measurement"; services {daemon Running snapshot_age_s 37, coordinator_pass last 1795040470 age_s 437, watchdog Running last line "2026-11-18T22:27:45Z watchdog PASS daemon pid 5212, snapshot 51s old" age_s 42}; **security** — suspicious_workers 0, invalid_shares 0, duplicate_shares 0, account_abuse 0, auth_failures 0, payout_anomalies 0, every empty_state "No events recorded"; **logs** — decisions total 301, window 50, dept_counts {scheduler 5, trading 5, mining 5, core 5, coordinator 30}, rows ids 301–252; events total 104, window 50, kind_counts {startup 50}, rows ids 104–55; **sync** {coordinator_exported_at 1795040471, rewards_exported_at 1795040471, dashboard_exported_at 1795040906, diagnostics_exported_at 1795040662, admin_exported_at 1795040907, stale false}; **provenance** {network "RECORDED (coordinator.json + dashboard.json)", mining "DERIVED (host) — ledger SUMs, SIMULATION-tagged", infrastructure "RECORDED (latest metrics row, PRAGMA, pool_stats, diagnostics.json, snapshot.json, watchdog log)", security "DERIVED (host) — design §4 definitions", logs "RECORDED (decisions / events latest-50 window)"}. No `token_hash`/`token_salt`/`wallet` field in the file (per test 25's own check). One verbatim inconsistency, flagged not fixed: both logs windows carry the note "Showing latest 20 of 50 mirrored rows — 301 total on host" / "— 104 total on host" while 50 rows are actually listed in each (ids 301–252 and 104–55). |
| `data/diagnostics.json` (5,225 B) | 22:28:27 | `ts` **1795040907**; 23 PASS / 2 FAIL (of 25) — the concurrent lane's run, not mine (see §4). |
| `data/snapshot.json` (381 B) | 22:30:30 | `ts` **1795041029**; age 2 s at 22:30:31 read (see §2). |
| `data/atlas.db` | 22:30:30 | 331,776 B (see §3). |
| `data/recover.lock` | 22:30:28 | 0 bytes (touched by the 22:30:28 recover run). |

## 9. Anomalies (recorded, not smoothed)

1. **Endpoints flapping (diagnostics FAIL 14 + 18 in two runs, confirmed all-200 by independent curl minutes later).** MoneroOcean, blockchain.info (and mempool.space) timed out in my run ~22:23 and in the concurrent run ~22:27, while CoinGecko answered 200 both times, DNS resolves, and my curls at 22:29:28–22:29:32 returned 200 on all four (MoneroOcean 1.29 s, mempool.space 0.64 s). Not a settled outage; not a config defect. Verifiers should re-probe before treating any endpoint as down — and note mempool.space is now observed reachable, contradicting the config's `unreachable-from-this-host` claim as a live measurement.
2. **Platform VM/runtime restart at ~21:58 UTC, pre-baseline (second of the day; M7 had one ~18:00 UTC).** `logs/monitor.log.1` ends 21:58:00; watchdog line `2026-11-18T22:04:11Z watchdog FIXED daemon was down (snapshot stale 281s, last write 21:58Z); recover.sh restarted it, pid 2084, snapshot fresh (age 7.1s at 22:03:49Z)`; `uptime` at 22:22 read 24 min (boot ~21:58). Daemon was DOWN ~21:58–22:02:41 (~4.5 min) and was auto-restarted by the existing `recover.sh` cron at 22:02:41 (pid 2084); snapshot fresh again by 22:02:42. No action by this lane. Note for verifiers: the M7 baseline's pid 1887 is long gone; the daemon at this baseline's start was pid 2084 and at its end pid 5773.
3. **Diagnostics suite + admin export built mid-baseline by another Mission 8 lane.** `core/diagnostics.py` mtime 22:26:10 UTC (during my baseline window); suite grew 24 → 25 tests (new test 25 "Admin export", PASS in the concurrent run); new `core/atlas_admin.py` (22:25:09 UTC, 31,180 B); `data/admin.json` appeared at 22:28:27 (28,259 B). The on-disk `data/diagnostics.json` is the concurrent lane's 23/25 run, not mine — my 22/24 result survives only in `/tmp/m8-diag-run1.txt`. Also `logs/refresh-attempts.log` shows other lanes' watchdog/refresh activity throughout the window (e.g. `22:22:48 watchdog PASS daemon pid 4525 snapshot fresh`, `22:27:45 watchdog PASS daemon pid 5212, snapshot 51s old`) — concurrent-lane activity, not mine.
4. **Daemon churn: five pids inside ~8 minutes, and 104 restarts in 24 h.** 2084 → 4525 → 4555 (my run) → 5212 (concurrent run) → 5773 (third run starting 22:30:28). Unlike M7, most restarts now have a logged cause (diagnostics tests 10/11 by three separate lanes, plus recover.sh after the VM restart) — but the 22:30:28 restart's trigger was not yet logged at write time, and `data/admin.json` reports `daemon_restarts_24h: 104`. The churn rate itself is unchanged in kind from M7's "restarts of undetermined cause" gap; only the per-restart explanations improved.
5. **Refresh failure carried — last observed 21:53:44 UTC (pre-baseline).** `logs/refresh-attempts.log`: `2026-11-18T21:53:44Z command-center-refresh FIXED button refreshatlasdata started 21:53:44Z but stayed state=started landedTs=null after 2x60s; fallback ingestsnapshot ts=1795038960 snapshotId=54 landed; dashboard snapshot 1795035176 -> 1795038960 age ~35s`. Same pattern at 20:56:18 (snapshotId 52). No refresh-failure entry during my baseline window 22:22–22:30; the host snapshot stayed fresh throughout (age 2–50 s). The carried issue is the dashboard-side refresh, not the host snapshot.
6. **Carried gaps (unchanged from Mission 7, NOT fixed by this lane):** rendered Mining-tab check not established (no artifact tools in this lane); Gate 1 hashrate still unmeasured (no probe measurement exists); refresh failure carried (anomaly 5); stale "no miner yet" copy carried (two literal strings in `Mining.tsx` per the M4 verification — host cannot verify the rendered tab); M6 finding 1 latent (reward display self-contradiction: settled sim batch `sim-batch-test-1`, 1 XMR shown while the DB holds 0 batches/0 entries; needs a repair-authorized inspection); duration wiring unverified (0 sessions exist, so `total_session_seconds` 0 / `active_sessions` 0 is trivially consistent and the wiring is unexercised); host memory above the 70% cap (79.44%–95.25% observed this window); referral rate 5% (500 bps) still a design parameter to confirm before any real-mode settlement; minimum payout still null.

## 10. Regression rule for verifiers (post-baseline state)

After this baseline, the daemon must still be exactly 1 pid (currently **5773**, started 22:30:28 by recover.sh — do not assume pid 2084 or 5212), DB integrity ok, `user_version` **3**, emergency_stop true, mining disabled, trading paper-only, configs sha256 `46d3d12c…` / `b01a22ad…` (see §5). Diagnostics: **MY run 22/24 against the 24-test suite** (FAILs 14 + 18 are the flappy-endpoint timeouts, verbatim in §4); the on-disk file is a different, later run: **23/25 against the 25-test suite** (same FAILs, new test 25 Admin export PASS). The only permitted new rows are the ones diagnostics runs, daemon cycles, and coordinator passes write (metrics/decisions/events/pool_stats); **ledger, reward_batches, reward_batch_shares, payouts, referrals, users, workers, shares, sessions, achievements must remain 0** unless Mission 8 build work explicitly writes labelled simulation rows and records the change. `data/admin.json` now exists (`exported_at` 1795040907) — verifiers should treat it as Mission 8 build output, not baseline output, and re-check its logs window-note inconsistency ("latest 20 of 50" vs 50 rows listed) with Lane E.
