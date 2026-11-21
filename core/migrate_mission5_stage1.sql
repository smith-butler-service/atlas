-- ATLAS Master Mission 5, Stage 1 — coordinator migration (schema version 2)
-- Design: docs/master-mission5-design.md §2. Applied by Lane C (host coordinator).
-- Additive only: new columns + indexes. Does NOT alter any existing table's
-- rows or any existing column. Single transaction; back up data/atlas.db first.
-- Amounts are integer piconero (1 XMR = 10^12 piconero), never float.
-- All timestamps are Unix epoch integers, matching existing convention.

PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

-- 2.1 workers — token + telemetry columns (design §2.1)
ALTER TABLE workers ADD COLUMN token_hash TEXT;          -- scrypt hash, never plaintext (§4.2)
ALTER TABLE workers ADD COLUMN token_salt TEXT;          -- per-worker salt, hex
ALTER TABLE workers ADD COLUMN token_status TEXT NOT NULL DEFAULT 'active'
    CHECK (token_status IN ('active', 'revoked'));
ALTER TABLE workers ADD COLUMN reported_hashrate_hps INTEGER;  -- agent self-report ONLY; NULL = not measured (§7 rule)
ALTER TABLE workers ADD COLUMN last_seen_at INTEGER;     -- last agent/probe check-in, epoch; NULL = never
ALTER TABLE workers ADD COLUMN xmrig_version TEXT;       -- desktop only; NULL for browser
ALTER TABLE workers ADD COLUMN xmrig_sha256 TEXT;        -- desktop only; verified hash of the running binary (§4.1)
CREATE UNIQUE INDEX IF NOT EXISTS idx_workers_user_name ON workers(user_id, name);

-- 2.2 shares — origin + external identity, dedupe keys (design §2.2)
ALTER TABLE shares ADD COLUMN origin TEXT NOT NULL DEFAULT 'pool'
    CHECK (origin IN ('pool', 'local-test'));
ALTER TABLE shares ADD COLUMN external_id TEXT;         -- pool share id, or 'local-test:<session>:<seq>'
ALTER TABLE shares ADD COLUMN job_id TEXT;              -- pool job id / local-test job id; NULL if unknown
CREATE UNIQUE INDEX IF NOT EXISTS idx_shares_worker_external
    ON shares(worker_id, external_id) WHERE external_id IS NOT NULL;

-- 2.3 sessions — worker sessions without breaking user sessions (design §2.3)
ALTER TABLE sessions ADD COLUMN worker_id INTEGER REFERENCES workers(id);
ALTER TABLE sessions ADD COLUMN kind TEXT NOT NULL DEFAULT 'user'
    CHECK (kind IN ('user', 'worker'));
ALTER TABLE sessions ADD COLUMN ended_at INTEGER;       -- NULL = still open
ALTER TABLE sessions ADD COLUMN session_ref TEXT;        -- browser probe tab-session id, or agent session id; never a secret
CREATE INDEX IF NOT EXISTS idx_sessions_worker_id ON sessions(worker_id);

-- 2.4 No other schema changes: users, ledger, payouts, referrals,
-- achievements, pool_stats, decisions, metrics, events are unchanged.

PRAGMA user_version = 2;

COMMIT;
