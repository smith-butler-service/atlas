# ATLAS — Master Mission 8: Admin Command Center — Design

**Mission:** Master Mission 8 — Admin command center
**Date:** Wednesday, 2026-11-18
**Author:** Lane A (design — coordinator)
**Status:** DESIGN ONLY. No code, no migration, no config change, no database write,
no artifact change was made by this lane. This document is the binding contract for
the build lane.
**Scope:** The private admin dashboard IN SIMULATION, built on the coordinator
(Mission 5), reward engine (Mission 6), user dashboard (Mission 7), and
diagnostics outputs. There are no real earnings, no workers, no shares, no
sessions: 0 users, 0 workers, 0 shares, 0 ledger rows. Every figure the admin
section shows is derived from host exports or is an honest null/zero, clearly
marked as such. The admin sees aggregates and operational data — NEVER private
credentials, keys, wallet secrets, token hashes, or per-user identifying data.

## 0. Grounding — what this design rests on

Read before writing this design (all under `~/workspace/atlas/`):

- Mission 1 inspection report (`docs/master-mission1-inspection-report-2026-11-18.md`)
  §8, Mission 8 row: "Private admin dashboard (network, mining, infrastructure,
  security per the master mission §16) + drill-down and operational logs" —
  aggregated data from the coordinator, ledger, and diagnostics; must NOT touch
  user private account data (admin sees aggregates and operational data, not
  private credentials). Also §6 (accounting basis: confirmed pool rewards only,
  integer piconero, attribution by verified accepted shares) and §4.5 (the five
  prototype gates; Gate 1 measured hashrate UNMEASURED).
- Master mission §16 (admin command center), as recorded in `docs/roadmap.md`
  line 100: "The Command Center is a single-user monitoring dashboard, not an
  admin console. Private admin dashboard: network (users, active/browser/desktop
  workers, total hashrate, shares, uptime), mining (XMR mined, confirmed/pending
  rewards, user allocations, ATLAS revenue, payout volume, failed payouts),
  infrastructure (CPU/memory/disk, DB health, queue lengths, API/pool
  connectivity, service status), security (suspicious workers, invalid/duplicate
  shares, account abuse, auth failures, payout anomalies). Drill-down details
  and complete operational logs."
- Mission 7 design (`docs/master-mission7-design.md`) — design conventions carried
  here: host DB is system of record, artifact is a read-only display mirror
  (D-M7-1); integer piconero, never floats (D-M7-2/3 pattern); balances derived
  by `SUM`, never stored; simulation marking everywhere (M6 §8); no new cron,
  ride the existing pass; placement directly below the previous section, no new
  tab; estimated vs confirmed hard rule (§3); STALE rules (§5); MIRROR-MISMATCH
  rule (§6); zero buttons/inputs/links/forms in the section; verbatim
  headings/labels/empty-state copy; provenance tags (RECORDED / DERIVED host /
  DERIVED mirror / ESTIMATE / UNAVAILABLE).
- Mission 5 design (`docs/master-mission5-design.md`) §7 — panel conventions:
  tables collapse to stacked cards below ~640 px; mobile overflow 0 at 390 px;
  status as text, never colour alone.
- Mission 7 report (`docs/master-mission7-report-2026-11-18.md`), Unresolved
  findings 1–17 — carried, NOT fixed by this design (see §9). Finding 1 (the
  rendered Mining-tab check never established) and finding 5 (Mission 6 finding 1
  latent — hardcoded zero literals in `RewardAccounting.tsx`) are the two this
  design is built to not repeat: the admin section must be designed so that class
  of defect cannot recur silently (§7).

**Safety state (unchanged):** emergency_stop true, mining disabled, trading
paper-only, eligible capital $0. No wallets, keys, or seed material. No real
payouts, no pool connection for earning, no share submission to any pool, no
mining activation, no spending. Gate 4 (a real payout) is a hard gate requiring
explicit authorization + successful security testing + a treasury design — none
exists.

**Baseline facts (verified by the coordinator just before this design was written,
read-only):**

- Live host DB (`data/atlas.db`): `user_version` 3, `integrity_check` ok; users 0,
  workers 0, shares 0, sessions 0, ledger 0, reward_batches 0, payouts 0,
  referrals 0; pool_stats 42, decisions 291, events 100, metrics 1100.
- Live host exports: `data/coordinator.json` (exported_at 1795039855): hashrate
  `not-measured`, `measured_hps` null, shares all 0, workers all 0, pool
  MoneroOcean 267,750,486 H/s, 4,908 miners, height 3,809,325.
  `data/rewards.json` (exported_at 1795039856): all totals 0, `ledger_entries` 0,
  `batches` [], `ledger` [], chain "ledger empty — chain trivially valid, 0 entries".
  `data/dashboard.json` (exported_at 1795039856): hashrate not-measured, shares
  0/0/0/0, duration 0 s, workers 0, earnings estimated null + verbatim reason,
  confirmed 0 SIMULATION ONLY, balances `{}`, lifetime all 0, payouts 0 rows,
  efficiency null + verbatim reason, sync stale false, host_verified_totals all 0.
- Live snapshot (`data/snapshot.json`, ts 1795040326): CPU 51.1%, memory **93.08%
  used** (above the 70% cap — standing issue), disk 18.95% used, net rx 17,323 B
  / tx 4,246 B, gpu null, mining `disabled`, trading `disabled-paper-only`,
  emergency_stop true. **No daemon start time is recorded anywhere** — daemon
  uptime is therefore UNAVAILABLE by rule (§5), not guessed.
- Latest metrics row (`metrics`, ts 1795040326): CPU 51.1, mem_used_pct 93.08,
  load1 2.81 / load5 1.59 / load15 1.17, disk_used_pct 18.95.
- Latest decisions: id 291 `coordinator-pass-complete`, id 289
  `pool-stats-polled` (MoneroOcean 267,750,486 H/s, miners 4,908, height
  3,809,325). Latest events: kind `startup`, message `atlas_monitor started`
  (repeated — daemon restarts, see §5).
- Config (`config/atlas.json`): emergency_stop true, mining enabled false
  (design-only), trading paper-only, eligible capital $0, limits max_cpu_pct 50,
  max_mem_pct 70 (immutable without user authorization).
- Artifact (`atlas-command-center`, build `61fac176`, Mission 7): Mining tab order
  MiningDashboard, WalletCenter, EarningsSection, HistorySections, PayoutSection,
  CalculatorSection, MinerPrototypeSection, CoordinatorSection, RewardAccounting,
  UserDashboard, SettingsSection, HelpSection. The new **Admin command center**
  section goes directly BELOW UserDashboard, above Settings.

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
| D-M8-1 | Host is the system of record; artifact tables are a read-only display mirror (M5 D1, M6 D-M6-1, M7 D-M7-1 carried). Admin data is DERIVED from `data/coordinator.json` + `data/rewards.json` + `data/dashboard.json` + `data/diagnostics.json` + DB queries — no new stored truth. **No new host DB tables.** One new host export, `data/admin.json` (atomic write, §1). No new artifact mirror tables EXCEPT the two log tables in §1.1 (flagged deviation, ordered by the task — operational logs cannot live in a singleton row). |
| D-M8-2 | Estimated vs confirmed (M7 §3, binding, carried verbatim): estimated earnings are NULL with the verbatim reason "Cannot estimate — hashrate not measured" while Gate 1 is unmeasured. Confirmed earnings = ledger `SUM`, SIMULATION-tagged while mode is `simulation-only`. The admin mining panel REUSES the dashboard export's earnings block by import (never recomputes it) — the admin section must never show a different earnings number than the user dashboard. Estimate and confirmed are never combined into one total. |
| D-M8-3 | **No private data, ever.** The admin section shows aggregates and operational data only. It NEVER mirrors or displays: wallet addresses, token hashes, token salts, session tokens, password hashes, seed phrases, private keys, or any credential. Per-worker rows show id + type + status + registered/last-seen timestamps only. Per-user data is a COUNT only — no user rows, no user ids, no addresses. Decisions/events message text is mirrored only after the defensive redaction in §1.2 (a message matching a credential pattern is replaced, never shown). A figure that would need private data to compute is UNAVAILABLE, never approximated from it. |
| D-M8-4 | Security figures use the binding definitions in §4 (suspicious worker, invalid share, duplicate share, account abuse, auth failure, payout anomaly). A security count of 0 renders the verbatim empty state "No events recorded", never a bare 0 without context and never an invented threshold breach. No threshold, flag, or `degraded` inference is drawn from a security count in this mission — the section reports the numbers only. |
| D-M8-5 | Infrastructure figures use the binding definitions in §5. CPU/memory/disk come from the latest `metrics` row (RECORDED, with its timestamp). DB health is `integrity_check` + `user_version` + table counts. Queue lengths are UNAVAILABLE with the verbatim reason "No queue system exists — the coordinator runs synchronously in the 10-minute pass" (§5). API/pool connectivity is the last `pool_stats` poll + the last diagnostics run's endpoint tests. Service status is daemon snapshot freshness + coordinator last pass + watchdog last PASS line. Daemon uptime is UNAVAILABLE (no start time is recorded); monitoring uptime is the `metrics` span; daemon restarts are counted from `events` kind `startup`. |
| D-M8-6 | The admin section is STALE when the coordinator mirror OR the rewards mirror OR the diagnostics export is > 1 h old; "Not synced yet" when never synced. Last-sync shows all three sync timestamps separately (§6). |
| D-M8-7 | MIRROR-MISMATCH rule (M7 §6, carried and extended): the admin section compares the mirror's own derived ledger totals against the host-verified totals carried in the mirrored rewards export (same six comparisons as M7 §6). On any disagreement it shows the HOST-VERIFIED totals plus the verbatim note "Mirror mismatch — figures under investigation", and NEVER silently presents mirror rows as real earnings. It ALSO compares the mirrored log window against the host's latest-50 window (§7, secondary check): on disagreement it shows the host counts plus the same verbatim note. |
| D-M8-8 | Placement: a new "Admin command center" section in the Mining tab, directly BELOW the User dashboard section; the existing Mining tab section order is otherwise unchanged; NO new tab; zero buttons, inputs, links, or forms in the admin section; Start/Stop stay hard-disabled and untouched. Drill-down is INLINE detail rows (the contributing rows are shown under each aggregate by default), never a control — see §8. |
| D-M8-9 | No token, session token, or password hash is ever mirrored or displayed (see D-M8-3). No new cron. The admin export rides the existing coordinator pass as a guarded sub-step (never fails the pass, logs no decision of its own) — same pattern as M6/M7. |
| D-M8-10 | Every figure carries its provenance (host export vs mirror derivation) — see the data-flow table in §2. A figure with no provenance is a defect, not a display choice. |
| D-M8-11 | Amounts are shown in XMR to 6 decimal places (e.g. `0.000000 XMR`), converted from integer piconero only. No USD/fiat figure anywhere: `xmrPriceUsd` is null, so no conversion is attempted, ever. |
| D-M8-12 | This design does NOT repair any carried issue (§9). In particular it does NOT fix the Mission 6 hardcoded zero literals in `RewardAccounting.tsx`, does NOT repair the refresh failure, does NOT fix the stale "no miner yet" copy, and does NOT establish the rendered Mining-tab check. Each needs its own repair authorization. The admin section is designed so the finding-1 defect class cannot recur silently (§7); that is prevention, not repair. |
| D-M8-13 | Scope: the admin section renders the host-global view and labels it as such, with the verbatim scope line in §8: "Admin view — aggregates and operational data only. No login exists yet — this section is not access-controlled." No user account system exists (M1 §8, later mission), so there is no admin identity to bind the view to. The build lane must NOT invent a login, an admin picker, or demo admin rows. |

---

## 1. Data rules — derived only; no new host tables

**No new host tables.** Every admin figure is derivable from tables and exports
that already exist at `user_version` 3, plus one new host export:

| Admin need | Existing source |
|---|---|
| Network: users, workers, hashrate, shares, uptime | `data/coordinator.json` + `data/dashboard.json` (reused, never recomputed) + `metrics` span + `events` startup count |
| Mining: XMR mined, confirmed/pending, allocations, ATLAS revenue, payout volume, failed payouts | `data/rewards.json` `totals` / `balances` / `batches` / `ledger` (derived `SUM`s) + `data/dashboard.json` earnings block (reused verbatim, D-M8-2) |
| Infrastructure: CPU/mem/disk, DB health, queues, connectivity, services | latest `metrics` row + `PRAGMA integrity_check`/`user_version` + table counts + latest `pool_stats` row + `data/diagnostics.json` + `data/snapshot.json` + `logs/refresh-attempts.log` last line |
| Security: suspicious workers, invalid/duplicate shares, abuse, auth failures, payout anomalies | `workers` + `shares` + `events` (by kind) + `payouts` + `ledger` (reversal entries) |
| Operational logs: recent decisions + recent events | `decisions` + `events` tables (latest-50 window each, §1.1) |

**One new host export (derived, not stored).** `data/admin.json`, written
atomically (temp + `os.replace`) by the new host module `core/atlas_admin.py`
(stdlib-only), from the sources above at export time. The export carries the
four panel groups, the security rows, and the latest-50 log windows. No new
column, no new table, no stored aggregate — the value is recomputed on every
export. The artifact cross-checks it against its own mirrored rows (§7).

**§1.1 Flagged deviation — two new artifact mirror tables (ordered by the task).**
D-M8-1 says "no new artifact mirror tables", but the mission requires
"complete operational logs" and log rows cannot live in a singleton totals row
(the M7 migration-0007 pattern only fits scalars). The build therefore adds,
by additive migration (next journal index, same pattern as 0006/0007):

- `mining_admin_decisions` — mirror of host `decisions` rows (host id as PK,
  ts, dept, decision, reason), capped at the latest 50 rows; ingest deletes
  mirrored rows older than the window.
- `mining_admin_events` — mirror of host `events` rows (host id as PK, ts,
  kind, message), capped at the latest 50 rows; same window rule.

The section displays the latest 20 of each, with the verbatim window note
"Showing latest 20 of 50 mirrored rows — N total on host". The host DB remains
the complete log; the mirror is a window, never presented as complete. The host
side of D-M8-1 is untouched (no new host tables). The ingest for these tables
rides the existing refresh step (same pattern as `ingestRewardsState`), deduped
on host id; re-ingest of unchanged rows reports "already up to date" and does
NOT advance `syncedAt`.

**§1.2 Defensive redaction (binding, D-M8-3).** The host module applies this
rule to every decisions/events message before it enters `data/admin.json`, and
the artifact applies it again before display (defence in depth — either layer
alone must be sufficient):

- If a message matches `(?i)(token|secret|password|seed|private.?key|bearer|api.?key)`
  OR contains a run of 20+ base58/hex characters that is not a known pool
  `external_id`/`job_id` shape, the message is replaced with the verbatim
  string `[redacted — possible credential]` and the row is still counted.
- Worker rows never carry `token_hash` or `token_salt` (the module selects
  `id, worker_type, status, registered_at, last_seen_at` only — a `SELECT *`
  over `workers` in this module is a defect).
- User rows are never exported at all (count only). Share rows export
  `external_id`/`job_id` only where needed for the duplicate check (§4);
  those are pool-assigned job identifiers, not credentials.

**What is NOT a source.** Pool-wide stats (`pool_stats`: pool hashrate, miner
count, block height) are context only, never admin inputs for ATLAS's own
figures — the pool's total hashrate says nothing about ATLAS's share of a
reward (M6 §1.2). The Mining tab calculator's output never enters the admin
section. Local-test shares (`origin='local-test'`) never enter any mining,
efficiency, or earnings figure (they are diagnostics, §4). `workers.reported_hashrate_hps`
is an agent self-report only; it is never a measured hashrate and never feeds
any estimate (§3). `config/atlas.json` endpoint status strings
(`blockchain_apis`) are recorded claims, not live measurements — the section
shows them only alongside the last live poll time, never alone.

---

## 2. Data flow and provenance

```
Host (system of record)                              Artifact (display mirror)
─────────────────────────                            ─────────────────────────
atlas.db (user_version 3)                            drizzle mining_* tables
  users 0, workers 0, shares 0,                          (mirror of host rows,
  sessions 0, ledger 0,                                  deduped on host id,
  reward_batches 0, payouts 0                            re-ingest = "already
  pool_stats 42, decisions 291                           up to date")
  events 100, metrics 1100                                    ▲
        │                                                      │ ingestCoordinatorState
        │ coordinator export (atomic write,                    │ + ingestRewardsState
        │ 10-min pass) + rewards + dashboard                  │ + ingestAdminState
        │ + admin export + diagnostics export                 │ (existing actions,
        ▼                                                      │  extended)
data/coordinator.json ──► refreshAtlasData ────────────────────┘
data/rewards.json    ──► (existing tracked round-trip:         getMining reads
data/dashboard.json       started/baselineTs/landedTs/failed,  mirror tables only
data/admin.json           5 s polling, 5-min honest timeout)   + admin block
data/diagnostics.json
```

The admin block in `getMining` carries, per figure, the value AND its
provenance. Provenance tags follow the existing tab pattern:

- **RECORDED** — a value read from a host export or a mirrored host row.
- **DERIVED (host)** — computed by the host from its own tables at export time
  (e.g. ledger `SUM`s in `rewards.json` totals, security counts).
- **DERIVED (mirror)** — computed by the artifact from mirrored rows (e.g. the
  mirror's own ledger `SUM`, used only for the §7 comparison).
- **ESTIMATE** — a projection from verified inputs; in this mission no ESTIMATE
  figure exists (the mining estimate is null, §3).
- **UNAVAILABLE** — the source has no value (null), shown as such, never as 0.

**Figure-by-figure provenance (normative):**

| Admin figure | Host source | Mirror derivation | Provenance tag shown |
|---|---|---|---|
| Users / workers / hashrate / shares (Network) | `coordinator.json` + `dashboard.json` (reused) | counts over mirrored `mining_workers` / `mining_shares` | RECORDED (or UNAVAILABLE when null) |
| Monitoring uptime / daemon restarts | `metrics` span + `events` startup count | none (read through) | RECORDED |
| XMR mined / confirmed / pending / allocations / ATLAS revenue / payout volume / failed payouts (Mining) | `rewards.json` `totals` + `dashboard.json` earnings block (reused) | `SUM` over mirrored `mining_ledger` / `mining_reward_batches` / `mining_payouts` | DERIVED (host), SIMULATION-tagged |
| CPU / memory / disk | latest `metrics` row | none (read through) | RECORDED (with row timestamp) |
| DB health | `PRAGMA integrity_check` + `user_version` + table counts | none | RECORDED |
| Queue lengths | no queue system exists | none | UNAVAILABLE (verbatim reason, §5) |
| API / pool connectivity | latest `pool_stats` row + `diagnostics.json` endpoint tests | none | RECORDED |
| Service status | `snapshot.json` + coordinator last pass + watchdog log last line | none | RECORDED |
| Suspicious workers / invalid / duplicate shares / abuse / auth failures / payout anomalies (Security) | `workers` + `shares` + `events` + `payouts` + `ledger` (§4) | same counts over mirrored rows | DERIVED (host) |
| Operational logs (decisions / events) | `decisions` / `events` latest-50 window | mirrored `mining_admin_decisions` / `mining_admin_events` | RECORDED |
| Last sync time | artifact mirror `syncedAt` (coordinator + rewards + admin blocks) | none — this IS the mirror state | RECORDED (mirror time) |

---

## 3. Estimated vs confirmed earnings — the hard rule (M7 §3, carried verbatim)

**Estimated earnings (D-M8-2, binding).** With Gate 1 unmeasured (no probe
hashrate exists anywhere — `coordinator.json` `hashrate.measured_hps` is null)
and 0 shares, NO estimate is computable. The estimate field is **null**, and
the mining panel shows the verbatim reason:

> `Cannot estimate — hashrate not measured`

The estimate is never derived from pool-wide hashrate, never a guessed number,
never a benchmark figure, never back-filled from `workers.reported_hashrate_hps`.
The estimate is never added to a confirmed figure or a balance. **The admin
mining panel reuses the dashboard export's earnings block by import** — it does
not recompute confirmed earnings, balances, lifetime, or payouts. If the admin
section and the user dashboard ever disagree on an earnings figure, that is a
mismatch (§7), not two views.

**Confirmed earnings (D-M8-2, binding).** Confirmed earnings = ledger `SUM`
over `user_allocation` + `referral_reward` entries (M6 §5.1 sign convention),
SIMULATION-tagged while mode is `simulation-only`. Today: 0 entries →
`0.000000 XMR`. Confirmed earnings come only from settled reward batches;
open/held batches contribute nothing to confirmed earnings (they contribute to
*pending*, §8 Panel 2). A simulated figure is never shown without the
SIMULATION tag, and the word "earned" never appears next to a simulated figure
without that qualifier (M6 §8).

**XMR mined (the §16 "mining" figure).** "XMR mined" in the admin mining panel
is defined as confirmed ledger earnings (settled batches only, §3 above) — it is
NOT pool-wide output and NOT an estimate. Today: `0.000000 XMR (SIMULATION)`.

---

## 4. Security — binding definitions (D-M8-4)

All counts are computed over the live host tables by the host module; the
artifact cross-checks them over mirrored rows (§7, secondary checks). Each
security row shown inline (§8, drill-down) carries its evidence, never just a
count.

| Security figure | Binding definition |
|---|---|
| Suspicious workers | `COUNT` over `workers` where `status IN ('suspended','revoked')` OR (pool-origin rejected shares ≥ 10 AND rejected / (accepted + rejected) > 0.5 for that worker). Today: 0 workers → verbatim "No events recorded". Rows shown: id, type, status, registered_at, last_seen_at — never token fields (§1.2). |
| Invalid shares | `COUNT` over `shares` where `origin='pool'` AND `accepted=0`. Today: 0 → "No events recorded". (Local-test rejected shares are a prototype bug signal, not a worker-health signal, and are NOT counted here — they live in the Coordinator section.) |
| Duplicate shares | Groups of `shares` sharing the same non-null `external_id` (or, when `external_id` is null, the same `worker_id` + `job_id`) with count > 1. Count = number of duplicate rows beyond the first per group. Today: 0 → "No events recorded". Rows shown: external_id/job_id + worker id + submitted_at. |
| Account abuse | `COUNT` over `events` where `kind='abuse'`. No such kind has ever been recorded (events kinds on file: `startup` and coordinator kinds) → 0, "No events recorded". The definition is the rule; the absence of the kind is itself reported in the panel note: "No abuse events recorded". |
| Auth failures | `COUNT` over `events` where `kind='auth_failure'`. No such kind has ever been recorded → 0, "No events recorded", with the panel note "No auth-failure events recorded". |
| Payout anomalies | `COUNT` over `payouts` where `status='failed'` PLUS `COUNT` over `ledger` where `entry_type='reversal'`. Today: 0 payouts, 0 reversals → "No events recorded". Rows shown: payout id, amount, status, reason where present. |

**What this section does NOT do.** No threshold, flag, or `degraded` inference is
drawn from any security count in this mission — the section reports the numbers
only. A count of 0 is an honest zero with its empty-state copy, not a claim
that the system is "secure". The word "secure" never appears as a verdict in
this section.

---

## 5. Infrastructure — binding definitions (D-M8-5)

| Infrastructure figure | Binding definition |
|---|---|
| CPU / memory / disk | The latest `metrics` row (highest `ts`): `cpu`, `mem_used_pct`, `disk_used_pct`, `load1/5/15`, `net_rx_bytes`/`net_tx_bytes` — shown WITH the row timestamp ("as of <time>"). If the latest row is > 10 min old, the panel carries the STALE tag for that figure (§6). Memory above the 70% cap is shown as the number with the verbatim note "Above the 70% cap" — never hidden, never re-baselined. |
| DB health | `PRAGMA integrity_check` result (must be `ok`), `PRAGMA user_version`, and row counts for users/workers/shares/sessions/ledger/reward_batches/payouts/pool_stats/decisions/events/metrics. Any `integrity_check` ≠ ok is a stop condition: the section shows the verbatim note "Database integrity check failed — figures under investigation" and no derived figure is presented as verified. |
| Queue lengths | UNAVAILABLE. There is no queue table and no async queue in the system; the coordinator runs synchronously inside the 10-minute pass. The panel shows the verbatim reason: "No queue system exists — the coordinator runs synchronously in the 10-minute pass". No queue figure is invented, and no queue table is created to satisfy this panel. |
| API / pool connectivity | Last `pool_stats` row (pool name, recorded_at, hashrate, miners, block height) + the last diagnostics run's endpoint tests (tests 14 and 18 in `data/diagnostics.json`: MoneroOcean, CoinGecko, blockchain.info, mempool.space outcomes). The config `blockchain_apis` statuses are shown only with the last live poll time, labelled "recorded claim, not a live measurement". mempool.space is reported as its last outcome (flappy — §9), never settled by this design. |
| Service status | Three rows: daemon (snapshot.json `ts` age — fresh < 3 min = "Running", else "Stale — last seen <age> ago"; pid is NOT shown — the snapshot carries no pid, and none is guessed); coordinator pass (`last_coordinator_pass_at` from `coordinator.json` + `last_decision_id`); watchdog (last line of `logs/refresh-attempts.log` + its age). |
| Monitoring uptime | `MAX(ts) - MIN(ts)` over `metrics` (the monitoring span), shown as `Xd Yh Zm`. |
| Daemon restarts | `COUNT` over `events` where `kind='startup'` in the last 24 h (and all-time count beside it). Daemon uptime itself is UNAVAILABLE with the verbatim reason "Daemon start time is not recorded" — no start time exists in `snapshot.json` or the DB, and none is inferred from the last `startup` event (a restart writes a new event; the start time of the CURRENT process is not stored). |

---

## 6. STALE rules and last sync time (D-M8-6, binding)

- The admin section is **STALE** when the coordinator mirror OR the rewards
  mirror OR the diagnostics export is > 1 h old, measured from that block's
  `syncedAt` / `exported_at` to now. Any one stale → the whole admin section
  carries the STALE tag (a stale third is not a fresh admin view). The STALE tag
  names which source is stale (`STALE — diagnostics data 73 min old`).
- **"Not synced yet"** when a block has never synced (`syncedAt` null). A block
  that has never synced shows `Not synced yet` instead of a time, never `0` and
  never a guessed time. If any block has never synced, the section is STALE.
- **Last-sync panel shows all three sync timestamps** (coordinator block
  `syncedAt`, rewards block `syncedAt`, admin block `syncedAt` — the admin
  block's sync time is the ingest time of `data/admin.json`), each with its age
  (`synced <date time> (<age> ago)`), each with its own STALE / SYNCED tag.
  The three timestamps are never merged into one "last sync" figure.
- A re-ingest of unchanged data reports "already up to date" and does NOT
  refresh `syncedAt` — a re-ingest must never be mislabelled as a fresh sync
  (Mission 3 finding 1, carried — §9).
- The refresh failure (Mission 3 finding 1, carried) is NOT repaired here
  (D-M8-12). The STALE labelling is the mitigation, not the fix.

---

## 7. MIRROR-MISMATCH rule (D-M8-7, binding — the Mission 6 lesson, carried)

**The rule (primary — ledger totals).** On every render, the artifact compares
the mirror's own derived ledger totals against the host-verified totals carried
in the mirrored rewards export — the same six comparisons as M7 §6 (ledger entry
count; total user rewards; total ATLAS share; total pool fees; total payouts;
settled batches). On any disagreement:

1. The admin section shows the **HOST-VERIFIED totals** (from the rewards
   export), not the mirror-derived ones.
2. The admin section shows the visible verbatim note, in the section header area,
   next to the affected figures:

> `Mirror mismatch — figures under investigation`

3. The mirror rows are still listed but are labelled as mirror rows under
   investigation — they are never silently presented as real earnings.
4. The mismatch is logged (artifact-side, in the same honest-failure pattern as
   the refresh flow: surfaced, not swallowed).

**Secondary check (log window).** The admin section also compares the mirrored
log window against the host's latest-50 window carried in `data/admin.json`
(`decisions_total`, `events_total`, and the id lists of the latest 50). A
disagreement shows the host counts plus the same verbatim mismatch note. The
ledger comparison above is the primary check and must exist even if the log
check is deferred; the log check must not be substituted for it.

**Secondary check (security counts).** The security counts derived from mirrored
rows are compared against the host-computed counts in `data/admin.json`. A
disagreement shows the host counts plus the same verbatim note.

**General-case requirement (binding).** The mismatch rule is written for the
general case, not today's zeros. The admin section's figures are therefore
always derived from the totals (host-verified first, mirror-derived for
comparison), never hardcoded literals. **No hardcoded zero (or any hardcoded
figure) is permitted anywhere in the admin section.** A panel whose value is a
literal in the component source is a defect, full stop — the build lane's grep
check (§10) enforces this. Agreement on today's all-zero state (0 = 0) is a
valid trivial agreement and says nothing about the check working — the build
lane must test the check with non-zero fixture data on a temp/sandbox mirror,
not with zeros alone.

---

## 8. UI spec — Admin command center section in the Mining tab (exact, build-ready)

### 8.1 Placement and rules

- **Location:** inside the existing Mining tab (`client/src/Mining.tsx`, artifact
  `atlas-command-center`). **NO new tab.** The section sits **directly below the
  "User dashboard" section** and above Settings. It does not reorder, restyle,
  or reword any existing section. Current tab order, unchanged (M7 §7.1,
  carried): MiningDashboard, WalletCenter, EarningsSection, HistorySections,
  PayoutSection, CalculatorSection, MinerPrototypeSection, CoordinatorSection,
  RewardAccountingSection, UserDashboardSection, **[AdminCommandCenterSection]**,
  SettingsSection, HelpSection.
- **Component:** new `client/src/AdminCommandCenter.tsx` (export
  `AdminCommandCenterSection`, taking the same `m` prop shape as
  `UserDashboardSection` — the `getMining` result). Data comes from the
  extended `getMining` action (`admin` block, §1–§2) reading the artifact
  `mining_*` mirror tables only. React Query refetch: same 30 s cadence as the
  rest of the Mining tab. No new refresh schedule.
- **Scope line (verbatim, D-M8-13):** directly under the section heading:

> `Admin view — aggregates and operational data only. No login exists yet — this section is not access-controlled.`

- **Provenance:** every figure carries a SNAPSHOT / RECORDED / ESTIMATE /
  UNAVAILABLE tag plus a SIMULATION tag while mode is `simulation-only`,
  following the existing tab pattern. Nothing is labelled live unless it was
  measured in the current probe/session.
- **Zero controls.** There is no button, input, link, or form anywhere in this
  section: no "suspend worker", no "retry payout", no "refresh now", no
  "recalculate", no filter input, no settings control. Admin actions are NOT
  in scope — this mission builds a monitoring dashboard, not an admin console
  (§16: "a single-user monitoring dashboard, not an admin console"). The
  existing Start/Stop buttons in the Mining dashboard stay **hard-disabled with
  no handler** (Missions 2/4/5/6/7) and are untouched by this section.
- **Drill-down is inline, not interactive (D-M8-8).** Each aggregate shows its
  contributing rows directly beneath it by default (security rows, batch rows,
  payout rows, log rows). There is no expand/collapse control, no row click,
  no detail page. A row that would need private data to show is omitted with
  the verbatim note "Row omitted — private data" (§1.2).
- **Copy that must NOT appear in this section:** any wallet address, token hash,
  session token, password hash, or credential; any per-user identifier or row;
  any hashrate number presented as ATLAS's without a `MEASURED` tag and a
  measurement time; the words "verified", "confirmed", or a checkmark next to
  any worker, address, or hashrate that has only passed format checks or
  self-report; the word "secure" as a verdict; "There is no miner yet" (stale
  copy, Mission 4 finding 4 — carried, §9); any earnings, balance, or payout
  figure derived from shares or hashrate; any USD/fiat figure; any combined
  "total earnings" mixing estimated and confirmed figures; any queue-length
  number (UNAVAILABLE by rule, §5).
- **Responsive / accessibility (binding, M5 §7.4 carried):** tables/cards
  collapse to stacked cards below ~640 px; no horizontal page overflow at
  390 px (mobile overflow 0); all status text is text, not colour alone
  (a screen reader must hear `Running` / `Stale` / `not measured`, not just
  a colour).

### 8.2 Panels (verbatim headings, labels, empty states)

**Panel group 1 — Network**

| Panel | Heading (verbatim) | Fields (verbatim labels) | Empty state (verbatim) |
|---|---|---|---|
| 1a | `Network — users and workers` | `Users` (count); `Workers total`; `Active`; `Browser`; `Desktop`; `Registered`; `Degraded`; `Suspended`; `Revoked`; `Pending` | `No users yet` when users = 0; `No workers yet` when workers = 0 |
| 1b | `Network — hashrate and shares` | `Total hashrate` (status + value); `Pool shares accepted`; `Pool shares rejected`; `Local-test shares accepted`; `Local-test shares rejected` | Hashrate: `not measured` (verbatim, Gate 1 unmeasured). Shares 0: `No shares yet` |
| 1c | `Network — uptime` | `Monitoring uptime` (metrics span, `Xd Yh Zm`); `Daemon restarts (24h)`; `Daemon restarts (all time)`; `Daemon uptime` | Daemon uptime: `Daemon start time is not recorded` (verbatim, §5) |

**Panel group 2 — Mining** (all figures SIMULATION-tagged; earnings block reused
from the dashboard export, D-M8-2)

| Panel | Heading (verbatim) | Fields (verbatim labels) | Empty state (verbatim) |
|---|---|---|---|
| 2a | `Mining — XMR mined` | `XMR mined (confirmed, settled batches only)`; `Estimated earnings` (null + reason) | Estimated: `Cannot estimate — hashrate not measured`. Confirmed 0: `0.000000 XMR (SIMULATION)` |
| 2b | `Mining — rewards` | `Confirmed rewards`; `Pending rewards (open/held batches)`; `User allocations`; `ATLAS revenue`; `Pool fees` | Pending 0: `No open or held batches`. All 0: figures shown as `0.000000 XMR (SIMULATION)` |
| 2c | `Mining — payouts` | `Payout volume`; `Payouts count`; `Failed payouts` (count + inline rows, §4) | `No payouts yet` when count = 0 |

**Panel group 3 — Infrastructure**

| Panel | Heading (verbatim) | Fields (verbatim labels) | Empty state (verbatim) |
|---|---|---|---|
| 3a | `Infrastructure — host resources` | `CPU` (latest metrics row, with row time); `Memory used`; `Disk used`; `Load 1/5/15 min`; `Network rx/tx` | Memory above cap: number + verbatim `Above the 70% cap`. Row > 10 min old: STALE tag on the figure |
| 3b | `Infrastructure — database health` | `Integrity check`; `Schema version`; per-table row counts (users, workers, shares, sessions, ledger, reward_batches, payouts, pool_stats, decisions, events, metrics) | Integrity ≠ ok: verbatim `Database integrity check failed — figures under investigation`, no derived figure presented as verified |
| 3c | `Infrastructure — queues` | `Queue lengths` | Verbatim: `No queue system exists — the coordinator runs synchronously in the 10-minute pass` |
| 3d | `Infrastructure — connectivity` | `Last pool poll` (pool, time, hashrate, miners, block height); `MoneroOcean`; `CoinGecko`; `blockchain.info`; `mempool.space` (last diagnostics outcomes) | Never polled: `Not polled yet`. Config statuses labelled `recorded claim, not a live measurement` |
| 3e | `Infrastructure — services` | `Daemon`; `Coordinator pass`; `Watchdog` (each: status text + last-seen age) | Daemon stale: `Stale — last seen <age> ago` |

**Panel group 4 — Security** (definitions §4; every count with its inline rows)

| Panel | Heading (verbatim) | Fields (verbatim labels) | Empty state (verbatim) |
|---|---|---|---|
| 4a | `Security — workers and shares` | `Suspicious workers` (count + rows); `Invalid shares` (count); `Duplicate shares` (count + rows) | Each 0: `No events recorded` |
| 4b | `Security — accounts and payouts` | `Account abuse events` (count + note); `Auth failures` (count + note); `Payout anomalies` (count + rows) | Each 0: `No events recorded`. Abuse note: `No abuse events recorded`. Auth note: `No auth-failure events recorded` |

**Panel group 5 — Operational logs** (latest-50 mirror window, §1.1)

| Panel | Heading (verbatim) | Fields | Window note (verbatim) |
|---|---|---|---|
| 5a | `Operational logs — decisions` | Latest 20 decisions: time, dept, decision, reason. Dept counts above the list (grouped counts). | `Showing latest 20 of 50 mirrored rows — N total on host` |
| 5b | `Operational logs — events` | Latest 20 events: time, kind, message (redacted per §1.2). Kind counts above the list. | `Showing latest 20 of 50 mirrored rows — N total on host` |

**Panel group 6 — Last sync**

| Panel | Heading (verbatim) | Fields |
|---|---|---|
| 6 | `Admin — last sync` | Coordinator `syncedAt` + age + tag; Rewards `syncedAt` + age + tag; Admin `syncedAt` + age + tag. STALE naming which source is stale (§6). |

---

## 9. Carried issues — NOT fixed by this design (D-M8-12)

1. **Rendered Mining-tab check NOT established** (M7 finding 1, still owed —
   now the fourth consecutive mission with this gap). No captured render ever
   selects the Mining tab on build `61fac176`. A repair-authorized Mining-tab
   render capture (select Mining, capture desktop + mobile, console, overflow,
   then reload + re-select Mining) is owed.
2. **Gate 1 still unmeasured** — every hashrate reads "not measured". A fresh
   interactive probe run is owed.
3. **Refresh failure carried** (Mission 3 finding 1, NOT fixed). The admin
   labels stale mirrors rather than presenting them as fresh, but a failed
   refresh still stalls the mirror.
4. **Stale "no miner yet" copy carried** (Mission 4 finding 4, NOT fixed) —
   exactly two strings in `Mining.tsx`. Repair needs a repair-authorized
   inspection.
5. **Mission 6 finding 1 is latent, not repaired.** The hardcoded zero literals
   in `RewardAccounting.tsx` are still there. The admin's mismatch rule detects
   the shape but the underlying display defect is NOT fixed — repair still needs
   a repair-authorized inspection. It does not bite today: the live mirror and
   live host totals are both 0.
6. **Duration secondary check wiring not independently verified** (M7 finding 6).
   Dormant at 0 sessions; verify the population path before any session exists.
7. **Panel 1 "0 users" wording tension (minor, source-level, M7 finding 7):**
   the dashboard counts distinct user_ids on mirrored ledger entries (0), while
   `mining_users` holds 1 scaffold row (`local-user`, no wallet). The admin
   network panel counts `users` from the coordinator export (0) and must use the
   same verbatim `No users yet` copy — a wording decision is owed, not a repair.
8. **"Derived host" tag wording (minor, M7 finding 8):** when mismatch is false
   the confirmed-figure tag reads "Derived host"; it may confuse. Same standing
   as finding 7.
9. **SupportXMR fallback not implemented** (D-M5-3, carried) — no verified
   stats-API URL; a URL must never be guessed.
10. **Referral rate 5% is a design parameter to confirm** before any real-mode
    settlement (engine defaults to 500 bps; `referral_rate_bps` absent from
    `pool-rewards.json`).
11. **Minimum payout still null/placeholder** — undecided, needed before any
    payout flow.
12. **D-M5-1 (carried):** browser-probe `session_token_hash` stores marker
    `none:browser-probe` instead of NULL. Confirmed in code; no live row to
    inspect (sessions 0).
13. **Host memory 78–93% above the 70% cap** (standing, pre-existing; 93.08%
    at design time). Re-scope proposal still needs user approval.
14. **mempool.space disputed, not settled.** 000 (timeout) on some attempts,
    200 on others. Flappy.
15. **Daemon restarts of undetermined cause** (carried). Watchdog restarts
    continue. Single instance maintained; not a stop condition.
16. **DB file growth, partly unexplained (carried).** The pre-Mission 2 jump
    (36,864 → 163,840 B) remains unexplained at page level.
17. **Diagnostics sensitivity:** the suite is sensitive to endpoint flapping;
    a 22/24 with only tests 14/18 failing is the known stall signature, not a
    regression. Test count grows 24 → 25 in this mission (new test 25, §10).

---

## 10. Verification requirements (binding on the build/test lanes)

- **Host module tests** (`core/test_atlas_admin.py`, temp DBs only): (a) zero-state
  derivation with all verbatim strings + read-only proof (all table counts
  unchanged across status+export, decisions table unchanged — the module logs no
  decision); (b) a non-zero fixture scenario (workers incl. one suspended +
  one high-rejection worker; pool shares accepted/rejected incl. a duplicate
  external_id group; one failed payout + one reversal; decisions/events rows
  incl. one message containing a fake token string asserting redaction; metrics
  rows incl. one stale row) asserting every security count, the redaction, the
  queue UNAVAILABLE reason, the uptime UNAVAILABLE reason, and the earnings
  block identical to the dashboard export; (c) export idempotence + atomic
  write (temp + `os.replace`, no partial file on failure); (d) `run_pass`
  sub-step on a temp DB — all exports written, exactly +1 decision per pass
  (`coordinator-pass-complete`), admin export fresh.
- **Diagnostics test 25** ("admin export": file parses, `exported_at` fresh,
  hashrate not-measured, estimate null, earnings block equals a fresh
  `dashboard.json` earnings block, host-verified totals match a fresh
  COUNT/SUM over the live DB, security counts match fresh SQL, no
  `token_hash`/`token_salt`/wallet field anywhere in the file). Suite must be
  25/25.
- **Mismatch proofs (sandbox, not zeros alone):** (a) ledger mismatch — mirror
  totals disagreeing with host totals returns `mismatch: true` with the
  disagreeing fields named and confirmed figures switched to host-verified;
  (b) log-window mismatch — mirrored log ids disagreeing with the host's
  latest-50 window returns the same verbatim note with host counts shown.
- **Grep checks (build lane, §5-style):** zero `<button>`/`<input>`/`<a>`/`<form>`
  in the new component; zero hardcoded figure literals as displayed values;
  verbatim strings present (§3, §4, §5, §8); no `token_hash`, `token_salt`,
  `password`, `seed`, `private_key`, wallet-address pattern in the component
  or in `data/admin.json`; no `SELECT *` over `workers` in the host module.
- **Live check (coordinator, after the build):** `getMining` admin block
  present — all zeros, estimate null + verbatim reason, `mismatch: false`,
  host == mirror totals, mirrors fresh; decisions/events mirror windows hold
  the latest rows; no credential field in the mirror.
- **Independent host verification (Lane E):** re-derive every `data/admin.json`
  field from the live DB with fresh SQL and compare; confirm the module wrote no
  decisions/ledger rows; confirm configs unchanged (sha256 vs baseline);
  confirm the full unit suite unmodified and passing; confirm the coordinator
  sub-step is guarded (temp-DB `run_pass` decisions exactly +1).
- **Independent artifact inspection (repair_authorized=false):** implementation
  verified in source + data (placement, panels, zero interactive elements, no
  hardcoded figures, all-zero totals, mismatch false, mirrors fresh). Render
  status reported honestly — a render capture is NOT required of this lane, but
  if no Mining-tab capture exists, the report must say so plainly (the M7
  finding-1 gap is not closed by assertion).
