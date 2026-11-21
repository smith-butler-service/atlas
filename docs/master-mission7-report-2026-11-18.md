# ATLAS MASTER MISSION 7 — USER DASHBOARD: COMPLETE (rendered check still not established)

**Verdict:** Built, deployed, and source/host/data-verified — with the rendered Mining-tab check NOT established on the current build (the same gap as Missions 4–6, now the third consecutive mission). The host module is correct and fully tested; the live ledger and mirror are honestly empty; the mismatch rule is proven in the sandbox; no fictional earnings ship. **STOP — awaiting authorization before Master Mission 8. Do not start Mission 8.**

**Mission report:** `docs/master-mission7-report-2026-11-18.md` (this file)

**Authorization:** User authorized Master Mission 7 on 2026-11-18 ~12:52 EST ("Try authorization", after being told Mission 6 was complete and Mission 7 awaited authorization).

**Artifact build:** `atlas-command-center`, build `61fac176-fd98-4e2e-af02-73ddc212757e` (previous build `8582d78e`, Mission 6).

## What was built

### Design (Lane A, read-only)

`docs/master-mission7-design.md` (912 lines). Thirteen binding decisions (D-M7-1–D-M7-13):

- **D-M7-1:** Host is the system of record; artifact tables are a read-only display mirror. Dashboard data is DERIVED from `data/coordinator.json` + `data/rewards.json` + DB queries — no new stored truth, no new host DB tables, no new artifact mirror tables (one additive derived export field, `worker_sessions_duration_seconds`, in `coordinator.json`).
- **D-M7-2/3:** Nine panels with verbatim headings, labels, and empty-state copy. Estimated earnings are null with the verbatim reason "Cannot estimate — hashrate not measured" (never from pool-wide hashrate or benchmarks); confirmed earnings are ledger SUMs, SIMULATION-tagged. Estimate and confirmed are never combined into one total.
- **D-M7-4:** Duration = SUM over desktop-agent worker sessions only (`kind='worker'`, browser-probe sessions excluded, degenerate rows 0); open sessions contribute up to the export time.
- **D-M7-5:** Efficiency = accepted/(accepted+rejected) over pool-origin shares only; denominator 0 → null with verbatim "Cannot compute — no pool shares yet", never 0% or 100%.
- **D-M7-6:** STALE when either mirror is >1h old; both mirror sync timestamps shown separately; "Not synced yet" when never synced.
- **D-M7-7 (the Mission 6 lesson):** MIRROR-MISMATCH rule — on any disagreement between mirror-derived ledger totals and host-verified export totals, the dashboard shows the HOST-VERIFIED totals plus the verbatim "Mirror mismatch — figures under investigation" note, and never silently presents mirror rows as real earnings. A ban on hardcoded figure literals is a regression test.
- **D-M7-8–D-M7-13:** Placement directly below Reward accounting, Mining tab order unchanged, no new tab, zero buttons/inputs/links/forms, no secrets mirrored, no new cron, every figure carries its provenance tag (RECORDED / DERIVED host / DERIVED mirror / UNAVAILABLE).

### Baseline (Lane B, read-only)

`docs/master-mission7-baseline.md` (21,528 B). Verdict: PASS (baseline usable) — not all-green. Daemon exactly 1 pid; snapshot fresh; DB integrity ok, `user_version` 3, all mining tables 0 except pool_stats 26→27 (routine cron poll); diagnostics 22/24 at baseline time (tests 14/18 FAIL — MoneroOcean + blockchain.info timeouts during a ~4-minute egress stall; all 200 on re-check); configs unchanged (sha256 recorded); endpoints flapping, not settled; no miner/pool-port/key evidence. Two mid-baseline incidents recorded verbatim: the endpoint stall, and a platform VM/runtime restart ~18:00 UTC that killed the lane's diagnostics exec and the daemon (auto-recovered via recover.sh at 18:02:39, pid 1887). Carried gaps unchanged.

### Host dashboard module (Lane C)

**`core/atlas_dashboard.py`** (333 lines, stdlib-only): `dashboard_status(con)` derives hashrate (always `not-measured`), shares, duration, workers, earnings (estimate always null with verbatim reason; confirmed = ledger SUM), balances, lifetime, payouts, efficiency, sync, and the host-verified totals block — reusing `coordinator_status()` and `reward_totals()`/`balances()` by import, never duplicating logic. `export_dashboard_json()` writes `data/dashboard.json` atomically (temp + `os.replace`). CLI: `status | export`.

**Wiring:** one guarded sub-step in `core/atlas_coordinator.py` `run_pass()` (+14 lines, Mission 6 pattern), placed after the rewards export so the sync block sees fresh source exports. It can never fail the pass and logs no decision of its own (verified: exactly +1 decision per pass, `coordinator-pass-complete`).

**Tests:** `core/test_atlas_dashboard.py` (352 lines, temp DBs only): **4/4 PASS** — (a) zero-state derivation with all verbatim strings + read-only proof (all table counts unchanged across status+export); (b) Mission 6 scenario-1 simulation (Alice 60 / Bob 40, Bob referred by Alice): confirmed 750,000,000,000 piconero, ATLAS retained 235,000,000,000, referral 15,000,000,000, balances Alice 465,000,000,000 / Bob 300,000,000,000, efficiency 0.6 (6 accepted / 4 rejected pool shares), duration 5,400 s, estimate still null; (c) export idempotence + atomic write; (d) `run_pass` sub-step on a temp DB, all three exports written, sync fresh.

**Diagnostics:** new test 24 ("dashboard export": file parses, `exported_at` fresh, hashrate not-measured, estimate null, host-verified totals match a fresh COUNT/SUM over the live DB). **Diagnostics 24/24 PASS** (Lane C's run; Lane E's independent run also 24/24).

**Live `data/dashboard.json`** (regenerated by the coordinator after the final doc fix, exported_at 1795027154): hashrate not-measured/nulls, shares 0/0/0/0, duration 0 s / 0 active sessions, workers 0, earnings estimated null + verbatim reason / confirmed 0 SIMULATION ONLY, balances `{}`, lifetime all 0, payouts 0 rows, efficiency null + verbatim reason, sync stale false, host_verified_totals all 0.

### Coordinator follow-up (coordinator, after Lane C — two design gaps found)

Lane C's build contradicted the binding design in two places; the coordinator fixed both directly (small, derived-only, no behaviour change beyond the design):

1. **Missing design field (D-M7-1/§1):** `worker_sessions_duration_seconds` was specified for `data/coordinator.json` but Lane C never added it. Added to `coordinator_status()` / `export_coordinator_json()` per the D-M7-4 formula (single `now` timestamp for `exported_at` and the COALESCE). Live value: 0 (0 sessions).
2. **Duration formula contradiction (D-M7-4):** Lane C counted ALL `kind='worker'` sessions — including browser-probe sessions — and gave stale open sessions 0. The design requires desktop-agent sessions only (probe marker `none:browser-probe` excluded) and open sessions contributing up to export time. Worse, Lane C's own test fixture inserted its two "worker sessions" WITH the `none:browser-probe` marker — sessions the design says must count 0 — while asserting 5,400 s. Fixed the implementation in both `atlas_coordinator.py` and `atlas_dashboard.py`, fixed the fixture to use a desktop token hash, and added probe/degenerate exclusion assertions (probe session + degenerate row now assert 0 contribution). New coordinator test `test_worker_sessions_duration_seconds` covers the full matrix (ended desktop 3,600 s; probe 0; degenerate 0; user session 0; open desktop ~600 s).
3. **Efficiency reason string:** host said "Not measurable — no shares yet"; design-verbatim UI copy is "Cannot compute — no pool shares yet". Aligned the host module and its test to the design-verbatim string (one constant + one test line).
4. **Docstring fix (Lane E finding):** `atlas_dashboard.py`'s module docstring still described the old stale-session-0 rule after the code was aligned to the design. One docstring paragraph corrected to the D-M7-4 formula; no code change.

After these fixes: **43/43 unit tests PASS** (4 dashboard + 19 coordinator + 20 rewards), diagnostics **24/24 PASS**, `data/dashboard.json` regenerated fresh.

### UI (Lane D spec + coordinator-executed artifact edit)

**Spec:** `docs/master-mission7-lane-d-ui-report-2026-11-18.md` (922 lines).

**Artifact build `61fac176`** (`atlas-command-center`): new component `client/src/UserDashboard.tsx` (`UserDashboardSection`, nine panels in design order, zero buttons/inputs/links/forms, no hardcoded displayed figures, XMR to 6 decimals from integer piconero, no fiat); `Mining.tsx` changed by import + one render line only (section directly below `RewardAccountingSection`, above Settings — tab order otherwise unchanged); `server/src/schema.ts` + additive migration `drizzle/0007_dashboard_host_totals.sql` (journal idx 6) adding the singleton `mining_dashboard_host_totals` table; `ingestRewardsState` extended to upsert the host totals row in the same transaction as batch/ledger ingest (identical totals → `upToDate`, `synced_at` untouched; missing totals → `hostTotalsMissing:true`, row untouched, never fabricated); `getMining` gains the `dashboard` block computed server-side from mirrored tables only, with `mirrorDerivedTotals`, `hostVerifiedTotals`, `mismatch` boolean + `mismatchDetails`. No new ingest action, no new cron, no new refresh step (totals ride existing refresh step 7). `RewardAccounting.tsx` untouched; Start/Stop untouched; no sim-batch rows touched; no token/session/password hash mirrored.

**One deviation from the design (documented, ordered by the task):** D-M7-1 says "no new artifact mirror tables", but M6's `ingestRewardsState` persisted rows only, never the `totals` block — without migration 0007 the binding D-M7-7 comparison has no host side to compare against. The spec records this as a minimal additive deviation (host side of D-M7-1 untouched). The builder additionally added one extra nullable column, `total_duration_seconds`, to the totals table so the duration secondary cross-check has a stored host value.

**Builder verification (sandbox):** typecheck PASS; migration 0007 validated on in-memory SQLite (singleton CHECK enforced); grep checks (zero interactive elements, zero hardcoded figure literals, verbatim strings present, no secret hashes); sandbox `getMining` returns the dashboard block with all-zero totals, estimate null + verbatim reason, efficiency null + verbatim reason, duration 0 / "No mining sessions yet", `mismatch: false`; sandbox ingest with a 1 XMR sim batch updates BOTH totals sides consistently (user 750,000,000,000 / ATLAS 250,000,000,000 pico, 2 entries, 1 settled, `mismatch: false`); sandbox mismatch proof with disagreeing totals (mirror 2 entries / 0.75 XMR vs host 0) returns `mismatch: true` with exactly the four disagreeing fields named and confirmed/available/lifetime switched to host-verified 750,000,000,000 piconero; identical re-ingest reports `upToDate:true` with neither `synced_at` advancing. All test writes stayed in the sandbox DB; durable rows unchanged (0 batches / 0 ledger entries). Desktop probe: all nine panels in order with verbatim copy, section ending directly above Settings, Mission 6 section unchanged; audit passed with no findings, no console errors, 390px deterministic checks pass. **Gap:** a phone-width capture of the Mining tab itself could not be obtained (probe viewport switch repeatedly timed out on the heavy WebGL page — pre-existing probe limitation, not a defect in the change).

### Live mirror state (coordinator's own check, `getMining`, after the build)

`dashboard` block present: all zeros, estimated null + verbatim reason, efficiency null + verbatim reason, hashrate nulls, `mismatch: false`, `mismatchDetails: []`, `hostVerifiedTotals` == `mirrorDerivedTotals` (all 0), `stale: false`, `coordinatorSyncedAt` 1795026161, `rewardsSyncedAt` 1795026181 (both fresh — the rewards mirror is no longer stale). Rewards batches `[]`, entries `[]`, totals all 0. Pool: MoneroOcean 264,024,654 H/s, miners 4,976, height 3809231. **Note:** the builder's probe screenshots showing "0.750000 XMR" and the mismatch note are sandbox-fixture state from the mismatch proof, NOT the live render — the live mirror is honestly zero with `mismatch: false`, verified by the coordinator's own live `getMining` call.

## Test evidence

| Lane / check | Result |
|---|---|
| Design (Lane A) | `docs/master-mission7-design.md`, 13 binding decisions, read-only |
| Baseline (Lane B) | `docs/master-mission7-baseline.md`, PASS (usable), diagnostics 22/24 at baseline time (network stall) |
| Host module (Lane C) | 4/4 unit tests, coordinator 18/18, rewards 20/20, diagnostics 24/24 |
| Coordinator follow-up | +1 coordinator test (duration matrix), efficiency string aligned, docstring fixed; **43/43 total, diagnostics 24/24** |
| UI build (Lane D spec + builder) | Typecheck PASS, migration 0007 validated, sandbox getMining zeros, mismatch proof PASS, desktop probe nine panels in order, audit no findings |
| Independent host verification (Lane E) | **PASS, all 9 areas** — `docs/master-mission7-verification-host.md`; daemon exactly 1 pid; DB integrity ok, user_version 3, all mining tables 0 (pool_stats 28, decisions 239, events 89, metrics 880); decisions growth exactly this lane's diagnostics run, **0 decisions matching `%dashboard%`** — dashboard wrote no ledger rows and no decisions; configs unchanged (sha256 matches baseline); every `dashboard.json` field re-derived from the DB with fresh SQL and matched; 43/43 suites unmodified; diagnostics 24/24 (endpoints all 200 this run); sub-step guarded, temp-DB `run_pass` decisions exactly +1; duration formula verified with fixtures on a temp DB (3,600+900 closed, 300 open, 7,200 probe, 3,600 user, 1 degenerate → **4,800 s from both coordinator and dashboard**, probe/user/degenerate excluded) |
| Independent artifact inspection (repair_authorized=false, inspection `6aed8aee`) | **Implementation verified, render unverified — confidence undetermined.** Source placement verified (`RewardAccountingSection` → `UserDashboardSection` → `SettingsSection`, build `61fac176`, fingerprint `79760593…`); nine panels in order; zero interactive elements; no hardcoded figures; verbatim null reasons; isolated tables all zero; host-totals row all zero (synced_at 1795026181); mismatch false by code trace; mirrors fresh (~12 min old at capture). **Not verified:** no Mining-tab render capture exists in the evidence bundle — the sole capture shows the Overview tab only — so desktop/mobile renders, 390px overflow for this section, Mining-tab console errors, reload persistence, and live render-vs-`getMining` agreement are unproven (the captured zero console errors / zero overflow belong to the Overview tab). Also noted: captured state shows a failed refresh ("Refresh could not start: Web artifact inference failed."); Panel 1 "0 users" counts ledger users while one scaffold `local-user` row exists; when mismatch is false the confirmed-figure tag reads "Derived host". |

## Safety verification (final)

- emergency_stop **true**; mining.enabled **false** (design-only); trading.mode **paper-only**, eligible capital **$0**; pool-rewards **simulation-only**, minimum payout still null.
- Exactly one daemon, snapshot fresh, DB integrity ok, `user_version` 3.
- Diagnostics **24/24 PASS** (coordinator's run after the final doc fix; Lane E's independent run also 24/24).
- Nothing mined, traded, spent, or created; no wallets or keys; no config change; emergency stop never lifted; no pool connection for earning; no share submitted; no payout attempted; no worker active.
- No seed phrase, private key, wallet password, or recovery credential is requested or stored anywhere. No token/session/password hash is mirrored or displayed.
- Start/Stop remain hard-disabled with no handler. The live ledger holds 0 rows; the durable artifact mirror holds 0 reward batches and 0 ledger entries; the host-totals singleton row is all zeros.

## Files changed

- Host: `docs/master-mission7-design.md`, `docs/master-mission7-baseline.md`, `docs/master-mission7-lane-d-ui-report-2026-11-18.md`, `docs/master-mission7-verification-host.md`, `core/atlas_dashboard.py` (333 lines), `core/test_atlas_dashboard.py` (352 lines), `core/atlas_coordinator.py` (guarded dashboard sub-step + `worker_sessions_duration_seconds` field), `core/test_atlas_coordinator.py` (+1 duration test), `core/diagnostics.py` (test 24), `data/dashboard.json`, `data/coordinator.json` (new derived field). No config files changed. No daemon changes. No new cron.
- Artifact (`atlas-command-center`, build `61fac176`): `client/src/UserDashboard.tsx` (new), `client/src/Mining.tsx` (import + one render line), `server/src/schema.ts` (totals table), `drizzle/0007_dashboard_host_totals.sql` (new migration + journal idx 6), `server/src/actions.ts` (`ingestRewardsState` totals upsert + `getMining` dashboard block). Artifact tables: `mining_dashboard_host_totals` 1 row (all zeros), `mining_reward_batches` 0 rows, `mining_ledger` 0 rows.

## Deviations (documented)

- **D-M7-1 deviation (ordered by the task):** migration 0007 adds one new artifact mirror table (`mining_dashboard_host_totals`) because the binding D-M7-7 comparison needs a stored host side. Host side of D-M7-1 untouched (no new host tables).
- **Builder addition:** the totals table carries one extra nullable column, `total_duration_seconds`, so the duration secondary cross-check has a stored host value. Its population path (whether `ingestRewardsState` fills it from `coordinator.json`'s `worker_sessions_duration_seconds`) was NOT independently verified — the check is dormant at 0 sessions and its wiring is an open verification item, not a proven behaviour.
- **Lane C duration/efficiency deviations (found and fixed by the coordinator, see above):** probe sessions counted toward duration; stale open sessions given 0; test fixture used probe-marker sessions; efficiency reason string differed from the design-verbatim copy. All corrected and re-tested; no deviation remains in the shipped code.
- **Design-framing note:** Lane A's design §1 lists `worker_sessions_duration_seconds` as a coordinator.json field; Lane C did not build it and the coordinator added it as follow-up. The field is now present and verified (live value 0).

## Unresolved findings (honest — do not present as verified)

1. **Rendered Mining-tab check NOT established on the current build (the M6-owed captures, still owed — now the third consecutive mission with this gap).** No captured render ever selects the Mining tab on build `61fac176`; the builder's desktop probe screenshots show the sandbox mismatch fixture, and the independent inspection's only capture shows Overview. Desktop 1440px + mobile 390px renders of the User dashboard section, 390px overflow for this section, Mining-tab console errors, and reload persistence are all unproven. The section's rendering is inferred from source + data + the builder's sandbox probe — plausible, not proven. A repair-authorized Mining-tab render capture (select Mining, capture desktop + mobile, console, overflow, then reload + re-select Mining) is owed.
2. **Gate 1 still unmeasured** — every hashrate reads "not measured". A fresh interactive probe run is owed.
3. **Refresh failure carried** (Mission 3 finding 1, NOT fixed). The independent inspection captured a failed refresh in state ("Refresh could not start: Web artifact inference failed."). The dashboard labels stale mirrors rather than presenting them as fresh, but a failed refresh still stalls the mirror.
4. **Stale "no miner yet" copy carried** (Mission 4 finding 4, NOT fixed) — exactly two strings in `Mining.tsx`. Repair needs a repair-authorized inspection.
5. **Mission 6 finding 1 is latent, not repaired.** The hardcoded zero literals in `RewardAccounting.tsx` are still there, and the M6 self-contradiction's shape (mirror rows disagreeing with host totals) is now *detected* by the dashboard's mismatch rule but the underlying display defect is NOT fixed — repair still needs a repair-authorized inspection. It does not bite today: the live mirror and live host totals are both 0, and the coordinator's live `getMining` check confirms `mismatch: false`.
6. **Duration secondary check wiring not independently verified** (see Deviations). Dormant at 0 sessions; verify the population path before any session exists.
7. **Panel 1 "0 users" wording tension (minor, source-level):** the dashboard counts distinct user_ids on mirrored ledger entries (0), while `mining_users` holds 1 scaffold row (`local-user`, no wallet). The inspection flags it as probably intentional, not a defect — a wording decision is owed, not a repair.
8. **"Derived host" tag wording (minor):** when mismatch is false the confirmed-figure tag reads "Derived host"; the inspection notes it may confuse. Same standing as finding 7.
9. **SupportXMR fallback not implemented** (D-M5-3, carried) — no verified stats-API URL; a URL must never be guessed.
10. **Referral rate 5% is a design parameter to confirm** before any real-mode settlement (engine defaults to 500 bps; `referral_rate_bps` absent from `pool-rewards.json`).
11. **Minimum payout still null/placeholder** — undecided, needed before any payout flow.
12. **D-M5-1 (carried):** browser-probe `session_token_hash` stores marker `none:browser-probe` instead of NULL. Confirmed in code; no live row to inspect (sessions 0).
13. **Host memory 78–89% above the 70% cap** (standing, pre-existing). Re-scope proposal still needs user approval.
14. **mempool.space disputed, not settled.** 000 (timeout) on some attempts, 200 on others. Flappy.
15. **Daemon restarts of undetermined cause** (carried). Watchdog restarts continue (overnight pid churn; a VM/runtime restart ~18:00 UTC mid-mission killed a lane exec; daemon auto-recovered). Single instance maintained; not a stop condition.
16. **DB file growth, partly unexplained (carried).** The pre-Mission 2 jump (36,864 → 163,840 B) remains unexplained at page level.
17. **Baseline diagnostics were 22/24** (tests 14/18 network FAILs during the egress stall) while Lane C's and Lane E's runs were 24/24. The suite is sensitive to endpoint flapping; a 22/24 with only 14/18 failing is the known stall signature, not a regression — but it must not be compared to M6's 23/23 as a regression either (the suite grew 23→24 tests in this mission).

## Authorization needed before proceeding

- Building Master Mission 8 (admin command center) and any later master mission.
- A repair-authorized Mining-tab render capture on build `61fac176` (finding 1) — capture only, no code/data changes; plus the reload-persistence check on desktop + mobile.
- Repairing the Mission 6 self-contradictory reward display (finding 5) — needs a repair-authorized inspection (`artifact.inspect` with `repair_authorized: true`); NOT authorized by this report.
- Repairing the stale "no miner yet" strings (finding 4) and the refresh defects (finding 3) — each needs a repair-authorized inspection.
- Verifying the duration secondary check wiring (finding 6) before any mining session exists.
- Deciding the Panel 1 "0 users" wording and the "Derived host" tag (findings 7–8).
- Connecting to a real pool for earning, submitting shares (Gate 2), or attempting a real payout (Gate 4) — each needs separate explicit authorization; Gate 4 additionally needs successful security testing and a treasury design (none exists).
- Confirming the referral rate (5%) before any real-mode settlement; deciding the minimum payout; the SupportXMR stats-API URL (verified, never guessed).
- Any external hosting, rental, or purchase; any wallet or key creation; the treasury design; real payouts; activating mining, lifting the emergency stop, or changing any safety setting; any spending.

**STOP — Mission 7 complete. Awaiting authorization before Master Mission 8. Do not start Mission 8.**

artifact_completion_card_widget_id: web-artifact-build-completed-61fac176-fd98-4e2e-af02-73ddc212757e
