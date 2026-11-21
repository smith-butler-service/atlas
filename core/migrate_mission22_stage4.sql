-- ATLAS Master Mission 22, Stage 4 — paper-trading engine migration
-- (schema version 5).
-- Design: docs/master-mission22-trading-design.md (D-M22-6).
-- Back up data/atlas.db first (backups/atlas-2026-11-20-pre-mission22.db),
-- verify integrity + user_version before and after. Single transaction.
-- Money is integer USD cents for cash and integer base units for coins
-- (XMR piconero 10^12; KAS/RVN/ERG 10^8 units), never float.
-- All timestamps are Unix epoch integers, matching existing convention.
-- Funding rule v2 (user order 2026-11-20 ~17:30 EST): eligible capital =
-- realized net mining profits + confirmed USDC deposits on Solana only.
-- The deposit address slot lives in config/trading.json (null until the
-- user provides it); this migration carries no address and no keys.

PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS trading_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('paper')),
    initial_virtual_usd_cents INTEGER NOT NULL CHECK (initial_virtual_usd_cents >= 0),
    source TEXT NOT NULL CHECK (source IN ('virtual-simulation')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','closed')),
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS trading_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES trading_accounts(id),
    order_ref TEXT NOT NULL UNIQUE,
    ts INTEGER NOT NULL,
    coin TEXT NOT NULL CHECK (coin IN ('xmr','kas','rvn','erg')),
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
CREATE INDEX IF NOT EXISTS idx_trading_orders_account_id
    ON trading_orders(account_id);
CREATE INDEX IF NOT EXISTS idx_trading_orders_coin_ts
    ON trading_orders(coin, ts);

CREATE TABLE IF NOT EXISTS trading_prices (
    coin TEXT PRIMARY KEY CHECK (coin IN ('xmr','kas','rvn','erg')),
    price_usd TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at INTEGER NOT NULL,
    stale INTEGER NOT NULL DEFAULT 0 CHECK (stale IN (0,1))
);

CREATE TABLE IF NOT EXISTS trading_deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_signature TEXT NOT NULL UNIQUE,
    deposit_address TEXT NOT NULL,             -- the Solana address the transfer went to; must equal the configured deposit address
    amount_usdc_micro INTEGER NOT NULL CHECK (amount_usdc_micro > 0),
    amount_usd_cents INTEGER NOT NULL CHECK (amount_usd_cents >= 0),
    remainder_micro INTEGER NOT NULL DEFAULT 0 CHECK (remainder_micro >= 0),
    confirmed_at INTEGER NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('solana-usdc')),
    status TEXT NOT NULL CHECK (status IN ('confirmed')),
    note TEXT
);

PRAGMA user_version = 5;

COMMIT;
