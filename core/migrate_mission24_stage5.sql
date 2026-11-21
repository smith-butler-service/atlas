-- ATLAS Master Mission 24, Stage 5 — live-trading ledger migration
-- (schema version 6).
-- Design: docs/master-mission23-live-trading-design.md (D-M23-7);
-- build: docs/master-mission24-live-trading-design.md (D-M24-1 to D-M24-8).
-- Back up data/atlas.db first (backups/atlas-2026-11-20-pre-mission24.db),
-- verify integrity + user_version before and after. Single transaction.
-- Money is integer USD cents for cash and integer base units for coins
-- (XMR piconero 10^12; KAS/ERG 10^8 units), never float.
-- All timestamps are Unix epoch integers, matching existing convention.
-- Live rows are kept strictly separate from the paper tables
-- (trading_*): paper and live never share a balance. Live orders are
-- append-only with UNIQUE(client_order_id); rejected orders are
-- recorded too, so every refusal is auditable. There is NO function
-- in the live module that moves funds off the exchange — no live
-- table, column, or code path represents an off-exchange transfer.

PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS live_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_order_id TEXT NOT NULL UNIQUE,
    exchange_order_id TEXT,
    ts INTEGER NOT NULL,
    symbol TEXT NOT NULL CHECK (symbol IN ('XMR/USDT','KAS/USDT','ERG/USDT')),
    coin TEXT NOT NULL CHECK (coin IN ('xmr','kas','erg')),
    side TEXT NOT NULL CHECK (side IN ('buy','sell')),
    qty_base_units INTEGER NOT NULL CHECK (qty_base_units > 0),
    price_usd TEXT,
    price_source TEXT,
    price_fetched_at INTEGER,
    price_stale INTEGER NOT NULL DEFAULT 0 CHECK (price_stale IN (0,1)),
    cost_usd_cents INTEGER,
    fee_usd_cents INTEGER NOT NULL DEFAULT 0 CHECK (fee_usd_cents >= 0),
    status TEXT NOT NULL CHECK (status IN ('placed','filled','partial','rejected','cancelled','unknown')),
    reject_reason TEXT,
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_live_orders_symbol_ts
    ON live_orders(symbol, ts);
CREATE INDEX IF NOT EXISTS idx_live_orders_status
    ON live_orders(status);

CREATE TABLE IF NOT EXISTS live_fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    live_order_id INTEGER NOT NULL REFERENCES live_orders(id),
    exchange_fill_id TEXT NOT NULL UNIQUE,
    ts INTEGER NOT NULL,
    symbol TEXT NOT NULL CHECK (symbol IN ('XMR/USDT','KAS/USDT','ERG/USDT')),
    side TEXT NOT NULL CHECK (side IN ('buy','sell')),
    qty_base_units INTEGER NOT NULL CHECK (qty_base_units > 0),
    price_usd TEXT NOT NULL,
    fee_usd_cents INTEGER NOT NULL DEFAULT 0 CHECK (fee_usd_cents >= 0),
    fee_currency TEXT
);
CREATE INDEX IF NOT EXISTS idx_live_fills_order_id
    ON live_fills(live_order_id);
CREATE INDEX IF NOT EXISTS idx_live_fills_ts
    ON live_fills(ts);

CREATE TABLE IF NOT EXISTS live_balances_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    currency TEXT NOT NULL,
    balance_base_units INTEGER NOT NULL CHECK (balance_base_units >= 0),
    available_base_units INTEGER NOT NULL CHECK (available_base_units >= 0),
    holds_base_units INTEGER NOT NULL CHECK (holds_base_units >= 0),
    source TEXT NOT NULL CHECK (source IN ('kucoin-accounts','manual')),
    CHECK (available_base_units + holds_base_units = balance_base_units)
);
CREATE INDEX IF NOT EXISTS idx_live_balances_ts_currency
    ON live_balances_snapshot(ts, currency);

CREATE TABLE IF NOT EXISTS live_reconciliation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    ok INTEGER NOT NULL CHECK (ok IN (0,1)),
    detail TEXT NOT NULL
);

PRAGMA user_version = 6;

COMMIT;
