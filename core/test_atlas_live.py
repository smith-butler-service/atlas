#!/usr/bin/env python3
"""ATLAS Master Mission 24 — live-trading engine tests.

Runs ONLY against temp copies of atlas.db in /tmp. NEVER writes to the
real ~/workspace/atlas/data/atlas.db. The real DB is copied from the
PRE-MIGRATION backup (user_version 1), the Stage 1 migration is applied,
then Stage 2, Stage 3, Stage 4 (Mission 22), and Stage 5 (Mission 24) —
all test/sim data lives in /tmp. (Same fixture pattern as
core/test_atlas_trading.py.)

Live network is NEVER attempted: every KuCoin call goes through an
injected fake `http` callable, so the placement / confirmation /
reconciliation paths are exercised deterministically. Credentials in
these tests are dummy strings ("test-..."), never real keys.

Test plan (design D-M23-4 to D-M23-9, build D-M24-1 to D-M24-8):
  (a) Stage 5 migration — temp DB reaches user_version 6, integrity
      ok, the four live tables exist, UNIQUE(client_order_id) holds.
  (b) Config enforcement — load_live_config returns the Mission 24
      defaults (enabled false, XMR/KAS/ERG, $5 cap, $10 minimum,
      $5 daily loss limit); a bad exchange, a non-allowed pair, a
      non-positive cap, or a non-boolean enabled is refused.
  (c) KuCoin signing — sign_request and encrypt_passphrase match
      independent HMAC-SHA256 vectors.
  (d) Quantity math — base units <-> decimal size round-trips for
      XMR (12 decimals), KAS and ERG (8 decimals).
  (e) Refusals are recorded — disabled, emergency stop ON, below
      minimum capital, over the per-order cap, no credentials, and a
      stale price each produce a rejected row with a reason and a
      logged decision, and NO HTTP call is made.
  (f) Full placement path (fake exchange) — with every gate passing,
      place_live_order places, confirms the fill, records the fill,
      snapshots balances, and reconciles to a baseline ok.
  (g) Duplicate client_order_id raises; bad coin / side / qty / ref
      raise.
  (h) Reconciliation mismatch halts — a second reconcile with wrong
      exchange balances records ok=0, and the next order is refused
      with reconciliation-halt.
  (i) Daily loss limit — FIFO realized P&L at -$5.00 blocks a new
      order; the FIFO math itself is unit-tested.
  (j) Export — payload carries the live state + fills, and contains
      no secret-trigger strings.
  (k) No off-exchange transfer path — the live module, migration,
      and config contain no "withdraw" substring, and there is no
      function that moves funds off the exchange.
  (l) Confirmation failure leaves the order 'placed' (never assumed
      filled) with a logged decision.
  (m) set_enabled flips the config and logs the decision; the
      kill-switch (disable) takes effect immediately.

Usage: python3 core/test_atlas_live.py [-v]
"""
import base64
import hashlib
import hmac
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.expanduser("~/workspace/atlas/core"))
import atlas_live as lv
import atlas_trading as tr

SRC_DB = os.path.expanduser(
    "~/workspace/atlas/backups/atlas-2026-11-18-pre-mission5.db")
MIGRATIONS = [os.path.expanduser(
    f"~/workspace/atlas/core/migrate_mission{m}.sql") for m in (
    "5_stage1", "6_stage2", "11_stage3", "22_stage4", "24_stage5")]
REAL_ATLAS_CFG = os.path.expanduser("~/workspace/atlas/config/atlas.json")
REAL_TRADING_CFG = os.path.expanduser(
    "~/workspace/atlas/config/trading.json")

# A valid 64-byte base58 transaction signature (shape-valid only).
VALID_TX_SIG = ("1GMkH3brNXiNNs1tiFZHu4yZSRrzJwxi5wB9bHFtMinfCXNnR1adh8Vo8N"
                "TheK4evneedH4qmvjeqcBBNAefgS")
SIG_B = ("67rZaavrqDqjSkwQYdccw7DZoq9ipp7Pqcak6SkP9nno1gH9zkh6eQ3KWDYHJLyV"
         "RVrP73Gu6NDvjMtNPAh1VC7y")


def fresh_db(path):
    if os.path.exists(path):
        os.remove(path)
    shutil.copy2(SRC_DB, path)
    con = sqlite3.connect(path)
    for migration in MIGRATIONS:
        with open(migration) as f:
            con.executescript(f.read())
    con.commit()
    uv = con.execute("PRAGMA user_version").fetchone()[0]
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()
    assert uv == 6, f"user_version after Stage 5 migration: {uv}"
    assert integ == "ok", f"integrity after Stage 5 migration: {integ}"
    return path


def table_count(con, table):
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def decision_count(con, decision):
    return con.execute(
        "SELECT COUNT(*) FROM decisions WHERE decision = ?",
        (decision,)).fetchone()[0]


class FakeKuCoin:
    """Deterministic KuCoin stand-in. `accounts` is the balance list
    returned by GET /api/v1/accounts; `order_status` and `fills`
    control the confirmation path. Every call is recorded."""

    def __init__(self, price="450.00", accounts=None, order_status=None,
                 fills=None, fail_on=None):
        self.price = price
        self.accounts = accounts if accounts is not None else []
        self.order_status = order_status if order_status is not None else {
            "status": "done", "dealSize": "0.002"}
        self.fills = fills if fills is not None else [{
            "tradeId": "fill-1", "orderId": "kucoin-order-1",
            "symbol": "XMR-USDT", "side": "buy", "price": "450.00",
            "size": "0.002", "funds": "0.90", "fee": "0.0009",
            "feeCurrency": "USDT", "createdAt": 1795215000000}]
        self.fail_on = fail_on or set()
        self.calls = []

    def __call__(self, method, path, params=None, body=None, signed=True):
        self.calls.append((method, path, params, body))
        if path in self.fail_on:
            raise ConnectionError(f"fake failure on {path}")
        if path == "/api/v1/market/orderbook/level1":
            return {"price": self.price}
        if path == "/api/v1/orders" and method == "POST":
            return {"orderId": "kucoin-order-1"}
        if path.startswith("/api/v1/orders/"):
            return dict(self.order_status)
        if path == "/api/v1/fills":
            return {"items": list(self.fills)}
        if path == "/api/v1/accounts":
            return list(self.accounts)
        raise AssertionError(f"unexpected fake call {method} {path}")


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="atlas-m24-live-")
        self.db_path = os.path.join(self.tmpdir, "test.db")
        fresh_db(self.db_path)
        self.con = lv.connect(self.db_path)
        # Temp configs (copies of the real ones, flipped as needed).
        with open(REAL_ATLAS_CFG) as f:
            atlas_cfg = json.load(f)
        atlas_cfg["emergency_stop"] = True
        atlas_cfg.setdefault("trading", {})["eligible_capital_usd"] = 0
        self.atlas_cfg_path = os.path.join(self.tmpdir, "atlas.json")
        with open(self.atlas_cfg_path, "w") as f:
            json.dump(atlas_cfg, f)
        with open(REAL_TRADING_CFG) as f:
            trading_cfg = json.load(f)
        self.trading_cfg_path = os.path.join(self.tmpdir, "trading.json")
        with open(self.trading_cfg_path, "w") as f:
            json.dump(trading_cfg, f)
        self.live_cfg_path = os.path.join(self.tmpdir, "live_trading.json")
        self._write_live_config(enabled=False)
        self.export_path = os.path.join(self.tmpdir, "live_trading.json")
        self._orig = {
            "lv_atlas": lv.CFG_ATLAS, "lv_live": lv.CFG_LIVE,
            "lv_export": lv.EXPORT, "tr_atlas": tr.CFG_ATLAS,
            "tr_trading": tr.CFG_TRADING, "tr_fetch": tr._fetch_prices,
        }
        lv.CFG_ATLAS = self.atlas_cfg_path
        lv.CFG_LIVE = self.live_cfg_path
        lv.EXPORT = self.export_path
        tr.CFG_ATLAS = self.atlas_cfg_path
        tr.CFG_TRADING = self.trading_cfg_path
        tr._fetch_prices = lambda: {"xmr": Decimal("500.00"),
                                    "kas": Decimal("0.025"),
                                    "erg": Decimal("0.20")}
        self._orig_env = {}
        for key in (lv.ENV_KEY, lv.ENV_SECRET, lv.ENV_PASSPHRASE):
            self._orig_env[key] = os.environ.pop(key, None)

    def tearDown(self):
        lv.CFG_ATLAS = self._orig["lv_atlas"]
        lv.CFG_LIVE = self._orig["lv_live"]
        lv.EXPORT = self._orig["lv_export"]
        tr.CFG_ATLAS = self._orig["tr_atlas"]
        tr.CFG_TRADING = self._orig["tr_trading"]
        tr._fetch_prices = self._orig["tr_fetch"]
        for key, value in self._orig_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.con.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- helpers ---------------------------------------------------------
    def _write_live_config(self, enabled=False, cap=500, min_cap=1000,
                           loss=500, pairs=None):
        cfg = {"exchange": "kucoin", "enabled": enabled, "mode": "live-gated",
               "version": "0.1.0-mission24",
               "allowed_pairs": pairs or ["XMR/USDT", "KAS/USDT",
                                          "ERG/USDT"],
               "per_order_cap_usd_cents": cap,
               "daily_loss_limit_usd_cents": loss,
               "min_capital_usd_cents": min_cap}
        with open(self.live_cfg_path, "w") as f:
            json.dump(cfg, f)
        return cfg

    def _set_stop(self, on):
        with open(self.atlas_cfg_path) as f:
            cfg = json.load(f)
        cfg["emergency_stop"] = on
        with open(self.atlas_cfg_path, "w") as f:
            json.dump(cfg, f)

    def _set_creds(self):
        os.environ[lv.ENV_KEY] = "test-key"
        os.environ[lv.ENV_SECRET] = "test-secret"
        os.environ[lv.ENV_PASSPHRASE] = "test-passphrase"

    def _deposit(self, amount_micro, sig=VALID_TX_SIG):
        return tr.record_deposit(self.con, sig, amount_micro)

    def _gates_open(self, deposit_micro=10000000):
        """Open every gate except the price/credentials ones: live
        enabled, stop OFF, capital >= $10 (deposit $10 by default:
        10,000,000 micro-USDC = 1000 cents)."""
        self._write_live_config(enabled=True)
        self._set_stop(False)
        self._deposit(deposit_micro)

    def _seed_live_fill(self, coin, side, qty, price, fee=0,
                        order_id=1, client_ref="seed-1", ts=None):
        """Insert one live order + one fill directly (test seeding)."""
        ts = ts or int(time.time())
        self.con.execute("BEGIN IMMEDIATE")
        cur = self.con.execute(
            """INSERT INTO live_orders
                   (client_order_id, exchange_order_id, ts, symbol, coin,
                    side, qty_base_units, price_usd, price_source,
                    price_fetched_at, price_stale, cost_usd_cents,
                    fee_usd_cents, status, reject_reason, note)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,'filled',NULL,NULL)""",
            (client_ref, f"kucoin-{client_ref}", ts,
             lv.COIN_SYMBOLS[coin], coin, side, qty, str(price),
             "test-seed", ts, 0,
             lv._order_cost_cents(qty, price, coin)))
        order_row = cur.lastrowid
        self.con.execute(
            """INSERT INTO live_fills
                   (live_order_id, exchange_fill_id, ts, symbol, side,
                    qty_base_units, price_usd, fee_usd_cents,
                    fee_currency)
               VALUES (?,?,?,?, ?,?,?,?,?)""",
            (order_row, f"fill-{client_ref}", ts,
             lv.COIN_SYMBOLS[coin], side, qty, str(price), fee, "USDT"))
        self.con.execute("COMMIT")
        return order_row

    # -- (a) migration ---------------------------------------------------
    def test_migration_user_version_and_live_tables(self):
        uv = self.con.execute("PRAGMA user_version").fetchone()[0]
        self.assertEqual(uv, 6)
        tables = {r[0] for r in self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ("live_orders", "live_fills",
                      "live_balances_snapshot", "live_reconciliation"):
            self.assertIn(table, tables)
        # UNIQUE(client_order_id) holds.
        self.con.execute("BEGIN IMMEDIATE")
        self.con.execute(
            "INSERT INTO live_orders (client_order_id, ts, symbol, coin, "
            "side, qty_base_units, status) VALUES ('dup-1', 1, 'XMR/USDT', "
            "'xmr', 'buy', 1000, 'rejected')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute(
                "INSERT INTO live_orders (client_order_id, ts, symbol, "
                "coin, side, qty_base_units, status) VALUES ('dup-1', 1, "
                "'XMR/USDT', 'xmr', 'buy', 1000, 'rejected')")
        self.con.execute("ROLLBACK")

    # -- (b) config enforcement ------------------------------------------
    def test_config_defaults(self):
        cfg = lv.load_live_config()
        self.assertEqual(cfg["exchange"], "kucoin")
        self.assertFalse(cfg["enabled"])
        self.assertEqual(cfg["allowed_pairs"],
                         ["XMR/USDT", "KAS/USDT", "ERG/USDT"])
        self.assertEqual(cfg["per_order_cap_usd_cents"], 500)
        self.assertEqual(cfg["min_capital_usd_cents"], 1000)
        self.assertEqual(cfg["daily_loss_limit_usd_cents"], 500)

    def test_config_rejects_bad_exchange_and_pair(self):
        self._write_live_config(pairs=["XMR/USDT", "RVN/USDT"])
        with self.assertRaises(lv.LiveError):
            lv.load_live_config()
        cfg = self._write_live_config()
        cfg["exchange"] = "binance"
        with open(self.live_cfg_path, "w") as f:
            json.dump(cfg, f)
        with self.assertRaises(lv.LiveError):
            lv.load_live_config()

    def test_config_rejects_bad_caps_and_enabled(self):
        self._write_live_config(cap=0)
        with self.assertRaises(lv.LiveError):
            lv.load_live_config()
        cfg = self._write_live_config()
        cfg["enabled"] = "yes"
        with open(self.live_cfg_path, "w") as f:
            json.dump(cfg, f)
        with self.assertRaises(lv.LiveError):
            lv.load_live_config()

    # -- (c) KuCoin signing ----------------------------------------------
    def test_hmac_sign_vector(self):
        secret = "test-secret"
        ts_ms = "1700000000000"
        method = "POST"
        endpoint = "/api/v1/orders"
        body = '{"symbol":"XMR-USDT"}'
        expected = base64.b64encode(hmac.new(
            secret.encode(), f"{ts_ms}{method}{endpoint}{body}".encode(),
            hashlib.sha256).digest()).decode()
        self.assertEqual(lv.sign_request(secret, ts_ms, method, endpoint,
                                         body), expected)

    def test_passphrase_encrypt_vector(self):
        expected = base64.b64encode(hmac.new(
            b"test-secret", b"test-passphrase",
            hashlib.sha256).digest()).decode()
        self.assertEqual(lv.encrypt_passphrase("test-secret",
                                               "test-passphrase"), expected)

    # -- (d) quantity math -----------------------------------------------
    def test_qty_decimal_round_trip(self):
        self.assertEqual(lv._qty_to_decimal(2000000000, "xmr"),
                         Decimal("0.002"))
        self.assertEqual(lv._decimal_to_base_units("0.002", "xmr"),
                         2000000000)
        self.assertEqual(lv._decimal_to_base_units("1", "kas"), 10 ** 8)
        self.assertEqual(lv._decimal_to_base_units("1.5", "erg"),
                         150000000)
        self.assertEqual(lv._qty_to_decimal(10 ** 8, "kas"), Decimal("1"))

    # -- (e) refusals are recorded, no HTTP call -------------------------
    def test_place_refused_when_disabled(self):
        fake = FakeKuCoin()
        order = lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                                    "ref-disabled", http=fake)
        self.assertEqual(order["status"], "rejected")
        self.assertIn("live-disabled", order["reject_reason"])
        # The price probe may run, but NO order is ever placed.
        self.assertFalse(any(m == "POST" for m, *_ in fake.calls))
        self.assertEqual(table_count(self.con, "live_orders"), 1)
        self.assertEqual(decision_count(self.con, "live-order-rejected"), 1)

    def test_place_refused_when_stop_on(self):
        self._write_live_config(enabled=True)
        fake = FakeKuCoin()
        order = lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                                    "ref-stop", http=fake)
        self.assertEqual(order["status"], "rejected")
        self.assertIn("emergency-stop-on", order["reject_reason"])
        self.assertFalse(any(m == "POST" for m, *_ in fake.calls))

    def test_place_refused_below_min_capital(self):
        self._write_live_config(enabled=True)
        self._set_stop(False)
        self._deposit(5720000)  # $5.72, the real capital at Mission 24 start
        fake = FakeKuCoin()
        order = lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                                    "ref-mincap", http=fake)
        self.assertEqual(order["status"], "rejected")
        self.assertIn("below-min-capital", order["reject_reason"])

    def test_place_refused_over_per_order_cap(self):
        self._gates_open()
        fake = FakeKuCoin()
        # 0.02 XMR @ $450 = $9.00 > $5 cap.
        order = lv.place_live_order(self.con, "xmr", "buy", 20000000000,
                                    "ref-cap", http=fake)
        self.assertEqual(order["status"], "rejected")
        self.assertIn("over-per-order-cap", order["reject_reason"])

    def test_place_refused_without_credentials(self):
        self._gates_open()
        fake = FakeKuCoin()
        order = lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                                    "ref-creds", http=fake)
        self.assertEqual(order["status"], "rejected")
        self.assertIn("no-credentials", order["reject_reason"])

    def test_place_refused_on_stale_price(self):
        self._gates_open()
        self._set_creds()
        # KuCoin ticker fails AND the CoinGecko fetch fails, so the
        # seeded price is the only price — and it is stale.
        self.con.execute("BEGIN IMMEDIATE")
        self.con.execute(
            "INSERT INTO trading_prices (coin, price_usd, source, "
            "fetched_at, stale) VALUES ('xmr', '500.00', "
            "'CoinGecko simple/price', ?, 1)",
            (int(time.time()) - 7200,))
        self.con.execute("COMMIT")
        orig_fetch = tr._fetch_prices
        # _fetch_prices never raises by contract (it returns None on
        # failure); an empty result means "no fresh price anywhere".
        tr._fetch_prices = lambda: None

        class NoTicker(FakeKuCoin):
            def __call__(self, method, path, params=None, body=None,
                         signed=True):
                if path == "/api/v1/market/orderbook/level1":
                    raise ConnectionError("ticker down")
                return super().__call__(method, path, params, body, signed)

        try:
            order = lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                                        "ref-stale", http=NoTicker())
        finally:
            tr._fetch_prices = orig_fetch
        self.assertEqual(order["status"], "rejected")
        self.assertIn("stale-price", order["reject_reason"])

    # -- (f) full placement path (fake exchange) -------------------------
    def test_place_succeeds_with_fake_exchange(self):
        self._gates_open()
        self._set_creds()
        fake = FakeKuCoin(accounts=[
            {"currency": "USDT", "balance": "9.10", "available": "9.10",
             "holds": "0"},
            {"currency": "XMR", "balance": "0.002", "available": "0.002",
             "holds": "0"}])
        order = lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                                    "live-1", http=fake)
        self.assertEqual(order["status"], "filled")
        self.assertEqual(order["exchange_order_id"], "kucoin-order-1")
        self.assertEqual(order["cost_usd_cents"], 90)  # 0.002 * $450
        self.assertEqual(table_count(self.con, "live_orders"), 1)
        self.assertEqual(table_count(self.con, "live_fills"), 1)
        self.assertEqual(table_count(self.con, "live_balances_snapshot"), 2)
        self.assertEqual(table_count(self.con, "live_reconciliation"), 1)
        self.assertEqual(decision_count(self.con, "live-order-placed"), 1)
        self.assertEqual(decision_count(self.con, "live-order-filled"), 1)
        self.assertEqual(decision_count(self.con, "live-reconciliation-ok"),
                         1)
        recon = lv._latest_reconciliation(self.con)
        self.assertTrue(recon["ok"])
        self.assertIn("baseline", recon["detail"])
        self.assertEqual(lv.live_positions(self.con),
                         {"xmr": 2000000000})

    # -- (g) duplicates and invalid inputs -------------------------------
    def test_duplicate_client_order_id_raises(self):
        self._gates_open()
        self._set_creds()
        fake = FakeKuCoin(accounts=[
            {"currency": "USDT", "balance": "9.10", "available": "9.10",
             "holds": "0"},
            {"currency": "XMR", "balance": "0.002", "available": "0.002",
             "holds": "0"}])
        lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                            "live-dup", http=fake)
        with self.assertRaises(lv.LiveError):
            lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                                "live-dup", http=fake)

    def test_invalid_inputs_raise(self):
        fake = FakeKuCoin()
        with self.assertRaises(lv.LiveError):
            lv.place_live_order(self.con, "rvn", "buy", 1000, "bad-coin",
                                http=fake)
        with self.assertRaises(lv.LiveError):
            lv.place_live_order(self.con, "xmr", "hold", 1000, "bad-side",
                                http=fake)
        with self.assertRaises(lv.LiveError):
            lv.place_live_order(self.con, "xmr", "buy", 0, "bad-qty",
                                http=fake)
        with self.assertRaises(lv.LiveError):
            lv.place_live_order(self.con, "xmr", "buy", 1000, "  ",
                                http=fake)

    # -- (h) reconciliation mismatch halts -------------------------------
    def test_reconciliation_mismatch_halts(self):
        self._gates_open()
        self._set_creds()
        good = FakeKuCoin(accounts=[
            {"currency": "USDT", "balance": "9.10", "available": "9.10",
             "holds": "0"},
            {"currency": "XMR", "balance": "0.002", "available": "0.002",
             "holds": "0"}])
        lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                            "live-m1", http=good)
        # Second reconcile: the exchange now reports WRONG balances.
        bad = FakeKuCoin(accounts=[
            {"currency": "USDT", "balance": "9.00", "available": "9.00",
             "holds": "0"},
            {"currency": "XMR", "balance": "0.001", "available": "0.001",
             "holds": "0"}])
        result = lv.reconcile(self.con, http=bad)
        self.assertFalse(result["ok"])
        self.assertIn("MISMATCH", result["detail"])
        self.assertEqual(decision_count(self.con,
                                        "live-reconciliation-mismatch"), 1)
        # The next order is refused by the reconciliation halt.
        order = lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                                    "live-m2", http=good)
        self.assertEqual(order["status"], "rejected")
        self.assertIn("reconciliation-halt", order["reject_reason"])

    # -- (i) daily loss limit / FIFO P&L ---------------------------------
    def test_realized_pnl_fifo(self):
        # Buy 0.002 XMR @ $450 (90c), sell 0.001 @ $400 (40c):
        # realized = 40 - 45 = -5c.
        self._seed_live_fill("xmr", "buy", 2000000000,
                             Decimal("450.00"), client_ref="fifo-b")
        self._seed_live_fill("xmr", "sell", 1000000000,
                             Decimal("400.00"), client_ref="fifo-s")
        self.assertEqual(lv._realized_pnl_today_cents(self.con), -5)

    def test_daily_loss_limit_blocks(self):
        # Buy 0.1 XMR @ $450 ($45.00), sell 0.1 @ $400 ($40.00):
        # realized -$5.00 = exactly the daily limit -> blocked.
        self._seed_live_fill("xmr", "buy", 100000000000,
                             Decimal("450.00"), client_ref="loss-b")
        self._seed_live_fill("xmr", "sell", 100000000000,
                             Decimal("400.00"), client_ref="loss-s")
        self.assertEqual(lv._realized_pnl_today_cents(self.con), -500)
        self._gates_open()
        self._set_creds()
        fake = FakeKuCoin()
        order = lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                                    "ref-loss", http=fake)
        self.assertEqual(order["status"], "rejected")
        self.assertIn("daily-loss-limit-breached", order["reject_reason"])

    # -- (j) export --------------------------------------------------------
    def test_export_has_no_secrets(self):
        self._gates_open()
        self._set_creds()
        fake = FakeKuCoin(accounts=[
            {"currency": "USDT", "balance": "9.10", "available": "9.10",
             "holds": "0"},
            {"currency": "XMR", "balance": "0.002", "available": "0.002",
             "holds": "0"}])
        lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                            "live-x1", http=fake)
        payload = lv.export_live(self.con)
        self.assertTrue(os.path.exists(self.export_path))
        with open(self.export_path) as f:
            text = f.read()
        lowered = text.lower()
        for trigger in lv.SECRET_TRIGGERS:
            self.assertNotIn(trigger, lowered)
        self.assertEqual(payload["live_trading"]["exchange"], "kucoin")
        self.assertEqual(len(payload["fills"]), 1)

    # -- (k) no off-exchange transfer path --------------------------------
    def test_no_off_exchange_transfer_function(self):
        for path in (os.path.expanduser(
                         "~/workspace/atlas/core/atlas_live.py"),
                     os.path.expanduser(
                         "~/workspace/atlas/core/migrate_mission24_stage5.sql"),
                     os.path.expanduser(
                         "~/workspace/atlas/config/live_trading.json")):
            with open(path) as f:
                text = f.read().lower()
            self.assertNotIn("withdraw", text, path)
        # No function in the live module moves funds off the exchange.
        self.assertFalse(any("withdraw" in name.lower()
                             for name in dir(lv)))

    # -- (l) confirmation failure leaves order placed ---------------------
    def test_confirm_failure_leaves_order_placed(self):
        self._gates_open()
        self._set_creds()
        fake = FakeKuCoin(fail_on={"/api/v1/orders/kucoin-order-1"})
        order = lv.place_live_order(self.con, "xmr", "buy", 2000000000,
                                    "live-cf", http=fake)
        self.assertEqual(order["status"], "placed")
        self.assertEqual(table_count(self.con, "live_fills"), 0)
        self.assertEqual(decision_count(self.con,
                                        "live-order-confirm-failed"), 1)

    # -- (m) enable / disable ---------------------------------------------
    def test_set_enabled_flips_and_logs(self):
        self.assertFalse(lv.load_live_config()["enabled"])
        lv.set_enabled(True, self.con)
        self.assertTrue(lv.load_live_config()["enabled"])
        self.assertEqual(decision_count(self.con, "live-enabled"), 1)
        lv.set_enabled(False, self.con)
        self.assertFalse(lv.load_live_config()["enabled"])
        self.assertEqual(decision_count(self.con, "live-disabled"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
