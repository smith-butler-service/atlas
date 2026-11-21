-- ATLAS Master Mission 11, Stage 3 — record_shares bottleneck fix (schema version 4)
-- Design: docs/master-mission11-report-2026-11-18.md §2 (D-M11-2).
-- Root cause (Mission 10, L5): the cross-worker conflict check in
-- atlas_coordinator.record_shares() looks up shares by external_id
-- alone, but the only external_id index was the composite UNIQUE
-- (worker_id, external_id). SQLite cannot serve an external_id-only
-- lookup from a worker_id-leading index, so it did a full covering
-- index SCAN per share — O(n^2), 398.917 s at 1,000 workers /
-- 100,000 shares.
-- Fix: one partial index on external_id alone. The conflict check
-- becomes an indexed lookup (O(log n) per batch) and the per-batch
-- INSERT OR IGNORE dedupe keeps using the composite UNIQUE index.
-- Additive only: one new index, no table rebuild, no row changes,
-- no column changes. Live shares/workers are 0 rows, so zero data
-- risk; a pre-migration backup was taken first
-- (backups/atlas-2026-11-18-pre-mission11.db).
-- Amounts are integer piconero (1 XMR = 10^12 piconero), never float.
-- All timestamps are Unix epoch integers, matching existing convention.

PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

CREATE INDEX IF NOT EXISTS idx_shares_external_id
    ON shares(external_id) WHERE external_id IS NOT NULL;

PRAGMA user_version = 4;

COMMIT;
