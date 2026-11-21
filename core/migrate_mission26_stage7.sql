-- ATLAS Master Mission 26, Stage 7 — widen trading coin CHECKs for
-- the four Mission 26 rotation coins (schema version 7).
-- Design: docs/master-mission26-pump-rotation-report-2026-11-20.md
-- (D-M26). Back up data/atlas.db first
-- (backups/atlas-2026-11-20-pre-mission26.db), verify integrity +
-- user_version before and after. Single transaction. SQLite cannot
-- ALTER a CHECK constraint, so both tables are rebuilt with identical
-- columns and rows (standard 12-step rebuild); the two trading_orders
-- indexes are recreated. No rows are added, removed, or changed.
-- Paper-only: this migration touches no live-trading tables and does
-- not apply Mission 24's Stage 5 migration (cancelled).

PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

CREATE TABLE trading_orders_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES trading_accounts(id),
    order_ref TEXT NOT NULL UNIQUE,
    ts INTEGER NOT NULL,
    coin TEXT NOT NULL CHECK (coin IN ('xmr','kas','rvn','erg','fiona','buttcoin','penny','chud','butthole','smoove')),
    side TEXT NOT NULL CHECK (side IN ('buy','sell')),
    qty_base_units INTEGER NOT NULL CHECK (qty_base_units > 0),
    price_usd TEXT,
    price_source TEXT,
    price_fetched_at INTEGER,
    price_stale INTEGER NOT NULL DEFAULT 0 CHECK (price_stale IN (0,1)),
    cost_usd_cents INTEGER,
    fee_usd_cents INTEGER NOT NULL DEFAULT 0 CHECK (fee_usd_cents >= 0),
    status TEXT NOT NULL CHECK (status IN ('filled','rejected')),
    reject_reason TEXT,
    mode TEXT NOT NULL CHECK (mode IN ('paper')),
    note TEXT
);
INSERT INTO trading_orders_new SELECT * FROM trading_orders;
DROP TABLE trading_orders;
ALTER TABLE trading_orders_new RENAME TO trading_orders;
CREATE INDEX idx_trading_orders_account_id
    ON trading_orders(account_id);
CREATE INDEX idx_trading_orders_coin_ts
    ON trading_orders(coin, ts);

CREATE TABLE trading_prices_new (
    coin TEXT PRIMARY KEY CHECK (coin IN ('xmr','kas','rvn','erg','fiona','buttcoin','penny','chud','butthole','smoove')),
    price_usd TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at INTEGER NOT NULL,
    stale INTEGER NOT NULL DEFAULT 0 CHECK (stale IN (0,1))
);
INSERT INTO trading_prices_new SELECT * FROM trading_prices;
DROP TABLE trading_prices;
ALTER TABLE trading_prices_new RENAME TO trading_prices;

PRAGMA user_version = 7;

COMMIT;

PRAGMA foreign_keys = ON;
