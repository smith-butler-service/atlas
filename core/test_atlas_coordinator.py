#!/usr/bin/env python3
"""ATLAS Master Mission 5 — Lane C unit tests + simulation.

Runs ONLY against temp copies of atlas.db in /tmp. NEVER writes to the
real ~/workspace/atlas/data/atlas.db. The real DB is copied, the Stage 1
migration is applied to the copy, and all test/sim data lives in /tmp.

Usage: python3 /tmp/atlas_m5_test.py
"""
import copy
import io
import json
import os
import shutil
import sqlite3
import sys
import time
import unittest
import urllib.error

sys.path.insert(0, os.path.expanduser("~/workspace/atlas/core"))
import atlas_coordinator as ac

REAL_DB = os.path.expanduser("~/workspace/atlas/data/atlas.db")
# Test source: the PRE-MIGRATION backup (user_version 1). The live DB is
# now user_version 2, so re-applying the migration to a live copy fails
# (duplicate column) — the backup is the correct pre-migration source.
SRC_DB = os.path.expanduser(
    "~/workspace/atlas/backups/atlas-2026-11-18-pre-mission5.db")
MIGRATION = os.path.expanduser("~/workspace/atlas/core/migrate_mission5_stage1.sql")
TEST_DB = "/tmp/atlas-m5-test.db"
SIM_DB = "/tmp/atlas-m5-sim.db"
SIM_EXPORT = "/tmp/atlas-m5-sim-coordinator.json"

# Canned MoneroOcean /pool/stats payload — same shape as the live response
# fetched 2026-11-18 (hashRate float, miners int, lastBlockFound height).
POOL_OK = {
    "pool_statistics": {
        "hashRate": 262107921.50166667,
        "miners": 4975,
        "lastBlockFound": 3808993,
        "lastBlockFoundTime": 1794995218,
        "totalHashes": 1.4763170154947991e+23,
    },
    "updatedAt": 1794997369,
}


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_opener_ok(req, timeout=None):
    return FakeResponse(POOL_OK)


def fake_opener_fail(req, timeout=None):
    raise urllib.error.URLError("timed out (simulated)")


def fresh_db(path):
    if os.path.exists(path):
        os.remove(path)
    shutil.copy2(SRC_DB, path)
    con = sqlite3.connect(path)
    con.executescript(open(MIGRATION).read())
    con.commit()
    uv = con.execute("PRAGMA user_version").fetchone()[0]
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()
    assert uv == 2, f"user_version after migration: {uv}"
    assert integ == "ok", f"integrity after migration: {integ}"
    return path


def make_user(con, username, email):
    cur = con.execute(
        "INSERT INTO users (username, email, email_verified, created_at) "
        "VALUES (?,?,0,?)", (username, email, int(time.time())))
    con.commit()
    return cur.lastrowid


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        # Fresh migrated copy per test: tests are independent and order-free.
        self.db_path = f"/tmp/atlas-m5-test-{self._testMethodName}.db"
        fresh_db(self.db_path)
        self.con = ac.connect(self.db_path)
        self.user_id = make_user(self.con, f"u-{self._testMethodName}"[:30],
                                 f"{self._testMethodName}@example.invalid")

    def tearDown(self):
        self.con.close()

    # -- registration ---------------------------------------------------
    def test_register_desktop_token_once_scrypt_only(self):
        t0 = time.time()
        r = ac.register_worker(self.con, self.user_id, "desktop", "rig1")
        dt = time.time() - t0
        self.assertEqual(r["status"], "registered")
        self.assertTrue(r["token"])
        self.assertLess(dt, 5.0, "scrypt must stay cheap on this host")
        row = self.con.execute(
            "SELECT token_hash, token_salt, token_status FROM workers WHERE id=?",
            (r["id"],)).fetchone()
        self.assertEqual(row["token_status"], "active")
        self.assertTrue(row["token_hash"] and row["token_salt"])
        self.assertNotEqual(row["token_hash"], r["token"])
        self.assertTrue(ac.verify_worker_token(self.con, r["id"], r["token"]))
        self.assertFalse(ac.verify_worker_token(self.con, r["id"], "wrong-token"))
        self.assertFalse(ac.verify_worker_token(self.con, r["id"], ""))
        # Plaintext token must not appear anywhere in the DB file.
        raw = open(self.db_path, "rb").read()
        self.assertNotIn(r["token"].encode(), raw)

    def test_register_browser_no_token(self):
        r = ac.register_worker(self.con, self.user_id, "browser", "tab1")
        self.assertIsNone(r["token"])
        row = self.con.execute(
            "SELECT token_hash, token_salt, status FROM workers WHERE id=?",
            (r["id"],)).fetchone()
        self.assertIsNone(row["token_hash"])
        self.assertIsNone(row["token_salt"])
        self.assertEqual(row["status"], "registered")

    def test_register_validation(self):
        with self.assertRaises(ac.CoordinatorError):
            ac.register_worker(self.con, self.user_id, "desktop", "Bad Name!")
        with self.assertRaises(ac.CoordinatorError):
            ac.register_worker(self.con, self.user_id, "desktop", "x" * 33)
        with self.assertRaises(ac.CoordinatorError):
            ac.register_worker(self.con, self.user_id, "gpu", "rig1")
        with self.assertRaises(ac.CoordinatorError):
            ac.register_worker(self.con, 999999, "desktop", "rig1")
        ac.register_worker(self.con, self.user_id, "desktop", "dup")
        with self.assertRaises(ac.CoordinatorError):
            ac.register_worker(self.con, self.user_id, "browser", "dup")
        # Same name for a DIFFERENT user is fine.
        other = make_user(self.con, "other-user", "other@example.invalid")
        ac.register_worker(self.con, other, "browser", "dup")

    def test_rotate_and_revoke(self):
        r = ac.register_worker(self.con, self.user_id, "desktop", "rig2")
        old = r["token"]
        new = ac.rotate_token(self.con, r["id"])
        self.assertNotEqual(new["token"], old)
        self.assertFalse(ac.verify_worker_token(self.con, r["id"], old))
        self.assertTrue(ac.verify_worker_token(self.con, r["id"], new["token"]))
        ac.revoke_worker(self.con, r["id"])
        row = self.con.execute(
            "SELECT status, token_status FROM workers WHERE id=?", (r["id"],)).fetchone()
        self.assertEqual(row["status"], "revoked")
        self.assertEqual(row["token_status"], "revoked")
        self.assertFalse(ac.verify_worker_token(self.con, r["id"], new["token"]))
        with self.assertRaises(ac.CoordinatorError):
            ac.rotate_token(self.con, r["id"])
        b = ac.register_worker(self.con, self.user_id, "browser", "tabx")
        with self.assertRaises(ac.CoordinatorError):
            ac.rotate_token(self.con, b["id"])

    # -- shares ---------------------------------------------------------
    def test_local_test_shares_never_count_as_pool(self):
        w = ac.register_worker(self.con, self.user_id, "browser", "ltab")
        batch = [{"difficulty": 1000, "accepted": 1, "submitted_at": 1794997000,
                  "origin": "local-test", "external_id": f"local-test:sess1:{i}",
                  "job_id": "job-a"} for i in range(1, 5)]
        batch.append({"difficulty": 1000, "accepted": 0, "submitted_at": 1794997001,
                      "origin": "local-test", "external_id": "local-test:sess1:5",
                      "job_id": "job-a"})
        res = ac.record_shares(self.con, w["id"], batch)
        self.assertEqual(res, {"inserted": 5, "duplicates_skipped": 0, "rejected": 0})
        self.assertEqual(ac.attribution_weights(self.con), {},
                         "local-test shares must carry zero attribution weight")
        st = ac.coordinator_status(self.con)
        self.assertEqual(st["shares"]["local_test_accepted"], 4)
        self.assertEqual(st["shares"]["local_test_rejected"], 1)
        self.assertEqual(st["shares"]["pool_accepted"], 0)
        self.assertEqual(st["shares"]["pool_rejected"], 0)

    def test_record_share_wrapper_verified_gate(self):
        w = ac.register_worker(self.con, self.user_id, "desktop", "wrap1")
        self.assertIsNone(ac.record_share(
            self.con, w["id"], 500, "deadbeef", verified=False, local_test=True))
        n = self.con.execute("SELECT COUNT(*) FROM shares").fetchone()[0]
        self.assertEqual(n, 0, "unverified shares must not be recorded")
        self.assertIsNotNone(ac.record_share(
            self.con, w["id"], 500, "deadbeef", verified=True, local_test=True))
        row = self.con.execute(
            "SELECT origin, external_id, accepted FROM shares").fetchone()
        self.assertEqual(row["origin"], "local-test")
        self.assertEqual(row["external_id"], "local-test:deadbeef")
        self.assertEqual(row["accepted"], 1)

    def test_share_dedupe_and_cross_worker_conflict(self):
        w1 = ac.register_worker(self.con, self.user_id, "desktop", "d1")
        w2 = ac.register_worker(self.con, self.user_id, "desktop", "d2")
        share = {"difficulty": 10, "accepted": 1, "submitted_at": 1794997000,
                 "origin": "pool", "external_id": "pool-share-1", "job_id": "j1"}
        self.assertEqual(ac.record_shares(self.con, w1["id"], [share])["inserted"], 1)
        res = ac.record_shares(self.con, w1["id"], [share])
        self.assertEqual(res["duplicates_skipped"], 1)
        self.assertEqual(res["inserted"], 0)
        # Same external_id for a DIFFERENT worker: conflict, batch rejected,
        # worker suspended.
        res = ac.record_shares(self.con, w2["id"], [share])
        self.assertEqual(res["rejected"], 1)
        self.assertEqual(res["inserted"], 0)
        row = self.con.execute("SELECT status FROM workers WHERE id=?",
                               (w2["id"],)).fetchone()
        self.assertEqual(row["status"], "suspended")

    def test_share_batch_rejected_unknown_and_revoked(self):
        res = ac.record_shares(self.con, 999999, [{
            "difficulty": 1, "accepted": 1, "origin": "pool",
            "external_id": "x1"}])
        self.assertEqual(res["rejected"], 1)
        w = ac.register_worker(self.con, self.user_id, "desktop", "rev1")
        ac.revoke_worker(self.con, w["id"])
        res = ac.record_shares(self.con, w["id"], [{
            "difficulty": 1, "accepted": 1, "origin": "pool",
            "external_id": "x2"}])
        self.assertEqual(res["rejected"], 1)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM shares").fetchone()[0], 0)

    def test_local_test_requires_prefix_and_pool_needs_active_token(self):
        w = ac.register_worker(self.con, self.user_id, "browser", "pfx")
        res = ac.record_shares(self.con, w["id"], [{
            "difficulty": 1, "accepted": 1, "origin": "local-test",
            "external_id": "not-prefixed"}])
        self.assertEqual(res, {"inserted": 0, "duplicates_skipped": 0, "rejected": 1})
        # NULL-difficulty pool share: inserted but flagged in the decision log.
        res = ac.record_shares(self.con, w["id"], [{
            "difficulty": None, "accepted": 1, "origin": "pool",
            "external_id": "pool-null-diff"}])
        self.assertEqual(res["inserted"], 1)
        flag = self.con.execute(
            "SELECT COUNT(*) FROM decisions WHERE decision='share-batch-null-difficulty'"
            ).fetchone()[0]
        self.assertEqual(flag, 1)

    # -- sessions -------------------------------------------------------
    def test_worker_sessions(self):
        b = ac.register_worker(self.con, self.user_id, "browser", "probe1")
        s = ac.record_worker_session(self.con, b["id"], "browser-probe",
                                     session_ref="tab-session-42")
        self.assertIsNone(s["session_token"])
        row = self.con.execute(
            "SELECT kind, session_token_hash, user_id, session_ref, ended_at "
            "FROM sessions WHERE id=?", (s["session_id"],)).fetchone()
        self.assertEqual(row["kind"], "worker")
        self.assertEqual(row["session_token_hash"], ac.NO_CREDENTIAL_MARKER)
        self.assertEqual(row["user_id"], self.user_id)
        self.assertEqual(row["session_ref"], "tab-session-42")
        self.assertIsNone(row["ended_at"])
        self.assertTrue(ac.close_worker_session(self.con, session_id=s["session_id"]))
        self.assertFalse(ac.close_worker_session(self.con, session_id=s["session_id"]))

    def test_worker_sessions_duration_seconds(self):
        # Design D-M7-4 (binding): duration counts desktop-agent worker
        # sessions only. Browser-probe sessions, degenerate ended rows,
        # and user sessions contribute 0; open sessions count up to now.
        d = ac.register_worker(self.con, self.user_id, "desktop", "rig-dur")
        now = int(time.time())
        rows = [
            # (token_hash, created_at, expires_at, ended_at, kind)
            ("desktop-token-hash", 1000, 2000000000, 4600, "worker"),  # +3600
            (ac.NO_CREDENTIAL_MARKER, 1000, 2000000000, 11000, "worker"),  # probe: 0
            ("desktop-token-hash", 5000, 2000000000, 4000, "worker"),  # degenerate: 0
            ("desktop-token-hash", 1000, 2000000000, 11000, "user"),  # user session: 0
            ("desktop-token-hash", now - 600, now + 3600, None, "worker"),  # open: ~600
        ]
        for token_hash, created_at, expires_at, ended_at, kind in rows:
            self.con.execute(
                "INSERT INTO sessions (user_id, session_token_hash, created_at, "
                "expires_at, worker_id, kind, ended_at, session_ref) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.user_id, token_hash, created_at, expires_at, d["id"],
                 kind, ended_at, f"dur-{created_at}-{kind}"))
        self.con.commit()
        status = ac.coordinator_status(self.con)
        total = status["worker_sessions_duration_seconds"]
        self.assertGreaterEqual(total, 4200)
        self.assertLessEqual(total, 4215)
        self.assertEqual(status["sessions_active"], 1)

    def test_desktop_session_token_conflict(self):
        w = ac.register_worker(self.con, self.user_id, "desktop", "agent1")
        s1 = ac.record_worker_session(self.con, w["id"], "desktop-agent",
                                      session_ref="agent-A")
        self.assertTrue(s1["session_token"])
        # Same agent instance re-checking in: idempotent, same session.
        s2 = ac.record_worker_session(self.con, w["id"], "desktop-agent",
                                      session_ref="agent-A")
        self.assertEqual(s2["session_id"], s1["session_id"])
        # Different agent instance, same token context: conflict -> suspended.
        with self.assertRaises(ac.CoordinatorError):
            ac.record_worker_session(self.con, w["id"], "desktop-agent",
                                     session_ref="agent-B")
        row = self.con.execute("SELECT status FROM workers WHERE id=?",
                               (w["id"],)).fetchone()
        self.assertEqual(row["status"], "suspended")

    def test_expired_sessions_close_lazily(self):
        w = ac.register_worker(self.con, self.user_id, "browser", "exp1")
        s = ac.record_worker_session(self.con, w["id"], "browser-probe",
                                     session_ref="tab-1")
        self.con.execute("UPDATE sessions SET expires_at = ? WHERE id = ?",
                         (int(time.time()) - 10, s["session_id"]))
        self.con.commit()
        self.assertEqual(ac.close_expired_sessions(self.con), 1)
        row = self.con.execute("SELECT ended_at FROM sessions WHERE id=?",
                               (s["session_id"],)).fetchone()
        self.assertIsNotNone(row["ended_at"])

    # -- activation gate -------------------------------------------------
    def test_verify_worker_active_gated(self):
        w = ac.register_worker(self.con, self.user_id, "desktop", "gate1")
        res = ac.verify_worker_active(self.con, w["id"])
        self.assertFalse(res["activated"])
        self.assertEqual(res["reason"], "emergency-stop")
        row = self.con.execute("SELECT status FROM workers WHERE id=?",
                               (w["id"],)).fetchone()
        self.assertEqual(row["status"], "registered")
        n = self.con.execute(
            "SELECT COUNT(*) FROM decisions WHERE decision='worker-activation-held'"
            ).fetchone()[0]
        self.assertEqual(n, 1)

    # -- pool stats -------------------------------------------------------
    def test_poll_pool_stats_success(self):
        res = ac.poll_pool_stats(self.con, opener=fake_opener_ok)
        self.assertTrue(res["ok"])
        self.assertEqual(res["hashrate"], 262107922)  # int(round(262107921.50...))
        self.assertEqual(res["miners"], 4975)
        self.assertEqual(res["height"], 3808993)
        self.assertIsNone(res["network_hashrate"])
        row = self.con.execute(
            "SELECT * FROM pool_stats WHERE id=?", (res["row_id"],)).fetchone()
        self.assertEqual(row["pool_name"], "MoneroOcean")
        self.assertEqual(row["block_reward_piconero"], 600_000_000_000)
        self.assertEqual(row["pool_fee_bps"], 0)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM pool_stats").fetchone()[0], 1)

    def test_poll_pool_stats_failure_streak(self):
        for i in (1, 2):
            res = ac.poll_pool_stats(self.con, opener=fake_opener_fail)
            self.assertFalse(res["ok"])
            self.assertEqual(res["consecutive_failures"], i)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM pool_stats").fetchone()[0], 0)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM decisions WHERE decision='pool-stats-unavailable'"
            ).fetchone()[0], 0)
        res = ac.poll_pool_stats(self.con, opener=fake_opener_fail)
        self.assertEqual(res["consecutive_failures"], 3)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM decisions WHERE decision='pool-stats-unavailable'"
            ).fetchone()[0], 1)
        # 4th failure: streak 4, no duplicate 'unavailable' row.
        ac.poll_pool_stats(self.con, opener=fake_opener_fail)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM decisions WHERE decision='pool-stats-unavailable'"
            ).fetchone()[0], 1)
        # A success resets the streak.
        ac.poll_pool_stats(self.con, opener=fake_opener_ok)
        ac.poll_pool_stats(self.con, opener=fake_opener_fail)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM decisions WHERE decision='pool-stats-unavailable'"
            ).fetchone()[0], 1, "streak reset: no new 'unavailable' at 1 failure")

    def test_record_pool_stats_direct(self):
        rid = ac.record_pool_stats(self.con, "MoneroOcean", 262107922, 4975, 3808993)
        row = self.con.execute("SELECT * FROM pool_stats WHERE id=?", (rid,)).fetchone()
        self.assertEqual(row["hashrate"], 262107922)
        self.assertIsNone(row["network_hashrate"])
        with self.assertRaises(ac.CoordinatorError):
            ac.record_pool_stats(self.con, "MoneroOcean", 1.5, 1, 1)

    # -- state / export / pass --------------------------------------------
    def test_status_and_export(self):
        w = ac.register_worker(self.con, self.user_id, "desktop", "st1")
        ac.record_shares(self.con, w["id"], [{
            "difficulty": 7, "accepted": 1, "origin": "pool",
            "external_id": "p1"}])
        st = ac.coordinator_status(self.con)
        self.assertEqual(st["workers"], {"total": 1, "active": 0, "registered": 1,
                                         "degraded": 0, "suspended": 0,
                                         "revoked": 0, "pending": 0})
        self.assertEqual(st["hashrate"]["status"], "not-measured")
        self.assertIsNone(st["hashrate"]["measured_hps"])
        self.assertFalse(st["pool_connected"])
        self.assertEqual(st["source_db_user_version"], 2)
        self.assertEqual(st["mode"], "simulation-only")
        path, payload = ac.export_coordinator_json(
            self.con, export_path="/tmp/atlas-m5-test-coordinator.json")
        on_disk = json.load(open(path))
        self.assertEqual(on_disk["workers"]["total"], 1)
        self.assertEqual(on_disk["shares"]["pool_accepted"], 1)
        # Second export: identical except exported_at.
        _, payload2 = ac.export_coordinator_json(
            self.con, export_path="/tmp/atlas-m5-test-coordinator.json")
        p1 = dict(payload); p2 = dict(payload2)
        p1.pop("exported_at"); p2.pop("exported_at")
        self.assertEqual(p1, p2)

    def test_run_pass(self):
        w = ac.register_worker(self.con, self.user_id, "desktop", "pass1")
        summary = ac.run_pass(db_path=self.db_path, force_poll=True,
                              opener=fake_opener_ok,
                              export_path="/tmp/atlas-m5-test-coordinator.json")
        self.assertTrue(summary["pool_poll"]["ok"])
        self.assertEqual(summary["activations_checked"], 1)
        self.assertEqual(summary["activations_activated"], 0)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM pool_stats").fetchone()[0], 1)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM decisions WHERE decision='coordinator-pass-complete'"
            ).fetchone()[0], 1)


def simulate():
    """End-to-end simulation on a FRESH temp DB: register -> record shares
    -> pool stats -> sessions -> decisions. Temp DB only."""
    print("\n=== SIMULATION (temp DB only: %s) ===" % SIM_DB)
    fresh_db(SIM_DB)
    con = ac.connect(SIM_DB)
    try:
        uid = make_user(con, "sim-user", "sim@example.invalid")
        d = ac.register_worker(con, uid, "desktop", "sim-rig1",
                               xmrig_version="6.26.0",
                               xmrig_sha256="verified-sha256-placeholder")
        b = ac.register_worker(con, uid, "browser", "sim-tab1")
        print(f"registered: desktop sim-rig1 id={d['id']} (token issued once, "
              f"len {len(d['token'])}), browser sim-tab1 id={b['id']} (no token)")
        # Local-test shares from the Mission 4 relay path.
        lt = [{"difficulty": 10000, "accepted": 1, "origin": "local-test",
               "external_id": f"local-test:sim-tab:1:{i}", "job_id": "lt-job-1"}
              for i in range(1, 6)]
        lt.append({"difficulty": 10000, "accepted": 0, "origin": "local-test",
                   "external_id": "local-test:sim-tab:1:6", "job_id": "lt-job-1"})
        print("local-test shares:", ac.record_shares(con, b["id"], lt))
        # Pool-path exercise (simulated accepted shares, temp DB only).
        print("pool shares:", ac.record_shares(con, d["id"], [
            {"difficulty": 5000, "accepted": 1, "origin": "pool",
             "external_id": "sim-pool-1", "job_id": "pool-job-9"},
            {"difficulty": 5000, "accepted": 1, "origin": "pool",
             "external_id": "sim-pool-2", "job_id": "pool-job-9"}]))
        print("attribution weights (pool-accepted only):",
              ac.attribution_weights(con))
        print("pool poll:", ac.poll_pool_stats(con, opener=fake_opener_ok))
        s1 = ac.record_worker_session(con, b["id"], "browser-probe",
                                      session_ref="sim-tab-session")
        s2 = ac.record_worker_session(con, d["id"], "desktop-agent",
                                      session_ref="sim-agent-1")
        print(f"sessions opened: browser-probe id={s1['session_id']}, "
              f"desktop-agent id={s2['session_id']}")
        print("activation check:", ac.verify_worker_active(con, d["id"]))
        print("sessions closed:",
              ac.close_worker_session(con, session_id=s1["session_id"]),
              ac.close_worker_session(con, session_id=s2["session_id"]))
        summary = ac.run_pass(db_path=SIM_DB, force_poll=False,
                              opener=fake_opener_ok, export_path=SIM_EXPORT)
        print("run_pass summary:", json.dumps(summary, indent=2))
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("users", "workers", "shares", "pool_stats", "sessions",
                            "ledger", "payouts", "referrals", "achievements")}
        print("temp-DB row counts:", counts)
        assert counts["ledger"] == 0 and counts["payouts"] == 0
        payload = json.load(open(SIM_EXPORT))
        print("coordinator.json hashrate:", payload["hashrate"])
        print("coordinator.json workers:", payload["workers"])
        print("coordinator.json shares:", payload["shares"])
        print("coordinator.json pool_stats_latest:",
              payload["pool_stats_latest"])
        print("coordinator decisions:",
              con.execute("SELECT COUNT(*) FROM decisions WHERE dept='coordinator'"
                          ).fetchone()[0])
    finally:
        con.close()
    print("=== SIMULATION DONE ===\n")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(CoordinatorTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    simulate()
    sys.exit(0 if result.wasSuccessful() else 1)
