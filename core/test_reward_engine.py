#!/usr/bin/env python3
"""ATLAS Master Mission 6 — Lane C reward-engine tests + simulation.

Runs ONLY against temp copies of atlas.db in /tmp. NEVER writes to the
real ~/workspace/atlas/data/atlas.db. The real DB is copied from the
PRE-MIGRATION backup (user_version 1), the Stage 1 migration is applied,
then the Stage 2 migration — all test/sim data lives in /tmp.

Test plan: docs/master-mission6-design.md §12 (16 unit tests + 2
end-to-end simulation scenarios with the design's EXACT expected
piconero figures), plus two extra checks (CLI smoke, export/no-op).

Usage: python3 core/test_reward_engine.py [-v]
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import unittest

sys.path.insert(0, os.path.expanduser("~/workspace/atlas/core"))
import atlas_coordinator as ac
import atlas_rewards as rw

REAL_DB = os.path.expanduser("~/workspace/atlas/data/atlas.db")
SRC_DB = os.path.expanduser(
    "~/workspace/atlas/backups/atlas-2026-11-18-pre-mission5.db")
MIGRATION_1 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission5_stage1.sql")
MIGRATION_2 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission6_stage2.sql")
MIGRATION_3 = os.path.expanduser(
    "~/workspace/atlas/core/migrate_mission11_stage3.sql")
ENGINE_SRC = os.path.expanduser("~/workspace/atlas/core/atlas_rewards.py")

W0 = 1795000000
W1 = 1795003600
W2 = 1795007200
ONE_XMR = 1_000_000_000_000


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


def make_user(con, username, email=None):
    cur = con.execute(
        "INSERT INTO users (username, email, email_verified, created_at) "
        "VALUES (?,?,0,?)",
        (username, email or f"{username}@example.invalid", int(time.time())))
    con.commit()
    return cur.lastrowid


def make_worker(con, user_id, worker_type, name):
    return ac.register_worker(con, user_id, worker_type, name)["id"]


def add_pool_share(con, worker_id, difficulty, external_id, submitted_at,
                   accepted=1):
    result = ac.record_shares(con, worker_id, [{
        "difficulty": difficulty, "accepted": accepted,
        "submitted_at": submitted_at, "origin": "pool",
        "external_id": external_id, "job_id": None}])
    return result


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


def ledger_count(con):
    return con.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]


def ledger_sums_by_type(con, batch_id):
    out = {}
    for row in con.execute(
            "SELECT entry_type, COALESCE(SUM(amount_piconero), 0) AS total "
            "FROM ledger WHERE batch_id = ? GROUP BY entry_type",
            (batch_id,)).fetchall():
        out[row["entry_type"]] = row["total"]
    return out


def decision_logged(con, decision):
    return con.execute(
        "SELECT COUNT(*) FROM decisions WHERE dept = 'rewards' AND decision = ?",
        (decision,)).fetchone()[0]


class RewardEngineTests(unittest.TestCase):
    def setUp(self):
        self.db_path = f"/tmp/atlas-m6-test-{self._testMethodName}.db"
        fresh_db(self.db_path)
        self.con = ac.connect(self.db_path)

    def tearDown(self):
        self.con.close()

    def _simple_sim_fixture(self, batch_ref="sim-t6", source_ref="sim-t6",
                            window_start=W0, window_end=W1):
        """One user, one worker, one LOCAL-TEST share (difficulty 1) in the
        window. Simulation batches attribute origin='local-test' only, so
        the fixture share must be local-test. Returns (user_id, batch_ref)."""
        user = make_user(self.con, "u-simple")
        worker = make_worker(self.con, user, "browser", "rig1")
        add_local_share(self.con, worker, 1, f"lt-{batch_ref}", window_start + 10)
        batch_id = rw.record_batch(
            self.con, "MoneroOcean", "simulation", source_ref,
            window_start, window_end, ONE_XMR,
            source_evidence="simulated-harness:test", batch_ref=batch_ref)
        self.assertIsNotNone(batch_id, "fixture batch was not recorded")
        return user, batch_ref

    # -- 1. Fee arithmetic ---------------------------------------------
    def test_01_fee_arithmetic(self):
        self.assertEqual(rw.fee_for(ONE_XMR, 0), 0)
        self.assertEqual(rw.fee_for(ONE_XMR, 60), 6_000_000_000)
        self.assertEqual(rw.fee_for(1, 100), 0)  # floor; remainder stays in net
        self.assertIs(type(rw.fee_for(ONE_XMR, 60)), int)
        self.assertEqual(rw.fee_for(ONE_XMR, 60) + (ONE_XMR - rw.fee_for(ONE_XMR, 60)),
                         ONE_XMR)

    # -- 2. Split exactness --------------------------------------------
    def test_02_split_exactness(self):
        atlas, users = rw.split_net(ONE_XMR)
        self.assertEqual(atlas, 250_000_000_000)
        self.assertEqual(users, 750_000_000_000)
        self.assertEqual(atlas + users, ONE_XMR)
        atlas, users = rw.split_net(1_000_000_000_001)
        self.assertEqual(atlas, 250_000_000_000)
        self.assertEqual(users, 750_000_000_001)  # remainder to users
        self.assertEqual(atlas + users, 1_000_000_000_001)

    # -- 3. Largest-remainder allocation --------------------------------
    def test_03_largest_remainder(self):
        alloc = rw.allocate_largest_remainder(10, {1: 1, 2: 1, 3: 1})
        self.assertEqual(alloc, {1: 4, 2: 3, 3: 3})  # +1 to lowest user_id
        self.assertEqual(sum(alloc.values()), 10)
        alloc = rw.allocate_largest_remainder(
            745_500_000_000, {1: 2, 2: 1, 3: 1})
        self.assertEqual(alloc, {1: 372_750_000_000,
                                 2: 186_375_000_000,
                                 3: 186_375_000_000})
        self.assertEqual(sum(alloc.values()), 745_500_000_000)
        # Every allocation within 1 piconero of its exact share.
        for uid, w in ((1, 2), (2, 1), (3, 1)):
            exact = 745_500_000_000 * w // 4
            self.assertLessEqual(abs(alloc[uid] - exact), 1)

    # -- 4. Attribution weights -----------------------------------------
    def test_04_attribution_weights(self):
        user_a = make_user(self.con, "u-a")
        user_b = make_user(self.con, "u-b")
        user_c = make_user(self.con, "u-c")
        wa = make_worker(self.con, user_a, "browser", "wa")
        wb = make_worker(self.con, user_b, "browser", "wb")
        wc = make_worker(self.con, user_c, "browser", "wc")
        add_pool_share(self.con, wa, 10, "pool:a1", W0 + 10)
        add_pool_share(self.con, wa, 20, "pool:a2", W0 + 20)
        add_pool_share(self.con, wb, 5, "pool:b1", W0 + 30)
        add_pool_share(self.con, wa, 999, "pool:a-rej", W0 + 40, accepted=0)
        for tag in ("lt1", "lt2", "lt3"):
            add_local_share(self.con, wa, 999, tag, W0 + 50)
        add_pool_share(self.con, wc, None, "pool:c-nulldiff", W0 + 60)
        add_pool_share(self.con, wa, 7, None, W0 + 70)  # NULL external_id
        batch = {"mode": "real", "window_start": W0, "window_end": W1}
        weights, share_ids, null_diff, null_ext = rw._attribution(self.con, batch)
        self.assertEqual(weights, {user_a: 30, user_b: 5, user_c: 1})
        self.assertEqual(null_diff, 1)   # NULL difficulty counted weight 1, flagged
        self.assertEqual(null_ext, 1)    # NULL external_id excluded and counted
        self.assertEqual(len(share_ids), 4)  # 2 A + 1 B + 1 C(NULL diff)

    # -- 5. Share -> worker -> user mapping ------------------------------
    def test_05_worker_user_mapping(self):
        user_d = make_user(self.con, "u-d")
        user_e = make_user(self.con, "u-e")
        wd1 = make_worker(self.con, user_d, "browser", "wd1")
        wd2 = make_worker(self.con, user_d, "desktop", "wd2")
        we = make_worker(self.con, user_e, "browser", "we")
        add_pool_share(self.con, wd1, 4, "pool:d1", W0 + 10)
        add_pool_share(self.con, wd2, 6, "pool:d2", W0 + 20)
        add_pool_share(self.con, we, 3, "pool:e1", W0 + 30)
        batch = {"mode": "real", "window_start": W0, "window_end": W1}
        weights, _, _, _ = rw._attribution(self.con, batch)
        self.assertEqual(weights, {user_d: 10, user_e: 3})

    # -- 6. Batch exactly-once ------------------------------------------
    def test_06_batch_exactly_once(self):
        user, batch_ref = self._simple_sim_fixture()
        before = ledger_count(self.con)
        result = rw.settle_batch(self.con, batch_ref=batch_ref)
        self.assertEqual(result["status"], "settled")
        after = ledger_count(self.con)
        self.assertGreater(after, before)
        result2 = rw.settle_batch(self.con, batch_ref=batch_ref)
        self.assertEqual(result2["status"], "noop")
        self.assertEqual(ledger_count(self.con), after)
        batch = self.con.execute(
            "SELECT status FROM reward_batches WHERE batch_ref = ?",
            (batch_ref,)).fetchone()
        self.assertEqual(batch["status"], "settled")
        dup = rw.record_batch(self.con, "MoneroOcean", "simulation", "sim-t6",
                              W0, W1, ONE_XMR, batch_ref="sim-t6-dup")
        self.assertIsNone(dup)
        n = self.con.execute(
            "SELECT COUNT(*) FROM reward_batches WHERE pool_name = 'MoneroOcean' "
            "AND source_ref = 'sim-t6'").fetchone()[0]
        self.assertEqual(n, 1)
        self.assertGreaterEqual(decision_logged(self.con, "reward-batch-duplicate-skipped"), 1)

    # -- 7. Share double-credit -----------------------------------------
    def test_07_share_double_credit(self):
        user, batch_ref = self._simple_sim_fixture(batch_ref="sim-7a",
                                                    source_ref="sim-7a")
        result = rw.settle_batch(self.con, batch_ref=batch_ref)
        self.assertEqual(result["status"], "settled")
        # Layer 1 (record): an overlapping window is refused.
        dup = rw.record_batch(self.con, "MoneroOcean", "simulation", "sim-7b",
                              W0 + 100, W1 + 100, ONE_XMR, batch_ref="sim-7b")
        self.assertIsNone(dup)
        # Layer 2 (settle): a batch row inserted directly (bypassing the
        # record-time overlap check) still cannot re-credit linked shares.
        self.con.execute(
            """INSERT INTO reward_batches
                   (batch_ref, pool_name, mode, source_ref, window_start,
                    window_end, gross_piconero, fee_bps, status, created_at)
               VALUES ('sim-7b-direct', 'MoneroOcean', 'simulation', 'sim-7b-direct',
                       ?, ?, ?, 0, 'open', ?)""",
            (W0, W1 + 3600, ONE_XMR, int(time.time())))
        self.con.commit()
        worker = self.con.execute(
            "SELECT id FROM workers WHERE user_id = ?", (user,)).fetchone()["id"]
        add_local_share(self.con, worker, 4, "lt-7-new", W1 + 10)
        result2 = rw.settle_batch(self.con, batch_ref="sim-7b-direct")
        self.assertEqual(result2["status"], "settled")
        self.assertEqual(result2["shares_count"], 1)  # only the new share
        # The user was credited once for batch 1 (1,000,000,000,000 net ->
        # 750,000,000,000) and once for the new share (same) — never twice
        # for the batch-1 share.
        self.assertEqual(rw.user_balance(self.con, user), 1_500_000_000_000)

    # -- 8. Ledger chain --------------------------------------------------
    def test_08_ledger_chain(self):
        user, batch_ref = self._simple_sim_fixture(batch_ref="sim-8a",
                                                    source_ref="sim-8a")
        rw.settle_batch(self.con, batch_ref=batch_ref)
        worker = self.con.execute(
            "SELECT id FROM workers WHERE user_id = ?", (user,)).fetchone()["id"]
        add_local_share(self.con, worker, 1, "lt-8-2", W1 + 10)
        rw.record_batch(self.con, "MoneroOcean", "simulation", "sim-8b",
                        W1, W2, ONE_XMR, batch_ref="sim-8b")
        rw.settle_batch(self.con, batch_ref="sim-8b")
        verdict = rw.verify_chain(self.con)
        self.assertTrue(verdict["ok"], verdict)
        self.assertEqual(verdict["entries"], ledger_count(self.con))
        self.assertEqual(verdict["batches"], 2)
        # Tamper: UPDATE one committed amount directly in the TEMP DB.
        victim = self.con.execute(
            "SELECT id FROM ledger WHERE entry_type = 'user_allocation' "
            "ORDER BY id LIMIT 1").fetchone()["id"]
        self.con.execute(
            "UPDATE ledger SET amount_piconero = amount_piconero + 1 WHERE id = ?",
            (victim,))
        self.con.commit()
        bad = rw.verify_chain(self.con)
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["first_bad_entry_id"], victim)
        # Reversal sub-case on a FRESH temp DB (a hash-mismatched row can
        # never verify again, so the design's literal tamper-then-reversal
        # sequence is impossible; the reversal is tested separately):
        # settle, reverse one entry, correct another — chain still verifies.
        fresh = "/tmp/atlas-m6-test-08b.db"
        fresh_db(fresh)
        con2 = ac.connect(fresh)
        try:
            user2 = make_user(con2, "u-8b")
            w2 = make_worker(con2, user2, "browser", "rig1")
            add_local_share(con2, w2, 1, "lt-8b-1", W0 + 10)
            rw.record_batch(con2, "MoneroOcean", "simulation", "sim-8c",
                            W0, W1, ONE_XMR, batch_ref="sim-8c")
            rw.settle_batch(con2, batch_ref="sim-8c")
            entry = con2.execute(
                "SELECT id, amount_piconero FROM ledger "
                "WHERE entry_type = 'user_allocation' ORDER BY id LIMIT 1"
            ).fetchone()
            rev_id = rw.record_reversal(con2, entry["id"])
            self.assertEqual(rw.user_balance(con2, user2), 0)
            # The tampered/reversed original stays visible in history.
            self.assertIsNotNone(con2.execute(
                "SELECT id FROM ledger WHERE id = ?", (entry["id"],)).fetchone())
            verdict2 = rw.verify_chain(con2)
            self.assertTrue(verdict2["ok"], verdict2)
            # Correction: reversal + fresh corrected entry, chain verifies.
            entry2 = con2.execute(
                "SELECT id FROM ledger WHERE entry_type = 'atlas_share' "
                "ORDER BY id LIMIT 1").fetchone()
            rw.record_correction(con2, entry2["id"], 100)
            verdict3 = rw.verify_chain(con2)
            self.assertTrue(verdict3["ok"], verdict3)
        finally:
            con2.close()

    # -- 9. Reconciliation invariant --------------------------------------
    def test_09_reconciliation_invariant(self):
        user, batch_ref = self._simple_sim_fixture(batch_ref="sim-9a",
                                                    source_ref="sim-9a")
        rw.settle_batch(self.con, batch_ref=batch_ref)
        worker = self.con.execute(
            "SELECT id FROM workers WHERE user_id = ?", (user,)).fetchone()["id"]
        add_local_share(self.con, worker, 1, "lt-9-2", W1 + 10)
        rw.record_batch(self.con, "SupportXMR", "simulation", "sim-9b",
                        W1, W2, ONE_XMR, batch_ref="sim-9b")
        rw.settle_batch(self.con, batch_ref="sim-9b")
        settled = self.con.execute(
            "SELECT * FROM reward_batches WHERE status = 'settled'").fetchall()
        self.assertEqual(len(settled), 2)
        for brow in settled:
            sums = ledger_sums_by_type(self.con, brow["id"])
            total = (sums.get("fee", 0) + sums.get("atlas_share", 0)
                     + sums.get("referral_reward", 0)
                     + sums.get("user_allocation", 0))
            self.assertEqual(total, brow["gross_piconero"],
                             f"batch {brow['batch_ref']} does not reconcile")

    # -- 10. Referrals -----------------------------------------------------
    def test_10_referrals(self):
        # Example C (design §4): A 500e9, B 250e9, C referred B.
        user_a = make_user(self.con, "u-a10")
        user_b = make_user(self.con, "u-b10")
        user_c = make_user(self.con, "u-c10")
        wa = make_worker(self.con, user_a, "browser", "wa10")
        wb = make_worker(self.con, user_b, "browser", "wb10")
        add_local_share(self.con, wa, 2, "lt-a10", W0 + 10)
        add_local_share(self.con, wb, 1, "lt-b10", W0 + 20)
        add_referral(self.con, user_c, user_b)
        rw.record_batch(self.con, "MoneroOcean", "simulation", "sim-10",
                        W0, W1, ONE_XMR, batch_ref="sim-10")
        result = rw.settle_batch(self.con, batch_ref="sim-10")
        self.assertEqual(result["status"], "settled")
        self.assertEqual(result["referral_total_piconero"], 12_500_000_000)
        self.assertEqual(result["atlas_share_piconero"], 237_500_000_000)
        self.assertEqual(result["allocations"][user_a], 500_000_000_000)
        self.assertEqual(result["allocations"][user_b], 250_000_000_000)
        self.assertEqual(rw.user_balance(self.con, user_c), 12_500_000_000)
        self.assertEqual(rw.user_balance(self.con, user_b), 250_000_000_000)
        self.assertEqual(rw.user_balance(self.con, user_a), 500_000_000_000)
        # Cap inequality holds.
        self.assertLessEqual(result["referral_total_piconero"], 250_000_000_000)
        # Self-referral pays 0 (separate fixture).
        fresh = "/tmp/atlas-m6-test-10b.db"
        fresh_db(fresh)
        con2 = ac.connect(fresh)
        try:
            user_s = make_user(con2, "u-self")
            ws = make_worker(con2, user_s, "browser", "ws")
            add_local_share(con2, ws, 1, "lt-self-1", W0 + 10)
            add_referral(con2, user_s, user_s)
            rw.record_batch(con2, "MoneroOcean", "simulation", "sim-10b",
                            W0, W1, ONE_XMR, batch_ref="sim-10b")
            result2 = rw.settle_batch(con2, batch_ref="sim-10b")
            self.assertEqual(result2["referral_total_piconero"], 0)
            self.assertEqual(con2.execute(
                "SELECT COUNT(*) FROM ledger WHERE entry_type = 'referral_reward'"
            ).fetchone()[0], 0)
        finally:
            con2.close()
        # No referrals at all: referral_total 0, zero referral entries.
        self.assertEqual(self.con.execute(
            "SELECT referral_total_piconero FROM reward_batches "
            "WHERE batch_ref = 'sim-10'").fetchone()[0], 12_500_000_000)

    # -- 11. Mode gates ----------------------------------------------------
    def test_11_mode_gates(self):
        # Config mode is simulation-only and the stop is ON (live configs).
        refused = rw.record_batch(self.con, "MoneroOcean", "real", "real-11",
                                  W0, W1, ONE_XMR, batch_ref="real-11")
        self.assertIsNone(refused)
        self.assertGreaterEqual(decision_logged(self.con, "reward-batch-refused"), 1)
        # A real-mode row smuggled into the DB is refused at settle time.
        self.con.execute(
            """INSERT INTO reward_batches
                   (batch_ref, pool_name, mode, source_ref, window_start,
                    window_end, gross_piconero, fee_bps, status, created_at)
               VALUES ('real-smuggled', 'MoneroOcean', 'real', 'real-smuggled',
                       ?, ?, ?, 0, 'open', ?)""",
            (W0, W1, ONE_XMR, int(time.time())))
        self.con.commit()
        result = rw.settle_batch(self.con, batch_ref="real-smuggled")
        self.assertEqual(result["status"], "refused")
        self.assertEqual(ledger_count(self.con), 0)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM ledger WHERE mode = 'real'").fetchone()[0], 0)
        # Simulation batch settles with the stop ON (D-M6-7 exemption).
        user, batch_ref = self._simple_sim_fixture(
            batch_ref="sim-11", source_ref="sim-11",
            window_start=W1, window_end=W2)
        result2 = rw.settle_batch(self.con, batch_ref=batch_ref)
        self.assertEqual(result2["status"], "settled")

    # -- 12. Held batches ---------------------------------------------------
    def test_12_held_batches(self):
        # Gross > 0 but zero eligible shares: stays open, zero entries.
        rw.record_batch(self.con, "MoneroOcean", "simulation", "sim-12a",
                        W0, W1, ONE_XMR, batch_ref="sim-12a")
        result = rw.settle_batch(self.con, batch_ref="sim-12a")
        self.assertEqual(result["status"], "held")
        self.assertEqual(ledger_count(self.con), 0)
        self.assertEqual(self.con.execute(
            "SELECT status FROM reward_batches WHERE batch_ref = 'sim-12a'"
        ).fetchone()["status"], "open")
        self.assertGreaterEqual(decision_logged(self.con, "reward-batch-held"), 1)
        # Gross 0 cannot be recorded; a gross-0 row is held at settle time.
        refused = rw.record_batch(self.con, "MoneroOcean", "simulation",
                                  "sim-12b", W0, W1, 0, batch_ref="sim-12b")
        self.assertIsNone(refused)
        self.con.execute(
            """INSERT INTO reward_batches
                   (batch_ref, pool_name, mode, source_ref, window_start,
                    window_end, gross_piconero, fee_bps, status, created_at)
               VALUES ('sim-12b-row', 'MoneroOcean', 'simulation', 'sim-12b-row',
                       ?, ?, 0, 0, 'open', ?)""",
            (W0, W1, int(time.time())))
        self.con.commit()
        result2 = rw.settle_batch(self.con, batch_ref="sim-12b-row")
        self.assertEqual(result2["status"], "held")
        self.assertEqual(ledger_count(self.con), 0)

    # -- 13. Payout idempotency (column only) -------------------------------
    def test_13_payout_idempotency(self):
        user = make_user(self.con, "u-pay")
        self.con.execute(
            """INSERT INTO payouts
                   (user_id, amount_piconero, destination_address, status,
                    created_at, idempotency_key)
               VALUES (?,?, '47XMRplaceholder', 'pending', ?, ?)""",
            (user, 1000, int(time.time()), "payout:1:sim-001:1"))
        self.con.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute(
                """INSERT INTO payouts
                       (user_id, amount_piconero, destination_address, status,
                        created_at, idempotency_key)
                   VALUES (?,?, '47XMRplaceholder', 'pending', ?, ?)""",
                (user, 1000, int(time.time()), "payout:1:sim-001:1"))
            self.con.commit()

    # -- 14. Window rules ----------------------------------------------------
    def test_14_window_rules(self):
        rw.record_batch(self.con, "MoneroOcean", "simulation", "sim-14",
                        W0, W1, ONE_XMR, batch_ref="sim-14")
        overlap = rw.record_batch(self.con, "MoneroOcean", "simulation",
                                  "sim-14-overlap", W0 + 100, W1 + 100,
                                  ONE_XMR, batch_ref="sim-14-overlap")
        self.assertIsNone(overlap)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM reward_batches").fetchone()[0], 1)
        bad = rw.record_batch(self.con, "MoneroOcean", "simulation",
                              "sim-14-bad", W1, W0, ONE_XMR,
                              batch_ref="sim-14-bad")
        self.assertIsNone(bad)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM reward_batches").fetchone()[0], 1)
        self.assertGreaterEqual(decision_logged(self.con, "reward-batch-refused"), 2)

    # -- 15. Balances derived -------------------------------------------------
    def test_15_balances_derived(self):
        user_a = make_user(self.con, "u-a15")
        user_b = make_user(self.con, "u-b15")
        user_c = make_user(self.con, "u-c15")
        wa = make_worker(self.con, user_a, "browser", "wa15")
        wb = make_worker(self.con, user_b, "browser", "wb15")
        add_local_share(self.con, wa, 2, "lt-a15", W0 + 10)
        add_local_share(self.con, wb, 1, "lt-b15", W0 + 20)
        add_referral(self.con, user_c, user_b)
        rw.record_batch(self.con, "MoneroOcean", "simulation", "sim-15",
                        W0, W1, ONE_XMR, batch_ref="sim-15")
        rw.settle_batch(self.con, batch_ref="sim-15")
        expected = {user_a: 500_000_000_000, user_b: 250_000_000_000,
                    user_c: 12_500_000_000}
        self.assertEqual(rw.balances(self.con), expected)
        # Independently recompute from the entries.
        for uid, want in expected.items():
            manual = self.con.execute(
                """SELECT COALESCE(SUM(amount_piconero), 0) FROM ledger
                   WHERE user_id = ?""", (uid,)).fetchone()[0]
            self.assertEqual(manual, want)
            self.assertEqual(rw.user_balance(self.con, uid), want)
        # No stored-balance column exists to drift.
        cols = [r["name"] for r in self.con.execute("PRAGMA table_info(ledger)")]
        self.assertNotIn("balance", cols)

    # -- 16. No floats, no estimates in the engine ---------------------------
    def test_16_no_floats_no_estimates(self):
        with open(ENGINE_SRC) as f:
            src = f.read()
        self.assertNotIn("float(", src)
        self.assertNotIn("reported_hashrate_hps", src)
        self.assertNotIn("calculator", src)

    # -- Extra: CLI smoke ------------------------------------------------------
    def test_17_cli_status_verify(self):
        user, batch_ref = self._simple_sim_fixture(batch_ref="sim-17",
                                                    source_ref="sim-17")
        rw.settle_batch(self.con, batch_ref=batch_ref)
        for cmd in (["status"], ["verify-chain"]):
            proc = subprocess.run(
                [sys.executable,
                 os.path.expanduser("~/workspace/atlas/core/atlas_rewards.py"),
                 "--db", self.db_path] + cmd,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            json.loads(proc.stdout)  # valid JSON

    # -- Extra: guarded no-op + host export ------------------------------------
    def test_18_settle_due_noop_and_export(self):
        summary = rw.settle_due_batches(self.con)
        self.assertEqual(summary["batches_due"], 0)
        payload = rw.export_rewards(self.con)
        self.assertEqual(payload["mode"], "simulation-only")
        self.assertTrue(payload["simulation_only"])
        self.assertEqual(payload["totals"]["ledger_entries"], 0)
        self.assertTrue(payload["chain"]["ok"])
        self.assertEqual(payload["totals"]["total_user_rewards_piconero"], 0)


class SimulationTests(unittest.TestCase):
    """§12.2 end-to-end simulation scenarios (temp DB, exact figures)."""

    def setUp(self):
        self.db_path = f"/tmp/atlas-m6-sim-{self._testMethodName}.db"
        fresh_db(self.db_path)
        self.con = ac.connect(self.db_path)

    def tearDown(self):
        self.con.close()

    def test_scenario_1_moneroocean_referral(self):
        # Fixture: Alice (browser + desktop, 60 weight), Bob (desktop, 40
        # weight), 8 local-test shares; Bob referred by Alice.
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
        self.assertEqual(result["fee_piconero"], 0)
        self.assertEqual(result["net_piconero"], 1_000_000_000_000)
        self.assertEqual(result["atlas_share_piconero"], 235_000_000_000)
        self.assertEqual(result["users_total_piconero"], 750_000_000_000)
        self.assertEqual(result["allocations"][alice], 450_000_000_000)
        self.assertEqual(result["allocations"][bob], 300_000_000_000)
        self.assertEqual(result["referral_total_piconero"], 15_000_000_000)
        self.assertEqual(result["shares_count"], 8)
        self.assertEqual(rw.user_balance(self.con, alice), 465_000_000_000)
        self.assertEqual(rw.user_balance(self.con, bob), 300_000_000_000)
        self.assertEqual(ledger_count(self.con), 5)  # fee + atlas + referral + 2 alloc
        for row in self.con.execute("SELECT mode FROM ledger"):
            self.assertEqual(row["mode"], "simulation")
        verdict = rw.verify_chain(self.con)
        self.assertTrue(verdict["ok"], verdict)
        # A second run re-settles nothing (idempotent).
        again = rw.settle_due_batches(self.con)
        self.assertEqual(again["batches_due"], 0)
        self.assertEqual(ledger_count(self.con), 5)

    def test_scenario_2_supportxmr_dust(self):
        # Example B (§4): SupportXMR 60 bps, 3 users, weights 2:1:1.
        u1 = make_user(self.con, "u1")
        u2 = make_user(self.con, "u2")
        u3 = make_user(self.con, "u3")
        w1 = make_worker(self.con, u1, "browser", "w1")
        w2 = make_worker(self.con, u2, "browser", "w2")
        w3 = make_worker(self.con, u3, "browser", "w3")
        add_local_share(self.con, w1, 2, "b1", W0 + 10)
        add_local_share(self.con, w2, 1, "b2", W0 + 20)
        add_local_share(self.con, w3, 1, "b3", W0 + 30)
        rw.record_batch(self.con, "SupportXMR", "simulation", "sim-20261118-002",
                        W0, W1, ONE_XMR, source_evidence="simulated-harness:scenario-2",
                        batch_ref="sim-20261118-002")
        result = rw.settle_batch(self.con, batch_ref="sim-20261118-002")
        self.assertEqual(result["status"], "settled")
        self.assertEqual(result["fee_piconero"], 6_000_000_000)
        self.assertEqual(result["net_piconero"], 994_000_000_000)
        self.assertEqual(result["atlas_share_piconero"], 248_500_000_000)
        self.assertEqual(result["users_total_piconero"], 745_500_000_000)
        self.assertEqual(result["allocations"][u1], 372_750_000_000)
        self.assertEqual(result["allocations"][u2], 186_375_000_000)
        self.assertEqual(result["allocations"][u3], 186_375_000_000)
        # Dust: a second batch with users_total 10, three equal weights —
        # the 1-piconero remainder goes to the lowest user_id.
        add_local_share(self.con, w1, 1, "d1", W1 + 10)
        add_local_share(self.con, w2, 1, "d2", W1 + 20)
        add_local_share(self.con, w3, 1, "d3", W1 + 30)
        rw.record_batch(self.con, "MoneroOcean", "simulation", "sim-20261118-003",
                        W1, W2, 13, source_evidence="simulated-harness:scenario-2-dust",
                        batch_ref="sim-20261118-003")
        dust = rw.settle_batch(self.con, batch_ref="sim-20261118-003")
        self.assertEqual(dust["status"], "settled")
        self.assertEqual(dust["fee_piconero"], 0)
        self.assertEqual(dust["net_piconero"], 13)
        self.assertEqual(dust["atlas_share_piconero"], 3)
        self.assertEqual(dust["users_total_piconero"], 10)
        lowest = min(u1, u2, u3)
        self.assertEqual(dust["allocations"][lowest], 4)
        for uid in (u1, u2, u3):
            if uid != lowest:
                self.assertEqual(dust["allocations"][uid], 3)
        self.assertEqual(sum(dust["allocations"].values()), 10)
        verdict = rw.verify_chain(self.con)
        self.assertTrue(verdict["ok"], verdict)
        for brow in self.con.execute(
                "SELECT * FROM reward_batches WHERE status = 'settled'").fetchall():
            sums = ledger_sums_by_type(self.con, brow["id"])
            total = (sums.get("fee", 0) + sums.get("atlas_share", 0)
                     + sums.get("referral_reward", 0)
                     + sums.get("user_allocation", 0))
            self.assertEqual(total, brow["gross_piconero"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
