#!/usr/bin/env python3
"""ATLAS Master Mission 7 — Lane C host dashboard module tests.

Runs ONLY against temp copies of atlas.db in /tmp. NEVER writes to the
real ~/workspace/atlas/data/atlas.db. The real DB is copied from the
PRE-MIGRATION backup (user_version 1), the Stage 1 migration is applied,
then the Stage 2 migration — all test/sim data lives in /tmp. (Same
fixture pattern as core/test_reward_engine.py.)

Test plan (task §3):
  (a) zero-state derivation — every field null/0 with the verbatim
      reasons; status + export write nothing to the DB.
  (b) simulation scenario — settled 1 XMR sim batch (Alice 60 / Bob 40,
      Bob referred by Alice; Mission 6 scenario-1 figures) + 6 accepted
      + 4 rejected pool shares + 2 ended sessions.
  (c) export idempotence + atomic write.
  (d) run_pass() dashboard sub-step does not fail the pass on a temp DB.

Usage: python3 core/test_atlas_dashboard.py [-v]
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
import atlas_rewards as rw

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


def make_user(con, username, email=None):
    cur = con.execute(
        "INSERT INTO users (username, email, email_verified, created_at) "
        "VALUES (?,?,0,?)",
        (username, email or f"{username}@example.invalid", int(time.time())))
    con.commit()
    return cur.lastrowid


def make_worker(con, user_id, worker_type, name):
    return ac.register_worker(con, user_id, worker_type, name)["id"]


def add_local_share(con, worker_id, difficulty, tag, submitted_at):
    result = ac.record_share(con, worker_id, difficulty, tag, True, True,
                             submitted_at=submitted_at)
    assert result is not None, f"local-test share {tag} was not recorded"
    return result


def add_referral(con, referrer_user_id, referred_user_id):
    cur = con.execute(
        "INSERT INTO referrals (referrer_user_id, referred_user_id, status, created_at) "
        "VALUES (?,?, 'pending', ?)",
        (referrer_user_id, referred_user_id, int(time.time())))
    con.commit()
    return cur.lastrowid


def table_count(con, table):
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="atlas-m7-dash-")
        self.db_path = os.path.join(self.tmpdir, "test.db")
        fresh_db(self.db_path)
        self.con = ac.connect(self.db_path)
        self.export_path = os.path.join(self.tmpdir, "dashboard.json")

    def tearDown(self):
        self.con.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- (a) zero-state derivation --------------------------------------
    def test_a_zero_state(self):
        before = {t: table_count(self.con, t) for t in
                  ("users", "workers", "shares", "sessions", "ledger",
                   "reward_batches", "payouts", "referrals", "decisions")}
        payload = db.dashboard_status(self.con, export_dir=self.tmpdir)
        # Status + export must write NOTHING to the DB (read-only derivation).
        path, exported = db.export_dashboard_json(
            self.con, export_path=self.export_path)
        after = {t: table_count(self.con, t) for t in before}
        self.assertEqual(after, before, "dashboard derivation wrote to the DB")
        self.assertEqual(exported, payload)

        self.assertEqual(payload["source_db_user_version"], 4)
        self.assertEqual(payload["mode"], "simulation-only")
        self.assertTrue(payload["emergency_stop"])
        # Hashrate: Gate 1 unmeasured, verbatim note.
        self.assertEqual(payload["hashrate"], {
            "status": "not-measured", "current_hps": None,
            "average_hps": None,
            "note": "Gate 1 unmeasured — no probe measurement exists"})
        # Shares / workers / duration: all zero.
        self.assertEqual(payload["shares"], {
            "pool_accepted": 0, "pool_rejected": 0,
            "local_test_accepted": 0, "local_test_rejected": 0})
        self.assertEqual(payload["workers"]["total"], 0)
        self.assertEqual(payload["workers"]["active"], 0)
        self.assertEqual(payload["duration"]["total_session_seconds"], 0)
        self.assertEqual(payload["duration"]["active_sessions"], 0)
        # Earnings: never an estimate; confirmed 0, simulation-only.
        self.assertEqual(payload["earnings"], {
            "estimated_piconero": None,
            "estimated_reason": "Cannot estimate — hashrate not measured",
            "confirmed_piconero": 0,
            "confirmed_note": "SIMULATION ONLY — no pool rewards",
            "mode": "simulation-only"})
        self.assertEqual(payload["balances"], {})
        self.assertEqual(payload["lifetime"], {
            "lifetime_user_rewards_piconero": 0,
            "lifetime_referral_rewards_piconero": 0,
            "lifetime_atlas_share_piconero": 0,
            "lifetime_pool_fees_piconero": 0,
            "lifetime_payouts_piconero": 0,
            "lifetime_reversals_piconero": 0})
        self.assertEqual(payload["payouts"], {
            "count": 0, "total_piconero": 0, "rows": []})
        # Efficiency: not measurable with no shares.
        self.assertEqual(payload["efficiency"], {
            "acceptance_rate": None,
            "reason": "Cannot compute — no pool shares yet"})
        # Sync: no source exports in the temp dir -> stale.
        self.assertIsNone(payload["sync"]["coordinator_exported_at"])
        self.assertIsNone(payload["sync"]["rewards_exported_at"])
        self.assertTrue(payload["sync"]["stale"])
        self.assertEqual(payload["sync"]["dashboard_exported_at"],
                         payload["exported_at"])
        # Host-verified totals: all zero.
        self.assertEqual(payload["host_verified_totals"], {
            "ledger_entries": 0, "batches_settled": 0,
            "total_user_rewards_piconero": 0,
            "total_atlas_share_piconero": 0})
        # The exported file parses and matches the payload.
        with open(path) as f:
            on_disk = json.load(f)
        self.assertEqual(on_disk, payload)

    # -- (b) simulation scenario -----------------------------------------
    def test_b_simulation_scenario(self):
        # Mission 6 scenario 1: Alice (browser + desktop, 60 weight),
        # Bob (desktop, 40 weight), 8 local-test shares; Bob referred
        # by Alice. 1 XMR sim batch, MoneroOcean (0 bps fee).
        alice = make_user(self.con, "alice")
        bob = make_user(self.con, "bob")
        wa_b = make_worker(self.con, alice, "browser", "alice-browser")
        wa_d = make_worker(self.con, alice, "desktop", "alice-desktop")
        wb_d = make_worker(self.con, bob, "desktop", "bob-desktop")
        for tag, diff, at in (("s1", 10, W0 + 10), ("s2", 20, W0 + 20)):
            add_local_share(self.con, wa_b, diff, tag, at)
        for tag, diff, at in (("s3", 15, W0 + 30), ("s4", 15, W0 + 40)):
            add_local_share(self.con, wa_d, diff, tag, at)
        for tag, diff, at in (("s5", 10, W0 + 50), ("s6", 10, W0 + 60),
                              ("s7", 10, W0 + 70), ("s8", 10, W0 + 80)):
            add_local_share(self.con, wb_d, diff, tag, at)
        add_referral(self.con, alice, bob)
        batch_id = rw.record_batch(
            self.con, "MoneroOcean", "simulation", "sim-20261118-001",
            W0, W1, ONE_XMR, source_evidence="simulated-harness:scenario-1",
            batch_ref="sim-20261118-001")
        self.assertIsNotNone(batch_id)
        result = rw.settle_batch(self.con, batch_ref="sim-20261118-001")
        self.assertEqual(result["status"], "settled")
        # 6 accepted + 4 rejected POOL shares (efficiency evidence only;
        # they never enter the simulation batch's attribution).
        pool_shares = []
        for i in range(6):
            pool_shares.append({"difficulty": 1, "accepted": 1,
                                "submitted_at": W0 + 100 + i, "origin": "pool",
                                "external_id": f"pool:sc-b-acc-{i}", "job_id": None})
        for i in range(4):
            pool_shares.append({"difficulty": 1, "accepted": 0,
                                "submitted_at": W0 + 200 + i, "origin": "pool",
                                "external_id": f"pool:sc-b-rej-{i}", "job_id": None})
        recorded = ac.record_shares(self.con, wa_b, pool_shares)
        self.assertEqual(recorded["inserted"], 10)
        # 2 ended DESKTOP worker sessions: 3600 s + 1800 s = 5400 s total.
        for created_at, ended_at in ((W0, W0 + 3600),
                                     (W0 + 7200, W0 + 7200 + 1800)):
            self.con.execute(
                """INSERT INTO sessions
                       (user_id, session_token_hash, created_at, expires_at,
                        worker_id, kind, ended_at, session_ref)
                   VALUES (?, 'desktop-session-token-hash', ?, ?, ?, 'worker', ?, ?)""",
                (alice, created_at, created_at + 86400, wa_b, ended_at,
                 f"session-{created_at}"))
        # A browser-probe session and a degenerate ended session must
        # contribute 0 (design D-M7-4).
        for created_at, ended_at, token_hash in (
                (W0, W0 + 10000, "none:browser-probe"),
                (W0 + 20000, W0 + 19000, "desktop-session-token-hash")):
            self.con.execute(
                """INSERT INTO sessions
                       (user_id, session_token_hash, created_at, expires_at,
                        worker_id, kind, ended_at, session_ref)
                   VALUES (?, ?, ?, ?, ?, 'worker', ?, ?)""",
                (alice, token_hash, created_at, created_at + 86400, wa_b,
                 ended_at, f"excluded-{created_at}"))
        self.con.commit()

        payload = db.dashboard_status(self.con, export_dir=self.tmpdir)
        # Confirmed totals: Mission 6 scenario-1 figures, exact.
        self.assertEqual(payload["earnings"]["confirmed_piconero"], 750_000_000_000)
        self.assertEqual(payload["earnings"]["estimated_piconero"], None)
        self.assertEqual(payload["earnings"]["estimated_reason"],
                         "Cannot estimate — hashrate not measured")
        self.assertEqual(payload["earnings"]["confirmed_note"],
                         "SIMULATION ONLY — no pool rewards")
        self.assertEqual(payload["lifetime"]["lifetime_user_rewards_piconero"],
                         750_000_000_000)
        self.assertEqual(payload["lifetime"]["lifetime_atlas_share_piconero"],
                         235_000_000_000)
        self.assertEqual(payload["lifetime"]["lifetime_referral_rewards_piconero"],
                         15_000_000_000)
        self.assertEqual(payload["lifetime"]["lifetime_pool_fees_piconero"], 0)
        self.assertEqual(payload["lifetime"]["lifetime_payouts_piconero"], 0)
        self.assertEqual(payload["lifetime"]["lifetime_reversals_piconero"], 0)
        self.assertEqual(payload["balances"],
                         {alice: 465_000_000_000, bob: 300_000_000_000})
        self.assertEqual(payload["host_verified_totals"], {
            "ledger_entries": 5, "batches_settled": 1,
            "total_user_rewards_piconero": 750_000_000_000,
            "total_atlas_share_piconero": 235_000_000_000})
        # Shares: pool 6/4, local-test 8 accepted.
        self.assertEqual(payload["shares"], {
            "pool_accepted": 6, "pool_rejected": 4,
            "local_test_accepted": 8, "local_test_rejected": 0})
        # Efficiency: pool shares only -> 6 / (6 + 4) = 0.6 exactly.
        self.assertEqual(payload["efficiency"]["acceptance_rate"], 0.6)
        self.assertIsNone(payload["efficiency"]["reason"])
        # Duration: SUM of ended sessions only.
        self.assertEqual(payload["duration"]["total_session_seconds"], 5400)
        self.assertEqual(payload["duration"]["active_sessions"], 0)
        # Workers: 3 registered, 0 active.
        self.assertEqual(payload["workers"]["total"], 3)
        self.assertEqual(payload["workers"]["active"], 0)
        self.assertEqual(payload["workers"]["registered"], 3)
        # Hashrate still unmeasured even with shares and a settled batch.
        self.assertEqual(payload["hashrate"]["status"], "not-measured")
        self.assertIsNone(payload["hashrate"]["current_hps"])
        self.assertIsNone(payload["hashrate"]["average_hps"])
        # No payouts yet.
        self.assertEqual(payload["payouts"]["count"], 0)
        self.assertEqual(payload["payouts"]["total_piconero"], 0)
        self.assertEqual(payload["payouts"]["rows"], [])
        # Chain still verifies on the fixture DB.
        self.assertTrue(rw.verify_chain(self.con)["ok"])

    # -- (c) export idempotence + atomic write ---------------------------
    def test_c_export_idempotence_atomic(self):
        _, payload1 = db.export_dashboard_json(
            self.con, export_path=self.export_path)
        self.assertTrue(os.path.exists(self.export_path))
        self.assertFalse(os.path.exists(self.export_path + ".tmp"),
                         "atomic-write temp file left behind")
        with open(self.export_path) as f:
            on_disk1 = json.load(f)
        self.assertEqual(on_disk1, payload1)
        _, payload2 = db.export_dashboard_json(
            self.con, export_path=self.export_path)
        self.assertFalse(os.path.exists(self.export_path + ".tmp"))
        with open(self.export_path) as f:
            on_disk2 = json.load(f)
        self.assertEqual(on_disk2, payload2)

        def _stable(payload):
            stable = dict(payload)
            stable.pop("exported_at", None)
            stable["sync"] = {k: v for k, v in payload["sync"].items()
                              if k != "dashboard_exported_at"}
            return stable

        # Byte-identical apart from exported_at (both exports landed in
        # the same second here, so the files are fully identical; the
        # stable comparison is what the requirement pins down).
        self.assertEqual(_stable(payload1), _stable(payload2))
        self.assertIsInstance(payload1["exported_at"], int)
        self.assertIsInstance(payload2["exported_at"], int)

    # -- (d) run_pass dashboard sub-step ---------------------------------
    def test_d_run_pass_dashboard_substep(self):
        # A fresh pool_stats row keeps the poll not-due, so the pass
        # never touches the network.
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
        summary = ac.run_pass(db_path=self.db_path, export_path=coord_path)
        self.assertIn("exported_at", summary)
        self.assertEqual(summary["rewards"], {"batches_due": 0, "settled": [],
                                              "held": [], "refused": [],
                                              "noop": [], "failed": []})
        # The pass logged exactly one new decision (pass-complete); the
        # dashboard sub-step logs none of its own.
        self.assertEqual(table_count(self.con, "decisions"), before + 1)
        self.assertEqual(
            self.con.execute(
                "SELECT decision FROM decisions ORDER BY id DESC LIMIT 1"
            ).fetchone()[0], "coordinator-pass-complete")
        # All three exports landed in the temp dir, none in the live dir.
        for name in ("coordinator.json", "rewards.json", "dashboard.json"):
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, name)),
                            f"{name} missing after run_pass")
        with open(os.path.join(self.tmpdir, "dashboard.json")) as f:
            dash = json.load(f)
        self.assertEqual(dash["host_verified_totals"]["ledger_entries"], 0)
        self.assertEqual(dash["host_verified_totals"]["batches_settled"], 0)
        self.assertFalse(dash["sync"]["stale"],
                         "sync should be fresh right after a pass")
        with open(coord_path) as f:
            coord_exported_at = json.load(f)["exported_at"]
        with open(os.path.join(self.tmpdir, "rewards.json")) as f:
            rewards_exported_at = json.load(f)["exported_at"]
        self.assertEqual(dash["sync"]["coordinator_exported_at"],
                         coord_exported_at)
        self.assertEqual(dash["sync"]["rewards_exported_at"],
                         rewards_exported_at)


if __name__ == "__main__":
    unittest.main(verbosity=2)
