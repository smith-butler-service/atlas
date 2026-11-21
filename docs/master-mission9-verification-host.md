# ATLAS Master Mission 9 — Host Verification (Lane E, independent)

- **Lane:** E (independent host verification) — read-only except running the
  existing test suites and diagnostics (the established method) and temp-DB
  checks in `/tmp`. No host file, config, or database row was edited; the
  artifact was not touched.
- **Verification window:** 2026-11-19 02:48–02:50 UTC (2026-11-18 21:48–21:50 EST).
- **Verifier note:** nothing from Lane C was taken on trust. Every
  `data/profitability.json` figure was re-derived from the recorded inputs
  with an independent script written from the design doc only (it does not
  import `atlas_profitability`), and every live input was re-fetched fresh
  with curl. Two exports were examined: Lane C's export (`exported_at`
  1795056354, read in full at 02:48 UTC) and the export re-issued by my own
  diagnostics run (`exported_at` 1795056561, re-derived 166/166).
- **Overall verdict: PASS — 9/9 areas pass, zero mismatches, zero defects.**
  Three cosmetic observations (export timestamp ordering, 6-decimal
  rounding of the KAS gross, RVN difficulty null) and one standing carried
  issue (host memory above the 70% cap); none is a defect.

## Summary

| Area | Verdict | Headline evidence |
|---|---|---|
| 1. Daemon | PASS | Exactly 1 pid at every check (19362, then 19944 after my diagnostics run's by-design restarts); the 21:39 dual-pid sighting did NOT recur; snapshot fresh (age 5–32 s), emergency_stop true |
| 2. DB integrity | PASS | `integrity_check` ok, `user_version` 3; all mining tables 0; pool_stats 58, decisions 383, events 126, metrics 1386 at close |
| 3. No writes by profitability module | PASS | 0 decisions matching `%profit%`/`%admin%`; decisions +4 since lane start fully explained (my diagnostics test 07); ledger / reward_batches 0 |
| 4. Configs unchanged | PASS | sha256 `46d3d12c…` / `b01a22ad…` — exact match to baseline |
| 5. Re-derive every profitability.json figure | PASS | 166/166 independent re-derivation checks, 0 fails (current export 1795056561); Lane C export 1795056354 read in full — all claimed figures match except the KAS gate, which moved 0.17% with live inputs between passes (see §5) |
| 6. Live figures vs fresh fetch | PASS | Export inputs match my fresh fetch 02:48:39–02:49:20 UTC within live movement (XMR $500.79 vs $500.82; difficulty 781,581,223,091 — exact match in the re-issued export); stale=False correct |
| 7. Full test suites + diagnostics | PASS | 59/59 unit tests (11+19+20+4+5); diagnostics **26/26 PASS** on my first run — no 14/18 flapping this time |
| 8. Coordinator sub-step guarded | PASS | Temp-DB `run_pass`: decisions exactly +1 (`coordinator-pass-complete`); all five exports written fresh (age 0 s); fallback STALE with preserved fetched_at |
| 9. Deviations + secrets + STALE semantics | PASS | All four Lane C deviations confirmed (a–d); secret grep 0 hits in live and temp exports; STALE semantics match D-M9-4/D-M9-10 |

## 1. Daemon — PASS

- `pgrep -c -f 'atlas_[m]onitor.py'` = **1** at 02:48:16 UTC: pid **19362**
  (`python3 core/atlas_monitor.py`). At lane start the snapshot was
  ts 1795056464 (age ~32 s), `mining: "disabled"`,
  `trading: "disabled-paper-only"`, `emergency_stop: true`, `gpu: null`.
- During my diagnostics run (tests 10/11 restart the daemon by design):
  19362 → **19944**; final check 02:50:21 UTC: exactly 1 pid, 19944.
- **The 21:39 dual-pid sighting (9757, 17864) did NOT recur.** Exactly 1 pid
  at every check in this window (02:48, during diagnostics, 02:50). The
  second pid in the report was transient, as suspected — not a second
  daemon.
- `data/snapshot.json` fresh throughout: ts 1795056464 at start;
  ts 1795056610 at close (age ~seconds). Memory 89.96–94.62% used (above
  the 70% cap — standing carried issue, not new).

## 2. DB integrity — PASS

Read-only (`mode=ro`) checks at 02:48 and 02:50 UTC:

| Check | 02:48 | 02:50 (close) |
|---|---|---|
| `PRAGMA integrity_check` | ok | ok |
| `PRAGMA user_version` | 3 | 3 |
| users / workers / shares / sessions | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| ledger / reward_batches / reward_batch_shares | 0 / 0 / 0 | 0 / 0 / 0 |
| payouts / referrals / achievements | 0 / 0 / 0 | 0 / 0 / 0 |
| pool_stats | 58 | 58 |
| decisions | 379 | 383 |
| events | 124 | 126 |
| metrics | 1382 | 1386 |

- Latest `pool_stats` row 58: MoneroOcean, recorded_at 1795056053,
  hashrate 282,034,550 H/s, miners 4,914, height 3,809,429.
- No miner processes (checked via the diagnostics test 15 PASS, which
  covers it).

## 3. No writes by the profitability module — PASS

- `SELECT COUNT(*) FROM decisions WHERE decision LIKE '%profit%' OR
  decision LIKE '%admin%' OR reason LIKE '%profitabilit%'` = **0**. No
  decision row mentions profitability or admin at all.
- `ledger` = 0 and `reward_batches` = 0 at every check (before, during, and
  after my diagnostics run and the temp-DB checks, which used `/tmp` DBs).
- Decisions growth since lane start (379 at 02:48:16 UTC) to close (383):
  **+4, fully explained, none from the profitability module:**
  - +4 — my diagnostics run, test 07 (decide pass): ids 380–383
    (`hold-all-live-activity`, `stay-disabled`, `stay-paper-only`,
    `no-throttle-needed`, ts 1795056547).
- Events 124 → 126 = +2 `startup` events from my diagnostics run's tests
  10/11 restarts (by design). Metrics 1382 → 1386 = daemon ~60 s cycles.
- Source check: `core/atlas_profitability.py` contains no `INSERT`,
  `UPDATE`, `DELETE`, or `log_decision` call and no `SELECT *` at all
  (the only `/api/stats` mentions are in docstrings/comments: MoneroOcean
  `/api/stats` 404s — never used — and the 2Miners `api/stats` endpoint,
  which is the correct fetch target). The fetch target constant is
  `MONERO_NETWORK_URL = "https://api.moneroocean.stream/network/stats"`.
  Imports are stdlib-only: `argparse, json, os, sqlite3, sys, time,
  urllib.error, urllib.request`. The coordinator's profitability sub-step
  (`core/atlas_coordinator.py` lines ~1014–1031) is wrapped in
  `try/except: pass`, sits directly after the admin sub-step, and logs no
  decision of its own.

## 4. Configs unchanged — PASS

```
46d3d12c1b907c048f2876755ce0d22a01316899d894561c6f86da67bfacab26  config/atlas.json
b01a22ad5d703765a84b3fd7daa1b3b624bdfc3b4b9ea0238d1da3e95ad13464  config/pool-rewards.json
```

Exact match to the baseline hashes (`46d3d12c…` / `b01a22ad…`).
`emergency_stop` still true.

## 5. Re-derive every figure of data/profitability.json — PASS (166/166, 0 fails)

Independent script `/tmp/m9_verify_rederive.py` (written from the design
§1 formula only; does not import `atlas_profitability`): reads the live
export, recomputes every panel figure, every `audit_usd` figure, every
pool-fee figure, every split figure, and every rate from the recorded
inputs, and compares within the panel rounding (6 dp for XMR/day, 1 dp
for H/W, 3 dp for ratios, 2 dp for ¢/kWh, full precision for audit USD).
Run against the current export (`exported_at` **1795056561**, re-issued by
my diagnostics run's test 26): **166 checks, 0 failures.**

Lane C's export (`exported_at` **1795056354**) was read in full before my
diagnostics run re-issued it. Its figures match Lane C's claims:

| Figure (Lane C export 1795056354) | Lane C claim | File value | Match |
|---|---|---|---|
| XMR price / difficulty / network hashrate | $500.82 / 784,521,706,195 → 6.517 GH/s | $500.82 / 782,021,032,919 → 6.517 GH/s | ✓ (difficulty moved between Lane C's read and mine; see note) |
| USD/CAD | 1.4348 | 1.4348230140803644 | ✓ |
| XMR net USD/day Tier 2 / Tier 1 / US avg | +$0.0133 / +$0.1299 / −$0.3751 | +0.0132997 / +0.1299135 / −0.3751267 | ✓ |
| XMR net XMR/day Tier 2 | +0.000027 | 0.000027 (2.7e-05) | ✓ |
| Breakeven gates Tier 2 / US avg (XMR) | 56.1 / 124.6 H/W | 56.1 / 124.6 | ✓ |
| Breakeven electricity price (XMR) | 8.09¢/kWh | 8.09 | ✓ |
| Profile 58.5 H/W, ratio 1.042, Above breakeven | as claimed | 58.5 / 1.042 / Above breakeven | ✓ |
| KAS / RVN / ERG breakeven H/W Tier 2 | 11,984.8 / 0.5 / 2.4 MH/W | 12005.4 / 0.5 / 2.4 | ✓ except KAS (see note) |
| KAS / RVN / ERG net USD/day Tier 2 | −$0.279 / −$0.340 / −$0.139 | −0.2794805 / −0.3400444 / −0.1391040 | ✓ |
| Pool fees Tier 2 (XMR/day) MoneroOcean / SupportXMR / P2Pool | 0.000027 / 0.000023 / 0.000027 | 2.7e-05 / 2.3e-05 / 2.7e-05 | ✓ |
| Split Tier 2 (XMR): user share / ATLAS share / user net | 0.000497 / 0.000166 / −0.000139 | 0.000497 / 0.000166 / −0.000139 | ✓ |
| `stale` / `not_computed` | false / [] | false / [] | ✓ |
| Your-hardware | null + verbatim reason | null, "Cannot estimate — hashrate not measured" | ✓ |
| Confirmed earnings | dashboard earnings block | identical to fresh `dashboard.json` earnings (see §6) | ✓ |

Notes on the two deltas:
- **KAS breakeven gate 12,005.4 vs Lane C's 11,984.8 (0.17%).** Lane C's
  figures are from export 1795056307; the export I read is 1795056354, a
  later coordinator pass. The KAS network hashrate moved between passes
  (2.8985e17 H/s in 1795056354); the gate is inversely proportional to it,
  so a 0.17% move is live-input movement, not an arithmetic error. The
  current export (1795056561) re-derives 166/166 from its own recorded
  inputs, which settles the arithmetic independently of either pass.
- **XMR difficulty 782,021,032,919 in 1795056354 vs Lane C's
  784,521,706,195.** Same cause: difficulty moved between Lane C's export
  (1795056307) and the pass I read (1795056354). Both are live values at
  their own fetch times; §6 confirms the direction with a fresh fetch.

Current export (1795056561) re-derived figures (for the record):
XMR net USD/day Tier 2 +$0.01349, Tier 1 +$0.13010, US avg −$0.37496;
KAS −$0.27946, RVN −$0.34002, ERG −$0.13909 (Tier 2). XMR price $500.79,
difficulty 781,581,223,091.

Other export properties verified on both exports:
- Tariff constants carry source + effective date, `fetched_at: null` on
  all four rows (HQ Tier 1/2: Hydro-Québec Rate D, 2026-04-01; US avg:
  U.S. EIA Form EIA-861 final 2025 data, 2025; proposed tariff: source
  "Proposed February 2026, pending Régie de l'énergie approval",
  effective_date null, label "Proposed tariff — not in effect").
- No USD figure in the panel payload; 0 `$` characters in the panel JSON.
- Reference profiles exactly per D-M9-5 (Ryzen 7 5800X 10,000 H/s @ 171 W;
  RTX 3060 Ti KAS 480 MH/s @ 150 W, RVN 27 MH/s @ 240 W, ERG 137 MH/s
  @ 132 W; browser laptop 200 H/s @ 45 W, desktop 850 H/s @ 50 W).
- Confirmed-earnings block reused by import (module calls
  `atlas_dashboard.dashboard_status`, never recomputes); byte-identical
  in value to the fresh dashboard earnings on both exports checked.

## 6. Live figures vs fresh fetch — PASS

Fresh curls 02:48:39–02:49:20 UTC (epoch 1795056519–1795056560), compared
against Lane C's export (1795056354, ~4–5 min old at fetch time):

| Input | Export (1795056354) | My fresh fetch | Assessment |
|---|---|---|---|
| XMR price (CoinGecko) | $500.82 | $500.79 | live movement, 0.006% |
| XMR difficulty (MoneroOcean /network/stats, key 18081) | 782,021,032,919 | 781,581,223,091 | live movement, 0.06%; the re-issued export (1795056561) records 781,581,223,091 — **exact match** to my fetch |
| XMR height | 3,809,490 | 3,809,491 | +1 block, as expected |
| USD/CAD (CoinGecko exchange_rates) | 1.4348230 | 1.4349300 | live movement, 0.007% |
| KAS price / network hashrate | $0.02705245 / 2.8985e17 | $0.0270236 / 2.9793e17 | live movement |
| RVN price / network hashrate | $0.00109782 / 5.1439e11 | $0.00109701 / 5.0343e11 | live movement, ~2% |
| ERG price / network hashrate | $0.204592 / 582,759,831,134 | $0.20459 / 582,759,831,134 | **exact match** on hashrate; price within rounding |
| KAS block reward (2Miners) | 1.94454365, live | "194454365" sompi in the raw payload | ✓ |
| RVN / ERG block reward | 1250.0 / 3.0, CARRIED | no blockReward field in either raw payload (§9a) | ✓ |

- The export's `stale=False` is correct: at my fetch the recorded inputs
  were 4–5 min old, far under the 1 h STALE threshold, and they track the
  fresh fetch within normal live movement. The export is fresh, not
  stale-but-labelled.
- Independent cross-checks from the same MoneroOcean fetch: key 8766 (RVN)
  `value` 125,000,552,000 satoshi = 1250.00552 RVN (confirms the 1,250
  carried reward); key 9053 (ERG) difficulty 67,279,622,504,447 vs the
  2Miners figure 67,279,622,504,448 (off by 1, rounding).

## 7. Full test suites unmodified and passing — PASS

Run by this lane, 02:48–02:49 UTC (temp DBs only for the unit suites):

| Suite | Result |
|---|---|
| `test_atlas_profitability` | **11/11 OK** (a Obj 4 regression, b M4 breakeven, c fees, d sensitivity flip, e stale handling, f your-hardware null, g read-only, h idempotence/atomic, i run_pass sub-step, blockReward bands, j 2Miners string payload) |
| `test_atlas_coordinator` | **19/19 OK** (confirms Lane C's note: 19 test methods, not 20) |
| `test_reward_engine` | **20/20 OK** |
| `test_atlas_dashboard` | **4/4 OK** |
| `test_atlas_admin` | **5/5 OK** |
| **Total unit** | **59/59 OK** |
| `core/diagnostics.py` | **26/26 PASS, 0 FAIL** (my run 02:49:06–02:49:26 UTC; test 26 Profitability export PASS — see below) |

- **No endpoint flapping on my run:** tests 14 and 18 both PASS
  (coingecko/moneroocean/blockchain.info 200; mempool.space 200). No
  re-run was needed — there was no FAIL to confirm as transient. The
  on-disk `diagnostics.json` before my run was Lane C's 26/26 run
  (ts 1795056566 is now mine; the pre-run file was the coordinator-pass
  era export set).
- Test 26 detail (verbatim from `data/diagnostics.json`):
  "profitability.json fresh (5s old), 81 figures re-derived from recorded
  inputs within rounding; XMR net XMR/day (Tier 2) 2.7e-05, breakeven
  56.1 H/W; your-hardware null + verbatim reason; earnings block ==
  dashboard earnings; no USD in panel; stale=False".
- "Unmodified" — stated honestly, as in M8: no reference hashes for the
  four older suites exist in the M7/M8 baselines to hash against. What I
  verified instead: all 59 tests pass with the expected counts and the
  expected test names (the profitability suite's 11 tests are exactly the
  §10 cases (a)–(i) plus the blockReward-band and 2Miners string-payload
  tests), and the suites run against temp DBs in `/tmp` only.

## 8. Coordinator sub-step guarded — PASS

Independent temp-DB run (this lane's own script, `/tmp/m9_temp_pass.py`,
fresh temp DB from `backups/atlas-2026-11-18-pre-mission5.db` + Stage 1/2
migrations, recent `pool_stats` row seeded so no network poll, HTTP layer
patched to fail so the fallback path is exercised):

- Decisions before/after `run_pass`: **76 → 77, delta exactly +1**; last
  decision `coordinator-pass-complete`; ledger 0 → 0, reward_batches
  0 → 0.
- All five exports written fresh in the temp dir, `exported_at` age **0 s**:
  `coordinator.json`, `rewards.json`, `dashboard.json`, `admin.json`,
  `profitability.json`.
- The temp profitability export is STALE (fallback from the seeded
  previous export, `fetched_at` preserved exactly), your-hardware null,
  0 secret-term hits. No file landed in the live `data/` dir from this
  check (live exports were only re-issued by my diagnostics run, §5 note).

## 9. Deviations, secrets, STALE semantics — PASS

**(a) RVN/ERG block rewards are CARRIED protocol constants — CONFIRMED.**
Raw curls of all three 2Miners `api/stats` payloads at 02:48:39 UTC:
- KAS payload contains `"blockReward":"194454365"` (sompi) in its node
  object — live, and the export records it as
  `live — 2Miners api/stats node blockReward` with `raw_block_reward`
  `"194454365"`.
- RVN payload contains **no `blockReward` substring anywhere** in the
  whole payload (node fields are only avgBlockTime, dagSize, difficulty,
  epoch, height, lastBeat, name, networkhashps). ERG payload likewise
  contains **no `blockReward` substring anywhere**. Lane C's claim is
  verified directly against the live payloads, not taken on trust.
- Each coin's export record carries `block_reward_source` stating live vs
  carried with the Obj 4 citation: RVN "CARRIED — Obj 4 §6: 1,250
  RVN/block post-halving (Jan 2026, block 4,200,000); next halving ~2030;
  2Miners node omits blockReward"; ERG "CARRIED — Obj 4 §7: 3 ERG/block
  verified on the Ergo explorer (blocks 1,919,263/4); 2Miners node omits
  blockReward". `raw_block_reward` is null for both, as expected.

**(b) 2Miners returns every numeric field as a string — CONFIRMED.**
The raw payloads show every numeric node field quoted
(`"networkhashps":"297925716228748139"`,
`"difficulty":"7089.1684"`, `"avgBlockTime":"58.69"`,
`"height":"4631765"`). The module's `_num()` / `_int_or_none()` coerce
them; the unit test (j) exercises exactly this shape and passes, and the
live export shows integer strings staying exact ints (KAS difficulty
30,274,296,942,479,743; ERG difficulty 67,279,622,504,448; heights exact).
One consequence, disclosed in Observations: RVN difficulty is null in
the export because its string is fractional ("7089.1684") and the module
records integers only — the figures use networkhashps, so nothing depends
on it.

**(c) STALE semantics — CONFIRMED as matching D-M9-4/D-M9-10, not a
deviation.** The code (`compute_profitability`) marks a coin STALE when
`status == "stale"` OR age > 3600 s, and `_normalize_staleness` re-derives
staleness from `fetched_at` at export time. D-M9-4 requires a
fallback-marked coin to be STALE with its last-fetch time; D-M9-10 adds
the > 1 h rule. A fallback record therefore counts as STALE even when
its last fetch was < 1 h ago — exactly what Lane C documented. Observed
live in my temp-DB run (§8): the seeded fallback (10 min old) produced
`stale: true` with the label "STALE — XMR network stats 10m 0s old" and
the original `fetched_at` preserved. The live export has no fallback
records, so this path is verified on temp DBs only, as in the unit tests.

**(d) Tariff constants carry source + effective date with `fetched_at:
null` — CONFIRMED.** All four tariff rows in the export's inputs block
carry `source` + `effective_date` and `fetched_at: null` (see §5). The
proposed tariff's `effective_date` is null with its label and pending-
approval source — correct, since it is not in effect.

**Secret grep — PASS.** `grep` over the live `data/profitability.json`
(and the temp-DB export): `token_hash` 0, `token_salt` 0, `wallet` 0,
`password` 0, `seed` 0, `private_key` 0.

## Observations (not defects)

1. **`exported_at` precedes the inputs' `fetched_at` by 1–5 s.** The
   module captures `now` at the start of `profitability_status`, then
   fetches; the fetches land 1–5 s later, so `exported_at` 1795056354
   sits before `fetched_at` 1795056355–59 (same in the re-issued export:
   1795056561 vs 1795056563–66). The panel's input `age_s` is therefore
   negative (−2…−5 s, displayed as "0s"). Cosmetic only: no rule requires
   `exported_at ≥ fetched_at`, staleness is computed from `fetched_at`,
   and the export is honestly fresh. A future lane could stamp
   `exported_at` after the fetch; nothing here depends on it.
2. **KAS `gross_xmr_per_day` rounds to 0.0 at 6 decimals.** True value
   ≈ 0.0000001418 XMR/day; the design mandates 6-decimal XMR/day, so the
   panel shows 0.0 while `audit_usd` carries the full-precision gross
   ($0.0000745/day). Per design, not a defect — but a reader of the panel
   alone would see KAS gross as zero.
3. **RVN `difficulty` is null in the export** (see §9b): 2Miners reports
   RVN difficulty as a fractional string ("7089.1684", different units
   from the MoneroOcean figure) and the module records integers only.
   The figures use `networkhashps`, so this has no effect on any
   computation.
4. **Host memory above the 70% cap (standing, carried):** 89.96–94.62%
   used across this window. Unchanged in kind from M7/M8/M9 baseline.
5. **Daemon churn continues (carried):** pid 19362 → 19944 in this window
   is fully explained (my diagnostics run's tests 10/11, by design); the
   21:39 dual-pid sighting did not recur (§1).

## Files and evidence

- This report: `~/workspace/atlas/docs/master-mission9-verification-host.md`
- Check scripts (scratch, not part of the repo): `/tmp/m9_verify_rederive.py`,
  `/tmp/m9_temp_pass.py`
- Live state at close (02:50:21 UTC): daemon pid 19944 (exactly 1);
  `data/profitability.json` `exported_at` 1795056561 (re-issued by my
  diagnostics run); `data/diagnostics.json` ts 1795056566, 26/26 PASS;
  decisions 383, events 126, metrics 1386, pool_stats 58;
  ledger/reward_batches/payouts/users/workers/shares/sessions all 0;
  configs sha256 unchanged; emergency_stop true.

## Sign-off

Mission 9 host verification is complete: the module implements the §1
formula exactly (166/166 independent re-derivation checks), the tests are
11/11, the diagnostics suite is 26/26, the coordinator sub-step is
guarded (+1 decision per pass), the live figures re-derive from fresh
live inputs, all four documented deviations are confirmed against live
payloads, and no decisions, ledger rows, or secrets were written. The
partial-report follow-up Lane E owed is now delivered. Mission 9's host
side is verified; Mission 10 still requires separate user authorization
and must not start on the strength of this report alone.
