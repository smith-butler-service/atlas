# ATLAS MASTER MISSION 12 — DESIGN

**Authorization:** User authorized by voice 2026-11-19 00:03 EST:
"launch mission 12." (Mission 11 STOP lifted by that order.)

**Mission report:** `docs/master-mission12-report-2026-11-18.md`
(this file's companion; design decisions D-M12-1–D-M12-6 below)

**Scope (from the task):** close the two honest gaps Mission 11
narrowed but did not close, plus the owed follow-ups that need no
new authorization:
1. Rendered Mining-tab check (8th mission unestablished).
2. Profitability mismatch-flag cause.
3. Re-ingest the Mission 11 security export (scale `run_at`
   1795064292) into the mirror.
4. Fix the scale harness spread quirk and re-run the scale battery
   at 1,000 / 100,000 to confirm the fix still holds with true
   per-worker spread.
5. Re-verify all suites + diagnostics + security battery; re-state
   the go/no-go gates with measured evidence.

## D-M12-1 — Harness spread fix (code change, host side)

**Root cause (confirmed):** `_build_synthetic_load()` in
`core/atlas_security.py` built each 500-share batch first and then
recorded it under `worker_ids[seq % n_workers]` where `seq` was
already the END of the batch. At 1,000 workers the batches landed
on workers 500 and 0 alternately; at 100 workers every batch
landed on worker 0. "1,000 workers / 100,000 shares" therefore
meant 1,000 registered workers with shares concentrated on 2 of
them (1 at the 100 level).

**Fix:** every worker gets its own equal share of the load
(`n_shares // n_workers` each, remainder to the first workers),
recorded in chunks of at most `MAX_BATCH_SHARES` (500) per worker.
`_build_synthetic_load()` now also returns `workers_with_shares`
(distinct-worker count measured from the shares table) and
`shares_per_worker`; `run_scale_tests()` stores both per level and
the L1 note now describes the spread instead of the stale "2 x
500-share batches" text. `run_scale_smoke()` exposes
`workers_with_shares` too. The scale test asserts
`workers_with_shares == 1000` (big level) and `== 100`
(100 level), `shares_per_worker == 100` at both.

**Consequence for before/after:** the Mission 11 figure (1.159 s,
86,291.1/s) was measured with 200 batches of 500; the Mission 12
figure is measured with 1,000 batches of 100 (one batched indexed
conflict query per batch). Per-batch overhead is higher, so the two
numbers are NOT the same measurement — both are reported, and the
fix is judged against the L5 limits (30 s single-step, >10,000/s),
not against the Mission 11 number. The O(n²) fix itself is
unchanged (Stage 3 index + batched conflict check, D-M11-2).

**Own-bug note (recorded, not hidden):** the first version of
this fix built each batch with a list comprehension that reused
the batch-start `seq` for every share's `external_id`, so dedupe
collapsed each 100-share batch to 1 inserted row (10 inserted of
1,000 in the spread check). Caught by the spread check itself
before any suite ran; fixed by numbering shares `seq + j` inside
the batch. The spread check (equal per-worker counts + uneven
7-worker/100-share split 15/15/14×5) now guards the helper.

## D-M12-2 — Profitability mismatch: mechanism ESTABLISHED from live data

**Mechanism (proven, not inferred):** the live `mismatch: false`
is CORRECT under the calibrated comparator installed by the
authorized Mission 9 repair (comparison calibration, R1–R4 in
`docs/master-mission9-repair-design.md`). The raw stored figures
still disagree exactly as Mission 11 reported — because those
disagreements are the four calibrated causes, and the comparator
normalizes all four before comparing:

- R1 precision: mirror rounded to the host field's display
  precision (6dp XMR/day, 1dp H/W, 3dp ratio, 2dp ¢/kWh) before
  the `max(1e-9, 1e-6·|host|)` tolerance.
- R2 units: GPU breakeven H/W ÷ 1e6 → MH/W before comparing.
- R3 null-scope: `currentHw` / `ratioTier2` / `verdictTier2`
  skipped for GPU rows (mirror null by design, host filled).
- R4 split scope: split fields compared only on the 4 host-emitted
  pairs; browser rows skipped (host null, mirror computed).

**Proof (this mission, live `getMining` figures):** applying
R1–R4 to all 6 profiles × 15 compared fields plus the 3 pool-fee
rows gives ZERO residual diffs — every compared figure agrees
exactly (diff 0.0 after rounding). Worked examples: KAS
`breakevenHwTier2` mirror 12,334,747,956 H/W ÷ 1e6 = 12,334.748
→ 12,334.7 = host; XMR `dailyCoinsNative` mirror
0.0006629512 → 0.000663 = host; GPU `currentHw` host 3.2 vs
mirror null is an R3 skip, not a disagreement.

**Why the comparator is known to run (not a default false):**
Mission 9 closed with `mismatch: true` (~100 details) on the same
figures — the comparison ran and flagged then. The flip to
`mismatch: false` happened across the authorized repair build
("do repair", artifact v19), with every figure byte-identical —
the only thing that changed was the comparator. Mission 10's
finding 2 ("cause NOT established") did not connect the flip to
that repair build; this mission does, with the numeric proof
above. The M9 defect as diagnosed (four causes) IS fixed by the
calibration; what Mission 11 called "the defect" was the raw
figure differences, which are the calibrated causes themselves.

**Residual gap (honest):** the repair design's binding regression
guard — a tampered host figure must still produce
`mismatch: true` with the field named — has no recorded
post-repair run for the profitability comparator (pre-repair
sandbox proofs passed; post-repair only the live agreement is
proven). No live tamper test was run (it would corrupt the live
mirror). Owed as a sandbox proof via a repair-authorized
inspection; proposed as a repair, NOT executed here.

## D-M12-3 — Artifact inspection sequencing

The galaxy edit build on `atlas-command-center` (agent
`892e6aff…`, later replaced by a second running edit build agent
`2c86b0c5…`) was still running when this mission started and at
every check during it. Per the standing rule, no diagnostic was
sent to an active builder and `artifact.inspect` was not retried
while a build ran. The rendered Mining-tab check and the
security-export re-ingest were therefore sequenced AFTER the
build finishes; if the build is still running at report time,
both are reported as owed, not claimed. No artifact edit was
made by this mission.

## D-M12-4 — No new schema, no config change

Mission 12 changes no schema (`user_version` stays 4), no config
(`atlas.json` / `pool-rewards.json` hashes unchanged), no
coordinator/rewards/dashboard code. Only `core/atlas_security.py`
(harness fix + spread fields + L1 note) and
`core/test_atlas_security.py` (spread assertions) change, plus
the regenerated `data/security.json` (new scale block) and
`data/diagnostics.json` (re-run). Backups of the pre-fix files:
`backups/atlas_security-2026-11-18-mission12.py`,
`backups/test_atlas_security-2026-11-18-mission12.py`.

## D-M12-5 — Gates re-stated, not re-decided

Mission 12 does not authorize Gate 1 (browser hashrate probe),
Gate 2 (real pool shares), Gate 3 (sustained run), or Gate 4
(real payout / treasury). The launch verdict is re-stated from
measured evidence only; a NO-GO on any gate stays NO-GO. No
mining, trading, wallet, payout, spend, or subscription in this
mission.

## D-M12-6 — Rollback

Harness fix rollback: restore the two backup files above and
re-run the security suite (expect the spread assertions to fail
— that failure IS the proof the old harness is back — and the
scale block to show 2 workers with shares again). No DB change
to roll back (temp DBs only; live mining tables stayed 0 rows).
