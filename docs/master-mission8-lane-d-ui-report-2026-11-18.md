# ATLAS Master Mission 8 — Lane D (UI build) SPECIFICATION

**Mission:** Master Mission 8 — Admin command center (private admin dashboard,
simulation only)
**Lane:** D (UI specification ONLY — this lane writes no artifact code, runs no
artifact edit, touches no artifact file)
**Date:** 2026-11-18
**Artifact:** `atlas-command-center`, current build `61fac176` (Mission 7)
**Status:** SPECIFICATION ONLY. The coordinator executes the artifact edit from
this spec (see §5 for the exact `verbatim_request` text). Nothing in this
document is deployed until that edit runs, typechecks, and passes the §5/§6
verification.

## 0. Binding inputs and ground truth

Read first (binding):

- `docs/master-mission8-design.md` (Lane A) — decisions D-M8-1–D-M8-13 are
  binding and are followed exactly, EXCEPT for the single explicitly-flagged
  minimal deviation in §3.1 (migration 0008), which the parent task orders
  and which the design itself flags in §1.1 as ordered by the task.
- `docs/master-mission7-lane-d-ui-report-2026-11-18.md` (Mission 7 UI spec —
  structure and conventions followed exactly here: §0 binding inputs /
  ground truth, §1 new component, §2 `getMining` block, §3 migrations,
  §4 verification, §5 exact `verbatim_request`, §6 sandbox verification).
- `docs/master-mission6-lane-d-ui-report-2026-11-18.md` (ingest patterns,
  migration conventions: `ingestRewardsState`, migration 0006, sandbox
  verification method).
- `docs/master-mission7-report-2026-11-18.md`, Unresolved findings 1–17 —
  carried, NOT fixed by this design (design §9). This spec does NOT repair
  any of them. In particular it does NOT fix the Mission 6 hardcoded zero
  literals in `RewardAccounting.tsx` (design D-M8-12), does NOT repair the
  refresh failure, does NOT fix the stale "no miner yet" copy, and does
  NOT establish the rendered Mining-tab check.
- `core/atlas_dashboard.py` + `data/dashboard.json` + `data/rewards.json` +
  `data/coordinator.json` (host exports — field names the admin block must
  match; see §2.1).

Ground truth (verified read-only by this lane from the live host at
2026-11-18 ~17:21 EST; host clock epoch 1795040508 = 2026-11-18 17:21:48 EST):

- Mining tab order (unchanged): MiningDashboard, WalletCenter,
  EarningsSection, HistorySections, PayoutSection, CalculatorSection,
  MinerPrototypeSection, CoordinatorSection, RewardAccounting,
  UserDashboard, SettingsSection, HelpSection. The new **Admin command
  center** section goes directly BELOW UserDashboard, above Settings.
- Live host DB (`data/atlas.db`): `user_version` 3, `integrity_check` ok;
  users 0, workers 0, shares 0, sessions 0, ledger 0, reward_batches 0,
  payouts 0, referrals 0; pool_stats 42, decisions 293, events 100,
  metrics 1104. Latest decisions: id 293 `coordinator-pass-complete`,
  id 292 `pool-stats-polled`. Latest events: kind `startup`, message
  `atlas_monitor started` (repeated — daemon restarts). Startup events
  all-time: 100 (the 24 h count is a host-module computation at export
  time; this lane does not guess it).
- Live host exports (all `exported_at` 1795040471):
  `data/coordinator.json`: hashrate `not-measured`, `measured_hps` null,
  shares all 0, workers all 0, pool MoneroOcean 259,064,041 H/s,
  4,916 miners, height 3,809,325, `last_decision_id` 293,
  `last_coordinator_pass_at` 1795040470,
  `worker_sessions_duration_seconds` 0 (see §0 gap note — this field IS
  present now, unlike at M7 spec time).
  `data/rewards.json`: all totals 0, `ledger_entries` 0, `batches` [],
  `ledger` [], chain "ledger empty — chain trivially valid, 0 entries".
  `data/dashboard.json`: hashrate not-measured, shares 0/0/0/0, duration
  0 s, workers 0, earnings estimated null + verbatim reason
  `Cannot estimate — hashrate not measured`, confirmed 0
  SIMULATION ONLY, balances `{}`, lifetime all 0, payouts 0 rows,
  efficiency `acceptance_rate` null + reason
  `Cannot compute — no pool shares yet`, sync stale false
  (host-export freshness — NOT mirror freshness, see §4),
  `host_verified_totals` all 0.
- Live snapshot (`data/snapshot.json`, ts 1795040508): CPU 53.88%,
  memory **79.44% used** (still above the 70% cap — standing issue),
  disk 18.95% used, net rx 59,379 B / tx 66,116 B, gpu null, mining
  `disabled`, trading `disabled-paper-only`, emergency_stop true.
  **No daemon start time is recorded anywhere** — daemon uptime is
  therefore UNAVAILABLE by rule (design §5), not guessed.
- Latest metrics row (`metrics`, ts 1795040508): CPU 53.88,
  mem_used_pct 79.44, load1 3.46 / load5 2.74 / load15 1.73,
  disk_used_pct 18.95. Metrics span: MIN(ts) 1794975856 → MAX(ts)
  1795040508 = 64,652 s ≈ 17 h 57 m 32 s (monitoring uptime, §2).
- Config (`config/atlas.json`, per design §0): emergency_stop true,
  mining enabled false, trading paper-only, eligible capital $0,
  limits max_cpu_pct 50, max_mem_pct 70.

**GAPS (recorded, never blockers, never fabricated):**

1. **Live mirror NOT read by this lane.** This subagent's toolset
   exposes no read-only `getMining` call (the artifact action layer is
   not callable from here; per the M6 report, `artifact.edit` is not
   available to this subagent either). Live-mirror state (mirror
   `syncedAt` values, whether the M7 `mining_dashboard_host_totals`
   singleton row exists, current STALE state) is therefore **"to be
   verified by the coordinator at edit time"** — it is NOT guessed
   anywhere in this spec. The §2.3 expected live values are the
   all-zero / null honest state derived from the host exports above,
   which the coordinator MUST confirm against the live mirror before
   the edit lands.
2. **Host admin export NOT landed yet.** `data/admin.json` does NOT
   exist at spec time and `core/atlas_admin.py` does NOT exist (Lane C
   host work runs in parallel). The admin block in §2 is therefore
   spec'd ENTIRELY from the design's field definitions (design §1,
   §2, §4, §5, §8) plus the already-existing host exports above. Any
   host field not yet present is recorded as a gap, never a blocker
   and never fabricated. The artifact side MUST NOT depend on
   `data/admin.json` existing at build time: the `admin` block is
   computed from the mirrored tables only (§2.2), and the
   `ingestAdminState` action (§3.3) must skip cleanly — reporting the
   admin block as "Not synced yet" — when the host export is absent,
   exactly as the M6 refresh step 7 skipped cleanly when the reward
   tables did not exist yet.
3. **`data/diagnostics.json` shape.** At spec time it carries keys
   `results` / `summary` / `ts` (no top-level `exported_at`). The
   admin block's diagnostics freshness MUST therefore use the
   diagnostics `ts` field (or a `diagnostics_exported_at` carried in
   `data/admin.json` if Lane C provides one); it must NOT invent an
   `exported_at`. If neither is present, diagnostics freshness is
   UNAVAILABLE with the note `Diagnostics export time not recorded`.
4. **Duration secondary check wiring (M7 finding 6) still unverified —
   CARRIED, not claimed.** The host field
   `worker_sessions_duration_seconds` IS now present in
   `data/coordinator.json` (value 0), so the duration secondary
   cross-check (§2.4) CAN be wired in this build — but the M7 finding-6
   wiring (the population path from the coordinator mirror payload
   into the comparison) was never independently verified, and this lane
   cannot verify it. This spec therefore wires the check per §2.4 and
   REQUIRES the §4 sandbox proof for it; it does NOT claim the check
   works. If the coordinator finds the population path absent at edit
   time, the check is skipped and the omission is recorded in the
   build report — it never blocks the build and never fabricates a
   duration.

**Where the artifact source lives.** The artifact source tree
(`client/src`, `server/src`, `drizzle/`) is NOT in `~/workspace/atlas/`; it
lives in the ts-space working tree the artifact builder uses (M6 Lane D
report §1, §5; M7 Lane D report §0). This lane therefore could not read
`schema.ts`, `actions.ts`, or `Mining.tsx` directly. File paths below
follow the M6/M7 Lane D file lists exactly; the coordinator MUST resolve
each path against the ts-space tree at edit time and MUST report back any
path that does not resolve, rather than guessing a different path.

---

## 1. New component — `client/src/AdminCommandCenter.tsx`

### 1.1 Identity and placement

- **New file:** `client/src/AdminCommandCenter.tsx` (export
  `AdminCommandCenterSection`, taking the same `m` prop shape as
  `UserDashboardSection` — the `getMining` result).
- **Placement:** in `client/src/Mining.tsx`, import and render
  `<AdminCommandCenterSection m={m} />` directly BELOW
  `<UserDashboardSection m={m} />` and directly ABOVE the Settings
  section. No other line in `Mining.tsx` moves. No existing section is
  reordered, restyled, or reworded. No new tab.
- **Data:** reads ONLY the `admin` block of the `getMining` result
  (§2), plus the `dashboard` block's earnings fields by REUSE (the
  mining panel reuses the dashboard export's earnings block by import
  — it never recomputes confirmed earnings, balances, lifetime, or
  payouts; see §1.3 Panel 2). Never reads any other action, never
  fetches, never writes. React Query refetch: same 30 s cadence as the
  rest of the Mining tab. No new refresh schedule.
- **Zero controls (hard limit):** zero `<button>`, `<input>`, `<a>`,
  `<form>`, or any clickable control anywhere in the section. No
  "suspend worker", no "retry payout", no "refresh now", no
  "recalculate", no filter input, no settings control, no admin picker,
  no login. Start/Stop stay hard-disabled and untouched.
- **No hardcoded figures (hard limit, D-M8-7 / design §7):** NO hardcoded
  zero — or any hardcoded figure — is permitted anywhere in this
  component as a displayed value. Every displayed figure flows from the
  `admin` block (or the reused `dashboard` earnings block). A panel
  whose value is a literal in the component source is a defect, full
  stop. The §5 grep check enforces this. (Verbatim copy strings such as
  `0.000000 XMR` inside empty-state *sentences* are copy, not values:
  they may appear ONLY inside the verbatim strings listed in §1.3, and
  only when the corresponding block value is actually 0 — the component
  MUST render the block value, formatted, and MUST NOT substitute a
  literal for it. Where a verbatim sentence contains a figure, the
  figure in the sentence MUST be produced by formatting the block
  value, never typed as a constant.)
- **Amounts:** XMR to 6 decimal places (e.g. `0.000000 XMR`), converted
  from integer piconero only (`piconero / 1e12`, formatted — never float
  arithmetic on money beyond the display division). **No USD/fiat figure
  anywhere.** `xmrPriceUsd` is null; no conversion is ever attempted.
- **Provenance tags:** every figure carries a SNAPSHOT / RECORDED /
  ESTIMATE / UNAVAILABLE tag plus a SIMULATION tag while mode is
  `simulation-only`, following the existing tab pattern (design §2
  table: RECORDED / DERIVED (host) / DERIVED (mirror) / ESTIMATE /
  UNAVAILABLE). Nothing is labelled live unless measured in the current
  probe/session. A figure with no provenance is a defect, not a display
  choice (D-M8-10).
- **Responsive / accessibility (binding, M5 §7.4 carried):** tables/cards
  collapse to stacked cards below ~640 px; no horizontal page overflow at
  390 px (mobile overflow 0); all status is text, never colour alone (a
  screen reader must hear `Running` / `Stale` / `not measured`, not just
  see a dot); disabled/absent controls are absent, not greyed-out fake
  buttons.
- **Drill-down is inline, not interactive (D-M8-8):** each aggregate
  shows its contributing rows directly beneath it by default (security
  rows, batch rows, payout rows, log rows). There is NO expand/collapse
  control, no row click, no detail page. A row that would need private
  data to show is omitted with the verbatim note
  `Row omitted — private data`.

### 1.2 Section header (verbatim)

> **Admin command center — Master Mission 8**
> Scope line (verbatim, D-M8-13, directly under the section heading):
> `Admin view — aggregates and operational data only. No login exists yet — this section is not access-controlled.`
> Mismatch note slot (shown ONLY on mismatch, verbatim, in the section
> header area next to the affected figures):
> `Mirror mismatch — figures under investigation`

### 1.3 The panels (verbatim headings, labels, and empty-state copy)

Panels render top-to-bottom in this exact order: Panel group 1 (1a–1c),
Panel group 2 (2a–2c), Panel group 3 (3a–3e), Panel group 4 (4a–4b),
Panel group 5 (5a–5b), Panel group 6. Values shown are today's honest
live state; the component MUST compute them from the `admin` block
(and the reused `dashboard` earnings block for Panel 2), never from
literals.

**Panel group 1 — Network**

**Panel 1a — Network — users and workers:**

Heading: `Network — users and workers`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Users` | `0` | RECORDED |
| `Workers total` | `0` | RECORDED |
| `Active` | `0` | RECORDED |
| `Browser` | `0` | RECORDED |
| `Desktop` | `0` | RECORDED |
| `Registered` | `0` | RECORDED |
| `Degraded` | `0` | RECORDED |
| `Suspended` | `0` | RECORDED |
| `Revoked` | `0` | RECORDED |
| `Pending` | `0` | RECORDED |

Empty states (verbatim): `No users yet` when users = 0; `No workers yet`
when workers = 0. Worker counts come from the coordinator export (0)
and are cross-checked against counts over mirrored `mining_workers`.
Per-worker rows (when any exist): id, type, status, registered_at,
last_seen_at ONLY — never `token_hash` / `token_salt` (§1.2 of the
design; a `SELECT *` over `workers` anywhere in this build is a defect).
Per-user data is a COUNT only — no user rows, no user ids, no addresses.
Note the carried M7 finding-7 wording tension: the dashboard counts
distinct user_ids on mirrored ledger entries (0) while `mining_users`
holds 1 scaffold row (`local-user`, no wallet). The admin network panel
counts `users` from the coordinator export (0) and uses the same verbatim
`No users yet` copy — a wording decision is owed, not a repair.

**Panel 1b — Network — hashrate and shares:**

Heading: `Network — hashrate and shares`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Total hashrate` | `not measured` | UNAVAILABLE |
| `Pool shares accepted` | `0` | RECORDED |
| `Pool shares rejected` | `0` | RECORDED |
| `Local-test shares accepted` | `0` | RECORDED |
| `Local-test shares rejected` | `0` | RECORDED |

Empty states (verbatim): hashrate `not measured` (Gate 1 unmeasured);
shares 0: `No shares yet`. This panel shows NO number in H/s while
unmeasured — not 0, not an estimate, not a benchmark. Pool-wide hashrate
(MoneroOcean 259,064,041 H/s) is context only and is NEVER shown here as
ATLAS's hashrate. `workers.reported_hashrate_hps` (agent self-report)
never feeds any figure here.

**Panel 1c — Network — uptime:**

Heading: `Network — uptime`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Monitoring uptime` | `17h 57m 32s` (metrics span at spec time; `Xd Yh Zm` format) | RECORDED |
| `Daemon restarts (24h)` | host-computed count (from `events` kind `startup`, last 24 h) | RECORDED |
| `Daemon restarts (all time)` | `100` at spec time | RECORDED |
| `Daemon uptime` | `Daemon start time is not recorded` | UNAVAILABLE |

Empty state (verbatim): daemon uptime
`Daemon start time is not recorded` (§5). No start time is inferred
from the last `startup` event.

**Panel group 2 — Mining** (all figures SIMULATION-tagged; earnings block
REUSED from the dashboard export, D-M8-2 — the admin section must never
show a different earnings number than the user dashboard)

**Panel 2a — Mining — XMR mined:**

Heading: `Mining — XMR mined`

| Row label | Value today | Provenance tag |
|---|---|---|
| `XMR mined (confirmed, settled batches only)` | `0.000000 XMR (SIMULATION)` | DERIVED (host), SIMULATION |
| `Estimated earnings` | `Cannot estimate — hashrate not measured` | UNAVAILABLE |

"XMR mined" is defined as confirmed ledger earnings (settled batches
only) — NOT pool-wide output and NOT an estimate. The estimate is null
with the verbatim reason `Cannot estimate — hashrate not measured`.
Estimate and confirmed are never combined into one total. The word
"earned" never appears next to a simulated figure without the SIMULATION
qualifier.

**Panel 2b — Mining — rewards:**

Heading: `Mining — rewards`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Confirmed rewards` | `0.000000 XMR (SIMULATION)` | DERIVED (host), SIMULATION |
| `Pending rewards (open/held batches)` | `0.000000 XMR (SIMULATION)` | DERIVED (host), SIMULATION |
| `User allocations` | `0.000000 XMR (SIMULATION)` | DERIVED (host), SIMULATION |
| `ATLAS revenue` | `0.000000 XMR (SIMULATION)` | DERIVED (host), SIMULATION |
| `Pool fees` | `0.000000 XMR (SIMULATION)` | DERIVED (host), SIMULATION |

Empty states (verbatim): pending 0: `No open or held batches`. All 0:
figures shown as `0.000000 XMR (SIMULATION)`. Confirmed = settled
batches only; open/held batches contribute to *pending* only. Batch rows
listed inline below the figures when any exist (batch ref, status,
amounts).

**Panel 2c — Mining — payouts:**

Heading: `Mining — payouts`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Payout volume` | `0.000000 XMR (SIMULATION)` | DERIVED (host), SIMULATION |
| `Payouts count` | `0` | RECORDED |
| `Failed payouts` | `0` (count + inline rows) | RECORDED |

Empty state (verbatim): `No payouts yet` when count = 0. Failed-payout
rows (when any exist): payout id, amount, status, reason where present.

**Panel group 3 — Infrastructure**

**Panel 3a — Infrastructure — host resources:**

Heading: `Infrastructure — host resources`

| Row label | Value today | Provenance tag |
|---|---|---|
| `CPU` | `53.88%` (latest metrics row, with row time) | RECORDED (with row timestamp) |
| `Memory used` | `79.44%` + verbatim `Above the 70% cap` | RECORDED (with row timestamp) |
| `Disk used` | `18.95%` | RECORDED (with row timestamp) |
| `Load 1/5/15 min` | `3.46 / 2.74 / 1.73` | RECORDED |
| `Network rx/tx` | `59,379 B / 66,116 B` | RECORDED |

Rules: CPU/memory/disk come from the latest `metrics` row (highest
`ts`), shown WITH the row timestamp ("as of <time>"). Memory above the
70% cap is shown as the number with the verbatim note
`Above the 70% cap` — never hidden, never re-baselined. If the latest
row is > 10 min old, the panel carries the STALE tag for that figure
(§4).

**Panel 3b — Infrastructure — database health:**

Heading: `Infrastructure — database health`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Integrity check` | `ok` | RECORDED |
| `Schema version` | `3` | RECORDED |
| Per-table row counts | users 0, workers 0, shares 0, sessions 0, ledger 0, reward_batches 0, payouts 0, pool_stats 42, decisions 293, events 100, metrics 1104 | RECORDED |

Empty state / stop condition (verbatim): integrity ≠ ok →
`Database integrity check failed — figures under investigation`, and no
derived figure is presented as verified.

**Panel 3c — Infrastructure — queues:**

Heading: `Infrastructure — queues`

| Row label | Value |
|---|---|
| `Queue lengths` | Verbatim reason below (UNAVAILABLE) |

Body (verbatim):
> `No queue system exists — the coordinator runs synchronously in the 10-minute pass`

No queue figure is invented, and no queue table is created to satisfy
this panel.

**Panel 3d — Infrastructure — connectivity:**

Heading: `Infrastructure — connectivity`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Last pool poll` | MoneroOcean, recorded_at 1795040469, 259,064,041 H/s, 4,916 miners, block height 3,809,325 | RECORDED |
| `MoneroOcean` | last diagnostics outcome | RECORDED |
| `CoinGecko` | last diagnostics outcome | RECORDED |
| `blockchain.info` | last diagnostics outcome | RECORDED |
| `mempool.space` | last diagnostics outcome (flappy — carried, §7) | RECORDED |

Empty state (verbatim): never polled: `Not polled yet`. Config
`blockchain_apis` statuses are shown only with the last live poll time,
labelled `recorded claim, not a live measurement`.

**Panel 3e — Infrastructure — services:**

Heading: `Infrastructure — services`

| Row label | Value | Provenance tag |
|---|---|---|
| `Daemon` | status text + last-seen age | RECORDED |
| `Coordinator pass` | `last_coordinator_pass_at` + `last_decision_id` (293 at spec time) | RECORDED |
| `Watchdog` | last line of `logs/refresh-attempts.log` + its age | RECORDED |

Rules: daemon — snapshot.json `ts` age; fresh < 3 min = `Running`, else
`Stale — last seen <age> ago`. Pid is NOT shown (the snapshot carries no
pid, and none is guessed). Daemon stale (verbatim):
`Stale — last seen <age> ago`.

**Panel group 4 — Security** (definitions design §4; every count with its
inline rows; NO threshold, flag, or `degraded` inference is drawn from any
security count in this mission — the section reports the numbers only. The
word "secure" never appears as a verdict in this section.)

**Panel 4a — Security — workers and shares:**

Heading: `Security — workers and shares`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Suspicious workers` | `0` + rows | DERIVED (host) |
| `Invalid shares` | `0` | DERIVED (host) |
| `Duplicate shares` | `0` + rows | DERIVED (host) |

Empty state (verbatim, each 0): `No events recorded`.
- Suspicious workers: `COUNT` over `workers` where
  `status IN ('suspended','revoked')` OR (pool-origin rejected shares
  ≥ 10 AND rejected / (accepted + rejected) > 0.5 for that worker).
  Rows shown: id, type, status, registered_at, last_seen_at — never
  token fields.
- Invalid shares: `COUNT` over `shares` where `origin='pool'` AND
  `accepted=0`. Local-test rejected shares are NOT counted here (they
  live in the Coordinator section).
- Duplicate shares: groups of `shares` sharing the same non-null
  `external_id` (or, when `external_id` is null, the same `worker_id` +
  `job_id`) with count > 1. Count = number of duplicate rows beyond
  the first per group. Rows shown: external_id/job_id + worker id +
  submitted_at.

**Panel 4b — Security — accounts and payouts:**

Heading: `Security — accounts and payouts`

| Row label | Value today | Provenance tag |
|---|---|---|
| `Account abuse events` | `0` + note | DERIVED (host) |
| `Auth failures` | `0` + note | DERIVED (host) |
| `Payout anomalies` | `0` + rows | DERIVED (host) |

Empty state (verbatim, each 0): `No events recorded`. Abuse note:
`No abuse events recorded`. Auth note:
`No auth-failure events recorded`. Payout anomalies: `COUNT` over
`payouts` where `status='failed'` PLUS `COUNT` over `ledger` where
`entry_type='reversal'`. Rows shown: payout id, amount, status, reason
where present. No `abuse` or `auth_failure` event kind has ever been
recorded (events kinds on file: `startup` and coordinator kinds) — the
absence of the kind is itself reported in the panel notes above.

**Panel group 5 — Operational logs** (latest-50 mirror window, §3.1)

**Panel 5a — Operational logs — decisions:**

Heading: `Operational logs — decisions`

Fields: latest 20 decisions — time, dept, decision, reason. Dept counts
above the list (grouped counts). Window note (verbatim):
`Showing latest 20 of 50 mirrored rows — N total on host`
(where N is the host `decisions_total` from `data/admin.json`; today
293). Messages are redacted per design §1.2 before display (defence in
depth — either layer alone must be sufficient): a message matching
`(?i)(token|secret|password|seed|private.?key|bearer|api.?key)` OR
containing a run of 20+ base58/hex characters that is not a known pool
`external_id`/`job_id` shape is replaced with the verbatim string
`[redacted — possible credential]` and the row is still counted.

**Panel 5b — Operational logs — events:**

Heading: `Operational logs — events`

Fields: latest 20 events — time, kind, message (redacted per §1.2).
Kind counts above the list. Window note (verbatim):
`Showing latest 20 of 50 mirrored rows — N total on host`
(where N is the host `events_total`; today 100). The host DB remains the
complete log; the mirror is a window, never presented as complete.

**Panel group 6 — Last sync:**

Heading: `Admin — last sync`

Fields: Coordinator `syncedAt` + age + tag; Rewards `syncedAt` + age +
tag; Admin `syncedAt` + age + tag. Each shown as
`synced <date time> (<age> ago)` with its own STALE / SYNCED tag. The
three timestamps are never merged into one "last sync" figure. STALE
naming which source is stale (§4, e.g.
`STALE — diagnostics data 73 min old`). `Not synced yet` when a block
has never synced (never `0`, never a guessed time).

**Copy that must NOT appear in this section:** any wallet address, token
hash, session token, password hash, or credential; any per-user
identifier or row; any hashrate number presented as ATLAS's without a
`MEASURED` tag and a measurement time; the words "verified",
"confirmed", or a checkmark next to any worker, address, or hashrate
that has only passed format checks or self-report; the word "secure" as
a verdict; "There is no miner yet" (stale copy, M4 finding 4 — carried,
§7); any earnings, balance, or payout figure derived from shares or
hashrate; any USD/fiat figure; any combined "total earnings" mixing
estimated and confirmed figures; any queue-length number (UNAVAILABLE
by rule, §5 of the design).

---

## 2. `getMining` admin block — computed server-side from ALREADY-MIRRORED data

### 2.1 Field names (must match the host exports)

Field names follow `data/admin.json` (design §1 — Lane C) and, where a
field is reused, `data/coordinator.json` / `data/rewards.json` /
`data/dashboard.json` exactly, so the mirror and the host can be
compared field-for-field. **Because `data/admin.json` does not exist yet
at spec time (§0 gap 2), every admin field below is defined from the
design's definitions, not from a landed file.** If Lane C's export names
a field differently, the coordinator MUST record the difference in the
build report and map it in the `admin` block — it must NOT silently
rename a design field, and must NOT invent a value for a field the
export does not carry (that field is UNAVAILABLE with its verbatim
reason, never approximated).

| Host source | Admin block field | Notes |
|---|---|---|
| `coordinator.json` workers | `networkUsers`, `networkWorkers{Total,Active,Browser,Desktop,Registered,Degraded,Suspended,Revoked,Pending}` + `workerRows` | Counts over mirrored `mining_workers`; per-worker rows id/type/status/registered_at/last_seen_at only |
| `coordinator.json` + `dashboard.json` hashrate/shares | `hashrateStatus`, `totalHashrateHps` (null), `shares{PoolAccepted,PoolRejected,LocalTestAccepted,LocalTestRejected}` | Mirror-derived `SUM` over `mining_shares` by `origin`; hashrate `not-measured` |
| `metrics` span + `events` startup count | `monitoringUptimeSeconds`, `daemonRestarts24h`, `daemonRestartsAllTime`, `daemonUptime` (null + verbatim reason) | `daemonUptime` is ALWAYS null in this mission |
| `rewards.json` totals + `dashboard.json` earnings block (REUSED, D-M8-2) | `mining{ xmrMinedPiconero, estimatedPiconero (null), estimatedReason, confirmedPiconero, pendingPiconero, userAllocationsPiconero, atlasRevenuePiconero, poolFeesPiconero, payoutVolumePiconero, payoutsCount, failedPayoutsCount, failedPayoutRows }` | Earnings figures are the dashboard block's values by import — never recomputed; pending = open/held batches only |
| latest `metrics` row | `infra{ cpuPct, memUsedPct, diskUsedPct, load1, load5, load15, netRxBytes, netTxBytes, metricsRowTs }` | RECORDED with row timestamp; STALE tag if row > 10 min old |
| `PRAGMA integrity_check` / `user_version` / table counts (via admin export) | `dbHealth{ integrityCheck, schemaVersion, tableCounts{ users, workers, shares, sessions, ledger, reward_batches, payouts, pool_stats, decisions, events, metrics } }` | Integrity ≠ ok → verbatim stop note, no derived figure presented as verified |
| (no queue system) | `queueLengths` = null, `queueReason` | Verbatim `No queue system exists — the coordinator runs synchronously in the 10-minute pass` |
| latest `pool_stats` + `diagnostics.json` | `connectivity{ lastPoolPoll{ poolName, recordedAt, hashrate, miners, blockHeight }, endpoints{ moneroOcean, coinGecko, blockchainInfo, mempoolSpace } }` | Config statuses labelled `recorded claim, not a live measurement` |
| `snapshot.json` + coordinator last pass + watchdog log | `services{ daemon{ status, lastSeenAgeSeconds }, coordinatorPass{ lastPassAt, lastDecisionId }, watchdog{ lastLine, lastLineAgeSeconds } }` | Daemon: snapshot `ts` age, fresh < 3 min = `Running`, else `Stale — last seen <age> ago`; pid never shown |
| `workers` + `shares` + `events` + `payouts` + `ledger` (§4 of the design) | `security{ suspiciousWorkers{ count, rows }, invalidShares, duplicateShares{ count, rows }, accountAbuseEvents, authFailures, payoutAnomalies{ count, rows } }` | Host-computed counts (from `data/admin.json`) + mirror-derived counts for the §2.4 secondary check |
| `decisions` / `events` latest-50 window | `logs{ decisions{ rows[≤20 shown], totalOnHost, mirroredCount }, events{ rows[≤20 shown], totalOnHost, mirroredCount } }` | Rows from the §3.1 mirror tables; redaction applied before display (§1.3 Panels 5a/5b) |
| — (mirror state) | `coordinatorSyncedAt`, `rewardsSyncedAt`, `adminSyncedAt` (epoch seconds, nullable) | The three mirror `syncedAt` values; `stale` computed per §4 |
| — (mirror derivation) | `mirrorDerivedTotals` | §2.4 — the mirror side of the comparison |
| — (host verification) | `hostVerifiedTotals` | §2.4 — from the M7 singleton row + the admin export's host totals |
| — (comparison) | `mismatch` (boolean), `mismatchDetails` (list of disagreeing quantities) | §2.4 |
| — (diagnostics freshness) | `diagnosticsSyncedAt` (epoch seconds, nullable) | From `diagnostics.json` `ts` (see §0 gap 3); null → UNAVAILABLE note `Diagnostics export time not recorded` |

### 2.2 Derivation rules (server-side, in `getMining`)

- The block is computed inside the existing `getMining` action from
  mirror tables ONLY (`mining_workers`, `mining_shares`,
  `mining_sessions`, `mining_ledger`, `mining_reward_batches`,
  `mining_payouts`, `mining_dashboard_host_totals` (M7 §3.2), plus the
  new §3.1 tables). **No new ingest action for the admin block itself
  beyond `ingestAdminState` (§3.3). No new action at all for the
  derived figures.** If a derived field is missing, extend this `admin`
  block — do not create a new table, a new action, or a new refresh
  step (design §1, carried).
- **Network:** counts over mirrored `mining_workers` (by lifecycle
  status and by type Browser/Desktop), cross-checked against the
  coordinator mirror counts. Users = the coordinator export count (0
  today) — the admin panel does NOT count `mining_users` scaffold rows.
- **Hashrate / shares:** `SUM` over mirrored `mining_shares` split by
  `origin` (`pool` vs `local-test`). Pool shares are the only shares
  that count toward rewards/efficiency; local-test shares never enter
  any mining, efficiency, or earnings figure. Hashrate stays
  `not-measured` / null until Gate 1 is measured.
- **Monitoring uptime:** `MAX(ts) - MIN(ts)` over `metrics` (the
  monitoring span), shown as `Xd Yh Zm`. Daemon restarts: `COUNT` over
  `events` where `kind='startup'` in the last 24 h (and all-time count
  beside it). Daemon uptime is ALWAYS null in this mission with the
  verbatim reason `Daemon start time is not recorded`.
- **Mining:** the earnings figures are the `dashboard` block's values
  by import (D-M8-2). Confirmed = ledger `SUM` over `user_allocation` +
  `referral_reward` entries (M6 §5.1 sign convention),
  SIMULATION-tagged while mode is `simulation-only`. Confirmed comes
  only from settled reward batches; open/held batches contribute to
  *pending* only. The estimate is ALWAYS null in this mission, with the
  verbatim reason. The estimate is never added to a confirmed figure or
  a balance.
- **Infrastructure:** CPU/memory/disk/load/net from the latest mirrored
  `metrics` row (highest `ts`) — the mirror of the host's latest
  metrics row — shown WITH the row timestamp. DB health from the admin
  export's recorded values (integrity, version, table counts). Queue
  lengths ALWAYS null with the verbatim reason. Connectivity from the
  latest mirrored `pool_stats` row + the diagnostics export's endpoint
  outcomes. Service status from the snapshot freshness + coordinator
  last pass + watchdog last line (all carried through the admin export
  / mirrored rows; none guessed).
- **Security:** counts per design §4 definitions, computed over the
  mirrored rows for the mirror side and read from the host-computed
  counts in `data/admin.json` for the host side (§2.4 secondary check).
  Each security row shown inline carries its evidence, never just a
  count.
- **Operational logs:** rows read from the §3.1 mirror tables
  (`mining_admin_decisions` / `mining_admin_events`), latest 20 of each
  shown, with the verbatim window note carrying the host totals
  (`decisions_total` / `events_total` from `data/admin.json`; when the
  export has not landed, the totals are UNAVAILABLE and the note reads
  `Showing latest 20 of 50 mirrored rows — host total not yet exported`).
  Redaction (§1.3) is applied artifact-side before display.
- **Scope (D-M8-13):** the section renders the host-global view with
  the verbatim scope line (§1.2). Do NOT invent a login, an admin
  picker, or demo admin rows.
- **Secrets:** no token, session token, password hash, seed phrase,
  private key, wallet address, or credential is ever mirrored or
  displayed. Entry hashes from the reward ledger are mirrored audit
  data (M6) but the admin section does not display them.

### 2.3 Expected live values of the block (today — the acceptance baseline)

All-zero / null honest state (to be confirmed by the coordinator against
the live mirror at edit time — §0 gap 1): `networkUsers: 0`,
`networkWorkers` all 0, `workerRows: []`; `hashrateStatus:
"not-measured"`, `totalHashrateHps: null`; shares 0/0/0/0;
`monitoringUptimeSeconds` = the live metrics span (≈ 64,652 s at spec
time); `daemonRestartsAllTime: 100` at spec time (24 h count =
host-computed at export time); `daemonUptime: null` +
`Daemon start time is not recorded`; mining: `xmrMinedPiconero: 0`,
`estimatedPiconero: null`,
`estimatedReason: "Cannot estimate — hashrate not measured"`,
`confirmedPiconero: 0`, `pendingPiconero: 0`,
`userAllocationsPiconero: 0`, `atlasRevenuePiconero: 0`,
`poolFeesPiconero: 0`, `payoutVolumePiconero: 0`, `payoutsCount: 0`,
`failedPayoutsCount: 0`, `failedPayoutRows: []`; infra:
`cpuPct: 53.88`, `memUsedPct: 79.44` (+ `Above the 70% cap`),
`diskUsedPct: 18.95`, `load1/load5/load15: 3.46/2.74/1.73`,
`netRxBytes: 59379`, `netTxBytes: 66116` (all at spec time, with the
metrics row timestamp); `dbHealth.integrityCheck: "ok"`,
`schemaVersion: 3`, table counts per §0; `queueLengths: null` +
verbatim reason; connectivity: MoneroOcean 259,064,041 H/s, 4,916
miners, block height 3,809,325, recorded_at 1795040469; security all 0
with `No events recorded`; logs: latest 20 decisions / 20 events with
window note `Showing latest 20 of 50 mirrored rows — 293 total on host`
(decisions) / `… — 100 total on host` (events); `mode:
"simulation-only"`, `emergencyStop: true`; `hostVerifiedTotals` all 0;
`mirrorDerivedTotals` all 0; `mismatch: false`;
`coordinatorSyncedAt` / `rewardsSyncedAt` / `adminSyncedAt` = the live
mirror values at read time (`adminSyncedAt` null → `Not synced yet` +
STALE until the first admin ingest lands); `stale` per §4.

### 2.4 MISMATCH MECHANISM (binding, D-M8-7 — design §7, M7 §6 carried and extended)

`getMining` computes, server-side, in the `admin` block:

- **`mirrorDerivedTotals`** (from mirrored rows only) — the same six
  comparisons as M7 §6, recomputed here for the admin view:
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
- **`hostVerifiedTotals`** (from the M7 singleton row
  `mining_dashboard_host_totals`, §3.2 of the M7 spec):
  - `ledgerEntries`, `batchesSettled`, `batchesOpen`, `batchesHeld`,
    `totalUserRewardsPiconero` (= host `total_user_rewards_piconero` +
    `total_referral_rewards_piconero`, per M7 §6 — the host splits
    user and referral rewards; the mirror sums them together, so the
    comparison adds them on the host side),
    `totalReferralRewardsPiconero`, `totalAtlasSharePiconero`,
    `totalPoolFeesPiconero`, `totalPayoutsPiconero`,
    `totalReversalsPiconero`. If the singleton row does not exist yet
    (never ingested), `hostVerifiedTotals` is `null` and `mismatch` is
    `false` with `mismatchDetails: ["host totals not yet synced"]` — the
    admin section shows the mirror-derived figures labelled as such and
    the Panel 6 `Not synced yet` state; it never invents host totals.
- **`mismatch`** (boolean) + **`mismatchDetails`** (array of the
  disagreeing quantity names, e.g. `["ledgerEntries",
  "totalUserRewardsPiconero"]`): true when ANY of the six design §6
  comparisons disagrees. Agreement on today's all-zero state (0 = 0)
  is a valid trivial agreement and says nothing about the check
  working — the §4 sandbox tests must prove the check with non-zero
  fixture data.
- **Secondary check (log window):** compare the mirrored log window
  against the host's latest-50 window carried in `data/admin.json`
  (`decisions_total`, `events_total`, and the id lists of the latest
  50). A disagreement shows the host counts plus the same verbatim
  mismatch note, and adds `"logWindow"` to `mismatchDetails`. The
  ledger comparison above is the primary check and MUST exist even if
  the log check is deferred; the log check must not be substituted for
  it. While `data/admin.json` has not landed (§0 gap 2), the log-window
  check is skipped, not faked — and the skip is recorded in the build
  report.
- **Secondary check (security counts):** the security counts derived
  from mirrored rows are compared against the host-computed counts in
  `data/admin.json`. A disagreement shows the host counts plus the same
  verbatim note, and adds `"securityCounts"` to `mismatchDetails`.
  While `data/admin.json` has not landed, this check is skipped, not
  faked.
- **Secondary check (duration):** compare the host-export duration
  (`worker_sessions_duration_seconds`, present in
  `data/coordinator.json` at spec time with value 0 — see §0 gap 4)
  against the artifact's own `SUM` over mirrored `mining_sessions`. A
  disagreement shows the host-export value plus the same verbatim
  mismatch note, and adds `"duration"` to `mismatchDetails`. The ledger
  comparison above is the primary check and MUST exist even if the
  duration check is deferred; the duration check must not be
  substituted for it. **CARRIED, NOT CLAIMED:** the M7 finding-6
  wiring (the population path from the coordinator mirror payload into
  this comparison) is still unverified — this spec wires the check and
  requires the §4 sandbox proof for it, but does NOT claim it works.
  If the coordinator finds the population path absent at edit time, the
  check is skipped and the omission is recorded in the build report.
- **On mismatch, the component MUST:** show the HOST-VERIFIED totals
  (not the mirror-derived ones) in every earnings/balance/lifetime
  figure; show the verbatim note
  `Mirror mismatch — figures under investigation` in the section header
  area next to the affected figures; keep listing mirror rows in
  ledger-derived panels but labelled as mirror rows under
  investigation — never silently present them as real earnings; show no
  mirror-derived figure as a confirmed earning or a balance. The
  mismatch is logged artifact-side in the honest-failure pattern
  (surfaced, not swallowed). On agreement, show the (equal) totals with
  no mismatch note.
- **The admin section must NOT display sandbox-only rows at all** — it
  reads only the durable live mirror, never a sandbox/test database.

---

## 3. Migrations — additive migration 0008 + `ingestAdminState`

### 3.1 Why two new tables are needed — flagged deviation from design D-M8-1

Design D-M8-1 states "No new artifact mirror tables EXCEPT the two log
tables in §1.1 (flagged deviation, ordered by the task — operational logs
cannot live in a singleton row)". The parent task orders this deviation
explicitly: the mission requires "complete operational logs" and log rows
cannot live in a singleton totals row (the M7 migration-0007 pattern only
fits scalars). The build therefore adds, by additive migration (next
journal index after 0007 — migration **0008**, journal idx 7), the two
tables below. It is additive only (new tables; no existing table, column,
row, or index is altered), it stores no new truth (it is a windowed
mirror of host rows, recomputed on every ingest), and it is the smallest
change that makes the operational-logs panels computable. The host side
of D-M8-1 is untouched (no new host tables). This deviation is recorded
here explicitly so Lane E can verify it as ordered, not as drift.

### 3.2 Migration 0008 — `drizzle/0008_admin_log_mirror.sql`

**Chosen shape: two new mirror tables, host id as PK, capped at the
latest 50 rows each.** The ingest deletes mirrored rows older than the
window (see §3.3).

**Exact tables and columns:**

`mining_admin_decisions` — mirror of host `decisions` rows:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | Host decision id (host id as PK; dedupe on host id) |
| `ts` | INTEGER NOT NULL | Host row timestamp (epoch seconds) |
| `dept` | TEXT NOT NULL | Host `dept` |
| `decision` | TEXT NOT NULL | Host `decision` |
| `reason` | TEXT | Host `reason` (nullable; redaction applied at display, §1.3) |
| `synced_at` | INTEGER | Artifact ingest time of the last CHANGED write for this row |

`mining_admin_events` — mirror of host `events` rows:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | Host event id (host id as PK; dedupe on host id) |
| `ts` | INTEGER NOT NULL | Host row timestamp (epoch seconds) |
| `kind` | TEXT NOT NULL | Host `kind` |
| `message` | TEXT | Host `message` (nullable; redaction applied at display, §1.3) |
| `synced_at` | INTEGER | Artifact ingest time of the last CHANGED write for this row |

No token, session token, password hash, seed, private key, or wallet
field in either table — the host module selects `id, ts, dept, decision,
reason` / `id, ts, kind, message` only. A `SELECT *` over `decisions` /
`events` that pulls a credential column, if one ever existed, is a
defect. No other columns.

**Schema file:** add both tables to `server/src/schema.ts` (drizzle
definitions mirroring the SQL exactly) and add the journal entry for
0008 in `drizzle/meta/_journal.json` (idx 7, following 0007's idx 6) —
same pattern as M6 migration 0006 / M7 migration 0007.

**Window cap (binding):** each table holds at most the latest 50 rows
(by host id / ts). The ingest deletes mirrored rows older than the
window — i.e. after upserting the incoming latest-50 window, delete
every mirrored row whose host id is not in the incoming window (or,
equivalently, keep only the 50 highest host ids). The section displays
the latest 20 of each. The host DB remains the complete log; the mirror
is a window, never presented as complete.

### 3.3 `ingestAdminState` (extend the existing ingest pattern — no new refresh step)

Extend the ingest pattern of `ingestRewardsState` (M6) / the M7 totals
upsert with a new action `ingestAdminState` in `server/src/actions.ts`,
riding the existing refresh step (same step family as the rewards
mirror — no new refresh step, no new cron, no new schedule):

- The ingest payload is the host `data/admin.json` export (when it
  exists). The action upserts the latest-50 decision rows into
  `mining_admin_decisions` and the latest-50 event rows into
  `mining_admin_events`, deduped on host id, in the same transaction
  discipline as `ingestRewardsState` (rows + window trim land together,
  never from different exports).
- **Missing export:** if `data/admin.json` does not exist yet (§0 gap
  2 — the state at spec time), the action MUST skip cleanly: it
  reports `adminExportMissing: true`, leaves both tables untouched,
  and does NOT advance any `syncedAt`. The admin block then reports
  `adminSyncedAt: null` → `Not synced yet` + STALE (§4). Never
  fabricate log rows.
- **Upsert semantics:** if the incoming window is identical to the
  stored window AND no row changed, the ingest reports
  `upToDate: true` with 0 added and does NOT touch `syncedAt` (a
  re-ingest of unchanged data is never mislabelled as a fresh sync —
  M5 §1.4 / M6 §10 / M7 §3.3, carried). If rows differ, upsert the
  changed rows, delete rows older than the window, and set `synced_at`
  to now (per changed row; the block `adminSyncedAt` is the ingest
  time of the last CHANGED write).
- **Redaction is NOT the ingest's job alone:** the host module applies
  design §1.2 redaction before the export; the artifact applies it
  again before display (§1.3). Either layer alone must be sufficient.
- The action's existing behavior for the other mirrors is otherwise
  unchanged: ledger ingest stays insert-only, host-id dedupe stays
  enforced, re-ingest of unchanged rows still reports "already up to
  date".

### 3.4 What this does NOT do (hard limits)

- This does NOT delete, alter, expire, or relabel any existing mirror
  row, and does NOT decide the fate of the sandbox-only
  `sim-batch-test-1` rows.
- This does NOT touch `client/src/RewardAccounting.tsx` or
  `client/src/UserDashboard.tsx` in any way — not one line. The Mission
  6 finding-1 repair (replacing the hardcoded zero literals in
  `RewardAccounting.tsx` with values derived from the mirrored ledger
  totals) is NOT authorized and is NOT part of this build. The admin
  section's mismatch mechanism is PREVENTION (the defect class cannot
  recur silently in the new section); it is not a repair of the
  existing section.
- This does NOT change the Mission 6 rewards block, the Mission 7
  dashboard block, the coordinator block, or any existing panel's copy.
  The existing User dashboard section keeps rendering exactly as it
  does on build `61fac176`, until a repair is separately authorized.
- This does NOT add any host table, host column, or stored aggregate
  (design D-M8-1 host side untouched). The host export
  `data/admin.json` and module `core/atlas_admin.py` are Lane C's scope,
  not this lane's; this spec only consumes them.

---

## 4. Refresh — rides the existing flow (D-M8-6, D-M8-9)

- **No new cron. No new schedule.** The admin section rides the existing
  refresh flow: the 10-minute coordinator pass (which exports
  `coordinator.json` and runs the guarded rewards sub-step) plus the
  existing `refreshAtlasData` round-trip. The admin ingest (§3.3) rides
  the existing refresh step family (same step as the rewards mirror) —
  no new refresh step is added. The admin export rides the existing
  coordinator pass as a guarded sub-step (never fails the pass, logs no
  decision of its own) — same pattern as M6/M7 (D-M8-9). If the refresh
  fails, the admin section goes STALE (§4.1) — it does not retry,
  re-fetch, or invent a sync. The refresh failure (M3 finding 1) is NOT
  repaired here.
- **STALE rule (D-M8-6, binding):** the admin section is STALE when the
  coordinator mirror OR the rewards mirror OR the diagnostics export is
  > 1 h old, measured from that block's `syncedAt` / `exported_at` to
  now (3600 s). Any one stale → the whole admin section carries the
  STALE tag (a stale third is not a fresh admin view). The STALE tag
  names which source is stale (e.g. `STALE — diagnostics data 73 min
  old`). Stale data is shown honestly, labelled STALE — never hidden,
  never presented as current.
- **"Not synced yet":** when a block has never synced (`syncedAt`
  null), that block shows `Not synced yet` instead of a time — never
  `0`, never a guessed time. If any block has never synced, the section
  is STALE. Until the first admin ingest lands, `adminSyncedAt` is null
  and the admin section is STALE by this rule — which is the honest
  state at build time, not a failure.
- **Last-sync panel shows ALL THREE mirror sync timestamps**
  (coordinator block `syncedAt`, rewards block `syncedAt`, admin block
  `syncedAt` — the admin block's sync time is the ingest time of
  `data/admin.json`), each with its age
  (`synced <date time> (<age> ago)`), each with its own STALE / SYNCED
  tag. The three timestamps are never merged into one "last sync"
  figure.
- **Re-ingest honesty:** a re-ingest of unchanged data reports "already
  up to date" and does NOT refresh any `syncedAt`. The admin section's
  sync times are the mirror ingest times of *changed* data, not the time
  of the last refresh attempt.
- **Host `dashboard.json` `sync.stale` is NOT the admin STALE flag.**
  It measures host-export freshness (fresh at spec time, `stale:
  false`). The UI STALE flag is computed from the MIRROR `syncedAt`
  values in the `admin` block. Do not wire the host flag into the UI.
- **Diagnostics freshness:** the diagnostics source for the STALE rule
  is the diagnostics export's `ts` (see §0 gap 3) — or a
  `diagnostics_exported_at` carried in `data/admin.json` if Lane C
  provides one. If neither is present, diagnostics freshness is
  UNAVAILABLE (`Diagnostics export time not recorded`) and the section
  does NOT claim the diagnostics source is fresh.

---

## 5. Exact file change list, `verbatim_request`, and verification

### 5.1 File change list (create/edit, with paths)

Paths are relative to the artifact ts-space working tree (see §0). The
coordinator MUST resolve each path there and report any that does not
resolve.

| # | File | Change |
|---|---|---|
| 1 | `client/src/AdminCommandCenter.tsx` | CREATE — `AdminCommandCenterSection`, six panel groups per §1.3, zero buttons/inputs/links/forms |
| 2 | `client/src/Mining.tsx` | EDIT — import + `<AdminCommandCenterSection m={m} />` directly below `<UserDashboardSection m={m} />`, above Settings. Nothing else in this file changes. Do NOT touch the two stale "no miner yet" strings (repair NOT authorized). Do NOT touch the hook order (M6 crash fix stays as-is). |
| 3 | `server/src/schema.ts` | EDIT — add drizzle definitions for `mining_admin_decisions` + `mining_admin_events` (§3.2). Nothing else changes. |
| 4 | `drizzle/0008_admin_log_mirror.sql` | CREATE — additive migration 0008 (§3.2) |
| 5 | `drizzle/meta/_journal.json` | EDIT — journal entry idx 7 for 0008 (following 0007's idx 6) |
| 6 | `server/src/actions.ts` | EDIT — (a) add `ingestAdminState` (§3.3, rides the existing refresh step family — no new refresh step); (b) `getMining` gains the `admin` block (§2). No new action for the derived figures. No change to the existing `rewards`, `dashboard`, or `coordinator` blocks. |

**NOT changed:** `client/src/RewardAccounting.tsx` (finding-1 repair NOT
authorized), `client/src/UserDashboard.tsx` (no change), any host file
under `~/workspace/atlas/` (`core/`, `config/`, `data/` — Lane C's
scope, not this lane's), any cron or schedule, any other tab or section,
any safety setting.

Resulting Mining tab order (verify after edit): MiningDashboard,
WalletCenter, EarningsSection, HistorySections, PayoutSection,
CalculatorSection, MinerPrototypeSection, CoordinatorSection,
RewardAccounting, UserDashboard, **AdminCommandCenter**, SettingsSection,
HelpSection.

### 5.2 Exact `verbatim_request` text for the coordinator to pass to `artifact.edit`

The coordinator MUST pass the following text verbatim as the
`verbatim_request` to `artifact.edit` (artifact slug
`atlas-command-center`). Do not paraphrase it — it is the build contract:

> ATLAS Master Mission 8 — Admin command center section (simulation only, artifact `atlas-command-center`, current build 61fac176). Add ONE new section to the Mining tab, directly BELOW the existing "User dashboard — Master Mission 7" section and above Settings; do not move, restyle, or reword any existing section; no new tab. CREATE `client/src/AdminCommandCenter.tsx` exporting `AdminCommandCenterSection` (same `m` prop as `UserDashboardSection`, reading only the new `getMining` `admin` block plus the reused `dashboard` earnings block), and EDIT `client/src/Mining.tsx` to import it and render `<AdminCommandCenterSection m={m} />` directly below `<UserDashboardSection m={m} />` — that is the ONLY change to `Mining.tsx`: do not touch the "no miner yet" strings, do not touch hook order, do not touch Start/Stop (stay hard-disabled). The section has SIX panel groups in this exact order, with the exact headings, labels, and empty-state copy below. Section header "Admin command center — Master Mission 8" with scope line "Admin view — aggregates and operational data only. No login exists yet — this section is not access-controlled." (1) Network — panels "Network — users and workers" (rows Users, Workers total, Active, Browser, Desktop, Registered, Degraded, Suspended, Revoked, Pending; empty states "No users yet" / "No workers yet"; per-worker rows id, type, status, registered_at, last_seen_at only, never token fields; per-user data is a count only), "Network — hashrate and shares" (rows Total hashrate "not measured", Pool shares accepted, Pool shares rejected, Local-test shares accepted, Local-test shares rejected; empty state "No shares yet"), "Network — uptime" (rows Monitoring uptime "Xd Yh Zm", Daemon restarts (24h), Daemon restarts (all time), Daemon uptime "Daemon start time is not recorded"). (2) Mining (all figures SIMULATION-tagged; earnings block REUSED from the dashboard export, never recomputed — the admin section must never show a different earnings number than the user dashboard) — panels "Mining — XMR mined" (rows "XMR mined (confirmed, settled batches only)" XMR to 6 decimals, "Estimated earnings" = "Cannot estimate — hashrate not measured"), "Mining — rewards" (rows Confirmed rewards, Pending rewards (open/held batches), User allocations, ATLAS revenue, Pool fees; pending 0 empty state "No open or held batches"; all 0 shown as "0.000000 XMR (SIMULATION)"), "Mining — payouts" (rows Payout volume, Payouts count, Failed payouts; empty state "No payouts yet"). (3) Infrastructure — panels "Infrastructure — host resources" (rows CPU, Memory used, Disk used, Load 1/5/15 min, Network rx/tx, all from the latest metrics row WITH its timestamp; memory above cap shows the number plus verbatim "Above the 70% cap"; row > 10 min old carries the STALE tag), "Infrastructure — database health" (rows Integrity check, Schema version, per-table row counts for users, workers, shares, sessions, ledger, reward_batches, payouts, pool_stats, decisions, events, metrics; integrity not ok shows verbatim "Database integrity check failed — figures under investigation" and no derived figure is presented as verified), "Infrastructure — queues" (row Queue lengths = verbatim "No queue system exists — the coordinator runs synchronously in the 10-minute pass"), "Infrastructure — connectivity" (rows Last pool poll with pool, time, hashrate, miners, block height; MoneroOcean, CoinGecko, blockchain.info, mempool.space last diagnostics outcomes; never polled = "Not polled yet"; config statuses labelled "recorded claim, not a live measurement"), "Infrastructure — services" (rows Daemon, Coordinator pass, Watchdog, each status text + last-seen age; daemon fresh < 3 min = "Running", else "Stale — last seen <age> ago"; no pid shown). (4) Security (definitions: suspicious workers = status suspended/revoked OR pool-origin rejected shares >= 10 with rejection ratio > 0.5; invalid shares = pool-origin accepted=0; duplicate shares = same non-null external_id or same worker_id + job_id with count > 1, counting rows beyond the first; account abuse = events kind abuse; auth failures = events kind auth_failure; payout anomalies = payouts status failed PLUS ledger entry_type reversal; NO threshold, flag, or degraded inference from any security count; the word "secure" never appears as a verdict) — panels "Security — workers and shares" (rows Suspicious workers, Invalid shares, Duplicate shares, each with inline evidence rows; each 0 empty state "No events recorded") and "Security — accounts and payouts" (rows Account abuse events with note "No abuse events recorded", Auth failures with note "No auth-failure events recorded", Payout anomalies with inline rows; each 0 empty state "No events recorded"). (5) Operational logs — panels "Operational logs — decisions" (latest 20: time, dept, decision, reason; dept counts above the list) and "Operational logs — events" (latest 20: time, kind, message; kind counts above the list); both carry the verbatim window note "Showing latest 20 of 50 mirrored rows — N total on host"; messages matching a credential pattern are replaced with verbatim "[redacted — possible credential]" and the row is still counted; a row needing private data is omitted with verbatim "Row omitted — private data". (6) Last sync — panel "Admin — last sync" (Coordinator, Rewards, and Admin syncedAt, each "synced <date time> (<age> ago)" with its own STALE/SYNCED tag, never merged; "Not synced yet" when never synced; STALE tag names which source is stale). All figures come from the getMining admin block only (plus the reused dashboard earnings block) — NO hardcoded figure literal anywhere in the component as a displayed value (grep-enforced); all amounts XMR to 6 decimals from integer piconero only; NO USD/fiat figure anywhere; zero <button>, <input>, <a>, or <form> in the section; drill-down is inline detail rows by default with NO expand/collapse control; tables collapse to stacked cards below ~640px; no horizontal overflow at 390px; status as text, never colour alone. SERVER: in `server/src/schema.ts` add drizzle tables `mining_admin_decisions` (id INTEGER PRIMARY KEY = host decision id, ts INTEGER NOT NULL, dept TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT, synced_at INTEGER) and `mining_admin_events` (id INTEGER PRIMARY KEY = host event id, ts INTEGER NOT NULL, kind TEXT NOT NULL, message TEXT, synced_at INTEGER); CREATE additive migration `drizzle/0008_admin_log_mirror.sql` creating both tables and add its journal entry (idx 7) in `drizzle/meta/_journal.json`; in `server/src/actions.ts` add `ingestAdminState` riding the existing refresh step family (upsert the latest-50 decision/event windows from data/admin.json, deduped on host id, in one transaction; after upsert delete mirrored rows older than the window; identical window + no row changes → report upToDate with 0 added and do NOT touch syncedAt; missing data/admin.json → skip cleanly, report adminExportMissing:true, leave tables untouched, never fabricate rows); extend `getMining` with an `admin` block computed server-side from the mirrored tables only — network counts + worker rows, hashrate status/nulls, pool/local-test share counts, monitoring uptime seconds, daemon restarts 24h/all-time, daemonUptime null with reason "Daemon start time is not recorded", mining figures reused from the dashboard earnings block (estimatedPiconero null with reason "Cannot estimate — hashrate not measured"), infrastructure figures from the latest mirrored metrics row with its timestamp, DB health, queueLengths null with reason "No queue system exists — the coordinator runs synchronously in the 10-minute pass", connectivity, services, security counts with inline rows, logs latest 20 of each with host totals, coordinatorSyncedAt, rewardsSyncedAt, adminSyncedAt, diagnosticsSyncedAt, stale flag (>3600s on the coordinator, rewards, or diagnostics source → STALE naming the stale source; null syncedAt → "Not synced yet" + STALE), mirrorDerivedTotals (COUNT/SUM over mining_ledger and mining_reward_batches per entry type), hostVerifiedTotals (from the mining_dashboard_host_totals singleton row; host totalUserRewards = total_user_rewards_piconero + total_referral_rewards_piconero), mismatch boolean + mismatchDetails list (true on ANY disagreement across ledgerEntries, totalUserRewards, totalAtlasShare, totalPoolFees, totalPayouts, batchesSettled; plus log-window, security-counts, and duration secondary checks when the host data for them is present — skipped, not faked, when absent); on mismatch the component shows HOST-VERIFIED totals plus the verbatim note "Mirror mismatch — figures under investigation" and never presents a mirror-derived figure as a confirmed earning or balance. NO new cron, NO new refresh step; do NOT touch `client/src/RewardAccounting.tsx` or `client/src/UserDashboard.tsx` in any way; do NOT delete, alter, or relabel any sim-batch-test-1 rows; do NOT mirror or display any token, session token, password hash, seed, private key, or wallet address. Run the full pipeline (migration, typecheck, bundle, publish) and report the new build id.

### 5.3 Typecheck + sandbox verification steps (build lane, before handoff to Lane E)

Same method as M6 Lane D (§3) and M7 Lane D (§5.3), extended for the
admin block:

1. **Typecheck:** `bun run typecheck` (client + server) — PASS, exit 0,
   zero errors. Any error found is fixed in this build's files only.
2. **Migration 0008 validation:** apply 0008 against an in-memory
   SQLite DB shaped like the pre-0008 schema (post-0007); insert 60
   fixture decision rows + 60 fixture event rows; run the window-trim
   logic and verify exactly the latest 50 of each remain (older rows
   deleted); verify duplicate host-id insert is rejected by the PK;
   verify the journal entry (idx 7) is well-formed.
3. **Grep checks on `AdminCommandCenter.tsx`:** zero `<button>`,
   `<input>`, `<a>`, `<form>`; zero hardcoded displayed-figure
   literals — grep for `0 XMR`, `0.000000 XMR`, and bare numeric XMR
   literals outside the verbatim copy strings listed in §1.3 (any hit
   outside those strings is a defect and must be removed); verbatim
   strings from §1.3 confirmed present; no `password_hash`,
   `token_hash`, `token_salt`, `session_token`, `seed`,
   `private_key`, or wallet-address pattern anywhere in the
   new/changed files; no `SELECT *` over `workers` / `decisions` /
   `events` in the ingest path.
4. **Changed-file sweep:** only the six files in §5.1 changed. Any
   other diff is out of scope and must be reverted or explicitly
   reported.
5. **Sandbox `getMining` (all-zero baseline):** on the sandbox action
   layer, `getMining` returns the `admin` block with the §2.3 expected
   values — all-zero totals, `estimatedPiconero` null + verbatim
   reason, `queueLengths` null + verbatim reason, `daemonUptime` null
   + verbatim reason, `mismatch: false`, `hostVerifiedTotals` all 0,
   `mirrorDerivedTotals` all 0, log windows holding the latest rows
   with the verbatim window note, and the `stale` flag correct for the
   sandbox mirror's `syncedAt` values (STALE when any of the three
   sources is > 1 h old; `Not synced yet` when a `syncedAt` is null —
   including `adminSyncedAt` null before the first admin ingest).
6. **Sandbox ingest with a non-zero admin fixture:** `ingestAdminState`
   with a fixture `data/admin.json` (decisions incl. one suspended
   worker + one high-rejection worker, pool shares incl. a duplicate
   `external_id` group, one failed payout + one reversal, one decision
   message containing a fake token string, one stale metrics row)
   asserts: every security count matches the design §4 definitions;
   the fake-token message is replaced with
   `[redacted — possible credential]` and the row is still counted;
   the queue UNAVAILABLE reason and the uptime UNAVAILABLE reason are
   the verbatim strings; the earnings block is identical to the
   dashboard export's earnings block; the window cap holds at 50 rows
   per table. (Sandbox only — durable storage keeps 0 workers / 0
   shares / 0 ledger entries; no fictional earnings ship.)
7. **Sandbox mismatch proofs (ledger + log-window, non-zero fixtures):**
   (a) ledger mismatch — mirror totals disagreeing with host totals
   returns `mismatch: true` with the disagreeing fields named in
   `mismatchDetails` and confirmed figures switched to host-verified;
   (b) log-window mismatch — mirrored log ids disagreeing with the
   host's latest-50 window returns the same verbatim note with host
   counts shown; (c) a second sub-case with agreeing non-zero fixture
   totals returns `mismatch: false`. Agreement on zeros alone is NOT
   accepted as proof of the check.
8. **Sandbox duration secondary check:** with the host duration field
   present (`worker_sessions_duration_seconds` from the coordinator
   mirror payload), a fixture disagreement between the host duration
   and the mirror's `SUM` over `mining_sessions` adds `"duration"` to
   `mismatchDetails` and shows the host-export value plus the verbatim
   mismatch note; agreement returns no duration entry. If the
   population path is absent at edit time, record the skip in the
   build report (M7 finding 6 carried — do NOT claim the check works
   without this proof).
9. **Re-ingest reports upToDate:** an identical re-ingest returns
   `upToDate: true` with 0 added, and NO `syncedAt` (admin block nor
   log-row `synced_at`) advances.
10. **No console errors; mobile 390 px overflow 0** — source-level
    where the build lane cannot render; the rendered proof is Lane E's
    job (§6). The build lane MUST NOT claim a render it did not perform.
    **Stated plainly:** a phone-width Mining-tab capture could not be
    obtained in M7 (the probe viewport switch timed out on the heavy
    WebGL page) — this spec does not claim a capture it does not have,
    and the 390 px check remains a Lane E rendered acceptance item.

---

## 6. Verification checklist — Lane E (acceptance; execute after deployment)

Lane E executes this against the NEW build id (reported by the build
lane). Every item is PASS / FAIL with evidence (capture id or log
excerpt). No item may be marked PASS from source inspection alone where
a render is required.

### 6.1 Rendered checks (fresh interactive audit — desktop 1440 px + mobile 390 px)

- [ ] **E1. Mining tab selects cleanly on desktop (1440 px)** with zero
  console errors; the Admin command center section renders directly
  BELOW the User dashboard section and above Settings; tab/section
  order otherwise unchanged (MiningDashboard, WalletCenter,
  EarningsSection, HistorySections, PayoutSection, CalculatorSection,
  MinerPrototypeSection, CoordinatorSection, RewardAccounting,
  UserDashboard, AdminCommandCenter, SettingsSection, HelpSection).
- [ ] **E2. Desktop-viewport screenshot of the admin section**
  (1440 px). **ACCEPTANCE CHECK.** Screenshot must show all six panel
  groups in §1.3 order.
- [ ] **E3. Mobile render (390 px):** Mining tab selects cleanly, all
  six panel groups present in §1.3 order, zero console errors, mobile
  overflow 0 px at 390 px, cards stacked (no horizontal scroll).
  **NOTE:** the M7 phone-width capture gap (probe viewport switch timed
  out on the heavy WebGL page) is carried here — E3 is the item that
  closes it for this section, and it must be attempted and its outcome
  reported honestly, not assumed.
- [ ] **E4. All zeros honest:** SIMULATION tags visible; verbatim
  estimate reason `Cannot estimate — hashrate not measured`, verbatim
  queue reason
  `No queue system exists — the coordinator runs synchronously in the 10-minute pass`,
  verbatim daemon-uptime reason `Daemon start time is not recorded`,
  verbatim scope line
  `Admin view — aggregates and operational data only. No login exists yet — this section is not access-controlled.`,
  verbatim empty states `No users yet`, `No workers yet`,
  `No shares yet`, `No payouts yet`, `No events recorded`,
  `No open or held batches` all visible; memory figure carries
  `Above the 70% cap` where applicable; no figure presented as live
  earnings; no USD/fiat figure anywhere in the section; no wallet
  address, token hash, or credential anywhere in the section.
- [ ] **E5. Zero controls:** no button, input, link, or form anywhere
  in the section (DOM check, not just source grep); Start/Stop visibly
  disabled; no user picker, no login, no demo admin rows.
- [ ] **E6. STALE rendering check:** with any of the three sources
  > 1 h old (the expected state at build time is `adminSyncedAt`
  null until the first admin ingest lands), the section renders STALE
  naming the stale source, with figures still shown (labelled STALE),
  not hidden and not presented as fresh. All three mirror sync
  timestamps visible, each with its own STALE / SYNCED tag.
- [ ] **E7. Reload-persistence check — desktop + mobile.
  ACCEPTANCE CHECK.** Reload the page, re-select Mining, confirm the
  section re-renders with the same figures on BOTH viewports. Record
  the reload explicitly (step log, not just a summary count).
- [ ] **E8. Other tabs / orb / refresh / emergency stop still render**
  (Overview desktop: orb, tabs, refresh state, emergency stop ON);
  no regression in the User dashboard section's rendering (its content
  is unchanged; the M6 finding-1 contradiction in Reward accounting is
  carried, NOT fixed — do not report it as a new failure, and do not
  report it as fixed).

### 6.2 Action-layer re-verification (independent, sandbox + live read-only)

- [ ] **E9.** Live `getMining` (read-only) returns the `admin` block
  with the §2.3 all-zero baseline; `mismatch: false`;
  `hostVerifiedTotals` all 0; `mirrorDerivedTotals` all 0; live mirror
  still batches `[]` / entries `[]` (no fictional earnings shipped;
  durable storage unchanged); log windows hold the latest host rows.
- [ ] **E10.** Sandbox re-run of §5.3 steps 6–8 (non-zero admin fixture
  → security counts + redaction + verbatim UNAVAILABLE reasons +
  earnings block identical to the dashboard export; ledger mismatch →
  `mismatch: true` + host-verified totals shown; log-window mismatch →
  same verbatim note + host counts; agreeing non-zero fixtures →
  `mismatch: false`; identical re-ingest → `upToDate: true`,
  `syncedAt` unmoved).
- [ ] **E11.** No token / session token / password hash / seed /
  private key / wallet address in the `admin` block, in
  `data/admin.json`, or in either new mirror table (same assertion
  shape as the M5 mirror test). A message containing a fake token
  string is `[redacted — possible credential]` in the mirror.
- [ ] **E12.** Migration 0008 applied on the deployed build; journal
  idx 7 present; both tables capped at the latest 50 rows (older rows
  deleted by ingest); `adminSyncedAt` null + `Not synced yet` is
  acceptable before the first admin ingest lands, if reported
  honestly — never a fabricated zero or a fabricated sync time.
- [ ] **E13.** Diagnostics still green (existing 24 must stay green;
  the new admin diagnostic — test 25 per design §9 — is reported with
  its number and result; suite must be 25/25).

### 6.3 Explicitly NOT acceptance criteria for this build

- The Mission 6 finding-1 self-contradiction in `RewardAccounting.tsx`
  is NOT fixed by this build and is NOT a failure of this build. Lane E
  records its carried state; it does not fail E1–E13 over it.
- The M7 duration secondary check wiring (M7 finding 6) is NOT claimed
  working by this spec; E10's duration sub-proof is the acceptance
  evidence for it, and a recorded skip (population path absent) is an
  acceptable honest outcome, not a failure of the admin section.
- Gate 1 (measured hashrate), the refresh failure, the stale "no miner
  yet" copy, host memory above the 70% cap, and the mempool.space
  dispute are carried, not fixed, not failed here.

---

## 7. Known issues carried (NOT fixed by this spec — D-M8-12)

1. **Rendered Mining-tab check NOT established** (M7 finding 1, still
   owed — now the fifth consecutive mission with this gap). No captured
   render ever selects the Mining tab on build `61fac176`. A
   repair-authorized Mining-tab render capture (select Mining, capture
   desktop + mobile, console, overflow, then reload + re-select Mining)
   is owed.
2. **Gate 1 still unmeasured** — every hashrate reads "not measured". A
   fresh interactive probe run is owed.
3. **Refresh failure carried** (Mission 3 finding 1, NOT fixed). The
   admin labels stale mirrors rather than presenting them as fresh, but
   a failed refresh still stalls the mirror.
4. **Stale "no miner yet" copy carried** (Mission 4 finding 4, NOT fixed)
   — exactly two strings in `Mining.tsx`. Repair needs a
   repair-authorized inspection.
5. **Mission 6 finding 1 is latent, not repaired.** The hardcoded zero
   literals in `RewardAccounting.tsx` are still there. The admin's
   mismatch rule detects the shape but the underlying display defect is
   NOT fixed — repair still needs a repair-authorized inspection. It
   does not bite today: the live mirror and live host totals are both 0.
6. **Duration secondary check wiring not independently verified** (M7
   finding 6). Dormant at 0 sessions; the host field
   `worker_sessions_duration_seconds` is now present in
   `data/coordinator.json` (value 0), but the population path into the
   comparison is unverified. Verify per §5.3 step 8 before any session
   exists. **This spec does NOT claim it works.**
7. **Panel 1 "0 users" wording tension (minor, source-level, M7 finding
   7):** the dashboard counts distinct user_ids on mirrored ledger
   entries (0), while `mining_users` holds 1 scaffold row
   (`local-user`, no wallet). The admin network panel counts `users`
   from the coordinator export (0) and must use the same verbatim
   `No users yet` copy — a wording decision is owed, not a repair.
8. **"Derived host" tag wording (minor, M7 finding 8):** when mismatch
   is false the confirmed-figure tag reads "Derived host"; it may
   confuse. Same standing as finding 7.
9. **SupportXMR fallback not implemented** (D-M5-3, carried) — no
   verified stats-API URL; a URL must never be guessed.
10. **Referral rate 5% is a design parameter to confirm** before any
    real-mode settlement (engine defaults to 500 bps;
    `referral_rate_bps` absent from `pool-rewards.json`).
11. **Minimum payout still null/placeholder** — undecided, needed before
    any payout flow.
12. **D-M5-1 (carried):** browser-probe `session_token_hash` stores
    marker `none:browser-probe` instead of NULL. Confirmed in code; no
    live row to inspect (sessions 0).
13. **Host memory 79.44% (was 78–93%) above the 70% cap** (standing,
    pre-existing; 79.44% at spec time). Re-scope proposal still needs
    user approval.
14. **mempool.space disputed, not settled.** 000 (timeout) on some
    attempts, 200 on others. Flappy.
15. **Daemon restarts of undetermined cause** (carried). Watchdog
    restarts continue. Single instance maintained; not a stop condition.
16. **DB file growth, partly unexplained (carried).** The pre-Mission 2
    jump (36,864 → 163,840 B) remains unexplained at page level.
17. **Diagnostics sensitivity:** the suite is sensitive to endpoint
    flapping; a 22/24 with only tests 14/18 failing is the known stall
    signature, not a regression. Test count grows 24 → 25 in this
    mission (new test 25, design §10).

## 8. Handoff checklist (what the build lane receives)

- [ ] §0: binding inputs + ground truth (host exports read at spec time;
  live-mirror state and `data/admin.json` flagged as gaps, to be
  verified by the coordinator at edit time).
- [ ] §1: component spec — file, placement, six panel groups with
  verbatim copy.
- [ ] §2: `admin` block — field names (design-defined), derivation
  rules, expected live all-zero values, mismatch mechanism (primary +
  log-window + security-counts + duration secondary checks).
- [ ] §3: migration 0008 (two log mirror tables, latest-50 window cap),
  `ingestAdminState`, non-repair statement for finding 1,
  `RewardAccounting.tsx`, and `UserDashboard.tsx`.
- [ ] §4: refresh — rides existing flow, STALE / "Not synced yet" rules
  over three sources.
- [ ] §5: exact file change list (6 files), verbatim `verbatim_request`
  text, typecheck + sandbox verification steps.
- [ ] §6: Lane E acceptance checklist (desktop 1440 px + mobile 390 px +
  reload persistence as acceptance checks).
- [ ] §7: known issues carried (17 items, none fixed here).

**Stop — specification complete. No artifact was edited by this lane. The
coordinator executes the artifact edit from §5.2 and hands the new build
id to Lane E for §6.**
