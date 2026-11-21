# ATLAS — Master Mission 5, Lane C: Host Coordinator Implementation — Report

**Mission:** ATLAS Master Mission 5 — Coordinator, Lane C (host coordinator implementation)
**Date:** Wednesday, 2026-11-18 (work ~04:20–10:35 EST; build ~10:20–10:35 EST)
**Design:** `docs/master-mission5-design.md` (Lane A) — implemented as specified, with three documented deviations (§5).
**Original brief functions reconciled to the design:** `register_worker` / `record_share` / `record_pool_stats` / `start_session` / `end_session` / `log_decision` — see §2 for the mapping. The design's signatures govern; the brief's names survive as wrappers where they differ.
**Scope kept:** temp-DB testing first; no demo data; no worker activation; no pool connection for earning; no share submission; no payout; no config change; no mining on the host; no cron job (per follow-up — scheduling is the parent's decision); artifact, wallet center, miner prototype, refresh failure, and stale "no miner yet" copy untouched.

## 1. What was built

### 1.1 `core/atlas_coordinator.py` (new, stdlib only, ~48 KB)

Host-side coordinator operating on the Stage 0 tables in `data/atlas.db`. Stdlib only (`sqlite3`, `json`, `urllib`, `hashlib`, `hmac`, `secrets`, `re`, `time`, `os`, `argparse`). Extends the `atlas_core.py` patterns (config load, decision log, status CLI); does not replace it. All money integer piconero; all timestamps Unix epoch integers; `BEGIN IMMEDIATE` + `busy_timeout=5000` on every write transaction; journal mode stays `delete`.

| Function | Behaviour |
|---|---|
| `register_worker(con, user_id, worker_type, name, xmrig_version=None, xmrig_sha256=None)` | Validates user exists, type browser/desktop, name `[a-z0-9-]{1,32}`, `(user_id, name)` unique. Desktop: token `secrets.token_urlsafe(32)`, salt `secrets.token_hex(16)`, stored as `hashlib.scrypt` hash (n=16384, r=8, p=1) + salt only; token returned once, never written to DB/file/log. Browser: no token. Status after registration: `registered` — never `active`. Logs `worker-registered`. |
| `verify_worker_token(con, worker_id, token)` | Constant-time scrypt re-hash comparison; False for revoked/no-token/wrong token. |
| `rotate_token(con, worker_id)` | Desktop only; old token invalid immediately; new token returned once. Logs `worker-token-rotated`. |
| `revoke_worker(con, worker_id)` | `token_status='revoked'`, status `revoked`; old token rejected. Logs `worker-revoked` (with the note that the operator must also stop the miner locally). |
| `verify_worker_active(con, worker_id)` | Gated (design §4.5): stop ON → log `worker-activation-held`, NOT_ACTIVATED; else no pool connection authorized → log `worker-activation-unverified`, NOT_ACTIVATED. Never changes status in this mission. |
| `record_shares(con, worker_id, shares)` | Batch ≤500, one transaction (design §3.2). Unknown/revoked worker → whole batch rejected + `share-batch-rejected`. Pool shares require `token_status='active'`. Dedupe on `(worker_id, external_id)` via partial unique index — same-worker duplicates skipped + counted + logged (`share-batch-duplicates-skipped`). Cross-worker `external_id` conflict → batch rejected, worker `suspended`, `worker-suspended` logged. Local-test shares require `external_id` prefixed `local-test:` (rejected otherwise). NULL-difficulty pool shares inserted but flagged (`share-batch-null-difficulty`). Returns `{inserted, duplicates_skipped, rejected}`. |
| `record_share(con, worker_id, difficulty, share_hash, verified, local_test, submitted_at=None)` | Original-brief wrapper: `verified=False` inserts nothing (returns None); `verified=True` records accepted=1, origin `local-test` (external_id `local-test:<hash>`) or `pool` (external_id = hash). |
| `attribution_weights(con, start=None, end=None)` | Difficulty-weighted pool-accepted shares per worker (design §3.3): `WHERE origin='pool' AND accepted=1` only. Definition/helper — the reward engine applies it later. |
| `record_pool_stats(con, pool, hashrate, miners, height, network_hashrate=None, ...)` | Inserts exactly one `pool_stats` row; missing fields stay NULL (never 0); fee defaults from `config/pool-rewards.json`; block reward 600,000,000,000 piconero (0.6 XMR). |
| `poll_pool_stats(con, pool_cfg=None, opener=None)` | Read-only GET of MoneroOcean `/pool/stats` (`User-Agent: ATLAS-coordinator/1.0`, 10 s timeout, 1 retry = 2 attempts). Parses `pool_statistics.hashRate` (float→int), `.miners`, `.lastBlockFound` (height); network hashrate NULL (not supplied). Success → one row + `pool-stats-polled` decision. Failure → NO row, `pool-stats-poll-failed`, and `pool-stats-unavailable` when the consecutive-failure streak reaches exactly 3 (not on later failures; a success resets the streak). Never raises on pool failure. |
| `record_worker_session(con, worker_id, session_type, session_ref=None, session_token=None)` | `kind='worker'`, `user_id` = worker's owner, `expires_at` = now + 24 h (assumption). Desktop-agent: token generated if not supplied, sha256 stored; same `session_ref` re-check-in returns the existing session; a different agent instance → `worker-token-conflict`, worker `suspended`, open refused. Browser-probe: no credential — see deviation D-M5-1. |
| `close_worker_session(con, session_id=None, worker_id=None)` / `close_expired_sessions(con)` | Sets `ended_at` (expired → `ended_at=expires_at`); routine expiry is row-only, not decision-logged. |
| `start_session` / `end_session` | Original-brief aliases for the two session functions above. |
| `log_decision(con, decision, reason)` | `dept='coordinator'` into the existing `decisions` table; reason required; caller owns the transaction. |
| `coordinator_status(con)` | Derived state per design §6.2 (D8 — computed, never stored as a second truth). Hashrate always `{status: "not-measured", measured_hps: null}` — Gate 1 unmeasured. `pool_connected: false`. |
| `export_coordinator_json(con=None, db_path, export_path)` | Atomic write (`.tmp` → `os.replace` + fsync) of `data/coordinator.json` — the bridge the artifact's `ingestCoordinatorState` action will consume. |
| `run_pass(db_path, force_poll=False, opener=None, export_path)` | One pass: poll if due (no row, or latest row ≥10 min old) or forced; close expired sessions; verify `registered` workers (gated); log `coordinator-pass-complete` **before** exporting, so the export's `last_coordinator_pass_at` reflects the pass just run; export. |
| CLI | `status | pass [--force-poll] | export | register --user-id --type --name [--xmrig-version] [--xmrig-sha256] | rotate-token --worker-id | revoke-worker --worker-id`. Registration/rotation print the token once with the shown-once instruction; the token never appears in a log line. |

### 1.2 `core/migrate_mission5_stage1.sql` (new) — Stage 1 migration, `user_version` 1 → 2

Exactly design §2, single transaction, backup first (§3):

- `workers`: `token_hash`, `token_salt`, `token_status TEXT NOT NULL DEFAULT 'active' CHECK (active/revoked)`, `reported_hashrate_hps` (NULL = not measured), `last_seen_at`, `xmrig_version`, `xmrig_sha256`; unique index `idx_workers_user_name (user_id, name)`.
- `shares`: `origin TEXT NOT NULL DEFAULT 'pool' CHECK (pool/local-test)`, `external_id`, `job_id`; partial unique index `idx_shares_worker_external (worker_id, external_id) WHERE external_id IS NOT NULL`.
- `sessions`: `worker_id REFERENCES workers(id)`, `kind TEXT NOT NULL DEFAULT 'user' CHECK (user/worker)`, `ended_at`, `session_ref`; index `idx_sessions_worker_id`.
- `users`, `ledger`, `payouts`, `referrals`, `achievements`, `pool_stats`, `decisions`, `metrics`, `events`: unchanged.

### 1.3 `data/coordinator.json` (new, derived export)

Written by `export_coordinator_json` / `run_pass`. Current live content: `mode simulation-only`, `emergency_stop true`, `mining_enabled false`, `pool_connected false`, workers all 0, shares all 0, hashrate `not-measured`, `pool_stats_latest` = the one live MoneroOcean row (§3), `sessions_active 0`, `last_coordinator_pass_at` set (§4 note on ordering).

## 2. Reconciliation: original brief → design

| Original brief | Design (governing) | Implemented |
|---|---|---|
| Module `core/coordinator.py` | `core/atlas_coordinator.py` (§6.3) | `core/atlas_coordinator.py` |
| `register_worker(name, token)`, status starts inactive | `register_worker(user_id, worker_type, name)`; token generated host-side (desktop only), shown once, scrypt hash + salt; status `registered`; "inactive" = every status except `active` (§4.2, §2.1) | Design form; no `register_worker(name, token)` — a caller-supplied token would put a secret in the call path |
| `record_share(worker_id, difficulty, hash, verified, local_test)` | `record_shares(worker_id, shares[])` batch, `origin` + `external_id` + `job_id` (§3.2) | `record_shares` primary; `record_share` wrapper preserves the brief's name/semantics (verified-gate, `local-test:<hash>` external_id) |
| `record_pool_stats(pool, hashrate, miners, height)` | `poll_pool_stats()` fetch + insert (§5.1) | Both: `poll_pool_stats` (live fetch) calls `record_pool_stats` (insert) |
| `start_session` / `end_session(worker_id)` | `record_worker_session` / `close_worker_session` (§5.2) | Design names primary; brief names kept as aliases |
| `log_decision(text)` | `log_decision(con, decision, reason)`, `dept='coordinator'` (§5.3) | Design form (decision + reason; a decision without a reason is a failed audit entry) |
| Schema change only if needed, backup first | Stage 1 migration specified exactly (§2) | Applied as specified; backup §3 |
| No cron | No cron; 10-min cadence is a scheduling decision for the parent (§6.3) | **No cron job created** |

## 3. Real-DB changes (the only writes to the real DB)

- **Backup first:** `~/workspace/atlas/backups/atlas-2026-11-18-pre-mission5.db` (176,128 B, SQLite backup API). Verified: integrity `ok`, `user_version` 1, all 9 Stage 0 tables 0 rows, decisions 76 at backup time.
- **Pre-migration (live):** integrity `ok`, `user_version` 1, all 9 Stage 0 tables 0 rows — confirmed, not assumed (design §9 handoff).
- **Migration applied** in one transaction (`sqlite3 data/atlas.db < core/migrate_mission5_stage1.sql`). **Post-migration:** integrity `ok`, `user_version` **2**, all new columns + 3 new indexes present, Stage 0 tables still 0 rows. No rollback needed.
- **Live pass** (`python3 core/atlas_coordinator.py pass --force-poll`): MoneroOcean `/pool/stats` fetched live (first attempt hit the 10 s timeout once during probing; the module's retry succeeded in ~1 s). **One `pool_stats` row inserted:** MoneroOcean, hashrate **265,452,841 H/s**, miners **4,979**, block height **3,808,993**, network_hashrate NULL (not supplied), block_reward 600,000,000,000 piconero, fee 0 bps, recorded 2026-11-18 10:27:17 EST. A second `pass` (poll not due) inserted no second row.
- **Decisions added (dept='coordinator', 3 total):** `pool-stats-polled`, `coordinator-pass-complete` ×2.
- **Final real-DB state:** integrity `ok`, `user_version` 2; users **0**, workers **0**, shares **0**, ledger **0**, payouts **0**, referrals **0**, achievements **0**, sessions **0**, pool_stats **1**. Safety unchanged: stop ON, mining disabled, trading paper-only, capital $0, pool-rewards simulation-only.
- **No other writes:** `config/atlas.json` and `config/pool-rewards.json` untouched (read-only as required). Artifact, wallet center, miner prototype untouched. No wallets/keys created, nothing spent.

## 4. Tests — temp DB only (never the real DB)

Test script: `/tmp/atlas_m5_test.py` (stdlib `unittest` + simulation; temp copies in `/tmp`). The test source is the pre-migration backup (the live DB is now v2, so re-applying the migration to a live copy correctly fails on duplicate columns).

**Unit tests: 18/18 PASS** (1.1 s), each on a fresh migrated copy:

- Registration: desktop token issued once, scrypt-only storage (plaintext token absent from the whole DB file bytes), verify true/false; browser no token; name/type/user/uniqueness validation; same name for a different user allowed.
- Rotate/revoke: old token invalid after rotate, new valid; revoke sets status + token_status `revoked`, token invalid, rotate refused after revoke; browser rotate refused.
- Shares: 5 local-test shares (4 accepted / 1 rejected) → attribution weight `{}` (zero), status counts split correctly; `verified=False` records nothing; dedupe skips the 2nd identical share; cross-worker `external_id` → batch rejected + worker `suspended`; unknown/revoked worker batch rejected; local-test without `local-test:` prefix rejected; NULL-difficulty pool share flagged in the decision log.
- Sessions: browser-probe session (marker hash, owner user_id, ref stored), close idempotent; desktop-agent same-ref re-check-in idempotent, different-ref → `worker-token-conflict` + suspended; expired sessions close lazily.
- Activation gate: stop ON → `worker-activation-held`, worker stays `registered`.
- Pool stats: fake-opener success maps hashRate 262,107,921.50… → **262,107,922** H/s, miners 4,975, height 3,808,993, network NULL, fee 0, reward 600e9; failure streak 1→2→3 logs `pool-stats-unavailable` exactly once at 3, no duplicate at 4, success resets the streak; direct `record_pool_stats` validates int-or-None.
- State/export/pass: status counts correct, hashrate `not-measured`/`measured_hps null`, `pool_connected false`, `user_version 2`, `mode simulation-only`; second export identical except `exported_at`; `run_pass` inserts 1 pool row, checks 1 activation (0 activated), logs `coordinator-pass-complete`.

**Simulation (fresh temp DB): register → record shares → pool stats → sessions → decisions — PASS.**
Desktop `sim-rig1` + browser `sim-tab1` registered; 6 local-test shares (5 accepted / 1 rejected) + 2 simulated pool shares recorded; attribution weights `{1: 10000}` (pool-accepted only); pool poll inserted 1 row; browser-probe + desktop-agent sessions opened and closed; activation check → `emergency-stop`, not activated; `run_pass` summary: 2 workers (0 active), pool 2/0, local-test 5/1, sessions 0 active; ledger/payouts/referrals/achievements 0 rows; `coordinator.json` hashrate `not-measured`; 7 coordinator decisions. All test/sim data stayed in `/tmp`.

**Fix found by testing:** first `run_pass` exported `coordinator.json` *before* logging `coordinator-pass-complete`, so `last_coordinator_pass_at` was null after the first pass. Fixed by logging pass-complete before the (single) export; re-tested 18/18 + simulation; the real DB was re-passed (poll skipped, not due) to regenerate the export with the pass time set.

**Diagnostics (existing suite, run after the migration): 22/22 PASS, 0 FAIL** on a clean retry (see §6 for the transient failure on the first two runs).

## 5. Design deviations (all forced, documented in the module docstring)

- **D-M5-1 — browser-probe `session_token_hash`:** design §2.3/§5.2 says it is NULL, but Stage 0 declares the column NOT NULL and the design specifies no rebuild. Browser-probe rows store the literal marker `none:browser-probe` — explicitly not a hash, never a secret, never mirrored (mirror never carries the column, §1.4). Desktop-agent sessions store a real sha256 hex token hash.
- **D-M5-2 — `pool-stats-polled` success decision:** the design's decision list (§5.3) has no success decision, but "3 consecutive failures" must persist across invocations with no extra state file. This module logs `pool-stats-polled` on every success so the streak derives from the decisions table (the audit trail). `pool-stats-unavailable` fires when the streak reaches exactly 3.
- **D-M5-3 — SupportXMR fallback NOT implemented:** design §5.1 specifies a fallback after 3 consecutive primary failures, but gives no verified SupportXMR stats-API endpoint URL (only that the site returned 200 after a 301), and a URL must never be guessed. After 3 consecutive MoneroOcean failures the module logs `pool-stats-unavailable` and degrades to the last good row. Fallback is owed pending the exact endpoint URL.

## 6. Diagnostics note — transient test-10 failure (not caused by this lane)

Two diagnostics runs during this lane showed test 10 FAIL ("daemon did not stop on SIGTERM") — the first (orphaned by an exec-service restart mid-run) at 20/22 with test 20 also failing (2 daemons `[5802, 5826]` found), the second (clean, detached) at 21/22 with test 10 the only failure. Evidence this is a pre-existing transient race, not a Mission 5 effect: this lane touched no daemon/diagnostics/recover code and no config, and the migration only adds columns to tables the daemon never writes; a direct manual test showed the daemon dies on SIGTERM in **<0.2 s** and `recover.sh` restarts it cleanly; test 10 kills only `pids[0]` and expects zero daemons, so it fails whenever a transient second daemon exists (the orphaned run proved duplication happens around overlapping diagnostics runs / service restarts / the 5-min watchdog). **Clean retry: 22/22 PASS, 0 FAIL** (2026-11-18 10:33:21 UTC), exactly 1 daemon (pid 6416 at the time), snapshot fresh. Final state after the retry: 1 daemon, snapshot age seconds, DB integrity `ok`.

## 7. What was NOT done (out of scope, per brief + design)

- No cron job, no watchdog entry for the coordinator (scheduling is the parent's decision).
- No artifact work: no `ingestCoordinatorState` action, no `getMining` extension, no `CoordinatorSection.tsx` (another lane; this lane delivers only `data/coordinator.json` as the bridge payload).
- No SupportXMR fallback (D-M5-3), no reward-engine computation, no payout flow, no treasury, no user-auth build-out, no in-browser registration, no artifact→host write path.
- No pool connection for earning, no stratum, no share submission, no mining activation on any host, no miner process spawned.
- Refresh failure and stale "no miner yet" copy noted only, not repaired (separate authorizations).
- Diagnostics additions proposed by design §9 (coordinator tests in the suite) not added — the existing 22 stay green; adding tests is a follow-up with its own numbering decision.

## 8. Open items / handoffs

1. **Scheduling:** `python3 core/atlas_coordinator.py pass` every 10 minutes (cron) + a `recover.sh`-style watchdog entry, per design §6.3 — needs the parent's decision (explicitly not created here).
2. **Artifact lane:** consume `data/coordinator.json` via `ingestCoordinatorState` + `CoordinatorSection.tsx` per design §7 (exact headings/copy, hashrate rule, dedupe keys §1.4). Mirror must never carry token hashes/salts, session token hashes, or password hashes.
3. **SupportXMR fallback endpoint URL** needed before D-M5-3 can be closed.
4. **Gate 1 still unmeasured** — every hashrate figure reads "not measured"; no probe run was done or fabricated.
5. **Test script location:** `/tmp/atlas_m5_test.py` is ephemeral scratch; if the parent wants the suite kept, it should be copied into the repo (not done here — not requested).

## 9. Files

- `~/workspace/atlas/core/atlas_coordinator.py` (new)
- `~/workspace/atlas/core/migrate_mission5_stage1.sql` (new)
- `~/workspace/atlas/data/coordinator.json` (new, derived export)
- `~/workspace/atlas/backups/atlas-2026-11-18-pre-mission5.db` (new, pre-migration backup)
- `~/workspace/atlas/docs/master-mission5-lane-c-coordinator-report-2026-11-18.md` (this report)
