# ATLAS MASTER MISSION 11 — LAUNCH PREP: DESIGN

**Authorization:** User authorized by voice 2026-11-18 23:52 EST:
"Fix the problem then start the mission 11." The problem is the
Mission 10 L5 bottleneck (`record_shares` O(n²), 398.917 s at 1,000
workers / 100,000 shares). Mission 11 scope: fix that bottleneck
first, re-prove scale, then launch prep — final pre-launch checklist,
go/no-go gates, security re-verification, documentation, rollback
plan, and a clear list of what is NOT launch-ready.

**Mission report:** `docs/master-mission11-report-2026-11-18.md`

## Binding decisions (D-M11-1–D-M11-8)

- **D-M11-1 (fix first, then launch prep):** No launch-prep verdict
  is written until the bottleneck fix is measured. The fix must be
  proven by a re-run of the Mission 10 scale battery at the same
  1,000 workers / 100,000 shares load, plus the full regression
  (all unit suites + diagnostics). A faster micro-benchmark alone
  does not close the finding.
- **D-M11-2 (the fix):** Two parts, both required. (a) Schema: Stage
  3 migration `core/migrate_mission11_stage3.sql` — one new partial
  index `idx_shares_external_id ON shares(external_id) WHERE
  external_id IS NOT NULL`, additive only, `user_version` 3 → 4.
  The old composite UNIQUE `(worker_id, external_id)` cannot serve
  an `external_id`-only lookup (EXPLAIN QUERY PLAN: full covering
  SCAN per share). (b) Code: `record_shares()` in
  `core/atlas_coordinator.py` replaces the per-share clash query
  with ONE batched indexed lookup per batch (`WHERE external_id IN
  (...) AND worker_id != ?`), then checks the result map in batch
  order. Behaviour is identical: first conflicting `external_id` in
  batch order suspends the worker and rejects the whole batch, with
  the same decision messages; same-worker dedupe still via
  `INSERT OR IGNORE` on the composite UNIQUE index; local-test
  shares still excluded from attribution; integer-piconero
  accounting and the hash-chained ledger are untouched.
- **D-M11-3 (L5 calibration):** The scale rule's clause-2
  (super-linear ratio) additionally requires the step to consume
  more than 1.0 s at the big level. Ranking by absolute time did
  not stop a false positive: after the fix,
  `attribution_weights` was the only ratio candidate (0.002 s →
  0.032 s, 16×) and was reported as "the bottleneck" although 32 ms
  cannot bottleneck anything. Clause 1 (absolute 30 s / 60 s
  limits) remains the hard gate.
- **D-M11-4 (no launch):** Mission 11 launches NOTHING. No mining
  start, no live trading, no real payout, no wallet/key creation, no
  capital, no config change. The verdict is a checklist + go/no-go,
  not a launch. Emergency stop stays ON throughout.
- **D-M11-5 (gates are evidence, not opinion):** Each go/no-go gate
  (Gate 1 measured browser hashrate, Gate 2 real pool shares, Gate 3
  sustained run, Gate 4 real payout, Gate 5 protocol/economics) is
  reported with its measured state and the exact authorization or
  measurement still owed. An unmeasured gate is NO-GO, never
  "probably fine".
- **D-M11-6 (honest gaps, not silent fixes):** The two Mission 10
  honest gaps are NOT fixed silently. (1) Rendered Mining-tab check:
  attempt a real check; report pass/fail honestly. (2)
  Profitability `mismatch` reading `false` with no established
  cause: do NOT claim the M9 defect fixed unless the cause is found
  and proven; report the cause as established or still unknown.
- **D-M11-7 (rollback):** The fix is reversible in two steps —
  `DROP INDEX idx_shares_external_id` + `PRAGMA user_version = 3`,
  and restore the pre-fix `record_shares` loop (exact old code is
  quoted in the report). A pre-migration DB backup is taken first:
  `backups/atlas-2026-11-18-pre-mission11.db`. Post-fix file
  snapshots are kept in `backups/atlas_coordinator-2026-11-18-
  mission11.py` and `backups/atlas_security-2026-11-18-mission11.py`.
- **D-M11-8 (no new artifact build unless needed):** Mission 11
  makes no Command Center change. If the artifact is busy with an
  unrelated build, do not inspect, edit, or ingest into it while
  the build runs; record the block honestly and let the hourly
  refresh re-ingest the new security export afterwards.

## Launch-prep checklist (what Mission 11 must answer)

1. Scale after the fix (L1–L5 re-run, same load).
2. Security re-verification (S1–S9 battery + full suites +
   diagnostics 28/28).
3. Go/no-go per gate (Gates 1–5) with evidence.
4. Rollback plan (D-M11-7).
5. What is NOT launch-ready (explicit list).
6. Pre-launch documentation state (design/baseline/reports,
   `docs/recovery.md`, roadmap/GOAL bookkeeping).
7. Safety state (stop ON, simulation-only, $0 capital, 0 ledger).

## Non-goals

- No Gate 1/2/3/4 measurement (each needs its own authorization /
  hardware / treasury design).
- No profitability-mismatch repair (needs repair-authorized
  inspection + edit; NOT authorized here).
- No refresh-button repair, no "no miner yet" copy repair, no
  RewardAccounting hardcoded-zero repair (all NOT authorized).
- No new cron, no new host tables, no new artifact migration.
