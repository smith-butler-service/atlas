#!/usr/bin/env python3
"""ATLAS LIVE-TRADING ENGINE — Master Mission 24 (host-side, stdlib only).

Implements docs/master-mission23-live-trading-design.md (D-M23-4 to
D-M23-9) as built in docs/master-mission24-live-trading-design.md
(D-M24-1 to D-M24-8). KuCoin spot trading, market orders only, with
the 8 refusal gates of D-M23-6 plus the reconciliation halt of
D-M23-7, all enforced in code. Building only: NO live order is placed
in this mission, and no order can be placed until every gate passes.

  - Venue: KuCoin only (D-M23-1). Allowed pairs XMR/USDT, KAS/USDT,
    ERG/USDT — spot only, no margin, no futures, no leverage, ever.
    RVN is NOT allowed (KuCoin delisted it 8 Oct 2026).
  - Config config/live_trading.json: exchange "kucoin", enabled FALSE
    by default (only the user enables it), per-order cap $5,
    daily loss limit $5, min capital $10, mode "live-gated".
    atlas.json and config/trading.json are NOT touched.
  - Credentials reach the engine ONLY through the environment
    (KUCOIN_API_KEY / KUCOIN_API_SECRET / KUCOIN_API_PASSPHRASE,
    set by the Secure Vault at run time). They are NEVER typed in
    chat, NEVER written in code, config, logs, memory, or any file.
    Any suspected exposure means rotate the key immediately.
  - Money is integer USD cents for cash and integer base units for
    coins (XMR piconero 10^12; KAS/ERG 10^8 units). Order cost is
    computed with Decimal and rounded HALF_UP to integer cents.
  - Live ledger (Stage 5, user_version 6): live_orders, live_fills,
    live_balances_snapshot, live_reconciliation — append-only,
    UNIQUE(client_order_id), kept strictly separate from the paper
    tables (trading_*). Paper and live never share a balance.
  - After every fill, exchange balances are fetched and reconciled
    against the internal ledger; a mismatch halts live trading
    (gate 9) and logs an alert decision.
  - There is deliberately NO function in this module that moves funds
    off the exchange: no endpoint, no table, no column, and no code
    path represents an off-exchange transfer. Moving funds off the
    exchange is always the user's manual action in the exchange UI.
  - Prices: KuCoin level-1 ticker first, CoinGecko fallback via
    atlas_trading.get_price (same fetch-with-fallback, never
    fabricated rule as D-M22-2). An order with no fresh price is
    refused.

Usage (CLI; --db defaults to the live DB — tests MUST pass a temp DB):
    python3 core/atlas_live.py status
    python3 core/atlas_live.py export
    python3 core/atlas_live.py place-order --coin xmr --side buy
        --qty <base-units> --ref <client-order-id>
    python3 core/atlas_live.py orders
    python3 core/atlas_live.py fills [--order <live-order-id>]
    python3 core/atlas_live.py balances
    python3 core/atlas_live.py reconcile
    python3 core/atlas_live.py enable    # user enables live (gates still apply)
    python3 core/atlas_live.py disable   # kill-switch: live off immediately

Stdlib only. Portable by copying ~/workspace/atlas.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

BASE = os.path.expanduser("~/workspace/atlas")
CORE = os.path.join(BASE, "core")
sys.path.insert(0, CORE)
import atlas_trading as tr  # noqa: E402  (eligible capital, prices, money math)

CFG_ATLAS = os.path.join(BASE, "config", "atlas.json")
CFG_LIVE = os.path.join(BASE, "config", "live_trading.json")
DB = os.path.join(BASE, "data", "atlas.db")
EXPORT = os.path.join(BASE, "data", "live_trading.json")

FETCH_TIMEOUT_S = 10
STALE_AFTER_S = 3600
BUSY_TIMEOUT_MS = 5000
USER_AGENT = "ATLAS-live/1.0"
KUCOIN_BASE_URL = "https://api.kucoin.com"
KUCOIN_API_VERSION = "2"

EXCHANGE = "kucoin"
LIVE_COINS = ("xmr", "kas", "erg")
COIN_SYMBOLS = {"xmr": "XMR/USDT", "kas": "KAS/USDT", "erg": "ERG/USDT"}
# KuCoin symbols use a hyphen: XMR-USDT.
KUCOIN_SYMBOLS = {"xmr": "XMR-USDT", "kas": "KAS-USDT", "erg": "ERG-USDT"}
COIN_DECIMALS = {"xmr": 12, "kas": 8, "erg": 8}
COIN_LABELS = {"xmr": "XMR", "kas": "KAS", "erg": "ERG"}

ENV_KEY = "KUCOIN_API_KEY"
ENV_SECRET = "KUCOIN_API_SECRET"
ENV_PASSPHRASE = "KUCOIN_API_PASSPHRASE"

# Secret-trigger strings the live export must never contain (t30).
SECRET_TRIGGERS = ("api_key", "api-key", "secret", "passphrase",
                   "password", "seed", "private key", "keypair",
                   "mnemonic", "token_hash", "token_salt")


class LiveError(ValueError):
    """Validation / safety refusal. Never carries a secret in its message."""


# ---------------------------------------------------------------------------
# Connection / config / audit
# ---------------------------------------------------------------------------

def connect(db_path=DB):
    """Open a connection with manual transaction control (autocommit mode),
    same pattern as atlas_trading.connect()."""
    con = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000.0)
    con.isolation_level = None
    con.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def load_live_config():
    """Read config/live_trading.json fresh on every call — never cached.
    Enforces the D-M23-5 shape: KuCoin only, allowed pairs a subset of
    the three spot pairs, caps positive integers, enabled a boolean."""
    with open(CFG_LIVE) as f:
        cfg = json.load(f)
    if cfg.get("exchange") != EXCHANGE:
        raise LiveError(
            f"live exchange must be {EXCHANGE!r}, got {cfg.get('exchange')!r}")
    if not isinstance(cfg.get("enabled"), bool):
        raise LiveError(
            f"live enabled must be a boolean, got {cfg.get('enabled')!r}")
    pairs = cfg.get("allowed_pairs")
    if not isinstance(pairs, list) or not pairs:
        raise LiveError("live allowed_pairs must be a non-empty list")
    allowed = {COIN_SYMBOLS[c] for c in LIVE_COINS}
    for pair in pairs:
        if pair not in allowed:
            raise LiveError(
                f"live pair {pair!r} is not an allowed spot pair "
                f"(allowed: {sorted(allowed)})")
    for key in ("per_order_cap_usd_cents", "daily_loss_limit_usd_cents",
                "min_capital_usd_cents"):
        value = cfg.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise LiveError(f"live {key} must be a positive integer, got {value!r}")
    return cfg


def load_atlas_config():
    with open(CFG_ATLAS) as f:
        return json.load(f)


def _now():
    return int(time.time())


def _log_decision(con, decision, reason):
    """Insert one audit row (dept='live'). Does NOT commit; the caller
    owns the transaction. A decision without a reason is a failed audit
    entry — reason is required and must name the evidence."""
    if not reason:
        raise LiveError("log_decision requires a non-empty reason")
    con.execute(
        "INSERT INTO decisions (ts, dept, decision, reason) VALUES (?,?,?,?)",
        (_now(), "live", decision, reason))


def _require_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise LiveError(f"{name} must be an integer, got {value!r}")
    return value


def _atomic_write_json(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Credentials — environment only, read at call time, never stored
# ---------------------------------------------------------------------------

def credentials_present():
    """True when all three credential values are present in the
    environment. The VALUES are never read here — presence only."""
    return bool(os.environ.get(ENV_KEY)
                and os.environ.get(ENV_SECRET)
                and os.environ.get(ENV_PASSPHRASE))


def _credentials():
    """Return (key, secret, passphrase). Raises when any is missing.
    Values are used only for the HMAC signature of the current call
    and are never logged, stored, or returned to a caller."""
    key = os.environ.get(ENV_KEY)
    secret = os.environ.get(ENV_SECRET)
    passphrase = os.environ.get(ENV_PASSPHRASE)
    if not key or not secret or not passphrase:
        raise LiveError(
            "KuCoin API credentials are not present in the environment "
            "(KUCOIN_API_KEY / KUCOIN_API_SECRET / KUCOIN_API_PASSPHRASE); "
            "credentials come from the Secure Vault only, never from a file")
    return key, secret, passphrase


# ---------------------------------------------------------------------------
# KuCoin REST client (stdlib only, HMAC-SHA256)
# ---------------------------------------------------------------------------

def sign_request(secret, timestamp_ms, method, endpoint, body=""):
    """KuCoin signature: base64(HMAC-SHA256(secret,
    timestamp + method + endpoint + body)). Returns the base64 string.
    Pure function — unit-tested against an independent HMAC vector."""
    message = f"{timestamp_ms}{method}{endpoint}{body}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), message,
                      hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def encrypt_passphrase(secret, passphrase):
    """KuCoin API v2 passphrase header: base64(HMAC-SHA256(secret,
    passphrase)). Pure function, unit-tested."""
    digest = hmac.new(secret.encode("utf-8"), passphrase.encode("utf-8"),
                      hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _kucoin_http(method, path, params=None, body=None, signed=True):
    """One KuCoin REST call. Returns the response `data` payload.
    Raises on any transport / HTTP / API error. `http` injection point
    for tests: pass a fake callable to the functions that need it."""
    url = KUCOIN_BASE_URL + path
    if params:
        query = "&".join(
            f"{k}={v}" for k, v in params.items())
        url += "?" + query
    payload = json.dumps(body) if body is not None else ""
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    if signed:
        key, secret, passphrase = _credentials()
        ts_ms = str(int(time.time() * 1000))
        endpoint = path
        if params:
            endpoint += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        headers["KC-API-KEY"] = key
        headers["KC-API-SIGN"] = sign_request(secret, ts_ms, method,
                                              endpoint, payload)
        headers["KC-API-TIMESTAMP"] = ts_ms
        headers["KC-API-PASSPHRASE"] = encrypt_passphrase(secret, passphrase)
        headers["KC-API-KEY-VERSION"] = KUCOIN_API_VERSION
    req = urllib.request.Request(url, data=payload.encode("utf-8") if body is not None else None,
                                 method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
            if resp.status != 200:
                raise urllib.error.HTTPError(url, resp.status, "non-200",
                                             None, None)
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise LiveError(f"KuCoin HTTP {exc.code} on {method} {path}: {exc}") from exc
    except Exception as exc:
        raise LiveError(f"KuCoin request failed ({method} {path}): {exc}") from exc
    if not isinstance(data, dict) or data.get("code") != "200000":
        raise LiveError(
            f"KuCoin API error on {method} {path}: "
            f"{str(data)[:200] if isinstance(data, dict) else 'unexpected shape'}")
    return data.get("data")


def get_accounts(http=None):
    """GET /api/v1/accounts — all balances (signed). Returns the list
    of account rows as returned by KuCoin."""
    call = http or _kucoin_http
    return call("GET", "/api/v1/accounts")


def get_ticker_price(coin, http=None):
    """KuCoin level-1 ticker price for a coin (public, unsigned).
    Returns a Decimal price or None when the call fails. Never raises,
    never fabricates — the caller falls back to CoinGecko."""
    symbol = KUCOIN_SYMBOLS[coin]
    call = http or _kucoin_http
    try:
        data = call("GET", "/api/v1/market/orderbook/level1",
                    params={"symbol": symbol}, signed=False)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    raw = data.get("price")
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        return None
    try:
        price = Decimal(str(raw))
    except InvalidOperation:
        return None
    return price if price > 0 else None


def get_live_price(con, coin, http=None):
    """The price to execute a live order at: KuCoin ticker first,
    CoinGecko fallback via atlas_trading.get_price (last recorded
    price, stale-flagged). Returns a dict like atlas_trading.get_price
    (price_usd Decimal, source, fetched_at, stale) — or None when no
    price exists anywhere. Never fabricates."""
    if coin not in LIVE_COINS:
        raise LiveError(f"unknown live coin {coin!r}")
    price = get_ticker_price(coin, http=http)
    if price is not None:
        return {"price_usd": price, "source": "KuCoin level1",
                "fetched_at": _now(), "stale": False}
    return tr.get_price(con, coin)


# ---------------------------------------------------------------------------
# Live ledger — derived positions, cash, realized P&L
# ---------------------------------------------------------------------------

def _order_cost_cents(qty_base_units, price_usd, coin):
    return tr._order_cost_cents(qty_base_units, price_usd, coin)


def live_positions(con):
    """Live holdings per coin, DERIVED from recorded fills only
    (buys minus sells, base units). Only nonzero positions returned.
    The coin lives on the order row, so fills are joined to orders."""
    held = {}
    for row in con.execute(
            "SELECT o.coin, f.side, f.qty_base_units FROM live_fills f "
            "JOIN live_orders o ON o.id = f.live_order_id").fetchall():
        qty = int(row["qty_base_units"])
        held[row["coin"]] = held.get(row["coin"], 0) + (
            qty if row["side"] == "buy" else -qty)
    return {coin: qty for coin, qty in held.items() if qty != 0}


def _realized_pnl_today_cents(con):
    """Realized P&L in USD cents for fills recorded since UTC midnight,
    FIFO-matched: each sell consumes the oldest open buy lots of the
    same coin; realized = sell proceeds − matched buy cost − sell fee.
    Buys open lots; sells with no open lot contribute their full
    proceeds as realized (no cost basis on record — conservative:
    counted as proceeds, not loss). Returns an int (negative = loss)."""
    day_start = _now() - (_now() % 86400)
    lots = {}  # coin -> list of [qty_remaining, cost_cents]
    pnl = 0
    for row in con.execute(
            "SELECT o.coin, f.side, f.qty_base_units, f.price_usd, "
            "f.fee_usd_cents FROM live_fills f "
            "JOIN live_orders o ON o.id = f.live_order_id "
            "WHERE f.ts >= ? ORDER BY f.ts, f.id",
            (day_start,)).fetchall():
        qty = int(row["qty_base_units"])
        price = Decimal(row["price_usd"])
        fee = int(row["fee_usd_cents"])
        if row["side"] == "buy":
            cost = _order_cost_cents(qty, price, row["coin"]) + fee
            lots.setdefault(row["coin"], []).append([qty, cost])
            continue
        # Sell: proceeds minus matched buy cost minus the sell fee.
        proceeds = _order_cost_cents(qty, price, row["coin"])
        remaining = qty
        matched_cost = 0
        queue = lots.setdefault(row["coin"], [])
        while remaining > 0 and queue:
            lot_qty, lot_cost = queue[0]
            take = min(remaining, lot_qty)
            matched_cost += lot_cost * take // lot_qty
            lot_qty -= take
            remaining -= take
            if lot_qty == 0:
                queue.pop(0)
            else:
                queue[0][0] = lot_qty
        pnl += proceeds - matched_cost - fee
    return pnl


def _latest_reconciliation(con):
    row = con.execute(
        "SELECT ok, detail, ts FROM live_reconciliation "
        "ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return {"ok": bool(row["ok"]), "detail": row["detail"], "ts": row["ts"]}


# ---------------------------------------------------------------------------
# Gates (D-M23-6 + reconciliation halt D-M23-7)
# ---------------------------------------------------------------------------

def check_gates(con, symbol, cost_usd_cents, price, live_cfg=None,
                atlas_cfg=None):
    """Evaluate every refusal gate. Returns a list of failed-gate
    reasons (empty = all gates pass). Read-only: never writes."""
    if live_cfg is None:
        live_cfg = load_live_config()
    if atlas_cfg is None:
        atlas_cfg = load_atlas_config()
    failures = []
    if not live_cfg.get("enabled"):
        failures.append("live-disabled: live trading is not enabled "
                        "(config/live_trading.json enabled is false)")
    if atlas_cfg.get("emergency_stop"):
        failures.append("emergency-stop-on: the emergency stop is ON — "
                        "live orders are refused while the stop is on")
    capital = tr.eligible_capital(con, atlas_cfg)
    if capital["total_usd_cents"] < live_cfg["min_capital_usd_cents"]:
        failures.append(
            f"below-min-capital: eligible capital "
            f"${capital['total_usd_cents'] / 100:.2f} is below the "
            f"${live_cfg['min_capital_usd_cents'] / 100:.2f} minimum")
    if cost_usd_cents > live_cfg["per_order_cap_usd_cents"]:
        failures.append(
            f"over-per-order-cap: order cost ${cost_usd_cents / 100:.2f} "
            f"exceeds the ${live_cfg['per_order_cap_usd_cents'] / 100:.2f} "
            "per-order cap")
    pnl = _realized_pnl_today_cents(con)
    if pnl <= -live_cfg["daily_loss_limit_usd_cents"]:
        failures.append(
            f"daily-loss-limit-breached: realized P&L today "
            f"${pnl / 100:.2f} is at or beyond the "
            f"-${live_cfg['daily_loss_limit_usd_cents'] / 100:.2f} limit")
    if symbol not in live_cfg["allowed_pairs"]:
        failures.append(
            f"pair-not-allowed: {symbol} is not in allowed_pairs "
            f"{live_cfg['allowed_pairs']}")
    if price is None:
        failures.append("no-live-price: no fresh price from KuCoin or "
                        "CoinGecko and no price ever recorded")
    elif price.get("stale") or (_now() - price["fetched_at"] > STALE_AFTER_S):
        failures.append("stale-price: the price is older than 1 h")
    if not credentials_present():
        failures.append("no-credentials: KuCoin API credentials are not "
                        "present in the environment (Secure Vault only)")
    recon = _latest_reconciliation(con)
    if recon is not None and not recon["ok"]:
        failures.append(
            f"reconciliation-halt: the latest balance reconciliation "
            f"MISMATCHED ({recon['detail']}); live trading is halted "
            "until the mismatch is resolved")
    return failures


# ---------------------------------------------------------------------------
# Live orders
# ---------------------------------------------------------------------------

def _qty_to_decimal(qty_base_units, coin):
    """Base units -> Decimal in whole coins (KuCoin `size` field)."""
    return Decimal(qty_base_units) / Decimal(10 ** COIN_DECIMALS[coin])


def _decimal_to_base_units(value, coin):
    """A KuCoin decimal amount (string/number) -> integer base units."""
    raw = Decimal(str(value)) * Decimal(10 ** COIN_DECIMALS[coin])
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _record_rejected(con, client_order_id, coin, symbol, side,
                     qty_base_units, price, cost_cents, reason, note=None):
    """Record a refused live order (status 'rejected') with its reason
    and a logged decision. Auditable, never silent."""
    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            """INSERT INTO live_orders
                   (client_order_id, exchange_order_id, ts, symbol, coin,
                    side, qty_base_units, price_usd, price_source,
                    price_fetched_at, price_stale, cost_usd_cents,
                    fee_usd_cents, status, reject_reason, note)
               VALUES (?,?, ?,?,?, ?,?,?, ?,?,?, ?, 0, 'rejected', ?, ?)""",
            (client_order_id, None, _now(), symbol, coin, side,
             qty_base_units,
             str(price["price_usd"]) if price else None,
             price["source"] if price else None,
             price["fetched_at"] if price else None,
             1 if price and price.get("stale") else 0,
             cost_cents, reason, note))
        order_id = cur.lastrowid
        _log_decision(
            con, "live-order-rejected",
            f"live order {client_order_id!r} refused ({symbol} {side} "
            f"{qty_base_units} base units): {reason}")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    return {"id": order_id, "client_order_id": client_order_id,
            "symbol": symbol, "coin": coin, "side": side,
            "qty_base_units": qty_base_units, "status": "rejected",
            "reject_reason": reason}


def place_live_order(con, coin, side, qty_base_units, client_order_id,
                     note=None, http=None):
    """Place ONE live market order on KuCoin — only when EVERY gate
    passes. Network I/O happens BEFORE any transaction opens, never
    while holding the DB lock. Returns the live order row dict.
    Refusals are RECORDED as rejected rows with a reason (auditable).
    A duplicate client_order_id raises (the original row is the audit
    trail). A placement that reaches the exchange but cannot be
    confirmed is recorded as status 'unknown' — never assumed filled.
    No order is placed in this mission: the live module is built and
    tested with mocked HTTP only, and every gate currently refuses
    (enabled is false, stop is ON, capital is below the minimum, no
    credentials are present)."""
    if coin not in LIVE_COINS:
        raise LiveError(f"unknown live coin {coin!r} (live: xmr/kas/erg)")
    if side not in ("buy", "sell"):
        raise LiveError(f"side must be 'buy' or 'sell', got {side!r}")
    _require_int("qty_base_units", qty_base_units)
    if qty_base_units <= 0:
        raise LiveError(
            f"qty_base_units must be > 0, got {qty_base_units}")
    if not isinstance(client_order_id, str) or not client_order_id.strip():
        raise LiveError("client_order_id must be a non-empty string")
    client_order_id = client_order_id.strip()
    symbol = COIN_SYMBOLS[coin]
    existing = con.execute(
        "SELECT id FROM live_orders WHERE client_order_id = ?",
        (client_order_id,)).fetchone()
    if existing is not None:
        raise LiveError(
            f"duplicate client_order_id {client_order_id!r} "
            f"(live order id {existing['id']})")

    live_cfg = load_live_config()
    atlas_cfg = load_atlas_config()
    price = get_live_price(con, coin, http=http)
    cost_cents = (_order_cost_cents(qty_base_units, price["price_usd"], coin)
                  if price is not None else None)
    failures = check_gates(con, symbol,
                           cost_cents if cost_cents is not None else 0,
                           price, live_cfg=live_cfg, atlas_cfg=atlas_cfg)
    if failures:
        return _record_rejected(
            con, client_order_id, coin, symbol, side, qty_base_units,
            price, cost_cents if cost_cents is not None else 0,
            "; ".join(failures), note=note)

    # All gates pass: place the market order on the exchange.
    call = http or _kucoin_http
    size = _qty_to_decimal(qty_base_units, coin)
    body = {"clientOid": client_order_id, "side": side,
            "symbol": KUCOIN_SYMBOLS[coin], "type": "market",
            "size": format(size.normalize(), "f")}
    try:
        placed = call("POST", "/api/v1/orders", body=body)
    except Exception as exc:
        try:
            con.execute("BEGIN IMMEDIATE")
            cur = con.execute(
                """INSERT INTO live_orders
                       (client_order_id, exchange_order_id, ts, symbol,
                        coin, side, qty_base_units, price_usd,
                        price_source, price_fetched_at, price_stale,
                        cost_usd_cents, fee_usd_cents, status,
                        reject_reason, note)
                   VALUES (?,?, ?,?,?, ?,?,?, ?,?,?, ?, 0, 'unknown',
                           ?, ?)""",
                (client_order_id, None, _now(), symbol, coin, side,
                 qty_base_units, str(price["price_usd"]),
                 price["source"], price["fetched_at"],
                 1 if price.get("stale") else 0, cost_cents,
                 f"placement failed: {exc}", note))
            order_id = cur.lastrowid
            _log_decision(
                con, "live-order-unknown",
                f"live order {client_order_id!r} placement failed "
                f"({symbol} {side} {qty_base_units} base units): {exc} — "
                "recorded as unknown, never assumed filled")
            con.execute("COMMIT")
        except Exception:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
            raise
        return {"id": order_id, "client_order_id": client_order_id,
                "symbol": symbol, "coin": coin, "side": side,
                "qty_base_units": qty_base_units, "status": "unknown",
                "reject_reason": f"placement failed: {exc}"}
    exchange_order_id = (placed or {}).get("orderId")
    if not isinstance(exchange_order_id, str) or not exchange_order_id:
        raise LiveError("KuCoin returned no orderId for the placed order")
    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            """INSERT INTO live_orders
                   (client_order_id, exchange_order_id, ts, symbol, coin,
                    side, qty_base_units, price_usd, price_source,
                    price_fetched_at, price_stale, cost_usd_cents,
                    fee_usd_cents, status, reject_reason, note)
               VALUES (?,?, ?,?,?, ?,?,?, ?,?,?, ?, 0, 'placed', NULL, ?)""",
            (client_order_id, exchange_order_id, _now(), symbol, coin,
             side, qty_base_units, str(price["price_usd"]),
             price["source"], price["fetched_at"],
             1 if price.get("stale") else 0, cost_cents, note))
        order_id = cur.lastrowid
        _log_decision(
            con, "live-order-placed",
            f"live order {client_order_id!r} placed on KuCoin "
            f"({symbol} {side} {qty_base_units} base units at "
            f"${price['price_usd']} [{price['source']}]; cost "
            f"{cost_cents} USD cents; exchange order {exchange_order_id})")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    order = {"id": order_id, "client_order_id": client_order_id,
             "exchange_order_id": exchange_order_id, "symbol": symbol,
             "coin": coin, "side": side, "qty_base_units": qty_base_units,
             "price_usd": str(price["price_usd"]),
             "price_source": price["source"],
             "price_fetched_at": price["fetched_at"],
             "price_stale": price.get("stale", False),
             "cost_usd_cents": cost_cents, "fee_usd_cents": 0,
             "status": "placed"}
    # Confirm the fill, record fills, reconcile balances.
    _confirm_order(con, order, http=http)
    return order


def _confirm_order(con, order, http=None):
    """Fetch the exchange order status + fills for a placed live order,
    record the fills, update the order status, and reconcile balances.
    Best effort on the network: a failed confirmation leaves the order
    'placed' (never assumed filled) and logs the gap."""
    call = http or _kucoin_http
    order_id = order["exchange_order_id"]
    try:
        status_data = call("GET", f"/api/v1/orders/{order_id}")
    except Exception as exc:
        _log_decision_standalone(
            con, "live-order-confirm-failed",
            f"live order {order['client_order_id']!r} (exchange "
            f"{order_id}): status fetch failed ({exc}) — order stays "
            "'placed', never assumed filled")
        return order
    status = (status_data or {}).get("status")
    deal_size = (status_data or {}).get("dealSize")
    try:
        fills_data = call("GET", "/api/v1/fills",
                          params={"orderId": order_id})
    except Exception as exc:
        _log_decision_standalone(
            con, "live-order-fills-failed",
            f"live order {order['client_order_id']!r} (exchange "
            f"{order_id}): fills fetch failed ({exc}) — fills not "
            "recorded yet; reconciliation will catch the gap")
        return order
    items = (fills_data or {}).get("items") or []
    filled_qty = 0
    total_fee_cents = 0
    try:
        con.execute("BEGIN IMMEDIATE")
        for item in items:
            trade_id = item.get("tradeId")
            if not isinstance(trade_id, str) or not trade_id:
                continue
            known = con.execute(
                "SELECT id FROM live_fills WHERE exchange_fill_id = ?",
                (trade_id,)).fetchone()
            if known is not None:
                continue
            fill_qty = _decimal_to_base_units(item.get("size"), order["coin"])
            fill_price = Decimal(str(item.get("price")))
            fee_currency = item.get("feeCurrency")
            fee_raw = item.get("fee")
            if fee_currency == "USDT" and fee_raw is not None:
                fee_cents = int((Decimal(str(fee_raw)) * 100).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP))
            else:
                fee_cents = 0
            con.execute(
                """INSERT INTO live_fills
                       (live_order_id, exchange_fill_id, ts, symbol, side,
                        qty_base_units, price_usd, fee_usd_cents,
                        fee_currency)
                   VALUES (?,?,?,?, ?,?,?,?,?)""",
                (order["id"], trade_id, _now(), order["symbol"],
                 order["side"], fill_qty, str(fill_price), fee_cents,
                 fee_currency))
            filled_qty += fill_qty
            total_fee_cents += fee_cents
        new_status = order["status"]
        if status == "done":
            new_status = ("filled" if filled_qty >= order["qty_base_units"]
                          else "partial")
        elif status == "active":
            new_status = "placed"
        else:
            new_status = "unknown"
        con.execute(
            "UPDATE live_orders SET status = ?, fee_usd_cents = ? "
            "WHERE id = ?", (new_status, total_fee_cents, order["id"]))
        _log_decision(
            con, "live-order-filled" if new_status == "filled"
            else "live-order-confirmed",
            f"live order {order['client_order_id']!r} (exchange "
            f"{order_id}): status {status} -> {new_status}; "
            f"{len(items)} fill(s), {filled_qty} base units filled, "
            f"fee {total_fee_cents} USD cents")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    order["status"] = new_status
    order["fee_usd_cents"] = total_fee_cents
    reconcile(con, http=http)
    return order


def _log_decision_standalone(con, decision, reason):
    """Log one decision in its own short transaction (used by
    best-effort confirmation paths)."""
    try:
        con.execute("BEGIN IMMEDIATE")
        _log_decision(con, decision, reason)
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise


# ---------------------------------------------------------------------------
# Reconciliation (D-M23-7)
# ---------------------------------------------------------------------------

def reconcile(con, http=None):
    """Fetch exchange balances, snapshot them, and reconcile against
    the internal ledger. The first snapshot establishes the baseline
    (ok, detail names it). Later snapshots compare: exchange coin
    balances vs holdings derived from live_fills, and the USDT change
    since the previous snapshot vs minus the net live spend from
    fills recorded in between (buys spend cost+fee; sells return
    cost-fee). The USDT check is delta-based, so no stored starting
    balance is needed — and a first snapshot taken after fills already
    exist is still a valid baseline, not a false mismatch. A mismatch
    records ok=0, logs an alert decision, and HALTS live trading
    (gate 9 refuses new orders until resolved). Returns the
    reconciliation dict."""
    call = http or _kucoin_http
    try:
        accounts = call("GET", "/api/v1/accounts")
    except Exception as exc:
        detail = f"balances fetch failed: {exc}"
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "INSERT INTO live_reconciliation (ts, ok, detail) "
                "VALUES (?,?,?)", (_now(), 0, detail))
            _log_decision(con, "live-reconciliation-mismatch", detail)
            con.execute("COMMIT")
        except Exception:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
            raise
        return {"ok": False, "detail": detail}
    if not isinstance(accounts, list):
        detail = "balances fetch returned an unexpected shape"
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "INSERT INTO live_reconciliation (ts, ok, detail) "
                "VALUES (?,?,?)", (_now(), 0, detail))
            _log_decision(con, "live-reconciliation-mismatch", detail)
            con.execute("COMMIT")
        except Exception:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
            raise
        return {"ok": False, "detail": detail}

    # Parse exchange balances: {currency: (balance, available, holds)}
    # in base units (coins) or USD cents (USDT).
    exchange = {}
    for row in accounts:
        if not isinstance(row, dict):
            continue
        currency = row.get("currency")
        if currency not in ("USDT", "XMR", "KAS", "ERG"):
            continue
        try:
            balance = Decimal(str(row.get("balance", "0")))
            available = Decimal(str(row.get("available", "0")))
            holds = Decimal(str(row.get("holds", "0")))
        except InvalidOperation:
            continue
        if currency == "USDT":
            scale = Decimal(100)
        else:
            scale = Decimal(10 ** COIN_DECIMALS[currency.lower()])
        exchange[currency] = (
            int((balance * scale).quantize(Decimal("1"),
                                           rounding=ROUND_HALF_UP)),
            int((available * scale).quantize(Decimal("1"),
                                             rounding=ROUND_HALF_UP)),
            int((holds * scale).quantize(Decimal("1"),
                                         rounding=ROUND_HALF_UP)))

    # Previous snapshot set: the latest row per currency, all stamped
    # with the same ts (one reconcile = one set). Empty on the first
    # run, when the snapshot below becomes the baseline.
    prev_ts = con.execute(
        "SELECT MAX(ts) FROM live_balances_snapshot").fetchone()[0]
    prev = {}
    if prev_ts is not None:
        prev = {row["currency"]: int(row["balance_base_units"])
                for row in con.execute(
                    "SELECT currency, balance_base_units "
                    "FROM live_balances_snapshot WHERE ts = ?",
                    (prev_ts,)).fetchall()}
    now = _now()
    try:
        con.execute("BEGIN IMMEDIATE")
        for currency, (balance, available, holds) in sorted(exchange.items()):
            con.execute(
                """INSERT INTO live_balances_snapshot
                       (ts, currency, balance_base_units,
                        available_base_units, holds_base_units, source)
                   VALUES (?,?, ?,?,?,'kucoin-accounts')""",
                (now, currency, balance, available, holds))
        if not prev:
            detail = ("baseline established from first balances fetch: "
                      + ", ".join(f"{c}={v[0]}" for c, v in sorted(exchange.items())))
            con.execute(
                "INSERT INTO live_reconciliation (ts, ok, detail) "
                "VALUES (?,?,?)", (_now(), 1, detail))
            _log_decision(con, "live-reconciliation-ok", detail)
            con.execute("COMMIT")
            return {"ok": True, "detail": detail}
        mismatches = []
        held = live_positions(con)
        for coin in ("xmr", "kas", "erg"):
            currency = COIN_LABELS[coin]
            exchange_qty = exchange.get(currency, (0, 0, 0))[0]
            internal_qty = held.get(coin, 0)
            if exchange_qty != internal_qty:
                mismatches.append(
                    f"{currency}: exchange {exchange_qty} vs internal "
                    f"{internal_qty} base units")
        # USDT: the change since the previous snapshot must equal
        # minus the net live spend from fills recorded in between
        # (buys spend cost+fee; sells return cost-fee). Delta-based,
        # so no stored starting balance is needed — and a first
        # snapshot taken after fills already exist is still a valid
        # baseline, not a false mismatch.
        if "USDT" in prev:
            net_spend = 0
            for row in con.execute(
                    "SELECT f.side, f.qty_base_units, f.price_usd, "
                    "f.fee_usd_cents, o.coin FROM live_fills f "
                    "JOIN live_orders o ON o.id = f.live_order_id "
                    "WHERE f.ts > ?", (prev_ts,)).fetchall():
                cost = _order_cost_cents(int(row["qty_base_units"]),
                                         Decimal(row["price_usd"]),
                                         row["coin"])
                fee = int(row["fee_usd_cents"])
                if row["side"] == "buy":
                    net_spend += cost + fee
                else:
                    net_spend -= (cost - fee)
            expected_usdt = prev["USDT"] - net_spend
            actual_usdt = exchange.get("USDT", (0, 0, 0))[0]
            if actual_usdt != expected_usdt:
                mismatches.append(
                    f"USDT: exchange {actual_usdt} vs expected "
                    f"{expected_usdt} USD cents (previous snapshot "
                    f"{prev['USDT']} minus net live spend {net_spend} "
                    "since then)")
        if mismatches:
            detail = "MISMATCH: " + "; ".join(mismatches)
            con.execute(
                "INSERT INTO live_reconciliation (ts, ok, detail) "
                "VALUES (?,?,?)", (_now(), 0, detail))
            _log_decision(con, "live-reconciliation-mismatch",
                          detail + " — live trading HALTED until resolved")
            con.execute("COMMIT")
            return {"ok": False, "detail": detail}
        detail = ("reconciled: exchange balances match the internal "
                  "ledger (positions "
                  + ", ".join(f"{c}={q}" for c, q in sorted(held.items()) or [("none", 0)])
                  + ")")
        con.execute(
            "INSERT INTO live_reconciliation (ts, ok, detail) "
            "VALUES (?,?,?)", (_now(), 1, detail))
        _log_decision(con, "live-reconciliation-ok", detail)
        con.execute("COMMIT")
        return {"ok": True, "detail": detail}
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise


# ---------------------------------------------------------------------------
# Status / export / enable / disable
# ---------------------------------------------------------------------------

def status(con, live_cfg=None, atlas_cfg=None):
    """Current live-trading state: config, capital, positions, orders,
    latest reconciliation, and which gates currently refuse an order
    (evaluated against a $0 cost so cost-based gates are neutral).
    Read-only."""
    if live_cfg is None:
        live_cfg = load_live_config()
    if atlas_cfg is None:
        atlas_cfg = load_atlas_config()
    capital = tr.eligible_capital(con, atlas_cfg)
    recon = _latest_reconciliation(con)
    gate_blockers = check_gates(
        con, live_cfg["allowed_pairs"][0], 0,
        {"price_usd": Decimal("1"), "source": "status-probe",
         "fetched_at": _now(), "stale": False},
        live_cfg=live_cfg, atlas_cfg=atlas_cfg)
    # The probe price is artificial: drop the price-related blockers
    # from the status view (a real order re-checks the real price).
    gate_blockers = [g for g in gate_blockers
                     if not g.startswith(("no-live-price",
                                          "stale-price"))]
    orders = [dict(r) for r in con.execute(
        "SELECT id, client_order_id, exchange_order_id, ts, symbol, coin, "
        "side, qty_base_units, price_usd, cost_usd_cents, fee_usd_cents, "
        "status, reject_reason FROM live_orders ORDER BY id").fetchall()]
    return {
        "exchange": live_cfg["exchange"],
        "enabled": live_cfg["enabled"],
        "mode": live_cfg.get("mode"),
        "emergency_stop": bool(atlas_cfg.get("emergency_stop")),
        "allowed_pairs": live_cfg["allowed_pairs"],
        "per_order_cap_usd_cents": live_cfg["per_order_cap_usd_cents"],
        "daily_loss_limit_usd_cents":
            live_cfg["daily_loss_limit_usd_cents"],
        "min_capital_usd_cents": live_cfg["min_capital_usd_cents"],
        "eligible_capital": capital,
        "realized_pnl_today_usd_cents": _realized_pnl_today_cents(con),
        "positions_base_units": live_positions(con),
        "orders": orders,
        "live_fills": con.execute(
            "SELECT COUNT(*) FROM live_fills").fetchone()[0],
        "latest_reconciliation": recon,
        "credentials_present": credentials_present(),
        "gate_blockers_now": gate_blockers,
    }


def export_live(con, live_cfg=None, atlas_cfg=None):
    """Export the live-trading state to data/live_trading.json
    (atomic write, same freshness rule as D-M22-8). The export
    contains NO secret strings — t30 checks the file against
    SECRET_TRIGGERS. Returns the payload dict."""
    state = status(con, live_cfg=live_cfg, atlas_cfg=atlas_cfg)
    fills = [dict(r) for r in con.execute(
        "SELECT id, live_order_id, exchange_fill_id, ts, symbol, side, "
        "qty_base_units, price_usd, fee_usd_cents, fee_currency "
        "FROM live_fills ORDER BY id").fetchall()]
    snapshots = [dict(r) for r in con.execute(
        "SELECT id, ts, currency, balance_base_units, "
        "available_base_units, holds_base_units, source "
        "FROM live_balances_snapshot ORDER BY id DESC LIMIT 20").fetchall()]
    payload = {
        "exported_at": _now(),
        "live_trading": state,
        "fills": fills,
        "recent_balance_snapshots": snapshots,
    }
    _atomic_write_json(EXPORT, payload)
    return payload


def set_enabled(enabled, con=None):
    """Flip live trading on/off in config/live_trading.json (atomic
    write, same pattern as set_emergency_stop). Does NOT commit to the
    DB itself when no connection is passed. When a connection is
    passed, the decision is logged in its own short transaction.
    Enabling never places an order — the gates still apply to every
    order, and the kill-switch (disable) takes effect immediately."""
    cfg = load_live_config()
    cfg["enabled"] = bool(enabled)
    _atomic_write_json(CFG_LIVE, cfg)
    if con is not None:
        _log_decision_standalone(
            con,
            "live-enabled" if enabled else "live-disabled",
            f"live trading {'ENABLED' if enabled else 'DISABLED'} by "
            f"explicit operator action (config/live_trading.json "
            f"enabled={'true' if enabled else 'false'}); "
            "the gates still apply to every order, and the emergency "
            "stop remains the kill-switch")
    return cfg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cmd_status(args):
    con = connect(args.db)
    try:
        st = status(con)
        print(f"exchange: {st['exchange']}  enabled: {st['enabled']}  "
              f"mode: {st['mode']}")
        print(f"emergency stop: {'ON' if st['emergency_stop'] else 'OFF'}")
        print(f"allowed pairs: {', '.join(st['allowed_pairs'])}  "
              f"per-order cap: ${st['per_order_cap_usd_cents'] / 100:.2f}  "
              f"daily loss limit: ${st['daily_loss_limit_usd_cents'] / 100:.2f}  "
              f"min capital: ${st['min_capital_usd_cents'] / 100:.2f}")
        cap = st["eligible_capital"]
        print(f"eligible capital: ${cap['total_usd_cents'] / 100:.2f} "
              f"(mining ${cap['mining_profits_usd_cents'] / 100:.2f} + deposits "
              f"${cap['usdc_deposits_usd_cents'] / 100:.2f})")
        print(f"realized P&L today: "
              f"${st['realized_pnl_today_usd_cents'] / 100:.2f}")
        print(f"positions: {st['positions_base_units'] or 'none'}  "
              f"live fills: {st['live_fills']}")
        recon = st["latest_reconciliation"]
        print("reconciliation: " + (recon["detail"] if recon
                                     else "none recorded yet"))
        print(f"credentials present: {st['credentials_present']}")
        if st["gate_blockers_now"]:
            print("gates refusing an order right now:")
            for blocker in st["gate_blockers_now"]:
                print(f"  - {blocker}")
        else:
            print("gates: all pass (a real order still needs a fresh "
                  "price and credentials)")
        for order in st["orders"]:
            print(f"  order {order['id']} {order['client_order_id']} "
                  f"{order['symbol']} {order['side']} "
                  f"{order['qty_base_units']} base units "
                  f"status={order['status']}")
    finally:
        con.close()


def _cmd_export(args):
    con = connect(args.db)
    try:
        payload = export_live(con)
        print(f"live export written: {EXPORT}")
        print(f"enabled: {payload['live_trading']['enabled']}  "
              f"orders: {len(payload['live_trading']['orders'])}  "
              f"fills: {len(payload['fills'])}")
    finally:
        con.close()


def _cmd_place_order(args):
    con = connect(args.db)
    try:
        order = place_live_order(
            con, args.coin, args.side, args.qty, args.ref, note=args.note)
        print(f"live order {order['client_order_id']}: "
              f"status={order['status']}")
        if order["status"] == "rejected":
            print(f"reason: {order['reject_reason']}")
        if order.get("exchange_order_id"):
            print(f"exchange order: {order['exchange_order_id']}")
    finally:
        con.close()


def _cmd_orders(args):
    con = connect(args.db)
    try:
        for row in con.execute(
                "SELECT id, client_order_id, exchange_order_id, ts, symbol, "
                "coin, side, qty_base_units, price_usd, cost_usd_cents, "
                "fee_usd_cents, status, reject_reason FROM live_orders "
                "ORDER BY id").fetchall():
            print(f"[{row['id']}] {row['client_order_id']} "
                  f"{row['symbol']} {row['side']} "
                  f"{row['qty_base_units']} base units @ "
                  f"{row['price_usd'] or '-'} "
                  f"cost={row['cost_usd_cents']}c fee={row['fee_usd_cents']}c "
                  f"status={row['status']}"
                  + (f" reason={row['reject_reason']}"
                     if row["reject_reason"] else ""))
    finally:
        con.close()


def _cmd_fills(args):
    con = connect(args.db)
    try:
        query = ("SELECT id, live_order_id, exchange_fill_id, ts, symbol, "
                 "side, qty_base_units, price_usd, fee_usd_cents, "
                 "fee_currency FROM live_fills")
        params = ()
        if args.order:
            query += " WHERE live_order_id = ?"
            params = (args.order,)
        query += " ORDER BY id"
        for row in con.execute(query, params).fetchall():
            print(f"[{row['id']}] order={row['live_order_id']} "
                  f"{row['symbol']} {row['side']} "
                  f"{row['qty_base_units']} base units @ {row['price_usd']} "
                  f"fee={row['fee_usd_cents']}c {row['fee_currency'] or ''} "
                  f"fill={row['exchange_fill_id']}")
    finally:
        con.close()


def _cmd_balances(args):
    con = connect(args.db)
    try:
        for row in con.execute(
                "SELECT id, ts, currency, balance_base_units, "
                "available_base_units, holds_base_units, source "
                "FROM live_balances_snapshot ORDER BY id DESC LIMIT 20"
                ).fetchall():
            print(f"[{row['id']}] {row['currency']} "
                  f"balance={row['balance_base_units']} "
                  f"available={row['available_base_units']} "
                  f"holds={row['holds_base_units']} source={row['source']}")
    finally:
        con.close()


def _cmd_reconcile(args):
    con = connect(args.db)
    try:
        result = reconcile(con)
        print(f"reconciliation ok={result['ok']}")
        print(result["detail"])
    finally:
        con.close()


def _cmd_enable(args):
    con = connect(args.db)
    try:
        set_enabled(True, con)
        print("live trading ENABLED (gates still apply to every order; "
              "the emergency stop remains the kill-switch)")
    finally:
        con.close()


def _cmd_disable(args):
    con = connect(args.db)
    try:
        set_enabled(False, con)
        print("live trading DISABLED — kill-switch on, no live order "
              "can be placed")
    finally:
        con.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="ATLAS live-trading engine (Mission 24, KuCoin spot, "
                    "gated, paper-first).")
    parser.add_argument("--db", default=DB,
                        help="path to atlas.db (default: live DB)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show live-trading state and gate blockers")
    sub.add_parser("export", help="write data/live_trading.json")
    p = sub.add_parser("place-order", help="place one live market order")
    p.add_argument("--coin", required=True, choices=LIVE_COINS)
    p.add_argument("--side", required=True, choices=("buy", "sell"))
    p.add_argument("--qty", required=True, type=int,
                   help="quantity in base units (XMR piconero; KAS/ERG 10^8)")
    p.add_argument("--ref", required=True,
                   help="client order id (unique)")
    p.add_argument("--note", default=None)
    sub.add_parser("orders", help="list live orders")
    p = sub.add_parser("fills", help="list live fills")
    p.add_argument("--order", type=int, default=None)
    sub.add_parser("balances", help="list recent balance snapshots")
    sub.add_parser("reconcile", help="fetch balances and reconcile")
    sub.add_parser("enable", help="enable live trading (gates still apply)")
    sub.add_parser("disable", help="kill-switch: disable live trading")
    args = parser.parse_args(argv)
    commands = {
        "status": _cmd_status,
        "export": _cmd_export,
        "place-order": _cmd_place_order,
        "orders": _cmd_orders,
        "fills": _cmd_fills,
        "balances": _cmd_balances,
        "reconcile": _cmd_reconcile,
        "enable": _cmd_enable,
        "disable": _cmd_disable,
    }
    try:
        commands[args.command](args)
    except LiveError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"DB ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
