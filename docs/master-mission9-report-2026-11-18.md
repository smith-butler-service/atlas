# ATLAS MASTER MISSION 9 — PROFITABILITY INTELLIGENCE: COMPLETE, WITH ONE LIVE-MIRROR MISMATCH OPEN

**Verdict:** COMPLETE — with one open defect. The design, the baseline, the
host module, the UI, the Lane E independent host verification, and the
coordinator's own live `getMining` check are all done and verified. The
profitability section is published on the Command Center (build `2131aa37`)
and the live mirror is seeded with real figures from the host export
(`exportedAt` 1795056798, `profitabilitySyncedAt` 1795057040, stale false).
**One defect remains open:** the live mirror-vs-host comparison reports
`mismatch: true` (~100 details) — the mirror derivation computes correctly,
but the comparison fails on host rounding vs the 1e-9 tolerance, on GPU
breakeven units (MH/W host vs H/W mirror), and on null-vs-value scope
differences (GPU `currentHw`/`ratioTier2`/`verdictTier2`, browser split
rows). No figure is wrong; the section shows the host-verified figures with
the designed verbatim note `Mirror mismatch — figures under investigation`.
The calibration fix needs a repair-authorized change and is NOT done here.
**STOP — do not start Mission 10 without separate authorization.**

**Mission report:** `docs/master-mission9-report-2026-11-18.md` (this file)

**Authorization:** User authorized Master Mission 9 on 2026-11-18 21:03 EST
("Engage. Engage the mission nine." in the ATLAS side chat). A speed-up order
arrived 21:39 EST ("finish whatever lane work is already in flight, skip all
optional polish and any new work, and deliver the final report now with what is
verified") — this report is written under that order, with Lane C still running
and Lane E not run.

**Artifact build:** `atlas-command-center`, build `2131aa37` (per the builder
completion card `web-artifact-build-completed-2131aa37-085f-4eff-89b0-93bc589da8be`;
previous build `bafa9e63` v16, the Smith Research tab build — NOT M8 `d5e7be84`,
which is v15).

## What was built

### Design (Lane A, coordinator)

`docs/master-mission9-design.md` (40,183 B). Thirteen binding decisions
(D-M9-1–D-M9-13):

- **D-M9-1:** Host is the system of record; artifact tables are a read-only
  display mirror. Profitability figures are DERIVED by the host module from
  live inputs + carried constants at export time — no new stored truth. **No
  new host DB tables.** One new host export, `data/profitability.json`
  (atomic write). One new artifact mirror singleton row (migration 0010 —
  see Deviations; the design said 0009).
- **D-M9-2:** Estimated vs confirmed (M7 §3 / M8 §3, carried verbatim): every
  profitability figure is an ESTIMATE. Confirmed earnings = ledger `SUM`,
  SIMULATION-tagged, reused from the dashboard export by import, never
  recomputed. Estimate and confirmed are never combined.
- **D-M9-3:** **No fiat in the panel.** Rates shown as ¢/kWh INPUTS; daily
  figures in XMR/day to 6 decimals; non-XMR coins compared in XMR/day via
  live-price conversion, labelled ESTIMATE, comparison-only. USD intermediates
  exist only inside the host export under `audit_usd` for audit, never
  rendered. Breakeven as H/s per wall watt and ¢/kWh.
- **D-M9-4:** Live inputs with source + `fetched_at` per input,
  fetch-with-fallback (MoneroOcean `/network/stats` + CoinGecko prices;
  KAS/RVN/ERG from 2Miners `api/stats` + CoinGecko; USD/CAD from CoinGecko
  `exchange_rates`). Short timeout; on failure use last recorded inputs and
  mark that coin STALE — never silently fresh, never guessed. Electricity
  rates are tariff constants (HQ Tier 1 7.065¢ CAD, Tier 2 11.142¢ CAD, US
  avg 17.23¢ USD) with source + effective date.
- **D-M9-5:** Reference profiles only (Obj 4 / M4 CARRIED): Ryzen 7 5800X
  10,000 H/s @ 171 W (XMR); RTX 3060 Ti — KAS 480 MH/s @ 150 W, RVN 27 MH/s
  @ 240 W, ERG 137 MH/s @ 132 W; browser workers (laptop 200 H/s @ 45 W,
  desktop 850 H/s @ 50 W). Hashrate/watts labelled ASSUMPTION. Your-hardware
  estimate NULL while Gate 1 is unmeasured, verbatim "Cannot estimate —
  hashrate not measured".
- **D-M9-6:** Breakeven definitions — gate H/W and breakeven ¢/kWh per coin
  per rate; distance-to-breakeven ratio + verbatim `Above breakeven` /
  `Below breakeven`.
- **D-M9-7:** Electricity sensitivity at Tier 1 / Tier 2 / US avg; the
  pending 19.5¢ CAD/kWh Quebec blockchain tariff ONLY as a labelled RISK
  SCENARIO row ("Proposed tariff — not in effect").
- **D-M9-8:** Pool-fee comparison — XMR net under MoneroOcean 0%, SupportXMR
  0.6%, P2Pool 0% (fee on projected gross only); KAS/RVN/ERG at 2Miners 1%
  (Obj 4, CARRIED). Fees disclosed beside each figure.
- **D-M9-9:** 75/25 split projection (user share, ATLAS share, user net
  position) per coin at Tier 2, XMR/day, ESTIMATE, verbatim "Projection only
  — not earnings". A projection of what the split WOULD be if the projected
  gross were realized — never an earning, never a balance.
- **D-M9-10:** STALE rules (M8 §6 pattern) — section STALE when any live
  input is > 1 h old, tag naming the stale input; "Not computed yet" when
  never computed; re-ingest of unchanged data reports "already up to date",
  never advances `syncedAt`.
- **D-M9-11:** MIRROR-MISMATCH rule (M7 §6 / M8 §7 carried) — on disagreement
  show HOST-VERIFIED figures + verbatim "Mirror mismatch — figures under
  investigation". No hardcoded figure literal permitted in the section
  (grep-enforced). Must be tested with non-zero fixtures, not zeros alone.
- **D-M9-12:** Placement directly below Admin command center, above Settings;
  no new tab; zero buttons/inputs/links/forms; Start/Stop untouched.
- **D-M9-13:** No new cron; export rides the coordinator pass as a guarded
  sub-step; every figure carries provenance. This design does NOT repair any
  carried issue.

### Baseline (Lane B, read-only)

`docs/master-mission9-baseline.md` (33,376 B; window 2026-11-18 21:06:23–
21:37:24 EST). Verdict: **PASS (baseline usable) — NOT all-green.**

- Daemon exactly 1 pid at every check (6920 → 9757 via diagnostics tests
  10/11); snapshot fresh (age 24–32 s), emergency_stop true.
- DB integrity ok, `user_version` 3; pool_stats 55→57, decisions 363→372,
  events 120→122, metrics 1338→1370 across the window; all zero tables
  (users/workers/shares/sessions/ledger/batches/payouts/referrals) remain 0.
- Configs sha256 identical to M7/M8 (`46d3d12c…` / `b01a22ad…`); mining
  disabled, trading paper-only, eligible capital $0; fees MoneroOcean 0% /
  SupportXMR 0.6% / P2Pool 0%. No miner processes, no pool-port connections,
  no key files.
- Diagnostics **23/25 PASS** on Lane B's run (02:06:44–02:08:25 UTC) — FAILs
  tests **14 + 18 only** (MoneroOcean/blockchain.info/mempool.space
  `TimeoutError` after retry; the known flapping signature from M7/M8, not a
  regression). The pre-baseline on-disk file was another lane's 25/25 run at
  01:52:52 UTC; Lane B's run overwrote it, as designed.
- Endpoints **9/9 reachable after retry** (8/9 first attempt): MoneroOcean
  `/pool/stats` 200 (285.8 MH/s, 4,926 miners) and `/network/stats` 200;
  blockchain.info 200; mempool.space 200; kas/rvn/erg 2Miners `api/stats`
  all 200; api.kaspa.org `/info/hashrate` + `/info/blockreward` 200.
  CoinGecko `simple/price` **429 rate-limit on first attempt, 200 on retry**
  — a new flap shape. All endpoints answered 200 by 02:36 UTC, ~28 min after
  the diagnostics timeouts, proving the FAILs transient.
- Live model inputs (VERIFIED, fetched 02:36:21–02:36:47 UTC; no
  profitability conclusions computed): XMR $500.37, difficulty
  787,880,387,293, height 3,809,486, block 0.6 XMR; KAS $0.0270543, network
  310.65 PH/s (2Miners) vs 302.38 PH/s (kaspa.org), reward 1.94454365 KAS;
  RVN $0.00109849, network 499.88 GH/s, block 1,250 RVN; ERG $0.204211,
  network 556.95 GH/s, difficulty 67,279,622,504,448, reward 3 ERG. Notable
  vs Obj 4: ERG hashrate down ~22% (713→557 GH/s), XMR difficulty +2.0%.
- Refresh failure observed again 01:53:00/01:54:41 UTC (button
  `refreshatlasdata` FAIL twice, dashboard ~57 min stale; fallback ingest
  fixed it 01:56:23) — pre-window but freshest occurrence.
- Lane B caveat: this lane had no artifact tools, so it could not verify the
  build id or Mining-tab order (the coordinator verified the build from the
  builder handoff instead: build `2131aa37`).
- Uptime-vs-metrics contradiction noted but NOT asserted: `uptime` read 1:10
  at 02:37 UTC implying a ~01:27 UTC boot, but metrics are continuous
  through 01:20–01:33 (max gap 67 s); the 01:27:44 event is a daemon restart
  only, cause unlogged. Daemon churn: 16 startup events since M8 end
  (7 diagnostics-run pairs + 2 unexplained single recover restarts at
  23:47:44 and 01:27:44 UTC); 122 restarts in 24 h / all-time.

### UI (Lane D + publish)

**Spec:** `docs/master-mission9-lane-d-ui-report-2026-11-18.md` (M8 Lane D
structure, §0–§9).

**Edit** (working tree, 7 files, verified by hash/mtime sweep vs v16):

- CREATE `client/src/ProfitabilityIntelligence.tsx` —
  `ProfitabilityIntelligenceSection`, 7 panel groups per design §8.2, zero
  buttons/inputs/links/forms, XMR/day to 6 decimals, no fiat (rates as ¢/kWh
  inputs only; all other input values bare), every figure ESTIMATE +
  SIMULATION-tagged, all verbatim strings from design §3/§6/§8.
- EDIT `client/src/Mining.tsx` — import + ONE render line directly below
  `AdminCommandCenterSection`, above Settings. Nothing else touched; stale
  "no miner yet" copy and `RewardAccounting.tsx` untouched.
- CREATE `server/src/profitability.ts` — pure derivation/comparison/
  block-assembly (design §1 formula, tolerance
  `max(1e-9, 1e-6·|host|)`), STALE naming, host-verified-first display.
- EDIT `server/src/schema.ts` + CREATE `drizzle/0010_profitability_mirror.sql`
  + journal idx 9 — singleton `mining_profitability` row (payload JSON,
  `audit_usd` stripped, never stored).
- EDIT `server/src/actions.ts` — `ingestProfitabilityState` (missing export →
  `profitabilityExportMissing:true`, stores nothing; identical re-ingest →
  `upToDate`, `synced_at` untouched), `getMining` profitability block
  (confirmed earnings reused from dashboard, never recomputed),
  `refreshAtlasData` step 9. No new cron, no new refresh step.

**Publish:** `artifact.edit` dispatched by the coordinator; builder completed
with `verification_status: SUCCEEDED`. **Build `2131aa37`.** (The first
publish attempt timed out at dispatch; this build is the retry of the same
submission.)

**Sandbox verification (in-memory SQLite + fixture data; live `app.db` never
touched; durable rows unchanged, 0 batches / 0 ledger entries):**

- Typecheck: **PASS**, exit 0, zero errors (2 errors found and fixed during
  the build).
- Migration 0010: **PASS** — singleton CHECK enforced, journal idx 9.
- Sandbox suite: **10 pass / 0 fail, 121 expects** — real
  `getMining`/`ingestProfitabilityState` handlers invoked end-to-end. Obj 4
  net/day regression reproduced within $0.002 for all 4 coins × 3 rates; M4
  gates 56.5 H/W (Tier 2), 125.2 H/W (US), $0.03302/day per kH/s reproduced;
  SupportXMR 0.6% = exactly 0.6% off MoneroOcean; US avg flips XMR negative,
  Tier 2 stays positive.
- Mismatch proof: **PASS** — tampered XMR `netXmrPerDayTier2` →
  `mismatch:true`, field named exactly, displayed figures switch to
  host-verified. Confirmed-earnings disagreement → `confirmedEarnings` in
  `mismatchDetails`, dashboard figure shown.
- Stale proof: **PASS** — KAS network stats 73 min old →
  `STALE — KAS network stats 73 min old`. Identical re-ingest →
  `upToDate:true`, `synced_at` unmoved. Null export →
  `profitabilityExportMissing:true`, nothing stored.
- Grep checks: **PASS** — zero interactive elements, zero bare `$` (15 hits
  are all `${` interpolations), zero hardcoded XMR/day literals, zero secret
  patterns, all verbatim strings present.
- Desktop probe: **25/25 PASS** — static render of the real component with a
  real block: 7 panels in order, verbatim copy, zero controls, no
  currency-marked amount, 6-decimal XMR/day, missing-export and stale
  variants correct.

**Live mirror state at publish time** (builder data rows): `mining_profitability`
0 rows (no export yet — the section honestly renders the export-missing
state); `mining_admin_decisions` 50, `mining_admin_events` 50,
`mining_dashboard_host_totals` 1, `mining_ledger` 0, `mining_reward_batches` 0,
`mining_pool_stats` 57, `mining_users` 1, `mining_workers` 0, decisions 338,
snapshots 75, `smith_research_rounds` 2.

### Host build (Lane C) — STILL IN FLIGHT, NOT VERIFIED

Lane C (`core/atlas_profitability.py` + `core/test_atlas_profitability.py` +
diagnostics test 26 + guarded coordinator sub-step) was still **running** at
21:39 EST when the speed-up order arrived (running ~31 min, last activity
seconds before the check). Verified at report time: `data/profitability.json`
does NOT exist, `core/atlas_profitability.py` does NOT exist,
`core/test_atlas_profitability.py` does NOT exist. No host-module figure,
test count, or diagnostics test 26 result is claimed in this report. When
Lane C lands, its results must be verified (Lane E) and appended — the
mission is not complete until then.

## Test evidence

| Suite / check | Result |
|---|---|
| Design (13 binding decisions D-M9-1–D-M9-13) | **DONE** — `docs/master-mission9-design.md` |
| Baseline (Lane B, read-only) | **PASS (usable, not all-green)** — `docs/master-mission9-baseline.md` |
| Baseline diagnostics | **23/25 PASS** (tests 14/18 fail — endpoint flapping, known signature) |
| Baseline endpoints | **9/9 reachable after retry** (CoinGecko 429 first, 200 on retry) |
| Host module unit tests | **NOT VERIFIED** — Lane C still in flight at report time |
| Diagnostics test 26 | **NOT VERIFIED** — Lane C still in flight at report time |
| Coordinator sub-step guard | **NOT VERIFIED** — Lane C still in flight at report time |
| Artifact build `2131aa37` typecheck | **PASS** (client + server, exit 0) |
| Migration 0010 (in-memory SQLite validation) | **PASS** — singleton CHECK, journal idx 9 |
| Sandbox suite (real handlers, fixture data) | **10/10 PASS, 121 expects** |
| Sandbox Obj 4 / M4 regressions | **PASS** — nets within $0.002, gates 56.5 / 125.2 H/W reproduced |
| Sandbox mismatch proofs | **PASS** — field named, display switches to host-verified |
| Sandbox stale proofs | **PASS** — STALE tag names the input; upToDate / null-export rules hold |
| Sandbox grep checks | **PASS** — zero controls, zero fiat, zero hardcoded literals, zero secrets |
| Desktop probe (static render) | **25/25 PASS** — 7 panels in order, verbatim copy, zero controls |
| Live `getMining` profitability block | **NOT VERIFIED** — no host export exists yet; section renders export-missing state |
| **Lane E independent host verification** | **NOT RUN** — blocked on Lane C landing + speed-up order |
| Independent artifact inspection (repair_authorized=false) | **NOT RUN** — the builder's own verification is the only artifact evidence in this report |

## Safety verification (hard limits)

Emergency stop `emergency_stop=True` throughout (snapshot ts 1795055932,
age 22 s at the coordinator's 21:39 EST check); no mining, no trading, no
wallet/key creation, no config change, no share submission, no payout attempt,
no worker activation, no spend, no subscription. No pool connection for
earning; no new cron. Live ledger 0 rows; mirror 0 batches / 0 entries; every
displayed figure is a host-derived value or an honest export-missing state,
never a fabricated value. No private credential, token, session, or wallet
value appears in the profitability UI or the mirror (grep-verified 0 hits on
`token_hash` / `token_salt` / `password` / `seed` / `private_key` in the Lane D
sandbox checks; the live export does not exist yet, so there is nothing to
grep on the host side — that check is owed with Lane E).

Coordinator's own live check (21:39 EST, read-only): snapshot fresh (22 s),
emergency_stop true; DB `user_version` 3, metrics 1372, decisions 372,
events 122, ledger 0, reward_batches 0. Note: `pgrep -f atlas_monitor.py`
returned two pids (9757, 17864) at that check; the second was NOT re-verified
before this report and is treated as a transient startup, unconfirmed — not
asserted as a second daemon. (Lane B recorded exactly 1 pid at every check
in its window.)

## Files changed

Host (`~/workspace/atlas/`):

- `docs/master-mission9-design.md` (design, 13 binding decisions)
- `docs/master-mission9-baseline.md` (baseline, PASS usable / not all-green)
- `docs/master-mission9-lane-d-ui-report-2026-11-18.md` (UI spec)
- `docs/master-mission9-report-2026-11-18.md` (this report)
- `core/atlas_profitability.py` — **NOT LANDED** (Lane C in flight)
- `core/test_atlas_profitability.py` — **NOT LANDED** (Lane C in flight)
- `core/diagnostics.py` (test 26) — **NOT LANDED** (Lane C in flight)
- `core/atlas_coordinator.py` (profitability sub-step) — **NOT LANDED** (Lane C in flight)
- `data/profitability.json` — **DOES NOT EXIST** (Lane C in flight)

Artifact (`atlas-command-center`, build `2131aa37`):

- `client/src/ProfitabilityIntelligence.tsx` (new)
- `client/src/Mining.tsx` (import + one render line)
- `server/src/profitability.ts` (new)
- `server/src/schema.ts` (+ singleton mirror table)
- `drizzle/0010_profitability_mirror.sql` (new migration, journal idx 9)
- `server/src/actions.ts` (`ingestProfitabilityState` + `getMining`
  profitability block + `refreshAtlasData` step 9)

## Deviations (all documented, none concealed)

1. **Migration is 0010, not 0009.** 0009 already exists
   (`smith_research_rounds`, journal idx 8). The design said 0009; the build
   correctly used the next free number.
2. **Current build at Lane D start was v16 `bafa9e63`, not M8 `d5e7be84`**
   (v15). The Smith Research tab build landed after Mission 8, so the
   design's build baseline was stale. The Mission 9 build is `2131aa37`.
3. **`ingestProfitabilityState` is a new action** riding the existing refresh
   (M8 reading of "no new refresh step").
4. **Pure module `server/src/profitability.ts`** instead of inline-handler
   logic, so the sandbox proofs run the real code.
5. **Panel 7a clarification:** input values render bare; only ¢/kWh on rate
   rows; labels/sources are metadata — the no-fiat rule constrains amounts.
6. **PARTIAL completion under the speed-up order — RESOLVED by the
   completion addendum.** The host module landed (Lane C), its tests and
   diagnostics test 26 pass, the coordinator sub-step is guarded, the live
   `getMining` check ran, and Lane E verification passed 9/9. What remains
   open is the live `mismatch: true` calibration defect (Unresolved
   finding 7) and the rendered Mining-tab check (finding 4).

## Unresolved findings (honest)

**New:**

1. **Host module not landed — RESOLVED.** `core/atlas_profitability.py`
   landed 2026-11-19 02:47 UTC (50,708 B, 11/11 unit tests), test 26 added
   (diagnostics 26/26), coordinator sub-step guarded, `data/profitability.json`
   live and fresh. The published section is seeded with real figures; the
   export-missing state is gone. See the completion addendum.
2. **Lane E independent host verification NOT run — RESOLVED.** Lane E ran
   2026-11-19 02:51:14 UTC: OVERALL PASS, 9/9 areas, zero defects. Independent
   re-derivation 166/166, suites 59/59, diagnostics 26/26, all four Lane C
   deviations confirmed against live payloads. Report:
   `docs/master-mission9-verification-host.md`.
3. **Independent artifact inspection (repair_authorized=false) NOT run.**
   The builder's own verification is the only artifact evidence. The
   rendered Mining-tab check is therefore still NOT established (finding 4
   below).
4. **Rendered Mining-tab check still NOT established on build `2131aa37` —
   the sixth consecutive mission.** The desktop probe is a static render of
   the real component, not a live render; it does not establish Mining-tab
   selection, a real-browser console, or real-viewport 390px overflow. This
   is the same gap carried from M4, M5, M6, M7, M8 — it is NOT fixed by
   Mission 9.
5. **CoinGecko 429 on first attempt (new flap shape) — OBSERVED, covered.**
   The price endpoint rate-limited once in the baseline, then answered 200 on
   retry. Since then the host module has live-fetched successfully on every
   coordinator pass (Lane C + Lane E fresh fetches all 200); the
   fetch-with-fallback design (D-M9-4) covers a 429, and no 429 has recurred
   under the module. Keep watching; no action owed.
6. **Two pids matched `atlas_monitor.py` at the coordinator's 21:39 EST
   check (9757, 17864) — RESOLVED as transient.** Lane E checked repeatedly
   and found exactly 1 pid at every check (19362 → 19944 after its own
   diagnostics restarts); the dual-pid sighting did not recur. Not a second
   daemon.

7. **Live `mismatch: true` — mirror-vs-host comparison calibration defect
   (NEW, primary open item).** The live mirror is seeded and fresh, the
   mirror derivation computes correctly, and every host figure was
   re-derived 166/166 by Lane E — but the comparison reports `mismatch:
   true` (~100 details) for four causes: (a) host 6dp/1dp rounding vs the
   1e-9 tolerance; (b) GPU breakeven gates in MH/W (host) vs H/W (mirror);
   (c) GPU `currentHw`/`ratioTier2`/`verdictTier2` null (mirror, per design)
   vs values (host); (d) split projection has no browser rows on the host
   (nulls) vs computed splits on the mirror. The section shows
   host-verified figures with the verbatim mismatch note. Fix needs a
   repair-authorized inspection + edit — NOT authorized. See the completion
   addendum.
8. **Refresh-task step-9 mapping is stale vs the real export shape
   (NEW).** The step-9 instruction assumes `profitability.json` already has
   top-level `inputs[]`/`coins[]` arrays; the real export nests figures
   under `panel.*` with an `inputs` object keyed by coin. The coordinator
   mapped it by hand for the live seed (payload `/tmp/m9-ingest-payload3.json`).
   The hourly refresh job needs the same canonical transform (or the export
   reshaped), or the next refresh will ingest nothing / fail validation and
   the mirror will go stale. Owed.
9. **Tariff-constant `fetchedAt` schema gap (NEW).** The ingest schema
   requires integer `fetchedAt` for every input, but D-M9-4 gives tariff
   constants `fetched_at: null`. The coordinator stored them with
   `fetchedAt` = the export instant and the source + effective date in the
   `source` string; the live check confirmed `stale: false`. A schema change
   to allow null `fetchedAt` for constants would be cleaner. Owed.

**Carried from Mission 8 (unchanged unless noted):**

10. Browser hashrate still unmeasured — all earnings still honest zeros;
   your-hardware estimate null with the verbatim reason.
11. Stale "no miner yet" copy still present in Mining.tsx.
12. **M6 finding 1 latent:** `RewardAccounting.tsx` hardcodes `0 XMR` literals
   (`confirmedXmr`, `simulatedXmr`, `pendingXmr`) instead of showing the
   ledger-derived values. Repair NOT authorized.
13. Panel 1 "0 users" + "Derived host" tag wording tensions (M7 findings
    7–8, unmeasured).
14. Gate 1 unmeasured (M7 finding 9).
15. M7 finding 6 still unverified: the duration secondary check wiring was
    not independently verified.
16. Host memory still above the project's standing 70% cap (84–93% across
    the day). Daemon pid churn continued (6920 → 9757 during the baseline
    window; 122 restarts in 24 h / all-time); crash cause still not
    established. The host is churning, not stable.
17. `mempool.space` endpoint flapping: diagnostics tests 14/18 failed on
    timeouts in the baseline run, then returned 200 repeatedly; still not
    settled as reliably reachable.
18. Refresh failure observed again (01:53:00/01:54:41 UTC, button
    `refreshatlasdata` FAIL twice; fallback ingest fixed it). The in-app
    refresh button + background task remains the broken path; the hourly
    fallback works.
19. `mempool.space` config status "unreachable-from-this-host" vs diagnostics
    outcome 200 — config-recorded claim vs live measurement, labelled in the
    UI as "recorded claim, not a live measurement". Carried.
20. Desktop-viewport reward screenshot NOT established; reload-persistence NOT
    established (carried from M6).
21. Referral rate 5% unconfirmed; minimum payout null; SupportXMR URL
    unconfirmed; external hosting unknown; treasury never deposited.
22. ERG network hashrate down ~22% vs Obj 4 (713→557 GH/s) and XMR difficulty
    +2.0% — the live inputs moved; the module must re-derive from live
    inputs at export time, never from the CARRIED Obj 4 results. (Design
    D-M9-4 covers this; host-module behaviour confirmed live by Lane C + Lane E (166/166 re-derivation).)
23. All other carried M8 findings not re-listed here (see
    `docs/master-mission8-report-2026-11-18.md`).

## Authorization needed before proceeding (not done by this mission)

- **Mission 9 completion** — DONE (Lane C landed, Lane E 9/9 PASS,
  coordinator live `getMining` check complete). The live `mismatch: true`
  calibration defect remains open (Unresolved finding 7).
- Mismatch-calibration repair (host rounding/tolerance, GPU units, GPU
  null-scope, browser split rows; refresh-task step-9 canonical transform;
  tariff `fetchedAt` schema) — repair-authorized inspection + edit,
  NOT authorized.
- **Master Mission 10** (security and scale testing) — requires user
  authorization. **STOP after this report — do not start Mission 10.**
- Rendered Mining-tab capture (the sixth-consecutive-mission gap): a
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

**RUN — COMPLETE 2026-11-19 02:51:14 UTC, agent `85b625f3-7940-43e4-8744-6765326e5c5d`.
OVERALL: PASS, 9/9 areas pass, zero defects, zero mismatches.** Report:
`docs/master-mission9-verification-host.md`.

| Area | Verdict |
|---|---|
| 1. Daemon | PASS — exactly 1 pid at every check (19362 → 19944 after its diagnostics run's by-design restarts). The 21:39 EST dual-pid sighting (9757/17864) did NOT recur — transient, not a second daemon. Snapshot fresh, emergency_stop true. |
| 2. DB integrity | PASS — integrity ok, `user_version` 3; all mining tables 0; pool_stats 58, decisions 383, events 126, metrics 1386 at close. |
| 3. No writes by profitability module | PASS — 0 profit/admin decisions; decisions +4 = its diagnostics test 07 quartet (ids 380–383); ledger/reward_batches 0. Module has no INSERT/UPDATE/DELETE/`log_decision`/`SELECT *`; stdlib-only imports. |
| 4. Configs unchanged | PASS — sha256 `46d3d12c…` / `b01a22ad…`, exact match to baseline. |
| 5. Re-derive every profitability.json figure | PASS — **166/166** independent checks (own script, no import of the module), 0 fails, against the current export (1795056561). Lane C's export (1795056354) read in full: all claimed figures match except the KAS gate (12,005.4 vs claimed 11,984.8, 0.17% — live-input movement between passes, not an error). |
| 6. Live figures vs fresh fetch | PASS — fresh curls 02:48:39–02:49:20 UTC: XMR $500.79 vs export $500.82; difficulty 781,581,223,091 (exact match in the re-issued export); USD/CAD 1.43493 vs 1.434823; ERG hashrate exact match. stale=False correct (inputs 4–5 min old). |
| 7. Full suites + diagnostics | PASS — **59/59** unit tests run by Lane E: profitability **11/11**, coordinator **19/19** (confirms Lane C's 19-not-20 note), reward engine **20/20**, dashboard **4/4**, admin **5/5**. Diagnostics **26/26 PASS first run**, no 14/18 flapping; test 26 detail verified verbatim. |
| 8. Coordinator sub-step guarded | PASS — own temp-DB `run_pass`: decisions exactly +1 (`coordinator-pass-complete`), all 5 exports fresh (age 0s), fallback STALE with preserved `fetched_at`. |
| 9. Deviations + secrets + STALE | PASS — all four Lane C deviations **confirmed**; secret grep 0 hits in live and temp exports. |

Live figures re-derived by Lane E (with fetch times): Lane C export
(1795056354): XMR $500.82, difficulty 782,021,032,919 → 6.517 GH/s, USD/CAD
1.4348; XMR net +0.000027 XMR/day Tier 2 (+$0.0133; Tier 1 +$0.1299, US
−$0.3751); gates 56.1/124.6 H/W; breakeven 8.09¢/kWh; profile 58.5 H/W,
ratio 1.042, Above breakeven; KAS/RVN/ERG Tier 2 nets −$0.279/−$0.340/−$0.139;
pool fees 0.000027/0.000023/0.000027 XMR/day; split 0.000497/0.000166/−0.000139.
Current export (1795056561, re-issued by Lane E's diagnostics run): XMR net
+$0.01349 Tier 2, +$0.13010 Tier 1, −$0.37496 US; KAS −$0.27946, RVN −$0.34002,
ERG −$0.13909 Tier 2 — re-derived 166/166. Fresh fetch 02:48:39–02:49:20 UTC
(epoch 1795056519–60): MoneroOcean key 8766 RVN value 125,000,552,000 satoshi
= 1250.00552 RVN (independently confirms the 1,250 carried reward); ERG
difficulty cross-check matches 2Miners to within 1.

Observations (not defects): `exported_at` precedes inputs' `fetched_at` by
1–5 s (clock captured before fetch); panel `age_s` goes negative (−2…−5 s,
shown as "0s"). Cosmetic. KAS `gross_xmr_per_day` rounds to 0.0 at 6dp (true
≈1.4e-7); full precision lives in `audit_usd`. Per design. RVN `difficulty`
null in export (2Miners reports fractional string "7089.1684"; module records
integers only) — figures use networkhashps, no impact. Host memory
89.96–94.62%, above the 70% cap — standing carried issue.

## Completion addendum — Lane C landing, Lane E, and the coordinator's live `getMining` check (2026-11-19 ~02:47–03:00 UTC)

### Lane C landing (host build, agent `39b94f5d-95d6-475a-9fa0-8df082445887`)

Module `core/atlas_profitability.py` (50,708 B, stdlib-only;
`profitability_status(con, export_dir)` + `export_profitability_json()` + CLI
`status|export`; implements the §1 formula exactly; live inputs per D-M9-4;
10 s/endpoint; fetch failure → last recorded inputs, coin STALE with
last-fetch time, never raises, never fabricates; tariff constants with source
+ effective date; reference profiles per D-M9-5 only; your-hardware null +
verbatim "Cannot estimate — hashrate not measured"; confirmed-earnings block
reused from the dashboard export by import; USD intermediates only under
`audit_usd`; atomic write temp + `os.replace`; writes no ledger rows, no
decisions, no shares — the export is its only write). Tests
`core/test_atlas_profitability.py` (28,959 B) **11/11 pass** (all §10 cases
(a)–(i), plus blockReward-band and 2Miners string-payload parsing tests).
Coordinator: one guarded profitability sub-step in `run_pass()` after the
admin sub-step (lines 1014–1029, confirmed present by the coordinator), same
pattern as M6/M7/M8, logs no decision of its own, never fails the pass.
Diagnostics test 26 (`t26_profitability_export`, `core/diagnostics.py`
line 841) added; **full suite 26/26 PASS on the first run** claimed (tests
14/18 did not flap, no re-run needed); other suites re-verified unmodified:
admin 5/5, dashboard 4/4, coordinator 19/19 (Lane C noted an earlier
mixed-output run made it look like 20; the file has 19 test methods), reward
engine 20/20. Live verification claimed: export run against the live DB —
`data/profitability.json` parses, `stale=False`, `not_computed=[]`, decisions
unchanged 374→374 (read-only proof; the 372→374 drift before its run was two
other passes, not Lane C's); coordinator pass run exactly **+1 decision**
(374→375, new row `coordinator-pass-complete`; pool poll skipped as not due),
export regenerated (`exported_at` 1795056331, 5 s old, `stale=False`).
Coordinator's own check 2026-11-19 ~02:47 UTC confirmed the files exist:
`data/profitability.json` 22,489 B, `exported_at` 1795056354, `stale: false`,
`not_computed: []`; decisions 379, ledger 0. Live figures claimed (export
1795056307; XMR $500.82, difficulty 784,521,706,195 → 6.517 GH/s, USD/CAD
1.4348): XMR net **+0.000027 XMR/day at Tier 2** (+$0.0133/day; Tier 1
+$0.1299, US avg −$0.3751); **breakeven gates XMR 56.1 H/W Tier 2, 124.6 H/W
US avg** (M4: 56.5 / 125.2 at slightly different inputs — consistent);
breakeven 8.09¢/kWh; profile 58.5 H/W, ratio 1.042, Above breakeven; KAS
11,984.8 MH/W, RVN 0.5 MH/W, ERG 2.4 MH/W Tier 2 — all Below breakeven; pool
fees Tier 2: MoneroOcean 0.000027, SupportXMR 0.000023, P2Pool 0.000027
XMR/day; split Tier 2: XMR user share 0.000497, ATLAS 0.000166, user net
−0.000139 XMR/day; KAS/RVN/ERG nets Tier 2: −$0.279 / −$0.340 / −$0.139 per
day. Deviations (documented, none concealed): (1) **RVN/ERG block rewards are
CARRIED protocol constants** (1,250 RVN, 3 ERG), not live from 2Miners — Lane
C verified live that the 2Miners `api/stats` payloads publish **no
`blockReward` field for RVN/ERG anywhere in the payload** (only KAS publishes
one); each coin's export record carries `block_reward_source` stating live vs
carried with the Obj 4 citation; network hashrate/difficulty/height/
avgBlockTime for all three coins are still live from 2Miners; (2) **2Miners
returns every numeric field as a string** (e.g. `networkhashps:
'306904484533747697'`) — parser coerces via `_num()`/`_int_or_none()`
(integer strings stay exact ints — float64 can't hold the 17-digit KAS
difficulty); the uncoerced parser was why the first live export showed
KAS/RVN/ERG as not-computed; fixed, regression-tested, re-run computes all
four coins; (3) **STALE semantics**: a fallback-marked record counts as
STALE even when its last fetch was <1 h ago (D-M9-4's fallback marking), in
addition to the >1 h age rule (D-M9-10); staleness is also re-derived from
`fetched_at` at export time rather than trusting the stored flag; (4)
**Tariff constants** carry source + effective date with `fetched_at: null` —
exactly the distinction D-M9-4 itself draws. Hard limits held: emergency
stop still ON (diagnostics t09 PASS); simulation-only; no mining/trading/
payouts/wallets/keys/spending/config changes (config mtimes unchanged, Nov 18
04:32/07:35); no carried issue repaired; no artifact touched; no Mission 10
work. Note: `browser.open` on the two API URLs failed on approval timeout —
Lane C did not repeat it; API shapes came from the Obj 4/M4 docs and were
verified live through the module's own fetch path. **Lane E confirmed all
four deviations directly against live 2Miners payloads**: KAS publishes
`"blockReward":"194454365"`; RVN and ERG payloads contain no `blockReward`
substring anywhere; string numerics confirmed, KAS difficulty
30,274,296,942,479,743 exact.

### Coordinator's live `getMining` check (2026-11-19 ~02:53–03:00 UTC)

The coordinator ran the live check itself (build `2131aa37`, artifact
`atlas-command-center`).

**First `getMining` (before any ingest):** profitability block present but
`profitabilityExportMissing: true`, `exportedAt: null`, `coins: []`,
`inputs: []`, `hostVerifiedFigures: null`, `mirrorDerivedFigures: null`,
`profitabilitySyncedAt: null`, `stale: true`,
`staleInputs: ["profitability export — not synced yet"]`,
`mismatch: false`, `yourHardware` null + verbatim reason, `confirmed`
0 / simulation-only. The published section was rendering its honest
export-missing state, exactly as the partial report said.

**Ingest 1 (export 1795056660, 16 live inputs, host ids `xmr`/`xmr_cpu`):**
stored (`profitabilityExportMissing: false`, `upToDate: false`). `getMining`
then showed the host-verified figures correctly (6 coins, inputs fresh,
stale false, `profitabilitySyncedAt` 1795056775) — but `mismatch: true`
with 9 details: the 6 host rows `missing-from-mirror` plus the 3 pool-fee
nets. Cause: the mirror derivation re-derives from the stored inputs by the
§1 formula using the design §2.4 input keys, and the first mapping omitted
the keys it needs (`*_blocks_per_day` ×4, `usd_cad_rate` — `usd_cad` was
sent instead — and all rate/fee/profile constants), and used host profile ids
(`xmr_cpu`) while the derivation's rows use display names (`Ryzen 7 5800X`).

**Ingest 2 (export 1795056798, 20 live inputs incl. `*_blocks_per_day` and
`usd_cad_rate`, coins renamed to the derivation convention `XMR` /
`Ryzen 7 5800X` etc., feeLabels `0%`/`0.6%`/`0%` per design §2.4):** the
join now worked (details named `XMR (Ryzen 7 5800X).computed` etc.), but
`mirrorDerivedFigures` were still all null / `computed: false`,
`hashrateHps` 0, `wallWatts` 0 — the derivation still lacked the rate, fee,
and profile constants, which it reads from stored inputs by the §2.4 keys.

**Ingest 3 (same export 1795056798, 40 inputs = 20 live + 20 constants:
4 rates, 4 fees, 12 profile hashrate/watts):** the derivation COMPUTED —
all 6 coins `computed: true`, full-precision figures, `hashrateHps` /
`wallWatts` correct. `stale: false`, `staleInputs: []`,
`profitabilitySyncedAt` 1795057040, your-hardware null + verbatim reason,
confirmed 0 / simulation-only, identical to the dashboard block, no
credential field anywhere in the block. **But `mismatch: true` with ~100
details.** The mirror figures are right — every one is within rounding of
the host figure — and the mismatch has four distinct, fully diagnosed
causes (below). Identical re-ingest of the same payload then reported
`upToDate: true` — the live idempotency check passes.

**Mapping decisions (coordinator, recorded per Lane D §2.1 — the parent
maps and records):** (a) Lane C's export shape ≠ the ingest action's shape.
The export nests figures under `panel.*` with snake_case keys and an
`inputs` object keyed by coin; the action wants flat camelCase arrays
(`inputs[]` {key,label,value,unit,source,fetchedAt}, `coins[]` with the §2.4
fields, `poolFees[]`, `yourHardware`, `confirmedEarnings`). The refresh-task
step-9 instruction as written ("mapped field-for-field from
profitability.json") assumes the export already has those top-level arrays —
it does not. The coordinator mapped panel → flat arrays (exact payload at
`/tmp/m9-ingest-payload3.json`). The hourly refresh job needs this same
canonical transform, or the export must be reshaped — owed work, not done
here. (b) Coin/profile join keys: host uses lowercase coin + snake profile id
(`xmr`/`xmr_cpu`); the derivation uses uppercase coin + display name
(`XMR`/`Ryzen 7 5800X`). The coordinator mapped to the derivation convention
(figures unchanged, keys only). (c) Tariff/fee/profile constants: the ingest
schema requires integer `fetchedAt` for every input, but D-M9-4 gives tariff
constants `fetched_at: null`. The coordinator stored them with `fetchedAt` =
the export instant (1795056798) and put the source + effective date in the
`source` string, so the panel never misreads a constant as a fresh fetch.
The STALE rule covers live inputs only (design D-M9-10), and the live check
confirmed `stale: false` with the constants stored this way. A schema change
to allow null `fetchedAt` for constants would be cleaner — owed, not done
here. (d) The inputs panel shows 40 rows (20 live + 20 constants); the
tariff rows are labelled constants in their source strings. (e)
`xmr_difficulty` and the `*_difficulty` rows are extra live inputs beyond
the §2.4 table (useful for the inputs panel; the derivation ignores them).

**The open defect — live `mismatch: true`, four causes (all verified
figure-by-figure from the live `getMining` output):**

1. **Host rounding vs the 1e-9 tolerance (most figures).** The host rounds
   XMR/day figures to 6 decimals, ratios to 3, H/W and ¢/kWh to 1–2; the
   mirror derivation keeps full precision; the binding tolerance is
   `max(1e-9, 1e-6·|host|)`. The rounding step (5e-7 at 6dp) is ~500× the
   tolerance, so nearly every figure mismatches on rounding alone. Verified:
   XMR Ryzen `dailyCoinsNative` host 0.000661 vs mirror
   0.0006614541490767802 (diff 4.54e-7); `netXmrPerDayTier2` host 0.000025
   vs mirror 0.000024761173311306335 (diff 2.39e-7); KAS net Tier 2 host
   −0.000558 vs mirror −0.0005583595222143204; RVN gross host 0.000214 vs
   mirror 0.00021418510932175573. The mirror formula is confirmed correct
   by hand: (10000 / 6531064936.291667) × 720 × 0.6 = 0.000661454… = the
   mirror value; the host value is that number rounded to 6dp.
2. **GPU breakeven units (KAS/RVN/ERG `breakevenHwTier2`/`breakevenHwUsAvg`).
   ** The host expresses GPU breakeven gates in MH/W; the mirror derivation
   applies the §1 formula literally in H/W — factor 1e6. Verified: KAS host
   12490.3 vs mirror 12490264911.63 (12,490,264,911 H/W = 12,490.3 MH/W);
   RVN host 0.5 vs mirror 469362.55 (= 0.469 MH/W); ERG host 2.4 vs mirror
   2389059.38 (= 2.389 MH/W).
3. **GPU null-vs-value scope (`currentHw`, `ratioTier2`, `verdictTier2` for
   KAS/RVN/ERG).** The design (§2.4) says `currentHw` is null for GPU rows
   ("XMR rows only"); the mirror follows it (null), but the host fills GPU
   `currentHw` in MH/W (3.2 / 0.1 / 1.0) and GPU `ratioTier2` (0.0 / 0.24 /
   0.434) and `verdictTier2` ("Below breakeven"). Null-vs-number is a
   mismatch by the §2.4 rule, never silently equal. The host deviates from
   the design here; the mirror follows it.
4. **Split projection scope (browser rows).** The host `split_projection`
   has only 4 rows (no browser profiles) → host `userShare`/`atlasShare`/
   `userNet` null for Laptop/Desktop browser; the mirror derivation computes
   the 75/25 split for all 6 profiles (e.g. Laptop `userShare`
   9.921812236151705e-6, `atlasShare` 3.307270745383901e-6, `userNet`
   −0.00015762897086002566). Null-vs-number = mismatch.

   Consequence (designed behaviour, working as specified): the section shows
   the HOST-VERIFIED figures (which Lane E re-derived 166/166 and the
   coordinator re-checked by hand) with the verbatim note `Mirror mismatch —
   figures under investigation`. No wrong figure is displayed. The fix is a
   calibration change on one side — host exports full precision (or the
   mirror rounds to host precision), GPU gates in one unit, one null-scope
   rule for GPU rows, split rows for all 6 profiles (or nulls on both sides)
   — and needs a repair-authorized inspection + edit. NOT authorized here;
   do not attempt it inside this mission.

### Final live figures (export 1795056798, the mirror's current state)

XMR $500.51, difficulty 783,727,792,355 → 6.531 GH/s, USD/CAD 1.43492. XMR
net **+0.000025 XMR/day at Tier 2** (Tier 1 +0.000258, US avg −0.000751,
proposed tariff −0.000453); **breakeven gates XMR 56.3 H/W Tier 2, 124.9 H/W
US avg**; breakeven 8.07¢/kWh; profile 58.5 H/W, ratio 1.039, Above
breakeven; KAS 12,490.3 MH/W, RVN 0.5 MH/W, ERG 2.4 MH/W Tier 2 — all Below
breakeven; pool fees Tier 2: MoneroOcean 0.000025, SupportXMR 0.000021,
P2Pool 0.000025 XMR/day; split Tier 2: XMR user share 0.000496, ATLAS
0.000165, user net −0.000141 XMR/day; KAS/RVN/ERG nets Tier 2: −0.000558 /
−0.000679 / −0.000278 XMR/day. Browser profiles both Below breakeven
(laptop −0.000154, desktop −0.000130 XMR/day Tier 2). All figures ESTIMATE,
SIMULATION-tagged, never earnings.

### Updated test-evidence table (additions since the partial report)

| Check | Result |
|---|---|
| Host module unit tests (`test_atlas_profitability.py`) | **11/11 PASS** (Lane C; re-run by Lane E) |
| Coordinator suite | **19/19 PASS** (Lane C note: file has 19 test methods) |
| Reward engine suite | **20/20 PASS** |
| Dashboard suite | **4/4 PASS** |
| Admin suite | **5/5 PASS** |
| Total unit tests run by Lane E | **59/59 PASS** |
| Diagnostics (full suite, incl. test 26) | **26/26 PASS** (Lane C first run; Lane E first run, no 14/18 flapping) |
| Lane E independent re-derivation of `profitability.json` | **166/166 checks, 0 fails** |
| Lane E live-fetch cross-check | PASS (XMR $500.79 vs export $500.82; ERG hashrate exact) |
| Coordinator temp-DB sub-step guard (Lane E) | PASS (decisions exactly +1, all 5 exports fresh) |
| Live `getMining` profitability block | Seeded, fresh, stale false; host figures correct; **mismatch: true (open defect, 4 causes above)** |
| Live identical re-ingest | `upToDate: true` — idempotency confirmed live |
| Secret grep on live + temp exports | 0 hits |
| Rendered Mining-tab check | **NOT established** (6th consecutive mission — see Unresolved findings) |

## Sign-off

Mission 9 is COMPLETE with one open defect: design, baseline, host module,
UI publish (build `2131aa37`), Lane E independent host verification (9/9
PASS), and the coordinator's own live `getMining` check are all done. The
live mirror is seeded with real figures from the host export, fresh, stale
false, your-hardware null with the verbatim reason, confirmed earnings 0 /
simulation-only, no credential field. The live mirror-vs-host comparison
reports `mismatch: true` — the mirror derivation computes correctly, but the
comparison fails on host rounding vs the 1e-9 tolerance, GPU breakeven units
(MH/W host vs H/W mirror), and null-vs-value scope differences. No figure is
wrong; the section shows host-verified figures with the designed mismatch
note. The calibration fix needs a repair-authorized inspection + edit and is
owed as follow-up work — it is NOT done by this mission. The rendered
Mining-tab check is still NOT established (6th consecutive mission).

**STOP — do not start Mission 10 without separate authorization.**
