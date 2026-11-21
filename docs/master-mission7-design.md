# ATLAS — Master Mission 7: User Dashboard (Earnings Dashboard) — Design

**Mission:** Master Mission 7 — User dashboard (earnings dashboard)
**Date:** Wednesday, 2026-11-18
**Author:** Lane A (design)
**Status:** DESIGN ONLY. No code, no migration, no config change, no database write,
no artifact change was made by this lane. This document is the binding contract for
the build lane.
**Scope:** The earnings dashboard IN SIMULATION, built on the coordinator (Mission 5)
and reward engine (Mission 6) outputs. There are no real earnings: 0 users,
0 workers, 0 shares, 0 ledger rows. Every figure the dashboard shows is derived
from host exports or is an honest null/zero, clearly marked as such.

## 0. Grounding — what this design rests on

Read before writing this design (all under `~/workspace/atlas/`):

- Mission 1 inspection report (`docs/master-mission1-inspection-report-2026-11-18.md`)
  §8, Mission 7 row: "Earnings dashboard (current/average hashrate,
  accepted/rejected shares, duration, worker status, estimated vs confirmed earnings
  clearly distinguished, balances, lifetime earnings, previous payouts, efficiency,
  last sync time)" — built on the coordinator + reward engine outputs, must NOT
  fabricate live statistics. Also §6 (accounting basis: confirmed pool rewards only,
  integer piconero, attribution by verified accepted shares) and §4.5 (the five
  prototype gates; Gate 1 measured hashrate UNMEASURED).
- Mission 6 design (`docs/master-mission6-design.md`) — design conventions carried
  here: host DB is system of record, artifact is a read-only display mirror
  (D-M6-1); integer piconero, never floats (D-M6-2); balances derived by `SUM`,
  never stored (D-M6-12); simulation marking everywhere (M6 §8); no new cron,
  ride the existing pass (D-M6-8); placement directly below the previous section,
  no new tab (D-M6-13).
- Mission 5 design (`docs/master-mission5-design.md`) §7 — panel conventions carried
  here: verbatim headings/labels/empty-state copy; provenance tags
  (SNAPSHOT / RECORDED / ESTIMATE / UNAVAILABLE); the hashrate rule ("not measured"
  until a real probe measurement exists); no start control; no registration form;
  tables collapse to stacked cards below ~640 px; mobile overflow 0 at 390 px;
  status as text, never colour alone.
- Mission 6 report (`docs/master-mission6-report-2026-11-18.md`), Unresolved
  findings 1–6 — carried, NOT fixed by this design (see §9). Finding 1 in
  particular is the lesson this design is built around: the Mission 6 display is
  self-contradictory (a sandbox-only settled batch shown alongside hardcoded zero
  literals), and this dashboard must be designed so that class of defect cannot
  recur silently.

**Safety state (unchanged):** emergency_stop true, mining disabled, trading
paper-only, eligible capital $0. No wallets, keys, or seed material. No real
payouts, no pool connection for earning, no share submission to any pool, no mining
activation, no spending. Gate 4 (a real payout) is a hard gate requiring explicit
authorization + successful security testing + a treasury design — none exists.

**Baseline facts (verified by the coordinator just before this design was written,
and re-confirmed read-only by this lane):**

- Live host DB (`data/atlas.db`): `user_version` 3, `integrity_check` ok; users 0,
  workers 0, shares 0, sessions 0, ledger 0, reward_batches 0, payouts 0,
  referrals 0; pool_stats 26 rows, decisions 209, events 76, metrics 830.
- Live artifact mirror (`atlas-command-center`, `getMining`): rewards batches []
  and entries [] — the Mission 6 self-contradiction's `sim-batch-test-1` rows are
  SANDBOX-ONLY, not in the live mirror. Live mirror totals are all 0.
- Mirror sync state at check: rewards block `stale:true`, `syncedAt` 1795019850
  (~73 min old); coordinator block `syncedAt` 1795023408 (~14 min old).
- Pool (MoneroOcean, point-in-time at check): 269,742,496 H/s, 5,000 miners,
  height 3,809,161. `xmrPriceUsd` null.
- `data/rewards.json` (host export, read by this lane): all totals 0,
  `ledger_entries` 0, `batches` [], `ledger` [], chain "ledger empty — chain
  trivially valid, 0 entries". `data/coordinator.json`: `hashrate.status`
  `not-measured`, `measured_hps` null, shares all 0, workers all 0.

**Labelling convention.** Every figure in this document carries one of three
labels, following the Mission 1 / Mission 4 / Mission 5 discipline:

- **VERIFIED** — measured or confirmed against a live source, the live host, or an
  official document cited here.
- **ESTIMATE** — computed from verified inputs with stated assumptions; a projection,
  never a measurement, never a payable balance.
- **ASSUMPTION** — a design choice or an unconfirmed property; the build/test lanes
  must verify it before relying on it.

No figure in this document is a promise of earnings. Realized mining revenue
remains **$0**.

## Decisions (binding on the build lane)

| # | Decision |
|---|---|
| D-M7-1 | Host is the system of record; artifact tables are a read-only display mirror (M5 D1, M6 D-M6-1 carried). Dashboard data is DERIVED from `data/coordinator.json` + `data/rewards.json` + DB queries — no new stored truth. **No new DB tables are needed on the host** (see §1). No new artifact mirror tables either (§1). |
| D-M7-2 | Estimated earnings are NULL with the verbatim reason "Cannot estimate — hashrate not measured" while Gate 1 is unmeasured and shares are 0. Never derived from pool-wide hashrate, never a guessed number (§3). |
| D-M7-3 | Confirmed earnings = ledger `SUM`, SIMULATION-tagged while mode is `simulation-only`. An estimate must never be added to a confirmed figure or a balance (§3). |
| D-M7-4 | Duration = total seconds over closed desktop-agent worker sessions from the `sessions` table; 0 sessions → verbatim "No mining sessions yet". Browser probe sessions are excluded (local test, not mining) (§4). |
| D-M7-5 | Efficiency = accepted / (accepted + rejected) over pool-origin shares only; denominator 0 → null with the verbatim reason "Cannot compute — no pool shares yet" (§4). |
| D-M7-6 | The dashboard is STALE when the coordinator mirror OR the rewards mirror is > 1 h old; "Not synced yet" when never synced. Last-sync time shows BOTH mirror sync timestamps (§5). |
| D-M7-7 | MIRROR-MISMATCH rule (the Mission 6 lesson): the dashboard compares the mirror's own derived ledger totals against the host-verified totals carried in the mirrored rewards export. On any disagreement it shows the HOST-VERIFIED totals plus the verbatim note "Mirror mismatch — figures under investigation", and NEVER silently presents mirror rows as real earnings (§6). |
| D-M7-8 | Placement: a new "User dashboard" section in the Mining tab, directly BELOW the Reward accounting section; the existing Mining tab section order is otherwise unchanged; NO new tab; zero buttons, inputs, links, or forms in the dashboard section; Start/Stop stay hard-disabled and untouched (§7). |
| D-M7-9 | No token, session token, or password hash is ever mirrored or displayed. No new cron. The dashboard rides the existing refresh flow (§8). |
| D-M7-10 | Every figure carries its provenance (host export vs mirror derivation) — see the data-flow table in §2. A figure with no provenance is a defect, not a display choice. |
| D-M7-11 | Amounts are shown in XMR to 6 decimal places (e.g. `0.000000 XMR`), converted from integer piconero only. No USD/fiat figure anywhere: `xmrPriceUsd` is null, so no conversion is attempted, ever (§2). |
| D-M7-12 | This design does NOT repair any carried issue (§9). In particular it does NOT fix the Mission 6 hardcoded zero literals in `RewardAccounting.tsx` (finding 1) and does NOT repair the refresh failure (finding 5) or the stale "no miner yet" copy (finding 6). Each needs its own repair authorization. The dashboard is designed so the finding-1 defect class cannot recur silently (§6); that is prevention, not repair. |
| D-M7-13 | Scope: the dashboard renders the host-global derived view and labels it as such. No user account system exists (M1 §8, later mission), so there is no viewer identity to bind a per-user view to. The build lane must NOT invent a login, a "current user" picker, or demo user rows. Per-user scoping is defined in the queries (§2) but has nothing to bind to until auth exists. |

---

## 1. Data rules — derived only; no new tables

**No new host tables.** Every dashboard figure is derivable from tables that
already exist at `user_version` 3:

| Dashboard need | Existing source |
|---|---|
| Hashrate status / measured value | `data/coordinator.json` `hashrate` (derived from probe/agent measurements; null today) |
| Shares accepted / rejected | `shares` via `data/coordinator.json` `shares` (pool vs local-test split) |
| Duration | `sessions` (`kind='worker'`, desktop-agent only — §4) |
| Worker status | `workers` via `data/coordinator.json` `workers` counts |
| Confirmed earnings, balances, lifetime earnings | `ledger` + `reward_batches` via `data/rewards.json` `totals` / `balances` (derived `SUM`s, M6 D-M6-12) |
| Previous payouts | `payouts` via `data/rewards.json` `totals.total_payouts_piconero` |
| Efficiency | `shares` (same counts as the Shares panel) |
| Last sync time | The mirror's own `syncedAt` values (artifact state, not host tables) |

**No new artifact mirror tables.** The dashboard reads only mirror tables that
already exist: `mining_workers`, `mining_shares`, `mining_sessions`,
`mining_ledger`, `mining_reward_batches`, `mining_payouts` (Missions 2/5/6).
The `getMining` action gains a `dashboard` block (same pattern as the existing
`coordinator` and `rewards` blocks) that carries the derived dashboard values
plus the two mirror sync timestamps plus the host-verified totals used by the
mismatch check (§6). If the build lane finds a derived field missing from
`getMining`, it extends the existing `dashboard` block — it does not create a
new table, a new action, or a new refresh step.

**One additive host-export field (derived, not stored).** Duration (§4) is not
currently carried in `data/coordinator.json` (which has only `sessions_active`).
The coordinator export gains one derived field, computed at export time from the
`sessions` table in the D8 derived-state pattern (M5 D8: computed from tables +
config at export time; if the file is deleted it is regenerated with no loss):

```json
"worker_sessions_duration_seconds": 0
```

No new column, no new table, no stored aggregate — the value is recomputed on
every export. The artifact cross-checks it against its own mirrored
`mining_sessions` rows; a disagreement is a mismatch (§6, secondary check).

**What is NOT a source.** Pool-wide stats (`pool_stats`: pool hashrate, miner
count, block height) are context only, never dashboard inputs — the pool's total
hashrate says nothing about ATLAS's share of a reward (M6 §1.2). The Mining tab
calculator's output never enters the dashboard. Local-test shares
(`origin='local-test'`) never enter any shares, efficiency, duration, or earnings
figure. `workers.reported_hashrate_hps` is an agent self-report only; it is never
a measured hashrate and never feeds the estimate (§3).

---

## 2. Data flow and provenance

```
Host (system of record)                              Artifact (display mirror)
─────────────────────────                            ─────────────────────────
atlas.db (user_version 3)                            drizzle mining_* tables
  users 0, workers 0, shares 0,                          (mirror of host rows,
  sessions 0, ledger 0,                                  deduped on host id,
  reward_batches 0, payouts 0                            re-ingest = "already
  pool_stats 26, decisions 209                          up to date")
        │                                                      ▲
        │ coordinator export (atomic write,                    │ ingestCoordinatorState
        │ 10-min pass) + rewards export                       │ + ingestRewardsState
        ▼                                                      │ (existing actions,
data/coordinator.json ──► refreshAtlasData ────────────────────┘
data/rewards.json    ──► (existing tracked round-trip:         getMining reads
                           started/baselineTs/landedTs/failed,  mirror tables only
                           5 s polling, 5-min honest timeout)   + dashboard block
```

The dashboard block in `getMining` carries, per figure, the value AND its
provenance. Provenance tags follow the existing tab pattern:

- **RECORDED** — a value read from a host export or a mirrored host row.
- **DERIVED (host)** — computed by the host from its own tables at export time
  (e.g. ledger `SUM`s in `rewards.json` totals, session duration).
- **DERIVED (mirror)** — computed by the artifact from mirrored rows (e.g. the
  mirror's own ledger `SUM`, used only for the §6 comparison).
- **ESTIMATE** — a projection from verified inputs; in this mission the estimate
  field is null (§3), so no ESTIMATE figure exists yet.
- **UNAVAILABLE** — the source has no value (null), shown as such, never as 0.

**Figure-by-figure provenance (normative):**

| Dashboard figure | Host source | Mirror derivation | Provenance tag shown |
|---|---|---|---|
| Current hashrate | `coordinator.json` `hashrate.status` / `measured_hps` | none (read through) | RECORDED (or UNAVAILABLE when null) |
| Average hashrate | no stored measurement series exists → null (§3) | none | UNAVAILABLE |
| Shares accepted / rejected | `coordinator.json` `shares` (pool origin) | `SUM` over mirrored `mining_shares` where `origin='pool'` | RECORDED |
| Duration | `coordinator.json` `worker_sessions_duration_seconds` (§1) | `SUM` over mirrored `mining_sessions` (§4) | DERIVED (host) |
| Worker status counts | `coordinator.json` `workers` | counts over mirrored `mining_workers` | RECORDED |
| Estimated earnings | null by rule (§3) | none | UNAVAILABLE |
| Confirmed earnings | `rewards.json` `totals.total_user_rewards_piconero` | `SUM` over mirrored `mining_ledger` `user_allocation` + `referral_reward` | DERIVED (host), SIMULATION-tagged |
| Available balance | `rewards.json` `balances` (per-user `SUM`) | `SUM` over mirrored `mining_ledger` per user | DERIVED (host), SIMULATION-tagged |
| Pending rewards | `rewards.json` `totals` + open/held batch list | open/held rows in mirrored `mining_reward_batches` | DERIVED (host), SIMULATION-tagged |
| Lifetime earnings | `rewards.json` `totals` (user + referral sums, all settled batches) | `SUM` over mirrored `mining_ledger` (all time) | DERIVED (host), SIMULATION-tagged |
| Previous payouts | `rewards.json` `totals.total_payouts_piconero` + `payouts` rows | rows in mirrored `mining_payouts` | RECORDED |
| Efficiency | `coordinator.json` `shares` (pool origin) | same counts as Shares panel | DERIVED (host) |
| Last sync time | artifact mirror `syncedAt` (coordinator block + rewards block) | none — this IS the mirror state | RECORDED (mirror time) |

**Scope note (D-M7-13).** Every per-user query is parameterized by `user_id`
(`WHERE user_id = :user_id`), but with 0 users and no auth the section renders
the host-global view: totals summed over all users, with the verbatim scope line
in §7. The build lane does not bind the view to a user, and does not render a
user picker.

---

## 3. Estimated vs confirmed earnings — the hard rule

**Estimated earnings (D-M7-2, binding).** With Gate 1 unmeasured (no probe
hashrate exists anywhere — `coordinator.json` `hashrate.measured_hps` is null)
and 0 shares, NO estimate is computable. The estimate field is **null**, and the
panel shows the verbatim reason:

> `Cannot estimate — hashrate not measured`

Rules that follow from this:

- The estimate is never derived from pool-wide hashrate. The MoneroOcean pool
  figure (269,742,496 H/s at check) is the whole pool's hashrate; ATLAS's share
  of it is unknown and unknowable from that number. Any formula of the form
  `pool_hashrate × …` producing an ATLAS earnings figure is forbidden.
- The estimate is never a guessed number, never a benchmark figure (the Mission 4
  published figures — 5800X 10.0–12.4 kH/s, 7950X 26,960 H/s — are other
  projects' benchmarks, not ATLAS measurements), and never back-filled from
  `workers.reported_hashrate_hps` (self-report only).
- The estimate is never added to a confirmed figure or a balance. Estimated and
  confirmed earnings live in separate panels with separate tags; no panel shows a
  combined "total earnings" that mixes them.
- **When an estimate becomes computable (future mission, not this one):** it
  requires BOTH a measured hashrate (Gate 1 passed, with a recorded measurement
  series) AND a stated formula with stated inputs (price source, network
  hashrate source, pool fee, split). Until both exist, the field stays null with
  the same verbatim reason. The formula itself is owed by the profitability
  mission (Mission 9), not by this design — this design does not invent one.
- **Average hashrate** follows the same rule: there is no stored series of
  measured hashrate values, so no average can be computed. It is null with the
  verbatim reason `Cannot compute — hashrate not measured` (see §7, Panel 2).
  Recording a measurement series is a future mission's schema decision; this
  mission adds no table for it (§1).

**Confirmed earnings (D-M7-3, binding).** Confirmed earnings = ledger `SUM`
over `user_allocation` + `referral_reward` entries (M6 §5.1 sign convention),
SIMULATION-tagged while mode is `simulation-only`. Today: 0 entries → `0.000000
XMR`. Confirmed earnings come only from settled reward batches; open/held
batches contribute nothing to confirmed earnings (they contribute to *pending*,
§7 Panel 6). A simulated figure is never shown without the SIMULATION tag, and
the word "earned" never appears next to a simulated figure without that
qualifier (M6 §8).

---

## 4. Duration and efficiency — definitions

**Duration (D-M7-4, binding).**

```
duration_seconds = SUM over worker sessions of
    (COALESCE(ended_at, exported_at) - created_at)
    WHERE kind = 'worker'
      AND the session is a desktop-agent session
      AND ended_at IS NULL OR ended_at > created_at
```

- Only `kind='worker'` sessions count (M5 §2.3). User sessions (`kind='user'`)
  are login sessions, not mining, and never count.
- Only **desktop-agent** sessions count. A browser probe session
  (`?atlas-miner-test=1`, `session_token_hash` marker `none:browser-probe`) is a
  local-test session, not mining (M5 §5.2); its seconds never count toward mining
  duration. An open session contributes up to the export time (`exported_at`),
  never beyond it.
- Sessions with `ended_at <= created_at` (degenerate rows) contribute 0 and are
  counted in the panel's diagnostic line, not hidden.
- Display format: total seconds rendered as `Xh Ym Zs` (e.g. `2h 14m 09s`),
  plus the session count (`N worker sessions`). Today: 0 sessions → the
  verbatim empty state `No mining sessions yet` (§7, Panel 4).
- The host export carries the value (§1); the artifact cross-checks it against
  mirrored `mining_sessions` rows (§6, secondary check).

**Efficiency (D-M7-5, binding).**

```
efficiency = accepted / (accepted + rejected)
    over pool-origin shares only (origin = 'pool')
```

- Displayed as a percentage to one decimal place (e.g. `98.5%`) with the
  RECORDED tag and the share counts it was computed from
  (`over N pool shares`).
- Denominator 0 (today: 0 accepted, 0 rejected) → the value is **null**, never
  `0%` and never `100%`. The panel shows the verbatim reason:

> `Cannot compute — no pool shares yet`

- Local-test shares never enter the numerator or the denominator. A rejected
  local-test share is a prototype bug signal (M5 §3.4), not a worker health
  signal, and is not shown in this panel at all — local-test counts live in the
  Coordinator section's Shares panel (M5 §7.2), not here.
- No threshold, flag, or `degraded` inference is drawn from efficiency in this
  mission (the M5 §3.4 thresholds are ASSUMPTIONS for the build lane to confirm
  with pool data; this dashboard reports the number only).

---

## 5. STALE rules and last sync time (D-M7-6, binding)

- The dashboard is **STALE** when the coordinator mirror OR the rewards mirror
  is > 1 h old, measured from that block's `syncedAt` to now. Either block stale
  → the whole dashboard section carries the STALE tag (a stale half is not a
  fresh dashboard). The STALE tag names which block is stale
  (`STALE — rewards data 73 min old`).
- **"Not synced yet"** when a block has never synced (`syncedAt` null). A block
  that has never synced shows `Not synced yet` instead of a time, never `0` and
  never a guessed time. If either block has never synced, the dashboard shows
  `Not synced yet` for that block and the section is STALE.
- **Last-sync panel shows BOTH mirror sync timestamps** (coordinator block
  `syncedAt` and rewards block `syncedAt`), each with its age
  (`synced <date time> (<age> ago)`), each with its own STALE / SYNCED tag.
  The two timestamps are never merged into one "last sync" figure — they are
  different mirrors of different exports and can disagree.
- A re-ingest of unchanged data reports "already up to date" (M5 §1.4, M6 §10)
  and does NOT refresh the `syncedAt` — a re-ingest must never be mislabelled as
  a fresh sync (Mission 3 finding 1, carried — §9). The dashboard's sync times
  are the mirror ingest times of *changed* data, not the time of the last
  refresh attempt.
- **Worked example from the baseline:** at design time the rewards block was
  ~73 min old (`syncedAt` 1795019850, `stale:true`) while the coordinator block
  was ~14 min old. Under this rule the dashboard renders **STALE — rewards data
  73 min old**, with the rewards figures still shown (labelled STALE) rather
  than hidden or presented as fresh. Stale data is shown honestly; it is never
  hidden and never presented as current.
- The refresh failure (Mission 3 finding 1, carried) is NOT repaired here
  (D-M7-12). The STALE labelling is the mitigation, not the fix.

---

## 6. MIRROR-MISMATCH rule (D-M7-7, binding — the Mission 6 lesson)

**The rule.** On every render of the dashboard, the artifact compares the
mirror's own derived ledger totals against the host-verified totals carried in
the mirrored rewards export (`rewards.json` `totals`: `ledger_entries`,
`total_user_rewards_piconero`, `total_atlas_share_piconero`,
`total_pool_fees_piconero`, `total_referral_rewards_piconero`,
`total_payouts_piconero`, `batches_settled`). The comparison covers, at minimum:

| Compared quantity | Mirror-derived side | Host-verified side |
|---|---|---|
| Ledger entry count | `COUNT(*)` over mirrored `mining_ledger` | `totals.ledger_entries` |
| Total user rewards | `SUM` over mirrored `mining_ledger` where `entry_type IN ('user_allocation','referral_reward')` | `totals.total_user_rewards_piconero + totals.total_referral_rewards_piconero` |
| Total ATLAS share | `SUM` over mirrored `mining_ledger` where `entry_type = 'atlas_share'` | `totals.total_atlas_share_piconero` |
| Total pool fees | `SUM` over mirrored `mining_ledger` where `entry_type = 'fee'` | `totals.total_pool_fees_piconero` |
| Total payouts | `SUM` over mirrored `mining_ledger` where `entry_type = 'payout'` | `totals.total_payouts_piconero` |
| Settled batches | `COUNT(*)` over mirrored `mining_reward_batches` where `status='settled'` | `totals.batches_settled` |

**On any disagreement:**

1. The dashboard shows the **HOST-VERIFIED totals** (from the rewards export),
   not the mirror-derived ones.
2. The dashboard shows the visible verbatim note, in the section header area,
   next to the affected figures:

> `Mirror mismatch — figures under investigation`

3. The mirror rows are still listed (in the ledger-derived panels) but are
   labelled as mirror rows under investigation — they are never silently
   presented as real earnings. No figure derived from the disagreeing mirror
   rows is shown as a confirmed earning or a balance.
4. The mismatch is logged (artifact-side, in the same honest-failure pattern as
   the refresh flow: surfaced, not swallowed).

**On agreement:** the dashboard shows the (equal) totals with no mismatch note.
Agreement on today's all-zero state (0 = 0) is a valid trivial agreement and
says nothing about the check working — the build lane must test the check with
non-zero fixture data on a temp/sandbox mirror (see §10), not with zeros alone.

**What this rule is for.** Mission 6 finding 1: the rendered Reward accounting
section showed a settled simulation batch (`sim-batch-test-1`, ATLAS 0.25 +
test-user 0.75 XMR) while the isolated database held 0 batches and 0 ledger
entries, and the section's own copy simultaneously claimed "all 0 XMR today"
and "no pool rewards" — because the Honest zero state panel hardcoded zero
literals that could never agree with the ledger above it. This rule makes that
defect class *visible on render* instead of silent: if the mirror and the host
export ever disagree again, the user sees the host-verified figures plus the
mismatch note, not two contradictory stories. **This design does NOT repair
finding 1 itself** (D-M7-12): the hardcoded literals in `RewardAccounting.tsx`
and the fate of the sandbox-only `sim-batch-test-1` rows remain for a
repair-authorized inspection. The dashboard must not display sandbox-only rows
at all — it reads only the durable live mirror, never a sandbox/test database.

**Secondary check (duration).** The dashboard also compares the host-export
duration (§1, §4) against the artifact's own `SUM` over mirrored
`mining_sessions`. A disagreement shows the host-export value plus the same
verbatim mismatch note. The ledger comparison above is the primary check and
must exist even if the duration check is deferred; the duration check must not
be substituted for it.

**General-case requirement (binding).** The mismatch rule is written for the
general case, not today's zeros. The hardcoded-zero defect in Mission 6 bites
only when the ledger has rows — and the live ledger will have rows the moment
real or simulated settlement happens. The dashboard's figures are therefore
always derived from the totals (host-verified first, mirror-derived for
comparison), never hardcoded literals. **No hardcoded zero (or any hardcoded
figure) is permitted anywhere in the dashboard section.** A panel whose value
is a literal in the component source is a defect, full stop — the build lane's
grep check (§10) enforces this.

---

## 7. UI spec — User dashboard section in the Mining tab (exact, build-ready)

### 7.1 Placement and rules

- **Location:** inside the existing Mining tab (`client/src/Mining.tsx`, artifact
  `atlas-command-center`). **NO new tab.** The section sits **directly below the
  "Reward accounting — Master Mission 6" section** and above Settings. It does
  not reorder, restyle, or reword any existing section. Current tab order,
  unchanged (M6 §10, carried): MiningDashboard, WalletCenter, EarningsSection,
  HistorySections, PayoutSection, CalculatorSection, MinerPrototypeSection,
  CoordinatorSection, RewardAccountingSection, **[UserDashboardSection]**,
  SettingsSection, HelpSection.
- **Component:** new `client/src/miner/UserDashboardSection.tsx` (name is a
  build-lane suggestion; the section heading and copy below are binding). Data
  comes from the extended `getMining` action (`dashboard` block, §1–§2) reading
  the artifact `mining_*` mirror tables only. React Query refetch: same 30 s
  cadence as the rest of the Mining tab. No new refresh schedule.
- **Provenance:** every figure carries a SNAPSHOT / RECORDED / ESTIMATE /
  UNAVAILABLE tag plus a SIMULATION tag while mode is `simulation-only`,
  following the existing tab pattern. Nothing is labelled live unless it was
  measured in the current probe/session.
- **Zero controls.** There is no button, input, link, or form anywhere in this
  section: no "claim", no "withdraw", no "refresh now", no "recalculate", no
  user picker, no settings control. Request-payout stays in the existing Payout
  center, hard-disabled (Mission 2). The existing Start/Stop buttons in the
  Mining dashboard stay **hard-disabled with no handler** (Missions 2/4/5/6) and
  are untouched by this section.
- **Copy that must NOT appear in this section:** any hashrate number presented
  as ATLAS's without a `MEASURED` tag and a measurement time; the words
  "verified", "confirmed", or a checkmark next to any worker, address, or
  hashrate that has only passed format checks or self-report; "There is no
  miner yet" (stale copy, Mission 4 finding 4 — carried, §9; the correct
  framing is: the prototype exists; mining is disabled; no measurement exists
  yet); any earnings, balance, or payout figure derived from shares or
  hashrate; any USD/fiat figure; any combined "total earnings" mixing estimated
  and confirmed figures.
- **Responsive / accessibility (binding, M5 §7.4 carried):** tables/cards
  collapse to stacked cards below ~640 px; no horizontal page overflow at
  390 px (mobile overflow 0); all status text is text, not colour alone
  (a screen reader must hear `Active` / `Registered` / `not measured`, not just
  see a dot); disabled/absent controls are absent, not greyed-out fake buttons.

### 7.2 Section layout (top to bottom)

**Section header (verbatim):**

> **User dashboard — Master Mission 7**
> Subtitle: `Simulation only — derived from the coordinator and reward engine outputs. Nothing here is live earnings.`
> Scope line (verbatim, while users = 0): `Showing all users — no user accounts exist yet (0 users).`
> Mismatch note slot (shown only on mismatch, verbatim): `Mirror mismatch — figures under investigation`

**Panel 1 — Dashboard status (status banner, always visible):**

| Row label | Value today (VERIFIED) | Value when populated |
|---|---|---|
| Mode | `Simulation only` | `Simulation only` (unchanged until a later mission + authorization changes it) |
| Emergency stop | `ON — all live activity held` | Same; if ever OFF, shows `OFF` + the time it was lifted + the decision id |
| Mining | `Disabled` | `Disabled` |
| Pool connection | `None — read-only stats polling only` | Same until a pool connection is separately authorized |
| Data freshness | `STALE — rewards data 73 min old` (at design time; §5) | `SYNCED` / `STALE — <block> data <age> old` / `Not synced yet` |
| Mirror check | `Mirror check: agree (0 = 0)` | `Mirror check: agree` / `Mirror mismatch — figures under investigation` |

Empty-state banner (verbatim, shown while users = 0, workers = 0, shares = 0,
ledger = 0):

> `No mining activity yet. The dashboard is running in simulation only — there is nothing to show but honest zeros.`

**Panel 2 — Hashrate:**

Heading: `Hashrate`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Current hashrate` | `not measured` | UNAVAILABLE |
| `Average hashrate` | `not measured` | UNAVAILABLE |

Body (verbatim while Gate 1 is unmeasured — this is the state today and until a
probe run exists):

> `Hashrate: not measured`
> `No measurement yet — Gate 1 (measured hashrate in a real browser) has not been run for the Mission 4 prototype. Published figures from other projects are shown in the Miner Prototype section above and are not ATLAS measurements.`

Average-hashrate line (verbatim, shown while no measurement series exists):

> `Average hashrate: not measured — Cannot compute — hashrate not measured`

Rules: this panel shows **no number** in H/s while unmeasured — not 0, not an
estimate, not a benchmark. After Gate 1 passes, it shows the measured value,
the probe session id, threads/mode, measurement time, and tag `MEASURED`; the
"not measured" copy is replaced, not kept alongside. A desktop agent
self-report is shown here only with the tag `REPORTED — agent self-report, not
measured by ATLAS`, and never replaces the `not measured` state for the browser
prototype. The pool-wide hashrate is never shown in this panel.

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

Rejection-rate line (shown only when pool total > 0, else hidden — not shown
as 0%):

> `Pool rejection rate: <x>% over <n> pool shares (RECORDED)`

**Panel 4 — Duration & worker status:**

Heading: `Duration & worker status`

Duration block:

| Row label | Value today | Provenance tag |
|---|---|---|
| `Total mining duration` | `No mining sessions yet` | UNAVAILABLE |
| `Worker sessions` | `0` | RECORDED |

Duration line when sessions exist: `Total mining duration: <Xh Ym Zs> over <N> worker sessions (DERIVED host)` — plus the diagnostic line when degenerate
rows exist: `<n> session rows with ended_at <= created_at counted as 0 seconds.`

Worker-status block:

Heading: `Worker status — 0 workers`

Status summary (exact labels, today's values): `Active 0 · Registered 0 ·
Degraded 0 · Suspended 0 · Revoked 0 · Pending 0`

Empty state (verbatim, shown when the table has no rows):

> `No workers registered yet. The coordinator is running in simulation only — there is nothing to coordinate.`

Populated-row rules (when workers exist): one line per worker —
`<name> — <type: Browser / Desktop> — <lifecycle status verbatim> — Hashrate:
not measured — Pool shares: <accepted> accepted / <rejected> rejected`. The
lifecycle status is shown verbatim (`Registered`, `Active`, `Degraded`,
`Suspended`, `Revoked`, `Pending`); an `Active` row carries a green dot, every
other status a grey/amber dot, and the derived grouping "Inactive" appears in
the summary only — never as the row's status. Worker detail (registration time,
XMRig version / "Binary unverified", token issuance) stays in the Coordinator
section above; this panel does not duplicate it and never displays a token,
token hash, or wallet address.

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

Rules: the two figures are never combined, never summed, and never shown in a
single "total earnings" line. The estimate is never derived from pool-wide
hashrate (§3). When confirmed earnings are non-zero in future, the panel shows
the settled-batch count alongside (`from <n> settled reward batches`).

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
pending = the not-yet-settled share of open/held batches (0 today). No stored
running-balance column is ever read or shown (M6 D-M6-12). A referral reward
included in the available balance is labelled as funded from the ATLAS 25%
(`includes <x> XMR referral rewards from the ATLAS 25%` — shown only when
non-zero).

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

Rules: lifetime earnings = `SUM` over all settled batches (all time), never
reset by a refresh or a new batch. Previous payouts lists each payout row when
any exist (date, amount XMR, status, txid or `no txid — simulation`), newest
first; the minimum payout is still null/placeholder (undecided — flag for the
user, do not decide it here). No payout is ever shown as "pending" unless a
payout row with that status exists.

**Panel 8 — Efficiency:**

Heading: `Efficiency`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Share efficiency` | `Cannot compute — no pool shares yet` | UNAVAILABLE |

Body (verbatim):

> `Share efficiency: Cannot compute — no pool shares yet`
> `Efficiency is accepted shares divided by all pool shares (accepted + rejected). Local-test shares are never counted.`

Rules: shown as a percentage to one decimal place when computable
(`Efficiency: <x>% over <n> pool shares (RECORDED)`), null with the verbatim
reason above when the denominator is 0 (§4). Never `0%`, never `100%`, on an
empty denominator.

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

Rules: both timestamps are shown, each with its own STALE / SYNCED tag (§5).
The two are never merged into one figure.

---

## 8. Safety, secrets, and scheduling (D-M7-9, binding)

- **No token, session token, or password hash is ever mirrored or displayed.**
  The dashboard reads only the mirror tables in §1; the mirror carries no
  `token_hash`, `token_salt`, `session_token_hash`, or `password_hash` (M5 D4
  carried). Entry hashes from the reward ledger ARE mirrored (public audit data,
  not secrets — M6 §10) but the dashboard does not display them; they belong to
  the Reward accounting section's ledger table. No worker token value, no wallet
  address, and no email is displayed in this section.
- **No new cron.** The dashboard rides the existing refresh flow: the 10-minute
  coordinator pass (`atlas-coordinator-pass-10m`, which exports
  `coordinator.json` and runs the guarded rewards sub-step) plus the existing
  `refreshAtlasData` round-trip. No new schedule, no duplicated pass, no new
  watchdog entry. If the refresh fails, the dashboard goes STALE (§5) — it does
  not retry, re-fetch, or invent a sync.
- **Hard limits (never violated by this design or its build):** never mine,
  never trade, never create wallets/keys, never change `config/atlas.json`,
  never lift the emergency stop (true throughout), never spend, never submit
  shares, never attempt a payout, never activate a worker. Simulation only.
- **No demo data.** No demo users, workers, shares, earnings, or payouts are
  seeded — the dashboard starts empty and stays honest (M5 §7.3, M6 §8).

---

## 9. Known issues — carried, NOT fixed by this design (D-M7-12)

These are carried forward from Missions 3–6. This design lane fixes none of
them; each needs its own authorization. The dashboard is specified so it neither
repeats them nor papers over them.

1. **Reward section display is self-contradictory (Mission 6 finding 1, the
   Mission 6 lesson).** The rendered Reward accounting section shows a settled
   simulation batch `sim-batch-test-1` (MoneroOcean, gross 1 XMR, 10 shares;
   ATLAS 0.25 + test-user 0.75 XMR) while the isolated database holds 0 reward
   batches and 0 ledger entries, and its own copy simultaneously claims "all 0
   XMR today", "no pool rewards", and "Pool rewards confirmed 0 XMR". The
   Honest zero state panel hardcodes "Available balance 0 XMR / Lifetime
   rewards 0 XMR / Pool rewards confirmed 0 XMR" as literals in
   `RewardAccounting.tsx`, so it can never agree with the ledger above it — and
   its own counts read "Reward batches 1 / Ledger entries 2". The live mirror
   totals are all 0 (VERIFIED for this design: rewards batches [] and entries
   []); the `sim-batch-test-1` rows are SANDBOX-ONLY. **Not fixed here.** The
   recommended fix (decide the fate of `sim-batch-test-1`, replace the hardcoded
   zero literals with values derived from the mirrored ledger totals, then
   re-verify with the two missing captures) needs a repair-authorized inspection
   (`artifact.inspect` with `repair_authorized: true`) if the user orders it.
   This design's contribution is prevention only: the §6 mirror-mismatch rule
   and the ban on hardcoded literals in the new section, so the defect class
   cannot recur silently in the dashboard.
2. **Desktop-viewport screenshot of the reward section NOT established
   (Mission 6 finding 2).** No desktop-viewport screenshot of the Mining tab or
   reward section exists; every Mining/reward capture is 390 px mobile-width.
   The dashboard's rendered verification (§10) must include the desktop capture
   for the new section — the Missions 2–6 gap must not be repeated for this
   section.
3. **Reload-persistence check NOT established (Mission 6 finding 3).** No
   recorded reload followed by re-selecting Mining and confirming the section
   re-renders. The dashboard's verification (§10) must include the reload check
   on desktop + mobile.
4. **Gate 1 still unmeasured (Mission 6 finding 4).** Every hashrate reads "not
   measured". A fresh interactive probe run is owed. This design fabricates
   nothing in its place (§3, §7 Panel 2).
5. **Refresh failure carried (Mission 6 finding 5 / Mission 3 finding 1).**
   Refresh intermittently fails at the platform spawn step and the UI has
   mislabelled a re-ingest as "Refresh complete". No refresh repair is
   authorized or attempted here. The dashboard labels stale mirrors STALE (§5)
   rather than presenting them as fresh.
6. **Stale "no miner yet" copy carried (Mission 6 finding 6 / Mission 4
   finding 4).** Exactly two strings remain in `Mining.tsx` (dashboard + Help)
   saying there is no miner yet; the prototype is built, so they are stale.
   Repair needs a repair-authorized inspection. This design forbids repeating
   the claim in the new section (§7.1).
7. **Also carried, out of this mission's scope:** SupportXMR fallback not
   implemented (M6 finding 7 / D-M5-3 — no verified stats-API URL, never
   guessed); the per-miner pool reward endpoint is unverified, so real-mode
   batch recording is still an interface, not a build; referral rate 5% is a
   design parameter to confirm before any real-mode settlement; minimum payout
   still null/placeholder; D-M5-1 (`none:browser-probe` marker instead of NULL);
   host memory above the 70% cap; mempool.space disputed; daemon restarts of
   undetermined cause; DB file growth partly unexplained. None is fixed, decided,
   or papered over here.

---

## 10. Test plan and verification owed (build lane)

All derivation tests run against a TEMPORARY database (fresh schema at
`user_version` 3, fixture data inserted by the test file) — never the live DB
(M6 D-M6-11 pattern). Stdlib only (`unittest`, same pattern as Mission 5's
`core/test_atlas_coordinator.py` and Mission 6's `core/test_reward_engine.py`).
The dashboard derivation lives in a host-side read function (same shape as the
M6 `reward_totals()` read function) so it is unit-testable without the artifact.

### 10.1 Derivation tests (each: name → what "pass" means)

1. **All-zero derivation.** Fixture: empty DB (0 users, 0 workers, 0 shares,
   0 sessions, 0 ledger rows). PASS: every dashboard figure is 0 or null with
   the exact verbatim empty-state copy from §7; estimate null with
   "Cannot estimate — hashrate not measured"; efficiency null with "Cannot
   compute — no pool shares yet"; duration "No mining sessions yet"; last sync
   "Not synced yet" when both `syncedAt` are null.
2. **Estimate stays null with shares but no hashrate.** Fixture: pool-accepted
   shares exist, `measured_hps` null. PASS: estimate is still null with the
   verbatim reason — shares alone never make an estimate computable.
3. **Estimate stays null with hashrate but no shares.** Fixture (hypothetical,
   temp DB only): a measured hashrate recorded, 0 shares. PASS: estimate is
   still null — both inputs are required (§3).
4. **Confirmed earnings = ledger SUM.** Fixture: settled sim batches with known
   ledger rows (reuse the M6 scenario figures: 1 XMR batch, ATLAS 0.25, user
   0.75). PASS: confirmed earnings, available balance, and lifetime earnings
   equal the ledger `SUM`s exactly, in integer piconero, SIMULATION-tagged.
5. **Duration definition.** Fixture: 2 closed desktop-agent worker sessions
   (3,600 s + 900 s), 1 open desktop-agent session (opened 300 s before export),
   1 browser probe session (7,200 s), 1 user session (3,600 s), 1 degenerate
   worker session (`ended_at <= created_at`). PASS: duration = 3,600 + 900 +
   300 = 4,800 s; probe, user, and degenerate sessions contribute 0; degenerate
   row counted in the diagnostic line.
6. **Efficiency definition.** Fixture: 95 pool-accepted, 5 pool-rejected,
   40 local-test accepted, 10 local-test rejected. PASS: efficiency 95.0%
   over 100 pool shares; local-test shares excluded from both terms.
7. **Efficiency null on empty denominator.** Fixture: 0 pool shares.
   PASS: null with "Cannot compute — no pool shares yet", never `0%` or `100%`.
8. **Mirror-mismatch detection.** Fixture: a sandbox mirror whose ledger `SUM`
   disagrees with the host-verified totals in the rewards export (e.g. mirror
   shows 2 entries / 0.75 XMR, export shows 0 entries / 0 XMR — the Mission 6
   finding-1 shape). PASS: the dashboard function returns the HOST-VERIFIED
   totals plus the mismatch flag; no mirror-derived figure is presented as a
   confirmed earning or balance. A second sub-case with agreeing non-zero
   fixture totals PASSes with no mismatch flag.
9. **Stale rule.** Fixture: coordinator `syncedAt` 14 min old, rewards
   `syncedAt` 73 min old. PASS: dashboard STALE, naming the rewards block.
   Sub-cases: both fresh → SYNCED; one null → "Not synced yet" + STALE.
10. **No hardcoded literals.** Grep over the new dashboard component source:
    PASS: no hardcoded `0 XMR`, `0.000000 XMR`, or other hardcoded figure
    literal appears as a displayed value (all values flow from the `dashboard`
    block). This is the direct regression test for the Mission 6 finding-1
    defect class.
11. **No secrets in the dashboard payload.** Fixture: host DB with token hashes,
    session token hashes, and password hashes present. PASS: the `dashboard`
    block and the mirror tables it reads contain none of them (same assertion
    shape as the M5 mirror test).
12. **Per-user scoping is parameterized.** Fixture: two users with different
    ledger sums. PASS: the per-user query returns each user's own sum; the
    host-global view returns the combined sum with the scope line. No viewer
    identity is invented (no login, no picker).

### 10.2 Rendered verification owed (build lane — none exists yet)

A fresh interactive audit must select the Mining tab on desktop + mobile on the
new build, scroll to the User dashboard section, and capture it — the Missions
2–6 gap (no captured Mining-tab render on the current build, findings 2–3)
must not be repeated for this section. The audit checks, and reports each
explicitly:

- All nine panels present, in the §7.2 order, directly below the Reward
  accounting section; tab/section order otherwise unchanged; Start/Stop visibly
  disabled; zero buttons, inputs, links, or forms in the section.
- All zeros honest; SIMULATION tags visible; the verbatim estimate reason and
  the verbatim efficiency/duration empty states visible; no console errors;
  mobile overflow 0 at 390 px.
- **Desktop-viewport screenshot of the dashboard section** (closes finding 2
  for this section).
- **Reload-persistence check** (reload, re-select Mining, confirm the section
  re-renders with the same figures) on desktop + mobile (closes finding 3 for
  this section).
- **STALE rendering check:** with the rewards mirror > 1 h old, the section
  renders STALE naming the rewards block (the design-time state is the test
  case — §5 worked example).
- **Mismatch rendering check (sandbox only):** with a sandbox mirror disagreeing
  with the export, the section shows host-verified totals plus the verbatim
  "Mirror mismatch — figures under investigation" note. Never tested against
  the live mirror.

**Diagnostics additions (proposed, build lane confirms numbering):** a test
asserting the dashboard derivation matches host totals on the live DB (trivial
0 = 0 today, reported as such); a test asserting the mismatch check fires on a
fixture disagreement; a test asserting no dashboard figure is a hardcoded
literal. Existing 23 diagnostics must stay green.

---

## 11. What the build lane receives from this design (handoff checklist)

**Build (later mission, needs authorization):**

1. Host: one derived read function for the dashboard (stdlib only, same shape
   as M6 `reward_totals()`), plus the one additive derived export field
   `worker_sessions_duration_seconds` in `data/coordinator.json` (§1) — no new
   tables, no new cron, no config change.
2. Artifact: `getMining` `dashboard` block + `UserDashboardSection.tsx` per §7
   (exact headings, labels, empty-state copy, and the estimate/efficiency/
   duration rules). Mirror tables unchanged. No token/session/password hash
   ever mirrored.
3. Tests per §10.1 on temp DBs; rendered verification per §10.2 (desktop +
   mobile + reload + STALE + sandbox mismatch).

**Verify (evidence owed by the build lane — none exists yet):**

- Dashboard derivation on the live DB returns the all-zero state with the exact
  verbatim copy from §7; estimate null with the verbatim reason; efficiency
  null with the verbatim reason; duration "No mining sessions yet".
- A second export/refresh with no changes reports "already up to date" and does
  not refresh the sync times.
- The mismatch check fires on a sandbox fixture disagreement and shows
  host-verified totals + the verbatim note.

**Do not build in this mission:**

- No pool connection for earning, no stratum client, no share submission
  (Gate 2 — separate authorization).
- No reward-engine change, no payout flow, no treasury design (Gate 4 —
  separate authorization + security testing).
- No repair of the Mission 6 hardcoded literals, the refresh failure, or the
  stale "no miner yet" copy (each needs its own repair authorization, §9).
- No in-browser registration, no artifact → host write path, no user auth
  build-out, no login or user picker.
- No mining activation on any host; Start/Stop stay hard-disabled.

## 12. Open items and risks carried forward (not resolved by this design)

1. **Per-user scoping** — deferred by design (D-M7-13). A per-user dashboard
   needs the user account system (M1 §8: registration, auth, sessions) first;
   the security design for that (auth, rate limiting, no cross-user data
   exposure) is owed by the mission that proposes it.
2. **Average hashrate series** — no stored measurement series exists, so the
   average is null indefinitely until a mission defines where measured hashrate
   samples are recorded (schema decision owed, not snuck in here).
3. **Estimate formula** — owed by the profitability mission (Mission 9), with
   stated inputs (price source, network hashrate source, pool fee, split).
   This design deliberately does not invent one.
4. **Pool-stats `network_hashrate` sourcing** — carried (M5 §10.4); the
   response field is not guaranteed and the dashboard never uses pool stats as
   an earnings input in any case.
5. **Share-table retention/pruning** — carried (M5 §3.2, §10.3); the 30-day raw
   + daily-rollup rule is a requirement, not an implementation.

**Stop — design complete. Awaiting authorization before any Mission 7 build work. Do not start building.**
