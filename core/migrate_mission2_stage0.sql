-- ATLAS Master Mission 2, Stage 0 — database migration (schema version 1)
-- Adds 9 tables for the mining platform. Does NOT alter existing
-- tables (metrics, decisions, events). Single transaction.
-- Amounts are integer piconero (1 XMR = 10^12 piconero), never float.
-- All timestamps are Unix epoch integers, matching existing convention.

PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    email_verified INTEGER NOT NULL DEFAULT 0 CHECK (email_verified IN (0, 1)),
    password_hash TEXT,                       -- placeholder only; no real auth in this mission
    xmr_address TEXT,                         -- receiving XMR address; format-validated on write by app layer
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    worker_type TEXT NOT NULL CHECK (worker_type IN ('browser', 'desktop')),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'registered',
    registered_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL REFERENCES workers(id),
    difficulty INTEGER,
    accepted INTEGER NOT NULL CHECK (accepted IN (0, 1)),
    submitted_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type TEXT NOT NULL CHECK (entry_type IN ('user_allocation', 'atlas_share', 'fee', 'payout')),
    user_id INTEGER REFERENCES users(id),
    amount_piconero INTEGER NOT NULL,         -- integer piconero only, never float
    reference TEXT,                           -- related share id or pool reward batch reference
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS payouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount_piconero INTEGER NOT NULL,
    destination_address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'failed')),
    txid TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_user_id INTEGER NOT NULL REFERENCES users(id),
    referred_user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'pending',
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    achievement_key TEXT NOT NULL,
    awarded_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pool_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pool_name TEXT NOT NULL,
    recorded_at INTEGER NOT NULL,
    hashrate INTEGER,
    miners INTEGER,
    block_height INTEGER,
    network_hashrate INTEGER,
    block_reward_piconero INTEGER,            -- integer piconero only, never float
    pool_fee_bps INTEGER                      -- pool fee in basis points (integer), not a float percent
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    session_token_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);

-- Indexes: FK columns + time columns
CREATE INDEX IF NOT EXISTS idx_workers_user_id ON workers(user_id);
CREATE INDEX IF NOT EXISTS idx_workers_registered_at ON workers(registered_at);
CREATE INDEX IF NOT EXISTS idx_shares_worker_id ON shares(worker_id);
CREATE INDEX IF NOT EXISTS idx_shares_submitted_at ON shares(submitted_at);
CREATE INDEX IF NOT EXISTS idx_ledger_user_id ON ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_ledger_created_at ON ledger(created_at);
CREATE INDEX IF NOT EXISTS idx_payouts_user_id ON payouts(user_id);
CREATE INDEX IF NOT EXISTS idx_payouts_created_at ON payouts(created_at);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_created_at ON referrals(created_at);
CREATE INDEX IF NOT EXISTS idx_achievements_user_id ON achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_achievements_awarded_at ON achievements(awarded_at);
CREATE INDEX IF NOT EXISTS idx_pool_stats_recorded_at ON pool_stats(recorded_at);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

PRAGMA user_version = 1;

COMMIT;
