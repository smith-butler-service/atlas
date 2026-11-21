# ATLAS Master Mission 7 — Lane D (UI build) SPECIFICATION

**Mission:** Master Mission 7 — User dashboard (earnings dashboard)
**Lane:** D (UI specification ONLY — this lane writes no artifact code, runs no
artifact edit, touches no artifact file)
**Date:** 2026-11-18
**Artifact:** `atlas-command-center`, current build `8582d78e` (Mission 6)
**Status:** SPECIFICATION ONLY. The coordinator executes the artifact edit from
this spec (see §5 for the exact `verbatim_request` text). Nothing in this
document is deployed until that edit runs, typechecks, and passes the §5/§6
verification.

## 0. Binding inputs and ground truth

Read first (binding):

- `docs/master-mission7-design.md` (Lane A) — decisions D-M7-1–D-M7-13 are
  binding and are followed exactly, EXCEPT for the single explicitly-flagged
  minimal deviation in §3.1 (migration 0007), which the parent task orders
  and which is required to implement binding D-M7-7.
- `docs/master-mission6-lane-d-ui-report-2026-11-18.md` (Mission 6 UI
  conventions: files changed, `ingestRewardsState`, `getMining` rewards block,
  migration 0006, sandbox verification method).
- `docs/master-mission6-report-2026-11-18.md`, Unresolved finding 1 (the
  self-contradictory reward display). This spec does NOT repeat it and does
  NOT repair it. Repair needs a separate, repair-authorized inspection and is
  NOT authorized here.
- `core/atlas_dashboard.py` + `data/dashboard.json` (host dashboard export —
  field names the UI block must match; see §2.1).

Ground truth (verified by the coordinator, re-checked read-only by this lane):

- Mining tab order (M6 report, keep unchanged): MiningDashboard, WalletCenter,
  EarningsSection, HistorySections, PayoutSection, CalculatorSection,
  MinerPrototypeSection, CoordinatorSection, RewardAccounting,
  SettingsSection, HelpSection. The new **User dashboard** section goes
  directly BELOW RewardAccounting, above SettingsSection.
- Live mirror (`getMining` just now): rewards batches `[]`, entries `[]`,
  totals all 0; rewards `stale:true`, `syncedAt` 1795019850; coordinator
  `syncedAt` 1795023408; shares all 0; workers `[]`; sessions `[]`; payouts
  `[]`; balances all 0; `xmrPriceUsd` null. The `sim-batch-test-1` rows from
  the Mission 6 inspection are SANDBOX-ONLY, not in the live mirror.
- Host dashboard export (`data/dashboard.json`, `exported_at` 1795025048):
  hashrate `not-measured`, `current_hps` null, `average_hps` null; shares all
  0; duration `total_session_seconds` 0; workers all 0; earnings estimated
  null + verbatim reason `Cannot estimate — hashrate not measured`,
  confirmed 0, `SIMULATION ONLY — no pool rewards`; balances `{}`; lifetime
  all 0; payouts count 0, rows `[]`; efficiency `acceptance_rate` null;
  `sync.stale` false (host-export freshness — NOT mirror freshness, see
  §4); `host_verified_totals`: `ledger_entries` 0, `batches_settled` 0,
  `total_user_rewards_piconero` 0, `total_atlas_share_piconero` 0.
- Host rewards export (`data/rewards.json`, `exported_at` 1795024871):
  `totals` = `total_user_rewards_piconero` 0,
  `total_referral_rewards_piconero` 0, `total_atlas_share_piconero` 0,
  `total_pool_fees_piconero` 0, `total_payouts_piconero` 0,
  `total_reversals_piconero` 0, `ledger_entries` 0, `batches_open` 0,
  `batches_settled` 0, `batches_held` 0; batches `[]`, ledger `[]`.
- Host coordinator export (`data/coordinator.json`, `exported_at`
  1795024871): hashrate `not-measured` / `measured_hps` null; shares all 0;
  workers all 0. **NOTE (gap, not a blocker):** the design §1 additive
  derived field `worker_sessions_duration_seconds` is NOT present in
  `coordinator.json` at spec time (Lane C host work is parallel). The
  dashboard block therefore MUST derive duration from the mirrored
  `mining_sessions` rows (§2.2) and MUST NOT depend on that host field
  existing. If Lane C adds it, the duration secondary cross-check (§3.3)
  becomes active; if it is absent, that secondary check is skipped and the
  omission is recorded in the build report — it never blocks the build and
  never fabricates a duration.

**Where the artifact source lives.** The artifact source tree
(`client/src`, `server/src`, `drizzle/`) is NOT in `~/workspace/atlas/`; it
lives in the ts-space working tree the artifact builder uses (M6 Lane D
report §1, §5). This lane therefore could not read `schema.ts`,
`actions.ts`, or `Mining.tsx` directly. File paths below follow the M6 Lane D
file list exactly; the coordinator MUST resolve each path against the
ts-space tree at edit time and MUST report back any path that does not
resolve, rather than guessing a different path.

---

## 1. New component — `client/src/UserDashboard.tsx`

### 1.1 Identity and placement

- **New file:** `client/src/UserDashboard.tsx` (export
  `UserDashboardSection`, taking the same `m` prop shape as
  `RewardAccountingSection` — the `getMining` result).
- **Path note (flagged deviation, non-binding):** design §7.1 suggests
  `client/src/miner/UserDashboardSection.tsx` and states the name is "a
  build-lane suggestion". The parent task binds `client/src/UserDashboard.tsx`.
  This spec follows the parent task: flat in `client/src/`, next to
  `RewardAccounting.tsx`, same import pattern as M6.
- **Placement:** in `client/src/Mining.tsx`, import and render
  `<UserDashboardSection m={m} />` directly BELOW
  `<RewardAccountingSection m={m} />` and directly ABOVE the Settings
  section. No other line in `Mining.tsx` moves. No existing section is
  reordered, restyled, or reworded. No new tab.
- **Data:** reads ONLY the `dashboard` block of the `getMining` result
  (§2). Never reads any other action, never fetches, never writes.
  React Query refetch: same 30 s cadence as the rest of the Mining tab.
  No new refresh schedule.
- **Zero controls (hard limit):** zero `<button>`, `<input>`, `<a>`,
  `<form>`, or any clickable control anywhere in the section. No "claim",
  no "withdraw", no "refresh now", no "recalculate", no user picker, no
  settings control. Start/Stop stay hard-disabled and untouched.
- **No hardcoded figures (hard limit, D-M7-7 / design §6):** NO hardcoded
  zero — or any hardcoded figure — is permitted anywhere in this component
  as a displayed value. Every displayed figure flows from the `dashboard`
  block. A panel whose value is a literal in the component source is a
  defect. The §5 grep check enforces this. (Verbatim copy strings such as
  `0.000000 XMR` inside empty-state *sentences* are copy, not values: they
  may appear ONLY inside the verbatim strings listed in §1.3, and only
  when the corresponding block value is actually 0 — the component MUST
  render the block value, formatted, and MUST NOT substitute a literal
  for it. Where a verbatim sentence contains a figure, the figure in the
  sentence MUST be produced by formatting the block value, never typed
  as a constant.)
- **Amounts:** XMR to 6 decimal places (e.g. `0.000000 XMR`), converted
  from integer piconero only (`piconero / 1e12`, formatted — never float
  arithmetic on money beyond the display division). **No USD/fiat figure
  anywhere.** `xmrPriceUsd` is null; no conversion is ever attempted.
- **Provenance tags:** every figure carries a SNAPSHOT / RECORDED /
  ESTIMATE / UNAVAILABLE tag plus a SIMULATION tag while mode is
  `simulation-only`, following the existing tab pattern. Nothing is
  labelled live unless measured in the current probe/session.
- **Responsive / accessibility (binding, M5 §7.4 carried):** tables/cards
  collapse to stacked cards below ~640 px; no horizontal page overflow at
  390 px (mobile overflow 0); all status is text, never colour alone (a
  screen reader must hear `Active` / `Registered` / `not measured`, not
  just see a dot); disabled/absent controls are absent, not greyed-out
  fake buttons.

### 1.2 Section header (verbatim)

> **User dashboard — Master Mission 7**
> Subtitle: `Simulation only — derived from the coordinator and reward engine outputs. Nothing here is live earnings.`
> Scope line (verbatim, while users = 0): `Showing all users — no user accounts exist yet (0 users).`
> Mismatch note slot (shown ONLY on mismatch, verbatim):
> `Mirror mismatch — figures under investigation`

### 1.3 The nine panels (verbatim headings, labels, and empty-state copy)

Panels render top-to-bottom in this exact order. Values shown are today's
honest live state; the component MUST compute them from the `dashboard`
block, never from literals.

**Panel 1 — Dashboard status (status banner, always visible):**

| Row label | Value today |
|---|---|
| Mode | `Simulation only` |
| Emergency stop | `ON — all live activity held` |
| Mining | `Disabled` |
| Pool connection | `None — read-only stats polling only` |
| Data freshness | `STALE — rewards data 73 min old` (at design time; per §4 in general: `SYNCED` / `STALE — <block> data <age> old` / `Not synced yet`) |
| Mirror check | `Mirror check: agree (0 = 0)` (in general: `Mirror check: agree` / `Mirror mismatch — figures under investigation`) |

Empty-state banner (verbatim, shown while users = 0, workers = 0,
shares = 0, ledger = 0):

> `No mining activity yet. The dashboard is running in simulation only — there is nothing to show but honest zeros.`

Emergency-stop OFF case (not today; specified so the component never
invents copy later): if ever OFF, shows `OFF` + the time it was lifted +
the decision id. Do not render that branch's copy today.

**Panel 2 — Hashrate:**

Heading: `Hashrate`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Current hashrate` | `not measured` | UNAVAILABLE |
| `Average hashrate` | `not measured` | UNAVAILABLE |

Body (verbatim while Gate 1 is unmeasured):

> `Hashrate: not measured`
> `No measurement yet — Gate 1 (measured hashrate in a real browser) has not been run for the Mission 4 prototype. Published figures from other projects are shown in the Miner Prototype section above and are not ATLAS measurements.`

Average-hashrate line (verbatim, shown while no measurement series exists):

> `Average hashrate: not measured — Cannot compute — hashrate not measured`

Rules: this panel shows NO number in H/s while unmeasured — not 0, not an
estimate, not a benchmark. After Gate 1 passes, it shows the measured
value, the probe session id, threads/mode, measurement time, and tag
`MEASURED`; the "not measured" copy is replaced, not kept alongside. A
desktop-agent self-report is shown here only with the tag `REPORTED —
agent self-report, not measured by ATLAS`, and never replaces the
`not measured` state for the browser prototype. The pool-wide hashrate is
never shown in this panel.

**Panel 3 — Shares:**

Heading: `Shares`

Four stat cards (exact labels + today's honest values):

| Card label | Value today | Provenance tag |
|---|---|---|
| `Pool shares accepted` | `0` | RECORDED |
| `Pool shares rejected` | `0` | RECORDED |
| `Local-test shares accepted` | `0` | RECORDED |
| `Local-test shares rejected` | `0` | RECORDED |

Empty state (verbatim, shown when pool shares total 0):

> `No pool shares yet — 0 accepted / 0 rejected.`

Below the cards (verbatim):

> `Pool shares are the only shares that count toward rewards or worker activation. Local-test shares come from the Mission 4 local-test relay only — they are not real mining shares and never earn anything.`

Rejection-rate line (shown ONLY when pool total > 0, else hidden — not
shown as 0%):

> `Pool rejection rate: <x>% over <n> pool shares (RECORDED)`

**Panel 4 — Duration & worker status:**

Heading: `Duration & worker status`

Duration block:

| Row label | Value today | Provenance tag |
|---|---|---|
| `Total mining duration` | `No mining sessions yet` | UNAVAILABLE |
| `Worker sessions` | `0` | RECORDED |

Duration line when sessions exist:
`Total mining duration: <Xh Ym Zs> over <N> worker sessions (DERIVED host)`
— plus the diagnostic line when degenerate rows exist:
`<n> session rows with ended_at <= created_at counted as 0 seconds.`

Worker-status block:

Heading: `Worker status — 0 workers`

Status summary (exact labels, today's values):
`Active 0 · Registered 0 · Degraded 0 · Suspended 0 · Revoked 0 · Pending 0`

Empty state (verbatim, shown when the table has no rows):

> `No workers registered yet. The coordinator is running in simulation only — there is nothing to coordinate.`

Populated-row rules (when workers exist): one line per worker —
`<name> — <type: Browser / Desktop> — <lifecycle status verbatim> — Hashrate:
not measured — Pool shares: <accepted> accepted / <rejected> rejected`.
The lifecycle status is shown verbatim (`Registered`, `Active`,
`Degraded`, `Suspended`, `Revoked`, `Pending`); an `Active` row carries a
green dot, every other status a grey/amber dot, and the derived grouping
"Inactive" appears in the summary only — never as the row's status.
Worker detail (registration time, XMRig version / "Binary unverified",
token issuance) stays in the Coordinator section above; this panel does
not duplicate it and NEVER displays a token, token hash, or wallet
address.

**Panel 5 — Earnings: estimated vs confirmed:**

Heading: `Earnings — estimated vs confirmed`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Estimated earnings` | `Cannot estimate — hashrate not measured` | UNAVAILABLE |
| `Confirmed earnings` | `0.000000 XMR` | DERIVED (host), SIMULATION |

Estimated-earnings body (verbatim):

> `Estimated earnings: Cannot estimate — hashrate not measured`
> `No estimate can be computed until a hashrate has been measured (Gate 1) and shares have been accepted by the pool. Estimates never create a payable balance.`

Confirmed-earnings body (verbatim):

> `Confirmed earnings (SIMULATION): 0.000000 XMR`
> `Confirmed earnings come only from settled reward batches — verified accepted shares and confirmed pool rewards. Simulation only — no real earnings yet.`

Rules: the two figures are never combined, never summed, and never shown
in a single "total earnings" line. The estimate is never derived from
pool-wide hashrate (design §3). When confirmed earnings are non-zero in
future, the panel shows the settled-batch count alongside
(`from <n> settled reward batches`).

**Panel 6 — Balances:**

Heading: `Balances`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Available balance` | `0.000000 XMR` | DERIVED (host), SIMULATION |
| `Pending rewards` | `0.000000 XMR — no open reward batches` | DERIVED (host), SIMULATION |

Body (verbatim):

> `Available balance: 0.000000 XMR`
> `Pending rewards: 0.000000 XMR — no open reward batches`
> `Balances are derived from the ledger (SIMULATION). Pending rewards are amounts in open or held reward batches that have not settled yet — they are not available and not confirmed.`

Rules: available balance = `SUM` over the user's ledger entries
(`user_allocation` + `referral_reward` + `payout` + `reversal`, M6 §5.1);
pending = the not-yet-settled share of open/held batches (0 today). No
stored running-balance column is ever read or shown (M6 D-M6-12). A
referral reward included in the available balance is labelled as funded
from the ATLAS 25% (`includes <x> XMR referral rewards from the ATLAS 25%`
— shown only when non-zero).

**Panel 7 — Lifetime earnings & previous payouts:**

Heading: `Lifetime earnings & previous payouts`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Lifetime earnings` | `0.000000 XMR` | DERIVED (host), SIMULATION |
| `Previous payouts` | `No payouts yet — no payout has ever been attempted (Gate 4 closed)` | RECORDED |

Body (verbatim):

> `Lifetime earnings: 0.000000 XMR — no settled reward batches yet`
> `Previous payouts: No payouts yet — no payout has ever been attempted (Gate 4 closed)`
> `Lifetime earnings are the sum of all settled user allocations and referral rewards since the ledger began. Payouts require explicit authorization, successful security testing, and a treasury design — none exists.`

Rules: lifetime earnings = `SUM` over all settled batches (all time),
never reset by a refresh or a new batch. Previous payouts lists each
payout row when any exist (date, amount XMR, status, txid or
`no txid — simulation`), newest first; the minimum payout is still
null/placeholder (undecided — flag for the user, do not decide it here).
No payout is ever shown as "pending" unless a payout row with that status
exists.

**Panel 8 — Efficiency:**

Heading: `Efficiency`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Share efficiency` | `Cannot compute — no pool shares yet` | UNAVAILABLE |

Body (verbatim):

> `Share efficiency: Cannot compute — no pool shares yet`
> `Efficiency is accepted shares divided by all pool shares (accepted + rejected). Local-test shares are never counted.`

Rules: shown as a percentage to one decimal place when computable
(`Efficiency: <x>% over <n> pool shares (RECORDED)`), null with the
verbatim reason above when the denominator is 0 (design §4). Never `0%`,
never `100%`, on an empty denominator.

**NOTE — host reason string differs (flagged, do not copy the host
string):** `data/dashboard.json` currently carries efficiency reason
`Not measurable — no shares yet`. The UI MUST show the design-verbatim
`Cannot compute — no pool shares yet`. The `dashboard` block MUST
therefore carry the design-verbatim reason string (§2.2), and the
component MUST render the block's reason — it must never pass the host
`dashboard.json` reason through unmapped. (The estimate reason matches
the host string exactly: `Cannot estimate — hashrate not measured`.)

**Panel 9 — Last sync time:**

Heading: `Last sync time`

| Row label | Value today (at design time) | Provenance tag |
|---|---|---|
| `Coordinator data` | `synced <date time> (<age> ago)` — ~14 min old at check | RECORDED (mirror time) |
| `Rewards data` | `synced <date time> (<age> ago)` — ~73 min old at check, STALE | RECORDED (mirror time) |

Body (verbatim while either block has never synced):

> `Not synced yet`

Body (verbatim, always visible below the two timestamps):

> `Both mirrors must be fresh for this dashboard to be current. If either is more than 1 hour old, the whole dashboard is marked STALE. A re-ingest of unchanged data reports "already up to date" and does not refresh these times.`

Rules: both timestamps are shown, each with its own STALE / SYNCED tag
(§4). The two are never merged into one figure.

**Copy that must NOT appear in this section:** any hashrate number
presented as ATLAS's without a `MEASURED` tag and a measurement time; the
words "verified", "confirmed", or a checkmark next to any worker, address,
or hashrate that has only passed format checks or self-report; "There is
no miner yet" (stale copy, M4 finding 4 — carried, §7); any earnings,
balance, or payout figure derived from shares or hashrate; any USD/fiat
figure; any combined "total earnings" mixing estimated and confirmed
figures. No demo users, workers, shares, earnings, or payouts are seeded.

---

## 2. `getMining` dashboard block — computed server-side from ALREADY-MIRRORED data

### 2.1 Field names (must match the host export)

Field names follow `data/dashboard.json` (`core/atlas_dashboard.py`)
exactly where a host field exists, so the mirror and the host can be
compared field-for-field. Host field → `dashboard` block field:

| Host (`dashboard.json`) | Dashboard block field | Notes |
|---|---|---|
| `hashrate.status` / `current_hps` / `average_hps` | `hashrateStatus`, `currentHps`, `averageHps` | Both null today; status `not-measured` |
| `shares.pool_accepted` / `pool_rejected` / `local_test_accepted` / `local_test_rejected` | `shares{PoolAccepted, PoolRejected, LocalTestAccepted, LocalTestRejected}` | Mirror-derived `SUM` over `mining_shares` where `origin='pool'` / `'local-test'`; cross-checked against the coordinator mirror counts |
| `duration.total_session_seconds` | `durationSeconds` | Mirror-derived `SUM` over `mining_sessions` (§2.2); host field is the cross-check, not the source, until Lane C's export field exists |
| `workers.{total,active,registered,degraded,suspended,revoked,pending}` | `workers{Total,Active,Registered,Degraded,Suspended,Revoked,Pending}` + `workerRows` (per-worker lines for Panel 4, when any exist) | Counts over mirrored `mining_workers` |
| `earnings.estimated_piconero` / `estimated_reason` | `estimatedPiconero` (null), `estimatedReason` | Verbatim `Cannot estimate — hashrate not measured` |
| `earnings.confirmed_piconero` | `confirmedPiconero` | Host-verified total when shown (§3); mirror-derived total carried separately for comparison |
| `balances` | `balances` (per-user derived `SUM`s; `{}` today) + `availableBalancePiconero` (host-global `SUM`) | Never a stored running balance |
| `lifetime.*_piconero` | `lifetime{UserRewards,ReferralRewards,AtlasShare,PoolFees,Payouts,Reversals}Piconero` | Host-verified side (§3) |
| `payouts.{count,total_piconero,rows}` | `payouts{Count,TotalPiconero,Rows}` | Rows from mirrored `mining_payouts` |
| `efficiency.acceptance_rate` / `reason` | `efficiencyRate` (null), `efficiencyReason` | Verbatim `Cannot compute — no pool shares yet` (§1.3 Panel 8 note) |
| `mode`, `emergency_stop` | `mode`, `emergencyStop` | `simulation-only`, `true` |
| `host_verified_totals` | `hostVerifiedTotals` | §3 — the four named fields PLUS the full totals block (see §3.2) |
| — (mirror state) | `coordinatorSyncedAt`, `rewardsSyncedAt` (epoch seconds, nullable) | The two mirror `syncedAt` values; `stale` computed per §4 |
| — (mirror derivation) | `mirrorDerivedTotals` | §3 — the mirror side of the comparison |
| — (comparison) | `mismatch` (boolean), `mismatchDetails` (list of disagreeing quantities) | §3 |

### 2.2 Derivation rules (server-side, in `getMining`)

- The block is computed inside the existing `getMining` action from
  mirror tables ONLY (`mining_workers`, `mining_shares`,
  `mining_sessions`, `mining_ledger`, `mining_reward_batches`,
  `mining_payouts`, plus the new §3.2 table). **No new ingest action for
  the dashboard itself. No new action at all.** If a derived field is
  missing, extend this `dashboard` block — do not create a new table, a
  new action, or a new refresh step (design §1, carried).
- **Shares:** `SUM` over mirrored `mining_shares` split by `origin`
  (`pool` vs `local-test`). Pool shares are the only shares that count
  toward rewards/efficiency; local-test shares never enter any shares,
  efficiency, duration, or earnings figure.
- **Duration:** `SUM` over mirrored `mining_sessions` of
  `COALESCE(ended_at, <mirror sync/export time>) - created_at` where
  `kind='worker'` AND the session is a desktop-agent session, with
  degenerate rows (`ended_at <= created_at`) contributing 0 and counted
  in the diagnostic line. Browser-probe sessions (local-test) contribute
  0 and are excluded — reuse the same flag/field the Coordinator
  section already uses to distinguish probe sessions in the mirror; if
  the mirror carries no such distinguishing field, count all
  `kind='worker'` rows and record that limitation in the build report
  (do NOT invent a flag, do NOT guess). Open sessions contribute up to
  the export time, never beyond it. Display `Xh Ym Zs` + session count.
  Today: 0 sessions → `No mining sessions yet`.
- **Efficiency:** `accepted / (accepted + rejected)` over pool-origin
  shares only, percentage to one decimal place. Denominator 0 → null
  with the verbatim reason (§1.3 Panel 8). Never `0%`, never `100%` on an
  empty denominator. Local-test shares never enter either term.
- **Confirmed earnings / balances / lifetime:** ledger `SUM`s in integer
  piconero (M6 §5.1 sign convention), SIMULATION-tagged while mode is
  `simulation-only`. Confirmed = settled batches only; open/held batches
  contribute to *pending* only. The estimate is never added to a
  confirmed figure or a balance.
- **Estimated earnings:** ALWAYS null in this mission, with the verbatim
  reason. Never derived from pool-wide hashrate, never a benchmark, never
  from `workers.reported_hashrate_hps` (self-report only). An estimate
  becomes computable only when BOTH a measured hashrate exists (Gate 1)
  AND a stated formula with stated inputs exists (Mission 9's job, not
  this build's).
- **Scope (D-M7-13):** every per-user query is parameterized by
  `user_id`, but with 0 users and no auth the section renders the
  host-global view (totals summed over all users) with the verbatim scope
  line. Do NOT invent a login, a "current user" picker, or demo user rows.
- **Secrets:** no token, session token, or password hash is ever mirrored
  or displayed. Entry hashes from the reward ledger are mirrored audit
  data (M6) but the dashboard does not display them.

### 2.3 Expected live values of the block (today — the acceptance baseline)

All-zero / null honest state: `hashrateStatus: "not-measured"`,
`currentHps: null`, `averageHps: null`; shares 0/0/0/0; `durationSeconds:
0`, worker sessions 0; workers all 0, `workerRows: []`;
`estimatedPiconero: null`,
`estimatedReason: "Cannot estimate — hashrate not measured"`;
`confirmedPiconero: 0`; balances `{}` / `availableBalancePiconero: 0`;
lifetime all 0; payouts count 0, rows `[]`; `efficiencyRate: null`,
`efficiencyReason: "Cannot compute — no pool shares yet"`;
`mode: "simulation-only"`, `emergencyStop: true`;
`hostVerifiedTotals` all 0; `mirrorDerivedTotals` all 0;
`mismatch: false`; `coordinatorSyncedAt` / `rewardsSyncedAt` = the live
mirror values at read time; `stale` per §4 (true while the rewards mirror
is > 1 h old, as at spec time).

---

## 3. MISMATCH MECHANISM (binding, D-M7-7)

### 3.1 Why a migration is needed — flagged deviation from design D-M7-1

Design D-M7-1 states "No new artifact mirror tables either (§1)", and
design §6 assumes the host-verified totals are "carried in the mirrored
rewards export". That assumption does not hold for the M6 build as
shipped: `ingestRewardsState` (M6) mirrors reward-batch and ledger
ROWS only — it never persists the host export's `totals` block anywhere
in the artifact. `getMining`'s rewards block returns totals DERIVED from
the mirrored rows, so there is no independent host-verified side in the
artifact to compare against. Without somewhere to store the host side,
the binding D-M7-7 comparison cannot be computed server-side at all.

**The parent task therefore orders this minimal additive deviation from
the D-M7-1 artifact sentence (host side of D-M7-1 is untouched — no new
host tables):** one new additive drizzle migration, 0007, persisting the
host export's totals block in the artifact. It is additive only (a new
table; no existing table, column, row, or index is altered), it stores
no new truth (it is a snapshot of the host export, recomputed on every
ingest), and it is the smallest change that makes D-M7-7 computable.
No other reading of D-M7-7 is implementable. This deviation is recorded
here explicitly so Lane E can verify it as ordered, not as drift.

### 3.2 Migration 0007 — `drizzle/0007_dashboard_host_totals.sql`

**Chosen shape: one small new singleton mirror table** (not additive
columns on an existing table).

**Justification.** The totals block is a snapshot of a host EXPORT, not
an attribute of any existing row. Additive columns on `mining_ledger`
or `mining_reward_batches` would duplicate the same global snapshot on
every row (wrong granularity, invites drift between copies) and would
force a totals read to pick an arbitrary row. A singleton table makes
the upsert-on-ingest trivial (one row, keyed by a constant), makes the
mismatch comparison a single-row read, and mirrors the host export's
`totals` object 1:1. Rejected alternative: columns on
`mining_reward_batches` — totals are global across batches, not
per-batch; rejected. Rejected alternative: deriving host totals from
`rewards.json` at `getMining` time — the artifact has no read path to
the host export file; the totals must arrive through the existing
ingest path like every other mirrored figure.

**Exact table and columns** (new table `mining_dashboard_host_totals`):

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY CHECK (`id` = 1) | Singleton row; exactly one row ever exists |
| `ledger_entries` | INTEGER NOT NULL | Host `totals.ledger_entries` |
| `batches_settled` | INTEGER NOT NULL | Host `totals.batches_settled` |
| `batches_open` | INTEGER NOT NULL | Host `totals.batches_open` |
| `batches_held` | INTEGER NOT NULL | Host `totals.batches_held` |
| `total_user_rewards_piconero` | INTEGER NOT NULL | Host `totals.total_user_rewards_piconero` |
| `total_referral_rewards_piconero` | INTEGER NOT NULL | Host `totals.total_referral_rewards_piconero` |
| `total_atlas_share_piconero` | INTEGER NOT NULL | Host `totals.total_atlas_share_piconero` |
| `total_pool_fees_piconero` | INTEGER NOT NULL | Host `totals.total_pool_fees_piconero` |
| `total_payouts_piconero` | INTEGER NOT NULL | Host `totals.total_payouts_piconero` |
| `total_reversals_piconero` | INTEGER NOT NULL | Host `totals.total_reversals_piconero` |
| `source_exported_at` | INTEGER | Host export's `exported_at` (the export the totals came from; nullable only if the ingest payload carries none) |
| `synced_at` | INTEGER | Artifact ingest time of the last CHANGED totals write (see §3.4) |

The four fields the parent task names as the minimum
(`ledger_entries`, `batches_settled`,
`total_user_rewards_piconero`, `total_atlas_share_piconero`) are
included; the remaining six totals fields are included because design
§6's comparison covers six quantities (fees, referrals, payouts included)
and the full block is what the host export carries — persisting a partial
block would make three of the six comparisons uncomputable. All values
integer piconero; no floats; no secrets; no token/session/password hash.

**Schema file:** add the table to `server/src/schema.ts` (drizzle
definition mirroring the SQL exactly) and add the journal entry for
0007 in `drizzle/meta/_journal.json` (idx 6, following 0006's idx 5) —
same pattern as M6 migration 0006.

### 3.3 `ingestRewardsState` extension (no new action)

Extend the EXISTING `ingestRewardsState` action (in
`server/src/actions.ts`) to also persist the totals block:

- The ingest payload already carries the host rewards export; the
  action MUST read its `totals` object and upsert the singleton row in
  `mining_dashboard_host_totals` (`id` = 1) in the same transaction as
  the batch/ledger row ingest, so totals and rows can never land from
  different exports.
- **Upsert semantics:** if the incoming totals are identical to the
  stored row AND no batch/ledger row changed, the ingest reports
  `upToDate: true` with 0 added and does NOT touch `synced_at` (a
  re-ingest of unchanged data is never mislabelled as a fresh sync —
  M5 §1.4 / M6 §10, carried). If the totals differ (or rows changed),
  overwrite the singleton row and set `synced_at` to now.
- **Missing totals:** if an ingest payload carries no `totals` object
  (older host export shape), the action MUST NOT delete or zero the
  stored row — it leaves the singleton untouched and records
  `hostTotalsMissing: true` in its return value. Never fabricate totals.
- The action's existing behavior is otherwise unchanged: ledger ingest
  stays insert-only, host-id dedupe stays enforced, re-ingest of
  unchanged rows still reports "already up to date".

### 3.4 `getMining` — both totals sides + the mismatch flag

`getMining` computes, server-side, in the `dashboard` block:

- **`mirrorDerivedTotals`** (from mirrored rows only):
  - `ledgerEntries`: `COUNT(*)` over `mining_ledger`
  - `totalUserRewardsPiconero`: `SUM` over `mining_ledger` where
    `entry_type IN ('user_allocation','referral_reward')`
  - `totalAtlasSharePiconero`: `SUM` over `mining_ledger` where
    `entry_type = 'atlas_share'`
  - `totalPoolFeesPiconero`: `SUM` over `mining_ledger` where
    `entry_type = 'fee'`
  - `totalPayoutsPiconero`: `SUM` over `mining_ledger` where
    `entry_type = 'payout'`
  - `batchesSettled`: `COUNT(*)` over `mining_reward_batches` where
    `status = 'settled'`
  - (plus `totalReferralRewardsPiconero`, `totalReversalsPiconero`,
    `batchesOpen`, `batchesHeld` where derivable, for completeness)
- **`hostVerifiedTotals`** (from the singleton row, §3.2):
  - `ledgerEntries`, `batchesSettled`, `batchesOpen`, `batchesHeld`,
    `totalUserRewardsPiconero` (= host `total_user_rewards_piconero` +
    `total_referral_rewards_piconero`, per design §6 — the host splits
    user and referral rewards; the mirror sums them together, so the
    comparison adds them on the host side),
    `totalReferralRewardsPiconero`, `totalAtlasSharePiconero`,
    `totalPoolFeesPiconero`, `totalPayoutsPiconero`,
    `totalReversalsPiconero`. If the singleton row does not exist yet
    (never ingested), `hostVerifiedTotals` is `null` and `mismatch` is
    `false` with `mismatchDetails: ["host totals not yet synced"]` — the
    dashboard shows the mirror-derived figures labelled as such and the
    Panel 9 `Not synced yet` state; it never invents host totals.
- **`mismatch`** (boolean) + **`mismatchDetails`** (array of the
  disagreeing quantity names, e.g. `["ledgerEntries",
  "totalUserRewardsPiconero"]`): true when ANY of the six design §6
  comparisons disagrees. Agreement on today's all-zero state (0 = 0)
  is a valid trivial agreement and says nothing about the check
  working — the §5 sandbox test must prove the check with non-zero
  fixture data.
- **Secondary check (duration):** compare the host-export duration
  (`worker_sessions_duration_seconds`, when present in the coordinator
  mirror payload) against the artifact's own `SUM` over mirrored
  `mining_sessions`. A disagreement shows the host-export value plus
  the same verbatim mismatch note, and adds `"duration"` to
  `mismatchDetails`. The ledger comparison above is the primary check
  and MUST exist even if the duration check is deferred; the duration
  check must not be substituted for it. While the host field is absent
  (spec time — see §0), the duration check is skipped, not faked.
- **On mismatch, the component MUST:** show the HOST-VERIFIED totals
  (not the mirror-derived ones) in every earnings/balance/lifetime
  figure; show the verbatim note `Mirror mismatch — figures under
  investigation` in the section header area next to the affected
  figures; keep listing mirror rows in ledger-derived panels but
  labelled as mirror rows under investigation — never silently present
  them as real earnings; show no mirror-derived figure as a confirmed
  earning or a balance. The mismatch is logged artifact-side in the
  honest-failure pattern (surfaced, not swallowed). On agreement, show
  the (equal) totals with no mismatch note.
- **The dashboard must NOT display sandbox-only rows at all** — it
  reads only the durable live mirror, never a sandbox/test database.

### 3.5 What this does NOT do (hard limits)

- This does NOT delete, alter, expire, or relabel the sandbox-only
  `sim-batch-test-1` rows, and does NOT decide their fate.
- This does NOT touch `RewardAccounting.tsx` in any way — not one line.
  The Mission 6 finding-1 repair (replacing the hardcoded zero
  literals in `RewardAccounting.tsx` with values derived from the
  mirrored ledger totals) is NOT authorized and is NOT part of this
  build. The dashboard's mismatch mechanism is PREVENTION (the defect
  class cannot recur silently in the new section); it is not a repair
  of the existing section.
- This does NOT change the Mission 6 rewards block, the coordinator
  block, or any existing panel's copy. The existing Reward accounting
  section keeps rendering exactly as it does on build `8582d78e`,
  self-contradiction included, until a repair is separately authorized.

---

## 4. Refresh — rides the existing flow (D-M7-6, D-M7-9)

- **No new cron. No new schedule.** The dashboard rides the existing
  refresh flow: the 10-minute coordinator pass
  (`atlas-coordinator-pass-10m`, which exports `coordinator.json` and
  runs the guarded rewards sub-step) plus the existing `refreshAtlasData`
  round-trip. The totals upsert (§3.3) rides the existing refresh step 7
  (rewards mirror) — no new refresh step is added. If the refresh fails,
  the dashboard goes STALE (§4.1) — it does not retry, re-fetch, or
  invent a sync. The refresh failure (M3 finding 1) is NOT repaired here.
- **STALE rule (D-M7-6, binding):** the dashboard is STALE when the
  coordinator mirror OR the rewards mirror is > 1 h old, measured from
  that block's `syncedAt` to now (3600 s). Either block stale → the whole
  dashboard section carries the STALE tag. The STALE tag names which
  block is stale (e.g. `STALE — rewards data 73 min old` — the
  design-time worked example: rewards `syncedAt` 1795019850 ~73 min old,
  coordinator `syncedAt` 1795023408 ~14 min old). Stale data is shown
  honestly, labelled STALE — never hidden, never presented as current.
- **"Not synced yet":** when a block has never synced (`syncedAt`
  null), that block shows `Not synced yet` instead of a time — never `0`,
  never a guessed time. If either block has never synced, the dashboard
  shows `Not synced yet` for that block and the section is STALE.
- **Last-sync panel shows BOTH mirror sync timestamps** (coordinator
  block `syncedAt` and rewards block `syncedAt`), each with its age
  (`synced <date time> (<age> ago)`), each with its own STALE / SYNCED
  tag. The two timestamps are never merged into one "last sync" figure.
- **Re-ingest honesty:** a re-ingest of unchanged data reports "already
  up to date" and does NOT refresh either `syncedAt`. The dashboard's
  sync times are the mirror ingest times of *changed* data, not the time
  of the last refresh attempt.
- **Host `dashboard.json` `sync.stale` is NOT the dashboard STALE flag.**
  It measures host-export freshness (both exports fresh at spec time,
  `stale: false`). The UI STALE flag is computed from the MIRROR
  `syncedAt` values in the `dashboard` block. Do not wire the host flag
  into the UI.

---

## 5. Exact file change list, `verbatim_request`, and verification

### 5.1 File change list (create/edit, with paths)

Paths are relative to the artifact ts-space working tree (see §0). The
coordinator MUST resolve each path there and report any that does not
resolve.

| # | File | Change |
|---|---|---|
| 1 | `client/src/UserDashboard.tsx` | CREATE — `UserDashboardSection`, nine panels per §1.3, zero buttons/inputs/links/forms |
| 2 | `client/src/Mining.tsx` | EDIT — import + `<UserDashboardSection m={m} />` directly below `<RewardAccountingSection m={m} />`, above Settings. Nothing else in this file changes. Do NOT touch the two stale "no miner yet" strings (repair NOT authorized). Do NOT touch the hook order (M6 crash fix stays as-is). |
| 3 | `server/src/schema.ts` | EDIT — add drizzle definition for `mining_dashboard_host_totals` (§3.2). Nothing else changes. |
| 4 | `drizzle/0007_dashboard_host_totals.sql` | CREATE — additive migration 0007 (§3.2) |
| 5 | `drizzle/meta/_journal.json` | EDIT — journal entry idx 6 for 0007 (following 0006's idx 5) |
| 6 | `server/src/actions.ts` | EDIT — (a) extend `ingestRewardsState` to upsert the totals singleton (§3.3); (b) `getMining` gains the `dashboard` block (§2–§3). No new action. No change to the existing `rewards` or `coordinator` blocks. `refreshAtlasData` gains NO new step (totals ride existing step 7). |

**NOT changed:** `client/src/RewardAccounting.tsx` (finding-1 repair NOT
authorized), any host file under `~/workspace/atlas/` (`core/`,
`config/`, `data/` — Lane C's scope, not this lane's), any cron or
schedule, any other tab or section, any safety setting.

Resulting Mining tab order (verify after edit): MiningDashboard,
WalletCenter, EarningsSection, HistorySections, PayoutSection,
CalculatorSection, MinerPrototypeSection, CoordinatorSection,
RewardAccounting, **UserDashboard**, SettingsSection, HelpSection.

### 5.2 Exact `verbatim_request` text for the coordinator to pass to `artifact.edit`

The coordinator MUST pass the following text verbatim as the
`verbatim_request` to `artifact.edit` (artifact slug
`atlas-command-center`). Do not paraphrase it — it is the build contract:

> ATLAS Master Mission 7 — User dashboard section (simulation only, artifact `atlas-command-center`, current build 8582d78e). Add ONE new section to the Mining tab, directly BELOW the existing "Reward accounting — Master Mission 6" section and above Settings; do not move, restyle, or reword any existing section; no new tab. CREATE `client/src/UserDashboard.tsx` exporting `UserDashboardSection` (same `m` prop as `RewardAccountingSection`, reading only the new `getMining` `dashboard` block), and EDIT `client/src/Mining.tsx` to import it and render `<UserDashboardSection m={m} />` directly below `<RewardAccountingSection m={m} />` — that is the ONLY change to `Mining.tsx`: do not touch the "no miner yet" strings, do not touch hook order, do not touch Start/Stop (stay hard-disabled). The section has NINE panels in this exact order, with the exact headings, labels, and empty-state copy below: (1) Dashboard status banner — header "User dashboard — Master Mission 7", subtitle "Simulation only — derived from the coordinator and reward engine outputs. Nothing here is live earnings.", scope line "Showing all users — no user accounts exist yet (0 users).", rows Mode "Simulation only", Emergency stop "ON — all live activity held", Mining "Disabled", Pool connection "None — read-only stats polling only", Data freshness STALE/SYNCED per mirror age, Mirror check "Mirror check: agree" or on mismatch "Mirror mismatch — figures under investigation"; empty-state banner "No mining activity yet. The dashboard is running in simulation only — there is nothing to show but honest zeros." (2) Hashrate — rows "Current hashrate" and "Average hashrate", both "not measured" (UNAVAILABLE); body "Hashrate: not measured" / "No measurement yet — Gate 1 (measured hashrate in a real browser) has not been run for the Mission 4 prototype. Published figures from other projects are shown in the Miner Prototype section above and are not ATLAS measurements." / "Average hashrate: not measured — Cannot compute — hashrate not measured"; NO hashrate number in H/s while unmeasured. (3) Shares — four stat cards "Pool shares accepted", "Pool shares rejected", "Local-test shares accepted", "Local-test shares rejected" (RECORDED); empty state "No pool shares yet — 0 accepted / 0 rejected."; note "Pool shares are the only shares that count toward rewards or worker activation. Local-test shares come from the Mission 4 local-test relay only — they are not real mining shares and never earn anything."; rejection-rate line only when pool total > 0. (4) Duration & worker status — "Total mining duration" = "No mining sessions yet" (UNAVAILABLE) while 0 sessions, else "<Xh Ym Zs> over <N> worker sessions (DERIVED host)"; "Worker sessions" count (RECORDED); heading "Worker status — 0 workers"; summary "Active 0 · Registered 0 · Degraded 0 · Suspended 0 · Revoked 0 · Pending 0"; empty state "No workers registered yet. The coordinator is running in simulation only — there is nothing to coordinate."; per-worker lines "<name> — <type: Browser / Desktop> — <lifecycle status verbatim> — Hashrate: not measured — Pool shares: <accepted> accepted / <rejected> rejected" when workers exist; never display a token, token hash, or wallet address. (5) Earnings — estimated vs confirmed — "Estimated earnings" = "Cannot estimate — hashrate not measured" (UNAVAILABLE) with body "Estimated earnings: Cannot estimate — hashrate not measured" / "No estimate can be computed until a hashrate has been measured (Gate 1) and shares have been accepted by the pool. Estimates never create a payable balance."; "Confirmed earnings" = XMR to 6 decimals (DERIVED host, SIMULATION) with body "Confirmed earnings (SIMULATION): <x> XMR" / "Confirmed earnings come only from settled reward batches — verified accepted shares and confirmed pool rewards. Simulation only — no real earnings yet."; never combine estimate and confirmed into one total. (6) Balances — "Available balance" and "Pending rewards" (DERIVED host, SIMULATION), XMR to 6 decimals; body "Available balance: <x> XMR" / "Pending rewards: <x> XMR — no open reward batches" / "Balances are derived from the ledger (SIMULATION). Pending rewards are amounts in open or held reward batches that have not settled yet — they are not available and not confirmed." (7) Lifetime earnings & previous payouts — "Lifetime earnings" XMR to 6 decimals (DERIVED host, SIMULATION); "Previous payouts" = "No payouts yet — no payout has ever been attempted (Gate 4 closed)" (RECORDED); body "Lifetime earnings: <x> XMR — no settled reward batches yet" / "Previous payouts: No payouts yet — no payout has ever been attempted (Gate 4 closed)" / "Lifetime earnings are the sum of all settled user allocations and referral rewards since the ledger began. Payouts require explicit authorization, successful security testing, and a treasury design — none exists." (8) Efficiency — "Share efficiency" = "Cannot compute — no pool shares yet" (UNAVAILABLE) while 0 pool shares, else "<x>% over <n> pool shares (RECORDED)"; body "Share efficiency: Cannot compute — no pool shares yet" / "Efficiency is accepted shares divided by all pool shares (accepted + rejected). Local-test shares are never counted."; never 0% or 100% on an empty denominator. (9) Last sync time — BOTH mirror timestamps, each "synced <date time> (<age> ago)" with its own STALE/SYNCED tag, never merged; "Not synced yet" when never synced; body "Both mirrors must be fresh for this dashboard to be current. If either is more than 1 hour old, the whole dashboard is marked STALE. A re-ingest of unchanged data reports "already up to date" and does not refresh these times." All figures come from the getMining dashboard block only — NO hardcoded figure literal anywhere in the component as a displayed value (grep-enforced); all amounts XMR to 6 decimals from integer piconero only; NO USD/fiat figure anywhere; zero <button>, <input>, <a>, or <form> in the section; tables collapse to stacked cards below ~640px; no horizontal overflow at 390px; status as text, never colour alone. SERVER: in `server/src/schema.ts` add drizzle table `mining_dashboard_host_totals` (singleton row id INTEGER PRIMARY KEY CHECK (id=1); ledger_entries, batches_settled, batches_open, batches_held, total_user_rewards_piconero, total_referral_rewards_piconero, total_atlas_share_piconero, total_pool_fees_piconero, total_payouts_piconero, total_reversals_piconero all INTEGER NOT NULL; source_exported_at INTEGER; synced_at INTEGER); CREATE additive migration `drizzle/0007_dashboard_host_totals.sql` creating that table and add its journal entry (idx 6) in `drizzle/meta/_journal.json`; in `server/src/actions.ts` extend the EXISTING `ingestRewardsState` to upsert the singleton row from the host rewards export `totals` object in the same transaction as the batch/ledger ingest (identical totals + no row changes → report upToDate with 0 added and do NOT touch synced_at; missing totals → leave the stored row untouched, report hostTotalsMissing:true, never fabricate totals); extend `getMining` with a `dashboard` block computed server-side from the mirrored tables only — hashrate status/nulls, pool/local-test share counts, duration seconds over kind='worker' desktop-agent sessions (browser-probe sessions excluded, degenerate rows 0), worker counts + rows, estimatedPiconero null with reason "Cannot estimate — hashrate not measured", confirmed/balance/lifetime piconero sums, payout count/total/rows, efficiencyRate null with reason "Cannot compute — no pool shares yet", mode, emergencyStop, coordinatorSyncedAt, rewardsSyncedAt, stale flag (>3600s on either mirror syncedAt → STALE naming the stale block; null syncedAt → "Not synced yet" + STALE), mirrorDerivedTotals (COUNT/SUM over mining_ledger and mining_reward_batches per entry type), hostVerifiedTotals (from the singleton row; host totalUserRewards = total_user_rewards_piconero + total_referral_rewards_piconero), mismatch boolean + mismatchDetails list (true on ANY disagreement across ledgerEntries, totalUserRewards, totalAtlasShare, totalPoolFees, totalPayouts, batchesSettled; plus duration secondary check when the host duration field is present); on mismatch the component shows HOST-VERIFIED totals plus the verbatim note "Mirror mismatch — figures under investigation" and never presents a mirror-derived figure as a confirmed earning or balance. NO new ingest action, NO new cron, NO new refresh step (totals ride existing refresh step 7); do NOT touch `client/src/RewardAccounting.tsx` in any way; do NOT delete, alter, or relabel any sim-batch-test-1 rows; do NOT mirror any token, session token, or password hash. Run the full pipeline (migration, typecheck, bundle, publish) and report the new build id.

### 5.3 Typecheck + sandbox verification steps (build lane, before handoff to Lane E)

Same method as M6 Lane D (§3), extended for the dashboard block:

1. **Typecheck:** `bun run typecheck` (client + server) — PASS, exit 0,
   zero errors. Any error found is fixed in this build's files only.
2. **Migration 0007 validation:** apply 0007 against an in-memory
   SQLite DB shaped like the pre-0007 schema (post-0006); insert the
   singleton row; verify a second row with `id = 1` is rejected and a
   row with `id != 1` violates the CHECK. Verify the journal entry
   (idx 6) is well-formed.
3. **Grep checks on `UserDashboard.tsx`:** zero `<button>`, `<input>`,
   `<a>`, `<form>`; zero hardcoded displayed-figure literals — grep for
   `0 XMR`, `0.000000 XMR`, and bare numeric XMR literals outside the
   verbatim copy strings listed in §1.3 (any hit outside those strings
   is a defect and must be removed); verbatim strings from §1.3
   confirmed present; no `password_hash`, `token_hash`,
   `session_token_hash` anywhere in the new/changed files.
4. **Changed-file sweep:** only the six files in §5.1 changed. Any
   other diff is out of scope and must be reverted or explicitly
   reported.
5. **Sandbox `getMining` (all-zero baseline):** on the sandbox
   action layer, `getMining` returns the `dashboard` block with the
   §2.3 expected values — all-zero totals, `estimatedPiconero` null +
   verbatim reason, `efficiencyRate` null + verbatim reason,
   `durationSeconds` 0 / `No mining sessions yet`, `mismatch: false`,
   `hostVerifiedTotals` all 0, `mirrorDerivedTotals` all 0, and the
   `stale` flag correct for the sandbox mirror's `syncedAt` values
   (STALE when either block is > 1 h old; `Not synced yet` when a
   `syncedAt` is null).
6. **Sandbox ingest with a 1 XMR sim batch:** `ingestRewardsState`
   with a 1 XMR simulation batch + 2 ledger entries (the M6 sandbox
   shape: ATLAS 0.25 + user 0.75 XMR) updates BOTH the
   mirror-derived totals AND the host-verified totals consistently —
   `getMining` then derives userRewards 750,000,000,000 pico
   (0.75 XMR) / atlasShare 250,000,000,000 pico (0.25 XMR) on BOTH
   sides, `ledgerEntries` 2 on both sides, `batchesSettled` 1 on both
   sides, `mismatch: false`. (Sandbox only — durable storage keeps 0
   batches / 0 ledger entries; no fictional earnings ship.)
7. **Sandbox mismatch proof:** on the sandbox only, ingest rows that
   disagree with the totals block (e.g. mirror shows 2 entries /
   0.75 XMR, host totals say 0 entries / 0 XMR — the Mission 6
   finding-1 shape). `getMining` MUST return `mismatch: true` with the
   disagreeing quantities named in `mismatchDetails`, and the
   host-verified (0) totals as the displayed figures. A second
   sub-case with agreeing non-zero fixture totals returns
   `mismatch: false`.
8. **Re-ingest reports upToDate:** an identical re-ingest returns
   `upToDate: true` with 0 added, and NEITHER `syncedAt` (rewards
   block nor totals row) advances.
9. **STALE rendering input check:** with the rewards mirror > 1 h old,
   the block reports `stale: true` naming the rewards block (the
   design-time state is the test case — §4).
10. **No console errors; mobile 390 px overflow 0** — source-level
    where the build lane cannot render; the rendered proof is Lane E's
    job (§6). The build lane MUST NOT claim a render it did not perform.

---

## 6. Verification checklist — Lane E (acceptance; execute after deployment)

Lane E executes this against the NEW build id (reported by the build
lane). Every item is PASS / FAIL with evidence (capture id or log
excerpt). No item may be marked PASS from source inspection alone where
a render is required.

### 6.1 Rendered checks (fresh interactive audit — desktop 1440 px + mobile 390 px)

- [ ] **E1. Mining tab selects cleanly on desktop (1440 px)** with zero
  console errors; the User dashboard section renders directly BELOW
  the Reward accounting section and above Settings; tab/section order
  otherwise unchanged (MiningDashboard, WalletCenter, EarningsSection,
  HistorySections, PayoutSection, CalculatorSection,
  MinerPrototypeSection, CoordinatorSection, RewardAccounting,
  UserDashboard, SettingsSection, HelpSection).
- [ ] **E2. Desktop-viewport screenshot of the dashboard section**
  (1440 px). **ACCEPTANCE CHECK — this closes Mission 6 finding 2 for
  this section.** M6 had no desktop-viewport screenshot of the Mining
  tab or reward section; the same gap MUST NOT be repeated for this
  section. Screenshot must show all nine panels.
- [ ] **E3. Mobile render (390 px):** Mining tab selects cleanly, all
  nine panels present in §1.3 order, zero console errors, mobile
  overflow 0 px at 390 px, cards stacked (no horizontal scroll).
- [ ] **E4. All zeros honest:** SIMULATION tags visible; verbatim
  estimate reason `Cannot estimate — hashrate not measured`, verbatim
  efficiency reason `Cannot compute — no pool shares yet`, verbatim
  duration empty state `No mining sessions yet`, verbatim payouts empty
  state `No payouts yet — no payout has ever been attempted (Gate 4
  closed)` all visible; no figure presented as live earnings; no
  USD/fiat figure anywhere in the section.
- [ ] **E5. Zero controls:** no button, input, link, or form anywhere
  in the section (DOM check, not just source grep); Start/Stop visibly
  disabled; no user picker, no login, no demo user rows.
- [ ] **E6. STALE rendering check:** with the rewards mirror > 1 h old
  (the state at build time), the section renders STALE naming the
  rewards block, with figures still shown (labelled STALE), not hidden
  and not presented as fresh. Both mirror sync timestamps visible, each
  with its own STALE / SYNCED tag.
- [ ] **E7. Reload-persistence check — desktop + mobile.
  ACCEPTANCE CHECK — this closes Mission 6 finding 3 for this section.**
  Reload the page, re-select Mining, confirm the section re-renders
  with the same figures on BOTH viewports. Record the reload explicitly
  (step log, not just a summary count).
- [ ] **E8. Other tabs / orb / refresh / emergency stop still render**
  (Overview desktop: orb, tabs, refresh state, emergency stop ON);
  no regression in the Reward accounting section's rendering (its
  content is unchanged — finding 1 is carried, NOT fixed; do not
  report its contradiction as a new failure, and do not report it as
  fixed).

### 6.2 Action-layer re-verification (independent, sandbox + live read-only)

- [ ] **E9.** Live `getMining` (read-only) returns the `dashboard`
  block with the §2.3 all-zero baseline; `mismatch: false`;
  `hostVerifiedTotals` all 0; `mirrorDerivedTotals` all 0; live mirror
  still batches `[]` / entries `[]` (no fictional earnings shipped;
  durable storage unchanged).
- [ ] **E10.** Sandbox re-run of §5.3 steps 6–8 (1 XMR sim batch →
  both totals sides consistent; fixture disagreement → `mismatch:
  true` + host-verified totals shown; identical re-ingest →
  `upToDate: true`, `syncedAt` unmoved).
- [ ] **E11.** No token / session token / password hash in the
  `dashboard` block or in the new mirror table (same assertion shape
  as the M5 mirror test). Entry hashes are audit data and are not
  displayed by the dashboard.
- [ ] **E12.** Migration 0007 applied on the deployed build; journal
  idx 6 present; singleton row exists (or is correctly absent with
  `hostVerifiedTotals: null` + `mismatchDetails:
  ["host totals not yet synced"]` if no ingest has landed yet — either
  state is acceptable if reported honestly, never a fabricated zero).
- [ ] **E13.** Diagnostics still green (existing 23 must stay green;
  any new dashboard diagnostic the build lane added is reported with
  its number and result).

### 6.3 Explicitly NOT acceptance criteria for this build

- The Mission 6 finding-1 self-contradiction in `RewardAccounting.tsx`
  is NOT fixed by this build and is NOT a failure of this build. Lane E
  records its carried state; it does not fail E1–E13 over it.
- Desktop-viewport screenshot of the REWARD section and the M6
  reload-persistence check remain owed from M6; E2/E7 close them for
  the DASHBOARD section only. If Lane E can capture the reward section
  on desktop in the same audit, record it as a bonus, not as a
  requirement.
- Gate 1 (measured hashrate), the refresh failure, and the stale "no
  miner yet" copy are carried, not fixed, not failed here.

---

## 7. Known issues carried (NOT fixed by this spec — D-M7-12)

1. **Mission 6 finding 1 — self-contradictory reward display.** Rendered
   Reward accounting section shows settled sim batch `sim-batch-test-1`
   (1 XMR, ATLAS 0.25 + test-user 0.75) while the isolated DB holds 0
   batches / 0 entries; Honest zero state panel hardcodes zero literals
   in `RewardAccounting.tsx`. NOT fixed here. Fix needs a
   repair-authorized inspection; this spec's contribution is prevention
   only (§3).
2. **Mission 6 finding 2 — desktop screenshot owed.** Now an acceptance
   check for THIS build (§6 E2) for the dashboard section.
3. **Mission 6 finding 3 — reload-persistence owed.** Now an acceptance
   check for THIS build (§6 E7) for the dashboard section.
4. **Gate 1 still unmeasured.** Every hashrate reads "not measured".
5. **Refresh failure carried** (M3 finding 1). STALE labelling is the
   mitigation, not the fix.
6. **Stale "no miner yet" copy carried** (M4 finding 4) — exactly two
   strings in `Mining.tsx`. Repair needs a repair-authorized inspection.
7. **Also carried:** SupportXMR fallback not implemented (no verified
   stats-API URL, never guessed); per-miner pool reward endpoint
   unverified (real-mode batch recording is an interface, not a build);
   referral rate 5% is a design parameter to confirm before any
   real-mode settlement; minimum payout still null/placeholder; D-M5-1
   (`none:browser-probe` marker instead of NULL); host memory above the
   70% cap; mempool.space disputed; daemon restarts of undetermined
   cause; DB file growth partly unexplained.

## 8. Handoff checklist (what the build lane receives)

- [ ] §1: component spec — file, placement, nine panels with verbatim copy.
- [ ] §2: `dashboard` block — field names (host-matched), derivation rules,
  expected live all-zero values.
- [ ] §3: mismatch mechanism — migration 0007 (singleton table, exact
  columns), `ingestRewardsState` extension, `getMining` both-sides +
  flag, non-repair statement for finding 1 and `RewardAccounting.tsx`.
- [ ] §4: refresh — rides existing flow, STALE / "Not synced yet" rules.
- [ ] §5: exact file change list (6 files), verbatim `verbatim_request`
  text, typecheck + sandbox verification steps.
- [ ] §6: Lane E acceptance checklist (desktop 1440 px + mobile 390 px +
  reload persistence as acceptance checks).

**Stop — specification complete. No artifact was edited by this lane. The
coordinator executes the artifact edit from §5.2 and hands the new build
id to Lane E for §6.**
