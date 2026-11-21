# ATLAS Master Mission 9 — Lane D (UI build) SPECIFICATION

**Mission:** Master Mission 9 — Profitability intelligence (simulation only)
**Lane:** D (UI build — this lane writes the spec AND executes the artifact
edit in the `atlas-command-center` working tree, typechecks it, and runs
the §5 sandbox verification)
**Date:** 2026-11-18
**Artifact:** `atlas-command-center`
**Status:** BUILD. The spec below (§0–§8) is the contract; the edit is
executed in the working tree per §5.1, verified per §5.3/§6, and handed to
Lane E for acceptance. The publish step (new build id) is NOT issued by
this lane — see §0 deviation 2: this subagent has no `artifact.*` tools,
so the new build id is issued when the parent/main agent publishes the
working tree through the artifact tooling.

## 0. Binding inputs and ground truth

Read first (binding):

- `docs/master-mission9-design.md` (Lane A) — decisions D-M9-1–D-M9-13
  are binding and are followed exactly, EXCEPT for the two explicitly
  flagged deviations in §0.1 below, which the live tree state forces and
  which this spec records so Lane E can verify them as ordered/recorded,
  not as drift.
- `docs/master-mission8-lane-d-ui-report-2026-11-18.md` (Mission 8 UI
  spec — structure and conventions followed exactly here: §0 binding
  inputs / ground truth, §1 new component, §2 `getMining` block, §3
  migrations, §4 verification, §5 exact file change list +
  verification steps, §6 Lane E checklist, §7 carried issues, §8
  handoff checklist). Where M8 was spec-only (the coordinator executed
  the edit), M9 Lane D executes the edit directly in the working tree
  (`~/workspace/ts-spaces/atlas-command-center/`), because the source
  tree is readable and editable from this lane — see §0.1 deviation 2
  for the one step this lane cannot do (publish / new build id).
- `docs/master-mission8-design.md` §1.1/§7 — the mirror-table +
  mismatch-rule patterns followed here: host is system of record,
  artifact is a read-only display mirror; on any disagreement the
  HOST-VERIFIED figures are shown plus the verbatim note
  `Mirror mismatch — figures under investigation`; no hardcoded figure
  literal is permitted anywhere in the new section.
- `docs/master-mission7-lane-d-ui-report-2026-11-18.md` (ingest/migration
  pattern: singleton mirror row, `upToDate` re-ingest honesty, STALE
  rules) and `docs/master-mission6-lane-d-ui-report-2026-11-18.md`
  (ingest patterns, sandbox verification method).
- `docs/master-mission8-report-2026-11-18.md`, Unresolved findings 1–17
  — carried, NOT fixed by this build (design §9). This spec does NOT
  repair any of them. In particular it does NOT fix the Mission 6
  hardcoded zero literals in `RewardAccounting.tsx` (design D-M9-12),
  does NOT repair the refresh failure, does NOT fix the stale
  "no miner yet" copy, and does NOT establish the rendered Mining-tab
  check.

### 0.1 Deviations from the parent task / design (flagged, none concealed)

1. **Migration number is 0010, not 0009.** The parent task orders
   `drizzle/0009_profitability_mirror.sql` as "next journal index".
   The live tree already carries `drizzle/0009_smith_research_rounds.sql`
   (journal idx 8, Smith Research rounds — landed after Mission 8).
   The next migration is therefore **`drizzle/0010_profitability_mirror.sql`,
   journal idx 9**. Reusing 0009 would collide with an existing
   migration and corrupt the journal. This is a forced correction, not
   a design change: same additive pattern, same singleton-row shape.
2. **Current build is v16 `bafa9e63`, not Mission 8 `d5e7be84`.** The
   parent task expects build `d5e7be84`. On-disk evidence says the live
   tree has moved on: `~/workspace/space-versions/atlas-command-center/v15/version.json`
   is the M8 build (`d5e7be84-61ad-46de-9d31-b45710310ef4`, "ATLAS Master
   Mission 8 — Admin command center section"), and `v16/version.json`
   is build `bafa9e63-cd7d-4afd-8fce-8db5ef537e81` (Smith Research tab,
   "Also add a tab of SMIT research…"). The working tree's file hashes
   match v16 exactly (`AdminCommandCenter.tsx` c79dcbb9…,
   `Mining.tsx` 79784e1a…, `actions.ts` 9cfb07d7…,
   `schema.ts` 7f1b921e…). This lane has no `artifact.status` tool to
   confirm the deployed build independently, so the build id is
   reported from the on-disk version record, not from a live status
   call — and the NEW build id for this mission can only be issued by
   the parent/main agent publishing the tree through the artifact
   tooling. The edit in §5.1 lands in the working tree, typechecks,
   and passes the §5.3 sandbox verification; the publish is owed to
   the parent and is recorded in §8 as an open handoff item, never
   claimed as done.
3. **`ingestProfitabilityState` is a new server action.** The parent
   task's point 3 ("No new ingest action") is read the M8 way: no new
   refresh step, no new cron, no new schedule — the ingest rides the
   existing refresh. The action itself (`ingestProfitabilityState`,
   on the `ingestRewardsState`/`ingestAdminState` pattern) is new, as
   the task's point 2 orders. Same reading as M8's `ingestAdminState`.
4. **Pure module `server/src/profitability.ts`.** The M7/M8 pattern
   puts the comparison logic inline in the `getMining` handler. This
   build extracts the profitability derivation, comparison, and block
   assembly into pure functions in `server/src/profitability.ts`,
   imported by `actions.ts`, so the design §10 mismatch/stale proofs
   can actually run in the sandbox (the `defineAction` handlers cannot
   execute outside the space SDK runtime). The handlers stay thin
   wrappers. No behaviour difference; the sandbox tests execute the
   REAL code paths, not replicas — except for the §5.3 step 6(b)
   host-reference implementation, which is deliberately independent
   (see §5.3).

### 0.2 Ground truth (verified read-only by this lane from the live host)

Host clock at check time: exports `exported_at` 1795054253
(2026-11-18 ~18:30 EST).

- Mining tab order (unchanged, verified in `Mining.tsx` lines 217–229):
  MiningDashboard, WalletCenter, EarningsSection, HistorySections,
  PayoutSection, CalculatorSection, MinerPrototypeSection,
  CoordinatorSection, RewardAccountingSection, UserDashboardSection,
  **AdminCommandCenterSection**, SettingsSection, HelpSection. The new
  **Profitability intelligence** section goes directly BELOW
  AdminCommandCenterSection, above Settings.
- Live host DB (`data/atlas.db`): `user_version` 3,
  `integrity_check` ok; users 0, workers 0, shares 0, sessions 0,
  ledger 0, reward_batches 0, payouts 0, referrals 0; pool_stats 56,
  decisions 369, events 122, metrics 1344.
- Live host exports (all `exported_at` 1795054253):
  `data/coordinator.json`, `data/rewards.json`,
  `data/dashboard.json`, `data/admin.json`; `data/diagnostics.json`
  1795054105; `data/snapshot.json` ts 1795054248. Emergency stop true
  in the snapshot (per design §0 baseline).
- Config (`config/atlas.json`, per design §0): emergency_stop true,
  mining enabled false, trading paper-only, eligible capital $0,
  limits max_cpu_pct 50, max_mem_pct 70.
- Pool config (`config/pool-rewards.json`): mode `simulation-only`;
  MoneroOcean 0% fee; SupportXMR 0.6%; P2Pool 0%; split 75/25;
  minimum payout null.

**GAPS (recorded, never blockers, never fabricated):**

1. **Host profitability export NOT landed yet.**
   `data/profitability.json` does NOT exist at build time and
   `core/atlas_profitability.py` does NOT exist (Lane C host work runs
   in parallel — the exact M8 gap-2 shape). The profitability block in
   §2 is therefore spec'd ENTIRELY from the design's field definitions
   (design §1, §2, §8) plus the already-existing host exports above.
   Any host field not yet present is recorded as a gap, never a blocker
   and never fabricated. The artifact side MUST NOT depend on
   `data/profitability.json` existing at build time: the `profitability`
   block is computed from the mirrored singleton row only (§2.2), and
   `ingestProfitabilityState` (§3.3) must skip cleanly — reporting
   `profitabilityExportMissing: true`, leaving the table untouched —
   when the host export is absent, exactly as the M8 refresh step 8
   skipped cleanly when `data/admin.json` was absent. Until the first
   profitability ingest lands, the section renders the
   `profitabilityExportMissing` state (§1.3 panel 7b + §4), never a
   fabricated figure.
2. **Lane C field names unconfirmed.** The design (§1) names blocks,
   not JSON field names. The ingest input schema (§3.3) and the refresh
   step-9 mapping (§4) use the snake_case field names defined in this
   spec from the design's block descriptions. If Lane C's landed export
   names a field differently, the parent/coordinator MUST record the
   difference in the build report and map it in the refresh instruction
   — it must NOT silently rename a design field, and must NOT invent a
   value for a field the export does not carry (that field is
   UNAVAILABLE with its verbatim reason, never approximated).
3. **Live mirror NOT read by this lane.** This subagent's toolset
   exposes no read-only `getMining` call and no `artifact.status`
   call. Live-mirror state (mirror `syncedAt` values, current STALE
   state) is therefore "to be verified by the parent at publish time"
   — it is NOT guessed anywhere in this spec. The §2.3 expected live
   values are the honest state derived from the host exports above,
   which the parent MUST confirm against the live mirror after the
   first profitability ingest lands.
4. **Rendered Mining-tab check NOT established (carried, M9 design
   §9 finding 1).** No captured render ever selects the Mining tab.
   The §5.3 desktop probe in this build is a sandbox static render
   (see §5.3 step 10) — it establishes panel order, verbatim copy, and
   zero interactive elements in the rendered output, and does NOT
   claim a live render, a real-browser console, or a real-viewport
   overflow measurement. The live-render gap is stated plainly in §6
   and §8; it is not closed by assertion.

**Where the artifact source lives.** The artifact source tree
(`client/src`, `server/src`, `drizzle/`) lives in the ts-space working
tree `~/workspace/ts-spaces/atlas-command-center/` (NOT in
`~/workspace/atlas/`). File paths below are relative to that tree.
The working tree matches space-version v16 exactly (hashes in §0.1
deviation 2). The ts-space `AGENTS.md` house rules are respected: no
hand-edit of the built bundle under `.space-build/`, no `bun run
build` (it does not publish), no sqlite/scripts against the live
`app.db` — all sandbox verification uses an in-memory SQLite DB and
fixture data only, and durable rows are unchanged (0 batches / 0 ledger
entries; the sandbox DB is discarded).

---

## 1. New component — `client/src/ProfitabilityIntelligence.tsx`

### 1.1 Identity and placement

- **New file:** `client/src/ProfitabilityIntelligence.tsx` (export
  `ProfitabilityIntelligenceSection`, taking the same `m` prop shape as
  `AdminCommandCenterSection` — the `getMining` result).
- **Placement:** in `client/src/Mining.tsx`, import and render
  `<ProfitabilityIntelligenceSection m={m} />` directly BELOW
  `<AdminCommandCenterSection m={m} />` and directly ABOVE the
  Settings section. No other line in `Mining.tsx` moves. No existing
  section is reordered, restyled, or reworded. No new tab.
- **Data:** reads ONLY the `profitability` block of the `getMining`
  result (§2). Never reads any other action, never fetches, never
  writes. React Query refetch: same 30 s cadence as the rest of the
  Mining tab. No new refresh schedule.
- **Zero controls (hard limit):** zero `<button>`, `<input>`, `<a>`,
  `<form>`, or any clickable control anywhere in the section. No
  "recalculate", no "refresh now", no rate input, no hardware picker,
  no settings control. Start/Stop stay hard-disabled and untouched.
- **No hardcoded figures (hard limit, D-M9-11 / design §7):** NO
  hardcoded figure literal is permitted anywhere in this component as
  a displayed value. Every displayed figure flows from the
  `profitability` block. A panel whose value is a literal in the
  component source is a defect, full stop. The §5 grep check enforces
  this. (Verbatim copy strings such as `2Miners 1% fee applied` are
  copy, not values: the `1%` inside that verbatim label is the design's
  own wording, not a displayed figure — the component MUST render the
  fee figures from the block and MUST NOT substitute a literal for
  them. Where a verbatim sentence contains a figure, the figure in the
  sentence MUST be produced by formatting the block value, never typed
  as a constant.)
- **Amounts:** XMR/day to exactly 6 decimal places (e.g.
  `0.000671 XMR/day`), formatted from the block's numeric values only.
  **No USD/fiat figure anywhere.** No `$` character, no `USD` string
  anywhere in the component. Electricity rates are shown as ¢/kWh
  INPUTS (tariff inputs, D-M9-3 — they are not earnings figures), to
  3 decimals. Breakeven is shown as H/s per wall watt and as ¢/kWh,
  never as a dollar figure.
- **Provenance tags:** every figure carries a RECORDED / DERIVED (host)
  / ESTIMATE / UNAVAILABLE tag plus a SIMULATION tag while mode is
  `simulation-only`, following the existing tab pattern (design §2
  table). Nothing is labelled live unless it was measured in the
  current probe/session. A figure with no provenance is a defect, not
  a display choice (D-M9-13).
- **Responsive / accessibility (binding, M5 §7.4 carried):** tables/cards
  collapse to stacked cards below ~640 px; no horizontal page overflow
  at 390 px (mobile overflow 0); all status text is text, not colour
  alone (a screen reader must hear `Above breakeven` /
  `Below breakeven` / `not measured` / `STALE`, not just a colour).
- **Atoms:** reuse the `AdminCommandCenter.tsx` atoms verbatim in shape
  (`Tag`, `Panel`, `PanelHead`, `Kv`, `EmptyNote`, `fmtDateTime`,
  `fmtAge`, `SyncRow`, `LogTable`-style responsive table) so the
  section matches the existing tab design language. New formatters:
  `fmtXmrPerDay` (6 decimals, `XMR/day`), `fmtCentsPerKwh` (3
  decimals, `¢/kWh`), `fmtHw` (1 decimal, `H/W`), `fmtRatio` (2
  decimals). Negative XMR/day values render with the same `−` (U+2212)
  sign convention as `fmtXmr6` in `AdminCommandCenter.tsx`.

### 1.2 Section header (verbatim)

> **Profitability intelligence — Master Mission 9**
> Estimate note (verbatim, D-M9-2, directly under the section heading):
> `All figures are estimates from live inputs and stated assumptions — not earnings, not a promise of profit.`
> Mismatch note slot (shown ONLY on mismatch, verbatim, in the section
> header area next to the affected figures):
> `Mirror mismatch — figures under investigation`

### 1.3 The panels (verbatim headings, labels, and empty-state copy)

Panels render top-to-bottom in this exact order: Panel group 1 (1a),
Panel group 2 (2a), Panel group 3 (3a), Panel group 4 (4a), Panel
group 5 (5a), Panel group 6 (6a), Panel group 7 (7a–7b). Values shown
are today's honest live state; the component MUST compute them from
the `profitability` block, never from literals.

**Panel group 1 — Coin comparison** (base case: HQ Tier 2; every figure
ESTIMATE, XMR/day to 6 decimals)

Heading: `Profitability — coin comparison`

| Field (verbatim label) | Value today (live state) | Provenance tag |
|---|---|---|
| `Coin` | `XMR` / `KAS` / `RVN` / `ERG` | RECORDED |
| `Reference hardware` | `Ryzen 7 5800X` / `RTX 3060 Ti` / `Laptop browser` / `Desktop browser` | RECORDED (ASSUMPTION) |
| `Hashrate` | profile hashrate from the block | RECORDED (ASSUMPTION) |
| `Wall watts` | profile wall watts from the block | RECORDED (ASSUMPTION) |
| `Daily coins` (native units, 6 decimals) | per-coin daily coins from the block | DERIVED (host) + ESTIMATE |
| `Gross XMR/day` | per-coin gross from the block | DERIVED (host) + ESTIMATE |
| `Net XMR/day (HQ Tier 2)` | per-coin net at Tier 2 from the block | DERIVED (host) + ESTIMATE |
| `Verdict` | `Above breakeven` / `Below breakeven` | DERIVED (host) + ESTIMATE |

Rows: one per reference profile (6 rows — XMR × Ryzen 7 5800X,
XMR × Laptop browser, XMR × Desktop browser, KAS × RTX 3060 Ti,
RVN × RTX 3060 Ti, ERG × RTX 3060 Ti). Empty state (verbatim): a coin
with no live inputs shows `Not computed yet` for that row, with the
STALE tag naming the missing input.

**Panel group 2 — Breakeven** (per coin; Tier 2 base case + US average)

Heading: `Profitability — breakeven`

| Field (verbatim label) | Provenance tag |
|---|---|
| `Breakeven H/W (HQ Tier 2)` | DERIVED (host) + ESTIMATE |
| `Breakeven H/W (US avg)` | DERIVED (host) + ESTIMATE |
| `Current H/W` | DERIVED (host) + ESTIMATE |
| `Distance to breakeven` (ratio) | DERIVED (host) + ESTIMATE |
| `Breakeven electricity price (¢/kWh)` | DERIVED (host) + ESTIMATE |
| `Verdict` (`Above breakeven` / `Below breakeven`) | DERIVED (host) + ESTIMATE |

Empty state (verbatim): a coin with no live inputs: `Not computed yet`.

**Panel group 3 — Electricity sensitivity** (net XMR/day per coin/profile)

Heading: `Profitability — electricity sensitivity`

| Field (verbatim label) | Provenance tag |
|---|---|
| `Net XMR/day (HQ Tier 1)` | DERIVED (host) + ESTIMATE |
| `Net XMR/day (HQ Tier 2)` | DERIVED (host) + ESTIMATE |
| `Net XMR/day (US avg)` | DERIVED (host) + ESTIMATE |
| `Net XMR/day (proposed tariff)` | DERIVED (host) + ESTIMATE |

Risk-scenario row label (verbatim): `Proposed tariff — not in effect`.

**Panel group 4 — Pool fees** (XMR under the three XMR pools; other coins noted)

Heading: `Profitability — pool fees`

| Field (verbatim label) | Provenance tag |
|---|---|
| `Pool` | RECORDED |
| `Fee` | RECORDED |
| `Net XMR/day (HQ Tier 2)` | DERIVED (host) + ESTIMATE |

KAS/RVN/ERG note (verbatim): `2Miners 1% fee applied`.

**Panel group 5 — Split projection** (per coin at Tier 2; ESTIMATE, XMR/day)

Heading: `Profitability — 75/25 split projection`

| Field (verbatim label) | Provenance tag |
|---|---|
| `User share (75%)` | DERIVED (host) + ESTIMATE |
| `ATLAS share (25%)` | DERIVED (host) + ESTIMATE |
| `User net position` | DERIVED (host) + ESTIMATE |

Projection note (verbatim): `Projection only — not earnings`.

**Panel group 6 — Your hardware** (null while Gate 1 is unmeasured)

Heading: `Profitability — your hardware`

| Field (verbatim label) | Value today |
|---|---|
| `Measured hashrate` | `Cannot estimate — hashrate not measured` |
| `Measured wall watts` | `Cannot estimate — hashrate not measured` |
| `Net XMR/day` | `Cannot estimate — hashrate not measured` |

All three fields show the verbatim reason while Gate 1 is unmeasured
(the block's `yourHardware` values are all null). No hashrate number,
no estimate, no benchmark is ever shown here.

**Panel group 7 — Inputs and last sync** (provenance for every input)

Heading 7a: `Profitability — inputs`

Every input: value, source, `fetched_at` + age; STALE tag naming any
stale input (design §6 rules, e.g. `STALE — KAS network stats 73 min old`).
Electricity rates appear here as ¢/kWh inputs with source + effective
date. No USD value is rendered in this panel (the `audit_usd` block of
the host export is never mirrored — §3.3 — and never rendered).
**Clarification (found in verification):** input values are rendered
bare, with no currency unit — the only unit suffix rendered in this
panel is `¢/kWh` on electricity-rate rows (key prefix `rate_`), per
D-M9-3. Labels and sources are metadata and may name a pair (e.g. the
label `USD/CAD rate`); the no-fiat rule constrains displayed AMOUNTS
(no currency symbol, no currency code attached to a number), not
metadata words. The §5.3 probe enforces exactly that: no `$`, and no
number adjacent to a currency code.

Heading 7b: `Profitability — last sync`

Profitability `syncedAt` + age + tag; coordinator `syncedAt` + age +
tag. STALE naming which source is stale. `Not synced yet` when a block
has never synced (never `0`, never a guessed time). When the host
export has never landed, the panel shows the verbatim state
`Profitability export not yet synced — no figures` (the section's
panels 1a–6a then show `Not computed yet` throughout).

**Copy that must NOT appear in this section:** any wallet address,
token hash, session token, password hash, or credential; any per-user
identifier or row; any hashrate number presented as ATLAS's without a
`MEASURED` tag and a measurement time; the words "verified",
"confirmed", or a checkmark next to any worker, address, or hashrate
that has only passed format checks or self-report; the word "secure"
as a verdict; "There is no miner yet" (stale copy, Mission 4 finding 4
— carried, §7); any earnings, balance, or payout figure derived from
shares or hashrate; any USD/fiat figure; any combined "total earnings"
mixing estimated and confirmed figures; any guaranteed-profit wording
("guaranteed", "will earn", "profit" without the ESTIMATE tag and the
§1.2 note). Confirmed earnings appear ONLY as the reused dashboard
figure in the §2.2 reuse rule, SIMULATION-tagged, never combined with
any estimate.

---

## 2. `getMining` profitability block — computed server-side from the ALREADY-MIRRORED singleton row

### 2.1 Field names (must match the host export)

Field names follow `data/profitability.json` (design §1 — Lane C) and,
where a field is reused, `data/dashboard.json` exactly, so the mirror
and the host can be compared field-for-field. **Because
`data/profitability.json` does not exist yet at build time (§0 gap 1),
every profitability field below is defined from the design's
definitions, not from a landed file.** If Lane C's export names a field
differently, the parent MUST record the difference in the build report
and map it in the `profitability` block — it must NOT silently rename a
design field, and must NOT invent a value for a field the export does
not carry (that field is UNAVAILABLE with its verbatim reason, never
approximated).

**Input records (the inputs block).** One record per live input, each
with value, source, `fetched_at`:

| Input key | Meaning | Source (design D-M9-4) |
|---|---|---|
| `xmr_price_usd` | XMR price (USD) | CoinGecko `simple/price` |
| `xmr_network_hashrate_hps` | XMR network hashrate (difficulty ÷ 120 s, derived by the host module) | MoneroOcean `/network/stats` |
| `xmr_block_reward` | XMR block reward (native) | MoneroOcean `/network/stats` |
| `xmr_blocks_per_day` | XMR blocks/day (720 at 120 s) | Derived from block time |
| `kas_network_hashrate_hps` / `rvn_network_hashrate_hps` / `erg_network_hashrate_hps` | Network hashrate per coin | 2Miners `api/stats` per coin |
| `kas_block_reward` / `rvn_block_reward` / `erg_block_reward` | Block reward (native) per coin | 2Miners `api/stats` per coin |
| `kas_blocks_per_day` / `rvn_blocks_per_day` / `erg_blocks_per_day` | Blocks/day per coin | Derived from block time |
| `kas_price_usd` / `rvn_price_usd` / `erg_price_usd` | Price (USD) per coin | CoinGecko `simple/price` |
| `usd_cad_rate` | USD/CAD rate | CoinGecko `exchange_rates` |
| `rate_hq_tier1_cad_per_kwh` (7.065) / `rate_hq_tier2_cad_per_kwh` (11.142) | HQ tariff constants (¢ CAD/kWh) | Tariff constant, source + effective date |
| `rate_us_avg_usd_per_kwh` (17.23) | US average (¢ USD/kWh) | EIA, CARRIED |
| `rate_proposed_qc_cad_per_kwh` (19.5) | Proposed Quebec blockchain tariff — RISK SCENARIO only | Labelled, never a base-case input |
| `fee_moneroocean_bps` (0) / `fee_supportxmr_bps` (60) / `fee_p2pool_bps` (0) / `fee_2miners_bps` (100) | Pool fees | `config/pool-rewards.json` / Obj 4 CARRIED |
| `profile_xmr_ryzen_hashrate_hps` (10,000) / `profile_xmr_ryzen_wall_watts` (171) | Ryzen 7 5800X profile | Obj 4 / M4 CARRIED, ASSUMPTION |
| `profile_kas_gpu_hashrate_hps` (480,000,000) / `profile_kas_gpu_wall_watts` (150) | RTX 3060 Ti / KAS | Obj 4 CARRIED, ASSUMPTION |
| `profile_rvn_gpu_hashrate_hps` (27,000,000) / `profile_rvn_gpu_wall_watts` (240) | RTX 3060 Ti / RVN | Obj 4 CARRIED, ASSUMPTION |
| `profile_erg_gpu_hashrate_hps` (137,000,000) / `profile_erg_gpu_wall_watts` (132) | RTX 3060 Ti / ERG | Obj 4 CARRIED, ASSUMPTION |
| `profile_xmr_laptop_hashrate_hps` (200) / `profile_xmr_laptop_wall_watts` (45) | Laptop browser | M4 CARRIED, ASSUMPTION |
| `profile_xmr_desktop_hashrate_hps` (850) / `profile_xmr_desktop_wall_watts` (50) | Desktop browser | M4 CARRIED, ASSUMPTION |

**Per-profile coin figure (one row per reference profile — 6 rows).**

| Host source | Profitability block field | Notes |
|---|---|---|
| §1 formula from the inputs block | `coins[]: { coin, profile, algo, hashrateHps, wallWatts, computed, dailyCoinsNative, grossXmrPerDay, netXmrPerDayTier1, netXmrPerDayTier2, netXmrPerDayUsAvg, netXmrPerDayProposedTariff, verdictTier2, breakevenHwTier2, breakevenHwUsAvg, currentHw, ratioTier2, breakevenCentsPerKwh, userShareXmrPerDay, atlasShareXmrPerDay, userNetXmrPerDay }` | `computed: false` + all figure fields null when the coin has no live inputs → `Not computed yet`. `verdictTier2` is `Above breakeven` / `Below breakeven` / null. `currentHw` = hashrate ÷ wall watts (XMR rows only; null for GPU rows, whose H/W unit is not comparable — the breakeven H/W gate is an XMR/RandomX gate). |
| §1 formula at each XMR pool fee | `poolFees[]: { pool, feeLabel, netXmrPerDayTier2 }` — MoneroOcean `0%`, SupportXMR `0.6%`, P2Pool `0%` | Fee applied to projected gross coins only, ESTIMATE. KAS/RVN/ERG carry no pool-fee row; the panel note `2Miners 1% fee applied` covers them. |
| Gate 1 unmeasured | `yourHardware: { measuredHashrateHps: null, measuredWallWatts: null, netXmrPerDay: null, reason: "Cannot estimate — hashrate not measured" }` | ALWAYS null in this mission. |
| `data/dashboard.json` earnings block (REUSED, D-M9-2) | `confirmed: { confirmedPiconero, mode }` | The dashboard block's confirmed figure by reuse — never recomputed, never combined with any estimate. |
| — (mirror state) | `exportedAt`, `profitabilitySyncedAt`, `coordinatorSyncedAt`, `profitabilityExportMissing`, `stale`, `staleInputs[]` | §2.2 / §4. |
| — (mirror derivation) | `mirrorDerivedFigures` | §2.4 — the mirror side of the comparison (re-derived from the stored inputs by the §1 formula). |
| — (host verification) | `hostVerifiedFigures` | §2.4 — the host's own computed figures, carried in the mirrored export payload. |
| — (comparison) | `mismatch` (boolean), `mismatchDetails` (list of disagreeing figure names, e.g. `XMR.netXmrPerDayTier2`) | §2.4. |

### 2.2 Derivation rules (server-side, in `getMining`)

- The block is computed inside the existing `getMining` action from
  the mirrored singleton row ONLY (`mining_profitability`, §3.2) plus
  the already-computed dashboard block for the confirmed-earnings
  reuse. **No new ingest action for the profitability block itself
  beyond `ingestProfitabilityState` (§3.3). No new action at all for
  the derived figures.** If a derived field is missing, extend this
  `profitability` block — do not create a new table, a new action, or
  a new refresh step (design §1, carried).
- **Formula (binding, design §1 — implemented exactly in
  `server/src/profitability.ts`, `deriveProfitabilityFigures`):**
  `daily coins = (your hashrate / network hashrate) × blocks/day ×
  block reward × (1 − pool fee)`; `gross $/day = daily coins × price
  (USD)`; `electricity $/day = wall watts × 24 / 1000 × price per kWh
  (USD)` — CAD rates converted at the recorded `usd_cad_rate`;
  `net $/day = gross − electricity`; `net XMR/day = net $/day ÷ XMR
  price (USD)`; `gross XMR/day (non-XMR) = gross $/day ÷ XMR price`;
  `breakeven H/W = (electricity $/day per wall watt) ÷ (gross $/day
  per H/s)`; `breakeven ¢/kWh = gross $/day ÷ kWh/day × 100`;
  `user share = 0.75 × gross XMR/day`;
  `user net = 0.75 × gross XMR/day − electricity $/day ÷ XMR price`.
  Money inside the derivation is USD; conversion to XMR/day happens
  only at the final step, at the recorded XMR price. The USD
  intermediates are NEVER stored in the mirror and NEVER rendered —
  the ingest strips the host export's `audit_usd` block (§3.3).
- **Host-verified figures** are the host module's own computed figures
  carried in the stored export payload (`coins[]` + `poolFees[]` as
  ingested). **Mirror-derived figures** are re-derived server-side by
  `deriveProfitabilityFigures` from the stored inputs block with the
  same §1 formula. The two are compared per §2.4.
- **Confirmed earnings (D-M9-2, binding):** the block reuses the
  dashboard block's `confirmedPiconero` (ledger `SUM`, SIMULATION-tagged
  while mode is `simulation-only`). It never recomputes confirmed
  earnings, balances, lifetime, or payouts. If the export's own
  `confirmedEarnings.confirmedPiconero` disagrees with the dashboard's
  figure, that is a mismatch (§2.4, `mismatchDetails` gains
  `confirmedEarnings`) and the dashboard figure is shown — the
  dashboard is the authority for confirmed earnings, never the
  profitability export.
- **Your hardware:** ALWAYS null in this mission, with the verbatim
  reason `Cannot estimate — hashrate not measured`. The estimate is
  never derived from pool-wide hashrate, never a guessed number, never
  a benchmark presented as a measurement, never back-filled from
  `workers.reported_hashrate_hps`.
- **Scope (D-M9-13):** the section renders the host-global view. Do
  NOT invent a login, a hardware picker, or demo rows.
- **Secrets:** no token, session token, password hash, seed phrase,
  private key, wallet address, or credential is ever mirrored or
  displayed. No `SELECT *` over `workers` in the profitability path
  (the ingest reads only `data/profitability.json`).

### 2.3 Expected live values of the block (today — the acceptance baseline)

Until Lane C lands the host export AND the first refresh ingests it:
`profitabilityExportMissing: true`, `exportedAt: null`,
`profitabilitySyncedAt: null`, `coins: []`,
`yourHardware` all null + verbatim reason,
`confirmed.confirmedPiconero: 0` (reused from the dashboard),
`mismatch: false`, `mismatchDetails: []`,
`hostVerifiedFigures: null`, `mirrorDerivedFigures: null`,
`stale: true`, `staleInputs: ["profitability export — not synced yet"]`.
The section then renders `Not computed yet` throughout panels 1a–6a
and the §1.3 panel-7b verbatim state — the honest state at build time,
not a failure.

After the first profitability ingest lands (to be confirmed by the
parent against the live mirror — §0 gap 3): `coins` holds 6 rows with
figures derived from the live export, `mismatch: false`,
host == mirror figures within the §2.4 tolerance, mirrors fresh;
your-hardware null + verbatim reason; confirmed-earnings block
identical to the dashboard block; no credential field in the mirror.

### 2.4 MISMATCH MECHANISM (binding, D-M9-11 — design §7, M7 §6 / M8 §7 carried)

`getMining` computes, server-side, in the `profitability` block
(`server/src/profitability.ts`, `compareProfitabilityFigures`):

- **`hostVerifiedFigures`** — the host's own computed figures, read
  from the stored export payload: per profile-row `dailyCoinsNative`,
  `grossXmrPerDay`, `netXmrPerDayTier1/Tier2/UsAvg/ProposedTariff`,
  `breakevenHwTier2`, `breakevenHwUsAvg`, `breakevenCentsPerKwh`,
  `ratioTier2`, `userShareXmrPerDay`, `atlasShareXmrPerDay`,
  `userNetXmrPerDay`; plus per XMR pool `netXmrPerDayTier2`. Null
  until the first ingest lands.
- **`mirrorDerivedFigures`** — the same figure set, re-derived
  server-side from the stored inputs block by the §1 formula
  (`deriveProfitabilityFigures`). Null until the first ingest lands.
  Null figures (a coin with no live inputs) compare equal only to
  null on the other side — a null-vs-number disagreement is a
  mismatch, never silently equal.
- **`mismatch`** (boolean) + **`mismatchDetails`** (array of the
  disagreeing figure names, e.g. `["XMR.netXmrPerDayTier2",
  "poolFees.SupportXMR"]`): true when ANY compared figure disagrees
  beyond the rounding tolerance below. Agreement on today's
  not-yet-synced state (both sides null) is a valid trivial agreement
  and says nothing about the check working — the §5.3 sandbox tests
  must prove the check with non-zero fixture data.
- **Rounding tolerance (binding):** two figures agree when
  `|mirror − host| ≤ max(1e-9, 1e-6 × |host|)` (absolute 1e-9 XMR/day
  floor, relative 1e-6). The tolerance exists because the host computes
  in USD and converts at the final step while the mirror re-derives
  from the recorded inputs; it is a rounding allowance, never a
  licence to present a wrong figure. Any disagreement beyond it is a
  mismatch, full stop.
- **Confirmed-earnings secondary check:** the export's
  `confirmedEarnings.confirmedPiconero` is compared against the
  dashboard block's `confirmedPiconero`. A disagreement adds
  `"confirmedEarnings"` to `mismatchDetails` and the dashboard figure
  is shown. The ledger comparison in the dashboard/admin blocks
  remains the primary earnings check; this check must not be
  substituted for it.
- **On mismatch, the component MUST:** show the HOST-VERIFIED figures
  (from the export payload, not the mirror-derived ones) in every
  profitability figure; show the verbatim note
  `Mirror mismatch — figures under investigation` in the section
  header area next to the affected figures; keep listing the
  mirror-derived figures labelled as mirror figures under
  investigation — never silently present them as real; show no
  mirror-derived figure as a confirmed earning or a balance. The
  mismatch is logged artifact-side in the honest-failure pattern
  (surfaced, not swallowed). On agreement, show the (equal) figures
  with no mismatch note.
- **The profitability section must NOT display sandbox-only rows at
  all** — it reads only the durable live mirror, never a sandbox/test
  database.

---

## 3. Migrations — additive migration 0010 + `ingestProfitabilityState`

### 3.1 Why a singleton row (M7 migration-0007 pattern, design D-M9-1)

Design D-M9-1 states "No new host DB tables" and "One new artifact
mirror singleton row (migration 0009, M7 migration-0007 pattern —
scalars only, no log tables needed)". The artifact side therefore adds
ONE singleton table holding the mirrored export payload (the export is
one document; its figures are scalars, not rows). The host side of
D-M9-1 is untouched (no new host tables). The migration number is
0010, not 0009 — see §0.1 deviation 1 (0009 already exists).

### 3.2 Migration 0010 — `drizzle/0010_profitability_mirror.sql`

**Chosen shape: one singleton row, id = 1 enforced by CHECK, holding
the export payload as JSON** (the `snapshots.payload` precedent — the
export is one document; typed columns would duplicate its whole
shape). The ingest upserts the row in one transaction; identical
re-ingest → `upToDate`, `synced_at` untouched.

**Exact table and columns:**

`mining_profitability` — mirror of host `data/profitability.json`:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY CHECK (`id` = 1) | Singleton row (M7 pattern) |
| `payload` | TEXT NOT NULL | Export JSON as ingested (inputs, coins, poolFees, yourHardware, confirmedEarnings) — `audit_usd` stripped at ingest, never stored |
| `exported_at` | INTEGER | Host export instant (epoch seconds) |
| `synced_at` | INTEGER | Artifact ingest instant (epoch seconds) of the last CHANGED write |

No token, session token, password hash, seed, private key, or wallet
field in this table — the host export carries none, and the ingest
never adds one. No USD figure is stored (the `audit_usd` block is
stripped by the zod input schema, which drops unknown keys). No other
columns.

**Schema file:** add the table to `server/src/schema.ts` (drizzle
definition mirroring the SQL exactly, with the singleton CHECK) and
add the journal entry for 0010 in `drizzle/meta/_journal.json`
(idx 9, following 0009's idx 8) — same pattern as M6 migration 0006 /
M7 migration 0007 / M8 migration 0008.

**Pure module:** add `server/src/profitability.ts` exporting the pure
functions the handlers use (see §0.1 deviation 4):
`deriveProfitabilityFigures(inputs)` (mirror-side re-derivation by
the §1 formula), `compareProfitabilityFigures(host, mirror)`
(tolerance comparison returning `mismatchDetails`),
`profitabilityStaleInputs(inputs, nowSec)` (STALE naming),
`buildProfitabilityBlock(args)` (assembles the §2 block from the
stored row + dashboard confirmed figure + coordinator syncedAt),
`upsertProfitabilityRow(db, payloadJson, exportedAt, nowSec)` (the
singleton upsert + `upToDate` decision, used by the ingest handler).
The module imports only `drizzle-orm` and the schema — no SDK, no
network, no file reads — so the sandbox tests execute the real code.

### 3.3 `ingestProfitabilityState` (extend the existing ingest pattern — no new refresh step)

Add a new action `ingestProfitabilityState` in `server/src/actions.ts`,
riding the existing refresh step family (same step family as the
rewards/admin mirrors — no new refresh step, no new cron, no new
schedule; see §4 for the refresh-task step-9 instruction):

- The ingest payload is the host `data/profitability.json` export
  (when it exists), mapped field-for-field per §4. The action upserts
  the singleton row in one transaction: `payload` = the export as
  validated by the zod input schema (§2.1 — `audit_usd` is dropped
  because the schema does not declare it), `exported_at` =
  `exportedAt`, `synced_at` = now on a CHANGED write only.
- **Missing export:** if `data/profitability.json` does not exist yet
  (§0 gap 1 — the state at build time), the action MUST skip cleanly:
  it reports `profitabilityExportMissing: true`, leaves the table
  untouched, and does NOT advance any `syncedAt`. The profitability
  block then reports `profitabilitySyncedAt: null` →
  `profitabilityExportMissing: true` + STALE (§4). Never fabricate
  figures.
- **Upsert semantics:** if the incoming payload is identical to the
  stored payload (canonical JSON comparison) AND `exported_at` is
  unchanged, the ingest reports `upToDate: true` with 0 changes and
  does NOT touch `synced_at` (a re-ingest of unchanged data is never
  mislabelled as a fresh sync — M5 §1.4 / M6 §10 / M7 §3.3 / M8 §3.3,
  carried). If the payload differs, upsert the row and set `synced_at`
  to now. The block `profitabilitySyncedAt` is the ingest time of the
  last CHANGED write.
- **Zod input schema** (`profitabilityExportInput`, §2.1): `exportedAt`
  int, `mode` string, `emergencyStop` boolean, `inputs[]` (key/label/
  value/unit/source/fetchedAt), `coins[]` (the §2.1 per-profile figure
  set, nullable figure fields), `poolFees[]` (pool/feeLabel/
  netXmrPerDayTier2), `yourHardware` (all-nullable + reason string),
  `confirmedEarnings` (confirmedPiconero int + mode string). Unknown
  keys (including `audit_usd`) are stripped by zod — the mirror never
  stores a USD figure.
- The action's existing behavior for the other mirrors is otherwise
  unchanged: ledger ingest stays insert-only, host-id dedupe stays
  enforced, re-ingest of unchanged rows still reports "already up to
  date".

### 3.4 What this does NOT do (hard limits)

- This does NOT delete, alter, expire, or relabel any existing mirror
  row, and does NOT decide the fate of any sandbox-only rows.
- This does NOT touch `client/src/RewardAccounting.tsx`,
  `client/src/UserDashboard.tsx`, or `client/src/AdminCommandCenter.tsx`
  in any way — not one line. The Mission 6 finding-1 repair
  (replacing the hardcoded zero literals in `RewardAccounting.tsx`
  with values derived from the mirrored ledger totals) is NOT
  authorized and is NOT part of this build. The profitability
  section's mismatch mechanism is PREVENTION (the defect class cannot
  recur silently in the new section); it is not a repair of the
  existing section.
- This does NOT change the Mission 6 rewards block, the Mission 7
  dashboard block, the Mission 8 admin block, the coordinator block,
  or any existing panel's copy. The existing Admin command center
  section keeps rendering exactly as it does on build `bafa9e63`,
  until a repair is separately authorized.
- This does NOT add any host table, host column, or stored aggregate
  (design D-M9-1 host side untouched). The host export
  `data/profitability.json` and module `core/atlas_profitability.py`
  are Lane C's scope, not this lane's; this spec only consumes them.
- This does NOT activate mining, trading, payouts, wallets, or keys,
  and does NOT change any config, limit, or safety setting. Emergency
  stop stays ON; simulation-only throughout.

---

## 4. Refresh — rides the existing flow (D-M9-13, D-M9-10)

- **No new cron. No new schedule.** The profitability section rides
  the existing refresh flow: the 10-minute coordinator pass (which
  exports `coordinator.json` and runs the guarded sub-steps) plus the
  existing `refreshAtlasData` round-trip. The profitability ingest
  (§3.3) rides the existing refresh step family as step 9 of the
  refresh-task instruction (same step as the rewards/admin mirrors) —
  no new refresh step is added. The profitability export rides the
  existing coordinator pass as a guarded sub-step (never fails the
  pass, logs no decision of its own) — same pattern as M6/M7/M8
  (D-M9-13). If the refresh fails, the profitability section goes
  STALE (§4.1) — it does not retry, re-fetch, or invent a sync. The
  refresh failure (M3 finding 1) is NOT repaired here.
- **Refresh-task step 9 (added to the `refreshAtlasData` instruction,
  after step 8):** "9. Profitability mirror (Master Mission 9): read
  ~/workspace/atlas/data/profitability.json (the host profitability
  export). If the file is missing or unreadable, call the
  ingestProfitabilityState action exactly once with export = null (it
  reports profitabilityExportMissing and stores nothing) — never
  invent profitability figures, and never let a profitability failure
  block the earlier ingest calls. SECURITY — never read, copy, or pass
  the export's audit_usd block anywhere (USD intermediates are audit
  data only, never rendered); never pass any token, token hash,
  session token, password hash, seed, private key, or wallet address —
  the profitability export carries none and none may be added.
  Otherwise call the ingestProfitabilityState action exactly once with
  export mapped field-for-field from profitability.json: exportedAt =
  exported_at; mode; emergencyStop = emergency_stop; inputs =
  inputs mapped to { key, label, value, unit, source, fetchedAt =
  fetched_at }; coins = coins mapped to { coin, profile, algo,
  hashrateHps = hashrate_hps, wallWatts = wall_watts, computed,
  dailyCoinsNative = daily_coins_native, grossXmrPerDay =
  gross_xmr_per_day, netXmrPerDayTier1 = net_xmr_per_day_tier1,
  netXmrPerDayTier2 = net_xmr_per_day_tier2, netXmrPerDayUsAvg =
  net_xmr_per_day_us_avg, netXmrPerDayProposedTariff =
  net_xmr_per_day_proposed_tariff, verdictTier2 = verdict_tier2,
  breakevenHwTier2 = breakeven_hw_tier2, breakevenHwUsAvg =
  breakeven_hw_us_avg, currentHw = current_hw, ratioTier2 =
  ratio_tier2, breakevenCentsPerKwh = breakeven_cents_per_kwh,
  userShareXmrPerDay = user_share_xmr_per_day, atlasShareXmrPerDay =
  atlas_share_xmr_per_day, userNetXmrPerDay =
  user_net_xmr_per_day }; poolFees = pool_fees mapped to { pool,
  feeLabel = fee_label, netXmrPerDayTier2 =
  net_xmr_per_day_tier2 }; yourHardware = your_hardware mapped to
  { measuredHashrateHps = measured_hashrate_hps, measuredWallWatts =
  measured_wall_watts, netXmrPerDay = net_xmr_per_day, reason };
  confirmedEarnings = confirmed_earnings mapped to
  { confirmedPiconero = confirmed_piconero, mode }."
  (If Lane C's landed field names differ from these, the parent maps
  them and records the difference — §0 gap 2.)
- **STALE rule (D-M9-10, binding):** the profitability section is
  STALE when any live input (price or network stats for any coin) is
  > 1 h old, measured from that input's `fetched_at` to now (3600 s).
  The STALE tag names the stale input (e.g.
  `STALE — KAS network stats 73 min old`). "Not computed yet" when a
  coin has never been computed. A re-ingest of unchanged data reports
  "already up to date" and does NOT advance `syncedAt` (Mission 3
  finding 1, carried). If the export has never landed, the section is
  STALE by the "not synced yet" rule.
- **"Not synced yet":** when a block has never synced (`syncedAt`
  null), that block shows `Not synced yet` instead of a time — never
  `0`, never a guessed time. If any block has never synced, the section
  is STALE. Until the first profitability ingest lands,
  `profitabilitySyncedAt` is null and the profitability section is
  STALE by this rule — which is the honest state at build time, not a
  failure.
- **Last-sync panel shows BOTH mirror sync timestamps**
  (profitability block `syncedAt`, coordinator block `syncedAt`), each
  with its age (`synced <date time> (<age> ago)`), each with its own
  STALE / SYNCED tag. The two timestamps are never merged into one
  "last sync" figure.
- **Re-ingest honesty:** a re-ingest of unchanged data reports "already
  up to date" and does NOT refresh any `syncedAt`. The profitability
  section's sync time is the mirror ingest time of *changed* data, not
  the time of the last refresh attempt.
- **Host `dashboard.json` `sync.stale` is NOT the profitability STALE
  flag.** It measures host-export freshness. The UI STALE flag is
  computed from the input `fetched_at` values and the mirror
  `syncedAt` in the `profitability` block. Do not wire the host flag
  into the UI.

---

## 5. Exact file change list and verification

### 5.1 File change list (create/edit, with paths)

Paths are relative to the artifact ts-space working tree
(`~/workspace/ts-spaces/atlas-command-center/`).

| # | File | Change |
|---|---|---|
| 1 | `client/src/ProfitabilityIntelligence.tsx` | CREATE — `ProfitabilityIntelligenceSection`, seven panel groups per §1.3, zero buttons/inputs/links/forms |
| 2 | `client/src/Mining.tsx` | EDIT — import + `<ProfitabilityIntelligenceSection m={m} />` directly below `<AdminCommandCenterSection m={m} />`, above Settings. Nothing else in this file changes. Do NOT touch the two stale "no miner yet" strings (repair NOT authorized). Do NOT touch the hook order. |
| 3 | `server/src/schema.ts` | EDIT — add drizzle definition for `mining_profitability` (§3.2). Nothing else changes. |
| 4 | `server/src/profitability.ts` | CREATE — pure derivation/comparison/block-assembly functions (§3.2): `deriveProfitabilityFigures`, `compareProfitabilityFigures`, `profitabilityStaleInputs`, `buildProfitabilityBlock`, `upsertProfitabilityRow` |
| 5 | `drizzle/0010_profitability_mirror.sql` | CREATE — additive migration 0010 (§3.2) |
| 6 | `drizzle/meta/_journal.json` | EDIT — journal entry idx 9 for 0010 (following 0009's idx 8) |
| 7 | `server/src/actions.ts` | EDIT — (a) add `profitabilityExportInput` zod schemas + `ingestProfitabilityState` (§3.3, rides the existing refresh step family — no new refresh step); (b) `getMining` gains the `profitability` block (§2, via `buildProfitabilityBlock`); (c) `refreshAtlasData` instruction gains step 9 (§4). No new action for the derived figures. No change to the existing `rewards`, `dashboard`, `coordinator`, or `admin` blocks. |

**NOT changed:** `client/src/RewardAccounting.tsx` (finding-1 repair NOT
authorized), `client/src/UserDashboard.tsx` (no change),
`client/src/AdminCommandCenter.tsx` (no change), any host file under
`~/workspace/atlas/` (`core/`, `config/`, `data/` — Lane C's scope,
not this lane's), any cron or schedule, any other tab or section, any
safety setting, the Energy Orb artifact (untouched, out of scope).

Resulting Mining tab order (verify after edit): MiningDashboard,
WalletCenter, EarningsSection, HistorySections, PayoutSection,
CalculatorSection, MinerPrototypeSection, CoordinatorSection,
RewardAccounting, UserDashboard, AdminCommandCenter,
**ProfitabilityIntelligence**, SettingsSection, HelpSection.

### 5.2 Typecheck + sandbox verification steps (build lane, before handoff to Lane E)

Same method as M6 Lane D (§3) and M7/M8 Lane D (§5.3), extended for
the profitability block. All sandbox work runs in `/tmp` against an
in-memory SQLite DB (drizzle + `bun:sqlite`) with fixture data only;
the live `app.db` is never touched and durable rows are unchanged
(0 batches / 0 ledger entries).

1. **Typecheck:** `bun run typecheck` (client + server) in the
   ts-space — PASS, exit 0, zero errors. Any error found is fixed in
   this build's files only.
2. **Migration 0010 validation:** apply 0010 against an in-memory
   SQLite DB shaped like the post-0009 schema; verify the singleton
   table exists with the id=1 CHECK; verify a second row with id ≠ 1
   is rejected by the CHECK; verify the journal entry (idx 9) is
   well-formed and follows 0009's idx 8.
3. **Grep checks on `ProfitabilityIntelligence.tsx`:** zero
   `<button>`, `<input>`, `<a `, `<form>`; zero `$` characters other
   than template-literal `${` interpolations (verify with
   `grep -v '\${'` — a bare `$` is a fiat figure and a defect); zero
   currency-marked amounts in the rendered output (§5.3 step 11);
   zero hardcoded displayed-figure literals — grep for
   `0.000000 XMR/day` and bare numeric XMR/day literals outside the
   verbatim copy strings listed in §1.3 (any hit outside those strings
   is a defect and must be removed); verbatim strings from §1.2/§1.3
   confirmed present — EXCEPT `Cannot estimate — hashrate not
   measured`, which is server-supplied (the block's `yourHardware`
   reason) and MUST NOT appear as a literal in the component: it is
   verified present in the §5.3 step-11 rendered output instead;
   no `password_hash`, `token_hash`, `token_salt`,
   `session_token`, `seed`, `private_key`, or wallet-address pattern
   anywhere in the new/changed files; no `SELECT *` over `workers` in
   the profitability path.
4. **Changed-file sweep:** only the seven files in §5.1 changed. Any
   other diff is out of scope and must be reverted or explicitly
   reported.
5. **Sandbox `getMining` block (missing-export baseline):** with no
   `mining_profitability` row, `buildProfitabilityBlock` returns the
   §2.3 baseline — `profitabilityExportMissing: true`,
   `exportedAt: null`, `profitabilitySyncedAt: null`, `coins: []`,
   your-hardware null + verbatim reason, confirmed figure reused from
   the dashboard (0), `mismatch: false`, `hostVerifiedFigures: null`,
   `mirrorDerivedFigures: null`, `stale: true`.
6. **Sandbox ingest with a non-zero profitability fixture:**
   (a) Build a fixture `profitability.json` from the Obj 4 inputs
   (§5.2 fixture table below) with an INDEPENDENT reference
   implementation of the §1 formula written in the test file — NOT by
   calling `deriveProfitabilityFigures` to produce the host figures
   (that would make the comparison trivially true). Assert the
   artifact's `deriveProfitabilityFigures` reproduces the Obj 4
   net/day figures for all four coins at all three rates within
   rounding (XMR +$0.021 / +$0.138 / −$0.367; KAS −$0.280 / −$0.178 /
   −$0.620; RVN −$0.349 / −$0.185 / −$0.893; ERG −$0.142 / −$0.052 /
   −$0.442) and the M4 gates (56.5 H/W at Tier 2, 125.2 H/W at the US
   average, $0.03302/day per kH/s). (b) `upsertProfitabilityRow`
   stores the fixture payload; `buildProfitabilityBlock` returns the
   profitability block with the §2.1 fields, `mismatch: false`,
   host == mirror figures within the §2.4 tolerance, your-hardware
   null + verbatim reason, confirmed-earnings block identical to the
   dashboard block. (Sandbox only — durable storage keeps 0 workers /
   0 shares / 0 ledger entries; no fictional earnings ship.)
7. **Sandbox mismatch proofs (non-zero fixtures):** (a) profitability
   mismatch — tamper ONE stored host figure in the payload (e.g.
   XMR `netXmrPerDayTier2` +0.000100) while the inputs stay unchanged:
   `buildProfitabilityBlock` returns `mismatch: true` with
   `mismatchDetails` naming exactly the tampered figure
   (`XMR.netXmrPerDayTier2`) and the displayed figures switch to
   host-verified; (b) a second sub-case with agreeing non-zero fixture
   figures returns `mismatch: false`. Agreement on zeros/nulls alone
   is NOT accepted as proof of the check. (c) confirmed-earnings
   disagreement — export `confirmedPiconero` ≠ dashboard figure adds
   `"confirmedEarnings"` to `mismatchDetails` and the dashboard figure
   is shown.
8. **Sandbox stale-input proof:** a fixture export with one input
   `fetched_at` > 1 h old (e.g. KAS network stats 73 min old) returns
   the STALE tag naming that input (`STALE — KAS network stats
   73 min old`); all other inputs fresh. A fixture with all inputs
   fresh returns no stale inputs.
9. **Re-ingest reports upToDate:** an identical re-ingest (same
   payload, same `exported_at`) returns `upToDate: true` with 0
   changes, and NO `syncedAt` advances. A changed payload upserts and
   advances `syncedAt`.
10. **Null export returns profitabilityExportMissing:** calling the
    ingest with `export: null` returns `profitabilityExportMissing:
    true` and stores nothing (table still empty).
11. **Desktop probe (sandbox static render):** render
    `ProfitabilityIntelligenceSection` to static HTML with a fixture
    `getMining`-shaped `m` prop (React `renderToStaticMarkup`, in the
    sandbox only): assert the seven panel groups appear in §1.3 order,
    all verbatim strings from §1.2/§1.3 are present, zero `<button>` /
    `<input>` / `<a` / `<form>` elements exist in the rendered output,
    and no `$` / `USD` string appears. **Stated plainly:** this probe
    establishes source + data rendering only. It does NOT establish a
    live render, Mining-tab selection, a real-browser console, or a
    real-viewport 390 px overflow measurement — those remain Lane E
    rendered acceptance items (§6). The build lane MUST NOT claim a
    render it did not perform.
12. **No console errors; mobile 390 px overflow 0** — source-level
    where the build lane cannot render; the rendered proof is Lane E's
    job (§6).

**§5.2 fixture table (Obj 4 inputs, CARRIED — the independent
reference implementation in the sandbox test is fed exactly these):**

| Input | Value |
|---|---|
| USD/CAD | 1.4316 |
| XMR price | $507.17; network hashrate 6,438,803,708 H/s; block reward 0.6; blocks/day 720; profile 10,000 H/s @ 171 W; fee 0% |
| KAS price | $0.02727563; network hashrate 317,016,508,646,590,909 H/s; block reward 1.94454365; blocks/day 864,000; profile 480,000,000 H/s @ 150 W; fee 1% |
| RVN price | $0.00110692; network hashrate 533,882,597,021 H/s; block reward 1,250; blocks/day 1,440; profile 27,000,000 H/s @ 240 W; fee 1% |
| ERG price | $0.205371; network hashrate 713,237,332,484 H/s; block reward 3; blocks/day 888.7; profile 137,000,000 H/s @ 132 W; fee 1% |
| Rates | HQ T1 7.065¢ CAD, HQ T2 11.142¢ CAD, US avg 17.23¢ USD, proposed QC 19.5¢ CAD |
| XMR pool fees | MoneroOcean 0%, SupportXMR 0.6%, P2Pool 0% |

---

## 6. Verification checklist — Lane E (acceptance; execute after deployment)

Lane E executes this against the NEW build id (reported by the parent
after publish). Every item is PASS / FAIL with evidence (capture id or
log excerpt). No item may be marked PASS from source inspection alone
where a render is required.

### 6.1 Rendered checks (fresh interactive audit — desktop 1440 px + mobile 390 px)

- [ ] **E1. Mining tab selects cleanly on desktop (1440 px)** with zero
  console errors; the Profitability intelligence section renders
  directly BELOW the Admin command center section and above Settings;
  tab/section order otherwise unchanged (MiningDashboard, WalletCenter,
  EarningsSection, HistorySections, PayoutSection, CalculatorSection,
  MinerPrototypeSection, CoordinatorSection, RewardAccounting,
  UserDashboard, AdminCommandCenter, ProfitabilityIntelligence,
  SettingsSection, HelpSection).
- [ ] **E2. Desktop-viewport screenshot of the profitability section**
  (1440 px). **ACCEPTANCE CHECK.** Screenshot must show all seven
  panel groups in §1.3 order.
- [ ] **E3. Mobile render (390 px):** Mining tab selects cleanly, all
  seven panel groups present in §1.3 order, zero console errors,
  mobile overflow 0 px at 390 px, cards stacked (no horizontal
  scroll). **NOTE:** the M7 phone-width capture gap (probe viewport
  switch timed out on the heavy WebGL page) is carried here — E3 is
  the item that closes it for this section, and it must be attempted
  and its outcome reported honestly, not assumed.
- [ ] **E4. All estimates honest:** SIMULATION + ESTIMATE tags visible;
  verbatim estimate note `All figures are estimates from live inputs
  and stated assumptions — not earnings, not a promise of profit.`,
  verbatim your-hardware reason `Cannot estimate — hashrate not
  measured`, verbatim projection note `Projection only — not earnings`,
  verbatim risk label `Proposed tariff — not in effect`, verbatim fee
  note `2Miners 1% fee applied` all visible; no figure presented as
  live earnings; no USD/fiat figure anywhere in the section; no wallet
  address, token hash, or credential anywhere in the section; XMR/day
  figures to 6 decimals.
- [ ] **E5. Zero controls:** no button, input, link, or form anywhere
  in the section (DOM check, not just source grep); Start/Stop visibly
  disabled; no hardware picker, no rate input, no recalculate.
- [ ] **E6. STALE rendering check:** with any input > 1 h old (the
  expected state at build time is `profitabilityExportMissing` until
  the first profitability ingest lands), the section renders STALE
  naming the stale source, with figures still shown (labelled STALE),
  not hidden and not presented as fresh. Both mirror sync timestamps
  visible, each with its own STALE / SYNCED tag.
- [ ] **E7. Reload-persistence check — desktop + mobile.
  ACCEPTANCE CHECK.** Reload the page, re-select Mining, confirm the
  section re-renders with the same figures on BOTH viewports. Record
  the reload explicitly (step log, not just a summary count).
- [ ] **E8. Other tabs / orb / refresh / emergency stop still render**
  (Overview desktop: orb, tabs, refresh state, emergency stop ON);
  no regression in the Admin command center section's rendering (its
  content is unchanged; the M6 finding-1 contradiction in Reward
  accounting is carried, NOT fixed — do not report it as a new
  failure, and do not report it as fixed).

### 6.2 Action-layer re-verification (independent, sandbox + live read-only)

- [ ] **E9.** Live `getMining` (read-only) returns the `profitability`
  block with the §2.3 baseline until the first ingest lands
  (`profitabilityExportMissing: true`, `mismatch: false`, confirmed
  figure identical to the dashboard block); after the first ingest,
  figures derived from the live export, `mismatch: false`, host ==
  mirror figures, mirrors fresh; your-hardware null + verbatim
  reason; live mirror still batches `[]` / entries `[]` (no fictional
  earnings shipped; durable storage unchanged).
- [ ] **E10.** Sandbox re-run of §5.3 steps 6–8 (non-zero fixture →
  Obj 4 regression + M4 gates reproduced; mismatch → `mismatch: true`
  + host-verified figures shown + disagreeing field named; agreeing
  non-zero fixtures → `mismatch: false`; stale input → STALE tag
  naming that input; identical re-ingest → `upToDate: true`,
  `syncedAt` unmoved; null export → `profitabilityExportMissing:
  true`, nothing stored).
- [ ] **E11.** No token / session token / password hash / seed /
  private key / wallet address in the `profitability` block, in
  `data/profitability.json`, or in the new mirror table (same
  assertion shape as the M5 mirror test). No USD figure in the mirror
  table or the block (USD lives only under `audit_usd` in the host
  export).
- [ ] **E12.** Migration 0010 applied on the deployed build; journal
  idx 9 present; singleton row holds at most one row (id = 1);
  `profitabilitySyncedAt` null + `profitabilityExportMissing` is
  acceptable before the first profitability ingest lands, if reported
  honestly — never a fabricated zero or a fabricated sync time.
- [ ] **E13.** Diagnostics still green (the existing suite must stay
  green; the new profitability diagnostic — test 26 per design §10 —
  is reported with its number and result; suite must be 26/26).

### 6.3 Explicitly NOT acceptance criteria for this build

- The Mission 6 finding-1 self-contradiction in `RewardAccounting.tsx`
  is NOT fixed by this build and is NOT a failure of this build. Lane E
  records its carried state; it does not fail E1–E13 over it.
- Gate 1 (measured hashrate), the refresh failure, the stale "no miner
  yet" copy, host memory above the 70% cap, and the mempool.space
  dispute are carried, not fixed, not failed here.
- The host profitability module (`core/atlas_profitability.py`) and
  export (`data/profitability.json`) are Lane C's scope; their absence
  at build time is a recorded gap (§0 gap 1), not a failure of this
  build — but the section MUST render the honest
  `profitabilityExportMissing` state until they land.

---

## 7. Known issues carried (NOT fixed by this spec — D-M9-12)

1. **Rendered Mining-tab check NOT established** (M7 finding 1, still
   owed — now the sixth consecutive mission with this gap). No captured
   render ever selects the Mining tab. A repair-authorized Mining-tab
   render capture (select Mining, capture desktop + mobile, console,
   overflow, then reload + re-select Mining) is owed.
2. **Gate 1 still unmeasured** — every hashrate reads "not measured". A
   fresh interactive probe run is owed.
3. **Refresh failure carried** (Mission 3 finding 1, NOT fixed). The
   profitability section labels stale inputs rather than presenting
   them as fresh, but a failed refresh still stalls the mirror.
4. **Stale "no miner yet" copy carried** (Mission 4 finding 4, NOT fixed)
   — exactly two strings in `Mining.tsx`. Repair needs a
   repair-authorized inspection.
5. **Mission 6 finding 1 is latent, not repaired.** The hardcoded zero
   literals in `RewardAccounting.tsx` are still there. The
   profitability mismatch rule detects the shape but the underlying
   display defect is NOT fixed — repair still needs a
   repair-authorized inspection. It does not bite today: the live
   mirror and live host totals are both 0.
6. **Duration secondary check wiring not independently verified** (M7
   finding 6). Dormant at 0 sessions; verify the population path
   before any session exists.
7. **Panel 1 "0 users" wording tension (minor, source-level, M7 finding 7):**
   the dashboard counts distinct user_ids on mirrored ledger entries
   (0), while `mining_users` holds 1 scaffold row (`local-user`, no
   wallet). Unchanged.
8. **"Derived host" tag wording (minor, M7 finding 8):** when mismatch
   is false the confirmed-figure tag reads "Derived host"; it may
   confuse. Unchanged.
9. **SupportXMR fallback not implemented** (D-M5-3, carried) — no
   verified stats-API URL; a URL must never be guessed. (The pool-fee
   panel uses the fee from `config/pool-rewards.json` only; no
   SupportXMR stats fetch is attempted.)
10. **Referral rate 5% is a design parameter to confirm** before any
    real-mode settlement (engine defaults to 500 bps;
    `referral_rate_bps` absent from `pool-rewards.json`).
11. **Minimum payout still null/placeholder** — undecided, needed before
    any payout flow.
12. **D-M5-1 (carried):** browser-probe `session_token_hash` stores
    marker `none:browser-probe` instead of NULL. Confirmed in code; no
    live row to inspect (sessions 0).
13. **Host memory above the 70% cap** (standing, pre-existing; 79–93%
    across the day, 83.6% in the latest audit). Re-scope proposal still
    needs user approval.
14. **mempool.space disputed, not settled.** 000 (timeout) on some
    attempts, 200 on others. Flappy. (Not a profitability input; listed
    because the diagnostics endpoint tests still cover it.)
15. **Daemon restarts of undetermined cause** (carried). Watchdog
    restarts continue. Single instance maintained; not a stop
    condition.
16. **DB file growth, partly unexplained (carried).** The pre-Mission 2
    jump (36,864 → 163,840 B) remains unexplained at page level.
17. **Diagnostics sensitivity:** the suite is sensitive to endpoint
    flapping; a 23/25 with only tests 14/18 failing is the known stall
    signature, not a regression. Test count grows 25 → 26 in this
    mission (new test 26, design §10).
18. **KAS/RVN/ERG live inputs depend on third-party APIs (2Miners,
    CoinGecko)** that the host has not polled in this mission's
    baseline yet — if any is unreachable from this host, that coin's
    figures are STALE by rule (D-M9-4), never fabricated. (Design §9
    finding 18, carried.)

## 8. Handoff checklist (what the build lane receives, and what is owed onward)

- [x] §0: binding inputs + ground truth (host exports read at build
  time; live-mirror state and `data/profitability.json` flagged as
  gaps, to be verified by the parent at publish time).
- [x] §1: component spec — file, placement, seven panel groups with
  verbatim copy.
- [x] §2: `profitability` block — field names (design-defined),
  derivation rules, expected live values, mismatch mechanism (primary
  + confirmed-earnings secondary check).
- [x] §3: migration 0010 (singleton mirror row), `ingestProfitabilityState`,
  pure module `server/src/profitability.ts`, non-repair statement for
  finding 1, `RewardAccounting.tsx`, and `UserDashboard.tsx`.
- [x] §4: refresh — rides existing flow, STALE / "Not synced yet" rules
  over live inputs + two mirror sync timestamps, step-9 instruction.
- [x] §5: exact file change list (7 files), typecheck + sandbox
  verification steps.
- [x] §6: Lane E acceptance checklist (desktop 1440 px + mobile 390 px +
  reload persistence as acceptance checks).
- [x] §7: known issues carried (18 items, none fixed here).
- [ ] **OWED TO THE PARENT (publish):** this lane has no `artifact.*`
  tools. The §5.1 edit lands in the working tree, typechecks, and
  passes the §5.3 sandbox verification — but the NEW BUILD ID is
  issued only when the parent/main agent publishes the tree through
  the artifact tooling. The parent MUST report the new build id to
  Lane E with the §6 checklist; it must NOT be claimed before publish.
- [ ] **OWED TO LANE C (host):** `core/atlas_profitability.py` +
  `data/profitability.json` (design §1, §10) — until they land, the
  section honestly renders `profitabilityExportMissing`. Field names
  must be confirmed against §2.1/§4 (§0 gap 2).

**Stop — specification complete. The edit in §5.1 is executed in the
working tree by this lane, typechecked, and sandbox-verified per §5.3.
Publish (new build id) is owed to the parent; Lane E acceptance is §6.**

---

## 9. Build record (Lane D execution, 2026-11-18/19)

Executed by Lane D in the working tree
(`~/workspace/ts-spaces/atlas-command-center/`). Publish (new build
id) is owed to the parent — see §0.1 deviation 2 / §8.

### 9.1 Files changed (exactly the §5.1 seven)

- CREATE `client/src/ProfitabilityIntelligence.tsx`
  (`ProfitabilityIntelligenceSection`, seven panel groups per §1.3).
- EDIT `client/src/Mining.tsx` — import + one render line directly
  below `<AdminCommandCenterSection m={m} />`, above Settings.
- EDIT `server/src/schema.ts` — `mining_profitability` singleton.
- CREATE `server/src/profitability.ts` — pure derivation/comparison/
  block-assembly (`deriveProfitabilityFigures`,
  `compareProfitabilityFigures`, `profitabilityStaleInputs`,
  `buildProfitabilityBlock`, `upsertProfitabilityRow`).
- CREATE `drizzle/0010_profitability_mirror.sql` (+ journal idx 9).
- EDIT `drizzle/meta/_journal.json` (idx 9).
- EDIT `server/src/actions.ts` — `profitabilityExportInput` zod
  schemas, `ingestProfitabilityState`, `getMining` profitability
  block, `refreshAtlasData` step 9, `getMining` description.

Changed-file sweep (vs space-version v16 manifest + mtimes): exactly
these seven files. The `bun run typecheck` runs regenerated the
`.tsbuildinfo` caches only — no other source touched. No Energy Orb
file, no host file, no config, no cron touched.

### 9.2 Verification results

- **Typecheck:** `bun run typecheck` (client + server) — PASS, exit 0,
  zero errors. (Two errors found and fixed during the build: shape
  consts used before declaration; `PROFILE_DEFS[0]` possibly
  undefined. Both fixed in this build's files only.)
- **Migration 0010 (sandbox, in-memory SQLite):** PASS — table exists
  with the id=1 CHECK; `INSERT id=2` rejected; journal idx 9 /
  tag `0010_profitability_mirror` follows idx 8 (`0009_smith_research_rounds`).
- **Sandbox suite** (`/tmp/m9-sandbox/m9-sandbox.test.ts`, `bun test`):
  **10 pass / 0 fail, 121 expects.** The REAL `Actions.getMining`
  and `Actions.ingestProfitabilityState` handlers were invoked with a
  fake ctx against an in-memory DB with migrations 0001–0010 applied.
  - Obj 4 regression: derive reproduces the independent reference
    implementation to <1e-9, and the CARRIED net/day figures within
    $0.002 (XMR +0.021/+0.138/−0.367; KAS/RVN/ERG as design §4);
    SupportXMR 0.6% reduces XMR gross by exactly 0.6% vs MoneroOcean;
    P2Pool 0% equals MoneroOcean; US avg flips XMR negative, Tier 2
    stays positive.
  - M4 gates: 56.5 H/W at Tier 2 (±0.3), 125.2 H/W at US avg (±0.5),
    $0.03302/day per kH/s (±0.0005) — reproduced with the M4 inputs
    ($501.26, difficulty 787,074,505,719).
  - Baseline: no row → `profitabilityExportMissing: true`, coins `[]`,
    your-hardware null + verbatim reason, confirmed 0, mismatch false,
    stale true.
  - Null export → `profitabilityExportMissing: true`, table still empty.
  - Fixture ingest → block present, mismatch false, host == mirror
    within tolerance, your-hardware null + verbatim reason, confirmed
    identical to dashboard, stale false; `audit_usd` never stored;
    durable rows unchanged (0 batches / 0 ledger entries).
  - Mismatch proof: tampered XMR `netXmrPerDayTier2` (+0.0001) →
    `mismatch: true`, `mismatchDetails` names exactly
    `XMR (Ryzen 7 5800X).netXmrPerDayTier2`, displayed figures switch
    to host-verified.
  - Confirmed-earnings disagreement → `confirmedEarnings` in
    `mismatchDetails`, dashboard figure (0) shown.
  - Stale proof: KAS network stats 73 min old →
    `STALE — KAS network stats 73 min old`, stale true.
  - Re-ingest identical → `upToDate: true`, `synced_at` unmoved;
    changed payload → `upToDate: false`. (Note: `synced_at` is
    second-resolution; the changed-payload ingest reported
    `upToDate: false` — the meaningful signal — and `synced_at` was
    ≥ the previous value.)
- **Grep checks:** zero `<button>`/`<input>`/`<a `/`<form>` in the
  component; the 15 `$` characters are all template-literal `${`
  interpolations (no bare `$`); zero hardcoded XMR/day literals; zero
  secret patterns; no `SELECT *` over `workers`; all verbatim strings
  present in the component except `Cannot estimate — hashrate not
  measured`, which is server-supplied by design and verified in the
  rendered probe instead.
- **Desktop probe** (`/tmp/m9-sandbox/probe.tsx`, static render via
  `renderToStaticMarkup` with a real `buildProfitabilityBlock`):
  **25/25 assertions PASS** — seven panel groups in §1.3 order, all
  verbatim strings present, zero interactive elements, no `$`, no
  currency-marked amount, XMR/day at 6 decimals, confirmed earnings
  `0.000000 XMR (SIMULATION)`, no mismatch note on agreement, no
  STALE tag when fresh; missing-export variant renders the verbatim
  state + `Not computed yet`; stale variant names the stale input.
  **Honest limit:** this probe establishes source + data rendering
  only. It does NOT establish a live render, Mining-tab selection, a
  real-browser console, or a real-viewport 390 px overflow measurement.
  Those remain Lane E items E1/E3/E7 (§6). The live-render gap (M9
  design §9 finding 1) is NOT closed by this build.

### 9.3 Deviations (all flagged in §0.1, none concealed)

1. Migration **0010** (not 0009 — already taken by
   `smith_research_rounds`, journal idx 8).
2. Current build **v16 `bafa9e63`** (not M8 `d5e7be84` — that is v15);
   new build id owed to the parent's publish step (no `artifact.*`
   tools in this lane; `artifact.status` could not be called).
3. `ingestProfitabilityState` is a new server action riding the
   existing refresh (M8 reading of "no new ingest action").
4. Pure module `server/src/profitability.ts` (M7/M8 put the logic
   inline in the handler; the pure module is what makes the sandbox
   mismatch/stale proofs runnable against the real code).
5. Panel 7a clarification: input values render bare (no currency
   unit); only `¢/kWh` on rate rows; labels/sources are metadata and
   may name a pair — the no-fiat rule constrains amounts. Found when
   the strict "no USD string" probe assertion tripped on the fixture
   label `USD/CAD rate`; the probe now asserts no currency-marked
   amount instead.

### 9.4 Open items owed onward

- **Parent (publish):** publish the working tree through the artifact
  tooling and report the new build id to Lane E with the §6 checklist.
- **Lane C (host):** `core/atlas_profitability.py` +
  `data/profitability.json` not landed at build time; field names to
  confirm against §2.1/§4 (§0 gaps 1–2). Until they land, the section
  honestly renders `profitabilityExportMissing`.
- **Lane E:** §6 acceptance (E1–E13), including the rendered
  desktop/mobile + reload-persistence checks this lane could not
  perform.
