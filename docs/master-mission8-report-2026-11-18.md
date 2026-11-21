# ATLAS MASTER MISSION 8 — ADMIN COMMAND CENTER: COMPLETE (rendered check still not established)

**Verdict:** Built, deployed, and source/host/data-verified — with the rendered
Mining-tab check NOT established on the current build (the same gap as Missions
4–7, now the fourth consecutive mission). The host module is correct and fully
tested; the live ledger and mirror are honestly empty; the mismatch rules are
proven in the sandbox; no fictional earnings ship; no private data is exposed.
**STOP — awaiting authorization before Master Mission 9. Do not start Mission 9.**

**Mission report:** `docs/master-mission8-report-2026-11-18.md` (this file)

**Authorization:** User authorized Master Mission 8 on 2026-11-18 17:16 EST
(tapped "Build Mission 8" on the authorization widget in the main chat, after
being told Mission 7 was complete and Mission 8 awaited authorization).

**Artifact build:** `atlas-command-center`, build `d5e7be84-61ad-46de-9d31-b45710310ef4`
(previous build `61fac176`, Mission 7).

## What was built

### Design (Lane A, read-only — coordinator)

`docs/master-mission8-design.md`. Thirteen binding decisions (D-M8-1–D-M8-13):

- **D-M8-1:** Host is the system of record; artifact tables are a read-only
  display mirror. Admin data is DERIVED from `data/coordinator.json` +
  `data/rewards.json` + `data/dashboard.json` + `data/diagnostics.json` + DB
  queries — no new stored truth, no new host DB tables, one new host export
  (`data/admin.json`, atomic). No new artifact mirror tables EXCEPT the two log
  tables in §1.1 (flagged deviation, ordered by the task — operational logs
  cannot live in a singleton row).
- **D-M8-2:** Estimated vs confirmed (M7 §3 carried verbatim): estimate null
  with the verbatim reason "Cannot estimate — hashrate not measured"; confirmed
  = ledger `SUM`, SIMULATION-tagged. The admin mining panel REUSES the dashboard
  export's earnings block by import (never recomputes it) — the admin section
  must never show a different earnings number than the user dashboard.
- **D-M8-3:** No private data, ever. Aggregates and operational data only:
  never wallet addresses, token hashes/salts, session tokens, password hashes,
  seeds, private keys, or any credential. Per-worker rows show id + type +
  status + timestamps only. Per-user data is a COUNT only. Decisions/events
  messages pass a defensive redaction (§1.2) before entering the export.
- **D-M8-4:** Security figures use the binding definitions in §4 (suspicious
  worker, invalid share, duplicate share, account abuse, auth failure, payout
  anomaly). Count 0 renders the verbatim empty state "No events recorded".
  No threshold, flag, or `degraded` inference is drawn from any security count.
- **D-M8-5:** Infrastructure figures use the binding definitions in §5.
  CPU/memory/disk from the latest `metrics` row (RECORDED, with its timestamp).
  DB health is `integrity_check` + `user_version` + table counts. Queue lengths
  are UNAVAILABLE with the verbatim reason "No queue system exists — the
  coordinator runs synchronously in the 10-minute pass". API/pool connectivity
  is the last `pool_stats` poll + the last diagnostics run's endpoint tests.
  Service status is daemon snapshot freshness + coordinator last pass +
  watchdog last PASS line. Daemon uptime is UNAVAILABLE (no start time is
  recorded anywhere); monitoring uptime is the `metrics` span; daemon restarts
  are counted from `events` kind `startup`.
- **D-M8-6:** STALE when the coordinator mirror OR the rewards mirror OR the
  diagnostics export is > 1 h old; "Not synced yet" when never synced. Last-sync
  shows all three sync timestamps separately.
- **D-M8-7 (the Mission 6 lesson, carried and extended):** MIRROR-MISMATCH rule
  — on any disagreement between mirror-derived ledger totals and host-verified
  totals, show the HOST-VERIFIED totals plus the verbatim "Mirror mismatch —
  figures under investigation" note, never silently present mirror rows as real
  earnings. Extended with log-window and security-count secondary checks.
- **D-M8-8–D-M8-13:** Placement directly below User dashboard, Mining tab order
  otherwise unchanged, no new tab, zero buttons/inputs/links/forms, drill-down
  is INLINE detail rows (no expand/collapse control), no secrets mirrored, no
  new cron (admin export rides the coordinator pass as a guarded sub-step),
  every figure carries its provenance, XMR to 6 decimals from integer piconero,
  no fiat, no repair of any carried issue, scope line "Admin view — aggregates
  and operational data only. No login exists yet — this section is not
  access-controlled." — no login, admin picker, or demo admin rows invented.

### Baseline (Lane B, read-only)

`docs/master-mission8-baseline.md` (28,990 B). Verdict: PASS (baseline usable) —
not all-green. Daemon exactly 1 pid at every check (pid churn 2084 → 5773 across
the window, all restarts by diagnostics tests 10/11 or recover.sh); snapshot
fresh; DB integrity ok, `user_version` 3, all mining tables 0 (pool_stats 43,
decisions 293 → 305, events 100 → 106, metrics 1104 → 1116 — deltas are
diagnostics runs + daemon cycles only); configs unchanged (sha256 recorded,
identical to M7); diagnostics **22/24** on its run (tests 14/18 FAIL —
MoneroOcean/blockchain.info timeouts, the known endpoint-flapping signature;
independent curls minutes later returned 200 on all four endpoints, including
mempool.space — the first 200 in that series); endpoints flapping, not settled;
no miner/pool-port/key evidence. Two incidents recorded verbatim: a second
platform VM restart ~21:58 UTC (daemon down ~4.5 min, auto-recovered by
recover.sh at 22:02:41, pid 2084), and the Mission 8 host build landing
mid-baseline (expected — Lane C parallel). Carried gaps unchanged.

### Host admin module (Lane C)

**`core/atlas_admin.py`** (756 lines, stdlib-only): `admin_status(con,
export_dir)` derives network (coordinator reuse), mining (dashboard earnings
block reused by import, never recomputed; pending = gross piconero of
open/held batches — see Deviations), infrastructure (latest metrics row +
PRAGMA + table counts + pool_stats + diagnostics.json tests 14/18 +
snapshot.json + watchdog log last line), security (design §4 definitions),
and latest-50 decisions/events windows with the §1.2 defensive redaction.
Queue lengths and daemon uptime are UNAVAILABLE with the verbatim reasons.
Worker rows select only `id, worker_type, status, registered_at, last_seen_at`
(grep-verified: zero `SELECT * FROM workers`); no user rows (count only). The
only write is the atomic `data/admin.json` export (temp + `os.replace`). CLI:
`status | export`.

**Wiring:** one guarded sub-step in `core/atlas_coordinator.py` `run_pass()`
(+12 lines, Mission 6/7 pattern), placed after the dashboard export. It can
never fail the pass and logs no decision of its own (verified: exactly +1
decision per pass, `coordinator-pass-complete`).

**Tests:** `core/test_atlas_admin.py` (527 lines, temp DBs only): **5/5 PASS** —
(a) zero-state derivation with all verbatim strings + read-only proof (all 12
table counts unchanged across status+export, decisions unchanged); (b) non-zero
fixture (suspended + high-rejection worker → suspicious 2; invalid 12;
duplicates 3 — 2 external_id + 1 null-external_id/job_id; abuse 1; auth
failures 2; payout anomalies 2 = 1 failed payout + 1 reversal; token-bearing
decision reason and 40-hex event message redacted to `[redacted — possible
credential]`, known-`external_id` message shown as-is; earnings block
identical to a fresh dashboard export; pending = 1 XMR open batch);
(c) export idempotence + atomic write (no `.tmp` left); (d) `run_pass` sub-step
on a temp DB — all four exports written, exactly +1 decision, admin export
fresh; (e) stale metrics row flags resources stale + `Above the 70% cap` note.

**Diagnostics:** new test 25 ("admin export": file parses, `exported_at`
fresh, hashrate not-measured, estimate null, earnings block equals a fresh
`dashboard.json` earnings block, host-verified totals match a fresh COUNT/SUM
over the live DB, security counts match fresh SQL, no `token_hash` /
`token_salt` / wallet field anywhere in the file). **Diagnostics 25/25 PASS**
(Lane C's final run; its first full run was 23/25 with only tests 14/18
failing on MoneroOcean/blockchain.info timeouts — the known endpoint-flapping
signature, not a regression; a re-run 60 s later passed 25/25. Test 25 passed
on both runs.)

**Live `data/admin.json`** (regenerated by the coordinator pass after the final
doc fix, exported_at 1795041656 at Lane E check): mode `simulation-only`,
emergency_stop true, `user_version` 3, sync stale false. Network: 0 users,
0 workers, hashrate `not-measured`, shares 0/0/0/0, monitoring uptime 0d 18h
6m (65,173 s), daemon restarts 106 (24h) / 106 (all time), daemon uptime null
+ verbatim reason. Mining: estimate null + verbatim reason, confirmed 0
SIMULATION ONLY, XMR mined 0, pending 0, payouts 0, failed 0. Infrastructure:
latest metrics row CPU 58.65%, memory 90.1% + `Above the 70% cap`, disk
18.94%; DB health `integrity_check ok`; queues null + verbatim reason; pool
MoneroOcean 259,064,041 H/s, 4,916 miners, height 3,809,325; endpoints all
200; services daemon `Running`, coordinator pass age 584 s, watchdog
`Running`. Security: all six counts 0, each with `No events recorded`.
Logs: decisions 306 total / events 106 total, latest-50 windows, window notes
`Showing latest 20 of 50 mirrored rows — 306 total on host` / `— 106 total
on host`. No `token_hash`, `token_salt`, `wallet`, `password`, `seed`, or
`private_key` string anywhere in the file (verified by grep and by test 25).

### Coordinator follow-up (coordinator, after Lane C — no contradictions found)

Unlike Mission 7, Lane C's build contradicted the binding design in NO place.
Checked directly by the coordinator: the earnings block is reused by import
(`_dashboard_status`, line 337–338); the coordinator sub-step is guarded and
placed after the dashboard export (lines 1000–1011); the live export is
regenerated by every coordinator pass (exported_at advanced 1795041054 →
1795041061 across passes); all four unit suites compile and pass (48/48).
The one unspecified point — the pending-rewards formula, which the design says
only "contributes to pending" without a formula — was defined by Lane C as
`SUM(gross_piconero)` over open/held batches, documented in the module
docstring and in the payload's `pending_note`. Lane E verified the definition
sound as a *gross* figure (fees are taken only at settle) and exact on a
1.5 XMR fixture. Accepted as a documented deviation, not a contradiction.

### UI (Lane D spec + coordinator-executed artifact edit)

**Spec:** `docs/master-mission8-lane-d-ui-report-2026-11-18.md` (1,215 lines).

**Artifact build `d5e7be84`** (`atlas-command-center`): new component
`client/src/AdminCommandCenter.tsx` (`AdminCommandCenterSection`, six panel
groups in design order, zero buttons/inputs/links/forms, no hardcoded
displayed figures, XMR to 6 decimals from integer piconero, no fiat);
`Mining.tsx` changed by import + one render line only (section directly below
`UserDashboardSection`, above Settings — tab order otherwise unchanged);
`server/src/schema.ts` + additive migration `drizzle/0008_admin_log_mirror.sql`
(journal idx 7) adding the `mining_admin_decisions` + `mining_admin_events`
mirror tables (host id PK, latest-50 cap, ingest deletes older rows);
`ingestAdminState` extended on the `ingestRewardsState` pattern (upsert the
latest-50 windows in one transaction; identical window → `upToDate`, `synced_at`
untouched; missing `data/admin.json` → `adminExportMissing:true`, tables
untouched, never fabricated); `getMining` gains the `admin` block computed
server-side from mirrored tables only, with `mirrorDerivedTotals`,
`hostVerifiedTotals`, `mismatch` boolean + `mismatchDetails`. No new ingest
action, no new cron, no new refresh step (ingest rides existing refresh step 8
— see Deviations). `RewardAccounting.tsx` untouched; `UserDashboard.tsx`
untouched; Start/Stop untouched; no sim-batch rows touched; no token/session/
password hash mirrored.

**Builder verification (sandbox):** typecheck PASS; migration 0008 validated
on in-memory SQLite (window cap enforced at exactly 50, duplicate host-id
rejected by PK, journal idx 7 well-formed); grep checks (zero interactive
elements, zero hardcoded figure literals, verbatim strings present, no secret
patterns); sandbox `getMining` returns the admin block with all-zero totals,
estimate null + verbatim reason, queue null + verbatim reason, daemon uptime
null + verbatim reason, `mismatch: false`; sandbox ingest with a non-zero
fixture asserts every security count, the redaction, the UNAVAILABLE reasons,
and the earnings block identical to the dashboard export; sandbox mismatch
proofs (ledger + log-window, non-zero fixtures) PASS with the disagreeing
fields named and confirmed figures switched to host-verified; identical
re-ingest reports `upToDate:true` with neither `synced_at` advancing; first
ingest added 50 decisions + 50 events; null export returned
`adminExportMissing:true` and stored nothing; partial window pruned the mirror
to exactly that window. All test writes stayed in the sandbox DB; durable rows
unchanged (0 batches / 0 ledger entries). Desktop probe: all six panel groups
in order with verbatim copy, section ending directly above Settings, Mission 7
section unchanged; audit passed with no findings, no console errors, 390px
overflow 0. **The builder's rendered claim is addressed under Unresolved
finding 1 — the independent inspection contradicts it.**

### Live mirror state (coordinator's own check, `getMining`, after the build)

`admin` block present: all zeros, estimated null + verbatim reason, efficiency
n/a, hashrate nulls, `mismatch: false`, `mismatchDetails: []`,
`hostVerifiedTotals` == `mirrorDerivedTotals` (all 0), `stale: false`,
`coordinatorSyncedAt` 1795039094, `rewardsSyncedAt` 1795039801,
`adminSyncedAt` 1795042073, `diagnosticsSyncedAt` 1795038790. Network: 0 users,
0 workers, monitoring uptime 65,173 s, daemon restarts 106/106, daemon uptime
null + verbatim reason. Mining: XMR mined 0, pending 0, payouts 0, failed 0.
Infrastructure: resources from the metrics row (CPU 8.38%, memory 92.19%,
`memoryAboveCap: true`, ts 1795039844 — the figure carries the STALE tag per
design, row > 10 min old); DB health ok / schema 3, all 11 table counts
(decisions 306, events 106, metrics 1116, poolStats 43); queues null +
verbatim reason; connectivity last pool poll MoneroOcean 268,651,149 H/s,
4,912 miners, height 3,809,325; endpoints with config statuses labelled
"recorded claim, not a live measurement" (mempool.space config
"unreachable-from-this-host" but diagnostics outcome 200 — the flappy
endpoint, §9); services with no pid shown. Security: all six counts 0 with
empty rows. Logs: decisions mirroredCount 50, shownCount 20, hostTotal 306,
dept counts 26/6/6/6/6; events mirroredCount 50, shownCount 20, hostTotal 106,
kind counts startup 50; rows present with real content — the post-submit
ingest DID seed the production mirror (the build completion's 0/0 row counts
were a pre-seed snapshot). Dashboard block unchanged and still all-zero with
`mismatch: false`. Rewards batches `[]`, entries `[]`, totals all 0. Pool:
MoneroOcean 268,651,149 H/s, miners 4,912, height 3809325.

## Test evidence

| Suite / check | Result |
|---|---|
| Host unit suites (4 suites, 19 coordinator + 20 rewards + 4 dashboard + 5 admin) | **48/48 PASS** (Lane C + coordinator's own run) |
| Host diagnostics (tests 01–25, incl. new test 25 admin export) | **25/25 PASS** (Lane C final run, and Lane E's own run — 14/18 both PASS, no flapping that time, no re-run needed; Lane C's first run 23/25 with 14/18 failing on MoneroOcean/blockchain.info timeouts, re-run 25/25) |
| Baseline diagnostics | **22/24** (14/18 endpoint flapping; independent curls 200 on all four endpoints minutes later, including mempool.space) |
| Admin fixture suite (temp DB, incl. security counts, redaction, pending formula, read-only proof, export idempotence) | **5/5 PASS** |
| Coordinator sub-step guard (temp DB `run_pass`) | **PASS** — exactly +1 decision (`coordinator-pass-complete`), ledger unchanged, all four exports fresh |
| Artifact build `d5e7be84` typecheck | **PASS** |
| Migration 0008 (in-memory SQLite validation) | **PASS** — 50-row cap enforced, duplicate host-id rejected by PK, journal idx 7 well-formed |
| Sandbox ingest + mismatch proofs (ledger, log-window, non-zero fixtures) | **PASS** — disagreeing fields named, confirmed figures switch to host-verified |
| Sandbox null-export + partial-window + upToDate | **PASS** — `adminExportMissing:true`, stores nothing; prune to window; identical re-ingest `upToDate:true` |
| Sandbox sandbox `getMining` admin block | **PASS** — all zeros, estimate null + verbatim, mismatch false |
| Coordinator live `getMining` (production mirror) | **PASS** — admin block present, all zeros, estimate null + verbatim, mismatch false, host == mirror totals, stale false |
| **Lane E independent host verification** | **PASS, 9/9 areas, zero mismatches, zero defects** (report: `docs/master-mission8-verification-host.md`) |
| Independent artifact inspection (3926b687) | Source + data verified; **rendered Mining-tab check NOT established** (see Unresolved finding 1) |

## Safety verification (hard limits)

Emergency stop `emergency_stop=True` throughout (both configs unchanged,
sha256 identical to the M7 baseline); no mining, no trading, no wallet/key
creation, no config change, no share submission, no payout attempt, no worker
activation, no spend, no subscription. No pool connection for earning; no new
cron; no new artifact ingest action/schedule. Live ledger 0 rows; mirror 0
batches / 0 entries; every displayed figure is a host-derived zero with its
provenance, never a fabricated value. No private credential, token, session,
or wallet value appears in the admin UI, `data/admin.json`, or the logs
(grep-verified 0 hits on `token_hash` / `token_salt` / `wallet` / `password` /
`seed` / `private_key`, and by test 25; Lane E re-ran the secret grep on the
live and temp admin.json files — 0 hits).

## Files changed

Host (`~/workspace/atlas/`):

- `docs/master-mission8-design.md` (design, 13 binding decisions)
- `docs/master-mission8-baseline.md` (baseline, PASS)
- `docs/master-mission8-lane-d-ui-report-2026-11-18.md` (UI spec)
- `docs/master-mission8-verification-host.md` (Lane E, PASS 9/9)
- `docs/master-mission8-report-2026-11-18.md` (this report)
- `core/atlas_admin.py` (new, 756 lines)
- `core/test_atlas_admin.py` (new, 527 lines, 5/5)
- `core/atlas_coordinator.py` (one guarded admin sub-step, +12 lines)
- `core/diagnostics.py` (new test 25, admin export)
- `data/admin.json` (new export, regenerated each coordinator pass)

Artifact (`atlas-command-center`, build `d5e7be84-61ad-46de-9d31-b45710310ef4`):

- `client/src/AdminCommandCenter.tsx` (new)
- `client/src/Mining.tsx` (import + one render line)
- `server/src/schema.ts` (+ two mirror tables)
- `drizzle/0008_admin_log_mirror.sql` (new migration, journal idx 7)
- `server/src/actions.ts` (`ingestAdminState` + `getMining` admin block)

## Deviations (all documented, none concealed)

1. **D-M8-1 ordered deviation:** two new artifact mirror tables
   (`mining_admin_decisions`, `mining_admin_events`) — the task ordered
   drill-down/operational logs; they cannot live in a singleton row. Only
   operational logs (kind, dept, message, timestamps); no secrets.
2. **Pending formula unspecified in the design:** Lane C defined pending as
   `SUM(gross_piconero)` over open/held batches, documented in the module
   docstring and in the payload's `pending_note`. Lane E verified the
   definition sound as a *gross* figure (fees taken only at settle) and exact
   on a 1.5 XMR fixture.
3. **Duplicate-share detection groups on non-null `external_id` only:** the
   share mirror carries no `job_id` column, so that grouping is skipped, not
   faked. Recorded in DATA-PLAN.md. The host definition still includes the
   `job_id` fallback — it is not implementable in the artifact.
4. **Refresh "step 8":** ingest rides the existing `refreshAtlasData` as a
   step inside that task (the artifact's refresh action is a numbered 8-step
   task; this is its 8th step). That reconciles "ingest rides the existing
   refresh as step 8" with "no new refresh step" — the step is a sub-step of
   the existing refresh, not a new action or schedule.

## Unresolved findings (honest)

**New:**

1. **Rendered Mining-tab check still NOT established on build `d5e7be84` — the
   fourth consecutive mission.** The builder's own verification notes claim a
   desktop probe showing all six admin panel groups in order with verbatim
   copy and the section ending directly above Settings, and that "audit
   passed with no findings". The independent artifact inspection
   (3926b687, repair_authorized=false) examined the artifacts API list page,
   live-app JSON snapshot, and `atlas-command-center` audit (22:41 UTC) and
   found **no Mining-tab rendering evidence in any of them** — the latest
   audit shows only the Overview tab, and the rendered Mining-tab state at the
   time was ~50 min old with a failed refresh ("Web artifact inference
   failed"). No screenshot or DOM text proves the Admin section rendered in
   the live app; source (Mining.tsx + AdminCommandCenter.tsx) and data
   (`getMining` admin block present and correct) are verified. The builder's
   render claim did not survive evidence review. Repeated render failures now
   span build 61fac176 (M7) and build d5e7be84 (M8). This is the same gap
   carried from M4, M5, M6, M7 — it is NOT fixed by Mission 8.
2. **Duplicate-share mirror fallback skipped** (Deviation 3) — the artifact
   cannot verify the `job_id`-grouped duplicate share count; it is skipped,
   not faked.
3. **Redaction over-redaction observation** (Lane E, not a defect): the
   known-id exception matches only when the whole external_id/job_id is one
   uninterrupted 20+ run — a hyphenated id with a 20+ segment gets redacted.
   Safe-direction (over-redaction), no such shape occurs in real pool-id data;
   Lane C's suite only tests the exception with a short id, so Lane E verified
   the long-run path.
4. **Refresh failure observed again in the 22:41 UTC audit** — "Web artifact
   inference failed"; mirrors ~50 min old at that moment (the carried M7
   refresh failure). The coordinator's own live `getMining` minutes later
   showed fresh mirrors and `stale: false`, so this is the carried failure,
   not a new one. The in-app refresh button + background task remains the
   broken path; the hourly fallback works.

**Settled in Mission 8 (not defects):**

5. **Logs window-note wording:** "Showing latest 20 of 50 mirrored rows" is
   the section's *display* copy (verbatim design §8.2/§1.1 — the artifact
   displays 20 rows); the export carries the 50-row *ingest* window. Lane E
   confirmed this is accurate as written; no change owed.

**Carried from Mission 7 (unchanged unless noted):**

6. Browser hashrate still unmeasured — all earnings still honest zeros;
   estimate null with the verbatim reason.
7. Stale "no miner yet" copy still present in Mining.tsx.
8. **M6 finding 1 latent:** `RewardAccounting.tsx` hardcodes `0 XMR` literals
   (`confirmedXmr`, `simulatedXmr`, `pendingXmr`) instead of showing the
   ledger-derived values; the rendered section shows settled sim batch
   `sim-batch-test-1`, 1 XMR, while the isolated DB holds 0 batches /
   0 entries. Repair NOT authorized.
9. Panel 1 "0 users" + "Derived host" tag wording tensions (M7 findings
   7–8, unmeasured).
10. Gate 1 unmeasured (M7 finding 9).
11. M7 finding 6 still unverified: the duration secondary check wiring was
    not independently verified — the builder's verification notes do not
    report the Lane D spec §5.3 step 8 proof (duration matrix against the
    coordinator's `duration: 4200` total) in the sandbox.
12. Host memory still above the project's standing 70% cap (78–96% all day,
    92.19% at the last live check). Daemon pid churn continued (2084 → 5773
    during the baseline window; pid 10039 at Lane E close after diagnostics
    test 10/11 restarts); crash cause still not established. The host is
    churning, not stable.
13. `mempool.space` endpoint flapping: diagnostics test 14/18 flapped
    (timeouts) in the baseline and in Lane C's first run, then returned 200
    repeatedly; still not settled as reliably reachable.
14. DB growth unexplained (metrics 1104 → 1139 rows across the day, decisions
    +9 after the baseline end — fully explained as coordinator passes +
    diagnostics test 07 + coordinator pass; events +2 = diagnostics restarts).
    The long-run growth trend is still not attributed.
15. Baseline diagnostics 22/24 (tests 14/18 failing on MoneroOcean /
    blockchain.info timeouts) — the known endpoint-flapping signature, not
    a regression.
16. Panel 1 wording: "0 users" is the honest count of registered users in an
    empty system, but reads as if no one is using the platform; "Derived host"
    is accurate but unclear. Unchanged from M7.
17. `mempool.space` config status "unreachable-from-this-host" vs diagnostics
    outcome 200 — config-recorded claim vs live measurement, labelled in the
    UI as "recorded claim, not a live measurement". Carried.
18. Reward display self-contradiction (M6 finding 1, repeated for emphasis):
    rendered section shows settled sim batch `sim-batch-test-1`, 1 XMR, while
    the isolated DB holds 0 batches / 0 entries. Not fixed, not authorized.
19. Desktop-viewport reward screenshot NOT established; reload-persistence NOT
    established (carried from M6).
20. Referral rate 5% unconfirmed; minimum payout null; SupportXMR URL
    unconfirmed; external hosting unknown; treasury never deposited.
21. The in-app refresh button + background task remains the broken path
    (finding 4 above); the hourly fallback works.
22. All other carried M7 findings not re-listed here (see
    `docs/master-mission7-report-2026-11-18.md`).

## Authorization needed before proceeding (not done by this mission)

- **Master Mission 9** (profitability intelligence) — requires user
  authorization. **STOP after this report — do not start Mission 9.**
- Rendered Mining-tab capture (the fourth-consecutive-mission gap): a
  repair-authorized independent render check of the live artifact with a
  Mining-tab screenshot/DOM capture, and a fix if the render genuinely fails.
- Repair of M6 finding 1 (hardcoded zero literals in `RewardAccounting.tsx`)
  — NOT authorized; do not repair without authorization.
- Stale "no miner yet" copy + dashboard refresh-button failure repair —
  NOT authorized.
- Duration secondary check wiring verification (Lane D spec §5.3 step 8).
- Wording decisions: Panel 1 "0 users" / "Derived host" tag; dashboard button
  copy.
- Any real pool, share, payout, referral, or treasury work — all gated behind
  authorization and the emergency stop.
- Minimum payout, referral rate, SupportXMR URL, external hosting, treasury.

## Lane E independent host verification

Full report: `docs/master-mission8-verification-host.md`. **PASS, 9/9 areas,
zero mismatches, zero defects.** Verification window 2026-11-18 22:48–22:53 UTC.
Read-only except running the existing suites/diagnostics; nothing edited,
artifact untouched.

- Daemon: exactly 1 pid at every check; snapshot fresh (age 2–46 s).
- DB integrity: `integrity_check` ok, `user_version` 3; users/workers/shares/
  sessions/ledger/reward_batches/payouts/referrals all 0; pool_stats 45,
  decisions 314, events 108, metrics 1139 at close.
- No writes by the admin module: 0 decisions matching `%admin%`;
  ledger/reward_batches 0; decisions +9 since baseline end fully explained
  (+3 coordinator passes, +4 diagnostics test 07, +2 coordinator pass);
  events +2 = diagnostics restarts.
- Configs unchanged: sha256 `46d3d12c…` / `b01a22ad…` exact match to baseline.
- Every admin.json field re-derived from fresh SQL as-of `exported_at`
  1795041656: network, uptime 65,776 s, restarts 106/106, latest metrics row,
  all 11 db_health counts, pool_stats row 44, diagnostics t14/t18
  byte-identical, services ages arithmetically consistent, all 6 security
  counts per §4 definitions, all 50+50 log rows field-identical with
  dept/kind counts matching. **Zero fields mismatch.**
- Earnings identity: admin earnings block value-identical to fresh dashboard
  earnings on both exports checked (estimate null + "Cannot estimate —
  hashrate not measured", confirmed 0 SIMULATION ONLY).
- Test suites: unit 48/48; diagnostics **25/25 PASS** on Lane E's own run
  (tests 14/18 both PASS, no flapping, no re-run needed). "Unmodified"
  caveat: no reference hashes exist in the baselines; established via
  pre-Lane-C mtimes (M7 era) for the three older suites plus expected
  counts/names.
- Coordinator sub-step guarded: temp-DB `run_pass` — decisions exactly +1
  (`coordinator-pass-complete`), ledger unchanged, all four exports fresh
  (age 0 s).
- Formula checks (temp DB): (a) pending = SUM(gross) over open/held — fixture
  1.5 XMR exact; definition sound as a *gross* figure, disclosed in
  `pending_note`. (b) Duration matrix exact: 4200 s, active 1 (ended desktop
  +3600, probe/user/degenerate excluded, open desktop ~+600); dashboard ==
  coordinator. (c) Redaction works — fake token and long-hex rows replaced
  with "[redacted — possible credential]" and still counted; known single-run
  hex external_id and plain rows shown verbatim. (d) Secret grep on live and
  temp admin.json: token_hash/token_salt/wallet/password/seed/private_key
  all 0 hits.

## Sign-off

Mission 8 is complete: design, baseline, host module, UI, live mirror, and
independent host verification all done and documented. The admin command
center exists in the artifact (build `d5e7be84`), shows the host's honest
zeros, hides no mismatch, and exposes no private data. The one standing gap
is the same as the last four missions: **the rendered Mining tab has never
been independently established on the live artifact** — source and data are
verified, the live render is not.

**STOP — awaiting authorization before Master Mission 9.**
