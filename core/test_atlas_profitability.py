#!/usr/bin/env python3
"""ATLAS Master Mission 9 — Lane C host profitability module tests.

Runs ONLY against temp copies of atlas.db in /tmp. NEVER writes to the
real ~/workspace/atlas/data/atlas.db. The real DB is copied from the
PRE-MIGRATION backup (user_version 1), the Stage 1 migration is applied,
then the Stage 2 migration — all test/sim data lives in /tmp. (Same
fixture pattern as core/test_atlas_admin.py.)

Live fetches are NEVER attempted in these tests except where explicitly
monkeypatched to fail: every computation test feeds fixture inputs
(Obj 4 / M4) directly, and the run_pass test patches the HTTP layer to
raise so the fallback path is exercised deterministically.

Test plan (design §10):
  (a) Obj 4 formula regression — fed the Obj 4 inputs, the module
      reproduces the Obj 4 net/day figures for all four coins at all
      three rates within rounding (XMR +$0.021 / +$0.138 / -$0.367;
      KAS, RVN, ERG as design §4); panel breakeven c/kWh 8.29 / ~0.00 /
      1.73 / 3.29; XMR verdict Above breakeven at Tier 2, the rest Below.
  (b) M4 breakeven regression — fed the M4 inputs, the XMR gate
      reproduces 56.5 H/W at Tier 2 and 125.2 H/W at the US average
      within rounding, and $0.03302/day per kH/s.
  (c) fee comparison — SupportXMR 0.6% reduces XMR gross by exactly
      0.6% vs MoneroOcean 0%; P2Pool 0% equals MoneroOcean.
  (d) sensitivity — the US-average rate flips the XMR reference profile
      negative while Tier 2 stays positive (at Obj 4 inputs).
  (e) stale-input handling — an input older than 1 h flags its coin
      STALE and the export carries the last-fetch time, never a fresh
      timestamp; a failed fetch never raises and never fabricates an
      input (monkeypatched HTTP failure -> not-computed / stale fallback).
  (f) your-hardware null — with Gate 1 unmeasured the block is null
      with the verbatim reason.
  (g) read-only proof — all table counts and the decisions table
      unchanged across status+export, the module logs no decision.
  (h) export idempotence + atomic write (temp + os.replace, no partial
      file on failure).
  (i) run_pass sub-step on a temp DB — all exports written, exactly +1
      decision per pass (coordinator-pass-complete), profitability
      export fresh.

Usage: python3 core/test_atlas_profitability.py [-v]
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.expanduser("~/workspace/atlas/core"))
import atlas_coordinator as ac
import atlas_dashboard as db
import atlas_profitability as prof

SRC_DB = os.path.expanduser(
    "~/workspace/atlas/backups/atlas-2026-11-18-pre-mission5.db")
MIGRATION_1 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission5_stage1.sql")
MIGRATION_2 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission6_stage2.sql")
MIGRATION_3 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission11_stage3.sql")

YOUR_HARDWARE_REASON = "Cannot estimate — hashrate not measured"
SPLIT_NOTE = "Projection only — not earnings"
TARIFF_LABEL = "Proposed tariff — not in effect"

# Obj 4 carried results (design §4), net $/day at (Tier 2, Tier 1, US).
OBJ4_NETS_USD = {
    "xmr_cpu": (0.021, 0.138, -0.367),
    "kas": (-0.280, -0.178, -0.620),
    "rvn": (-0.349, -0.185, -0.893),
    "erg": (-0.142, -0.052, -0.442),
}
# Obj 4 breakeven electricity price, c/kWh (design §4).
OBJ4_BREAKEVEN_CENTS = {"xmr_cpu": 8.29, "kas": 0.00, "rvn": 1.73,
                        "erg": 3.29}


def _coin(network_hashrate_hps, difficulty, height, block_reward,
          blocks_per_day, price_usd, fetched_at, source_network,
          avg_block_time_s=None, last_block_value_xmr=None):
    rec = {"network_hashrate_hps": network_hashrate_hps,
           "difficulty": difficulty, "height": height,
           "block_reward": block_reward, "blocks_per_day": blocks_per_day,
           "price_usd": price_usd, "source_network": source_network,
           "source_price": "CoinGecko simple/price",
           "fetched_at": fetched_at, "stale": False, "status": "fresh"}
    if avg_block_time_s is not None:
        rec["avg_block_time_s"] = avg_block_time_s
    if last_block_value_xmr is not None:
        rec["last_block_value_xmr"] = last_block_value_xmr
    return rec


def obj4_inputs(now):
    """The Obj 4 inputs (docs/mission2-obj4-findings.md §§2-7)."""
    return {
        "xmr": _coin(772656444936 / 120.0, 772656444936, 3808871, 0.6, 720,
                     507.17, now, "MoneroOcean /network/stats (port 18081)",
                     last_block_value_xmr=0.6045),
        "kas": _coin(317016508646590909, 31344111208331531, None, 1.94454365,
                     864000, 0.02727563, now,
                     "2Miners api/stats (kas.2miners.com)",
                     avg_block_time_s=0.1),
        "rvn": _coin(533882597021, 33098427129147, 4630530, 1250, 1440,
                     0.00110692, now, "2Miners api/stats (rvn.2miners.com)",
                     avg_block_time_s=60),
        "erg": _coin(713237332484, 69338556006400, 1919265, 3, 888.7,
                     0.205371, now, "2Miners api/stats (erg.2miners.com)",
                     avg_block_time_s=97.22),
        "usd_cad": {"value": 1.4316, "source": "CoinGecko exchange_rates",
                    "fetched_at": now, "stale": False, "status": "fresh"},
    }


def m4_inputs(now):
    """The M4 inputs (docs/master-mission4-cost-accounting.md §1/§3):
    XMR price $501.26, difficulty 787,074,505,719, USD/CAD 1.4327;
    the other coins carry the Obj 4 inputs."""
    inputs = obj4_inputs(now)
    inputs["xmr"] = _coin(787074505719 / 120.0, 787074505719, 3808948, 0.6,
                          720, 501.26, now,
                          "MoneroOcean /network/stats (port 18081)",
                          last_block_value_xmr=0.60540582)
    inputs["usd_cad"] = {"value": 1.4327,
                         "source": "CoinGecko exchange_rates",
                         "fetched_at": now, "stale": False, "status": "fresh"}
    return inputs


def fresh_db(path):
    if os.path.exists(path):
        os.remove(path)
    shutil.copy2(SRC_DB, path)
    con = sqlite3.connect(path)
    with open(MIGRATION_1) as f:
        con.executescript(f.read())
    with open(MIGRATION_2) as f:
        con.executescript(f.read())
    with open(MIGRATION_3) as f:
        con.executescript(f.read())
    con.commit()
    uv = con.execute("PRAGMA user_version").fetchone()[0]
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()
    assert uv == 4, f"user_version after Stage 3 migration: {uv}"
    assert integ == "ok", f"integrity after Stage 2 migration: {integ}"
    return path


def table_count(con, table):
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


ALL_TABLES = ("users", "workers", "shares", "sessions", "ledger",
              "reward_batches", "payouts", "referrals", "decisions",
              "events", "metrics", "pool_stats")


def _no_usd_in_panel(node, path="panel"):
    """No USD figure in the panel payload: no key mentions usd, no
    string mentions USD or $, no price key anywhere in the panel."""
    if isinstance(node, dict):
        for key, value in node.items():
            assert "usd" not in key.lower(), f"USD key in panel: {path}.{key}"
            assert "price" not in key.lower(), f"price key in panel: {path}.{key}"
            _no_usd_in_panel(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _no_usd_in_panel(value, f"{path}[{i}]")
    elif isinstance(node, str):
        assert "USD" not in node, f"USD string in panel: {path}={node!r}"
        assert "$" not in node, f"$ string in panel: {path}={node!r}"


class ProfitabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="atlas-m9-profit-")
        self.db_path = os.path.join(self.tmpdir, "test.db")
        fresh_db(self.db_path)
        self.con = ac.connect(self.db_path)
        self.export_path = os.path.join(self.tmpdir, "profitability.json")
        self.now = int(time.time())

    def tearDown(self):
        self.con.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _panel_row(self, payload, section, profile):
        rows = payload["panel"][section]
        if isinstance(rows, dict):
            rows = rows["rows"]
        for row in rows:
            if row["profile"] == profile:
                return row
        self.fail(f"no {section} row for {profile}")

    # -- (a) Obj 4 formula regression ----------------------------------
    def test_a_obj4_regression(self):
        computed = prof.compute_profitability(obj4_inputs(self.now),
                                              now=self.now)
        for pid, (t2, t1, us) in OBJ4_NETS_USD.items():
            nets = computed["profiles"][pid]["figures"]["net_usd_per_day"]
            self.assertAlmostEqual(nets["tier2"], t2, delta=0.001,
                                   msg=f"{pid} Tier 2 net")
            self.assertAlmostEqual(nets["tier1"], t1, delta=0.001,
                                   msg=f"{pid} Tier 1 net")
            self.assertAlmostEqual(nets["us_avg"], us, delta=0.001,
                                   msg=f"{pid} US net")
        # Panel breakeven c/kWh + Tier 2 verdicts.
        payload = prof.profitability_status(
            self.con, export_dir=self.tmpdir,
            inputs=obj4_inputs(self.now), now=self.now)
        for pid, cents in OBJ4_BREAKEVEN_CENTS.items():
            row = self._panel_row(payload, "breakeven", pid)
            self.assertAlmostEqual(row["breakeven_cents_per_kwh"], cents,
                                   delta=0.01, msg=f"{pid} breakeven c/kWh")
        self.assertEqual(
            self._panel_row(payload, "coin_comparison", "xmr_cpu")["verdict"],
            "Above breakeven")
        for pid in ("kas", "rvn", "erg", "xmr_browser_laptop",
                    "xmr_browser_desktop"):
            self.assertEqual(
                self._panel_row(payload, "coin_comparison", pid)["verdict"],
                "Below breakeven", msg=pid)
        # XMR panel net (Tier 2) re-derives from the USD audit figure.
        xmr = self._panel_row(payload, "coin_comparison", "xmr_cpu")
        audit_net = computed["profiles"]["xmr_cpu"]["figures"][
            "net_usd_per_day"]["tier2"]
        self.assertAlmostEqual(xmr["net_xmr_per_day_tier2"],
                               audit_net / 507.17, delta=1e-6)
        # Split projection (Tier 2, XMR): 0.75 x gross, user net negative.
        split = self._panel_row(payload, "split_projection", "xmr_cpu")
        self.assertEqual(split["note"], SPLIT_NOTE)
        gross_xmr = computed["profiles"]["xmr_cpu"]["figures"][
            "gross_xmr_per_day"]
        self.assertAlmostEqual(split["user_share_xmr_per_day"],
                               0.75 * gross_xmr, delta=1e-6)
        self.assertAlmostEqual(split["atlas_share_xmr_per_day"],
                               0.25 * gross_xmr, delta=1e-6)
        self.assertLess(split["user_net_xmr_per_day"], 0)
        # No USD anywhere in the panel payload; USD only under audit_usd.
        _no_usd_in_panel(payload["panel"])
        self.assertIn("audit_usd", payload)
        self.assertIn("xmr_cpu", payload["audit_usd"]["profiles"])
        # Confirmed earnings reused verbatim from the dashboard export.
        dash = db.dashboard_status(self.con, export_dir=self.tmpdir)
        self.assertEqual(payload["confirmed_earnings"], dash["earnings"])
        self.assertEqual(payload["confirmed_earnings"]["confirmed_piconero"], 0)
        self.assertFalse(payload["stale"])
        self.assertEqual(payload["stale_inputs"], [])

    # -- (b) M4 breakeven regression ------------------------------------
    def test_b_m4_breakeven_regression(self):
        computed = prof.compute_profitability(m4_inputs(self.now),
                                              now=self.now)
        figs = computed["profiles"]["xmr_cpu"]["figures"]
        self.assertAlmostEqual(figs["breakeven_hw"]["tier2"], 56.5,
                               delta=0.15, msg="Tier 2 gate")
        self.assertAlmostEqual(figs["breakeven_hw"]["us_avg"], 125.2,
                               delta=0.15, msg="US avg gate")
        audit = prof.compute_profitability(m4_inputs(self.now), now=self.now)
        per_khs = audit["profiles"]["xmr_cpu"]["figures"][
            "gross_usd_per_hps"] * 1000.0
        self.assertAlmostEqual(per_khs, 0.03302, delta=1e-4,
                               msg="$/day per kH/s")
        # The panel carries the same gates (rounded to 1 dp).
        payload = prof.profitability_status(
            self.con, export_dir=self.tmpdir,
            inputs=m4_inputs(self.now), now=self.now)
        row = self._panel_row(payload, "breakeven", "xmr_cpu")
        self.assertAlmostEqual(row["breakeven_hw_tier2"], 56.5, delta=0.15)
        self.assertAlmostEqual(row["breakeven_hw_us_avg"], 125.2, delta=0.15)

    # -- (c) fee comparison ---------------------------------------------
    def test_c_fee_comparison(self):
        computed = prof.compute_profitability(obj4_inputs(self.now),
                                              now=self.now)
        fees = computed["pool_fees"]
        mo = fees["moneroocean"]["figures"]["gross_usd_per_day"]
        sx = fees["supportxmr"]["figures"]["gross_usd_per_day"]
        p2 = fees["p2pool"]["figures"]["gross_usd_per_day"]
        # SupportXMR 0.6% = exactly 0.6% less gross than MoneroOcean 0%.
        self.assertAlmostEqual(sx, mo * 0.994, delta=abs(mo) * 1e-9 + 1e-12)
        # P2Pool 0% equals MoneroOcean 0%.
        self.assertEqual(p2, mo)
        self.assertEqual(fees["moneroocean"]["fee_percent"], 0.0)
        self.assertEqual(fees["supportxmr"]["fee_percent"], 0.6)
        self.assertEqual(fees["p2pool"]["fee_percent"], 0.0)
        # The fee bites the net too: SupportXMR net < MoneroOcean net.
        mo_net = fees["moneroocean"]["figures"]["net_xmr_per_day"]["tier2"]
        sx_net = fees["supportxmr"]["figures"]["net_xmr_per_day"]["tier2"]
        self.assertLess(sx_net, mo_net)

    # -- (d) sensitivity flip --------------------------------------------
    def test_d_sensitivity_flip(self):
        computed = prof.compute_profitability(obj4_inputs(self.now),
                                              now=self.now)
        nets = computed["profiles"]["xmr_cpu"]["figures"]["net_usd_per_day"]
        self.assertGreater(nets["tier2"], 0, "Tier 2 stays positive")
        self.assertGreater(nets["tier1"], 0, "Tier 1 stays positive")
        self.assertLess(nets["us_avg"], 0, "US average flips negative")
        # Same flip visible in the panel (XMR/day).
        payload = prof.profitability_status(
            self.con, export_dir=self.tmpdir,
            inputs=obj4_inputs(self.now), now=self.now)
        sens = self._panel_row(payload, "sensitivity", "xmr_cpu")
        self.assertGreater(sens["net_xmr_per_day"]["tier2"], 0)
        self.assertLess(sens["net_xmr_per_day"]["us_avg"], 0)
        # The risk scenario is present as a labelled row, never a base case.
        self.assertIn("proposed_tariff", sens["net_xmr_per_day"])
        self.assertLess(sens["net_xmr_per_day"]["proposed_tariff"],
                        sens["net_xmr_per_day"]["tier2"])

    # -- (e) stale-input handling ----------------------------------------
    def test_e_stale_input_handling(self):
        stale_at = self.now - 3700  # 61 min 40 s old
        inputs = obj4_inputs(self.now)
        inputs["kas"]["fetched_at"] = stale_at
        payload = prof.profitability_status(
            self.con, export_dir=self.tmpdir, inputs=inputs, now=self.now)
        self.assertTrue(payload["stale"])
        self.assertEqual(len(payload["stale_inputs"]), 1)
        self.assertIn("KAS", payload["stale_inputs"][0])
        # The last-fetch time is carried, never re-stamped fresh.
        self.assertEqual(payload["inputs"]["kas"]["fetched_at"], stale_at)
        self.assertTrue(payload["inputs"]["kas"]["stale"])
        # The stale coin is still computed from its last recorded inputs.
        kas = self._panel_row(payload, "coin_comparison", "kas")
        self.assertEqual(kas["status"], "computed")
        self.assertIsNotNone(kas["net_xmr_per_day_tier2"])
        # A failed fetch never raises and never fabricates an input.
        orig = prof._http_get_json
        try:
            prof._http_get_json = lambda url: (_ for _ in ()).throw(
                RuntimeError("simulated egress failure"))
            live = prof.fetch_live_inputs(export_dir=self.tmpdir)
            for coin in ("xmr", "kas", "rvn", "erg"):
                self.assertEqual(live[coin]["status"], "not_computed")
                self.assertIsNone(live[coin]["network_hashrate_hps"])
                self.assertIsNone(live[coin]["price_usd"])
            self.assertEqual(live["usd_cad"]["status"], "not_computed")
            self.assertIsNone(live["usd_cad"]["value"])
            # ... and a status/export on failed-fetch inputs still works,
            # with every figure null and 'Not computed yet' shown.
            payload2 = prof.profitability_status(
                self.con, export_dir=self.tmpdir, inputs=live, now=self.now)
            for pid in ("xmr_cpu", "kas", "rvn", "erg"):
                row = self._panel_row(payload2, "coin_comparison", pid)
                self.assertEqual(row["status"], "not_computed")
                self.assertEqual(row["empty_state"], "Not computed yet")
                self.assertIsNone(row["net_xmr_per_day_tier2"])
            self.assertEqual(payload2["not_computed"],
                             ["XMR", "KAS", "RVN", "ERG", "USD/CAD"])
        finally:
            prof._http_get_json = orig
        # Fallback to last recorded inputs: a previous export exists, the
        # fetch fails, the coin goes STALE with its old fetched_at.
        prev = obj4_inputs(self.now - 1800)
        with open(self.export_path, "w") as f:
            json.dump({"exported_at": self.now - 1800, "inputs": prev}, f)
        try:
            prof._http_get_json = lambda url: (_ for _ in ()).throw(
                RuntimeError("simulated egress failure"))
            live2 = prof.fetch_live_inputs(export_dir=self.tmpdir)
            self.assertEqual(live2["xmr"]["status"], "stale")
            self.assertEqual(live2["xmr"]["fetched_at"], self.now - 1800)
            self.assertEqual(live2["xmr"]["network_hashrate_hps"],
                             prev["xmr"]["network_hashrate_hps"])
            self.assertEqual(live2["usd_cad"]["status"], "stale")
            self.assertEqual(live2["usd_cad"]["value"], 1.4316)
        finally:
            prof._http_get_json = orig

    # -- (f) your-hardware null ------------------------------------------
    def test_f_your_hardware_null(self):
        payload = prof.profitability_status(
            self.con, export_dir=self.tmpdir,
            inputs=obj4_inputs(self.now), now=self.now)
        self.assertIsNone(payload["your_hardware"])
        self.assertEqual(payload["your_hardware_reason"],
                         YOUR_HARDWARE_REASON)
        self.assertIsNone(payload["panel"]["your_hardware"])
        self.assertEqual(payload["panel"]["your_hardware_reason"],
                         YOUR_HARDWARE_REASON)

    # -- (g) read-only proof ----------------------------------------------
    def test_g_read_only(self):
        before = {t: table_count(self.con, t) for t in ALL_TABLES}
        inputs = obj4_inputs(self.now)
        prof.profitability_status(self.con, export_dir=self.tmpdir,
                                  inputs=inputs, now=self.now)
        prof.export_profitability_json(self.con, export_path=self.export_path,
                                       inputs=inputs)
        after = {t: table_count(self.con, t) for t in ALL_TABLES}
        self.assertEqual(after, before,
                         "status+export wrote to the DB")
        self.assertEqual(before["decisions"], after["decisions"])
        # The export file itself exists and parses.
        with open(self.export_path) as f:
            on_disk = json.load(f)
        self.assertEqual(on_disk["your_hardware"], None)
        self.assertEqual(on_disk["confirmed_earnings"]["confirmed_piconero"], 0)

    # -- (h) export idempotence + atomic write ----------------------------
    def test_h_export_idempotence_atomic(self):
        inputs = obj4_inputs(self.now)
        _, payload1 = prof.export_profitability_json(
            self.con, export_path=self.export_path, inputs=inputs)
        self.assertTrue(os.path.exists(self.export_path))
        self.assertFalse(os.path.exists(self.export_path + ".tmp"),
                         "atomic-write temp file left behind")
        with open(self.export_path) as f:
            on_disk1 = json.load(f)
        self.assertEqual(on_disk1, payload1)
        _, payload2 = prof.export_profitability_json(
            self.con, export_path=self.export_path, inputs=inputs)
        self.assertFalse(os.path.exists(self.export_path + ".tmp"))
        with open(self.export_path) as f:
            on_disk2 = json.load(f)
        self.assertEqual(on_disk2, payload2)

        def _stable(payload):
            stable = dict(payload)
            stable.pop("exported_at", None)
            stable["panel"] = dict(payload["panel"])
            stable["panel"]["last_sync"] = {
                k: v for k, v in payload["panel"]["last_sync"].items()
                if k != "profitability_exported_at"}
            return stable

        self.assertEqual(_stable(payload1), _stable(payload2))
        self.assertIsInstance(payload1["exported_at"], int)
        self.assertIsInstance(payload2["exported_at"], int)

    # -- (i) run_pass profitability sub-step ------------------------------
    def test_i_run_pass_profitability_substep(self):
        # A fresh pool_stats row keeps the poll not-due, so the pass
        # never touches the pool network; the HTTP layer is patched to
        # fail so the profitability sub-step exercises its STALE
        # fallback deterministically (seeded previous export below).
        self.con.execute(
            """INSERT INTO pool_stats
                   (pool_name, recorded_at, hashrate, miners, block_height,
                    network_hashrate, block_reward_piconero, pool_fee_bps)
               VALUES ('MoneroOcean', ?, 262107922, 4975, 3808993, NULL,
                       600000000000, 0)""",
            (int(time.time()),))
        self.con.commit()
        seed_at = int(time.time()) - 600
        with open(self.export_path, "w") as f:
            json.dump({"exported_at": seed_at,
                       "inputs": obj4_inputs(seed_at)}, f)
        coord_path = os.path.join(self.tmpdir, "coordinator.json")
        before = table_count(self.con, "decisions")
        orig = prof._http_get_json
        try:
            prof._http_get_json = lambda url: (_ for _ in ()).throw(
                RuntimeError("simulated egress failure"))
            summary = ac.run_pass(db_path=self.db_path, export_path=coord_path)
        finally:
            prof._http_get_json = orig
        self.assertIn("exported_at", summary)
        self.assertEqual(summary["rewards"], {"batches_due": 0, "settled": [],
                                              "held": [], "refused": [],
                                              "noop": [], "failed": []})
        # The pass logged exactly one new decision (pass-complete); the
        # profitability sub-step logs none of its own.
        self.assertEqual(table_count(self.con, "decisions"), before + 1)
        self.assertEqual(
            self.con.execute(
                "SELECT decision FROM decisions ORDER BY id DESC LIMIT 1"
            ).fetchone()[0], "coordinator-pass-complete")
        # All five exports landed in the temp dir, none in the live dir.
        for name in ("coordinator.json", "rewards.json", "dashboard.json",
                     "admin.json", "profitability.json"):
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, name)),
                            f"{name} missing after run_pass")
        with open(os.path.join(self.tmpdir, "profitability.json")) as f:
            profit = json.load(f)
        age = int(time.time()) - profit["exported_at"]
        self.assertLess(age, 600, f"profitability.json exported_at {age}s old")
        self.assertIsNone(profit["your_hardware"])
        self.assertEqual(profit["your_hardware_reason"], YOUR_HARDWARE_REASON)
        # Fallback figures computed from the seeded inputs (STALE, not fresh).
        self.assertTrue(profit["stale"])
        self.assertEqual(profit["inputs"]["xmr"]["fetched_at"], seed_at)
        xmr = next(r for r in profit["panel"]["coin_comparison"]
                   if r["profile"] == "xmr_cpu")
        self.assertEqual(xmr["status"], "computed")
        self.assertGreater(xmr["net_xmr_per_day_tier2"], 0)
        with open(os.path.join(self.tmpdir, "dashboard.json")) as f:
            dash = json.load(f)
        self.assertEqual(profit["confirmed_earnings"], dash["earnings"])

    # -- blockReward normalization -----------------------------------------
    def test_block_reward_bands(self):
        self.assertAlmostEqual(
            prof._normalize_block_reward("kas", 194454365), 1.94454365)
        self.assertAlmostEqual(
            prof._normalize_block_reward("rvn", 1250), 1250.0)
        self.assertAlmostEqual(
            prof._normalize_block_reward("erg", 3000000000), 3.0)
        self.assertAlmostEqual(
            prof._normalize_block_reward("erg", 3), 3.0)
        self.assertIsNone(prof._normalize_block_reward("kas", 999999999999))
        self.assertIsNone(prof._normalize_block_reward("rvn", 0.5))
        self.assertIsNone(prof._normalize_block_reward("erg", None))

    # -- 2Miners string-valued payloads (live shape, 2026-11-18) ---------
    def test_j_twominers_string_payload(self):
        # Live 2Miners api/stats returns every numeric field as a STRING,
        # and the RVN/ERG nodes publish NO blockReward at all. The parser
        # must coerce the strings and fall back to the CARRIED protocol
        # constants for RVN/ERG block rewards (with provenance), never
        # fail the coin.
        payloads = {
            "https://kas.2miners.com/api/stats": {
                "nodes": [{"networkhashps": "306904484533747697",
                           "difficulty": "30375167126801947",
                           "blockReward": "194454365",
                           "avgBlockTime": "0.1", "height": "596356340"}]},
            "https://rvn.2miners.com/api/stats": {
                "nodes": [{"networkhashps": "492712329267.5665",
                           "difficulty": "7110.2819",
                           "avgBlockTime": "60.01", "height": "4631761"}]},
            "https://erg.2miners.com/api/stats": {
                "nodes": [{"networkhashps": "582759831134",
                           "difficulty": "67279622504448",
                           "avgBlockTime": "115.45", "height": "1919880"}]},
        }
        orig = prof._http_get_json
        try:
            prof._http_get_json = lambda url: payloads[url]
            prices = {"kas": 0.027, "rvn": 0.0011, "erg": 0.205}
            kas = prof._fetch_2miners("kas", prices, None)
            self.assertEqual(kas["status"], "fresh")
            # float64 cannot hold an 18-digit integer exactly; allow a
            # tiny relative error (network hashrate is a float everywhere).
            self.assertAlmostEqual(kas["network_hashrate_hps"],
                                   306904484533747697.0, delta=1e6)
            self.assertAlmostEqual(kas["block_reward"], 1.94454365)
            self.assertIn("live", kas["block_reward_source"])
            self.assertEqual(kas["difficulty"], 30375167126801947)
            self.assertEqual(kas["height"], 596356340)
            self.assertAlmostEqual(kas["blocks_per_day"], 864000.0)
            rvn = prof._fetch_2miners("rvn", prices, None)
            self.assertEqual(rvn["status"], "fresh")
            self.assertAlmostEqual(rvn["block_reward"], 1250.0)
            self.assertIn("CARRIED", rvn["block_reward_source"])
            self.assertAlmostEqual(rvn["blocks_per_day"], 86400.0 / 60.01,
                                   delta=0.01)
            erg = prof._fetch_2miners("erg", prices, None)
            self.assertEqual(erg["status"], "fresh")
            self.assertAlmostEqual(erg["block_reward"], 3.0)
            self.assertIn("CARRIED", erg["block_reward_source"])
            # Live avgBlockTime (115.45 s) beats the carried 888.7/day.
            self.assertAlmostEqual(erg["blocks_per_day"], 86400.0 / 115.45,
                                   delta=0.01)
            self.assertLess(erg["blocks_per_day"], 800)
        finally:
            prof._http_get_json = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
