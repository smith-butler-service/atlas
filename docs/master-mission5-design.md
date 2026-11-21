# ATLAS — Master Mission 5: Coordinator — Design

**Mission:** Master Mission 5 — Coordinator (worker registry, share accounting, pool stats, sessions, coordinator state + UI)
**Date:** Wednesday, 2026-11-18
**Lane:** A (design) — **DESIGN ONLY. Nothing was built, edited, activated, or connected.**
**Status:** DESIGN ONLY. No code, no migration, no config change, no database write, no artifact change was made by this lane. The build lane implements from this document; it does not improvise around it.
**Authoritative inputs:** `docs/master-mission1-inspection-report-2026-11-18.md` (75/25 accounting basis, payout gate, browser-mining verdict, 5 prototype gates), `docs/master-mission2-report-2026-11-18.md` (Stage 0 schema, Mining tab, artifact `mining_*` tables), `docs/master-mission3-report-2026-11-18.md` (wallet center, refresh failure), `docs/master-mission4-report-2026-11-18.md` + `docs/master-mission4-design.md` + `docs/master-mission4-desktop-xmrig-design.md` (browser prototype, local-test relay, desktop XMRig design, worker name + per-worker token, status lifecycle), `core/migrate_mission2_stage0.sql`, `config/atlas.json`, `config/pool-rewards.json`.

## Labelling convention

Every figure in this document carries one of three labels, following the Mission 1 / Mission 4 discipline:

- **VERIFIED** — measured or confirmed against a live source, the live host, or an official document cited here.
- **ESTIMATE** — computed from verified inputs with stated assumptions; a projection, not a measurement.
- **ASSUMPTION** — a design choice or an unconfirmed property; the build/test lanes must verify it before relying on it.

No figure in this document is a promise of earnings. Realized mining revenue remains **$0**.

## Safety state at design time (VERIFIED 2026-11-18 ~04:20 EST, read-only checks)

- `emergency_stop`: **true**; `mining.enabled`: **false** (design-only); `trading.mode`: **paper-only**, `eligible_capital_usd`: **0**.
- `config/pool-rewards.json`: mode **simulation-only**; primary pool MoneroOcean, 0% fee; fallbacks SupportXMR 0.6%, P2Pool 0%; 75/25 split on confirmed pool rewards only; minimum payout still null/placeholder.
- Live host DB `~/workspace/atlas/data/atlas.db`: `user_version` 1, integrity ok; all 9 Stage 0 tables at **0 rows** (users 0, workers 0, shares 0, pool_stats 0, sessions 0); `decisions` 68 rows. No demo data exists anywhere.
- Latest snapshot: mining `disabled`, trading `disabled-paper-only`, emergency_stop true.
- **Gate 1 is UNMEASURED.** The Mission 4 prototype has no measured hashrate anywhere — no `?atlas-miner-test=1` load and no probe call exist in any captured evidence. This design **does not fabricate hashrate data and does not run the interactive probe**. Every hashrate figure in the UI reads **"not measured"** until a real probe measurement exists (see §7).

## 0. Design decisions at a glance

| # | Decision | Rationale (one line) |
|---|---|---|
| D1 | Host module is the **system of record**; artifact tables are a **read-only display mirror** | The artifact server cannot read the host SQLite DB; only the host can be authoritative for money-adjacent records |
| D2 | Sync bridge is the **existing snapshot ingest pipeline**, extended with a `coordinator.json` payload | Reuses the proven, deduped, tracked round-trip pattern instead of inventing a second channel |
| D3 | **No artifact→host write path in this mission** — no registration form that writes to the mirror only | A mirror write that looks like a registration would be a false record; registration stays host-side until a real API exists |
| D4 | Token hashes, session token hashes, and password hashes live **only in the host DB, never in the artifact DB** | The website database must never become a credential store |
| D5 | Shares live in **one `shares` table with an `origin` column** (`pool` vs `local-test`); reward attribution queries filter `origin='pool' AND accepted=1` only | One table, one query path, and local-test shares can never leak into earnings by forgetting a join |
| D6 | A worker is `active` **only after pool-accepted shares** for its wallet + worker name; local hashrate never activates a worker | Mission 4 §5.4 + the VoltMiner rounding-mode bug: local metrics can look perfect while every share is invalid |
| D7 | Pool stats are a **read-only public-API fetch** (GET only, no auth, no submission) | Reading `/pool/stats` is not a pool connection for earning |
| D8 | Coordinator state is **derived, not stored as a second truth** — computed from the Stage 0 tables + config at export time | No drift between the state the UI shows and the rows it is computed from |
| D9 | Every coordinator decision is logged to the existing **`decisions` table** with `dept='coordinator'` | Reuses the audit trail that already exists; no new decisions table |
| D10 | The coordinator **never starts, stops, or throttles mining** in this mission; Start/Stop stay hard-disabled | Activation is a separate authorization (Mission 4 gates 2/4 boundary) |

---

## 1. Where the coordinator lives

### 1.1 Decision (D1 + D2)

The coordinator is a **host-side Python stdlib-only module** operating directly on the Stage 0 tables in `~/workspace/atlas/data/atlas.db`:

- **New module (build lane creates):** `core/atlas_coordinator.py` — stdlib only (`sqlite3`, `json`, `urllib`, `hashlib`, `secrets`, `time`, `os`), same portability contract as `core/atlas_monitor.py` and `core/atlas_core.py`. It extends the `atlas_core.py` skeleton (config load, `log_decision`, `status` CLI pattern) — it does not replace it.
- **Authoritative store:** the host DB tables `users`, `workers`, `shares`, `ledger`, `payouts`, `referrals`, `achievements`, `pool_stats`, `sessions`, plus the existing `decisions` table for the audit trail. All money stays integer piconero (1 XMR = 10¹² piconero); all timestamps stay Unix epoch integers — the existing conventions.
- **The artifact server is a display mirror only.** The Command Center artifact (`atlas-command-center`) cannot read the host SQLite DB directly, and this design does not give it that access. The UI reads **only** the artifact's own drizzle `mining_*` tables (`mining_workers`, `mining_shares`, `mining_pool_stats`, `mining_sessions`, `mining_ledger`, `mining_users`, `mining_payouts`, `mining_referrals`, `mining_achievements` — created by Mission 2 migration `0004_mining_data_model.sql`, all 0 rows today).

### 1.2 How host state and artifact tables stay consistent

The bridge is the **existing snapshot ingest pipeline**, extended — not a new channel:

```
Host (system of record)                          Artifact (display mirror)
─────────────────────────                        ─────────────────────────
atlas.db (Stage 0 tables)                        drizzle mining_* tables
        │                                                ▲
        │ coordinator export (atomic write)              │ ingestCoordinatorState
        ▼                                                │ (new server action)
data/coordinator.json ──► refreshAtlasData ───────────────┘
        (same tracked round-trip as snapshot.json:        getMining reads
         started/baselineTs/landedTs/failed,               mirror tables only
         5 s polling, 5-min honest timeout)
```

Concretely:

1. The coordinator writes `data/coordinator.json` by **atomic write** (`.tmp` → `os.replace`), the same pattern as the monitor daemon's `snapshot.json` write. The file is a **derived export**, not a second database: it is computed from the Stage 0 tables + `config/atlas.json` + `config/pool-rewards.json` at export time (D8). If the file is deleted, it is regenerated from the DB with no loss.
2. The existing `refreshAtlasData` flow ingests it alongside `snapshot.json` via a new server action `ingestCoordinatorState` (build lane, later mission — this design only specifies its contract, §1.4). Ingest **dedupes on natural keys** (the Mission 1.1 pattern): workers on host worker `id`, shares on `(worker_id, external_id)` / host share `id`, pool_stats on `(pool_name, recorded_at)`, sessions on host session `id`. Re-ingesting the same export is a no-op and must be reported as "already up to date", never as a fresh sync (see the refresh-failure known issue, §8.1 — the same mislabelling defect must not be repeated for coordinator data).
3. The UI (`getMining` and the new Coordinator section, §7) reads **only** the artifact `mining_*` tables. It never reads the host DB, never calls the pool API from the browser, and never computes balances from anything but stored mirror rows.
4. **Sync direction is host → artifact only, in this mission (D3).** There is no artifact → host write path. Consequences, stated plainly so the build lane does not invent one:
   - Worker registration is performed **host-side** (CLI, §4.5) in this mission. The UI shows registration status and explains that registration opens in a later mission — it does **not** present a registration form whose submit would write only to the mirror and look like a registration.
   - Token issuance happens host-side only. The token is shown **once** by the host CLI; it is never rendered in the UI, never stored in the artifact DB, and never placed in a URL or a log line (Mission 4 §5.2).
   - A future mission that wants in-browser registration must add a real, authenticated host-side API endpoint first (design owed then, not now) — it must not be faked by writing intents into the mirror.

### 1.3 What the coordinator module does (and does not do)

**Does (simulation-only scope):**

- `register_worker(user_id, worker_type, name)` — validate, issue token, store salted hash, status `registered`.
- `record_worker_session(worker_id, kind, …)` — open/close worker sessions (§5).
- `record_shares(worker_id, shares[])` — insert local-test and (later, authorized) pool shares with dedupe (§3).
- `verify_worker_active(worker_id)` — poll the pool API for the wallet + worker pair; move `registered` → `active` only on pool-accepted shares (§4.4). **In this mission this function exists but its activation path is gated: with no pool connection authorized, it always records "not verified — no pool connection" and never activates a worker.**
- `poll_pool_stats()` — read-only GET of MoneroOcean `/pool/stats` (+ fallbacks, §4), insert one `pool_stats` row per poll.
- `coordinator_status()` — derive the coordinator state object (§6) from tables + config.
- `export_coordinator_json()` — write `data/coordinator.json` atomically.
- `decide()` / CLI — one coordination pass + `status` command, mirroring `atlas_core.py` (§6.3).

**Does not do (hard boundaries, same as Missions 1–4):**

- No pool connection for earning, no stratum client, no share submission to any pool.
- No real payout, no treasury access, no transaction signing, no minimum-payout change (still null/placeholder).
- No mining start/stop/throttle on any host, including the Muse VM host. No miner process is spawned.
- No wallet/key/seed creation, no config change (`config/atlas.json`, `config/pool-rewards.json` untouched by this design).
- No user authentication build-out (password auth, email verification, rate limiting are later missions; `users.password_hash` remains a placeholder).
- No reward-engine computation in this mission: the coordinator records shares and pool stats; the 75/25 split is applied only to actual confirmed pool rewards by the reward engine (later mission), never by the coordinator from estimates.

### 1.4 Ingest contract (`ingestCoordinatorState`, specified here, built later)

| Item | Contract |
|---|---|
| Payload | `data/coordinator.json` (§6.2) — one JSON object: `exported_at`, `mode`, `emergency_stop`, `mining_enabled`, `pool_connected: false`, `workers[]`, `share_totals`, `pool_stats_latest`, `sessions_active`, `last_decision_id`, `source_db_user_version` |
| Dedupe keys | Workers: host `id`. Shares: host share `id` (mirror stores `host_share_id` UNIQUE). Pool stats: `(pool_name, recorded_at)`. Sessions: host session `id` (mirror stores `host_session_id` UNIQUE) |
| Mirror tables | `mining_workers` (+ `host_worker_id`, `reported_hashrate_hps` NULL-able, `last_seen_at`), `mining_shares` (+ `host_share_id`, `origin`, `external_id`), `mining_pool_stats`, `mining_sessions` (+ `host_session_id`, `worker_id`, `kind`) — additive columns only; existing columns untouched |
| Never mirrored | Token hashes/salts, session token hashes, password hashes, raw pool API responses containing wallet addresses beyond the already-stored receiving address. The mirror carries no secret of any kind (D4) |
| Freshness labelling | Mirror rows carry `synced_at` (artifact ingest time) and `recorded_at` (host time). The UI shows "as of <host time>" and labels data older than 1 h **STALE**, following the existing provenance pattern. A re-ingest of an unchanged export reports "already up to date" |
| Failure behaviour | Ingest failure leaves the previous mirror rows untouched and surfaces the failure honestly; it never synthesizes rows, never zeroes real rows, and never reports success on `ok:true` alone — success requires the write to be confirmed (Mission 1.1 tracked-round-trip rule) |

---

## 2. Schema: what Stage 0 already has, and the one migration this design requires

Stage 0 (Mission 2, `core/migrate_mission2_stage0.sql`, `PRAGMA user_version` = 1) already provides the tables. The coordinator needs **three additive gaps** closed by a single build-lane migration — specified here, **not applied by this design lane**:

**New migration (build lane creates): `core/migrate_mission5_stage1.sql`, `PRAGMA user_version` 1 → 2, single transaction, backup first** (same discipline as Mission 2: back up `data/atlas.db` before applying; verify integrity before and after; existing tables/rows untouched except the additive changes below).

### 2.1 `workers` — add token + telemetry columns

```sql
ALTER TABLE workers ADD COLUMN token_hash TEXT;          -- scrypt hash, never plaintext (see §4.2)
ALTER TABLE workers ADD COLUMN token_salt TEXT;          -- per-worker salt, hex
ALTER TABLE workers ADD COLUMN token_status TEXT NOT NULL DEFAULT 'active'
    CHECK (token_status IN ('active', 'revoked'));
ALTER TABLE workers ADD COLUMN reported_hashrate_hps INTEGER;  -- agent self-report ONLY; NULL = not measured (§7 rule)
ALTER TABLE workers ADD COLUMN last_seen_at INTEGER;     -- last agent/probe check-in, epoch; NULL = never
ALTER TABLE workers ADD COLUMN xmrig_version TEXT;       -- desktop only; NULL for browser
ALTER TABLE workers ADD COLUMN xmrig_sha256 TEXT;        -- desktop only; verified hash of the running binary (§4.1)
CREATE UNIQUE INDEX IF NOT EXISTS idx_workers_user_name ON workers(user_id, name);
```

- `status` values: the Mission 4 §5.4 lifecycle is authoritative — `pending`, `registered`, `active`, `degraded`, `suspended`, `revoked`. The task's "active/inactive" wording maps onto this as: **Active = `active` only; Inactive = every other status.** The UI shows the lifecycle status verbatim and derives the Active/Inactive grouping from it (§7.2); no separate boolean is stored, so the two can never disagree.
- `worker_type` CHECK (`browser`, `desktop`) is unchanged from Stage 0.
- Name rules (Mission 4 §5.2, binding): charset `[a-z0-9-]`, max 32 characters, unique per user via `idx_workers_user_name`. A second registration with the same name for the same user is rejected with `worker name already in use`. (ASSUMPTION carried from Mission 4: the 32-char limit is to be confirmed against pool naming rules when a pool connection is authorized; it is a registration rule, not a pool fact.)
- No worker row exists today (0 rows, VERIFIED). The registry starts empty and stays honest (§4).

### 2.2 `shares` — add origin + external identity (dedupe keys)

```sql
ALTER TABLE shares ADD COLUMN origin TEXT NOT NULL DEFAULT 'pool'
    CHECK (origin IN ('pool', 'local-test'));
ALTER TABLE shares ADD COLUMN external_id TEXT;         -- pool share id, or 'local-test:<session>:<seq>'
ALTER TABLE shares ADD COLUMN job_id TEXT;              -- pool job id / local-test job id; NULL if unknown
CREATE UNIQUE INDEX IF NOT EXISTS idx_shares_worker_external
    ON shares(worker_id, external_id) WHERE external_id IS NOT NULL;
```

- `difficulty` (Stage 0, nullable INTEGER) is the per-share difficulty; attribution weight = difficulty (§3.2). A share with NULL difficulty counts as weight 1 in display totals only if it is pool-accepted — and the build lane must confirm the pool always supplies difficulty before relying on it; until then, any NULL-difficulty pool share is flagged in the coordinator log, not silently weighted.
- `accepted` (Stage 0, CHECK 0/1) keeps its meaning: **pool-accepted (origin `pool`) or relay-accepted-locally (origin `local-test`)**. The two meanings are distinguished only by `origin` — never by `accepted` alone (§3.1).

### 2.3 `sessions` — add worker sessions without breaking user sessions

Stage 0 `sessions` is a **user** session table (`user_id`, `session_token_hash`, `created_at`, `expires_at`). Worker sessions are a different thing (an agent check-in session / a browser probe session), so the table is extended, not replaced:

```sql
ALTER TABLE sessions ADD COLUMN worker_id INTEGER REFERENCES workers(id);
ALTER TABLE sessions ADD COLUMN kind TEXT NOT NULL DEFAULT 'user'
    CHECK (kind IN ('user', 'worker'));
ALTER TABLE sessions ADD COLUMN ended_at INTEGER;       -- NULL = still open
ALTER TABLE sessions ADD COLUMN session_ref TEXT;        -- browser probe tab-session id, or agent session id; never a secret
CREATE INDEX IF NOT EXISTS idx_sessions_worker_id ON sessions(worker_id);
```

- Rules: a `kind='user'` row must have `worker_id IS NULL`; a `kind='worker'` row must have `worker_id NOT NULL` and `user_id` = that worker's owner (enforced by the coordinator module, not by a CHECK — SQLite cannot cross-check that in a CHECK; the build lane's tests must cover it).
- `session_token_hash` keeps its meaning for `kind='user'` rows and for desktop-agent auth sessions (`kind='worker'`, desktop). For browser probe sessions it is **NULL** — a browser local-test session has no credential, and none is invented for it. The mirror never carries this column (§1.4).
- No session row exists today (0 rows, VERIFIED).

### 2.4 No other schema changes

`users`, `ledger`, `payouts`, `referrals`, `achievements`, `pool_stats`, `decisions`, `metrics`, `events` are **unchanged**. In particular:

- `pool_stats` already has every column the coordinator needs (`pool_name`, `recorded_at`, `hashrate`, `miners`, `block_height`, `network_hashrate`, `block_reward_piconero`, `pool_fee_bps`). One clarification, binding on the build lane: `hashrate` = **pool** hashrate in H/s (integer); `network_hashrate` = network hashrate in H/s (integer) from a separate source or NULL if unavailable — the two are never conflated, and NULL is shown as UNAVAILABLE, never as 0 (§4.3).
- `ledger` is append-only and is **not written by the coordinator** in this mission (no confirmed pool rewards exist to allocate). The reward engine (later mission) writes it.
- `decisions` is unchanged — the coordinator logs into it (§5.2).

---

## 3. Share accounting

### 3.1 What counts as a share, and what does not

| Share kind | Source | `origin` | `accepted` means | Counts toward |
|---|---|---|---|---|
| Pool share | Pool API / stratum (authorized connection only — **none exists in this mission**) | `pool` | The pool accepted it | Reward attribution, worker activation, all mining totals |
| Local-test share | Mission 4 local-test relay (`miner-relay-worker.ts`): independent single-thread re-hash + exact 256-bit difficulty check | `local-test` | The **local relay** accepted it locally | Local-test diagnostics display ONLY — never attribution, never activation, never earnings |

Rules, binding:

1. **A share counts only when the pool accepts it** (Mission 1 §6). Local hashrate, submit-rate, and local-test relay verdicts are not evidence of accepted work — the VoltMiner rounding-mode bug proved local metrics can look perfect while every share is invalid.
2. **Local-test shares are permanently marked.** Every local-test share row carries `origin='local-test'` and an `external_id` prefixed `local-test:` (§2.2). Every UI surface that shows them labels them **"Local test — not real mining"** (§7.3). They are never summed into any "shares" total without the qualifier, and no query that feeds attribution, activation, or balances may include them — the canonical attribution query is `WHERE origin='pool' AND accepted=1`.
3. **No pool connection, no share submission in this mission.** The `origin='pool'` path is specified here so the build lane implements it once, correctly — but with no authorized pool connection, zero `pool` rows can exist after this mission. The shares table honestly stays at 0 pool rows.

### 3.2 Recording a share (build-lane procedure)

```
record_shares(worker_id, shares):
  1. BEGIN IMMEDIATE; busy_timeout 5000 ms (journal mode is `delete`, not WAL —
     coordinator + monitor daemon share one DB; keep transactions short).
  2. Worker must exist and token_status='active' (pool shares) — else reject the batch,
     log dept='coordinator' decision 'share-batch-rejected', reason includes worker id.
  3. For each share: INSERT OR IGNORE INTO shares
     (worker_id, difficulty, accepted, submitted_at, origin, external_id, job_id)
     — dedupe on (worker_id, external_id) via idx_shares_worker_external (§2.2).
     A duplicate (same worker + same external_id) is skipped, not double-counted;
     the skip is counted and logged if a batch contains any.
  4. COMMIT. Return {inserted, duplicates_skipped, rejected}.
```

- `submitted_at` is the Unix epoch second the share was submitted (pool time where the pool supplies it, else coordinator receipt time — record which; never fabricate a submission second).
- Batch size: one transaction per batch, max 500 shares per batch (ASSUMPTION — prevents a long write lock against the 60 s monitor cycle; the build lane measures and adjusts).
- **Retention (design note, build lane to implement with the reward engine):** shares are high-volume. The coordinator must not let `shares` grow unbounded on this host (Mission 1 §3: mining-rate shares would dwarf the current ~170 KB DB within days). Rule: raw share rows are retained 30 days, then aggregated per worker per day (accepted/rejected counts + difficulty-weighted sums) into a daily rollup the reward engine owns, and raw rows older than 30 days are pruned. Pruning is a later-mission operation with its own authorization; this design records the requirement so the build lane does not design a table with no retention story.

### 3.3 Difficulty-weighted attribution (definition, not yet executed)

Attribution is defined now so the reward engine inherits it exactly:

```
weight(worker, window) = SUM(difficulty) over shares
    WHERE worker_id = worker AND origin = 'pool' AND accepted = 1
    AND submitted_at IN window
user_share(window) = weight(worker) / SUM(weight over all workers in window)
```

- Only **pool-accepted** shares carry weight. Rejected shares (`accepted=0`) carry zero weight and are tracked separately as a health signal (rejection rate = rejected / (accepted + rejected) per worker, pool origin only).
- Attribution is computed **only over confirmed pool reward batches** (Mission 1 §6): a reward batch references its window and its share set, and is processed exactly once (dedupe on batch id). Estimates from hashrate never create attribution.
- All amounts integer piconero; the 75/25 split applies to net distributable rewards after disclosed pool fees, never to gross estimates. Referral rewards, if introduced, come from the ATLAS 25% only.

### 3.4 Share health signals the coordinator watches

- **Rejection rate** per worker (pool origin only): `rejected / total`. Thresholds are ASSUMPTIONS for the build lane to confirm with pool data: >5% sustained over 100+ shares → `degraded` flag + decision log; >20% → `suspended` pending review. A local-test rejection is a **prototype bug signal** (self-check drop, Mission 4 R2), not a worker health signal — it is logged under the probe session, never against the worker.
- **Duplicate / replay detection:** a share `external_id` seen for a different worker, or the same `external_id` submitted twice with different payloads, is a conflict: batch rejected, worker flagged `suspended`, decision logged with reason. (Mission 4 §5.5, layer 3 — pool-side duplicate detection, coordinator-enforced.)
- **Stale shares:** shares with `submitted_at` older than the current pool job are expected at job change; the coordinator records them but does not flag them.

---

## 4. Worker registry

### 4.1 Registry state today (VERIFIED)

**Empty.** `workers` has 0 rows; `users` has 0 rows. There is no worker to register, activate, or display. The registry starts empty and stays honest: the UI shows zero workers with an explicit empty state (§7.2), never a demo worker, never a bootstrap worker presented as a miner. (The artifact's existing `workers` table holding `worker-1-bootstrap` is a **monitoring-only** host record from Mission 1, not a mining worker; it must not be displayed in the Coordinator section as a mining worker.)

### 4.2 Registration (host-side CLI, this mission)

```
atlas_coordinator.py register --user-id <id> --type desktop|browser --name <name>
```

1. Validate: user exists; `worker_type` in (`browser`, `desktop`); name matches `[a-z0-9-]{1,32}`; `(user_id, name)` not already registered.
2. **Desktop only — token issuance:** generate with `secrets.token_urlsafe(32)`; generate a per-worker salt with `secrets.token_hex(16)`; store `token_hash = scrypt(token, salt)` (stdlib `hashlib.scrypt`, n=16384, r=8, p=1 — ASSUMPTION, build lane confirms cost against host CPU) and `token_salt`. Print the token **once** to the operator, with the instruction that it is shown once and must be pasted into the worker agent config. Never write the plaintext token to the DB, a file, or a log.
3. **Browser only — no token:** a browser worker has no credential. Registration records the worker (name, type, status `registered`, `registered_at`) and nothing secret. The browser worker's identity is its name + owner; its work is validated by the pool, not by a token. (XMRig never sees an ATLAS token and the browser never holds one — Mission 4 §5.2: giving a pool-bound miner an ATLAS credential would be a category error.)
4. Desktop registration also records `xmrig_version` (pinned 6.26.0 per Mission 4 design) and `xmrig_sha256` (the verified SHA-256 of the running binary, recorded at registration per Mission 4 §1.3) — NULL until the operator supplies verified values; a desktop worker with NULL `xmrig_sha256` stays `registered` and its agent reports are labelled "binary unverified".
5. Log to `decisions` (`dept='coordinator'`, decision `worker-registered`, reason: `worker <name> (<type>) registered for user <id>`).
6. Status after registration: **`registered`** — never `active` (§4.4).

**Token rotation / revocation (specified, host-side CLI):**

- `rotate-token --worker-id <id>`: generate a new token, replace hash+salt, old token invalidated immediately, new token shown once, decision logged (`worker-token-rotated`).
- `revoke-worker --worker-id <id>`: set `token_status='revoked'`, status `revoked`, decision logged (`worker-revoked`). Reports presenting the old token are rejected. Revocation does **not** stop the XMRig process — the UI must say, in the same breath as the revoke confirmation, that the user must also stop the miner locally (Mission 4 §5.6).
- A token presented by two different agent instances is a conflict: the second check-in is rejected, the worker is flagged `suspended`, decision logged (`worker-token-conflict`), resolution is rotate-or-revoke by the user.

### 4.3 Per-worker fields the coordinator tracks

| Field | Source | Label in UI |
|---|---|---|
| `name` | Registration | Worker name (verbatim) |
| `worker_type` | Registration | Browser / Desktop |
| `status` | Lifecycle (§4.4) | Registered / Active / Degraded / Suspended / Revoked / Pending |
| `reported_hashrate_hps` | Agent self-report (desktop) or probe measurement (browser, after Gate 1) | **"not measured" when NULL — always** (§7 rule) |
| `last_seen_at` | Last agent check-in / probe session | "Last seen: <time>" or "Never" |
| `xmrig_version` / `xmrig_sha256` | Registration / agent report (desktop) | Version string, or "Binary unverified" |
| Share counts | `shares` table, split by origin | Accepted (pool) / Rejected (pool) / Local-test (separate) |
| Owner | `users` row | Username (never email in the coordinator section) |

**What `reported_hashrate_hps` is and is not:** it is a self-reported number from the worker agent (desktop) or a probe-measured number (browser, only after a real Gate 1 probe run). It is **never** computed from share counts, never estimated from hardware, and never back-filled from other projects' benchmarks. The Mission 4 published figures (5800X 10.0–12.4 kH/s, 7950X 26,960 H/s) are **community benchmarks, not ATLAS measurements**, and are never stored in this column. NULL is the honest default and the UI renders NULL as "not measured".

### 4.4 Status lifecycle (Mission 4 §5.4, adopted verbatim)

| Status | Meaning | How a worker gets here |
|---|---|---|
| `pending` | Registration started, not finished | Registration begun; token not yet issued (desktop) |
| `registered` | Token issued, worker configured, **no pool-accepted shares yet** | Registration complete + first agent check-in. Local hashrate — however high — keeps a worker here |
| `active` | Pool shows accepted shares for this wallet + worker name | Coordinator verifies ≥1 pool-accepted share via the pool API, cross-checked against the agent's report (§4.5) |
| `degraded` | Active, but pool/agent reports disagree or rejection rate is abnormal | Coordinator flags it; worker keeps mining but its shares are not credited until resolved |
| `suspended` | ATLAS-side hold (duplicate conflict, abuse flag, emergency stop) | Coordinator or admin action, logged with reason |
| `revoked` | Token revoked by the user | User revokes; reports with the old token rejected |

- **While the emergency stop is active, no worker may move to `active`** — a worker can register, but activation waits for the stop to be lifted by an authorized action. The stop never lifts automatically. (`config/pool-rewards.json` safety rules.)
- **Local hashrate never activates a worker.** This is the single most important lifecycle rule and the reason the lifecycle exists.

### 4.5 Activation verification (`verify_worker_active`, gated in this mission)

```
verify_worker_active(worker_id):
  1. If emergency_stop is true → log 'worker-activation-held' (reason: emergency stop active);
     return NOT_ACTIVATED. No pool query is needed.
  2. If no pool connection is authorized → log 'worker-activation-unverified'
     (reason: no pool connection authorized — simulation-only); return NOT_ACTIVATED.
     *** THIS IS THE OUTCOME IN THIS MISSION, EVERY TIME. ***
  3. (Future, authorized only) Query the pool API for the wallet + worker pair;
     confirm ≥1 accepted share; cross-check the pool's accepted count against the
     agent's reported count. A material mismatch → `degraded`, not activation.
     On confirmation: status `registered` → `active`, decision logged
     ('worker-activated', reason includes pool, wallet (masked), worker name,
     accepted-share count, and check time).
```

- The verification decision is logged in `decisions` (`dept='coordinator'`) with its reason, in all three branches — including the held/unverified branches, so the audit trail shows activation was considered and refused, not forgotten.
- Duplicate prevention (Mission 4 §5.5, all four layers, coordinator-enforced): (1) `(user_id, name)` uniqueness; (2) one token per worker, token-conflict → `suspended`; (3) pool-side duplicate detection via `external_id` (§3.4); (4) one agent per machine (agent lockfile/PID check, agent-side, reported to the coordinator).

---

## 5. Pool stats and sessions

### 5.1 Pool stats — read-only public API fetch

**Source:** MoneroOcean `/pool/stats` — `https://api.moneroocean.stream/pool/stats` (primary pool per `config/pool-rewards.json`, 0% fee, VERIFIED reachable 200 from this host 2026-11-18; note Mission 1 measured 7.67 s for one fetch — slow enough that timeouts under load are a real risk).

**Procedure (`poll_pool_stats`, build lane):**

- HTTP **GET only**, no auth, no credentials, no request body, `User-Agent: ATLAS-coordinator/1.0`, timeout **10 s**, max 1 retry on timeout (2 attempts total, then fail the poll — never hammer a slow pool).
- Cadence: **every 10 minutes**, not every 60 s monitor cycle. Pool stats change slowly; a 10-minute cadence is 6 rows/hour/pool and keeps the fetch off the monitor daemon's critical path. The poll runs in the coordinator's own loop/CLI invocation, never inside `atlas_monitor.py`'s 60 s cycle.
- On success, insert **one row** into `pool_stats`:
  - `pool_name` = `MoneroOcean` (verbatim from config).
  - `hashrate` = pool hashrate in H/s (integer, from the response's pool-hashrate field; NULL if the field is absent — never 0, never guessed).
  - `miners` = pool miner count (integer; NULL if absent).
  - `block_height` = pool-reported block height (integer; NULL if absent).
  - `network_hashrate` = network hashrate in H/s **only if the response supplies it**; otherwise NULL. (If a future build lane sources it from network difficulty ÷ 120 s, that derivation, its source, and its timestamp must be recorded in the decision log — it is a computed value, not a pool fact.)
  - `block_reward_piconero` = 600,000,000,000 (0.6 XMR tail emission, integer piconero; VERIFIED Mission 1/4 — recorded per row so a future reward change does not rewrite history).
  - `pool_fee_bps` = 0 (from `config/pool-rewards.json`, primary pool; integer basis points, never a float percent).
  - `recorded_at` = Unix epoch second of receipt.
- **Fallbacks** (only if MoneroOcean fails 3 consecutive polls): SupportXMR API (0.6% fee, 60 bps — VERIFIED reachable 200 after 301) as the next source, then P2Pool (0% fee; no central pool API — stats via local P2Pool node/observer only, so a P2Pool row is recorded only when such a source exists; the coordinator never invents P2Pool stats). Fallback use is logged (`pool-stats-fallback`, reason names the pool and the failure count). Fallback never changes the primary pool in config.
- **On failure:** no row is inserted (a failed fetch is not a zero-hashrate observation — inserting 0 would be fabricated data). After 3 consecutive failures, log `pool-stats-unavailable` (`dept='coordinator'`) and the UI shows pool stats as **STALE / UNAVAILABLE** with the age of the last good row (§7.5). The coordinator never crashes on a pool failure; it degrades to the last good row.
- **This is not a pool connection for earning.** Reading a public stats endpoint submits nothing, earns nothing, and creates no account. No stratum, no wallet address, and no worker credential is sent to the pool in this fetch.

### 5.2 Sessions — worker sessions in the `sessions` table

Two session kinds share the table (§2.3). The coordinator owns `kind='worker'` rows:

| Session kind | Opens when | Closes when | Identity |
|---|---|---|---|
| Desktop agent session | Agent checks in with a valid per-worker token | Agent disconnects, token revoked, or 24 h without check-in (ASSUMPTION — build lane confirms) | `session_token_hash` (hash of the agent session token); `session_ref` = agent session id |
| Browser probe session | A `?atlas-miner-test=1` probe run starts (Mission 4 probe hook) | Probe stops, 600 s cap reached, or tab hidden > probe pause | `session_token_hash` = **NULL** (no credential exists); `session_ref` = tab session id |

Rules:

- One open worker session per worker per agent instance. A second concurrent session for the same worker from a different agent instance is a token-conflict signal (§4.2), not a second session.
- `expires_at` is set at open (user sessions: existing behaviour; worker sessions: open time + 24 h, ASSUMPTION). Expired sessions are closed lazily on the next coordinator pass (`ended_at` set, decision logged only if the session was active — routine expiry is not decision-logged, it is recorded in the row).
- **Browser local-test probe sessions are test sessions, not mining sessions.** They are recorded so a Gate 1/Gate 3 run has an audit trail (threads, mode, dataset state, H/s measured, drops, buckets), but they never appear in the Workers table as activity, never activate a worker, and never contribute shares with `origin='pool'`. Their shares are `origin='local-test'` (§3.1).
- Session rows are mirrored to `mining_sessions` with `host_session_id` (§1.4); the mirror never carries `session_token_hash`.

### 5.3 Coordinator decisions — audit trail in `decisions`

Every coordinator decision is a row in the **existing** `decisions` table (`ts`, `dept`, `decision`, `reason`). New `dept` value: **`coordinator`** (alongside the existing `core`/`mining`/`scheduler`/`trading` values; Mission 1 §2.3 anticipated new dept values such as `rewards`/`payouts` for later missions — the coordinator uses `coordinator` for its own actions and leaves `rewards`/`payouts` to those engines).

Decisions the coordinator must log (decision name → when):

| Decision | When |
|---|---|
| `worker-registered` | A worker registers (§4.2) |
| `worker-token-rotated` | A token is rotated |
| `worker-revoked` | A worker is revoked |
| `worker-token-conflict` | One token presented by two agent instances |
| `worker-activation-held` | Activation refused: emergency stop active |
| `worker-activation-unverified` | Activation refused: no pool connection authorized (the outcome in this mission) |
| `worker-activated` | Pool-accepted shares verified (future, authorized only) |
| `worker-degraded` / `worker-suspended` | Rejection-rate or report-mismatch flag; duplicate/abuse hold |
| `share-batch-rejected` | A share batch failed validation (unknown/revoked worker) |
| `share-batch-duplicates-skipped` | A batch contained duplicates (only when count > 0) |
| `pool-stats-fallback` | Fallback pool used after 3 consecutive primary failures |
| `pool-stats-unavailable` | 3 consecutive failures on all configured sources |
| `coordinator-pass-complete` | Each scheduled coordinator pass finishes (summary reason: workers/shares/pool rows touched) — one row per pass, not one per action |

Reason strings must name the worker id/name, the pool where relevant, and the evidence (counts, timestamps) — a decision without a reason is a failed audit entry. The UI's Coordinator section shows the latest decisions (§7.6) from the mirror.

---

## 6. Coordinator state

### 6.1 What "coordinator state" is

Coordinator state is a **derived read model** (D8): a single JSON object computed from the Stage 0 tables + both configs at export time. It is not stored in its own table, so it cannot drift from the rows it summarizes. It answers, at a glance: is the coordinator running, is anything authorized, is anyone mining, and how fresh is the data?

### 6.2 The state object (`data/coordinator.json`)

```json
{
  "exported_at": 1794993543,
  "source_db_user_version": 2,
  "mode": "simulation-only",
  "emergency_stop": true,
  "mining_enabled": false,
  "pool_connected": false,
  "pool_connection_note": "No pool connection authorized — read-only /pool/stats polling only",
  "workers": { "total": 0, "active": 0, "registered": 0, "degraded": 0, "suspended": 0, "revoked": 0, "pending": 0 },
  "shares": {
    "pool_accepted": 0, "pool_rejected": 0,
    "local_test_accepted": 0, "local_test_rejected": 0
  },
  "hashrate": { "status": "not-measured", "measured_hps": null, "note": "Gate 1 unmeasured — no probe measurement exists" },
  "pool_stats_latest": null,
  "pool_stats_last_recorded_at": null,
  "sessions_active": 0,
  "last_decision_id": 68,
  "last_coordinator_pass_at": null
}
```

- `pool_stats_latest` is either `null` (no row yet — the honest state today) or the latest `pool_stats` row verbatim (pool name, recorded_at, hashrate, miners, block_height, network_hashrate, block_reward_piconero, pool_fee_bps).
- `hashrate.measured_hps` is `null` until a real probe measurement exists. It is **never** populated from benchmarks, estimates, or agent self-report without the "reported, not measured" label — and the top-level `hashrate.status` stays `not-measured` until Gate 1 passes (see §7 rule).
- `last_coordinator_pass_at` is `null` until the coordinator has run one pass.

### 6.3 Module + CLI shape (build lane)

```
core/atlas_coordinator.py          # stdlib only; imports config + DB paths from the same
                                   # BASE/CFG/DB constants as atlas_core.py
  load_config()                    # reads config/atlas.json + config/pool-rewards.json every pass (never cached across passes)
  log_decision(con, decision, reason)   # dept='coordinator', same shape as atlas_core.log_decision
  register_worker(...) / rotate_token(...) / revoke_worker(...)
  record_worker_session(...) / close_worker_session(...)
  record_shares(...)               # §3.2
  verify_worker_active(...)        # §4.5 (gated)
  poll_pool_stats(...)             # §5.1
  coordinator_status() -> dict     # §6.2
  export_coordinator_json()        # atomic write of data/coordinator.json
  run_pass()                       # one pass: poll pool stats (if due) + close expired sessions
                                   # + verify pending activations (gated) + export + log pass-complete
  CLI: status | pass | register | rotate-token | revoke-worker | export
```

- **Scheduling:** the coordinator runs as a **separate invocation**, not inside the 60 s monitor daemon. Recommended: cron every 10 minutes for `pass` (aligned to the pool-stats cadence), plus on-demand CLI for registration. It must never run inside `atlas_monitor.py`'s loop — the monitor's job is host metrics, and a 7-second pool fetch must never stall it. (A `recover.sh`-style watchdog entry for the coordinator is owed by the build lane, following the existing recovery doc pattern.)
- **Concurrency:** single-threaded; `BEGIN IMMEDIATE` + `busy_timeout=5000` on every write transaction; journal mode stays `delete` in this mission (WAL is a build-lane decision with its own backup + verification, per Mission 1 §3 — not snuck in here).
- **Failure discipline (from the monitor daemon):** the coordinator never crashes on a DB lock (retry once after 1 s, then log and exit non-zero) or a pool failure (§5.1); logging failures are swallowed so logging never breaks coordination.

---

## 7. UI spec — Coordinator section in the Mining tab (exact, build-ready)

### 7.1 Placement and rules

- **Location:** inside the existing Mining tab (`client/src/Mining.tsx`, artifact `atlas-command-center`). **NO new tab.** The section sits **directly below the "Miner Prototype — Master Mission 4" section** and above the Payout center. It does not reorder, restyle, or reword any existing section (dashboard, wallet center, earnings, history, reward history, payout center, calculator, settings, help, Miner Prototype).
- **Component:** new `client/src/miner/CoordinatorSection.tsx` (name is a build-lane suggestion; the section heading and copy below are binding). Data comes from the **extended `getMining` action** reading the artifact `mining_*` mirror tables only (§1.2). React Query refetch: same 30 s cadence as the rest of the Mining tab. No new refresh schedule.
- **Provenance:** every figure carries a SNAPSHOT / RECORDED / ESTIMATE / UNAVAILABLE tag, following the existing tab pattern. Nothing in this section is labelled live unless it was measured in the current probe/session.
- **No start control.** There is no Start button, Stop button, "activate mining", or "connect to pool" control anywhere in this section. The existing Start/Stop buttons in the Mining dashboard stay **hard-disabled with no handler** (Mission 2/4). The coordinator does not start mining.
- **No registration form in this mission.** Registration is host-side CLI (§4.2). The section explains that and does not present a form that would write to the mirror (§7.2).
- **The hashrate rule (binding, overrides any other copy):** every hashrate figure in this section — worker rows, totals, pool stats, and the header — reads **"not measured"** until a real probe measurement exists. Gate 1 is UNMEASURED. No benchmark figure, estimate, or other project's number is ever shown as an ATLAS hashrate. The only hashrate-adjacent numbers permitted are other projects' published figures, explicitly labelled as theirs (already present in the Miner Prototype section — not repeated here).

### 7.2 Section layout (top to bottom)

**Section header (verbatim):**

> **Coordinator — Master Mission 5**
> Subtitle: `Simulation only — the coordinator tracks workers, shares, and pool stats. It does not start mining, connect to a pool for earning, or pay out.`

**Panel 1 — Coordinator state (status banner, always visible):**

| Row label | Value when empty / today (VERIFIED) | Value when populated |
|---|---|---|
| Mode | `Simulation only` | `Simulation only` (unchanged until a later mission + authorization changes it) |
| Emergency stop | `ON — all live activity held` | Same; if ever OFF, shows `OFF` + the time it was lifted + the decision id |
| Mining | `Disabled` | `Disabled` |
| Pool connection | `None — read-only stats polling only` | Same until a pool connection is separately authorized |
| Workers | `0 workers` | `<n> workers (<a> active)` |
| Last coordinator pass | `No coordinator pass has run yet` | `<date time> — <n> decisions logged` |
| Data as of | `No coordinator data yet` | `<host export time> (STALE if > 1 h old)` |

Empty-state banner (verbatim, shown while workers = 0 and shares = 0):

> `No workers registered yet. The coordinator is running in simulation only — there is nothing to coordinate.`

**Panel 2 — Workers (registry table):**

Heading: `Workers — 0 registered`

Column headers (exact): `Worker | Type | Status | Hashrate | Shares (pool) | Last seen`

Empty state (verbatim, shown when the table has no rows):

> `No workers registered. Workers appear here after host-side registration — registration is not open in the browser in this mission.`

Populated-row rules:

- `Worker`: name verbatim (e.g. `rig1`). Never an email, never a wallet address.
- `Type`: `Browser` or `Desktop`.
- `Status`: lifecycle status verbatim (`Registered`, `Active`, `Degraded`, `Suspended`, `Revoked`, `Pending`). An `Active` row carries a green dot; every other status carries a grey/amber dot and the derived grouping "Inactive" in the section summary only — the row itself shows the lifecycle status, never just "Inactive".
- `Hashrate`: **`not measured`** for every worker until Gate 1 passes for that worker type. After a real probe measurement exists, the cell shows the measured value with its measurement time and the tag `MEASURED <time>`; a desktop agent self-report shows the value with the tag `REPORTED — agent self-report, not measured by ATLAS`. A worker with no value shows `not measured`, never `0 H/s` as a measurement (0 is a recorded zero only when a probe actually measured 0, which has not happened).
- `Shares (pool)`: `<accepted> accepted / <rejected> rejected`. Local-test shares are **not** in this column.
- `Last seen`: `<date time>` or `Never`.
- Row detail (expandable or below the table, per row): `Registered <date time>` · `XMRig <version>` or `Binary unverified` (desktop) · `Token: issued <date>` — the token value itself is **never displayed**.
- Registration note (verbatim, below the table):

> `Worker registration is host-side in this mission. A desktop worker registers with a name and a per-worker token (shown once at registration); a browser worker registers with a name only. A worker becomes Active only after the pool shows accepted shares for it — local hashrate never activates a worker.`

**Panel 3 — Shares (accounting):**

Heading: `Shares`

Four stat cards (exact labels + today's honest values):

| Card label | Value today | Provenance tag |
|---|---|---|
| `Pool shares accepted` | `0` | RECORDED |
| `Pool shares rejected` | `0` | RECORDED |
| `Local-test shares accepted` | `0` | RECORDED |
| `Local-test shares rejected` | `0` | RECORDED |

Below the cards (verbatim):

> `Pool shares are the only shares that count toward rewards or worker activation. Local-test shares come from the Mission 4 local-test relay only — they are not real mining shares and never earn anything.`

Rejection-rate line (shown only when pool total > 0, else hidden — not shown as 0%):

> `Pool rejection rate: <x>% over <n> pool shares (RECORDED)`

Attribution line (verbatim, always visible):

> `Reward attribution: difficulty-weighted pool-accepted shares only, applied to confirmed pool rewards. No confirmed pool rewards exist yet, so no attribution has been calculated.`

**Panel 4 — Hashrate:**

Heading: `Hashrate`

Body (verbatim while Gate 1 is unmeasured — this is the state today and until a probe run exists):

> `Hashrate: not measured`
> `No measurement yet — Gate 1 (measured hashrate in a real browser) has not been run for the Mission 4 prototype. Published figures from other projects are shown in the Miner Prototype section above and are not ATLAS measurements.`

Rules: this panel shows **no number** in H/s while unmeasured — not 0, not an estimate, not a benchmark. After Gate 1 passes, it shows the measured value, the probe session id, threads/mode, measurement time, and tag `MEASURED`; the "not measured" copy is replaced, not kept alongside. A desktop agent self-report is shown here only with the tag `REPORTED — agent self-report, not measured by ATLAS`, and never replaces the `not measured` state for the browser prototype.

**Panel 5 — Pool stats:**

Heading: `Pool stats — MoneroOcean (read-only)`

Fields (exact labels): `Pool hashrate | Miners | Block height | Network hashrate | Block reward | Pool fee`

Empty state (verbatim, shown while no `pool_stats` row has been ingested — the state today):

> `No pool stats recorded yet. The coordinator polls the public MoneroOcean /pool/stats endpoint every 10 minutes (read-only — no pool connection, no submission).`

Populated-state rules:

- Each field shows its value with tag `RECORDED <recorded_at time>`, or `UNAVAILABLE` when the source did not supply it (never 0, never a stale value carried forward silently).
- `Block reward`: `0.6 XMR` (from the stored integer piconero value).
- `Pool fee`: `0%` (MoneroOcean primary; the fee of the pool the row came from — a fallback row shows that pool's fee, e.g. SupportXMR `0.6%`).
- Stale rule: if the latest row is older than 1 h, the panel header shows `STALE — last good reading <age>` and the fields keep their `RECORDED <time>` tags.
- Footnote (verbatim):

> `Pool stats are public data, read only. Reading them does not connect ATLAS to the pool for earning and submits no shares.`

**Panel 6 — Sessions & coordinator decisions (audit):**

Heading: `Sessions & decisions`

Sessions sub-block:

- Line 1 (verbatim while empty): `No worker sessions. Worker sessions appear here when a desktop agent checks in or a browser probe run starts.`
- Populated rows: `<worker name> — <kind: Desktop agent / Browser probe> — opened <time> — <Open / Closed <time>>`. A browser probe row carries the tag `LOCAL TEST`. No token, token hash, or session secret is ever displayed.

Decisions sub-block (latest 10 coordinator decisions, from the mirror of `decisions` where `dept='coordinator'`):

- Empty state (verbatim): `No coordinator decisions yet.`
- Row format: `<time> — <decision> — <reason>` (reason verbatim from the host log).
- Link text below: `Full decision log is on the Activity tab.` (no new log view is built here.)

### 7.3 Copy that must NOT appear in this section

- Any hashrate number presented as ATLAS's without a `MEASURED` tag and a measurement time.
- The words "verified", "confirmed", or a checkmark next to any worker, address, or hashrate that has only passed format checks or self-report.
- "There is no miner yet" — this copy is **stale** (Mission 4 finding 4: two strings remain in `Mining.tsx`, dashboard + Help). This design does **not** fix it (repair needs separate authorization, §8.2) and the new section must not repeat it. The correct framing, used in this section, is: the prototype exists; mining is disabled; no measurement exists yet.
- Any earnings, balance, or payout figure derived from shares or hashrate. Balances stay in the existing Earnings/Payout panels (all 0 XMR from the empty ledger) and are untouched by this section.

### 7.4 Responsive / accessibility notes (binding on the build lane)

- The Workers table collapses to stacked cards below ~640 px width (same breakpoint behaviour as the existing Mining tab tables); no horizontal page overflow at 390 px (the Mission 3 audit standard: mobile overflow 0).
- All status text is text, not colour alone (a screen reader must hear `Active` / `Registered`, not just see a dot).
- Disabled/absent controls are absent, not greyed-out fake buttons — there is no Start control to disable in this section.

---

## 8. Known issues (noted only — NOT fixed by this design)

These are carried forward from Missions 3–4. This design lane fixes none of them; each needs its own authorization.

1. **Refresh failure (Mission 3 finding 1, carried).** Refresh intermittently fails at the platform spawn step ("Refresh could not start: Web artifact inference failed"), the dashboard goes stale, and the UI mislabels a re-ingest of the already-stored snapshot as "Refresh complete". The coordinator ingest in §1.4 is specified to avoid repeating the mislabelling defect (re-ingest must say "already up to date"), but **no refresh repair is authorized or attempted here**. A stale coordinator mirror is labelled STALE (§7.2) rather than silently presented as fresh.
2. **Stale "no miner yet" copy (Mission 4 finding 4, carried).** Exactly two strings remain in `Mining.tsx` (dashboard + Help) saying there is no miner yet; the prototype is built, so they are stale. Repair needs a repair-authorized inspection. This design notes it and forbids repeating the claim in the new section (§7.3).
3. **Gate 1 unmeasured (Mission 4 finding 1, carried — the most important).** No measured hashrate exists for the prototype. A fresh interactive probe run on the current build is owed; this design does not run it and fabricates nothing in its place.
4. **Current-build interactive audit never executed (Mission 4 finding 2, carried).** No captured render selects the Mining tab on the current build; the Coordinator section's rendering will likewise need a fresh interactive audit (desktop + mobile) after the build lane implements §7.
5. **Host memory 87–92% (standing, pre-existing).** Above the 70% config cap; the re-scope proposal (alert on ATLAS's own footprint; host MEM% informational) still needs user approval. The coordinator is a lightweight CLI invoked every 10 minutes, not a resident daemon, partly for this reason — it adds no permanent memory footprint.
6. **mempool.space disputed, not settled.** Recorded as measured (000/timeout on recent attempts after earlier 200s), not settled either way. It is not a coordinator input and this design takes no position.

---

## 9. What the build lane receives from this design (handoff checklist)

**Build (later mission, needs authorization):**

1. `core/atlas_coordinator.py` — per §6.3 (stdlib only; CLI: `status | pass | register | rotate-token | revoke-worker | export`).
2. `core/migrate_mission5_stage1.sql` — per §2 (backup first; single transaction; `user_version` 1 → 2; verify integrity before/after; all 9 Stage 0 tables at 0 rows before applying — confirm, do not assume).
3. `data/coordinator.json` export (atomic write) + 10-minute cron for `pass` + `recover.sh`-style watchdog entry (following the existing recovery doc pattern).
4. Artifact: `ingestCoordinatorState` action + `getMining` extension + `CoordinatorSection.tsx` per §7 (exact headings, labels, empty states, and the hashrate rule). Mirror columns per §1.4. No token/session/password hash ever mirrored.
5. Diagnostics additions (proposed, build lane confirms numbering): a test asserting `coordinator.json` exports and matches the DB row counts; a test asserting no `origin='local-test'` share is counted by the attribution query; a test asserting no worker is `active` while the emergency stop is on; a test asserting the mirror contains no token hash. Existing 22 diagnostics must stay green.

**Verify (evidence owed by the build lane — none exists yet):**

- Coordinator `pass` runs clean on the host; `coordinator.json` matches DB counts exactly; a second `pass` with no changes exports identically (idempotent).
- Registration via CLI creates a worker with status `registered`, token shown once, hash stored salted — and the UI shows it as `Registered` with hashrate `not measured` (rendered check, desktop + mobile, Mining tab selected on the current build).
- A local-test share recorded via the Mission 4 relay path appears in the UI only under "Local-test shares" and never in pool totals or attribution.
- Pool-stats poll inserts exactly one row per poll; a forced failure inserts no row and logs `pool-stats-unavailable` after 3 consecutive failures.
- `verify_worker_active` with the stop ON logs `worker-activation-held` and leaves the worker `registered`.

**Do not build in this mission:**

- No pool connection for earning, no stratum client, no share submission (Gate 2 — separate authorization).
- No reward-engine computation, no payout flow, no treasury design (Gate 4 — separate authorization + security testing).
- No in-browser registration, no artifact → host write path, no user auth build-out.
- No mining activation on any host; Start/Stop stay hard-disabled.

## 10. Open items and risks carried forward (not resolved by this design)

1. **Artifact → host write path** — deferred by design (D3). Any future in-browser registration needs a real authenticated host-side API first; the security design for that endpoint (auth, rate limiting, token transport over TLS, abuse controls) is owed by the mission that proposes it.
2. **WAL vs `delete` journal mode** — deferred. The coordinator + monitor share one DB under `delete` mode; short transactions + `busy_timeout` are specified, but contention under a 10-minute coordinator pass overlapping the 60 s monitor cycle is unmeasured. The build lane measures lock-wait behaviour before proposing WAL.
3. **Share-table retention/pruning** — the 30-day raw + daily-rollup rule (§3.2) is a requirement, not an implementation; the rollup table and pruning job belong to the reward-engine mission.
4. **Pool-stats `network_hashrate` sourcing** — the response field is not guaranteed; the fallback derivation (difficulty ÷ 120 s) is specified as a labelled computation, not a pool fact, and needs its source recorded if ever used.
5. **The 32-char worker-name limit** is an ASSUMPTION carried from Mission 4 §5.2, to be confirmed against pool naming rules when a pool connection is authorized.
6. **Browser worker identity** — a browser worker has no token by design; its abuse story (one tab registering many worker names, name-squatting) is unaddressed until registration opens, and is a reason registration stays host-side in this mission.
7. **Coordinator scheduling on VM replacement** — processes do not survive VM replacement; the 10-minute cron + watchdog must be re-established by the restore procedure (existing recovery doc), and the build lane must confirm the cron survives the next restore.

---

## 11. Safety checklist (binding on the build lane)

- [ ] emergency_stop true, mining disabled, trading paper-only, eligible capital $0 — verified before and after every build step.
- [ ] No pool connection for earning, no stratum client, no share submission, no real payout, no wallet/key/seed creation, no spending, no config change.
- [ ] No mining on the Muse VM host; the coordinator spawns no miner process.
- [ ] No hashrate figure is fabricated: every hashrate reads "not measured" until a real probe measurement exists.
- [ ] No local-test share is presented as a real mining share, anywhere, in any total.
- [ ] No worker is `active` without pool-accepted shares; no worker is `active` while the emergency stop is on.
- [ ] No token hash, session token hash, or password hash in the artifact DB, the UI, a URL, or a log line.
- [ ] No demo users, workers, shares, earnings, or payouts seeded — the registry starts empty.
- [ ] Refresh failure (§8.1) and stale copy (§8.2) noted only, not repaired.
- [ ] Diagnostics 22/22 stay green, plus the new coordinator tests in §9.

**Stop — design complete. Awaiting authorization before any Mission 5 build work. Do not start building.**
