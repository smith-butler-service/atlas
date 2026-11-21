# ATLAS Master Mission 8 — Host Verification (Lane E, independent)

- **Lane:** E (independent host verification) — read-only except running the
  existing test suites and diagnostics (the established method). No host file,
  config, or database row was edited; the artifact was not touched.
- **Verification window:** 2026-11-18 22:48–22:53 UTC (17:48–17:53 EST).
- **Verifier note:** nothing from Lane C was taken on trust. Every
  `data/admin.json` field was re-derived from the live DB with fresh SQL,
  as-of the export's `exported_at` (1795041656 for the field-by-field check;
  the export was then re-issued by my own diagnostics run at 1795042267 and
  re-checked against live counts). Temp-DB checks used fresh copies in `/tmp`
  only, built from `backups/atlas-2026-11-18-pre-mission5.db` + the Stage 1/2
  migrations (the same fixture pattern as `core/test_atlas_admin.py`).
- **Overall verdict: PASS — 9/9 areas pass, zero mismatches, zero defects.**
  One safe-direction observation (redaction over-redacts hyphenated ids) and
  one wording verdict (see below); neither is a defect.

## Summary

| Area | Verdict | Headline evidence |
|---|---|---|
| 1. Daemon | PASS | Exactly 1 pid at every check (5773, then 10039 after my diagnostics run's by-design restarts); snapshot fresh (age 2–46 s) |
| 2. DB integrity | PASS | `integrity_check` ok, `user_version` 3; all mining tables 0; pool_stats 45, decisions 314, events 108, metrics 1139 at close |
| 3. No writes by admin module | PASS | 0 decisions matching `%admin%`; decisions +9 since baseline end fully explained (see §3); ledger / reward_batches 0 |
| 4. Configs unchanged | PASS | sha256 `46d3d12c…` / `b01a22ad…` — exact match to baseline |
| 5. Re-derive every admin.json field | PASS | All fields match fresh SQL as-of `exported_at`; 0 mismatches (full table in §5) |
| 6. Earnings identity | PASS | Admin earnings block byte-identical in value to fresh dashboard earnings (estimate null + verbatim reason, confirmed 0 SIMULATION ONLY) |
| 7. Full test suites + diagnostics | PASS | 48/48 unit tests (19+20+4+5); diagnostics **25/25 PASS** on my run — no 14/18 flapping this time |
| 8. Coordinator sub-step guarded | PASS | Temp-DB `run_pass`: decisions exactly +1 (`coordinator-pass-complete`); all four exports written fresh (age 0 s) |
| 9. Formula checks (temp DB) | PASS | Pending = SUM(gross) over open/held (1.5 XMR fixture); duration matrix exact (4200 s); redaction works, rows still counted; 0 secret-term hits in admin.json |

## 1. Daemon — PASS

- `pgrep -c -f 'atlas_[m]onitor.py'` = **1** at 22:48:59 UTC: pid **5773**
  (`python3 core/atlas_monitor.py`), the same pid as the baseline end.
- During my diagnostics run (tests 10/11 restart the daemon by design):
  5773 → **10039**; final check 22:52:40 UTC: exactly 1 pid, 10039.
- `data/snapshot.json` fresh throughout: ts 1795042115 (age ~24 s) at 22:48:59;
  ts 1795042314 (age ~26 s) at 22:52:40. Fields unchanged in kind:
  `mining: "disabled"`, `trading: "disabled-paper-only"`,
  `emergency_stop: true`, `gpu: null`. Memory 76.75–87.47% used (above the
  70% cap — standing issue, not new).

## 2. DB integrity — PASS

Read-only (`mode=ro`) checks at 22:48 and 22:52 UTC:

| Check | 22:48 | 22:52 (close) |
|---|---|---|
| `PRAGMA integrity_check` | ok | ok |
| `PRAGMA user_version` | 3 | 3 |
| users / workers / shares / sessions | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| ledger / reward_batches / reward_batch_shares | 0 / 0 / 0 | 0 / 0 / 0 |
| payouts / referrals / achievements | 0 / 0 / 0 | 0 / 0 / 0 |
| pool_stats | 44 | 45 |
| decisions | 308 | 314 |
| events | 106 | 108 |
| metrics | 1134 | 1139 |

- Metrics span at 22:48: MIN 1794975856, MAX 1795042115, span 66,259 s,
  1,134 rows. Latest row (1795042115): CPU 77.45, mem 87.47%, load
  4.49/3.07/2.85, disk 18.95%.
- Latest `pool_stats` row 44 at 22:48: MoneroOcean, recorded_at 1795041655,
  hashrate 267,944,116 H/s, miners 4,904, height 3,809,325.
- No miner processes (`xmrig|randomx|miner|cpuminer` grep: 0).

## 3. No writes by the admin module — PASS

- `SELECT COUNT(*) FROM decisions WHERE decision LIKE '%admin%' OR reason
  LIKE '%admin%'` = **0**. No decision row mentions admin at all.
- `ledger` = 0 and `reward_batches` = 0 at every check (before, during, and
  after my diagnostics run and the temp-DB checks, which used `/tmp` DBs).
- Decisions growth since baseline end (305 at 22:30:31 UTC) to close (314):
  **+9, fully explained, none from the admin module:**
  - +3 — two coordinator passes before my run: id 306 `coordinator-pass-complete`
    (22:31:01, pool poll skipped) and ids 307 `pool-stats-polled` + 308
    `coordinator-pass-complete` (22:40:55/56).
  - +4 — my diagnostics run, test 07 (decide pass): ids 309–312
    (`hold-all-live-activity`, `stay-disabled`, `stay-paper-only`,
    `throttle-background-work`).
  - +2 — coordinator pass 22:50:56: ids 313 `pool-stats-polled` + 314
    `coordinator-pass-complete`.
- Events 106 → 108 = +2 `startup` events from my diagnostics run's tests
  10/11 restarts (by design). Metrics 1116 → 1139 = daemon ~60 s cycles.
  pool_stats 43 → 45 = the two coordinator polls above.
- Source check: `core/atlas_admin.py` contains no `INSERT`/`UPDATE`/`DELETE`
  and no `log_decision` call; the only `SELECT *` in the module is over
  `metrics` (line 385), never over `workers` — the worker query selects the
  five columns only (design §1.2). The coordinator's admin sub-step is
  wrapped in `try/except: pass` and logs no decision of its own
  (`core/atlas_coordinator.py` lines ~1000–1015).

## 4. Configs unchanged — PASS

```
46d3d12c1b907c048f2876755ce0d22a01316899d894561c6f86da67bfacab26  config/atlas.json
b01a22ad5d703765a84b3fd7daa1b3b624bdfc3b4b9ea0238d1da3e95ad13464  config/pool-rewards.json
```

Exact match to the baseline hashes (`46d3d12c…` / `b01a22ad…`). Mtimes
unchanged (2026-11-18 04:32:36 / 07:35:40 UTC). `emergency_stop` still true.

## 5. Re-derive every field of data/admin.json — PASS (0 mismatches)

Export under check: `exported_at` **1795041656** (22:40:56 UTC), 27,868 B.
All comparisons below are fresh SQL **as-of that timestamp** (rows with
`ts`/`recorded_at` ≤ 1795041656), because the live DB keeps growing after
export. Every field matched; there is no mismatch list because there were no
mismatches.

| Field (admin.json) | Admin value | Fresh re-derivation | Match |
|---|---|---|---|
| `exported_at` / `source_db_user_version` / `mode` / `emergency_stop` | 1795041656 / 3 / simulation-only / true | coordinator/rewards/dashboard exports all 1795041656; `user_version` 3; config | ✓ |
| `scope` | verbatim D-M8-13 line | design §8.1 verbatim | ✓ |
| network.users | 0 | `COUNT(users)` = 0 | ✓ |
| network.workers (all 7 counts) | all 0 | identical to `coordinator.json` workers and `dashboard.json` workers | ✓ |
| network.worker_rows | `[]` | `COUNT(workers)` = 0 | ✓ |
| network.hashrate | not-measured, null, Gate 1 note | identical to `coordinator.json` hashrate | ✓ |
| network.shares (4 counts) | all 0 | identical to coordinator + dashboard shares | ✓ |
| network.monitoring_uptime | 65,776 s, "0d 18h 16m", first 1794975856, last 1795041632, 1,126 rows | `MIN/MAX/MAX-MIN/COUNT FROM metrics WHERE ts<=exp` = (1794975856, 1795041632, 65776, 1126) | ✓ |
| network.daemon_restarts_24h / all_time | 106 / 106 | `COUNT(events kind='startup' AND ts>=exp-86400)` = 106; total = 106 (earliest startup ts 1794975833, inside 24 h) | ✓ |
| network.daemon_uptime | null, "Daemon start time is not recorded" | verbatim design §5 reason | ✓ |
| mining.earnings | null / verbatim reason / 0 / SIMULATION ONLY | identical to `dashboard.json` earnings (see §6) | ✓ |
| mining xmr_mined / confirmed / pending / user_allocations / referral / atlas_revenue / pool_fees / payout_volume | all 0 | `rewards.json` totals all 0; ledger 0 rows; batches 0/0/0 | ✓ |
| mining.payouts_count / failed_payouts | 0 / 0 | `COUNT(payouts)` = 0; failed = 0 | ✓ |
| mining.batches open/settled/held | 0 / 0 / 0 | `GROUP BY status` over `reward_batches` = no rows | ✓ |
| mining.balances / lifetime | `{}` / all 0 | identical to `dashboard.json` balances/lifetime | ✓ |
| mining.host_verified_totals | all 0 | identical to `dashboard.json` host_verified_totals; ledger 0, settled 0 | ✓ |
| infra.resources latest row | ts 1795041632, cpu 34.33, mem 92.32, disk 18.95, load 2.09/2.95/2.71, rx 738706 / tx 517282, stale false, "Above the 70% cap" | latest `metrics` row with `ts<=exp` — identical tuple | ✓ |
| infra.db_health | ok / 3 / counts {0,0,0,0,0,0,0,44,308,106,1126} | `integrity_check` ok, `user_version` 3; all 11 counts re-derived as-of-exp — all match | ✓ |
| infra.queues | null, verbatim "No queue system exists…" reason | design §5 verbatim | ✓ |
| infra.connectivity.pool_stats_latest | row 44 (MoneroOcean, 1795041655, 267944116, 4904, 3809325, fee 0) | latest `pool_stats` with `recorded_at<=exp` — identical | ✓ |
| infra.connectivity.diagnostics_ts / test_14 / test_18 | 1795041045; t14 and t18 strings | `diagnostics.json` ts 1795041045; t14/t18 detail strings **byte-identical** to diagnostics tests 14/18 | ✓ |
| infra.connectivity.endpoints | coingecko/moneroocean/blockchain.info 200/200; mempool.space 200 (test 18) | parsed from the same diagnostics test 14/18 details | ✓ |
| infra.connectivity.blockchain_apis | config statuses + "recorded claim, not a live measurement" | `config/atlas.json` statuses verbatim | ✓ |
| infra.services.daemon | Running, snapshot_age_s 24 | consistent: 1795041656 − 1795041632 (latest metrics/snapshot ts) = 24 | ✓ |
| infra.services.coordinator_pass | last 1795041656, last_decision_id 308, age 0 | `coordinator.json` last pass/decisions — identical | ✓ |
| infra.services.watchdog | Running, last line "2026-11-18T22:37:44Z watchdog PASS daemon pid 5773, snapshot fresh", age 192 | consistent: 1795041656 − 1795041464 (22:37:44Z) = 192 | ✓ |
| security (all 6 counts) | 0 each, "No events recorded" | §4 definitions re-run: suspended/revoked workers 0; pool-origin `accepted=0` shares 0; duplicate external_id groups 0; duplicate worker+job groups 0; `kind='abuse'` 0; `kind='auth_failure'` 0; failed payouts 0 + reversal ledger rows 0 | ✓ |
| logs.decisions | total 308, window 50, ids 308–259, dept_counts {coordinator 28, scheduler 6, trading 6, mining 5, core 5} | `COUNT(decisions)` = 308; latest-50 ids 308–259; **all 50 rows field-identical** (id/ts/dept/decision/reason); dept counts over the window recomputed — identical | ✓ |
| logs.events | total 106, window 50, ids 106–57, kind_counts {startup 50} | `COUNT(events)` = 106; latest-50 ids 106–57; **all 50 rows field-identical** (id/ts/kind/message); kind counts recomputed — identical | ✓ |
| sync | coordinator/rewards/dashboard/admin 1795041656, diagnostics 1795041045, stale false | matches the four exports' `exported_at` and diagnostics ts | ✓ |
| provenance | 5 blocks (RECORDED / DERIVED (host) / RECORDED / DERIVED (host) / RECORDED) | design §2 tags present for every panel group | ✓ |

Notes on the check:
- The export was re-issued during my diagnostics run (`exported_at`
  1795042267); the fresh export's decisions/events totals (314/108) match the
  live DB exactly at close, and its `db_health` metrics count (1138) lags the
  live count (1139) by exactly one daemon-cycle row that landed between the
  export and my read — expected, not a mismatch.
- The daemon `snapshot_age_s` (24) and watchdog `age_s` (192) cannot be
  re-observed retroactively (the snapshot/log have moved on), but both are
  arithmetically consistent with the timestamps they cite.

## 6. Earnings identity — PASS

- `admin.json` mining earnings == fresh `data/dashboard.json` earnings,
  value-identical on both exports checked (1795041656 and the post-diagnostics
  1795042267):
  `estimated_piconero: null`, reason `"Cannot estimate — hashrate not
  measured"`, `confirmed_piconero: 0`, note `"SIMULATION ONLY — no pool
  rewards"`, `mode: "simulation-only"`.
- `host_verified_totals`, `lifetime`, and `balances` are likewise identical
  between the two files on both exports.

## 7. Full test suites unmodified and passing — PASS

Run by this lane, 22:48–22:51 UTC (temp DBs only for the unit suites):

| Suite | Result |
|---|---|
| `test_atlas_coordinator` | **19/19 OK** |
| `test_reward_engine` | **20/20 OK** |
| `test_atlas_dashboard` | **4/4 OK** |
| `test_atlas_admin` | **5/5 OK** (a zero-state, b non-zero scenario, c idempotence/atomic, d run_pass sub-step, e stale metrics — the design §10 plan) |
| **Total unit** | **48/48 OK** (expected 48) |
| `core/diagnostics.py` | **25/25 PASS, 0 FAIL** (my run 22:50:48–22:51:08 UTC; test 25 Admin export PASS with the full detail string) |

- **No endpoint flapping on my run:** tests 14 and 18 both PASS
  (coingecko/moneroocean/blockchain.info 200; mempool.space 200). No re-run
  was needed — there was no FAIL to confirm as transient. The on-disk
  `diagnostics.json` before my run was a 25/25 PASS from another lane
  (ts 1795041045, tests 14/18 PASS), also with no flapping.
- "Unmodified" — stated honestly: no reference hashes for the four suites
  exist in the M7/M8 baselines to hash against. What I verified instead:
  mtimes predate Lane C's build for the three older suites
  (`test_atlas_coordinator.py` / `test_atlas_dashboard.py` 18:09 UTC,
  `test_reward_engine.py` 16:22 UTC, all Mission 7 era) while the new files
  are Lane C's (`test_atlas_admin.py`, `diagnostics.py`, `atlas_admin.py`
  22:25–22:26 UTC); all 48 tests pass with the expected counts and the
  expected test names, and the suites run against temp DBs in `/tmp` only.
  (Two pre-existing `ResourceWarning`s about unclosed files in the
  coordinator suite are cosmetic; all tests pass.)

## 8. Coordinator sub-step guarded — PASS

Independent temp-DB run (this lane's own script, `/tmp/m8_temp_checks.py`,
fresh temp DB, recent `pool_stats` row seeded so no network poll):

- Decisions before/after `run_pass`: **76 → 77, delta exactly +1**; last
  decision `coordinator-pass-complete`; ledger unchanged.
- All four exports written fresh in the temp dir, `exported_at` age **0 s**:
  `coordinator.json`, `rewards.json`, `dashboard.json`, `admin.json`
  (admin `exported_at` 1795042322, mode simulation-only).
- No file landed in the live `data/` dir from this check (live exports were
  only re-issued by my diagnostics run, §5 note).

## 9. Formula checks on a temp DB — PASS

Independent fixtures (same script, second temp DB):

**(a) Pending definition — PASS, sound.** Fixtures: open batch gross
1 XMR (fee 0 bps), held batch gross 0.5 XMR (fee 600 bps), settled batch
gross 2 XMR. Admin `pending_piconero` = **1,500,000,000,000** = SUM(gross)
over open/held only — settled excluded, exact match. Checked against the
rewards module's batch schema (`reward_batches.gross_piconero` is the
recorded amount; `fee_piconero`/`net_piconero` are computed only at settle
time — `_settle_figures`: fee from gross, net = gross − fee, then the net is
split). **The definition is sound as a gross-pending figure**, with one
disclosed caveat: pending is *gross* (pre-fee), so the eventual confirmed
total from those batches will be less than pending by the pool fee. The
admin export discloses this in `pending_note` ("Gross piconero of
open/held (unsettled) batches; contributes nothing to confirmed
earnings"). The rewards export itself carries no pending field — pending is
a Lane C admin derivation, not a rewards-module figure, and it is labelled
as gross where shown.

**(b) Duration formula — PASS.** Fixture matrix on the temp DB
(same matrix as M7), dashboard + coordinator durations agree exactly:

| Fixture | Expected | Result |
|---|---|---|
| Ended desktop worker session (created T, ended T+3600) | +3600 s | counted |
| Browser probe (`none:browser-probe`, ended T+9999) | excluded (0) | excluded |
| Degenerate ended session (ended_at < created_at) | 0 | 0 |
| User session (`kind='user'`, ended T+7777) | excluded (0) | excluded |
| Open desktop session (created now−600, unended, unexpired) | ~+600 s, active | counted |
| **Total** | **~4200 s, active 1** | **4200 s, active_sessions 1; coordinator `worker_sessions_duration_seconds` = 4200, identical** |

**(c) Redaction — PASS.** On the temp DB:
- Decision reason containing a fake token string
  (`login failed token=abcdef0123456789…`) → replaced with the verbatim
  `"[redacted — possible credential]"`; row still counted (decisions total
  80 = live DB count including the fixture rows).
- Event message containing a 32-char hex run not matching any known id →
  redacted; row still counted (events total 45 = DB count).
- Control 1: a decision reason containing a known pool `external_id` that
  is a single uninterrupted 32-hex run → shown **verbatim, not redacted**
  (the known-id exception works for the realistic pool-id shape).
- Control 2: an ordinary reason ("pool poll ok, 0 shares accepted") →
  shown verbatim.

**(d) Secret grep — PASS.** `grep` over the live `data/admin.json` and over
the temp-DB export: `token_hash` 0, `token_salt` 0, `wallet` 0, `password` 0,
`seed` 0, `private_key` 0.

**Observation (not a defect):** the known-id exception compares the
20+-character run against the *whole* `external_id`/`job_id` string, so a
hyphenated id whose 20+ segment is only part of the id (e.g.
`ext-abcdefghijklmnopqrstuv`) is still redacted. That is over-redaction in
the safe direction — it hides a benign identifier rather than leaking a
credential — and no such hyphenated long id occurs in this codebase's real
pool-id shapes (all observed ids are single runs or short segments). Lane C's
own test only exercises the exception with a short id (`pool:dup-001`,
no 20+ run), so the exception's long-run path was verified by this lane,
not by Lane C's suite.

## Wording question — the logs window_note: NOT a defect

**Verdict: correct, not a defect.** The note
`"Showing latest 20 of 50 mirrored rows — N total on host"` is the section's
**display** copy, verbatim from design §8.2 (and §1.1): the artifact
*displays* the latest 20 rows of each log. The host export carries the
**50-row ingest window** the mirror ingests (ids 308–259 and 106–57,
verified field-identical above). "20 of 50 mirrored rows" describes the
display window (20 shown out of the 50 mirrored), not the export's row
count — the export is the host source for the mirror, not the display.
The note is therefore accurate as written; changing it would contradict the
binding design copy. No change owed.

## Files and evidence

- This report: `~/workspace/atlas/docs/master-mission8-verification-host.md`
- Check scripts (scratch, not part of the repo): `/tmp/m8_verify.py`,
  `/tmp/m8_temp_checks.py`, `/tmp/m8_redact2.py`
- Live state at close (22:52:40 UTC): daemon pid 10039 (exactly 1);
  `data/admin.json` + `data/dashboard.json` `exported_at` 1795042267
  (re-issued by my diagnostics run); decisions 314, events 108, metrics
  1139, pool_stats 45; ledger/reward_batches/payouts/users/workers/shares/
  sessions all 0; configs sha256 unchanged; emergency_stop true.
