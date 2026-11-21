# ATLAS — Master Mission 6: Reward Accounting (75/25 Engine) — Design

**Mission:** Master Mission 6 — Reward Accounting (75/25 reward engine, simulation only)
**Date:** Wednesday, 2026-11-18
**Author:** Lane A (design)
**Authorization:** User authorized Master Mission 6 at 11:06 EST, 2026-11-18.
**Status:** DESIGN ONLY. No code, config, database, or website artifact was edited in this
mission. This document is the binding contract for the build lane.
**Scope:** The 75/25 reward engine IN SIMULATION. There are no real pool rewards yet
(0 workers, 0 shares, no pool connection for earning), so every figure the engine
produces in this mission is simulated or zero, clearly marked as such.

## 0. Grounding — what this design rests on

Read before writing this design (all under `~/workspace/atlas/`):

- Mission 1 inspection report (`docs/master-mission1-inspection-report-2026-11-18.md`) §6 —
  the accounting basis: distributions only from actual confirmed pool rewards; integer
  piconero; difficulty-weighted pool-accepted shares; immutable append-only ledger;
  batch dedupe; payout idempotency keys; 75% inviolable; referral rewards from the
  ATLAS 25% only.
- Mission 2 report — Stage 0 schema (9 tables, `user_version` 1) and
  `config/pool-rewards.json` (MoneroOcean primary 0% fee, SupportXMR 0.6%, P2Pool 0%,
  75/25 split, mode `simulation-only`, minimum payout null/placeholder, ledger rules).
- Mission 3 report — wallet center; finding 1 (refresh failure) is a known issue, NOT
  fixed here. Finding: the UI mislabels a re-ingest of the already-stored snapshot as
  "Refresh complete".
- Mission 4 report — miner prototype (browser WASM + local-test relay, probe hook
  `?atlas-miner-test=1`); Gate 1 measured hashrate UNMEASURED; Gate 2 (real pool
  accepted shares) NOT TESTED; Gate 4 (real payout) NOT TESTED — hard gate. Finding 4:
  exactly two stale "no miner yet" strings in `Mining.tsx` (`:234` dashboard, `:1204`
  Help) — NOT fixed here.
- Mission 5 report + `core/atlas_coordinator.py` — coordinator (worker registry, share
  accounting, pool stats, sessions, 10-min cron `atlas-coordinator-pass-10m`);
  decisions D1–D10 (host DB is system of record, artifact is a read-only mirror, no
  artifact→host write path, no hashes mirrored, one `shares` table with `origin`,
  worker `active` only after pool-accepted shares, pool stats read-only GET, derived
  state, `dept='coordinator'` decisions, coordinator never starts/stops mining).
  Deviations carried: D-M5-1 (`none:browser-probe` marker), D-M5-2 (`pool-stats-polled`
  success decision), D-M5-3 (SupportXMR stats fallback NOT implemented — no verified
  stats-API URL, never guessed).
- `core/migrate_mission2_stage0.sql`, `core/migrate_mission5_stage1.sql`.
- Live DB schema, read 2026-11-18 (read-only): `PRAGMA user_version` = 2,
  `integrity_check` = ok; users 0, workers 0, shares 0, ledger 0, payouts 0,
  referrals 0, sessions 0, pool_stats 20 (MoneroOcean polls), decisions 175.

**Safety state (unchanged, verified by prior missions):** emergency_stop true, mining
disabled, trading paper-only, eligible capital $0. No wallets, keys, or seed material.
No real payouts, no pool connection for earning, no share submission to any pool, no
mining activation, no spending. Gate 4 (a real payout) is a hard gate requiring explicit
authorization + successful security testing + a treasury design — none exists.

**Known issues noted only, NOT fixed by this mission (no repair authorized):**
- Refresh failure (Mission 3 finding 1, carried through Missions 4–5): refresh fails at
  the platform spawn step; the UI mislabels a re-ingest as "Refresh complete". The
  reward section must therefore label mirrored data STALE when the underlying snapshot
  is stale, exactly as the Coordinator section already does — never present stale
  reward figures as fresh.
- Stale "no miner yet" copy (Mission 4 finding 4): two strings in `Mining.tsx`.
- Gate 1 unmeasured: no measured hashrate exists. The engine does not use hashrate at
  all (see §1) — this gap does not block the engine, and the engine must never fill it
  with an estimate.

## Decisions (binding on the build lane)

| # | Decision |
|---|---|
| D-M6-1 | Host DB is the system of record; the artifact is a read-only display mirror (M5 D1 carried). The engine writes only to the host DB. No artifact→host write path. |
| D-M6-2 | All money is integer piconero (1 XMR = 10^12). Never floats. Split: pool fee floored, ATLAS 25% floored, users receive the remainder; per-user allocation by the largest-remainder method (§4) so the batch reconciles to the piconero with zero unaccounted dust. |
| D-M6-3 | Attribution is difficulty-weighted pool-accepted shares only. NULL difficulty counts as weight 1 and is flagged; a pool-accepted share with NULL `external_id` is EXCLUDED from attribution (no dedupe key, no credit) and counted in the batch record. |
| D-M6-4 | Ledger is append-only with a SHA-256 hash chain (genesis `prev_hash` = 64 zeros; deterministic entry order fee → atlas_share → referral_reward → user_allocation). Corrections are `reversal` entries only, never UPDATE/DELETE. |
| D-M6-5 | Exactly-once processing: `UNIQUE(pool_name, source_ref)` on reward batches + `UNIQUE(share_id)` on the batch↔share link table. A re-settle of the same batch is a logged no-op. |
| D-M6-6 | Referral reward = 5% (500 bps, config parameter) of the referred user's allocation in that cycle, funded from the ATLAS 25% only, direct referrals only, no self-referral, only when the referred user earned > 0 in that cycle. Zero when no referrals exist — honestly 0. |
| D-M6-7 | Simulation exemption: simulation-mode batches may settle while the emergency stop is ON (they move no real value and are the only way to test the engine while the stop is correctly ON). Real-mode batches are REFUSED while the stop is ON or while config mode is `simulation-only`. |
| D-M6-8 | No new cron and no duplicate of the coordinator cron. The engine rides the existing 10-min coordinator pass as a guarded sub-step that is a no-op when no batch is due (§9). On-demand CLI for the simulation test. |
| D-M6-9 | A Stage 2 schema migration IS required (proved in §11): `reward_batches` + `reward_batch_shares` tables, ledger rebuild (new entry types + hash-chain/batch/mode columns), `payouts.idempotency_key`. `user_version` 2 → 3. Build lane backs up the DB first, applies in one transaction. The live ledger is empty (0 rows), so the rebuild copies zero rows. |
| D-M6-10 | A batch with zero eligible share weight is HELD (status stays `open`, no ledger entries, decision logged). Its value is never auto-allocated to ATLAS and never invented. |
| D-M6-11 | In this mission the simulation runs against a TEMPORARY database copy (same pattern as Mission 5's 18/18 unit tests). The live DB receives ZERO ledger rows from Mission 6. |
| D-M6-12 | Balances are DERIVED (`SUM` over ledger entries per user), never stored. No stored running-balance column — a stored balance can drift from the entries; the entries are the single truth. |
| D-M6-13 | The reward section goes directly below the Coordinator section in the Mining tab (no new tab). All other tab order is unchanged (see §10). |

---

## 1. Engine inputs — what counts as verified, and what does not

### 1.1 The two inputs

The engine consumes exactly two inputs. Nothing else enters the calculation.

**Input A — verified accepted shares.** Rows in the existing `shares` table satisfying
ALL of the following:

- `origin = 'pool'` (Mission 5 D5: one table, `origin` column; local-test shares are
  permanently marked and excluded from every attribution/activation/balance query).
- `accepted = 1` (rejected shares earn nothing).
- `external_id IS NOT NULL` (the dedupe key; §3, §6). A pool-accepted share with NULL
  `external_id` is excluded from attribution and counted in the batch record as
  `null_external_id_count` (§1.3).
- `submitted_at` inside the batch's window `[window_start, window_end)` (§9).
- Not already linked to any earlier batch (§6 — enforced by `UNIQUE(share_id)` on the
  link table; the settle query selects only unattributed shares).
- The owning worker's batch was not rejected at record time. (The coordinator already
  rejects batches for revoked workers and for non-active tokens; every recorded
  pool-accepted share therefore passed those gates. The engine does not re-litigate
  worker status — it trusts the coordinator's record, and attributes by the
  share→worker→user mapping in §3.)

Weight of one share = `COALESCE(difficulty, 1)`. A NULL difficulty is flagged at record
time by the coordinator (`share-batch-null-difficulty` decision) and counted in the
batch record as `null_difficulty_count`; it still counts as weight 1 (Mission 5
precedent). The engine never guesses a difficulty and never uses a default other than 1.

**Input B — a confirmed pool reward.** One row in the new `reward_batches` table (§11)
carrying: `pool_name`, `mode` (`real` | `simulation`), `source_ref` (the pool's own
payout/credit reference), `source_evidence` (how the reward was confirmed — e.g. the
pool API response reference and txid, or `simulated-harness:<id>`), `gross_piconero`
(> 0), `fee_bps` (copied from `config/pool-rewards.json` for that pool at record time),
and the attribution window `[window_start, window_end)`.

- **Real mode:** "confirmed" means the pool's own accounting shows a credit/payout to
  the ATLAS pool wallet for the period, cross-checked against the chain where feasible
  (Mission 1 §6). The per-miner/per-wallet pool reward endpoint has NOT been verified
  yet — the engine's interface is defined here, but the live fetch that would record
  a real batch is NOT built in Mission 6 and must never be guessed. Recording a real
  batch is a future mission's work, after that endpoint is verified.
- **Simulation mode:** the batch is injected by the test harness with
  `mode='simulation'`, a `sim-…` batch ref, and `source_evidence` naming the harness
  run. Simulated rewards are clearly marked `simulation` in the DB row, in every
  ledger entry derived from them (`ledger.mode='simulation'`), and in the UI (§8, §10).

### 1.2 What does NOT count (never an input, never paid from)

- **Local hashrate.** `workers.reported_hashrate_hps` is an agent self-report only; it
  is NULL by default and is NEVER populated from benchmarks or estimates (Mission 5).
  It is not evidence of work and never enters attribution. (VoltMiner's rounding-mode
  bug, Mission 1 §4: local metrics can look perfect while every share is invalid.)
- **Estimated hashrate.** Estimates may be shown on the dashboard labelled ESTIMATE;
  they must never create a payable balance and never enter the engine.
- **Local-test shares** (`origin='local-test'`). Diagnostics only. In simulation they
  may be used ONLY inside a simulation-mode batch, to exercise the attribution math
  against known difficulties — and every figure derived from them is labelled
  SIMULATION / LOCAL TEST (§8). A local-test share can never appear in a real-mode
  batch: the settle query for a real batch filters `origin='pool'` unconditionally.
- **Pool-wide stats.** `pool_stats` rows (pool hashrate, miners, block height) are
  context for the UI, not engine inputs. The pool's total hashrate says nothing about
  ATLAS's share of a reward.
- **Projected earnings / calculator output.** The Mining tab calculator is an estimate
  tool (Mission 2). Its output never enters the ledger.
- **Unverified work of any kind.** No credit without a pool-accepted share (real mode)
  or a harness-verified local-test share inside a simulation batch (simulation mode).

### 1.3 Batch record — what the settle pass reports

Every settle attempt writes a `reward_batches` outcome and a `decisions` row
(`dept='rewards'`). The batch record carries: `shares_count` (pool-accepted shares
attributed in the window), `null_difficulty_count`, `null_external_id_count` (excluded
shares), `fee_piconero`, `net_piconero`, `atlas_share_piconero`,
`users_total_piconero`, `referral_total_piconero`, `status`, `settled_at`. A batch that
settles with any excluded shares still settles — the exclusions are counted, not hidden.

---

## 2. Fee deduction — disclosed pool fees only, in order

Order of operations for one batch (all integer piconero, all steps exact):

```
1. gross_piconero            confirmed pool reward (Input B; must be > 0)
2. fee_piconero   = gross_piconero * fee_bps // 10_000   (floor division)
3. net_piconero   = gross_piconero - fee_piconero
4. atlas_share    = net_piconero * 25 // 100              (floor; §4)
5. users_total    = net_piconero - atlas_share             (remainder to users)
6. users_total is split per-user by largest remainder (§4)
7. referral_total is taken OUT OF atlas_share (§7); atlas_retained = atlas_share - referral_total
```

- **Pool fee** comes from `config/pool-rewards.json` for the batch's pool, read at
  batch-record time and stored on the batch row (`fee_bps`): MoneroOcean 0 bps,
  SupportXMR 60 bps (0.6%), P2Pool 0 bps. The fee is floored (`//`); the sub-piconero
  remainder stays in `net` (it favours users, never ATLAS silently). Only the
  configured fee for the named pool is deducted — no other fee, ever.
- **Payout transaction fees are NOT deducted here.** Per the config, network
  transaction fees for payouts are deducted from the payout amount and disclosed to
  the user before payout. There are no payouts in Mission 6 (Gate 4), so payout fees
  are $0 / not applicable in this mission. When the payout flow is built (later
  mission), the fee is computed at payout time, never retroactively against a settled
  batch.
- **Infrastructure charges: none.** The config states "none agreed; any future
  infrastructure charge must be disclosed to users before mining, never added
  silently." The engine deducts no infrastructure charge. If one is ever agreed, it
  requires a config change + user authorization + a design update — the engine must
  refuse an unknown charge rather than invent one.
- **Fee entry in the ledger:** one `fee` entry per settled batch (`user_id` NULL,
  `amount_piconero = +fee_piconero`, `batch_id` set, `reference =
  "pool-fee:<pool_name>:<batch_ref>"`). A zero fee (MoneroOcean, P2Pool) still gets a
  `fee` entry of 0 piconero, so the batch reconciliation (§5) always has all four
  terms present and auditable.

---

## 3. Attribution — by verified accepted shares

**Mapping.** A share maps to a user in two hops, both by foreign key — no name matching,
no address matching, no inference:

```
shares.worker_id  →  workers.id  →  workers.user_id  →  users.id
```

Attribution aggregates per USER (a user with several workers has their weights summed
across all their workers). The engine query for a batch window is:

```sql
SELECT w.user_id AS user_id, SUM(COALESCE(s.difficulty, 1)) AS weight
FROM shares s JOIN workers w ON w.id = s.worker_id
WHERE s.origin = 'pool' AND s.accepted = 1
  AND s.external_id IS NOT NULL
  AND s.submitted_at >= :window_start AND s.submitted_at < :window_end
  AND NOT EXISTS (SELECT 1 FROM reward_batch_shares l WHERE l.share_id = s.id)
GROUP BY w.user_id
```

(Simulation batches use the identical query with `origin = 'local-test'` instead of
`'pool'` — the origin filter is a parameter of the batch mode, never omitted. A
simulation batch therefore exercises the same code path with test shares.)

**Share-id dedupe (two layers).**
1. **At record time (coordinator, already built):** `UNIQUE INDEX
   idx_shares_worker_external ON shares(worker_id, external_id) WHERE external_id IS
   NOT NULL` + `INSERT OR IGNORE` — a same-worker duplicate is skipped and counted;
   an `external_id` seen for a DIFFERENT worker suspends the worker and rejects the
   batch (`worker-suspended` decision). This is the first line of defence and is
   unchanged.
2. **At settle time (this engine):** the `reward_batch_shares` link table carries
   `UNIQUE(share_id)` — one share can belong to at most one batch — and the settle
   query excludes already-linked shares (`NOT EXISTS` above). A share is linked to its
   batch in the same transaction that writes the ledger entries, so a crash mid-settle
   rolls everything back and the batch stays `open`.

**What a share's weight is.** `COALESCE(difficulty, 1)` per share, summed per user.
Difficulty here is the pool-assigned share difficulty as recorded by the coordinator
— the pool's own measure of the work's value, not a local estimate.

**Edge cases.**
- A worker revoked after its shares were recorded: the shares were verified when
  accepted, so they still attribute (the coordinator already rejects any batch
  submitted after revocation). The engine does not re-check current worker status.
- A user with no validated XMR address: allocation is still credited. Balances are
  ledger-based, not wallet-based; an address is required only at payout time (Mission
  3 validation), never for earning.
- A user whose workers contributed zero accepted shares in the window: allocation 0,
  no ledger entry (no zero-amount `user_allocation` rows — they add noise, not
  information; the batch record's `shares_count` and the decision-log reason show who
  contributed).

---

## 4. The 75/25 split — exact integer arithmetic

All arithmetic is integer piconero. **Floats are forbidden anywhere in the engine**
(no `float`, no `round()` on floats, no percentage floats). Fees are integer basis
points; the split is integer percent; weights are integers.

**Split (per batch, after the fee in §2):**

```
atlas_share = net_piconero * 25 // 100        # floor
users_total = net_piconero - atlas_share       # users receive the remainder
```

The ATLAS share is floored and the users receive `net − atlas_share`, so the rounding
remainder (0 or 1 piconero: writing `net = 4q + r` with `r ∈ {0,1,2,3}`, the floored
ATLAS share is exactly `q`, so `users_total = 3q + r` exceeds `net*75//100` by at most
1) goes to the users, never silently to ATLAS (Mission 1 §6: dust is never "rounded
to ATLAS").

**Per-user allocation — largest-remainder method.** Let `W` = total weight of all
contributing users in the batch, `w_i` = user `i`'s weight:

```
exact_i  = users_total * w_i          # exact numerator; never a float
floor_i  = exact_i // W               # base allocation
rem_i    = exact_i % W                # fractional remainder, 0 <= rem_i < W
leftover = users_total - SUM(floor_i) # 0 <= leftover < (number of users)
```

Distribute `leftover` one piconero at a time to the users with the largest `rem_i`
(ties broken by lowest `user_id` first) until `leftover` is exhausted. Each user
receives `floor_i` plus at most 1 extra piconero. Result: `SUM(allocations) =
users_total` exactly — zero unaccounted dust, every piconero owned by someone.

**Where the ATLAS 25% goes.** The ATLAS share is credited as one `atlas_share` ledger
entry per batch (`user_id` NULL) for the RETAINED amount — i.e. `atlas_share −
referral_total` (§7). Referral rewards are separate `referral_reward` entries paid
from that 25% (§7). The ATLAS share is ATLAS's revenue: it is recorded, never spent,
never moved by this engine (no treasury, no payout path — Gate 4). The transparency
figures (Mission 1 §6: total user rewards, total ATLAS share, pool fees, total
payouts) are derived by `SUM` over the ledger by entry type — the engine exposes a
`reward_totals()` read function for the UI/mirror; it never stores aggregates.

**Worked examples (normative — the unit tests assert these exact numbers).**

*Example A — MoneroOcean, exact split.* Simulated gross 1,000,000,000,000 piconero
(1 XMR), fee 0 bps → fee 0, net 1,000,000,000,000. ATLAS 250,000,000,000;
users_total 750,000,000,000. Two users, weights 2:1 → user A 500,000,000,000, user B
250,000,000,000. Reconciliation: 0 + 250,000,000,000 + 500,000,000,000 +
250,000,000,000 = 1,000,000,000,000 = gross. ✓

*Example B — SupportXMR fee + dust.* Simulated gross 1,000,000,000,000, fee 60 bps →
fee = 1,000,000,000,000 × 60 // 10,000 = 6,000,000,000; net 994,000,000,000. ATLAS =
994,000,000,000 × 25 // 100 = 248,500,000,000; users_total 745,500,000,000. Three
users, equal weights 1:1:1 → floor 248,500,000,000 each, leftover 0. (For a dust
case, see the unit test: users_total 10, three equal weights → floors 3/3/3, leftover
1 → the lowest `user_id` receives 4, the others 3; Σ = 10. ✓)

*Example C — referral (see §7).* Same as A, plus user B was referred by user C.
Referral = 5% of B's 250,000,000,000 = 12,500,000,000, paid to C from the ATLAS
share. Ledger: fee 0; atlas_share (retained) 237,500,000,000; referral_reward to C
12,500,000,000; user A 500,000,000,000; user B 250,000,000,000. Reconciliation:
0 + 237,500,000,000 + 12,500,000,000 + 500,000,000,000 + 250,000,000,000 =
1,000,000,000,000 = gross. ✓

---

## 5. Ledger — append-only, tamper-evident

### 5.1 Entry fields (exact)

Every ledger row has exactly these columns (Stage 2 schema, §11):

| Column | Type / rule |
|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` — insertion order IS the chain order |
| `created_at` | Unix epoch integer (existing convention) |
| `entry_type` | `CHECK IN ('user_allocation','atlas_share','fee','payout','referral_reward','reversal')` |
| `user_id` | FK to `users(id)`, NULL for `fee` / `atlas_share` entries |
| `amount_piconero` | Signed integer piconero. Sign convention (§5.2) |
| `batch_id` | FK to `reward_batches(id)`, NULL only for entries not tied to a batch (none in M6; every M6 entry belongs to a batch) |
| `reference` | Free-text source reference, e.g. `batch:sim-20261118-001`, `pool-fee:MoneroOcean:sim-20261118-001`, `referral:<referral_id>:batch:<batch_ref>`, `reversal-of:<entry_id>` |
| `mode` | `CHECK IN ('real','simulation')` — copied from the batch; `simulation` in M6 |
| `prev_hash` | Hex SHA-256 of the previous entry's `entry_hash`; genesis entry uses 64 zeros (`'0'*64`) |
| `entry_hash` | Hex SHA-256 of the canonical serialization of this entry (§5.3) |
| `note` | Nullable free text (e.g. "null-difficulty shares: 2; null-external-id excluded: 1") |

**Sign convention.** `amount_piconero` is the amount credited to the named party:
`user_allocation` +X (to the user), `atlas_share` +X (to ATLAS, `user_id` NULL),
`fee` +X (fee magnitude, `user_id` NULL), `referral_reward` +X (to the referrer),
`payout` −X (money leaving a user's balance — NO payout entries exist in M6),
`reversal` −X (negates a prior entry; `reference` names the reversed entry id).
A user's available balance = `SUM(amount_piconero)` over their `user_allocation` +
`referral_reward` + `payout` + `reversal` entries. ATLAS retained =
`SUM(atlas_share)`; pool fees paid = `SUM(fee)`.

**Batch reconciliation invariant (checked by the verifier, §5.4):** for every settled
batch,
`fee + atlas_share(retained) + referral_total + Σ user_allocations = gross_piconero`,
where each term is the sum of that batch's entries of that type. If it does not hold,
the chain is broken and the batch must be investigated — never silently adjusted.

### 5.2 No updates, no deletes — corrections are reversals

- After a ledger transaction COMMITs, no row in `ledger` is ever UPDATEd or DELETEd.
  The engine exposes no update/delete function for the ledger. (The single exception
  is mechanical, inside the settle transaction itself: a row is INSERTed with
  `prev_hash`/`entry_hash` NULL, then UPDATEd with its computed hash in the SAME
  transaction before COMMIT — because `id` is only known after INSERT. No committed
  row is ever modified afterwards. See §5.3.)
- A wrong entry is corrected by TWO new entries in a later batch (or a standalone
  correction record): a `reversal` entry (−X, `reference = "reversal-of:<entry_id>"`,
  same `batch_id` as the correction context) followed by a fresh corrected entry of
  the proper type. The original entry stays in the chain, visible, forever.
- The `decisions` table carries the audit narrative (`dept='rewards'`, §9); it never
  substitutes for a ledger entry.

### 5.3 Hash chain — exact construction

For entry `n` (in `id` order):

```
prev_hash(n) = entry_hash(n-1), or '0'*64 for the first entry (genesis)
payload(n)   = canonical JSON of {
                 "id": n, "created_at": created_at, "entry_type": entry_type,
                 "user_id": user_id, "amount_piconero": amount_piconero,
                 "batch_id": batch_id, "reference": reference,
                 "mode": mode, "note": note, "prev_hash": prev_hash(n) }
               with keys sorted, separators (',', ':'), no whitespace,
               JSON null for NULL values
entry_hash(n) = hex( SHA-256( payload(n) encoded UTF-8 ) )
```

SHA-256 is `hashlib.sha256` (stdlib — the coordinator is stdlib-only and the engine
must be too). Deterministic entry order inside a settle transaction (required, because
the chain order is the audit order): `fee` first, then `atlas_share`, then
`referral_reward` ordered by referrer `user_id`, then `user_allocation` ordered by
`user_id`. The `prev_hash` of the first entry of a batch is the `entry_hash` of the
last entry of the previous batch (or genesis zeros for the very first entry) — the
chain is global across batches, not per-batch.

This chain is tamper-EVIDENT, not tamper-proof: editing any committed row breaks every
subsequent hash unless the attacker recomputes the whole tail — which the verifier
(§5.4) detects by recomputation. State this honestly in the UI copy: "tamper-evident
ledger", never "tamper-proof" or "blockchain-secured".

### 5.4 How a reader verifies the chain (procedure)

A `verify_chain()` function (read-only, no writes) that any auditor can run:

1. Read all ledger rows ordered by `id`. Check the `id` sequence has no gaps
   (a gap means a deleted row).
2. For each row in order: recompute `entry_hash` from the canonical payload (§5.3)
   and compare to the stored `entry_hash`; check `prev_hash` equals the previous
   row's `entry_hash` (or 64 zeros for row 1). Any mismatch → FAIL, naming the first
   bad entry id.
3. For each settled batch: recompute fee/net/split/allocations from the batch row and
   the share weights, and check the reconciliation invariant (§5.1). Any mismatch →
   FAIL, naming the batch.
4. Check every `user_allocation`/`referral_reward` entry's user exists and every
   `batch_id` references a settled batch; check no `payout` entries exist while Gate 4
   is closed (in M6: any `payout` row is a FAIL — no payout path exists yet).
5. Report PASS only if all checks pass, with the entry count, batch count, and total
   sums. A PASS on an empty ledger (0 entries — the live state in M6) is a valid
   trivial PASS and must say so ("ledger empty — chain trivially valid, 0 entries").

The build lane adds this as a diagnostics check (new test 23) so the existing suite
catches a future break (§12).

---

## 6. Double-credit prevention

Three independent layers; a double credit requires defeating all three, and layer 3
detects it even then.

**Layer 1 — share dedupe (record time, coordinator, already built).** `UNIQUE INDEX
idx_shares_worker_external ON shares(worker_id, external_id) WHERE external_id IS NOT
NULL` + `INSERT OR IGNORE` (same-worker duplicates skipped and counted) + cross-worker
conflict suspends the worker and rejects the batch. A share id can therefore exist at
most once per worker, and a replayed share id against another worker is a suspension
event, not a credit.

**Layer 2 — batch exactly-once (settle time, this engine).**
- `reward_batches` has `UNIQUE(pool_name, source_ref)`: the same pool reward can
  never be recorded twice. Recording the same `source_ref` again fails the constraint
  (the record-batch function catches it, logs `reward-batch-duplicate-skipped`, and
  inserts nothing).
- `reward_batch_shares` has `UNIQUE(share_id)`: one share belongs to at most one
  batch. The settle query excludes already-linked shares, and the link INSERTs run in
  the same transaction as the ledger entries — a second settle of the same batch
  finds zero unattributed shares and no open batch (status is already `settled`),
  so it is a logged no-op, not a second credit.
- The whole settle (links + ledger entries + batch status flip + decision log) is ONE
  transaction (`BEGIN IMMEDIATE … COMMIT`); any failure rolls everything back and the
  batch stays `open`.

**Layer 3 — payout idempotency keys (for the later payout mission; column added now).**
`payouts.idempotency_key TEXT UNIQUE`. When payouts are built, the key is generated
BEFORE any submission attempt (e.g. `payout:<user_id>:<batch_ref>:<seq>` or a UUIDv4
stored first), and every retry presents the same key: a second row with the same key
fails the constraint and the existing row is returned instead. No payout is ever
created without a key, and no key is ever reused for a different payout. In M6 no
payout code exists and the `payouts` table stays at 0 rows — the column is preparatory
only (§11).

**Detection (backstop).** The §5.4 verifier recomputes allocations from shares and
batches; any share linked to two batches, or any batch settled twice, fails check 3.
The engine also refuses a settle if the pre-check finds a share already linked
(defensive re-check before INSERT, not just reliance on the constraint).

---

## 7. Referrals — funded from the ATLAS 25% only

**Exact rule.** For a settled batch, for each referral row where the referred user
earned an allocation `A > 0` in this batch:

```
referral_reward = A * 500 // 10_000     # 5% of the referred user's allocation, floored
```

- Paid to the referrer (`referrer_user_id`) as a `referral_reward` ledger entry
  (`reference = "referral:<referral_id>:batch:<batch_ref>"`, same `batch_id`).
- Funded entirely from the ATLAS 25%: `atlas_retained = atlas_share −
  referral_total`, where `referral_total = Σ referral_reward`. The users' 75% is
  never reduced — the referred user's allocation `A` is untouched, and no other
  user's allocation is touched.
- The rate is a parameter, not hard-coded: `referral_rate_bps = 500` (5%), to be
  stored in `config/pool-rewards.json` by the build lane (the engine reads it from
  config at settle time; the design does not change config itself). **This rate is a
  user-confirmable parameter** — flag it in the build report for the user to confirm
  or change before any real-mode settlement. In simulation it is fixed at 500 bps.
- **Cap proof (the cap never binds):** `referral_total ≤ 5% × users_total = 5% × 75%
  × net = 3.75% × net < 25% × net = atlas_share`. Referral rewards can never exceed
  the ATLAS share. If the rate were ever raised, the engine must enforce
  `referral_total ≤ atlas_share` as a hard check and refuse to settle a batch that
  violates it (log `reward-batch-referral-cap`, batch stays `open`).
- **Only direct referrals, one level.** No multi-level chains: a referrer's referrer
  earns nothing from this allocation.
- **No self-referral:** `referrer_user_id = referred_user_id` pays 0 (skipped, counted
  in the batch note).
- **No reward for recruitment alone.** A referral pays only when the referred user
  earned a verified allocation in that cycle. A signup with zero shares pays zero.
- **Eligibility is computed per cycle, not stored.** The `referrals.status` column
  (`pending` default, no CHECK) is left as recorded; the engine does not mutate it
  and does not gate payment on it. Payment is driven by verified work in the cycle,
  full stop. (A future mission may define status transitions; this design does not.)
- **When no referrals exist (the live state: 0 rows):** `referral_total = 0`,
  `atlas_retained = atlas_share`, zero `referral_reward` entries, and the UI shows
  "Referral rewards: 0 XMR — no referrals yet" (§10). Nothing is invented, nothing is
  pre-allocated.

---

## 8. Simulation mode — what is simulated, and what is never attempted

- **Mode flag.** `config/pool-rewards.json` `mode` is `simulation-only` and the engine
  reads it fresh on every pass (never cached across passes — same rule as the
  coordinator's `load_configs()`). While it reads `simulation-only`:
  - Real-mode batches are REFUSED at record time (`reward-batch-refused`, decision
    logged, nothing inserted) and at settle time (a real-mode row can never exist in
    this mode; if one somehow does, settle refuses it).
  - Simulation-mode batches settle normally (D-M6-7 exemption: the stop stays ON and
    simulation still runs, because it moves no real value).
- **Simulated pool rewards.** Injected by the test harness as `reward_batches` rows
  with `mode='simulation'`, `batch_ref` prefixed `sim-`, `source_evidence` naming the
  harness run. There is no live pool fetch behind them. The harness reward is a
  chosen test figure (e.g. exactly 1 XMR — see §12), not a market observation.
- **Local-test shares in simulation.** The simulation fixture registers users/workers
  on a TEMP DB and records `origin='local-test'` shares with known difficulties via
  the coordinator's `record_share(..., local_test=True)` path (which requires the
  `local-test:` external-id prefix). The settle query for a simulation batch filters
  `origin='local-test'`; the identical code path with `origin='pool'` is exercised by
  the unit tests with fixture pool shares on the temp DB.
- **Marking (everywhere, no exceptions).** Every simulation-derived figure carries
  its mark: DB rows (`reward_batches.mode='simulation'`, `ledger.mode='simulation'`),
  the coordinator-export/ UI data (`mode: "simulation-only"`), and the UI itself
  (SIMULATION tags on the split panel, the ledger table, and every balance — §10).
  The word "earned" must not appear next to a simulated figure without the SIMULATION
  qualifier; simulated balances are test data, not earnings.
- **All figures 0 / simulation-labelled until real data exists.** Live state today: 0
  users, 0 workers, 0 shares, 0 ledger rows. The live UI therefore shows honest
  zeros (§10). The simulation lives on a temp DB (D-M6-11) and its figures never
  enter the live DB or the live UI.
- **NO payout attempt.** No payout code path exists in Mission 6. The `payouts` table
  stays at 0 rows; `minimum_payout` stays null/placeholder (undecided — flag for the
  user, do not decide it here). **Gate 4 restated:** a real payout requires explicit
  user authorization + successful security testing + a treasury design. None exists.
  The engine must refuse any payout-shaped call with a logged refusal, not a silent
  no-op.

---

## 9. Reward cycles — open/close, triggers, and the coordinator cron

**What a cycle is.** One cycle = one reward batch (`reward_batches` row). A cycle has:
a pool, a mode, a source reward, an attribution window `[window_start, window_end)`,
and a lifecycle `open → settled` (or `open` held indefinitely, §9.3).

**Opening a cycle.** A cycle opens when a batch is RECORDED — by the operator/harness
CLI (`record-batch`), never by the engine itself. Recording requires: a pool named in
`config/pool-rewards.json`, a `source_ref` unique for that pool, `gross_piconero > 0`,
a window with `window_end > window_start` that does not overlap any existing batch's
window for the same pool (checked by query; overlap → record refused, decision
logged), and `fee_bps` copied from config at record time. Windows are contiguous by
convention (each new `window_start` = the previous batch's `window_end` for that pool)
but contiguity is NOT enforced — gaps are allowed (e.g. a period with no pool reward);
overlaps are forbidden. The first batch's `window_start` is the reward period start
supplied with the batch (in simulation, the harness supplies it; never default to 0
silently — the record-batch call requires both bounds explicitly).

**Closing a cycle.** A cycle closes when the engine SETTLES it, in one transaction:
compute fee/net/split/allocations/referrals from the recorded batch + the shares in
its window (§2–§4, §7); insert `reward_batch_shares` links; insert ledger entries in
deterministic order (§5.3); flip the batch to `settled` with `settled_at`; log
`reward-batch-settled` (`dept='rewards'`) with the full arithmetic in the reason
string (gross, fee, net, ATLAS, users_total, referral_total, shares attributed,
excluded counts). Any failure rolls the whole transaction back; the batch stays `open`
and a `reward-batch-failed` decision is logged in a separate transaction.

**What triggers an engine pass.** Two triggers, same function:
1. **The 10-min coordinator cron (primary, live).** `run_pass()` in
   `core/atlas_coordinator.py` gains ONE guarded sub-step after the pool poll:
   `reward_engine.settle_due_batches(con)` — "due" = a batch with status `open`
   whose mode is allowed (simulation always; real only if config mode is not
   `simulation-only` AND the emergency stop is off). The call is wrapped so an engine
   exception logs `reward-pass-failed` and NEVER fails the coordinator pass (pool
   polling, session expiry, and the export must continue). On the live DB in M6
   there are no batches, so this step is a no-op that reports `{"batches_due": 0}` in
   the pass summary. **No new cron, no duplicated schedule** (D-M6-8).
2. **On-demand CLI (simulation + operations).** `python3 core/reward_engine.py settle
   [--batch-ref <ref>]` settles one named batch or all due batches; `verify-chain`
   runs §5.4; `status` prints batch/ledger totals (derived, read-only). The CLI is how
   the simulation test drives settlement on the temp DB (§12).

**Held batches (§9.3).** A due batch is NOT settled — it stays `open`, no ledger
entries are written, and a decision is logged — when: total eligible weight is 0
(D-M6-10: nothing to attribute; never auto-allocate to ATLAS); `gross_piconero` is 0
(nothing to distribute); the batch is real-mode while the stop is ON or config mode
is `simulation-only` (D-M6-7); or the referral cap check fails (§7). A held batch is
retried on the next pass; it is not an error and not a failure — the decision reason
must say why it is held.

**Decisions the engine logs (`dept='rewards'`, all with a reason naming the
evidence):** `reward-batch-recorded`, `reward-batch-duplicate-skipped`,
`reward-batch-refused` (real mode while simulation-only / stop ON), `reward-batch-settled`
(full arithmetic in the reason), `reward-batch-held` (reason names the cause),
`reward-batch-failed` (reason names the error, no secrets), `reward-pass-failed`
(engine exception inside a coordinator pass), `reward-chain-verified` (verifier result,
entry + batch counts). The existing `decisions` table needs no schema change.

---

## 10. UI section requirements — Mining tab (no new tab)

**Placement.** A "Reward accounting — Master Mission 6" section in the existing Mining
tab, directly BELOW the Coordinator section and ABOVE Settings (current tab order,
Mission 5 §3d — keep unchanged: MiningDashboard, WalletCenter, EarningsSection,
HistorySections, PayoutSection, CalculatorSection, MinerPrototypeSection,
CoordinatorSection, **[RewardAccountingSection]**, SettingsSection, HelpSection). No new
tab, no new card outside the Mining tab. The section contains ZERO buttons, inputs,
or links that move money (same rule as the Coordinator section): no "claim", no
"withdraw", no "settle now" control. Request-payout stays in the existing Payout
center, hard-disabled (Mission 2).

**Panels (exact content).**
1. **Reward split — 75 / 25.** The split rule in one line, then the live derived
   totals: total user rewards, total ATLAS share, total pool fees, total referral
   rewards, total payouts — all from `SUM` over the mirrored ledger, all 0 XMR today.
   Each figure carries a provenance tag (RECORDED for ledger sums; SIMULATION while
   mode is simulation-only).
2. **Methodology (verbatim, short).** "Rewards come only from confirmed pool payouts,
   never from estimated hashrate. The pool fee is deducted first. 75% goes to miners
   by verified accepted shares; 25% to ATLAS. Referral rewards come from the ATLAS 25%
   only. All amounts in XMR (1 XMR = 10¹² piconero). Simulation only — no real
   earnings yet." No guaranteed-profit language anywhere; no "earn $X/day" copy.
3. **Ledger table.** Mirrored host ledger rows (newest first): date, type, user (or
   "ATLAS" / "Pool fee"), amount XMR, batch ref, mode tag. Empty state (the live
   state): "No reward entries yet — simulation only, 0 workers, 0 shares." A
   SIMULATION tag on every simulation row; a tamper-evident note ("each entry links
   to the previous entry's hash — see the design doc").
4. **Referrals line.** "Referral rewards: 0 XMR — no referrals yet." (When referrals
   exist: total paid from the ATLAS 25%, never from the users' 75%.)
5. **Honest zero state (today).** All balances 0 XMR; the section header states
   "SIMULATION ONLY — no pool rewards, no workers, no shares". Estimates (calculator)
   are never shown here and never added to any balance.

**Data path.** Host is the system of record (D-M6-1). The existing mirror pattern is
extended, not reinvented: `getMining` gains a `rewards` block (mode, split totals,
batch list, ledger entries, referral total); the ingest action that mirrors
`coordinator.json` (Mission 5's `ingestCoordinatorState`) is extended to mirror the
host ledger + batch rows into the artifact's `mining_ledger` / new `mining_reward_batches`
mirror tables, deduped on host ledger id / host batch id. Re-ingest of unchanged data
reports "already up to date". **No hashes, tokens, or secrets are ever mirrored**
(M5 D4 carried) — entry hashes ARE mirrored: they are public audit data, not secrets.
Mirror staleness: if the underlying snapshot/export is stale (> 1 h, or the refresh
failure in §0 applies), the section labels its data STALE rather than presenting it
as fresh — never silently show a stale ledger as current.

**Rendered verification owed (build lane).** A fresh interactive audit must select the
Mining tab on desktop + mobile on the new build, scroll to the Reward accounting
section, and capture it — the Missions 2–5 gap (no captured Mining-tab render on the
current build) must not be repeated for this section. The audit checks: all five
panels present, all zeros honest, SIMULATION tags visible, no console errors, mobile
overflow 0 at 390 px.

---

## 11. Data rules — prefer existing tables; the migration that IS needed

**Preferred: existing tables, unchanged.** `shares` (attribution source — no new
columns; the link table covers batch membership), `pool_stats` (context only, no
engine use), `decisions` (audit narrative, new `dept='rewards'`), `users`/`workers`
(mapping, unchanged), `referrals` (read-only for the engine; eligibility computed per
cycle, §7). The engine reads `config/pool-rewards.json` for fees, split, mode, and
the referral rate — it writes no config.

**Migration REQUIRED — Stage 2 (`core/migrate_mission6_stage2.sql`, `user_version`
2 → 3).** The design proves one is needed, for three reasons that cannot be met any
other way:
1. **Tamper-evidence needs new columns.** The Stage 0 `ledger` has no hash-chain
   columns (`prev_hash`, `entry_hash`), no `batch_id`, and no `mode`. A chain cannot
   be verified without them.
2. **Referrals and reversals need new entry types.** The Stage 0 `entry_type` CHECK
   allows only `user_allocation/atlas_share/fee/payout`. SQLite cannot ALTER a CHECK —
   the table must be rebuilt to add `referral_reward` and `reversal`.
3. **Exactly-once needs new tables + a key.** `reward_batches` (with
   `UNIQUE(pool_name, source_ref)`) and `reward_batch_shares` (with
   `UNIQUE(share_id)`) have no existing home; `payouts` has no idempotency key column.

Exact DDL (normative — the build lane implements this, in one transaction, after
backing up `data/atlas.db` to `backups/atlas-YYYY-MM-DD-pre-mission6.db` and verifying
integrity before and after):

```sql
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS reward_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_ref TEXT NOT NULL UNIQUE,              -- 'sim-YYYYMMDD-NNN' or 'pool-<pool>-<pool_ref>'
    pool_name TEXT NOT NULL,                     -- must name a pool in pool-rewards.json
    mode TEXT NOT NULL CHECK (mode IN ('real','simulation')),
    source_ref TEXT NOT NULL,                    -- pool's own payout/credit reference
    source_evidence TEXT,                       -- how confirmed (API ref/txid, or 'simulated-harness:<id>')
    window_start INTEGER NOT NULL,
    window_end INTEGER NOT NULL CHECK (window_end > window_start),
    gross_piconero INTEGER NOT NULL CHECK (gross_piconero >= 0),
    fee_bps INTEGER NOT NULL,                    -- copied from config at record time
    fee_piconero INTEGER NOT NULL DEFAULT 0,
    net_piconero INTEGER NOT NULL DEFAULT 0,
    atlas_share_piconero INTEGER NOT NULL DEFAULT 0,
    users_total_piconero INTEGER NOT NULL DEFAULT 0,
    referral_total_piconero INTEGER NOT NULL DEFAULT 0,
    shares_count INTEGER NOT NULL DEFAULT 0,
    null_difficulty_count INTEGER NOT NULL DEFAULT 0,
    null_external_id_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','settled','held')),
    created_at INTEGER NOT NULL,
    settled_at INTEGER,
    UNIQUE (pool_name, source_ref)
);

CREATE TABLE IF NOT EXISTS reward_batch_shares (
    batch_id INTEGER NOT NULL REFERENCES reward_batches(id),
    share_id INTEGER NOT NULL REFERENCES shares(id),
    PRIMARY KEY (batch_id, share_id),
    UNIQUE (share_id)                            -- one share, at most one batch
);
CREATE INDEX IF NOT EXISTS idx_rbs_batch_id ON reward_batch_shares(batch_id);

-- Ledger rebuild: new entry types + hash-chain/batch/mode columns.
-- Live ledger is EMPTY (0 rows), so this copies zero rows — zero data risk.
CREATE TABLE ledger_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type TEXT NOT NULL
        CHECK (entry_type IN ('user_allocation','atlas_share','fee','payout',
                              'referral_reward','reversal')),
    user_id INTEGER REFERENCES users(id),
    amount_piconero INTEGER NOT NULL,
    reference TEXT,
    created_at INTEGER NOT NULL,
    batch_id INTEGER REFERENCES reward_batches(id),
    prev_hash TEXT,
    entry_hash TEXT,
    mode TEXT NOT NULL DEFAULT 'simulation' CHECK (mode IN ('real','simulation')),
    note TEXT
);
INSERT INTO ledger_new (id, entry_type, user_id, amount_piconero, reference, created_at,
                        batch_id, prev_hash, entry_hash, mode, note)
    SELECT id, entry_type, user_id, amount_piconero, reference, created_at,
           NULL, NULL, NULL, 'simulation', NULL FROM ledger;
DROP TABLE ledger;
ALTER TABLE ledger_new RENAME TO ledger;
CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_entry_hash ON ledger(entry_hash)
    WHERE entry_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ledger_user_id ON ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_ledger_created_at ON ledger(created_at);
CREATE INDEX IF NOT EXISTS idx_ledger_batch_id ON ledger(batch_id);

ALTER TABLE payouts ADD COLUMN idempotency_key TEXT UNIQUE;   -- preparatory; no payouts in M6

PRAGMA user_version = 3;
COMMIT;
```

**Notes for the build lane.** Rebuild order matters: `reward_batches` must exist before
the new `ledger` references it. The `INSERT … SELECT` maps the four legacy entry types
unchanged (they are a subset of the new CHECK) and defaults `mode='simulation'` for
the zero existing rows. `journal_mode` stays `delete` in this mission (WAL is a
separate, deferred decision from Mission 1). The artifact mirror needs a matching
drizzle migration (new `mining_reward_batches` table + the new ledger columns on
`mining_ledger`) — additive only, same pattern as Mission 5's `0005` migration.

---

## 12. Test plan

All tests run against a TEMPORARY database (fresh schema at `user_version` 3, fixture
data inserted by the test file) — never the live DB (D-M6-11). Stdlib only (`unittest`,
same pattern as Mission 5's `core/test_atlas_coordinator.py`, 18/18). The test file is
`core/test_reward_engine.py`, preserved in the repo.

### 12.1 Unit tests (each: name → what "pass" means)

1. **Fee arithmetic.** Gross 1,000,000,000,000 at 0 bps → fee 0; at 60 bps → fee
   exactly 6,000,000,000; at 100 bps on gross 1 → fee 0 (floor), remainder stays in
   net. PASS: exact integers, no floats anywhere (assert `type(x) is int`).
2. **Split exactness.** Net 1,000,000,000,000 → ATLAS 250,000,000,000,
   users_total 750,000,000,000. Net 1,000,000,000,001 → ATLAS 250,000,000,000,
   users_total 750,000,000,001 (remainder to users). PASS: `atlas + users == net`.
3. **Largest-remainder allocation.** users_total 10, three users equal weight → 4/3/3
   with the +1 going to the lowest `user_id`; users_total 745,500,000,000, weights
   2:1:1 → 372,750,000,000 / 186,375,000,000 / 186,375,000,000. PASS: Σ allocations
   == users_total exactly, every allocation within 1 piconero of its exact share.
4. **Attribution weights.** Fixture: user A 2 pool-accepted shares (difficulty 10, 20),
   user B 1 pool-accepted share (difficulty 5), plus 1 pool-REJECTED share (difficulty
   999), 3 local-test shares (difficulty 999), 1 pool-accepted share with NULL
   difficulty, 1 pool-accepted share with NULL `external_id`. PASS: weights A=30, B=5,
   NULL-difficulty share counted weight 1 and flagged, NULL-external-id share
   excluded and counted, rejected/local-test shares weight 0.
5. **Share→worker→user mapping.** A user with two workers has weights summed across
   both. PASS: per-user totals correct, no worker double-counted.
6. **Batch exactly-once.** Record batch X, settle it, settle it again. PASS: second
   settle is a logged no-op; ledger entry count unchanged; batch still `settled`.
   Record the same `(pool_name, source_ref)` again. PASS: refused, one batch row only.
7. **Share double-credit.** Settle batch 1 over window W, then record batch 2 with an
   overlapping window and settle. PASS: shares linked to batch 1 are excluded from
   batch 2 (overlap record is refused in any case — §9 — but the settle also excludes
   them; test both layers).
8. **Ledger chain.** Settle two batches, then run `verify_chain()`. PASS: PASS verdict,
   entry count and sums reported. Then tamper: UPDATE one committed amount in the TEMP
   DB directly. PASS: `verify_chain()` FAILs naming the first bad entry id. Then add
   a `reversal` + corrected entry. PASS: balances correct again and the chain verifies
   (the tampered entry stays visible in history — the test asserts it is still there).
9. **Reconciliation invariant.** For each settled batch: fee + retained ATLAS +
   referral_total + Σ user allocations == gross. PASS: exact equality, every batch.
10. **Referrals.** Fixture: referrer C, referred user B (allocation 250,000,000,000),
    rate 500 bps → referral exactly 12,500,000,000 to C, ATLAS retained reduced by
    exactly that, B's allocation unchanged. Self-referral fixture → 0. No-referral
    fixture → referral_total 0, zero referral entries. PASS: exact integers + the
    cap inequality `referral_total ≤ atlas_share` holds.
11. **Mode gates.** With config mode `simulation-only`: record a real-mode batch →
    refused; settle a real-mode row smuggled into the temp DB → refused. Emergency
    stop ON + real-mode batch → refused (`reward-batch-held`/`refused`). Simulation
    batch with stop ON → settles (D-M6-7). PASS: refusals logged with reasons, zero
    real-mode ledger entries.
12. **Held batches.** Batch with gross > 0 but zero eligible shares → stays `open`,
    zero ledger entries, `reward-batch-held` logged. Batch with gross 0 → held.
    PASS: no allocation invented, no ATLAS auto-credit.
13. **Payout idempotency (column only).** Insert two payout rows with the same
    `idempotency_key` on the temp DB. PASS: second insert fails the UNIQUE constraint.
    (No payout flow exists to test end-to-end — Gate 4.)
14. **Window rules.** Record a batch overlapping an existing batch's window → refused.
    Record a batch with `window_end ≤ window_start` → refused. PASS: one batch row in
    each case, refusal logged.
15. **Balances derived.** After settling, user balance = `SUM` over ledger entries;
    recompute independently in the test from the entries. PASS: derived balance equals
    the expected allocation + referral rewards − 0 payouts; no stored-balance column
    exists to drift.
16. **No floats, no estimates in the engine.** Grep the engine module for `float(`
    and for any read of `reported_hashrate_hps` / calculator output. PASS: zero hits.
    (Static check, run in the test file.)

### 12.2 Simulation (temp DB, end-to-end — the Mission 6 acceptance run)

Fixture (temp DB, `user_version` 3): 2 users (Alice, Bob), 3 workers (Alice/browser,
Alice/desktop, Bob/desktop), 8 local-test shares with known difficulties (Alice 60
weight, Bob 40 weight) + 1 simulated MoneroOcean reward batch, gross exactly
1,000,000,000,000 piconero (1 XMR), window covering the fixture shares, referral:
Bob referred by Alice.

Expected outcome (asserted exactly): fee 0; net 1,000,000,000,000; ATLAS share
250,000,000,000; users_total 750,000,000,000; Alice allocation 450,000,000,000;
Bob allocation 300,000,000,000; referral to Alice = 5% × 300,000,000,000 =
15,000,000,000; ATLAS retained 235,000,000,000; Alice's total balance 465,000,000,000;
Bob's 300,000,000,000. Ledger entries: 1 fee (0) + 1 atlas_share + 1 referral_reward
+ 2 user_allocation = 5 entries, hash chain verifies, reconciliation holds. Every
entry `mode='simulation'`; batch `mode='simulation'`; UI copy (if rendered against
this fixture) shows SIMULATION tags. A second run re-settles nothing (idempotent).

Second scenario (same fixture shape, SupportXMR 60 bps, 3 users, dust): assert the
Example B numbers (§4) and a 1-piconero dust distribution to the lowest `user_id`.

**"Pass" for the mission:** all unit tests pass, both simulation scenarios produce
the exact expected integers, `verify_chain()` passes, the live DB is untouched
(0 ledger rows, `user_version` still 2 until the build lane's migration — the design
does not migrate anything), diagnostics 22/22 still pass, and safety is unchanged
(stop ON, mining disabled, paper-only, $0). The build lane adds diagnostics test 23
(ledger hash-chain verification on the live DB — trivially PASS on an empty ledger)
so the suite guards the chain from here on.

### 12.3 What is NOT tested in this mission

- Gate 1 (measured hashrate) — the engine does not use hashrate; no probe run.
- Gate 2 (real pool accepted shares) — no pool connection for earning; no share
  submission. The `origin='pool'` settle path is tested only with fixture rows on a
  temp DB.
- Gate 4 (real payout) — no payout flow, no treasury, no transaction. The
  idempotency column is tested at the constraint level only (§12.1.13).
- Rendered Mining-tab check on the current build — owed by the build lane's audit
  (§10); this design does not claim it.

---

## 13. What the engine does NOT do (hard limits restated for the build lane)

- No real pool rewards, no real payouts, no pool connection for earning, no share
  submission to any pool, no wallet or key creation, no spending, no config changes
  (the build lane writes `referral_rate_bps` into `config/pool-rewards.json` as the
  ONE config addition this design specifies — everything else in config is untouched),
  no lifting the emergency stop, no mining activation, no workers active.
- No price conversion: the ledger is XMR piconero only. Any USD display is an
  ESTIMATE from a price feed, labelled as such, and never enters the ledger.
- No repair of the refresh failure (Mission 3 finding 1) or the stale "no miner yet"
  copy (Mission 4 finding 4). Both are noted in §0 only.
- No interactive probe run. No changes to `core/atlas_coordinator.py` except the one
  guarded `settle_due_batches()` sub-step call in `run_pass()` (§9) — and that call
  must never fail the pass.
- No new cron job, no new tab, no new refresh schedule, no artifact→host write path,
  no token/session/password hash mirrored or stored.

## 14. Open items / questions for the user (decisions still owed, not decided here)

1. **Referral rate 5% (500 bps)** — the design's parameter (§7). Confirm, or name a
   different rate, before any real-mode settlement. It is changeable in config; the
   engine never hard-codes it.
2. **Minimum payout** — still null/placeholder (Mission 2). Undecided; needed before
   any payout flow is designed. All balances stay pending until it is set.
3. **Per-miner pool reward endpoint** — unverified. Real-mode batch recording needs
   the verified endpoint (MoneroOcean per-wallet/miner accounting) — a future mission,
   never guessed (cf. D-M5-3 for SupportXMR stats).
4. **SupportXMR stats-API URL** — still owed (D-M5-3). The engine does not need it
   (it reads the fee from config, not from pool stats), but the coordinator's fallback
   still does.
5. **Treasury design + Gate 4** — none exists. No real payout until authorized +
   security-tested + treasury-designed.

## Appendix A — Files the build lane creates (no files are created by this design)

- `core/reward_engine.py` (new, stdlib only) — `record_batch`, `settle_batch`,
  `settle_due_batches`, `verify_chain`, `reward_totals`, `balances`, CLI
  (`settle | verify-chain | status | record-batch`).
- `core/migrate_mission6_stage2.sql` (new) — §11 DDL, `user_version` 2 → 3, backup
  first, one transaction.
- `core/test_reward_engine.py` (new) — §12 tests, temp DB only, preserved in repo.
- `client/src/RewardAccounting.tsx` (new) + `Mining.tsx` wiring (section below
  Coordinator) + `getMining` rewards block + mirror ingest extension + drizzle
  migration `0006` (mirror tables/columns, additive only).
- `docs/master-mission6-report-2026-11-18.md` (new) — build report, with the rendered
  Mining-tab audit (§10) and the simulation evidence (§12.2).
- Config addition (one key, by the build lane): `referral_rate_bps: 500` in
  `config/pool-rewards.json`.

## Appendix B — Sources

- Mission 1 report §6 (accounting basis); Mission 2 report + `config/pool-rewards.json`
  (fees, split, simulation-only, ledger rules); Mission 5 design D1–D10 + coordinator
  source (share dedupe, attribution query shape, `run_pass` structure, decision
  conventions); Mission 3/4 reports (known issues carried, not fixed); live DB schema
  and counts read 2026-11-18 (see §0).
