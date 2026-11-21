-- ATLAS Master Mission 6, Stage 2 — reward accounting migration (schema version 3)
-- Design: docs/master-mission6-design.md §11. Applied by Lane C (host engine).
-- Back up data/atlas.db first (backups/atlas-YYYY-MM-DD-pre-mission6.db),
-- verify integrity + user_version before and after. Single transaction.
-- Amounts are integer piconero (1 XMR = 10^12 piconero), never float.
-- All timestamps are Unix epoch integers, matching existing convention.
--
-- DEVIATION D-M6-A (forced by SQLite, documented): the design's DDL says
--   ALTER TABLE payouts ADD COLUMN idempotency_key TEXT UNIQUE;
-- SQLite rejects a UNIQUE constraint in ADD COLUMN ("Cannot add a UNIQUE
-- column"). The migration therefore adds the plain column and enforces
-- uniqueness with an equivalent UNIQUE INDEX (idx_payouts_idempotency_key).
-- Same exactly-once guarantee, same constraint failure on a duplicate key.
-- Live ledger is EMPTY (0 rows), so the rebuild copies zero rows.

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

-- Payout idempotency key (preparatory; no payouts in M6). See D-M6-A above:
-- SQLite forbids UNIQUE in ADD COLUMN, so the column is added plain and the
-- uniqueness is enforced by the index below (identical guarantee).
ALTER TABLE payouts ADD COLUMN idempotency_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_payouts_idempotency_key
    ON payouts(idempotency_key) WHERE idempotency_key IS NOT NULL;

PRAGMA user_version = 3;

COMMIT;
