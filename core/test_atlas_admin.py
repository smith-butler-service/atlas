#!/usr/bin/env python3
"""ATLAS Master Mission 8 — Lane C host admin module tests.

Runs ONLY against temp copies of atlas.db in /tmp. NEVER writes to the
real ~/workspace/atlas/data/atlas.db. The real DB is copied from the
PRE-MIGRATION backup (user_version 1), the Stage 1 migration is applied,
then the Stage 2 migration — all test/sim data lives in /tmp. (Same
fixture pattern as core/test_atlas_dashboard.py.)

Test plan (design §10):
  (a) zero-state derivation — every security count 0 with the verbatim
      empty states, queue + daemon-uptime UNAVAILABLE with the verbatim
      reasons; status + export write nothing to the DB (all table counts
      unchanged, decisions table unchanged — the module logs no decision).
  (b) non-zero fixture scenario — one suspended worker + one
      high-rejection worker; pool shares accepted/rejected incl. a
      duplicate external_id group; one failed payout + one reversal;
      decisions/events rows incl. one message containing a fake token
      string asserting redaction; metrics rows incl. one stale row —
      asserting every security count, the redaction, the queue
      UNAVAILABLE reason, the uptime UNAVAILABLE reason, and the
      earnings block identical to the dashboard export.
  (c) export idempotence + atomic write.
  (d) run_pass() admin sub-step on a temp DB — all exports written,
      exactly +1 decision per pass (coordinator-pass-complete), admin
      export fresh.
  (e) stale latest metrics row flags resources stale.

Usage: python3 core/test_atlas_admin.py [-v]
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
import atlas_admin as adm
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

QUEUE_REASON = ("No queue system exists — the coordinator runs "
                "synchronously in the 10-minute pass")
DAEMON_UPTIME_REASON = "Daemon start time is not recorded"
REDACTED = "[redacted — possible credential]"
NO_EVENTS = "No events recorded"


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


def table_count(con, table):
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


ALL_TABLES = ("users", "workers", "shares", "sessions", "ledger",
              "reward_batches", "payouts", "referrals", "decisions",
              "events", "metrics", "pool_stats")


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="atlas-m8-admin-")
        self.db_path = os.path.join(self.tmpdir, "test.db")
        fresh_db(self.db_path)
        self.con = ac.connect(self.db_path)
        self.export_path = os.path.join(self.tmpdir, "admin.json")

    def tearDown(self):
        self.con.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- (a) zero-state derivation --------------------------------------
    def test_a_zero_state(self):
        before = {t: table_count(self.con, t) for t in ALL_TABLES}
        payload = adm.admin_status(self.con, export_dir=self.tmpdir)
        # Status + export must write NOTHING to the DB (read-only
        # derivation); the module logs no decision of its own.
        path, exported = adm.export_admin_json(
            self.con, export_path=self.export_path)
        after = {t: table_count(self.con, t) for t in before}
        self.assertEqual(after, before, "admin derivation wrote to the DB")
        self.assertEqual(exported, payload)

        self.assertEqual(payload["source_db_user_version"], 4)
        self.assertEqual(payload["mode"], "simulation-only")
        self.assertTrue(payload["emergency_stop"])
        self.assertEqual(
            payload["scope"],
            "Admin view — aggregates and operational data only. "
            "No login exists yet — this section is not access-controlled.")
        # Network: zero users/workers/shares, hashrate not measured.
        self.assertEqual(payload["network"]["users"], 0)
        self.assertEqual(payload["network"]["workers"]["total"], 0)
        self.assertEqual(payload["network"]["worker_rows"], [])
        self.assertEqual(payload["network"]["hashrate"]["status"], "not-measured")
        self.assertIsNone(payload["network"]["hashrate"]["measured_hps"])
        self.assertEqual(payload["network"]["shares"], {
            "pool_accepted": 0, "pool_rejected": 0,
            "local_test_accepted": 0, "local_test_rejected": 0})
        # Daemon uptime UNAVAILABLE with the verbatim reason.
        self.assertEqual(payload["network"]["daemon_uptime"], {
            "value": None, "reason": DAEMON_UPTIME_REASON})
        # Monitoring uptime = metrics span from the fixture DB.
        span = self.con.execute(
            "SELECT MAX(ts) - MIN(ts) FROM metrics").fetchone()[0]
        self.assertEqual(payload["network"]["monitoring_uptime"]["seconds"], span)
        self.assertEqual(payload["network"]["monitoring_uptime"]["display"],
                         adm._fmt_duration(span))
        # Daemon restarts: all fixture events are kind 'startup'.
        self.assertEqual(payload["network"]["daemon_restarts_all_time"],
                         table_count(self.con, "events"))
        # Mining: earnings block reused from the dashboard (all zero).
        self.assertEqual(payload["mining"]["earnings"], {
            "estimated_piconero": None,
            "estimated_reason": "Cannot estimate — hashrate not measured",
            "confirmed_piconero": 0,
            "confirmed_note": "SIMULATION ONLY — no pool rewards",
            "mode": "simulation-only"})
        self.assertEqual(payload["mining"]["xmr_mined_piconero"], 0)
        self.assertEqual(payload["mining"]["pending_piconero"], 0)
        self.assertEqual(payload["mining"]["payouts_count"], 0)
        self.assertEqual(payload["mining"]["failed_payouts"], 0)
        # Infrastructure: queue lengths UNAVAILABLE, verbatim reason.
        self.assertEqual(payload["infrastructure"]["queues"], {
            "value": None, "reason": QUEUE_REASON})
        # DB health: integrity ok, all zero counts for the empty tables.
        self.assertEqual(payload["infrastructure"]["db_health"]["integrity_check"], "ok")
        self.assertEqual(payload["infrastructure"]["db_health"]["user_version"], 4)
        self.assertIsNone(payload["infrastructure"]["db_health"]["note"])
        for table in ("users", "workers", "shares", "sessions", "ledger",
                      "reward_batches", "payouts"):
            self.assertEqual(
                payload["infrastructure"]["db_health"]["table_counts"][table], 0)
        # Connectivity: never polled in the fixture DB.
        self.assertIsNone(payload["infrastructure"]["connectivity"]["pool_stats_latest"])
        self.assertEqual(
            payload["infrastructure"]["connectivity"]["pool_stats_note"],
            "Not polled yet")
        # Security: every count 0 with the verbatim empty state.
        sec = payload["security"]
        for key in ("suspicious_workers", "invalid_shares", "duplicate_shares",
                    "account_abuse", "auth_failures", "payout_anomalies"):
            self.assertEqual(sec[key]["count"], 0, f"{key} not 0")
            self.assertEqual(sec[key]["empty_state"], NO_EVENTS, key)
        self.assertEqual(sec["suspicious_workers"]["rows"], [])
        self.assertEqual(sec["duplicate_shares"]["rows"], [])
        self.assertEqual(sec["payout_anomalies"]["failed_payout_rows"], [])
        self.assertEqual(sec["payout_anomalies"]["reversal_rows"], [])
        self.assertEqual(sec["account_abuse"]["note"], "No abuse events recorded")
        self.assertEqual(sec["auth_failures"]["note"],
                         "No auth-failure events recorded")
        # Logs: latest-50 window over the fixture's decisions/events.
        self.assertEqual(payload["logs"]["decisions"]["total"],
                         table_count(self.con, "decisions"))
        self.assertEqual(payload["logs"]["events"]["total"],
                         table_count(self.con, "events"))
        self.assertEqual(len(payload["logs"]["decisions"]["rows"]), 50)
        self.assertEqual(len(payload["logs"]["events"]["rows"]), 44)
        self.assertEqual(
            payload["logs"]["decisions"]["window_note"],
            f"Showing latest 20 of 50 mirrored rows — "
            f"{table_count(self.con, 'decisions')} total on host")
        # No credential field anywhere in the exported file.
        with open(path) as f:
            raw = f.read()
        for forbidden in ("token_hash", "token_salt", "wallet",
                          "password", "seed", "private_key"):
            self.assertNotIn(forbidden, raw, f"{forbidden!r} leaked into admin.json")
        # No worker row carries a token field.
        self.assertNotIn("token", json.dumps(payload["network"]["worker_rows"]))
        # The exported file parses and matches the payload.
        with open(path) as f:
            on_disk = json.load(f)
        self.assertEqual(on_disk, payload)

    # -- (b) non-zero fixture scenario -----------------------------------
    def _build_scenario_b(self):
        now = int(time.time())
        alice = make_user(self.con, "alice")
        bob = make_user(self.con, "bob")
        wa_b = make_worker(self.con, alice, "browser", "alice-browser")
        wa_d = make_worker(self.con, alice, "desktop", "alice-desktop")
        wb_d = make_worker(self.con, bob, "desktop", "bob-desktop")
        # Suspended worker (bob's desktop).
        self.con.execute(
            "UPDATE workers SET status = 'suspended' WHERE id = ?", (wb_d,))
        # High-rejection worker (alice's desktop): 12 rejected / 4 accepted
        # pool shares -> rejected 12 >= 10 and 12/16 = 0.75 > 0.5.
        for i in range(12):
            self.con.execute(
                """INSERT INTO shares
                       (worker_id, difficulty, accepted, submitted_at, origin,
                        external_id, job_id)
                   VALUES (?,?,0,?,'pool',?,?)""",
                (wa_d, 1, W0 + 100 + i, f"pool:rej-{i}", None))
        for i in range(4):
            self.con.execute(
                """INSERT INTO shares
                       (worker_id, difficulty, accepted, submitted_at, origin,
                        external_id, job_id)
                   VALUES (?,?,1,?,'pool',?,?)""",
                (wa_d, 1, W0 + 200 + i, f"pool:acc-{i}", None))
        # Duplicate external_id group: 3 rows, 2 workers, 1 group -> 2 dups.
        for worker_id, at in ((wa_b, W0 + 300), (wb_d, W0 + 301), (wa_d, W0 + 302)):
            self.con.execute(
                """INSERT INTO shares
                       (worker_id, difficulty, accepted, submitted_at, origin,
                        external_id, job_id)
                   VALUES (?,?,1,?,'pool','pool:dup-001',?)""",
                (worker_id, 1, at, None))
        # Duplicate null-external_id group: same worker + job_id, 2 rows -> 1 dup.
        for at in (W0 + 400, W0 + 401):
            self.con.execute(
                """INSERT INTO shares
                       (worker_id, difficulty, accepted, submitted_at, origin,
                        external_id, job_id)
                   VALUES (?,?,1,?,'pool',NULL,'job-7')""",
                (wa_b, 1, at))
        # One failed payout + one ledger reversal.
        self.con.execute(
            """INSERT INTO payouts
                   (user_id, amount_piconero, destination_address, status,
                    created_at)
               VALUES (?,?, 'XMR-test-destination', 'failed', ?)""",
            (alice, 500_000_000_000, now))
        self.con.execute(
            """INSERT INTO ledger
                   (entry_type, user_id, amount_piconero, reference,
                    created_at, batch_id, prev_hash, entry_hash, mode, note)
               VALUES ('reversal', ?, -100000000000, 'reversal-of:1', ?,
                       NULL, NULL, NULL, 'simulation', 'test reversal')""",
            (alice, now))
        # One open (unsettled) 1 XMR sim batch -> pending gross 1 XMR.
        batch_id = rw.record_batch(
            self.con, "MoneroOcean", "simulation", "sim-20261118-002",
            W0, W1, ONE_XMR, source_evidence="simulated-harness:scenario-b",
            batch_ref="sim-20261118-002")
        self.assertIsNotNone(batch_id)
        # Decisions/events rows, incl. credential-bearing messages.
        self.con.execute(
            "INSERT INTO decisions (ts, dept, decision, reason) "
            "VALUES (?,?,?,?)",
            (now, "coordinator", "worker-token-rotated",
             "rotated token for worker alice-desktop: "
             "abcdef1234567890abcdef1234567890"))
        self.con.execute(
            "INSERT INTO decisions (ts, dept, decision, reason) "
            "VALUES (?,?,?,?)",
            (now, "coordinator", "share-batch-recorded",
             "share pool:dup-001 recorded for worker alice-browser"))
        self.con.execute(
            "INSERT INTO events (ts, kind, message) VALUES (?,?,?)",
            (now, "note",
             "suspicious blob 0123456789abcdef0123456789abcdef01234567 seen"))
        self.con.execute(
            "INSERT INTO events (ts, kind, message) VALUES (?,?,?)",
            (now, "abuse", "reported abusive worker behaviour"))
        for i in range(2):
            self.con.execute(
                "INSERT INTO events (ts, kind, message) VALUES (?,?,?)",
                (now, "auth_failure", f"login failed attempt {i}"))
        self.con.execute(
            "INSERT INTO events (ts, kind, message) VALUES (?,?,?)",
            (now, "startup", "atlas_monitor started"))
        # Metrics: one stale row + one fresh row (fresh latest -> not stale).
        self.con.execute("DELETE FROM metrics")
        self.con.execute(
            "INSERT INTO metrics (ts, cpu, mem_used_pct, load1, load5, "
            "load15, disk_used_pct, net_rx_bytes, net_tx_bytes) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (now - 90000, 10.0, 50.0, 0.5, 0.6, 0.7, 10.0, 100, 200))
        self.con.execute(
            "INSERT INTO metrics (ts, cpu, mem_used_pct, load1, load5, "
            "load15, disk_used_pct, net_rx_bytes, net_tx_bytes) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (now - 30, 42.5, 55.0, 1.0, 1.5, 2.0, 20.0, 1000, 2000))
        self.con.commit()
        return {"alice": alice, "bob": bob, "wa_b": wa_b, "wa_d": wa_d,
                "wb_d": wb_d, "now": now}

    def test_b_nonzero_scenario(self):
        ids = self._build_scenario_b()
        now = ids["now"]
        payload = adm.admin_status(self.con, export_dir=self.tmpdir)

        # Network counts.
        self.assertEqual(payload["network"]["users"], 2)
        self.assertEqual(payload["network"]["workers"]["total"], 3)
        self.assertEqual(payload["network"]["workers"]["suspended"], 1)
        self.assertEqual(payload["network"]["shares"], {
            "pool_accepted": 9, "pool_rejected": 12,
            "local_test_accepted": 0, "local_test_rejected": 0})
        # Daemon uptime still UNAVAILABLE, verbatim.
        self.assertEqual(payload["network"]["daemon_uptime"], {
            "value": None, "reason": DAEMON_UPTIME_REASON})
        # Monitoring uptime = the two controlled metrics rows' span.
        self.assertEqual(payload["network"]["monitoring_uptime"]["seconds"], 89970)
        # Queue lengths still UNAVAILABLE, verbatim.
        self.assertEqual(payload["infrastructure"]["queues"], {
            "value": None, "reason": QUEUE_REASON})
        # Latest metrics row is fresh (30 s old) and below the memory cap.
        res = payload["infrastructure"]["resources"]
        self.assertFalse(res["stale"])
        self.assertEqual(res["cpu"], 42.5)
        self.assertEqual(res["mem_used_pct"], 55.0)
        self.assertIsNone(res["memory_note"])
        self.assertEqual(res["latest_ts"], now - 30)

        # Security: every count, per the binding definitions.
        sec = payload["security"]
        # Suspicious: 1 suspended + 1 high-rejection = 2.
        self.assertEqual(sec["suspicious_workers"]["count"], 2)
        susp_ids = {r["id"] for r in sec["suspicious_workers"]["rows"]}
        self.assertEqual(susp_ids, {ids["wa_d"], ids["wb_d"]})
        for row in sec["suspicious_workers"]["rows"]:
            self.assertEqual(set(row),
                             {"id", "worker_type", "status",
                              "registered_at", "last_seen_at"})
        # Invalid: pool rejected = 12 (local-test excluded by definition).
        self.assertEqual(sec["invalid_shares"]["count"], 12)
        # Duplicates: 2 (external_id group) + 1 (null external_id group) = 3.
        self.assertEqual(sec["duplicate_shares"]["count"], 3)
        self.assertEqual(len(sec["duplicate_shares"]["rows"]), 3)
        dup_ext = [r for r in sec["duplicate_shares"]["rows"]
                   if r["external_id"] == "pool:dup-001"]
        self.assertEqual(len(dup_ext), 2)
        dup_job = [r for r in sec["duplicate_shares"]["rows"]
                   if r["job_id"] == "job-7"]
        self.assertEqual(len(dup_job), 1)
        # Abuse: 1; auth failures: 2.
        self.assertEqual(sec["account_abuse"]["count"], 1)
        self.assertIsNone(sec["account_abuse"]["note"])
        self.assertEqual(sec["auth_failures"]["count"], 2)
        self.assertIsNone(sec["auth_failures"]["note"])
        # Payout anomalies: 1 failed payout + 1 reversal = 2.
        self.assertEqual(sec["payout_anomalies"]["count"], 2)
        self.assertEqual(len(sec["payout_anomalies"]["failed_payout_rows"]), 1)
        self.assertEqual(sec["payout_anomalies"]["failed_payout_rows"][0]["status"],
                         "failed")
        self.assertEqual(sec["payout_anomalies"]["failed_payout_rows"][0]["amount_piconero"],
                         500_000_000_000)
        self.assertEqual(len(sec["payout_anomalies"]["reversal_rows"]), 1)
        self.assertEqual(sec["payout_anomalies"]["reversal_rows"][0]["reference"],
                         "reversal-of:1")
        # No empty states on non-zero counts.
        for key in sec:
            self.assertIsNone(sec[key]["empty_state"], key)

        # Mining: pending = open batch gross; confirmed still 0.
        self.assertEqual(payload["mining"]["pending_piconero"], ONE_XMR)
        self.assertEqual(payload["mining"]["confirmed_piconero"], 0)
        self.assertEqual(payload["mining"]["batches"]["open"], 1)
        self.assertEqual(payload["mining"]["failed_payouts"], 1)
        self.assertEqual(payload["mining"]["payouts_count"], 1)

        # Redaction (§1.2): the token-bearing decision reason and the
        # long-hex event message are replaced; the known-external_id
        # decision reason and ordinary rows are shown as-is.
        decisions = {r["decision"]: r["reason"]
                     for r in payload["logs"]["decisions"]["rows"]}
        self.assertEqual(decisions["worker-token-rotated"], REDACTED)
        self.assertEqual(decisions["share-batch-recorded"],
                         "share pool:dup-001 recorded for worker alice-browser")
        events = payload["logs"]["events"]["rows"]
        blob = [r for r in events if r["kind"] == "note"]
        self.assertEqual(len(blob), 1)
        self.assertEqual(blob[0]["message"], REDACTED)
        abuse = [r for r in events if r["kind"] == "abuse"]
        self.assertEqual(len(abuse), 1)
        self.assertEqual(abuse[0]["message"], "reported abusive worker behaviour")
        # Log totals include the fixture rows.
        self.assertEqual(payload["logs"]["decisions"]["total"],
                         table_count(self.con, "decisions"))
        self.assertEqual(payload["logs"]["events"]["total"],
                         table_count(self.con, "events"))

        # Earnings block identical to a fresh dashboard export.
        _, dash_payload = db.export_dashboard_json(
            self.con, export_path=os.path.join(self.tmpdir, "dashboard.json"))
        self.assertEqual(payload["mining"]["earnings"], dash_payload["earnings"])
        # The dashboard export landed in the same temp dir, so the admin
        # sync block now sees it; re-derive to compare earnings exactly.
        payload2 = adm.admin_status(self.con, export_dir=self.tmpdir)
        self.assertEqual(payload2["mining"]["earnings"], dash_payload["earnings"])
        self.assertEqual(payload2["mining"]["host_verified_totals"],
                         dash_payload["host_verified_totals"])

    # -- (c) export idempotence + atomic write ---------------------------
    def test_c_export_idempotence_atomic(self):
        _, payload1 = adm.export_admin_json(
            self.con, export_path=self.export_path)
        self.assertTrue(os.path.exists(self.export_path))
        self.assertFalse(os.path.exists(self.export_path + ".tmp"),
                         "atomic-write temp file left behind")
        with open(self.export_path) as f:
            on_disk1 = json.load(f)
        self.assertEqual(on_disk1, payload1)
        _, payload2 = adm.export_admin_json(
            self.con, export_path=self.export_path)
        self.assertFalse(os.path.exists(self.export_path + ".tmp"))
        with open(self.export_path) as f:
            on_disk2 = json.load(f)
        self.assertEqual(on_disk2, payload2)

        def _stable(payload):
            stable = dict(payload)
            stable.pop("exported_at", None)
            stable["sync"] = {k: v for k, v in payload["sync"].items()
                              if k != "admin_exported_at"}
            return stable

        self.assertEqual(_stable(payload1), _stable(payload2))
        self.assertIsInstance(payload1["exported_at"], int)
        self.assertIsInstance(payload2["exported_at"], int)

    # -- (d) run_pass admin sub-step --------------------------------------
    def test_d_run_pass_admin_substep(self):
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
        # admin sub-step logs none of its own.
        self.assertEqual(table_count(self.con, "decisions"), before + 1)
        self.assertEqual(
            self.con.execute(
                "SELECT decision FROM decisions ORDER BY id DESC LIMIT 1"
            ).fetchone()[0], "coordinator-pass-complete")
        # All four exports landed in the temp dir, none in the live dir.
        for name in ("coordinator.json", "rewards.json", "dashboard.json",
                     "admin.json"):
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, name)),
                            f"{name} missing after run_pass")
        with open(os.path.join(self.tmpdir, "admin.json")) as f:
            admin = json.load(f)
        age = int(time.time()) - admin["exported_at"]
        self.assertLess(age, 600, f"admin.json exported_at {age}s old")
        self.assertEqual(admin["network"]["users"], 0)
        self.assertEqual(admin["security"]["suspicious_workers"]["count"], 0)
        self.assertEqual(admin["infrastructure"]["queues"]["reason"], QUEUE_REASON)
        self.assertEqual(admin["network"]["daemon_uptime"]["reason"],
                         DAEMON_UPTIME_REASON)
        with open(os.path.join(self.tmpdir, "dashboard.json")) as f:
            dash = json.load(f)
        self.assertEqual(admin["mining"]["earnings"], dash["earnings"])
        # NOTE: the temp dir has no diagnostics.json, so sync.stale is
        # True by design (a missing source export is stale). The fresh
        # check that matters here is exported_at above.
        self.assertTrue(admin["sync"]["stale"])
        self.assertIsNone(admin["sync"]["diagnostics_exported_at"])

    # -- (e) stale latest metrics row --------------------------------------
    def test_e_stale_metrics_row(self):
        now = int(time.time())
        self.con.execute("DELETE FROM metrics")
        self.con.execute(
            "INSERT INTO metrics (ts, cpu, mem_used_pct, load1, load5, "
            "load15, disk_used_pct, net_rx_bytes, net_tx_bytes) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (now - 3600, 80.0, 85.0, 3.0, 2.0, 1.0, 25.0, 500, 600))
        self.con.commit()
        payload = adm.admin_status(self.con, export_dir=self.tmpdir)
        res = payload["infrastructure"]["resources"]
        self.assertTrue(res["stale"])
        self.assertEqual(res["latest_ts"], now - 3600)
        self.assertEqual(res["memory_note"], "Above the 70% cap")


if __name__ == "__main__":
    unittest.main(verbosity=2)
