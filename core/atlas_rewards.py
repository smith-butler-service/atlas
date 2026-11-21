#!/usr/bin/env python3
"""ATLAS REWARD ENGINE — Master Mission 6 (host-side, stdlib only).

The 75/25 reward engine, SIMULATION ONLY. Implements
docs/master-mission6-design.md §1–§9 exactly:

  - Inputs are ONLY verified accepted shares (Input A) and confirmed pool
    reward batches (Input B). Local hashrate is never evidence and never
    enters any calculation; estimated hashrate never creates a balance.
  - All money is integer piconero (1 XMR = 10^12 piconero). Integer
    arithmetic only: fee floored by basis points, ATLAS 25% floored,
    users receive the remainder, per-user allocation by largest remainder
    (ties -> lowest user_id) so every batch reconciles to the piconero.
  - Attribution is difficulty-weighted pool-accepted shares only
    (weight = COALESCE(difficulty, 1)); a pool-accepted share with NULL
    external_id is excluded from attribution and counted.
  - Ledger is append-only with a SHA-256 hash chain (genesis prev_hash =
    64 zeros; canonical sorted-key JSON; entry order fee -> atlas_share
    -> referral_reward -> user_allocation). Corrections are `reversal`
    entries only, never UPDATE/DELETE of a committed row. (The single
    mechanical exception is inside the settle transaction itself: a row
    is INSERTed with entry_hash NULL, then UPDATEd with its computed
    hash in the SAME transaction before COMMIT, because the id is only
    known after INSERT. No committed row is ever modified afterwards.)
  - Exactly-once: UNIQUE(pool_name, source_ref) on reward batches,
    UNIQUE(share_id) on the batch<->share link table, whole settle in
    ONE transaction; a re-settle is a logged no-op.
  - Referrals: 5% (500 bps, config parameter, default 500 when the key
    is absent) of the referred user's allocation per cycle, funded from
    the ATLAS 25% only, direct only, no self-referral, only when the
    referred user earned > 0 in that cycle.
  - Mode gates: simulation batches settle while the emergency stop is ON
    (D-M6-7 exemption — they move no real value). Real-mode batches are
    REFUSED while the stop is ON or while config mode is simulation-only.
  - No payout code path exists (Gate 4). Any payout-shaped call is
    refused with a logged refusal. The payouts.idempotency_key column
    added by the Stage 2 migration is preparatory only.

Balances are DERIVED (SUM over ledger entries per user), never stored.

Config: reads config/pool-rewards.json fresh on every call (never cached
across passes) for pool fees, mode, and the referral rate. Writes NO
config. NOTE (deviation D-M6-B, forced by the task's no-config-change
limit): the design (§7/§13) specifies the build lane add
`referral_rate_bps: 500` to config/pool-rewards.json. That key was NOT
added here — the task forbids config changes — so the engine defaults
to 500 bps when the key is absent and reads it when present.

Usage (CLI; --db defaults to the live DB — tests MUST pass a temp DB):
    python3 core/atlas_rewards.py record-batch --pool MoneroOcean --mode simulation \
        --source-ref sim-001 --window-start <ts> --window-end <ts> --gross 1000000000000
    python3 core/atlas_rewards.py settle [--batch-ref <ref>]
    python3 core/atlas_rewards.py status
    python3 core/atlas_rewards.py verify-chain
    python3 core/atlas_rewards.py export [--path <file>]

Stdlib only. Portable by copying ~/workspace/atlas.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time

BASE = os.path.expanduser("~/workspace/atlas")
CFG_ATLAS = os.path.join(BASE, "config", "atlas.json")
CFG_POOL = os.path.join(BASE, "config", "pool-rewards.json")
DB = os.path.join(BASE, "data", "atlas.db")
EXPORT = os.path.join(BASE, "data", "rewards.json")

GENESIS_PREV_HASH = "0" * 64
PICONERO_PER_XMR = 10 ** 12
REFERRAL_RATE_BPS_DEFAULT = 500   # 5%; design §7 parameter, default when config key absent
USERS_PERCENT = 75
ATLAS_PERCENT = 25
BUSY_TIMEOUT_MS = 5000
LEDGER_ENTRY_TYPES = ("user_allocation", "atlas_share", "fee", "payout",
                      "referral_reward", "reversal")
# Entry types whose amounts credit a user's derived balance.
BALANCE_ENTRY_TYPES = ("user_allocation", "referral_reward", "payout", "reversal")


class RewardsError(ValueError):
    """Validation / safety refusal. Never carries a secret in its message."""


# ---------------------------------------------------------------------------
# Connection / config / audit
# ---------------------------------------------------------------------------

def connect(db_path=DB):
    """Open a connection with manual transaction control (autocommit mode),
    same pattern as atlas_coordinator.connect()."""
    con = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000.0)
    con.isolation_level = None
    con.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def load_configs():
    """Read both configs fresh on every call — never cached across passes."""
    with open(CFG_ATLAS) as f:
        atlas_cfg = json.load(f)
    with open(CFG_POOL) as f:
        pool_cfg = json.load(f)
    return atlas_cfg, pool_cfg


def _now():
    return int(time.time())


def _log_decision(con, decision, reason):
    """Insert one audit row (dept='rewards'). Does NOT commit; the caller
    owns the transaction. A decision without a reason is a failed audit
    entry — reason is required and must name the evidence."""
    if not reason:
        raise RewardsError("log_decision requires a non-empty reason")
    con.execute(
        "INSERT INTO decisions (ts, dept, decision, reason) VALUES (?,?,?,?)",
        (_now(), "rewards", decision, reason))


def _pool_fee_bps(pool_cfg, pool_name):
    """Configured pool fee in basis points (integer) for the named pool."""
    if pool_cfg.get("primary_pool", {}).get("name") == pool_name:
        return int(pool_cfg["primary_pool"].get("pool_fee_bps", 0))
    for fb in pool_cfg.get("fallback_pools", []):
        if fb.get("name") == pool_name:
            return int(fb.get("pool_fee_bps", 0))
    raise RewardsError(f"unknown pool {pool_name!r} (not in pool-rewards.json)")


def _known_pools(pool_cfg):
    names = set()
    primary = pool_cfg.get("primary_pool", {}).get("name")
    if primary:
        names.add(primary)
    for fb in pool_cfg.get("fallback_pools", []):
        if fb.get("name"):
            names.add(fb["name"])
    return names


def _referral_rate_bps(pool_cfg):
    """Referral rate in basis points. Config key when present (design §7);
    500 bps default when absent (see module docstring, D-M6-B)."""
    value = pool_cfg.get("referral_rate_bps", REFERRAL_RATE_BPS_DEFAULT)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RewardsError(
            f"referral_rate_bps must be an integer, got {value!r}")
    if value < 0 or value > 10000:
        raise RewardsError(f"referral_rate_bps out of range: {value}")
    return value


def _require_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise RewardsError(f"{name} must be an integer, got {value!r}")
    return value


# ---------------------------------------------------------------------------
# Pure arithmetic (design §2, §4) — integer piconero only, no estimates
# ---------------------------------------------------------------------------

def fee_for(gross_piconero, fee_bps):
    """Pool fee, floored. The sub-piconero remainder stays in net."""
    gross_piconero = _require_int("gross_piconero", gross_piconero)
    fee_bps = _require_int("fee_bps", fee_bps)
    if gross_piconero < 0:
        raise RewardsError(f"gross_piconero must be >= 0, got {gross_piconero}")
    if fee_bps < 0 or fee_bps > 10000:
        raise RewardsError(f"fee_bps out of range: {fee_bps}")
    return gross_piconero * fee_bps // 10000


def split_net(net_piconero):
    """(atlas_share, users_total). ATLAS 25% floored; users get the
    remainder, so the rounding remainder (0 or 1 piconero) goes to the
    users, never silently to ATLAS."""
    net_piconero = _require_int("net_piconero", net_piconero)
    if net_piconero < 0:
        raise RewardsError(f"net_piconero must be >= 0, got {net_piconero}")
    atlas_share = net_piconero * ATLAS_PERCENT // 100
    return atlas_share, net_piconero - atlas_share


def allocate_largest_remainder(users_total, weights):
    """Split users_total across users by difficulty weight, largest
    remainder method (design §4). weights: {user_id: weight int > 0}.
    Returns {user_id: amount int} with SUM == users_total exactly.
    Ties on remainder go to the lowest user_id first."""
    users_total = _require_int("users_total", users_total)
    if users_total < 0:
        raise RewardsError(f"users_total must be >= 0, got {users_total}")
    if not weights:
        if users_total != 0:
            raise RewardsError("cannot allocate a non-zero total with no weights")
        return {}
    total_weight = 0
    for user_id, w in weights.items():
        _require_int("weight", w)
        if w <= 0:
            raise RewardsError(f"weight for user {user_id} must be > 0, got {w}")
        total_weight += w
    if total_weight <= 0:
        raise RewardsError("total weight must be > 0")
    floors = {}
    remainders = {}
    for user_id, w in weights.items():
        exact = users_total * w
        floors[user_id] = exact // total_weight
        remainders[user_id] = exact % total_weight
    leftover = users_total - sum(floors.values())
    # 0 <= leftover < number of users, by construction.
    order = sorted(weights, key=lambda u: (-remainders[u], u))
    allocations = dict(floors)
    for user_id in order[:leftover]:
        allocations[user_id] += 1
    assert sum(allocations.values()) == users_total
    return allocations


# ---------------------------------------------------------------------------
# Ledger hash chain (design §5.3)
# ---------------------------------------------------------------------------

def _canonical_payload(entry):
    """Canonical JSON of one entry (sorted keys, no whitespace, JSON null
    for NULL values), encoded UTF-8. entry holds the §5.3 fields."""
    payload = {
        "id": entry["id"],
        "created_at": entry["created_at"],
        "entry_type": entry["entry_type"],
        "user_id": entry["user_id"],
        "amount_piconero": entry["amount_piconero"],
        "batch_id": entry["batch_id"],
        "reference": entry["reference"],
        "mode": entry["mode"],
        "note": entry["note"],
        "prev_hash": entry["prev_hash"],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _entry_hash(entry):
    return hashlib.sha256(_canonical_payload(entry)).hexdigest()


def _last_entry_hash(con):
    row = con.execute(
        "SELECT entry_hash FROM ledger ORDER BY id DESC LIMIT 1").fetchone()
    if row is None or row["entry_hash"] is None:
        return GENESIS_PREV_HASH
    return row["entry_hash"]


def _append_ledger_entry(con, entry_type, user_id, amount_piconero,
                         reference, batch_id, mode, note, created_at=None):
    """Append one entry inside the caller's transaction. INSERTs with
    entry_hash NULL, then UPDATEs it with the computed hash in the SAME
    transaction (the id is only known after INSERT — design §5.2).
    Returns the new entry id. Never commits."""
    if entry_type not in LEDGER_ENTRY_TYPES:
        raise RewardsError(f"unknown entry_type {entry_type!r}")
    amount_piconero = _require_int("amount_piconero", amount_piconero)
    if user_id is not None:
        _require_int("user_id", user_id)
    prev_hash = _last_entry_hash(con)
    cur = con.execute(
        """INSERT INTO ledger
               (entry_type, user_id, amount_piconero, reference, created_at,
                batch_id, prev_hash, entry_hash, mode, note)
           VALUES (?,?,?,?, ?, ?, ?, NULL, ?, ?)""",
        (entry_type, user_id, amount_piconero, reference,
         created_at if created_at is not None else _now(),
         batch_id, prev_hash, mode, note))
    entry_id = cur.lastrowid
    row = con.execute("SELECT * FROM ledger WHERE id = ?", (entry_id,)).fetchone()
    entry = dict(row)
    entry_hash = _entry_hash(entry)
    con.execute("UPDATE ledger SET entry_hash = ? WHERE id = ?",
                (entry_hash, entry_id))
    return entry_id


# ---------------------------------------------------------------------------
# Attribution (design §3) — verified accepted shares only
# ---------------------------------------------------------------------------

def _attribution(con, batch):
    """Difficulty-weighted attribution for one batch row.

    Origin filter is a parameter of the batch mode, never omitted:
    real batches use origin='pool', simulation batches use
    origin='local-test' (the identical code path, test shares only).
    Returns (weights {user_id: weight}, share_ids [linked in settle],
    null_difficulty_count, null_external_id_count)."""
    origin = "pool" if batch["mode"] == "real" else "local-test"
    start = batch["window_start"]
    end = batch["window_end"]
    weights = {}
    share_ids = []
    null_difficulty_count = 0
    for row in con.execute(
            """SELECT s.id AS share_id, w.user_id AS user_id, s.difficulty AS difficulty
               FROM shares s JOIN workers w ON w.id = s.worker_id
               WHERE s.origin = ? AND s.accepted = 1
                 AND s.external_id IS NOT NULL
                 AND s.submitted_at >= ? AND s.submitted_at < ?
                 AND NOT EXISTS (SELECT 1 FROM reward_batch_shares l
                                 WHERE l.share_id = s.id)
               ORDER BY s.id""",
            (origin, start, end)).fetchall():
        weight = row["difficulty"] if row["difficulty"] is not None else 1
        weights[row["user_id"]] = weights.get(row["user_id"], 0) + weight
        share_ids.append(row["share_id"])
        if row["difficulty"] is None:
            null_difficulty_count += 1
    # Pool-accepted shares in the window with NULL external_id are
    # EXCLUDED from attribution (no dedupe key, no credit) and counted.
    null_external_id_count = con.execute(
        """SELECT COUNT(*) FROM shares s
           WHERE s.origin = ? AND s.accepted = 1
             AND s.external_id IS NULL
             AND s.submitted_at >= ? AND s.submitted_at < ?
             AND NOT EXISTS (SELECT 1 FROM reward_batch_shares l
                             WHERE l.share_id = s.id)""",
        (origin, start, end)).fetchone()[0]
    return weights, share_ids, null_difficulty_count, null_external_id_count


def _referral_rewards(allocations, con, batch_ref, referral_rate_bps):
    """Referral rewards for one settled batch (design §7).

    For each referral row where the referred user earned A > 0 in this
    batch: reward = A * rate // 10000, paid to the referrer from the
    ATLAS 25% only. Direct only, no self-referral, only when A > 0.
    Returns (rewards [(referral_id, referrer_user_id, amount)],
    self_referral_skipped_count). Zero-amount rewards produce no entry."""
    rewards = []
    self_skipped = 0
    for row in con.execute(
            "SELECT * FROM referrals ORDER BY id").fetchall():
        referrer = row["referrer_user_id"]
        referred = row["referred_user_id"]
        earned = allocations.get(referred, 0)
        if earned <= 0:
            continue
        if referrer == referred:
            self_skipped += 1
            continue
        amount = earned * referral_rate_bps // 10000
        if amount <= 0:
            continue
        rewards.append((row["id"], referrer, amount))
    return rewards, self_skipped


# ---------------------------------------------------------------------------
# Batch recording (design §9 — opening a cycle)
# ---------------------------------------------------------------------------

def _get_batch(con, batch_ref=None, batch_id=None):
    if batch_id is not None:
        return con.execute(
            "SELECT * FROM reward_batches WHERE id = ?", (batch_id,)).fetchone()
    if batch_ref is not None:
        return con.execute(
            "SELECT * FROM reward_batches WHERE batch_ref = ?", (batch_ref,)).fetchone()
    raise RewardsError("settle/record needs batch_ref or batch_id")


def _log_own_txn(con, decision, reason):
    """Log a decision in its own transaction. Never raises on the log
    itself (a logging failure must not mask the outcome)."""
    try:
        con.execute("BEGIN IMMEDIATE")
        _log_decision(con, decision, reason)
        con.execute("COMMIT")
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass


def record_batch(con, pool_name, mode, source_ref, window_start, window_end,
                 gross_piconero, source_evidence=None, batch_ref=None,
                 atlas_cfg=None, pool_cfg=None):
    """Record (open) one reward batch. Returns the batch id, or None when
    the record is refused (refusal logged with a reason, nothing
    inserted). Raises RewardsError only on programmer errors (bad types,
    unknown mode value). Business refusals: unknown pool, gross <= 0,
    bad window, overlapping window, duplicate (pool, source_ref),
    real-mode while simulation-only / stop ON."""
    if atlas_cfg is None or pool_cfg is None:
        atlas_cfg, pool_cfg = load_configs()
    if mode not in ("real", "simulation"):
        raise RewardsError(f"mode must be 'real' or 'simulation', got {mode!r}")
    if not isinstance(pool_name, str) or not pool_name:
        raise RewardsError(f"pool_name must be a non-empty string, got {pool_name!r}")
    if not isinstance(source_ref, str) or not source_ref:
        raise RewardsError(f"source_ref must be a non-empty string, got {source_ref!r}")
    window_start = _require_int("window_start", window_start)
    window_end = _require_int("window_end", window_end)
    gross_piconero = _require_int("gross_piconero", gross_piconero)

    if pool_name not in _known_pools(pool_cfg):
        _log_own_txn(con, "reward-batch-refused",
                f"batch refused: unknown pool {pool_name!r} (not in pool-rewards.json)")
        return None
    if gross_piconero <= 0:
        _log_own_txn(con, "reward-batch-refused",
                f"batch refused: gross_piconero {gross_piconero} must be > 0 "
                f"(pool {pool_name}, source_ref {source_ref})")
        return None
    if window_end <= window_start:
        _log_own_txn(con, "reward-batch-refused",
                f"batch refused: window_end {window_end} <= window_start "
                f"{window_start} (pool {pool_name}, source_ref {source_ref})")
        return None
    if mode == "real" and (pool_cfg.get("mode") == "simulation-only"
                           or atlas_cfg.get("emergency_stop")):
        _log_own_txn(con, "reward-batch-refused",
                f"real-mode batch refused: pool {pool_name}, source_ref "
                f"{source_ref} (config mode {pool_cfg.get('mode')}, "
                f"emergency_stop {atlas_cfg.get('emergency_stop')})")
        return None
    clash = con.execute(
        "SELECT id FROM reward_batches WHERE pool_name = ? AND source_ref = ?",
        (pool_name, source_ref)).fetchone()
    if clash is not None:
        _log_own_txn(con, "reward-batch-duplicate-skipped",
                f"duplicate batch skipped: pool {pool_name}, source_ref "
                f"{source_ref} already recorded as batch id {clash['id']}")
        return None
    overlap = con.execute(
        """SELECT id, batch_ref FROM reward_batches
           WHERE pool_name = ? AND window_start < ? AND window_end > ?
           ORDER BY id LIMIT 1""",
        (pool_name, window_end, window_start)).fetchone()
    if overlap is not None:
        _log_own_txn(con, "reward-batch-refused",
                f"batch refused: window [{window_start}, {window_end}) overlaps "
                f"existing batch {overlap['batch_ref']} (id {overlap['id']}) "
                f"for pool {pool_name}")
        return None

    if batch_ref is None:
        batch_ref = (f"sim-{window_start}-{source_ref}" if mode == "simulation"
                     else f"pool-{pool_name}-{source_ref}")
    fee_bps = _pool_fee_bps(pool_cfg, pool_name)
    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            """INSERT INTO reward_batches
                   (batch_ref, pool_name, mode, source_ref, source_evidence,
                    window_start, window_end, gross_piconero, fee_bps,
                    status, created_at)
               VALUES (?,?,?,?, ?, ?, ?, ?, ?, 'open', ?)""",
            (batch_ref, pool_name, mode, source_ref, source_evidence,
             window_start, window_end, gross_piconero, fee_bps, _now()))
        batch_id = cur.lastrowid
        _log_decision(con, "reward-batch-recorded",
                      f"batch {batch_ref} (id {batch_id}) recorded: pool "
                      f"{pool_name}, mode {mode}, source_ref {source_ref}, "
                      f"gross {gross_piconero} piconero, fee_bps {fee_bps}, "
                      f"window [{window_start}, {window_end})")
        con.execute("COMMIT")
    except sqlite3.IntegrityError:
        con.rollback()
        _log_own_txn(con, "reward-batch-duplicate-skipped",
                f"duplicate batch skipped: pool {pool_name}, source_ref "
                f"{source_ref} violates the exactly-once constraint")
        return None
    except Exception:
        con.rollback()
        raise
    return batch_id


# ---------------------------------------------------------------------------
# Settlement (design §9 — closing a cycle)
# ---------------------------------------------------------------------------

def _settle_figures(batch, weights, pool_cfg):
    """Pure computation of one batch's figures from its row + weights.
    Returns a dict of exact integers (no writes)."""
    gross = batch["gross_piconero"]
    fee = fee_for(gross, batch["fee_bps"])
    net = gross - fee
    atlas_share, users_total = split_net(net)
    allocations = allocate_largest_remainder(users_total, weights)
    rate = _referral_rate_bps(pool_cfg)
    return {"gross": gross, "fee": fee, "net": net, "atlas_share": atlas_share,
            "users_total": users_total, "allocations": allocations,
            "referral_rate_bps": rate}


def settle_batch(con, batch_ref=None, batch_id=None):
    """Settle one open batch in ONE transaction (links + ledger entries +
    batch status flip + decision log). Returns a result dict with
    status 'settled' | 'held' | 'refused' | 'noop' | 'failed'.

    Held (stays 'open', no ledger entries, decision logged): zero
    eligible share weight, gross 0, or referral cap violated. Refused:
    real-mode while the stop is ON or config mode is simulation-only.
    A re-settle of a settled batch is a logged no-op."""
    batch = _get_batch(con, batch_ref=batch_ref, batch_id=batch_id)
    if batch is None:
        raise RewardsError(
            f"unknown batch (ref={batch_ref!r}, id={batch_id!r})")
    batch_ref = batch["batch_ref"]
    atlas_cfg, pool_cfg = load_configs()

    if batch["status"] == "settled":
        _log_own_txn(con, "reward-batch-settled",
                f"batch {batch_ref} (id {batch['id']}) already settled — "
                "re-settle ignored, no new ledger entries")
        return {"status": "noop", "batch_ref": batch_ref,
                "batch_id": batch["id"], "reason": "already settled"}
    if batch["mode"] == "real" and (pool_cfg.get("mode") == "simulation-only"
                                    or atlas_cfg.get("emergency_stop")):
        _log_own_txn(con, "reward-batch-refused",
                f"settle refused for real-mode batch {batch_ref}: config mode "
                f"{pool_cfg.get('mode')}, emergency_stop "
                f"{atlas_cfg.get('emergency_stop')}")
        return {"status": "refused", "batch_ref": batch_ref,
                "batch_id": batch["id"], "reason": "real-mode gate"}

    weights, share_ids, null_diff, null_ext = _attribution(con, batch)
    total_weight = sum(weights.values())
    if batch["gross_piconero"] <= 0:
        _log_own_txn(con, "reward-batch-held",
                f"batch {batch_ref} held: gross_piconero "
                f"{batch['gross_piconero']} is 0 — nothing to distribute")
        return {"status": "held", "batch_ref": batch_ref,
                "batch_id": batch["id"], "reason": "gross is 0"}
    if total_weight == 0:
        _log_own_txn(con, "reward-batch-held",
                f"batch {batch_ref} held: zero eligible share weight in "
                f"window [{batch['window_start']}, {batch['window_end']}) — "
                "nothing to attribute, value never auto-allocated to ATLAS")
        return {"status": "held", "batch_ref": batch_ref,
                "batch_id": batch["id"], "reason": "zero eligible weight"}

    figures = _settle_figures(batch, weights, pool_cfg)
    referrals, self_skipped = _referral_rewards(
        figures["allocations"], con, batch_ref, figures["referral_rate_bps"])
    referral_total = sum(amount for _, _, amount in referrals)
    if referral_total > figures["atlas_share"]:
        _log_own_txn(con, "reward-batch-held",
                f"batch {batch_ref} held: referral_total {referral_total} "
                f"exceeds atlas_share {figures['atlas_share']} (referral cap)")
        return {"status": "held", "batch_ref": batch_ref,
                "batch_id": batch["id"], "reason": "referral cap"}
    atlas_retained = figures["atlas_share"] - referral_total
    note = (f"null-difficulty shares: {null_diff}; "
            f"null-external-id excluded: {null_ext}")
    if self_skipped:
        note += f"; self-referrals skipped: {self_skipped}"

    try:
        con.execute("BEGIN IMMEDIATE")
        fresh = _get_batch(con, batch_id=batch["id"])
        if fresh["status"] != "open":
            con.execute("ROLLBACK")
            _log_own_txn(con, "reward-batch-settled",
                    f"batch {batch_ref} (id {batch['id']}) no longer open "
                    f"(status {fresh['status']}) — settle ignored")
            return {"status": "noop", "batch_ref": batch_ref,
                    "batch_id": batch["id"], "reason": "no longer open"}
        # Defensive re-check inside the transaction: shares linked since
        # the pre-check are excluded by the NOT EXISTS clause; recompute
        # from the fresh attribution so the ledger can never double-credit.
        weights2, share_ids2, null_diff2, null_ext2 = _attribution(con, batch)
        if weights2 != weights or share_ids2 != share_ids:
            weights, share_ids = weights2, share_ids2
            null_diff, null_ext = null_diff2, null_ext2
            total_weight = sum(weights.values())
            if total_weight == 0:
                con.execute("ROLLBACK")
                _log_own_txn(con, "reward-batch-held",
                        f"batch {batch_ref} held on re-check: zero eligible "
                        "share weight — nothing to attribute")
                return {"status": "held", "batch_ref": batch_ref,
                        "batch_id": batch["id"],
                        "reason": "zero eligible weight on re-check"}
            figures = _settle_figures(batch, weights, pool_cfg)
            referrals, self_skipped = _referral_rewards(
                figures["allocations"], con, batch_ref,
                figures["referral_rate_bps"])
            referral_total = sum(amount for _, _, amount in referrals)
            if referral_total > figures["atlas_share"]:
                con.execute("ROLLBACK")
                _log_own_txn(con, "reward-batch-held",
                        f"batch {batch_ref} held on re-check: referral_total "
                        f"{referral_total} exceeds atlas_share "
                        f"{figures['atlas_share']}")
                return {"status": "held", "batch_ref": batch_ref,
                        "batch_id": batch["id"], "reason": "referral cap"}
            atlas_retained = figures["atlas_share"] - referral_total
            note = (f"null-difficulty shares: {null_diff}; "
                    f"null-external-id excluded: {null_ext}")
            if self_skipped:
                note += f"; self-referrals skipped: {self_skipped}"
        for share_id in share_ids:
            con.execute(
                "INSERT INTO reward_batch_shares (batch_id, share_id) VALUES (?,?)",
                (batch["id"], share_id))
        # Deterministic entry order (design §5.3): fee, atlas_share,
        # referral_reward (by referrer user_id), user_allocation (by user_id).
        _append_ledger_entry(
            con, "fee", None, figures["fee"],
            f"pool-fee:{batch['pool_name']}:{batch_ref}",
            batch["id"], batch["mode"], note)
        _append_ledger_entry(
            con, "atlas_share", None, atlas_retained,
            f"batch:{batch_ref}", batch["id"], batch["mode"], None)
        for referral_id, referrer, amount in sorted(referrals, key=lambda r: r[1]):
            _append_ledger_entry(
                con, "referral_reward", referrer, amount,
                f"referral:{referral_id}:batch:{batch_ref}",
                batch["id"], batch["mode"], None)
        for user_id in sorted(figures["allocations"]):
            amount = figures["allocations"][user_id]
            if amount <= 0:
                continue
            _append_ledger_entry(
                con, "user_allocation", user_id, amount,
                f"batch:{batch_ref}", batch["id"], batch["mode"], None)
        con.execute(
            """UPDATE reward_batches SET status = 'settled', settled_at = ?,
                   fee_piconero = ?, net_piconero = ?,
                   atlas_share_piconero = ?, users_total_piconero = ?,
                   referral_total_piconero = ?, shares_count = ?,
                   null_difficulty_count = ?, null_external_id_count = ?
               WHERE id = ?""",
            (_now(), figures["fee"], figures["net"], atlas_retained,
             figures["users_total"], referral_total, len(share_ids),
             null_diff, null_ext, batch["id"]))
        _log_decision(con, "reward-batch-settled",
                      f"batch {batch_ref} (id {batch['id']}) settled: gross "
                      f"{figures['gross']}, fee {figures['fee']}, net "
                      f"{figures['net']}, ATLAS retained {atlas_retained}, "
                      f"users_total {figures['users_total']}, referral_total "
                      f"{referral_total}, shares attributed {len(share_ids)}, "
                      f"null-difficulty {null_diff}, null-external-id "
                      f"excluded {null_ext}, mode {batch['mode']}")
        con.execute("COMMIT")
    except Exception as exc:
        try:
            con.rollback()
        except Exception:
            pass
        _log_own_txn(con, "reward-batch-failed",
                f"batch {batch_ref} settle failed, rolled back, batch stays "
                f"open: {exc}")
        return {"status": "failed", "batch_ref": batch_ref,
                "batch_id": batch["id"], "reason": str(exc)}
    return {"status": "settled", "batch_ref": batch_ref,
            "batch_id": batch["id"], "mode": batch["mode"],
            "gross_piconero": figures["gross"],
            "fee_piconero": figures["fee"],
            "net_piconero": figures["net"],
            "atlas_share_piconero": atlas_retained,
            "users_total_piconero": figures["users_total"],
            "referral_total_piconero": referral_total,
            "shares_count": len(share_ids),
            "null_difficulty_count": null_diff,
            "null_external_id_count": null_ext,
            "allocations": figures["allocations"]}


def settle_due_batches(con):
    """Settle every due (open) batch. Guarded sub-step for the coordinator
    pass (design §9): "due" = status open and mode allowed (simulation
    always; real only if config mode is not simulation-only AND the
    emergency stop is off). NEVER raises — an engine exception is
    collected and the pass continues. Returns a summary dict."""
    summary = {"batches_due": 0, "settled": [], "held": [],
               "refused": [], "noop": [], "failed": []}
    try:
        rows = con.execute(
            "SELECT id, batch_ref FROM reward_batches WHERE status = 'open' "
            "ORDER BY id").fetchall()
    except Exception as exc:
        summary["error"] = f"could not list open batches: {exc}"
        return summary
    summary["batches_due"] = len(rows)
    for row in rows:
        try:
            result = settle_batch(con, batch_id=row["id"])
        except Exception as exc:
            result = {"status": "failed", "batch_ref": row["batch_ref"],
                      "batch_id": row["id"], "reason": str(exc)}
            _log_own_txn(con, "reward-pass-failed",
                    f"reward engine exception settling batch "
                    f"{row['batch_ref']}: {exc}")
        status = result.get("status", "failed")
        if status in summary:
            summary[status].append(result.get("batch_ref", row["batch_ref"]))
        else:
            summary["failed"].append(result.get("batch_ref", row["batch_ref"]))
    return summary


# ---------------------------------------------------------------------------
# Corrections — reversals only (design §5.2)
# ---------------------------------------------------------------------------

def record_reversal(con, entry_id, note=None):
    """Correct a wrong entry with a `reversal` entry (-X, reference
    "reversal-of:<entry_id>", same batch_id and mode as the original).
    The original entry stays in the chain, visible, forever. Returns the
    new reversal entry id."""
    row = con.execute("SELECT * FROM ledger WHERE id = ?", (entry_id,)).fetchone()
    if row is None:
        raise RewardsError(f"unknown ledger entry id {entry_id}")
    if row["entry_type"] == "reversal":
        raise RewardsError(f"entry {entry_id} is already a reversal")
    try:
        con.execute("BEGIN IMMEDIATE")
        new_id = _append_ledger_entry(
            con, "reversal", row["user_id"], -row["amount_piconero"],
            f"reversal-of:{entry_id}", row["batch_id"], row["mode"],
            note or f"reverses entry {entry_id} ({row['entry_type']} "
                    f"{row['amount_piconero']} piconero)")
        _log_decision(con, "reward-reversal-recorded",
                      f"reversal entry {new_id} recorded for ledger entry "
                      f"{entry_id} ({row['entry_type']} "
                      f"{row['amount_piconero']} piconero, batch "
                      f"{row['batch_id']})")
        con.execute("COMMIT")
    except Exception:
        con.rollback()
        raise
    return new_id


def record_correction(con, entry_id, corrected_amount_piconero, note=None):
    """Two new entries in one transaction: a `reversal` of the wrong
    entry, followed by a fresh corrected entry of the same type. Returns
    (reversal_entry_id, corrected_entry_id)."""
    row = con.execute("SELECT * FROM ledger WHERE id = ?", (entry_id,)).fetchone()
    if row is None:
        raise RewardsError(f"unknown ledger entry id {entry_id}")
    if row["entry_type"] == "reversal":
        raise RewardsError(f"entry {entry_id} is already a reversal")
    corrected_amount_piconero = _require_int(
        "corrected_amount_piconero", corrected_amount_piconero)
    try:
        con.execute("BEGIN IMMEDIATE")
        reversal_id = _append_ledger_entry(
            con, "reversal", row["user_id"], -row["amount_piconero"],
            f"reversal-of:{entry_id}", row["batch_id"], row["mode"],
            note or f"reverses entry {entry_id} before correction")
        corrected_id = _append_ledger_entry(
            con, row["entry_type"], row["user_id"], corrected_amount_piconero,
            f"correction-of:{entry_id}", row["batch_id"], row["mode"],
            note or f"corrected entry for {entry_id}")
        _log_decision(con, "reward-reversal-recorded",
                      f"entry {entry_id} corrected: reversal {reversal_id} "
                      f"(-{row['amount_piconero']}) + corrected entry "
                      f"{corrected_id} ({corrected_amount_piconero} piconero)")
        con.execute("COMMIT")
    except Exception:
        con.rollback()
        raise
    return reversal_id, corrected_id


# ---------------------------------------------------------------------------
# Verification (design §5.4) — read-only
# ---------------------------------------------------------------------------

def verify_chain(con, atlas_cfg=None, pool_cfg=None, log_result=False):
    """Run the §5.4 verifier. Read-only by default (no writes) so any
    auditor can run it; pass log_result=True to also log the
    'reward-chain-verified' decision (§9). Returns a dict with ok,
    entries, batches, totals, and the first failure named. A PASS on
    an empty ledger (0 entries — the live state in M6) is a valid trivial
    PASS and says so."""
    if atlas_cfg is None or pool_cfg is None:
        atlas_cfg, pool_cfg = load_configs()
    result = {"ok": False, "entries": 0, "batches": 0, "totals": {},
              "corrections": 0,
              "error": None, "first_bad_entry_id": None, "first_bad_batch": None}
    rows = con.execute("SELECT * FROM ledger ORDER BY id").fetchall()
    result["entries"] = len(rows)
    # 1. No gaps in the id sequence (a gap means a deleted row).
    for index, row in enumerate(rows, start=1):
        if row["id"] != index:
            result["error"] = (f"id gap: expected entry id {index}, "
                               f"found {row['id']} (a deleted row)")
            result["first_bad_entry_id"] = row["id"]
            return result
    # 2. Recompute every hash; check the prev_hash linkage.
    prev_hash = GENESIS_PREV_HASH
    for row in rows:
        entry = dict(row)
        if entry["prev_hash"] != prev_hash:
            result["error"] = (f"entry {entry['id']}: prev_hash mismatch "
                               f"(chain broken before this entry)")
            result["first_bad_entry_id"] = entry["id"]
            return result
        if entry["entry_hash"] != _entry_hash(entry):
            result["error"] = (f"entry {entry['id']}: entry_hash mismatch "
                               "(row was modified after commit)")
            result["first_bad_entry_id"] = entry["id"]
            return result
        prev_hash = entry["entry_hash"]
    # 3. Per settled batch: recompute fee/net/split/allocations from the
    #    batch row + linked share weights; check the reconciliation
    #    invariant fee + retained ATLAS + referral_total + user
    #    allocations == gross.
    batches = con.execute(
        "SELECT * FROM reward_batches WHERE status = 'settled' ORDER BY id"
    ).fetchall()
    result["batches"] = len(batches)
    for batch in batches:
        bad = _verify_batch(con, batch, pool_cfg)
        if bad is not None:
            result["error"] = bad
            result["first_bad_batch"] = batch["batch_ref"]
            return result
    # 4. Referential checks + Gate 4 closed: no payout entries may exist.
    for row in rows:
        if row["entry_type"] == "payout":
            result["error"] = (f"entry {row['id']}: payout entry exists "
                               "while Gate 4 is closed (no payout path)")
            result["first_bad_entry_id"] = row["id"]
            return result
        if row["entry_type"] in ("user_allocation", "referral_reward"):
            user = con.execute("SELECT id FROM users WHERE id = ?",
                               (row["user_id"],)).fetchone()
            if user is None:
                result["error"] = (f"entry {row['id']}: references unknown "
                                   f"user {row['user_id']}")
                result["first_bad_entry_id"] = row["id"]
                return result
        if row["batch_id"] is not None:
            brow = con.execute(
                "SELECT status FROM reward_batches WHERE id = ?",
                (row["batch_id"],)).fetchone()
            if brow is None or brow["status"] != "settled":
                result["error"] = (f"entry {row['id']}: references batch "
                                   f"{row['batch_id']} which is not settled")
                result["first_bad_entry_id"] = row["id"]
                return result
    # 5. PASS — with entry count, batch count, and total sums. Corrections
    # (reversal / corrected entries) are counted and reported, never hidden.
    result["totals"] = reward_totals(con)
    result["corrections"] = con.execute(
        "SELECT COUNT(*) FROM ledger WHERE entry_type = 'reversal' "
        "OR reference LIKE 'correction-of:%'").fetchone()[0]
    result["ok"] = True
    if not rows:
        result["message"] = "ledger empty — chain trivially valid, 0 entries"
    else:
        result["message"] = (f"chain valid: {len(rows)} entries, "
                             f"{len(batches)} settled batch(es)")
    if log_result:
        _log_chain_verified(con, result)
    return result


def _verify_batch(con, batch, pool_cfg):
    """Recompute one settled batch. Returns an error string, or None."""
    ref = batch["batch_ref"]
    gross = batch["gross_piconero"]
    fee = fee_for(gross, batch["fee_bps"])
    net = gross - fee
    atlas_share, users_total = split_net(net)
    if batch["fee_piconero"] != fee or batch["net_piconero"] != net:
        return (f"batch {ref}: stored fee/net "
                f"({batch['fee_piconero']}/{batch['net_piconero']}) != "
                f"recomputed ({fee}/{net})")
    # Weights from the shares actually linked to this batch.
    weights = {}
    linked = 0
    null_diff = 0
    for row in con.execute(
            """SELECT s.difficulty AS difficulty, w.user_id AS user_id
               FROM reward_batch_shares l
               JOIN shares s ON s.id = l.share_id
               JOIN workers w ON w.id = s.worker_id
               WHERE l.batch_id = ?""", (batch["id"],)).fetchall():
        weight = row["difficulty"] if row["difficulty"] is not None else 1
        weights[row["user_id"]] = weights.get(row["user_id"], 0) + weight
        linked += 1
        if row["difficulty"] is None:
            null_diff += 1
    if linked != batch["shares_count"]:
        return (f"batch {ref}: linked shares {linked} != stored "
                f"shares_count {batch['shares_count']}")
    if null_diff != batch["null_difficulty_count"]:
        return (f"batch {ref}: null-difficulty shares {null_diff} != stored "
                f"{batch['null_difficulty_count']}")
    expected_allocs = allocate_largest_remainder(users_total, weights) if weights else {}
    rate = _referral_rate_bps(pool_cfg)
    expected_referrals, _ = _referral_rewards(expected_allocs, con, ref, rate)
    expected_referral_total = sum(a for _, _, a in expected_referrals)
    expected_retained = atlas_share - expected_referral_total
    if batch["atlas_share_piconero"] != expected_retained:
        return (f"batch {ref}: stored atlas_share "
                f"{batch['atlas_share_piconero']} != recomputed retained "
                f"{expected_retained}")
    if batch["users_total_piconero"] != users_total:
        return (f"batch {ref}: stored users_total "
                f"{batch['users_total_piconero']} != recomputed {users_total}")
    if batch["referral_total_piconero"] != expected_referral_total:
        return (f"batch {ref}: stored referral_total "
                f"{batch['referral_total_piconero']} != recomputed "
                f"{expected_referral_total}")
    # Ledger sums for this batch, by entry type — ORIGINAL settlement
    # entries only. Reversal entries (type 'reversal') and corrected
    # entries (reference 'correction-of:<id>') are audit events layered
    # on top of the settlement, not part of it: the verifier checks that
    # the ORIGINAL settlement recomputes exactly, and the hash-chain
    # check (step 2) already validates every row including corrections.
    # The number of corrections is reported in the result, never hidden.
    sums = {}
    for row in con.execute(
            """SELECT entry_type, COALESCE(SUM(amount_piconero), 0) AS total,
                      COUNT(*) AS n FROM ledger WHERE batch_id = ?
               AND NOT (reference LIKE 'correction-of:%')
               GROUP BY entry_type""", (batch["id"],)).fetchall():
        sums[row["entry_type"]] = (row["total"], row["n"])
    fee_sum = sums.get("fee", (0, 0))[0]
    atlas_sum = sums.get("atlas_share", (0, 0))[0]
    referral_sum = sums.get("referral_reward", (0, 0))[0]
    user_sum = sums.get("user_allocation", (0, 0))[0]
    if fee_sum != fee:
        return f"batch {ref}: ledger fee sum {fee_sum} != recomputed {fee}"
    if atlas_sum != expected_retained:
        return (f"batch {ref}: ledger atlas_share sum {atlas_sum} != "
                f"recomputed retained {expected_retained}")
    if referral_sum != expected_referral_total:
        return (f"batch {ref}: ledger referral sum {referral_sum} != "
                f"recomputed {expected_referral_total}")
    if user_sum != users_total:
        return (f"batch {ref}: ledger user allocations sum {user_sum} != "
                f"recomputed users_total {users_total}")
    for user_id, expected in expected_allocs.items():
        actual = con.execute(
            """SELECT COALESCE(SUM(amount_piconero), 0) FROM ledger
               WHERE batch_id = ? AND entry_type = 'user_allocation'
                 AND user_id = ? AND NOT (reference LIKE 'correction-of:%')""",
            (batch["id"], user_id)).fetchone()[0]
        if actual != expected:
            return (f"batch {ref}: user {user_id} allocation {actual} != "
                    f"recomputed {expected}")
    if fee + atlas_sum + referral_sum + user_sum != gross:
        return (f"batch {ref}: reconciliation failed: fee {fee} + ATLAS "
                f"{atlas_sum} + referrals {referral_sum} + users {user_sum} "
                f"!= gross {gross}")
    return None


def _log_chain_verified(con, result):
    """Log the verifier outcome (best-effort, its own transaction; a
    logging failure never flips the verdict)."""
    try:
        con.execute("BEGIN IMMEDIATE")
        _log_decision(con, "reward-chain-verified",
                      f"chain verification: {'PASS' if result['ok'] else 'FAIL'}; "
                      f"{result['entries']} entries, {result['batches']} "
                      f"settled batch(es)"
                      + (f"; {result['error']}" if result["error"] else ""))
        con.execute("COMMIT")
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Derived reads (design §4, §10) — SUMs over the ledger, never stored
# ---------------------------------------------------------------------------

def reward_totals(con):
    """Derived split totals for the UI/mirror. All figures are SUMs over
    the ledger — nothing is stored, so nothing can drift."""
    totals = {}
    for entry_type in ("user_allocation", "referral_reward", "atlas_share",
                       "fee", "payout", "reversal"):
        totals[entry_type] = con.execute(
            "SELECT COALESCE(SUM(amount_piconero), 0) FROM ledger "
            "WHERE entry_type = ?", (entry_type,)).fetchone()[0]
    batches = con.execute(
        "SELECT status, COUNT(*) AS n FROM reward_batches GROUP BY status"
    ).fetchall()
    batch_counts = {"open": 0, "settled": 0, "held": 0}
    for row in batches:
        batch_counts[row["status"]] = row["n"]
    return {
        "total_user_rewards_piconero": totals["user_allocation"],
        "total_referral_rewards_piconero": totals["referral_reward"],
        "total_atlas_share_piconero": totals["atlas_share"],
        "total_pool_fees_piconero": totals["fee"],
        "total_payouts_piconero": totals["payout"],
        "total_reversals_piconero": totals["reversal"],
        "ledger_entries": con.execute(
            "SELECT COUNT(*) FROM ledger").fetchone()[0],
        "batches_open": batch_counts["open"],
        "batches_settled": batch_counts["settled"],
        "batches_held": batch_counts["held"],
    }


def balances(con):
    """Derived user balances: SUM over user_allocation + referral_reward +
    payout + reversal entries per user. {user_id: balance_piconero}."""
    out = {}
    for row in con.execute(
            """SELECT user_id, COALESCE(SUM(amount_piconero), 0) AS balance
               FROM ledger WHERE entry_type IN
                   ('user_allocation', 'referral_reward', 'payout', 'reversal')
                 AND user_id IS NOT NULL
               GROUP BY user_id""").fetchall():
        out[row["user_id"]] = row["balance"]
    return out


def user_balance(con, user_id):
    """Derived balance for one user (0 when the user has no entries)."""
    return balances(con).get(user_id, 0)


# ---------------------------------------------------------------------------
# Payout refusal — Gate 4 is closed (design §8)
# ---------------------------------------------------------------------------

def request_payout(con, user_id, amount_piconero):
    """No payout code path exists in Mission 6. Refuse with a logged
    refusal, never a silent no-op."""
    _log_own_txn(con, "reward-payout-refused",
            f"payout refused for user {user_id} ({amount_piconero} "
            "piconero): no payout flow exists — Gate 4 requires explicit "
            "authorization + security testing + a treasury design")
    raise RewardsError(
        "payout refused: no payout flow exists (Gate 4 closed)")


# ---------------------------------------------------------------------------
# Host export for the artifact mirror (design §10)
# ---------------------------------------------------------------------------

def export_rewards(con, atlas_cfg=None, pool_cfg=None):
    """Reward state for the artifact mirror. Host DB is the system of
    record; the artifact mirrors this read-only. Entry hashes ARE
    included — they are public audit data, not secrets. No tokens,
    hashes of credentials, or secrets are ever exported."""
    if atlas_cfg is None or pool_cfg is None:
        atlas_cfg, pool_cfg = load_configs()
    user_version = con.execute("PRAGMA user_version").fetchone()[0]
    batches = [dict(r) for r in con.execute(
        "SELECT * FROM reward_batches ORDER BY id").fetchall()]
    ledger = [dict(r) for r in con.execute(
        "SELECT * FROM ledger ORDER BY id").fetchall()]
    chain = verify_chain(con, atlas_cfg=atlas_cfg, pool_cfg=pool_cfg)
    mode = pool_cfg.get("mode", "simulation-only")
    return {
        "exported_at": _now(),
        "source_db_user_version": user_version,
        "mode": mode,
        "emergency_stop": bool(atlas_cfg.get("emergency_stop")),
        "mining_enabled": bool(atlas_cfg.get("mining", {}).get("enabled")),
        "simulation_only": mode == "simulation-only",
        "note": ("SIMULATION ONLY — no pool rewards, no workers, no shares; "
                 "all figures are simulation/test data, not earnings")
                if mode == "simulation-only" else
                "Live reward accounting — figures come only from confirmed pool rewards",
        "split": {"users_percent": USERS_PERCENT,
                  "atlas_percent": ATLAS_PERCENT,
                  "referral_rate_bps": _referral_rate_bps(pool_cfg)},
        "totals": reward_totals(con),
        "balances": balances(con),
        "batches": batches,
        "ledger": ledger,
        "chain": {"ok": chain["ok"], "entries": chain["entries"],
                  "batches": chain["batches"],
                  "message": chain.get("message") or chain.get("error")},
    }


def export_rewards_json(con=None, db_path=DB, export_path=EXPORT):
    """Write data/rewards.json by atomic write (.tmp -> os.replace),
    the same pattern as the coordinator export. Derived export: deleting
    it loses nothing, it regenerates from the DB. Returns (path, payload)."""
    own_con = False
    if con is None:
        con = connect(db_path)
        own_con = True
    try:
        payload = export_rewards(con)
    finally:
        if own_con:
            con.close()
    tmp_path = export_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(payload, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, export_path)
    return export_path, payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _open(db_path):
    return connect(db_path)


def cmd_record_batch(args):
    con = _open(args.db)
    try:
        batch_id = record_batch(
            con, args.pool, args.mode, args.source_ref,
            args.window_start, args.window_end, args.gross,
            source_evidence=args.source_evidence, batch_ref=args.batch_ref)
    finally:
        con.close()
    if batch_id is None:
        print("record refused (see decisions log, dept='rewards')",
              file=sys.stderr)
        return 1
    print(f"Batch recorded: id {batch_id}, ref {args.batch_ref or '(auto)'}")
    return 0


def cmd_settle(args):
    con = _open(args.db)
    try:
        if args.batch_ref:
            result = settle_batch(con, batch_ref=args.batch_ref)
        else:
            result = settle_due_batches(con)
    finally:
        con.close()
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in ("settled", "noop", "held") or \
        "batches_due" in result else 1


def cmd_status(args):
    con = _open(args.db)
    try:
        atlas_cfg, pool_cfg = load_configs()
        payload = {
            "mode": pool_cfg.get("mode"),
            "emergency_stop": bool(atlas_cfg.get("emergency_stop")),
            "totals": reward_totals(con),
            "balances": balances(con),
            "batches": [dict(r) for r in con.execute(
                "SELECT batch_ref, pool_name, mode, status, gross_piconero, "
                "fee_piconero, net_piconero, atlas_share_piconero, "
                "users_total_piconero, referral_total_piconero, shares_count "
                "FROM reward_batches ORDER BY id").fetchall()],
        }
    finally:
        con.close()
    print(json.dumps(payload, indent=2))
    return 0


def cmd_verify_chain(args):
    con = _open(args.db)
    try:
        result = verify_chain(con, log_result=True)
    finally:
        con.close()
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


def cmd_export(args):
    path, payload = export_rewards_json(export_path=args.path)
    print(f"Exported {path} (exported_at {payload['exported_at']}, "
          f"ledger entries {payload['totals']['ledger_entries']}, "
          f"batches settled {payload['totals']['batches_settled']})")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="ATLAS reward engine (Master Mission 6) — simulation only.")
    parser.add_argument("--db", default=DB, help="database path (default: live DB)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_rec = sub.add_parser("record-batch", help="record (open) a reward batch")
    p_rec.add_argument("--pool", required=True)
    p_rec.add_argument("--mode", choices=("real", "simulation"), required=True)
    p_rec.add_argument("--source-ref", required=True)
    p_rec.add_argument("--source-evidence", default=None)
    p_rec.add_argument("--window-start", type=int, required=True)
    p_rec.add_argument("--window-end", type=int, required=True)
    p_rec.add_argument("--gross", type=int, required=True)
    p_rec.add_argument("--batch-ref", default=None)

    p_set = sub.add_parser("settle", help="settle one batch or all due batches")
    p_set.add_argument("--batch-ref", default=None)

    sub.add_parser("status", help="print derived reward totals (read-only)")
    sub.add_parser("verify-chain", help="verify the ledger hash chain (read-only)")

    p_exp = sub.add_parser("export", help="write data/rewards.json (atomic)")
    p_exp.add_argument("--path", default=EXPORT)

    args = parser.parse_args(argv)
    handlers = {"record-batch": cmd_record_batch, "settle": cmd_settle,
                "status": cmd_status, "verify-chain": cmd_verify_chain,
                "export": cmd_export}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
