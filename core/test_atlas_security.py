#!/usr/bin/env python3
"""ATLAS Master Mission 10 — Lane C security + scale tests.

Runs ONLY against temp copies of atlas.db in /tmp (plus a temp export
dir). NEVER writes to the real ~/workspace/atlas/data/atlas.db. The
real DB is copied from the PRE-MIGRATION backup (user_version 1), the
Stage 1 migration is applied, then the Stage 2 migration — all test
data lives in /tmp. The live battery is exercised through
security_status() on a temp DB with a temp export dir seeded with a
fresh admin.json (so S6's live check has a file to compare against).

Test plan: docs/master-mission10-design.md §4 (S1–S9) and §5 (L1–L5
on-demand + the fast smoke level for diagnostics test 28).

Usage: python3 core/test_atlas_security.py [-v]
NOTE: the L1–L5 test runs the full diagnostics suite once as a
subprocess for the L3 live leg (its normal behaviour: daemon restarts,
live decision logging, diagnostics.json rewrite) and loads 100,000
synthetic shares — it takes several minutes. The remaining tests are
fast (seconds).
"""
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.expanduser("~/workspace/atlas/core"))
import atlas_admin
import atlas_coordinator as ac
import atlas_rewards as rw
import atlas_security as sec

REAL_DB = os.path.expanduser("~/workspace/atlas/data/atlas.db")
SRC_DB = os.path.expanduser(
    "~/workspace/atlas/backups/atlas-2026-11-18-pre-mission5.db")
MIGRATION_1 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission5_stage1.sql")
MIGRATION_2 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission6_stage2.sql")
MIGRATION_3 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission11_stage3.sql")

W0 = 1795000000
W1 = 1795003600
ONE_XMR = 1_000_000_000_000

SECRET_PATTERNS = ("token_hash", "token_salt", "wallet", "password",
                   "seed", "private_key")
ADDRESS_SHAPE_RE = re.compile(r"[1-9A-HJ-NP-Za-km-z]{95}|[1-9A-HJ-NP-Za-km-z]{106}")

# Payload bytes deliberately different from the module's own fixtures.
SPEND = bytes([7]) * 32
VIEW = bytes([11]) * 32
PAYMENT = bytes([13]) * 8


def fresh_db(path):
    if os.path.exists(path):
        os.remove(path)
    shutil.copy2(SRC_DB, path)
    con = sqlite3.connect(path)
    con.executescript(open(MIGRATION_1).read())
    con.executescript(open(MIGRATION_2).read())
    con.executescript(open(MIGRATION_3).read())
    con.commit()
    uv = con.execute("PRAGMA user_version").fetchone()[0]
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()
    assert uv == 4, f"user_version after Stage 3 migration: {uv}"
    assert integ == "ok", f"integrity after Stage 2 migration: {integ}"
    return path


def make_user(con, username):
    cur = con.execute(
        "INSERT INTO users (username, email, email_verified, created_at) "
        "VALUES (?,?,0,?)",
        (username, f"{username}@example.invalid", int(time.time())))
    con.commit()
    return cur.lastrowid


def table_count(con, table):
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


ALL_TABLES = ("users", "workers", "shares", "sessions", "ledger",
              "reward_batches", "payouts", "referrals", "decisions",
              "events", "metrics", "pool_stats")


def snapshot_counts(con):
    return {t: table_count(con, t) for t in ALL_TABLES}


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="atlas-m10-sec-")
        self.db_path = os.path.join(self.tmpdir, "test.db")
        fresh_db(self.db_path)
        self.con = ac.connect(self.db_path)
        self.export_dir = os.path.join(self.tmpdir, "exports")
        os.makedirs(self.export_dir, exist_ok=True)

    def tearDown(self):
        self.con.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seed_admin_export(self):
        """Fresh admin.json for the temp DB in the temp export dir, so
        the battery's S6 live check has a file to compare against."""
        path = os.path.join(self.export_dir, "admin.json")
        atlas_admin.export_admin_json(self.con, export_path=path)
        return path

    def _run_check(self, check_id):
        fn = dict((c[0], c[2]) for c in sec.CHECK_DEFS)[check_id]
        name = dict((c[0], c[1]) for c in sec.CHECK_DEFS)[check_id]
        return sec._check(self.con, self.export_dir, check_id, name, fn)

    # -- Keccak-256 + Base58 --------------------------------------------
    def test_keccak_vectors(self):
        self.assertEqual(
            sec.keccak_256(b"").hex(), sec.KECCAK_EMPTY_HEX)
        # Known Keccak-256("abc") vector; must differ from NIST SHA3-256.
        import hashlib
        self.assertEqual(
            sec.keccak_256(b"abc").hex(),
            "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45")
        self.assertNotEqual(
            sec.keccak_256(b"").hex(), hashlib.sha3_256(b"").hexdigest())
        self.assertNotEqual(
            sec.keccak_256(b"abc").hex(), hashlib.sha3_256(b"abc").hexdigest())

    def test_b58_roundtrip(self):
        for data in (bytes(69), bytes(range(69)), bytes(range(77)),
                     bytes([255]) * 69):
            encoded = sec.monero_b58_encode(data)
            self.assertEqual(sec.monero_b58_decode(encoded), data)
        # Block lengths: 69 bytes -> 95 chars, 77 bytes -> 106 chars.
        self.assertEqual(len(sec.monero_b58_encode(bytes(69))), 95)
        self.assertEqual(len(sec.monero_b58_encode(bytes(77))), 106)
        with self.assertRaises(sec.SecurityError):
            sec.monero_b58_decode("0" * 11)  # forbidden char
        with self.assertRaises(sec.SecurityError):
            sec.monero_b58_decode("z" * 11)  # oversized block

    # -- S1 ---------------------------------------------------------------
    def test_s1_tamper_evidence(self):
        result = self._run_check("S1")
        self.assertEqual(result["result"], "PASS", result["evidence"])
        # Independent recomputation: tamper a fresh fixture, verify
        # names the entry; reversal + correction restores PASS.
        path, tcon = sec._fresh_temp_db(self.con)
        try:
            sec._scenario1_fixture(tcon)
            self.assertEqual(table_count(tcon, "ledger"), 5)
            self.assertTrue(rw.verify_chain(tcon)["ok"])
            victim = tcon.execute(
                "SELECT id FROM ledger ORDER BY id LIMIT 1").fetchone()["id"]
            tcon.execute("UPDATE ledger SET amount_piconero = amount_piconero + 1 "
                         "WHERE id = ?", (victim,))
            tcon.commit()
            bad = rw.verify_chain(tcon)
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["first_bad_entry_id"], victim)
        finally:
            sec._close_remove(tcon, path)

    # -- S2 ---------------------------------------------------------------
    def test_s2_share_dedupe(self):
        result = self._run_check("S2")
        self.assertEqual(result["result"], "PASS", result["evidence"])
        # Independent: same external_id under a different worker is a
        # conflict (batch rejected, worker suspended) — the engine rule.
        user = make_user(self.con, "zoe")
        w1 = ac.register_worker(self.con, user, "browser", "zoe-w1")["id"]
        w2 = ac.register_worker(self.con, user, "browser", "zoe-w2")["id"]
        share = {"difficulty": 3, "accepted": 1, "submitted_at": W0 + 5,
                 "origin": "pool", "external_id": "dup-x", "job_id": None}
        self.assertEqual(ac.record_shares(self.con, w1, [share])["inserted"], 1)
        clash = ac.record_shares(self.con, w2, [share])
        self.assertEqual(clash["inserted"], 0)
        self.assertEqual(clash["rejected"], 1)
        self.assertEqual(self.con.execute(
            "SELECT status FROM workers WHERE id = ?", (w2,)).fetchone()[0],
            "suspended")

    # -- S3 ---------------------------------------------------------------
    def test_s3_payout_idempotency(self):
        result = self._run_check("S3")
        self.assertEqual(result["result"], "PASS", result["evidence"])
        # Independent: the UNIQUE idempotency constraint rejects a
        # duplicate key on a temp DB.
        user = make_user(self.con, "yara")
        address = sec.build_monero_address(18, SPEND, VIEW)
        self.con.execute(
            "INSERT INTO payouts (user_id, amount_piconero, "
            "destination_address, status, created_at, idempotency_key) "
            "VALUES (?,?,?,?,?,?)",
            (user, 500, address, "pending", int(time.time()), "t-idem-1"))
        self.con.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute(
                "INSERT INTO payouts (user_id, amount_piconero, "
                "destination_address, status, created_at, idempotency_key) "
                "VALUES (?,?,?,?,?,?)",
                (user, 500, address, "pending", int(time.time()), "t-idem-1"))
            self.con.commit()
        self.con.rollback()

    # -- S4 ---------------------------------------------------------------
    def test_s4_token_handling(self):
        result = self._run_check("S4")
        self.assertEqual(result["result"], "PASS", result["evidence"])
        # Independent: plaintext credential never lands in the DB file.
        user = make_user(self.con, "xena")
        outcome = ac.register_worker(self.con, user, "desktop", "xena-d")
        with open(self.db_path, "rb") as f:
            self.assertNotIn(outcome["token"].encode("utf-8"), f.read())

    # -- S5 ---------------------------------------------------------------
    def test_s5_address_validation(self):
        result = self._run_check("S5")
        self.assertEqual(result["result"], "PASS", result["evidence"])
        # Independent vectors with different payload bytes.
        std = sec.build_monero_address(18, SPEND, VIEW)
        sub = sec.build_monero_address(42, SPEND, VIEW)
        integ = sec.build_monero_address(19, SPEND, VIEW, PAYMENT)
        self.assertEqual(sec.validate_monero_address(std),
                         (True, sec.FORMAT_VALID_LINE))
        self.assertTrue(std.startswith("4") and len(std) == 95)
        self.assertEqual(sec.validate_monero_address(sub),
                         (True, sec.FORMAT_VALID_LINE))
        self.assertTrue(sub.startswith("8") and len(sub) == 95)
        self.assertEqual(sec.validate_monero_address(integ),
                         (True, sec.FORMAT_VALID_LINE))
        self.assertTrue(integ.startswith("4") and len(integ) == 106)
        # Rejections with exact reasons.
        ok, reason = sec.validate_monero_address(std[:94])
        self.assertFalse(ok)
        self.assertIn("invalid length 94", reason)
        ok, reason = sec.validate_monero_address(std[:10] + "O" + std[11:])
        self.assertFalse(ok)
        self.assertIn("forbidden character 'O'", reason)
        ok, reason = sec.validate_monero_address(
            sec.build_monero_address(53, SPEND, VIEW))
        self.assertFalse(ok)
        self.assertIn("testnet network byte 53 rejected", reason)
        ok, reason = sec.validate_monero_address(
            sec.build_monero_address(24, SPEND, VIEW))
        self.assertFalse(ok)
        self.assertIn("stagenet network byte 24 rejected", reason)
        ok, reason = sec.validate_monero_address(
            sec.build_monero_address(42, SPEND, VIEW, PAYMENT))
        self.assertFalse(ok)
        self.assertIn("does not match length 106", reason)
        bad = std[:90] + ("1" if std[90] != "1" else "2") + std[91:]
        ok, reason = sec.validate_monero_address(bad)
        self.assertFalse(ok)
        self.assertIn("checksum mismatch", reason)
        ok, reason = sec._validate_payload(bytes(68))
        self.assertFalse(ok)
        self.assertIn("decoded length 68", reason)

    # -- S6 ---------------------------------------------------------------
    def test_s6_redaction(self):
        self._seed_admin_export()
        result = self._run_check("S6")
        self.assertEqual(result["result"], "PASS", result["evidence"])
        # Independent: a decision carrying a fake credential is redacted
        # in the admin export and the row is still counted.
        fake_hex = "b" * 64
        self.con.execute(
            "INSERT INTO decisions (ts, dept, decision, reason) VALUES "
            "(?,?,?,?)", (int(time.time()), "coordinator", "t6-fixture",
                          f"credential {fake_hex} seen"))
        self.con.commit()
        path = os.path.join(self.export_dir, "admin.json")
        atlas_admin.export_admin_json(self.con, export_path=path)
        with open(path) as f:
            raw = f.read()
        admin = json.loads(raw)
        self.assertNotIn(fake_hex, raw)
        self.assertEqual(admin["logs"]["decisions"]["total"],
                         table_count(self.con, "decisions"))
        rows = [r for r in admin["logs"]["decisions"]["rows"]
                if r["decision"] == "t6-fixture"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reason"], atlas_admin.REDACTED)
        for forbidden in SECRET_PATTERNS:
            self.assertNotIn(forbidden, raw)

    # -- S7 ---------------------------------------------------------------
    def test_s7_emergency_stop(self):
        result = self._run_check("S7")
        self.assertEqual(result["result"], "PASS", result["evidence"])
        # Independent: no start entry point exists in coordinator/monitor.
        for filename in ("atlas_coordinator.py", "atlas_monitor.py"):
            with open(os.path.join(sec.CORE, filename)) as f:
                self.assertNotIn("start_mining", f.read())

    # -- S8 ---------------------------------------------------------------
    def test_s8_simulation_only(self):
        result = self._run_check("S8")
        self.assertEqual(result["result"], "PASS", result["evidence"])
        _atlas_cfg, pool_cfg = sec.load_configs()
        self.assertEqual(pool_cfg.get("mode"), "simulation-only")
        self.assertIsNone(
            (pool_cfg.get("minimum_payout") or {}).get("piconero"))

    # -- S9 ---------------------------------------------------------------
    def test_s9_no_private_data(self):
        self._seed_admin_export()
        payload = sec.security_status(self.con, export_dir=self.export_dir)
        results = {t["id"]: t for t in payload["security_tests"]}
        self.assertEqual(results["S9"]["result"], "PASS",
                         results["S9"]["evidence"])
        serialized = json.dumps(payload, sort_keys=True)
        for forbidden in SECRET_PATTERNS:
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(ADDRESS_SHAPE_RE.findall(serialized), [])

    # -- Battery as a whole -------------------------------------------------
    def test_battery_all_pass_on_temp_db(self):
        self._seed_admin_export()
        payload = sec.security_status(self.con, export_dir=self.export_dir)
        self.assertEqual(len(payload["security_tests"]), 9)
        failed = [t for t in payload["security_tests"]
                  if t["result"] != "PASS"]
        self.assertEqual(failed, [])
        self.assertTrue(payload["emergency_stop"])
        self.assertEqual(payload["mode"], "simulation-only")
        counts = payload["security_counts"]
        self.assertEqual(set(counts), {
            "suspicious_workers", "invalid_shares", "duplicate_shares",
            "account_abuse", "auth_failures", "payout_anomalies"})
        self.assertEqual(counts, sec._live_counts_sql(self.con))
        self.assertEqual(payload["host_verified_totals"],
                         sec.host_verified_totals(self.con))
        self.assertEqual(payload["scale"]["reason"], sec.NO_SCALE_REASON)

    def test_security_status_writes_nothing(self):
        self._seed_admin_export()
        before = snapshot_counts(self.con)
        sec.security_status(self.con, export_dir=self.export_dir)
        after = snapshot_counts(self.con)
        self.assertEqual(before, after)

    def test_export_atomic_and_scale_preserved(self):
        self._seed_admin_export()
        path = os.path.join(self.export_dir, "security.json")
        sec.export_security_json(self.con, export_path=path)
        with open(path) as f:
            first = json.load(f)
        self.assertIsNone(first["scale"]["run_at"])
        self.assertEqual(first["scale"]["reason"], sec.NO_SCALE_REASON)
        self.assertFalse(os.path.exists(path + ".tmp"))
        fake_scale = {"run_at": 1234567890, "levels": [],
                      "l1": {}, "l2": {}, "l3": {}, "l4": {}, "l5": {},
                      "stale": False}
        sec.export_security_json(self.con, export_path=path, scale=fake_scale)
        _p, second = sec.export_security_json(self.con, export_path=path)
        self.assertEqual(second["scale"]["run_at"], 1234567890)

    def test_scale_refuses_non_temp_path(self):
        with self.assertRaises(sec.SecurityError):
            sec._require_temp_db(REAL_DB)
        with self.assertRaises(sec.SecurityError):
            sec._require_temp_db(os.path.expanduser("~/workspace/atlas/data/x.db"))
        sec._require_temp_db("/tmp/atlas-m10-ok.db")  # no raise

    def test_scale_smoke(self):
        smoke = sec.run_scale_smoke()
        self.assertEqual(smoke["workers"], 100)
        self.assertEqual(smoke["shares"], 10000)
        self.assertEqual(smoke["shares_inserted"], 10000)
        self.assertGreater(smoke["duration_s"], 0)
        self.assertGreater(smoke["shares_per_s"], 0)
        self.assertGreater(smoke["db_size_bytes"], 0)

    def test_run_pass_security_substep(self):
        # A fresh pool_stats row keeps the poll not-due, so the pass
        # never touches the pool network.
        self.con.execute(
            """INSERT INTO pool_stats
                   (pool_name, recorded_at, hashrate, miners, block_height,
                    network_hashrate, block_reward_piconero, pool_fee_bps)
               VALUES ('MoneroOcean', ?, 262107922, 4975, 3808993, NULL,
                       600000000000, 0)""",
            (int(time.time()),))
        self.con.commit()
        coord_path = os.path.join(self.tmpdir, "coordinator.json")
        before = table_count(self.con, "decisions")
        orig = None
        try:
            import atlas_profitability as prof
            orig = prof._http_get_json
            prof._http_get_json = lambda url: (_ for _ in ()).throw(
                RuntimeError("simulated egress failure"))
            summary = ac.run_pass(db_path=self.db_path, export_path=coord_path)
        finally:
            if orig is not None:
                prof._http_get_json = orig
        self.assertIn("exported_at", summary)
        # The pass logged exactly one new decision (pass-complete); the
        # security sub-step logs none of its own.
        self.assertEqual(table_count(self.con, "decisions"), before + 1)
        self.assertEqual(
            self.con.execute(
                "SELECT decision FROM decisions ORDER BY id DESC LIMIT 1"
            ).fetchone()[0], "coordinator-pass-complete")
        # All six exports landed in the temp dir, none in the live dir.
        for name in ("coordinator.json", "rewards.json", "dashboard.json",
                     "admin.json", "profitability.json", "security.json"):
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, name)),
                            f"{name} missing after run_pass")
        with open(os.path.join(self.tmpdir, "security.json")) as f:
            security = json.load(f)
        age = int(time.time()) - security["exported_at"]
        self.assertLess(age, 600, f"security.json exported_at {age}s old")
        self.assertEqual(len(security["security_tests"]), 9)
        self.assertTrue(all(t["result"] == "PASS"
                            for t in security["security_tests"]),
                        [t for t in security["security_tests"]
                         if t["result"] != "PASS"])
        self.assertIsNone(security["scale"]["run_at"])
        self.assertEqual(security["scale"]["reason"], sec.NO_SCALE_REASON)

    def test_scale_l1_l5_on_demand(self):
        """Full on-demand scale battery (slow: loads 100,000 synthetic
        shares and runs the full diagnostics suite once for L3)."""
        scale = sec.run_scale_tests()
        self.assertIsInstance(scale["run_at"], int)
        self.assertGreater(scale["run_duration_s"], 0)
        labels = [lv["label"] for lv in scale["levels"]]
        self.assertEqual(labels, [
            "1x baseline (live shape: 0 workers, 0 shares)",
            "100 workers / 10,000 shares",
            "1,000 workers / 100,000 shares"])
        for lv in scale["levels"]:
            self.assertGreater(lv["run_pass_s"], 0)
            self.assertLess(lv["run_pass_s"], 60)
            self.assertGreater(lv["db_size_bytes"], 0)
            self.assertIn(lv["slowest_step"],
                          ("run_pass_s", "attribution_weights_s",
                           "verify_chain_10000_s", "record_shares_total_s"))
        big = scale["levels"][2]
        self.assertEqual(big["shares_inserted"], 100000)
        # Mission 12 fix (D-M12-1): true per-worker spread — the load
        # must land on all registered workers, not 2 of them.
        self.assertEqual(big["workers_with_shares"], 1000)
        self.assertEqual(big["shares_per_worker"], 100)
        self.assertEqual(scale["levels"][1]["workers_with_shares"], 100)
        self.assertEqual(scale["levels"][1]["shares_per_worker"], 100)
        self.assertIsNotNone(big["verify_chain_10000_s"])
        self.assertGreater(big["record_shares_per_s"], 0)
        self.assertEqual(scale["l2"]["result"], "NOT_RUN")
        self.assertEqual(scale["l2"]["reason"], sec.L2_NOT_RUN_REASON)
        l3 = scale["l3"]
        self.assertGreater(l3["live_s"], 0)
        self.assertEqual(l3["temp_reason"], sec.L3_TEMP_NOT_RUN_REASON)
        self.assertGreater(l3["temp_db_checks_s"], 0)
        l4 = scale["l4"]
        self.assertEqual(l4["label"], "ESTIMATE")
        self.assertEqual(l4["formula"],
                         "size ≈ base + rows × bytes_per_row")
        self.assertEqual(set(l4["projection_shares"]),
                         {"10000", "100000", "1000000"})
        self.assertGreater(l4["bytes_per_row"]["shares"], 0)
        self.assertGreater(l4["bytes_per_row"]["ledger_entries"], 0)
        l5 = scale["l5"]
        self.assertIn("bottleneck", l5)
        self.assertIsInstance(l5["bottleneck"], str)
        self.assertTrue(l5["bottleneck"])
        # Mission 11 fix (D-M11-2): the record_shares O(n^2) bottleneck
        # is FIXED — batched indexed conflict check + Stage 3
        # idx_shares_external_id. At 1,000 workers / 100,000 shares the
        # whole share load must now finish well under the 30 s
        # single-step limit, and L5 must report no bottleneck.
        self.assertEqual(l5["bottleneck"], sec.NO_BOTTLENECK)
        self.assertIsNone(l5["first_bottleneck_load"])
        self.assertLess(big["record_shares_total_s"], 30)
        self.assertGreater(big["record_shares_per_s"], 10000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
