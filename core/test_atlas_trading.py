#!/usr/bin/env python3
"""ATLAS Master Mission 22 — paper-trading engine tests.

Runs ONLY against temp copies of atlas.db in /tmp. NEVER writes to the
real ~/workspace/atlas/data/atlas.db. The real DB is copied from the
PRE-MIGRATION backup (user_version 1), the Stage 1 migration is applied,
then Stage 2, Stage 3, and the Stage 4 (Mission 22) migration — all
test/sim data lives in /tmp. (Same fixture pattern as
core/test_atlas_profitability.py.)

Live fetches are NEVER attempted: every price test monkeypatches the
module's _fetch_prices to return fixture prices or to fail, so the
fallback / rejection paths are exercised deterministically.

Test plan (design D-M22-1 to D-M22-7):
  (a) Stage 6 migration — temp DB reaches user_version 6, integrity
      ok, the four trading tables exist (Stage 4 + Stage 6 widening).
  (b) Config enforcement — load_configs refuses a deposit network
      other than Solana or a deposit token other than USDC.
  (c) Address validation — the configured Solana address passes; bad
      charset, wrong length, wrong decoded size, and EVM-style
      addresses fail.
  (d) Signature validation — a 64-byte base58 signature passes;
      short / bad-charset signatures fail.
  (e) Accounts — default $10,000 virtual; any source other than
      'virtual-simulation' refused; negative initial refused.
  (f) Order math — buy 0.001 XMR at $500.00 fills at exactly 50
      virtual cents; cash and positions derive correctly; sell
      returns proceeds; Decimal HALF_UP rounding (445.6 -> 446).
  (g) Refusals are recorded — insufficient virtual funds, insufficient
      holdings, and no-live-price each produce a rejected row with a
      reason and a logged decision; duplicate order_ref raises.
  (h) Stale price — a seeded price with a failed fetch still fills,
      with price_stale = 1 and the original fetched_at preserved.
  (i) Funding rule — eligible capital is $0 with no deposits;
      fund_from_capital always refuses and logs the refusal;
      record_deposit (valid signature, bound to the configured
      address) raises eligible capital by exactly the deposit; a
      sub-cent amount records with its remainder kept; duplicate
      signature, non-positive amount, bad signature, and recording
      without a configured address are refused. scan_deposits with
      a stubbed RPC records a new USDC transfer, skips an
      already-recorded signature and a failed transaction, and
      records nothing when the RPC fails.
  (j) Export — payload is paper-only, carries the deposit block and
      both eligible-capital sources, reconciles cash/positions from
      filled orders, and contains no secret-trigger strings.
  (k) Read-only proof — status + export change no table counts
      (decisions/ledger/orders/accounts) on a seeded temp DB.

Usage: python3 core/test_atlas_trading.py [-v]
"""
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
import atlas_trading as tr

SRC_DB = os.path.expanduser(
    "~/workspace/atlas/backups/atlas-2026-11-18-pre-mission5.db")
MIGRATION_1 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission5_stage1.sql")
MIGRATION_2 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission6_stage2.sql")
MIGRATION_3 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission11_stage3.sql")
MIGRATION_4 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission22_stage4.sql")
MIGRATION_6 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission25_stage6.sql")
MIGRATION_7 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission26_stage7.sql")

# Fixture prices (deterministic; no live fetch in tests).
FIXTURE_PRICES = {"xmr": Decimal("500.00"), "kas": Decimal("0.025"),
                  "rvn": Decimal("0.001"), "erg": Decimal("0.20")}
# A valid Solana address (the mission's configured deposit address —
# public, safe to use in tests).
VALID_ADDRESS = "5HpcbrtF1Gy7Ee2cRPqowWRYKM5HG1CfT22idECuJ7Ln"
# A valid 64-byte base58 transaction signature (86 chars, decodes to
# exactly 64 bytes — shape-valid, never a real transaction).
VALID_TX_SIG = ("1GMkH3brNXiNNs1tiFZHu4yZSRrzJwxi5wB9bHFtMinfCXNnR1adh8Vo8N"
                "TheK4evneedH4qmvjeqcBBNAefgS")
SIG_B = ("67rZaavrqDqjSkwQYdccw7DZoq9ipp7Pqcak6SkP9nno1gH9zkh6eQ3KWDYHJLyV"
         "RVrP73Gu6NDvjMtNPAh1VC7y")
SIG_C = ("4XR92Zct9ZodXzisJ4kov3upmTvMotYVrg65MHP8aoCjSPJwUa7vjaXK5VhDF7Z"
         "iiF16v7cY5BPazCLnVqZ3yzb")


def fresh_db(path):
    if os.path.exists(path):
        os.remove(path)
    shutil.copy2(SRC_DB, path)
    con = sqlite3.connect(path)
    for migration in (MIGRATION_1, MIGRATION_2, MIGRATION_3, MIGRATION_4,
                      MIGRATION_6, MIGRATION_7):
        with open(migration) as f:
            con.executescript(f.read())
    con.commit()
    uv = con.execute("PRAGMA user_version").fetchone()[0]
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()
    assert uv == 7, f"user_version after Stage 7 migration: {uv}"
    assert integ == "ok", f"integrity after Stage 4 migration: {integ}"
    return path


def table_count(con, table):
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


class TradingTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="atlas-m22-trading-")
        self.db_path = os.path.join(self.tmpdir, "test.db")
        fresh_db(self.db_path)
        self.con = tr.connect(self.db_path)
        self.now = int(time.time())
        self._orig_fetch = tr._fetch_prices
        tr._fetch_prices = lambda: dict(FIXTURE_PRICES)

    def tearDown(self):
        tr._fetch_prices = self._orig_fetch
        self.con.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- helpers ---------------------------------------------------------
    def _account(self, name="demo", cents=None):
        kwargs = {} if cents is None else {
            "initial_virtual_usd_cents": cents}
        return tr.create_account(self.con, name, **kwargs)

    def _seed_price(self, coin, price, fetched_at, stale=0):
        self.con.execute("BEGIN IMMEDIATE")
        self.con.execute(
            """INSERT INTO trading_prices
                   (coin, price_usd, source, fetched_at, stale)
               VALUES (?,?,?,?,?)""",
            (coin, str(price), "CoinGecko simple/price", fetched_at, stale))
        self.con.execute("COMMIT")

    # -- (a) migration ---------------------------------------------------
    def test_migration_user_version_and_tables(self):
        uv = self.con.execute("PRAGMA user_version").fetchone()[0]
        self.assertEqual(uv, 7)
        tables = {r[0] for r in self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ("trading_accounts", "trading_orders",
                      "trading_prices", "trading_deposits"):
            self.assertIn(table, tables)

    # -- (b) config enforcement ------------------------------------------
    def test_config_rejects_other_network_and_token(self):
        bad = {"deposit": {"network": "Ethereum", "token": "USDC",
                           "token_standard": "SPL", "address": None,
                           "status": "address-pending"},
               "fee_bps": 0, "mode": "paper-only",
               "price_stale_after_s": 3600,
               "virtual_starting_balance_usd_cents": 1000000}
        path = os.path.join(self.tmpdir, "trading-bad.json")
        with open(path, "w") as f:
            json.dump(bad, f)
        orig = tr.CFG_TRADING
        try:
            tr.CFG_TRADING = path
            with self.assertRaises(tr.TradingError):
                tr.load_configs()
            bad["deposit"]["network"] = "Solana"
            bad["deposit"]["token"] = "DAI"
            with open(path, "w") as f:
                json.dump(bad, f)
            with self.assertRaises(tr.TradingError):
                tr.load_configs()
        finally:
            tr.CFG_TRADING = orig

    def test_config_live_is_solana_usdc(self):
        _, cfg = tr.load_configs()
        dep = cfg["deposit"]
        self.assertEqual(dep["network"], "Solana")
        self.assertEqual(dep["token"], "USDC")
        self.assertEqual(dep["address"], VALID_ADDRESS)
        self.assertEqual(dep["status"], "configured")

    # -- (c) address validation -------------------------------------------
    def test_solana_address_validation(self):
        ok, _ = tr.validate_solana_address(VALID_ADDRESS)
        self.assertTrue(ok)
        for bad, why in (
                ("0x4735c9589c916Ef120B5fa2c0939a134E3079259",
                 "EVM-style address"),
                ("5HpcbrtF1Gy7Ee2cRPqowWRYKM5HG1CfT22idECuJ7L0",
                 "bad base58 char '0'"),
                ("5Hpc", "too short"),
                ("", "empty")):
            ok, reason = tr.validate_solana_address(bad)
            self.assertFalse(ok, f"{why} should fail: {bad!r} ({reason})")

    # -- (d) signature validation -----------------------------------------
    def test_tx_signature_validation(self):
        ok, _ = tr.validate_tx_signature(VALID_TX_SIG)
        self.assertTrue(ok)
        for bad in ("1" * 87, "1" * 88, "1" * 89, "0" * 88, ""):
            ok, _ = tr.validate_tx_signature(bad)
            self.assertFalse(ok, f"bad signature should fail: {bad!r}")

    # -- (e) accounts ------------------------------------------------------
    def test_create_account_defaults_and_source_gate(self):
        acc = self._account()
        self.assertEqual(acc["initial_virtual_usd_cents"], 1000000)
        self.assertEqual(acc["mode"], "paper")
        self.assertEqual(acc["source"], "virtual-simulation")
        with self.assertRaises(tr.TradingError):
            tr.create_account(self.con, "bad", source="mining-profits")
        with self.assertRaises(tr.TradingError):
            tr.create_account(self.con, "bad",
                              initial_virtual_usd_cents=-1)
        with self.assertRaises(tr.TradingError):
            tr.create_account(self.con, "   ")

    # -- (f) order math ------------------------------------------------------
    def test_buy_sell_math_and_derived_balances(self):
        acc = self._account()
        buy = tr.place_order(self.con, acc["id"], "xmr", "buy",
                             10 ** 9, "ord-001")  # 0.001 XMR @ $500
        self.assertEqual(buy["status"], "filled")
        self.assertEqual(buy["cost_usd_cents"], 50)
        self.assertEqual(buy["price_usd"], "500.00")
        self.assertFalse(buy["price_stale"])
        self.assertEqual(tr.cash_balance_cents(self.con, acc["id"]),
                         1000000 - 50)
        self.assertEqual(tr.positions(self.con, acc["id"]),
                         {"xmr": 10 ** 9})
        sell = tr.place_order(self.con, acc["id"], "xmr", "sell",
                              5 * 10 ** 8, "ord-002")
        self.assertEqual(sell["status"], "filled")
        self.assertEqual(sell["cost_usd_cents"], 25)
        self.assertEqual(tr.cash_balance_cents(self.con, acc["id"]),
                         1000000 - 50 + 25)
        self.assertEqual(tr.positions(self.con, acc["id"]),
                         {"xmr": 5 * 10 ** 8})

    def test_cost_rounding_half_up(self):
        # 0.01 XMR at $445.60 -> 445.6 cents -> 446 (HALF_UP, not floor).
        self.assertEqual(
            tr._order_cost_cents(10 ** 10, Decimal("445.60"), "xmr"), 446)
        self.assertEqual(
            tr._order_cost_cents(1, Decimal("445.60"), "xmr"), 0)

    # -- (g) refusals recorded ----------------------------------------------
    def test_refusals_recorded_with_reason(self):
        acc = self._account(cents=100)
        big = tr.place_order(self.con, acc["id"], "xmr", "buy",
                             10 ** 12, "ord-big")  # 1 XMR @ $500 > $1 cash
        self.assertEqual(big["status"], "rejected")
        self.assertIn("insufficient-virtual-funds",
                      big["reject_reason"])
        self.assertEqual(table_count(self.con, "trading_orders"), 1)
        no_hold = tr.place_order(self.con, acc["id"], "xmr", "sell",
                                 10 ** 9, "ord-nohold")
        self.assertEqual(no_hold["status"], "rejected")
        self.assertIn("insufficient-holdings", no_hold["reject_reason"])
        decisions = [r[0] for r in self.con.execute(
            "SELECT decision FROM decisions WHERE dept = 'trading'")]
        self.assertIn("trading-order-rejected", decisions)

    def test_no_price_rejects_never_fabricates(self):
        tr._fetch_prices = lambda: None  # live fetch fails entirely
        acc = self._account()
        order = tr.place_order(self.con, acc["id"], "xmr", "buy",
                               10 ** 9, "ord-noprice")
        self.assertEqual(order["status"], "rejected")
        self.assertIn("no-live-price", order["reject_reason"])
        self.assertIsNone(order.get("price_usd"))

    def test_duplicate_ref_and_bad_mode_raise(self):
        acc = self._account()
        tr.place_order(self.con, acc["id"], "xmr", "buy", 10 ** 9, "ord-1")
        with self.assertRaises(tr.TradingError):
            tr.place_order(self.con, acc["id"], "xmr", "buy", 10 ** 9,
                           "ord-1")
        with self.assertRaises(tr.TradingError):
            tr.place_order(self.con, acc["id"], "xmr", "buy", 10 ** 9,
                           "ord-2", mode="live")

    # -- (h) stale price ------------------------------------------------------
    def test_stale_price_still_fills_flagged(self):
        tr._fetch_prices = lambda: None  # live fetch fails
        self._seed_price("xmr", Decimal("500.00"),
                         self.now - 7200, stale=0)
        acc = self._account()
        order = tr.place_order(self.con, acc["id"], "xmr", "buy",
                               10 ** 9, "ord-stale")
        self.assertEqual(order["status"], "filled")
        self.assertTrue(order["price_stale"])
        self.assertEqual(order["price_fetched_at"], self.now - 7200)

    # -- (i) funding rule ------------------------------------------------------
    def test_eligible_capital_zero_and_fund_refusal(self):
        cap = tr.eligible_capital(self.con)
        self.assertEqual(cap["total_usd_cents"], 0)
        self.assertEqual(cap["mining_profits_usd_cents"], 0)
        self.assertEqual(cap["usdc_deposits_usd_cents"], 0)
        acc = self._account()
        with self.assertRaises(tr.TradingError):
            tr.fund_from_capital(self.con, acc["id"], 100)
        decisions = [r[0] for r in self.con.execute(
            "SELECT decision FROM decisions WHERE dept = 'trading'")]
        self.assertIn("trading-capital-funding-refused", decisions)

    def test_record_deposit_rules(self):
        dep = tr.record_deposit(self.con, VALID_TX_SIG, 25000000)  # $25.00
        self.assertEqual(dep["amount_usd_cents"], 2500)
        self.assertEqual(dep["remainder_micro"], 0)
        self.assertEqual(dep["deposit_address"], VALID_ADDRESS)
        self.assertEqual(dep["source"], "solana-usdc")
        cap = tr.eligible_capital(self.con)
        self.assertEqual(cap["usdc_deposits_usd_cents"], 2500)
        self.assertEqual(cap["total_usd_cents"], 2500)
        # A sub-cent amount records with its remainder, never dropped.
        dep2 = tr.record_deposit(self.con, SIG_B, 2500099)  # $2.500099
        self.assertEqual(dep2["amount_usd_cents"], 250)
        self.assertEqual(dep2["remainder_micro"], 99)
        with self.assertRaises(tr.TradingError):
            tr.record_deposit(self.con, VALID_TX_SIG, 1000000)
        with self.assertRaises(tr.TradingError):
            tr.record_deposit(self.con, SIG_C, 0)
        with self.assertRaises(tr.TradingError):
            tr.record_deposit(self.con, "short", 1000000)

    def test_record_deposit_refuses_without_address(self):
        cfg = {"deposit": {"network": "Solana", "token": "USDC",
                           "token_standard": "SPL", "address": None,
                           "status": "address-pending"},
               "fee_bps": 0, "mode": "paper-only",
               "price_stale_after_s": 3600,
               "virtual_starting_balance_usd_cents": 1000000}
        path = os.path.join(self.tmpdir, "trading-noaddr.json")
        with open(path, "w") as f:
            json.dump(cfg, f)
        orig = tr.CFG_TRADING
        try:
            tr.CFG_TRADING = path
            with self.assertRaises(tr.TradingError):
                tr.record_deposit(self.con, VALID_TX_SIG, 1000000)
        finally:
            tr.CFG_TRADING = orig

    # -- scan (D-M22-5) -------------------------------------------------------
    def _parsed_tx(self, delta_micro, err=None, mint=None,
                   owner=None):
        mint = mint if mint is not None else tr.USDC_MINT
        owner = owner if owner is not None else VALID_ADDRESS
        return {"meta": {
            "err": err,
            "preTokenBalances": [],
            "postTokenBalances": ([{"accountIndex": 1, "mint": mint,
                                    "owner": owner,
                                    "uiTokenAmount": {
                                        "amount": str(delta_micro),
                                        "decimals": 6,
                                        "uiAmount": delta_micro / 1e6}}]
                                  if delta_micro else [])}}

    def test_scan_records_new_usdc_skips_rest(self):
        # SIG_B is already recorded -> skipped; SIG_C is a failed tx.
        tr.record_deposit(self.con, SIG_B, 5000000)
        rpc_calls = {"sigs": [{"signature": VALID_TX_SIG},
                              {"signature": SIG_B},
                              {"signature": SIG_C}]}

        def fake_rpc(method, params):
            if method == "getSignaturesForAddress":
                return rpc_calls["sigs"]
            if method == "getTransaction":
                sig = params[0]
                if sig == VALID_TX_SIG:
                    return self._parsed_tx(10000000)
                if sig == SIG_C:
                    return self._parsed_tx(0, err={"InstructionError": [0, "Custom"]})
            raise AssertionError(f"unexpected RPC call {method} {params}")

        orig_rpc = tr._solana_rpc
        try:
            tr._solana_rpc = fake_rpc
            summary = tr.scan_deposits(self.con, limit=10)
        finally:
            tr._solana_rpc = orig_rpc
        self.assertEqual(summary["checked"], 3)
        self.assertEqual(len(summary["new"]), 1)
        self.assertEqual(summary["new"][0]["amount_usd_cents"], 1000)
        self.assertEqual(summary["skipped"], 2)
        self.assertEqual(summary["errors"], [])
        cap = tr.eligible_capital(self.con)
        self.assertEqual(cap["usdc_deposits_usd_cents"], 500 + 1000)

    def test_scan_rpc_failure_records_nothing(self):
        def failing_rpc(method, params):
            raise ConnectionError("rpc down")

        orig_rpc = tr._solana_rpc
        try:
            tr._solana_rpc = failing_rpc
            summary = tr.scan_deposits(self.con, limit=5)
        finally:
            tr._solana_rpc = orig_rpc
        self.assertEqual(summary["new"], [])
        self.assertEqual(summary["checked"], 0)
        self.assertTrue(summary["errors"])
        self.assertEqual(table_count(self.con, "trading_deposits"), 0)

    def test_scan_refuses_without_address(self):
        cfg = {"deposit": {"network": "Solana", "token": "USDC",
                           "token_standard": "SPL", "address": None,
                           "status": "address-pending"},
               "fee_bps": 0, "mode": "paper-only",
               "price_stale_after_s": 3600,
               "virtual_starting_balance_usd_cents": 1000000}
        path = os.path.join(self.tmpdir, "trading-noaddr2.json")
        with open(path, "w") as f:
            json.dump(cfg, f)
        orig = tr.CFG_TRADING
        try:
            tr.CFG_TRADING = path
            with self.assertRaises(tr.TradingError):
                tr.scan_deposits(self.con, limit=5)
        finally:
            tr.CFG_TRADING = orig

    # -- (j) export -------------------------------------------------------------
    def test_export_reconciles_and_has_no_secrets(self):
        acc = self._account()
        tr.place_order(self.con, acc["id"], "xmr", "buy", 10 ** 9,
                       "ord-e1")
        tr.place_order(self.con, acc["id"], "kas", "buy", 10 ** 8,
                       "ord-e2")  # 1 KAS @ $0.025 -> 3 cents (2.5 -> 3)
        path = os.path.join(self.tmpdir, "trading.json")
        payload = tr.export_trading_json(con=self.con,
                                         export_path=path)
        self.assertEqual(payload["mode"], "paper-only")
        self.assertEqual(payload["eligible_capital_usd_cents"], 0)
        self.assertEqual(payload["deposit"]["network"], "Solana")
        self.assertEqual(payload["deposit"]["token"], "USDC")
        self.assertEqual(payload["deposit"]["address"], VALID_ADDRESS)
        self.assertEqual(len(payload["accounts"]), 1)
        portfolio = payload["accounts"][0]["portfolio"]
        # cash = 1,000,000 - 50 - 3 = 999,947
        self.assertEqual(portfolio["cash_usd_cents"], 999947)
        held = {p["coin"]: p["qty_base_units"]
                for p in portfolio["positions"]}
        self.assertEqual(held, {"xmr": 10 ** 9, "kas": 10 ** 8})
        with open(path) as f:
            raw = f.read()
        for banned in ("seed", "private key", "keypair", "mnemonic"):
            self.assertNotIn(banned, raw.lower(),
                             f"secret-trigger string in export: {banned}")

    # -- (k) read-only proof ------------------------------------------------------
    def test_status_and_export_change_no_core_counts(self):
        acc = self._account()
        tr.place_order(self.con, acc["id"], "xmr", "buy", 10 ** 9,
                       "ord-ro")
        before = {t: table_count(self.con, t) for t in
                  ("decisions", "ledger", "trading_orders",
                   "trading_accounts")}
        tr.export_trading_json(con=self.con, export_path=os.path.join(
            self.tmpdir, "trading.json"))
        after = {t: table_count(self.con, t) for t in before}
        self.assertEqual(before, after)

    # -- (l) Mission 24: ATA deposit-scan fix -----------------------------------
    # The live on-chain ATA for the configured deposit address, verified
    # 2026-11-20 ~18:22 EST from the token-account history (the second
    # deposit, 4.78776 USDC, landed 17:53 but was invisible to the
    # wallet-address query for ~30 minutes).
    LIVE_ATA = "HAvmUB6eHZM2Z1NNbXXnpEvVqh4adB9pB49qHgdVwjdK"
    # The two real confirmed deposits (public signatures, safe in tests).
    FIRST_TX = ("4LadRjiJAexiW3KrUbba5fpC2yjkPwFxpNtku5V3vPTExcdVoEjkUzSty"
                "qLg7Dr93X6j4bG7BDQNM4VLR3wbzKAv")
    SECOND_TX = ("QjPQmDCaW8Vts1ypef1y6bx7gzzgUxwtPJSVdC7HwawFBf2u7R3yMcE"
                 "HpaAscrZ5G3uDD5moLfmxAYMADAY7wG3")

    def test_derive_ata_matches_live_account(self):
        self.assertEqual(tr.derive_associated_token_account(VALID_ADDRESS),
                         self.LIVE_ATA)

    def test_b58encode_round_trip(self):
        raw = tr._b58decode(VALID_ADDRESS)
        self.assertEqual(tr._b58encode(raw), VALID_ADDRESS)
        self.assertEqual(tr._b58decode(tr._b58encode(b"\x00\x00abc")),
                         b"\x00\x00abc")

    def test_derive_ata_rejects_bad_address(self):
        with self.assertRaises(tr.TradingError):
            tr.derive_associated_token_account("not-base58!!")
        with self.assertRaises(tr.TradingError):
            tr.derive_associated_token_account("short")

    def test_scan_queries_token_account_and_finds_both_deposits(self):
        # The wallet history shows only the first deposit (it created
        # the ATA); the ATA history shows both. A wallet-only scan
        # would record 1; the fixed scan must record 2.
        def fake_rpc(method, params):
            if method == "getSignaturesForAddress":
                if params[0] == VALID_ADDRESS:
                    return [{"signature": self.FIRST_TX}]
                if params[0] == self.LIVE_ATA:
                    return [{"signature": self.FIRST_TX},
                            {"signature": self.SECOND_TX}]
                raise AssertionError(f"unexpected address {params[0]}")
            if method == "getTransaction":
                if params[0] == self.FIRST_TX:
                    return self._parsed_tx(944520)
                if params[0] == self.SECOND_TX:
                    return self._parsed_tx(4787760)
            raise AssertionError(f"unexpected RPC call {method} {params}")

        orig_rpc = tr._solana_rpc
        try:
            tr._solana_rpc = fake_rpc
            summary = tr.scan_deposits(self.con, limit=10)
        finally:
            tr._solana_rpc = orig_rpc
        self.assertEqual(summary["token_account"], self.LIVE_ATA)
        self.assertEqual(summary["checked"], 2)
        self.assertEqual(len(summary["new"]), 2)
        self.assertEqual(summary["errors"], [])
        self.assertEqual(table_count(self.con, "trading_deposits"), 2)
        cap = tr.eligible_capital(self.con)
        # 0.94452 + 4.78776 = 5.73228 USDC -> 572 cents + 3280 micro left.
        self.assertEqual(cap["usdc_deposits_usd_cents"], 572)
        self.assertEqual(cap["total_usd_cents"], 572)

    def test_scan_dedupes_signature_in_both_histories(self):
        # The first deposit appears in BOTH histories; it must be
        # checked and recorded exactly once.
        def fake_rpc(method, params):
            if method == "getSignaturesForAddress":
                return [{"signature": self.FIRST_TX}]
            if method == "getTransaction":
                return self._parsed_tx(944520)
            raise AssertionError(f"unexpected RPC call {method} {params}")

        orig_rpc = tr._solana_rpc
        try:
            tr._solana_rpc = fake_rpc
            summary = tr.scan_deposits(self.con, limit=10)
        finally:
            tr._solana_rpc = orig_rpc
        self.assertEqual(summary["checked"], 1)
        self.assertEqual(len(summary["new"]), 1)
        self.assertEqual(summary["skipped"], 0)


    # -- (m25) pump.fun paper trading ----------------------------------
    def test_pump_buy_fills_at_dexscreener_price(self):
        # D-M25: pump.fun coins price from Dexscreener (public), not
        # CoinGecko; a $1 paper buy fills at the fixture price.
        orig = tr._fetch_pump_price
        try:
            tr._fetch_pump_price = lambda coin: Decimal("0.001200")
            self.assertEqual(
                tr.PUMP_COINS["fiona"],
                "B34nXKzCgsJb9ChLuSHPRpXLE3WFSWyeT8Cqkzzmpump")
            self.assertEqual(tr.COIN_DECIMALS["fiona"], 6)
            self.assertEqual(tr.COIN_DECIMALS["buttcoin"], 6)
            acc = self._account()
            order = tr.place_order(self.con, acc["id"], "fiona", "buy",
                                   833333333, "ord-pump-1")
            self.assertEqual(order["status"], "filled")
            self.assertEqual(Decimal(order["price_usd"]),
                             Decimal("0.001200"))
            self.assertIn("Dexscreener", order["price_source"])
            self.assertEqual(order["cost_usd_cents"], 100)
            pos = tr.positions(self.con, acc["id"])
            self.assertEqual(pos["fiona"], 833333333)
        finally:
            tr._fetch_pump_price = orig

    def test_m26_rotation_coins_registered_and_buyable(self):
        # D-M26: the four rotation coins are in the registry with the
        # verified mints and 6 decimals; a $3 paper buy of penny fills
        # at the stubbed Dexscreener price.
        self.assertEqual(
            tr.PUMP_COINS["penny"],
            "8fWsV1u1SYcN358tSA6dyTjfpmaQTziftcHwKBFSpump")
        self.assertEqual(
            tr.PUMP_COINS["chud"],
            "EV7J2QaPXPytSkM1LD9GPRkgAbmSEr9R3kYiXBzbpump")
        self.assertEqual(
            tr.PUMP_COINS["butthole"],
            "BWkSWbiyfbw1Td5hFwQn7E4B7vTjgCcF96M25aiCpump")
        self.assertEqual(
            tr.PUMP_COINS["smoove"],
            "BSe1q3SL6KQPLeZHFG9nNw5VFbDL3ZXvBmtjBVpYpump")
        for coin in ("penny", "chud", "butthole", "smoove"):
            self.assertEqual(tr.COIN_DECIMALS[coin], 6)
            self.assertIn(coin, tr.COINS)
        orig = tr._fetch_pump_price
        try:
            tr._fetch_pump_price = lambda coin: Decimal("0.000120")
            acc = self._account()
            order = tr.place_order(self.con, acc["id"], "penny", "buy",
                                   25000000000, "ord-m26-penny-1")
            self.assertEqual(order["status"], "filled")
            self.assertEqual(Decimal(order["price_usd"]),
                             Decimal("0.000120"))
            self.assertEqual(order["cost_usd_cents"], 300)
            pos = tr.positions(self.con, acc["id"])
            self.assertEqual(pos["penny"], 25000000000)
        finally:
            tr._fetch_pump_price = orig

    def test_pump_price_failure_rejects_or_falls_back_stale(self):
        # D-M25: a failed Dexscreener fetch never fabricates a price.
        orig = tr._fetch_pump_price
        try:
            tr._fetch_pump_price = lambda coin: None
            acc = self._account()
            order = tr.place_order(self.con, acc["id"], "buttcoin", "buy",
                                   100000000, "ord-pump-noprice")
            self.assertEqual(order["status"], "rejected")
            self.assertIn("no-live-price", order["reject_reason"])
            self._seed_price("buttcoin", Decimal("0.006000"),
                             self.now - 7200, stale=0)
            order2 = tr.place_order(self.con, acc["id"], "buttcoin", "buy",
                                    100000000, "ord-pump-stale")
            self.assertEqual(order2["status"], "filled")
            self.assertTrue(order2["price_stale"])
        finally:
            tr._fetch_pump_price = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
