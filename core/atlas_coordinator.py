#!/usr/bin/env python3
"""ATLAS COORDINATOR — Master Mission 5 (host-side, stdlib only).

System of record for the mining-worker registry, share accounting, pool
stats, and worker sessions. Operates directly on the Stage 0 tables in
``data/atlas.db`` (design: docs/master-mission5-design.md).

Scope (simulation-only, binding):
  - Worker registration is host-side CLI only. Desktop workers get a
    per-worker token, shown ONCE, stored as scrypt hash + salt only.
    Browser workers have no token. Status after registration is
    ``registered`` — never ``active``.
  - A worker becomes ``active`` ONLY after pool-accepted shares are
    verified via the pool API. Local hashrate never activates a worker.
    In this mission activation is gated: with the emergency stop ON and
    no pool connection authorized, verify_worker_active() always refuses
    and logs the refusal.
  - Shares live in ONE table with an ``origin`` column (``pool`` vs
    ``local-test``). Reward attribution queries filter
    ``origin='pool' AND accepted=1`` ONLY. Local-test shares are
    diagnostics only — never attribution, never activation, never
    earnings.
  - Pool stats are a READ-ONLY public-API fetch (GET of MoneroOcean
    /pool/stats). No stratum, no share submission, no pool connection
    for earning. A failed fetch inserts NO row.
  - No real payout, no treasury access, no wallet/key/seed creation,
    no mining start/stop/throttle, no config change, no spending.
    The coordinator spawns no miner process and never mines on the host.
  - Every hashrate figure is "not measured" until a real Gate 1 probe
    measurement exists. ``reported_hashrate_hps`` is NULL by default
    and is NEVER populated from benchmarks or estimates.
  - All money is integer piconero (1 XMR = 10^12 piconero), never float.
    All timestamps are Unix epoch integers.

Design deviations (forced, documented — see the Lane C report):
  D-M5-1  Stage 0 declares sessions.session_token_hash NOT NULL, but
          design §2.3/§5.2 says a browser probe session has NO
          credential (NULL). Relaxing the column would need a table
          rebuild the design did not specify, so browser-probe rows
          store the literal marker ``none:browser-probe`` — explicitly
          not a hash, never a secret, never mirrored. Desktop-agent
          sessions store a real sha256 hex token hash.
  D-M5-2  The design's decision list (§5.3) has no success decision
          for a pool poll, but "3 consecutive failures" must persist
          across invocations. This module logs ``pool-stats-polled``
          on every successful poll so the failure streak can be
          derived from the decisions table (the audit trail), with no
          extra state file. ``pool-stats-unavailable`` is logged when
          the streak reaches exactly 3 (not on every later failure).
  D-M5-3  The design's SupportXMR fallback (§5.1) is NOT implemented:
          no verified SupportXMR stats-API endpoint URL is given in
          the design (only that the site returned 200 after a 301),
          and a URL must never be guessed. Fallback is owed pending
          the exact endpoint.

Usage:
    python3 core/atlas_coordinator.py status
    python3 core/atlas_coordinator.py pass [--force-poll]
    python3 core/atlas_coordinator.py export
    python3 core/atlas_coordinator.py register --user-id <id> --type desktop|browser --name <name>
        [--xmrig-version <ver>] [--xmrig-sha256 <hex>]
    python3 core/atlas_coordinator.py rotate-token --worker-id <id>
    python3 core/atlas_coordinator.py revoke-worker --worker-id <id>

Stdlib only. Portable by copying ~/workspace/atlas.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.expanduser("~/workspace/atlas")
CFG_ATLAS = os.path.join(BASE, "config", "atlas.json")
CFG_POOL = os.path.join(BASE, "config", "pool-rewards.json")
DB = os.path.join(BASE, "data", "atlas.db")
EXPORT = os.path.join(BASE, "data", "coordinator.json")

# Design §5.1 / §6.3 constants.
POOL_STATS_TIMEOUT_S = 10            # per attempt; max 1 retry (2 attempts total)
POOL_STATS_MAX_ATTEMPTS = 2
POOL_STATS_POLL_INTERVAL_S = 600     # 10-minute cadence
POOL_STATS_USER_AGENT = "ATLAS-coordinator/1.0"
BLOCK_REWARD_PICONERO = 600_000_000_000   # 0.6 XMR tail emission, integer piconero
MAX_BATCH_SHARES = 500               # one transaction per batch (design §3.2)
WORKER_SESSION_TTL_S = 86400         # 24 h without check-in (design §5.2, assumption)
BUSY_TIMEOUT_MS = 5000

WORKER_NAME_RE = re.compile(r"^[a-z0-9-]{1,32}$")
WORKER_STATUSES = ("pending", "registered", "active", "degraded", "suspended", "revoked")
SHARE_ORIGINS = ("pool", "local-test")
SESSION_TYPES = ("desktop-agent", "browser-probe")
# D-M5-1: marker stored in sessions.session_token_hash for browser-probe
# sessions (Stage 0 column is NOT NULL; there is no credential to hash).
NO_CREDENTIAL_MARKER = "none:browser-probe"

# scrypt cost (design §4.2 assumption; confirmed cheap on this host in tests).
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32


class CoordinatorError(ValueError):
    """Validation / safety refusal. Never carries a secret in its message."""


# ---------------------------------------------------------------------------
# Connection / config / audit
# ---------------------------------------------------------------------------

def connect(db_path=DB):
    """Open a connection with manual transaction control (autocommit mode).

    Every public function owns its transaction: BEGIN IMMEDIATE ... COMMIT
    (or ROLLBACK on error). busy_timeout 5000 ms; journal mode stays
    ``delete`` in this mission (WAL is a separate, deferred decision).
    """
    con = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000.0)
    con.isolation_level = None
    con.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def load_configs():
    """Read both configs fresh on every pass — never cached across passes."""
    with open(CFG_ATLAS) as f:
        atlas_cfg = json.load(f)
    with open(CFG_POOL) as f:
        pool_cfg = json.load(f)
    return atlas_cfg, pool_cfg


def log_decision(con, decision, reason):
    """Insert one audit row (dept='coordinator'). Does NOT commit; the
    caller owns the transaction. A decision without a reason is a failed
    audit entry — reason is required and must name the evidence."""
    if not reason:
        raise CoordinatorError("log_decision requires a non-empty reason")
    con.execute(
        "INSERT INTO decisions (ts, dept, decision, reason) VALUES (?,?,?,?)",
        (int(time.time()), "coordinator", decision, reason))


def _now():
    return int(time.time())


def _get_worker(con, worker_id):
    row = con.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()
    if row is None:
        raise CoordinatorError(f"unknown worker id {worker_id}")
    return row


# ---------------------------------------------------------------------------
# Worker registry (design §4)
# ---------------------------------------------------------------------------

def _scrypt_hash(token, salt_hex):
    salt = bytes.fromhex(salt_hex)
    return hashlib.scrypt(token.encode("utf-8"), salt=salt,
                          n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
                          dklen=SCRYPT_DKLEN).hex()


def register_worker(con, user_id, worker_type, name,
                    xmrig_version=None, xmrig_sha256=None):
    """Register a worker. Status after registration is ``registered``.

    Desktop: a per-worker token is generated (secrets.token_urlsafe(32)),
    stored as scrypt hash + per-worker salt only, and returned in the
    result dict so the CLI can show it ONCE. The plaintext token is never
    written to the DB, a file, or a log line.
    Browser: no token — token_hash/token_salt stay NULL.

    Raises CoordinatorError on: unknown user, bad type, bad name
    (charset [a-z0-9-], max 32 chars), or a name already in use for
    the same user.
    """
    if worker_type not in ("browser", "desktop"):
        raise CoordinatorError(f"worker_type must be 'browser' or 'desktop', got {worker_type!r}")
    if not isinstance(name, str) or not WORKER_NAME_RE.match(name):
        raise CoordinatorError(
            "worker name must match [a-z0-9-]{1,32} (lowercase, digits, hyphens only)")
    user = con.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise CoordinatorError(f"unknown user id {user_id}")
    existing = con.execute(
        "SELECT id FROM workers WHERE user_id = ? AND name = ?", (user_id, name)).fetchone()
    if existing is not None:
        raise CoordinatorError(f"worker name already in use for this user: {name!r}")

    token = None
    token_hash = None
    token_salt = None
    if worker_type == "desktop":
        token = secrets.token_urlsafe(32)
        token_salt = secrets.token_hex(16)
        token_hash = _scrypt_hash(token, token_salt)

    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            """INSERT INTO workers
                   (user_id, worker_type, name, status, registered_at,
                    token_hash, token_salt, xmrig_version, xmrig_sha256)
               VALUES (?,?,?, 'registered', ?, ?, ?, ?, ?)""",
            (user_id, worker_type, name, _now(), token_hash, token_salt,
             xmrig_version, xmrig_sha256))
        worker_id = cur.lastrowid
        log_decision(con, "worker-registered",
                     f"worker {name} ({worker_type}) registered for user {user_id}"
                     + ("; xmrig binary unverified (no sha256 supplied)"
                        if worker_type == "desktop" and not xmrig_sha256 else ""))
        con.execute("COMMIT")
    except Exception:
        con.rollback()  # no-op if no transaction is active
        raise
    return {"id": worker_id, "user_id": user_id, "worker_type": worker_type,
            "name": name, "status": "registered", "token": token}


def verify_worker_token(con, worker_id, token):
    """True only if the presented token matches the stored scrypt hash and
    the worker's token is active. Constant-time comparison. Never logs
    the token. Browser workers (no token) always return False."""
    if not token:
        return False
    try:
        row = _get_worker(con, worker_id)
    except CoordinatorError:
        return False
    if row["token_status"] != "active" or not row["token_hash"] or not row["token_salt"]:
        return False
    try:
        candidate = _scrypt_hash(token, row["token_salt"])
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, row["token_hash"])


def rotate_token(con, worker_id):
    """Issue a new token for a desktop worker; the old token is invalid
    immediately. Returns the new token (CLI shows it once). Browser
    workers have no token to rotate."""
    row = _get_worker(con, worker_id)
    if row["worker_type"] != "desktop":
        raise CoordinatorError(
            f"worker {row['name']} is a browser worker and has no token to rotate")
    if row["status"] == "revoked":
        raise CoordinatorError(f"worker {row['name']} is revoked; rotate is refused")
    token = secrets.token_urlsafe(32)
    token_salt = secrets.token_hex(16)
    token_hash = _scrypt_hash(token, token_salt)
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "UPDATE workers SET token_hash = ?, token_salt = ?, token_status = 'active' WHERE id = ?",
            (token_hash, token_salt, worker_id))
        log_decision(con, "worker-token-rotated",
                     f"token rotated for worker {row['name']} (id {worker_id}); old token invalidated")
        con.execute("COMMIT")
    except Exception:
        con.rollback()  # no-op if no transaction is active
        raise
    return {"id": worker_id, "name": row["name"], "token": token}


def revoke_worker(con, worker_id):
    """Revoke a worker: token_status='revoked', status='revoked'. Reports
    with the old token are rejected from now on. Revocation does NOT stop
    any running miner process — the operator must also stop the miner
    locally (design §4.2 / Mission 4 §5.6)."""
    row = _get_worker(con, worker_id)
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "UPDATE workers SET token_status = 'revoked', status = 'revoked' WHERE id = ?",
            (worker_id,))
        log_decision(con, "worker-revoked",
                     f"worker {row['name']} (id {worker_id}) revoked; old token rejected; "
                     "operator must also stop the miner locally")
        con.execute("COMMIT")
    except Exception:
        con.rollback()  # no-op if no transaction is active
        raise
    return {"id": worker_id, "name": row["name"], "status": "revoked"}


def verify_worker_active(con, worker_id, atlas_cfg=None):
    """Activation verification (design §4.5). GATED in this mission.

    1. Emergency stop ON  -> log 'worker-activation-held', NOT_ACTIVATED.
    2. No pool connection authorized (simulation-only) -> log
       'worker-activation-unverified', NOT_ACTIVATED.
    3. (Future, authorized only) pool-API verification — NOT implemented;
       if ever reached, it refuses safely and never activates.
    The worker's status is never changed by this function in this mission.
    """
    row = _get_worker(con, worker_id)
    if atlas_cfg is None:
        atlas_cfg, _ = load_configs()
    try:
        con.execute("BEGIN IMMEDIATE")
        if atlas_cfg.get("emergency_stop"):
            log_decision(con, "worker-activation-held",
                         f"activation refused for worker {row['name']} (id {worker_id}): "
                         "emergency stop active")
            con.execute("COMMIT")
            return {"activated": False, "reason": "emergency-stop",
                    "worker_id": worker_id, "status": row["status"]}
        # Branch 2 is the outcome in this mission, every time.
        log_decision(con, "worker-activation-unverified",
                     f"activation refused for worker {row['name']} (id {worker_id}): "
                     "no pool connection authorized — simulation-only")
        con.execute("COMMIT")
        return {"activated": False, "reason": "no-pool-connection",
                "worker_id": worker_id, "status": row["status"]}
    except Exception:
        con.rollback()  # no-op if no transaction is active
        raise


# ---------------------------------------------------------------------------
# Share accounting (design §3)
# ---------------------------------------------------------------------------

def _validate_share(share):
    """Validate one share dict. Returns a cleaned tuple or None if the
    share must be rejected (counted, never inserted)."""
    if not isinstance(share, dict):
        return None
    origin = share.get("origin")
    if origin not in SHARE_ORIGINS:
        return None
    accepted = share.get("accepted")
    if accepted not in (0, 1) or isinstance(accepted, bool):
        return None
    difficulty = share.get("difficulty")
    if difficulty is not None and (isinstance(difficulty, bool)
                                   or not isinstance(difficulty, int)):
        return None
    submitted_at = share.get("submitted_at", _now())
    if isinstance(submitted_at, bool) or not isinstance(submitted_at, int):
        return None
    external_id = share.get("external_id")
    if external_id is not None and not isinstance(external_id, str):
        return None
    job_id = share.get("job_id")
    if job_id is not None and not isinstance(job_id, str):
        return None
    # Local-test shares are permanently marked: origin='local-test' AND an
    # external_id prefixed 'local-test:' (design §3.1). Anything else is
    # rejected, not silently re-labelled.
    if origin == "local-test":
        if not external_id or not external_id.startswith("local-test:"):
            return None
    return (difficulty, accepted, submitted_at, origin, external_id, job_id)


def record_shares(con, worker_id, shares):
    """Insert a batch of shares (design §3.2). One transaction, max 500.

    - Worker must exist; a revoked worker's batch is rejected whole.
    - Pool-origin shares require token_status='active'.
    - Dedupe on (worker_id, external_id): same-worker duplicates are
      skipped, counted, and logged if any.
    - An external_id seen for a DIFFERENT worker is a conflict: the
      batch is rejected, the worker is flagged 'suspended', and the
      decision is logged (design §3.4).
    - A NULL-difficulty pool share is flagged in the decision log, not
      silently weighted (design §2.2).
    Returns {inserted, duplicates_skipped, rejected}.
    """
    if len(shares) > MAX_BATCH_SHARES:
        raise CoordinatorError(
            f"batch of {len(shares)} shares exceeds the {MAX_BATCH_SHARES} limit")
    try:
        worker = _get_worker(con, worker_id)
    except CoordinatorError:
        try:
            con.execute("BEGIN IMMEDIATE")
            log_decision(con, "share-batch-rejected",
                         f"share batch for unknown worker id {worker_id} rejected "
                         f"({len(shares)} shares)")
            con.execute("COMMIT")
        except Exception:
            con.rollback()  # no-op if no transaction is active
            raise
        return {"inserted": 0, "duplicates_skipped": 0, "rejected": len(shares)}

    valid = []
    rejected = 0
    null_difficulty_pool = 0
    for share in shares:
        cleaned = _validate_share(share)
        if cleaned is None:
            rejected += 1
            continue
        if cleaned[3] == "pool" and cleaned[0] is None:
            null_difficulty_pool += 1
        valid.append(cleaned)

    try:
        con.execute("BEGIN IMMEDIATE")
        if worker["status"] == "revoked" or worker["token_status"] == "revoked":
            log_decision(con, "share-batch-rejected",
                         f"share batch for revoked worker {worker['name']} (id {worker_id}) "
                         f"rejected ({len(shares)} shares)")
            con.execute("COMMIT")
            return {"inserted": 0, "duplicates_skipped": 0, "rejected": len(shares)}
        has_pool = any(s[3] == "pool" for s in valid)
        if has_pool and worker["token_status"] != "active":
            log_decision(con, "share-batch-rejected",
                         f"pool share batch for worker {worker['name']} (id {worker_id}) "
                         "rejected: token_status is not 'active'")
            con.execute("COMMIT")
            return {"inserted": 0, "duplicates_skipped": 0, "rejected": len(shares)}
        # Cross-worker duplicate conflict (design §3.4).
        # Mission 11 fix (D-M11-2): ONE batched indexed lookup per batch,
        # not one query per share. The old loop ran
        #   SELECT ... WHERE external_id = ? AND worker_id != ?
        # once per share; external_id-only lookups could not use the
        # (worker_id, external_id) composite index, so SQLite did a full
        # covering-index SCAN per share — O(n^2), 398.917 s at 1,000
        # workers / 100,000 shares (Mission 10, L5). The Stage 3
        # migration adds idx_shares_external_id (external_id alone), so
        # this single IN lookup is O(log n) per distinct id, and the
        # whole batch is O(batch log n). Behaviour is identical: the
        # first conflicting external_id in batch order suspends the
        # worker and rejects the whole batch, with the same decision
        # messages. On a DB without the Stage 3 index (older fixtures)
        # the same single query still runs — one scan per batch instead
        # of one per share — so the fix degrades gracefully.
        distinct_ids = []
        seen_ids = set()
        for _, _, _, _, external_id, _ in valid:
            if external_id is None or external_id in seen_ids:
                continue
            seen_ids.add(external_id)
            distinct_ids.append(external_id)
        if distinct_ids:
            placeholders = ",".join("?" for _ in distinct_ids)
            clash_map = {
                row["external_id"]: row["worker_id"]
                for row in con.execute(
                    f"SELECT external_id, worker_id FROM shares "
                    f"WHERE external_id IN ({placeholders}) AND worker_id != ?",
                    (*distinct_ids, worker_id)).fetchall()}
            for _, _, _, _, external_id, _ in valid:
                if external_id is None:
                    continue
                clash_worker = clash_map.get(external_id)
                if clash_worker is not None:
                    con.execute(
                        "UPDATE workers SET status = 'suspended' WHERE id = ?", (worker_id,))
                    log_decision(con, "worker-suspended",
                                 f"worker {worker['name']} (id {worker_id}) suspended: share "
                                 f"external_id {external_id!r} already recorded for worker "
                                 f"id {clash_worker} (duplicate/replay conflict)")
                    log_decision(con, "share-batch-rejected",
                                 f"share batch for worker {worker['name']} (id {worker_id}) "
                                 "rejected: cross-worker external_id conflict")
                    con.execute("COMMIT")
                    return {"inserted": 0, "duplicates_skipped": 0, "rejected": len(shares)}
        inserted = 0
        for difficulty, accepted, submitted_at, origin, external_id, job_id in valid:
            cur = con.execute(
                """INSERT OR IGNORE INTO shares
                       (worker_id, difficulty, accepted, submitted_at, origin, external_id, job_id)
                   VALUES (?,?,?,?,?,?,?)""",
                (worker_id, difficulty, accepted, submitted_at, origin, external_id, job_id))
            inserted += cur.rowcount
        duplicates = len(valid) - inserted
        if duplicates:
            log_decision(con, "share-batch-duplicates-skipped",
                         f"{duplicates} duplicate share(s) skipped for worker "
                         f"{worker['name']} (id {worker_id}); {inserted} inserted")
        if null_difficulty_pool:
            log_decision(con, "share-batch-null-difficulty",
                         f"{null_difficulty_pool} pool share(s) with NULL difficulty for worker "
                         f"{worker['name']} (id {worker_id}) flagged — not silently weighted")
        con.execute("COMMIT")
    except Exception:
        con.rollback()  # no-op if no transaction is active
        raise
    return {"inserted": inserted, "duplicates_skipped": duplicates,
            "rejected": rejected}


def record_share(con, worker_id, difficulty, share_hash, verified, local_test,
                 submitted_at=None):
    """Single-share convenience wrapper (original Mission 5 brief).

    Only shares that pass verification are recorded: verified=False
    inserts nothing and returns None. verified=True records accepted=1
    with origin 'local-test' (external_id 'local-test:<hash>') or 'pool'
    (external_id = the share hash, the dedupe key). Local-test shares
    are never presented as real mining shares.
    """
    if not verified:
        return None
    origin = "local-test" if local_test else "pool"
    external_id = f"local-test:{share_hash}" if local_test else share_hash
    result = record_shares(con, worker_id, [{
        "difficulty": difficulty, "accepted": 1,
        "submitted_at": submitted_at if submitted_at is not None else _now(),
        "origin": origin, "external_id": external_id, "job_id": None}])
    if result["inserted"] == 0:
        return None
    return result


def attribution_weights(con, start=None, end=None):
    """Difficulty-weighted pool-accepted shares per worker (design §3.3).

    Definition only — the reward engine (later mission) applies it to
    confirmed pool reward batches. Local-test shares carry zero weight
    by construction: the query filters origin='pool' AND accepted=1.
    Returns {worker_id: total_difficulty_weight} (NULL difficulty counts
    as weight 1 in display totals only; flagged at record time).
    """
    sql = ("SELECT worker_id, SUM(COALESCE(difficulty, 1)) AS w FROM shares "
           "WHERE origin = 'pool' AND accepted = 1")
    params = []
    if start is not None:
        sql += " AND submitted_at >= ?"
        params.append(start)
    if end is not None:
        sql += " AND submitted_at <= ?"
        params.append(end)
    sql += " GROUP BY worker_id"
    return {row["worker_id"]: row["w"]
            for row in con.execute(sql, params).fetchall()}


# ---------------------------------------------------------------------------
# Pool stats (design §5.1) — read-only public API fetch
# ---------------------------------------------------------------------------

def record_pool_stats(con, pool, hashrate, miners, height,
                      network_hashrate=None,
                      block_reward_piconero=BLOCK_REWARD_PICONERO,
                      pool_fee_bps=None):
    """Insert ONE pool_stats row (a recorded observation — never 0 for a
    missing field; missing fields stay NULL). pool_fee_bps defaults to
    the configured fee for the pool. All money is integer piconero."""
    for label, value in (("hashrate", hashrate), ("miners", miners),
                         ("height", height), ("network_hashrate", network_hashrate)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise CoordinatorError(f"{label} must be an integer or None, got {value!r}")
    if pool_fee_bps is None:
        _, pool_cfg = load_configs()
        pool_fee_bps = _pool_fee_bps(pool_cfg, pool)
    if isinstance(pool_fee_bps, bool) or not isinstance(pool_fee_bps, int):
        raise CoordinatorError(f"pool_fee_bps must be an integer, got {pool_fee_bps!r}")
    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            """INSERT INTO pool_stats
                   (pool_name, recorded_at, hashrate, miners, block_height,
                    network_hashrate, block_reward_piconero, pool_fee_bps)
               VALUES (?,?, ?, ?, ?, ?, ?, ?)""",
            (pool, _now(), hashrate, miners, height, network_hashrate,
             block_reward_piconero, pool_fee_bps))
        row_id = cur.lastrowid
        con.execute("COMMIT")
    except Exception:
        con.rollback()  # no-op if no transaction is active
        raise
    return row_id


def _pool_fee_bps(pool_cfg, pool_name):
    if pool_cfg.get("primary_pool", {}).get("name") == pool_name:
        return int(pool_cfg["primary_pool"].get("pool_fee_bps", 0))
    for fb in pool_cfg.get("fallback_pools", []):
        if fb.get("name") == pool_name:
            return int(fb.get("pool_fee_bps", 0))
    return 0


def _fetch_pool_stats_json(pool_cfg, opener=None):
    """GET the primary pool's /pool/stats. 10 s timeout, 1 retry on
    timeout/transport error (2 attempts total). Returns the parsed JSON
    dict. Raises on failure — the caller logs it and inserts NO row."""
    primary = pool_cfg["primary_pool"]
    url = primary["api_base"].rstrip("/") + primary["stats_endpoint"]
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": POOL_STATS_USER_AGENT})
    last_error = None
    for _ in range(POOL_STATS_MAX_ATTEMPTS):
        try:
            open_fn = opener or urllib.request.urlopen
            with open_fn(req, timeout=POOL_STATS_TIMEOUT_S) as resp:
                if resp.status != 200:
                    raise urllib.error.HTTPError(url, resp.status, "non-200", None, None)
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError,
                json.JSONDecodeError) as exc:
            last_error = exc
    raise CoordinatorError(f"pool stats fetch failed after "
                           f"{POOL_STATS_MAX_ATTEMPTS} attempts: {last_error}")


def _parse_pool_stats(data):
    """Extract the recorded fields from a MoneroOcean /pool/stats payload.

    Verified live shape (2026-11-18): top-level ``pool_statistics``
    object with ``hashRate`` (float H/s, pool-wide), ``miners`` (int),
    ``lastBlockFound`` (int block height). No network-hashrate field is
    supplied -> NULL (never 0, never guessed). Floats are rounded to
    integers; a missing field stays NULL.
    """
    stats = data.get("pool_statistics") or {}
    def _int_or_none(value):
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return int(round(value))
        return None
    return {"hashrate": _int_or_none(stats.get("hashRate")),
            "miners": _int_or_none(stats.get("miners")),
            "height": _int_or_none(stats.get("lastBlockFound")),
            "network_hashrate": None}


def _consecutive_pool_failures(con):
    """Count trailing 'pool-stats-poll-failed' decisions since the most
    recent 'pool-stats-polled' success (D-M5-2). 'pool-stats-unavailable'
    rows do not break the streak."""
    count = 0
    for row in con.execute(
            "SELECT decision FROM decisions WHERE dept = 'coordinator' "
            "ORDER BY id DESC LIMIT 100"):
        if row["decision"] == "pool-stats-poll-failed":
            count += 1
        elif row["decision"] == "pool-stats-polled":
            break
    return count


def poll_pool_stats(con, pool_cfg=None, opener=None):
    """One pool-stats poll (design §5.1). On success inserts exactly one
    pool_stats row and logs 'pool-stats-polled'. On failure inserts NO
    row, logs 'pool-stats-poll-failed', and logs 'pool-stats-unavailable'
    when the consecutive-failure streak reaches 3. Never raises on a
    pool failure; returns a result dict."""
    if pool_cfg is None:
        _, pool_cfg = load_configs()
    pool_name = pool_cfg["primary_pool"]["name"]
    try:
        data = _fetch_pool_stats_json(pool_cfg, opener=opener)
    except CoordinatorError as exc:
        try:
            con.execute("BEGIN IMMEDIATE")
            log_decision(con, "pool-stats-poll-failed",
                         f"MoneroOcean /pool/stats poll failed: {exc}")
            failures = _consecutive_pool_failures(con)
            if failures == 3:
                log_decision(con, "pool-stats-unavailable",
                             "MoneroOcean /pool/stats unavailable after 3 consecutive "
                             "failed polls; showing last good reading as STALE")
            con.execute("COMMIT")
        except Exception:
            con.rollback()  # no-op if no transaction is active
            raise
        return {"ok": False, "pool": pool_name,
                "consecutive_failures": failures, "error": str(exc)}
    parsed = _parse_pool_stats(data)
    row_id = record_pool_stats(
        con, pool_name, parsed["hashrate"], parsed["miners"], parsed["height"],
        network_hashrate=parsed["network_hashrate"],
        pool_fee_bps=_pool_fee_bps(pool_cfg, pool_name))
    try:
        con.execute("BEGIN IMMEDIATE")
        log_decision(con, "pool-stats-polled",
                     f"MoneroOcean /pool/stats: hashrate "
                     f"{parsed['hashrate'] if parsed['hashrate'] is not None else 'UNAVAILABLE'} H/s, "
                     f"miners {parsed['miners'] if parsed['miners'] is not None else 'UNAVAILABLE'}, "
                     f"height {parsed['height'] if parsed['height'] is not None else 'UNAVAILABLE'}")
        con.execute("COMMIT")
    except Exception:
        con.rollback()  # no-op if no transaction is active
        raise
    return {"ok": True, "pool": pool_name, "row_id": row_id, **parsed}


# ---------------------------------------------------------------------------
# Sessions (design §5.2)
# ---------------------------------------------------------------------------

def record_worker_session(con, worker_id, session_type, session_ref=None,
                          session_token=None):
    """Open a worker session (kind='worker').

    desktop-agent: an agent session token is required (generated if not
    supplied); its sha256 is stored. A second concurrent desktop-agent
    session for the same worker from a DIFFERENT agent instance
    (different session_ref) is a token-conflict signal: the worker is
    flagged 'suspended', the decision is logged, and the open is refused.
    The same session_ref re-checking in returns the existing session.
    browser-probe: no credential exists — session_token_hash stores the
    marker 'none:browser-probe' (D-M5-1); session_ref is the tab session
    id. Probe sessions are LOCAL TEST, never mining sessions.
    user_id is always the worker's owner (enforced here, not by CHECK).
    expires_at = open time + 24 h (assumption).
    Returns {session_id, session_token} — session_token only for a newly
    created desktop-agent session (shown to the agent once, never logged).
    """
    if session_type not in SESSION_TYPES:
        raise CoordinatorError(f"session_type must be one of {SESSION_TYPES}")
    worker = _get_worker(con, worker_id)
    if worker["status"] == "revoked":
        raise CoordinatorError(f"worker {worker['name']} is revoked; session refused")
    now = _now()
    try:
        con.execute("BEGIN IMMEDIATE")
        if session_type == "desktop-agent":
            open_row = con.execute(
                """SELECT * FROM sessions WHERE worker_id = ? AND kind = 'worker'
                       AND ended_at IS NULL AND expires_at > ?
                       AND session_token_hash != ? ORDER BY id DESC LIMIT 1""",
                (worker_id, now, NO_CREDENTIAL_MARKER)).fetchone()
            if open_row is not None:
                if session_ref is not None and open_row["session_ref"] == session_ref:
                    con.execute("COMMIT")
                    return {"session_id": open_row["id"], "session_token": None}
                con.execute("UPDATE workers SET status = 'suspended' WHERE id = ?",
                            (worker_id,))
                log_decision(con, "worker-token-conflict",
                             f"token for worker {worker['name']} (id {worker_id}) presented "
                             "by a second agent instance; worker suspended")
                con.execute("COMMIT")
                raise CoordinatorError(
                    f"token conflict for worker {worker['name']}: a session is already "
                    "open from a different agent instance; worker suspended")
            token = session_token or secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        else:
            token = None
            token_hash = NO_CREDENTIAL_MARKER
        cur = con.execute(
            """INSERT INTO sessions
                   (user_id, session_token_hash, created_at, expires_at,
                    worker_id, kind, ended_at, session_ref)
               VALUES (?,?,?, ?, ?, 'worker', NULL, ?)""",
            (worker["user_id"], token_hash, now, now + WORKER_SESSION_TTL_S,
             worker_id, session_ref))
        session_id = cur.lastrowid
        con.execute("COMMIT")
    except CoordinatorError:
        raise
    except Exception:
        con.rollback()  # no-op if no transaction is active
        raise
    return {"session_id": session_id, "session_token": token}


def close_worker_session(con, session_id=None, worker_id=None):
    """Close a worker session (set ended_at=now). By session id, or the
    latest open session for a worker. Returns True if a session was
    closed, False if there was nothing open."""
    if session_id is None and worker_id is None:
        raise CoordinatorError("close_worker_session needs session_id or worker_id")
    now = _now()
    try:
        con.execute("BEGIN IMMEDIATE")
        if session_id is not None:
            cur = con.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ? AND kind = 'worker' "
                "AND ended_at IS NULL", (now, session_id))
        else:
            cur = con.execute(
                """UPDATE sessions SET ended_at = ? WHERE id = (
                       SELECT id FROM sessions WHERE worker_id = ? AND kind = 'worker'
                       AND ended_at IS NULL ORDER BY id DESC LIMIT 1)""",
                (now, worker_id))
        closed = cur.rowcount > 0
        con.execute("COMMIT")
    except Exception:
        con.rollback()  # no-op if no transaction is active
        raise
    return closed


def start_session(con, worker_id, session_type="browser-probe", session_ref=None):
    """Original-brief alias for record_worker_session()."""
    return record_worker_session(con, worker_id, session_type, session_ref=session_ref)


def end_session(con, worker_id):
    """Original-brief alias: close the latest open worker session."""
    return close_worker_session(con, worker_id=worker_id)


def close_expired_sessions(con):
    """Lazily close worker sessions past expires_at (ended_at=expires_at).
    Routine expiry is recorded in the row only — not decision-logged
    (design §5.2). Returns the number closed."""
    now = _now()
    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "UPDATE sessions SET ended_at = expires_at WHERE kind = 'worker' "
            "AND ended_at IS NULL AND expires_at <= ?", (now,))
        count = cur.rowcount
        con.execute("COMMIT")
    except Exception:
        con.rollback()  # no-op if no transaction is active
        raise
    return count


# ---------------------------------------------------------------------------
# Coordinator state + derived export (design §6)
# ---------------------------------------------------------------------------

def coordinator_status(con, atlas_cfg=None, pool_cfg=None):
    """Derive the coordinator state object from the tables + configs
    (D8: derived, not stored as a second truth). Every hashrate figure
    reads 'not measured' until a real probe measurement exists — Gate 1
    is UNMEASURED, so measured_hps is always None in this mission."""
    if atlas_cfg is None or pool_cfg is None:
        atlas_cfg, pool_cfg = load_configs()
    user_version = con.execute("PRAGMA user_version").fetchone()[0]
    now = _now()

    workers = {"total": 0, "active": 0, "registered": 0, "degraded": 0,
               "suspended": 0, "revoked": 0, "pending": 0}
    for row in con.execute("SELECT status, COUNT(*) AS n FROM workers GROUP BY status"):
        workers["total"] += row["n"]
        if row["status"] in workers:
            workers[row["status"]] = row["n"]

    shares = {"pool_accepted": 0, "pool_rejected": 0,
              "local_test_accepted": 0, "local_test_rejected": 0}
    for row in con.execute(
            "SELECT origin, accepted, COUNT(*) AS n FROM shares GROUP BY origin, accepted"):
        key = (("pool_" if row["origin"] == "pool" else "local_test_")
               + ("accepted" if row["accepted"] == 1 else "rejected"))
        shares[key] = row["n"]

    latest = con.execute(
        "SELECT * FROM pool_stats ORDER BY recorded_at DESC, id DESC LIMIT 1").fetchone()
    pool_stats_latest = None
    pool_stats_last_recorded_at = None
    if latest is not None:
        pool_stats_latest = {
            "pool_name": latest["pool_name"], "recorded_at": latest["recorded_at"],
            "hashrate": latest["hashrate"], "miners": latest["miners"],
            "block_height": latest["block_height"],
            "network_hashrate": latest["network_hashrate"],
            "block_reward_piconero": latest["block_reward_piconero"],
            "pool_fee_bps": latest["pool_fee_bps"]}
        pool_stats_last_recorded_at = latest["recorded_at"]

    sessions_active = con.execute(
        "SELECT COUNT(*) FROM sessions WHERE kind = 'worker' AND ended_at IS NULL "
        "AND expires_at > ?", (_now(),)).fetchone()[0]
    # Mission 7 design D-M7-4 (binding): total mining duration over
    # desktop-agent worker sessions only. Browser-probe sessions (token
    # marker none:browser-probe) are local-test sessions, not mining;
    # degenerate ended rows contribute 0; open sessions contribute up
    # to the export time. Derived at export time, never stored.
    worker_sessions_duration_seconds = con.execute(
        "SELECT COALESCE(SUM(CASE "
        "WHEN ended_at IS NULL THEN MAX(? - created_at, 0) "
        "WHEN ended_at > created_at THEN ended_at - created_at "
        "ELSE 0 END), 0) "
        "FROM sessions WHERE kind = 'worker' "
        "AND session_token_hash != ?",
        (now, NO_CREDENTIAL_MARKER)).fetchone()[0]
    last_decision = con.execute("SELECT MAX(id) FROM decisions").fetchone()[0]
    last_pass = con.execute(
        "SELECT MAX(ts) FROM decisions WHERE dept = 'coordinator' "
        "AND decision = 'coordinator-pass-complete'").fetchone()[0]

    return {
        "exported_at": now,
        "source_db_user_version": user_version,
        "mode": pool_cfg.get("mode", "simulation-only"),
        "emergency_stop": bool(atlas_cfg.get("emergency_stop")),
        "mining_enabled": bool(atlas_cfg.get("mining", {}).get("enabled")),
        "pool_connected": False,
        "pool_connection_note": "No pool connection authorized — read-only /pool/stats polling only",
        "workers": workers,
        "shares": shares,
        "hashrate": {"status": "not-measured", "measured_hps": None,
                     "note": "Gate 1 unmeasured — no probe measurement exists"},
        "pool_stats_latest": pool_stats_latest,
        "pool_stats_last_recorded_at": pool_stats_last_recorded_at,
        "sessions_active": sessions_active,
        "worker_sessions_duration_seconds": worker_sessions_duration_seconds,
        "last_decision_id": last_decision if last_decision is not None else 0,
        "last_coordinator_pass_at": last_pass,
    }


def export_coordinator_json(con=None, db_path=DB, export_path=EXPORT):
    """Write data/coordinator.json by atomic write (.tmp -> os.replace),
    the same pattern as the monitor daemon's snapshot.json. The file is
    a derived export: deleting it loses nothing, it regenerates from
    the DB. Returns (path, payload)."""
    own_con = False
    if con is None:
        con = connect(db_path)
        own_con = True
    try:
        payload = coordinator_status(con)
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
# One coordination pass (design §6.3)
# ---------------------------------------------------------------------------

def run_pass(db_path=DB, force_poll=False, opener=None, export_path=EXPORT):
    """One coordination pass: poll pool stats (if due — no row, or the
    latest row is older than 10 minutes — or force_poll), close expired
    sessions, verify pending activations (gated: always refused in this
    mission), export coordinator.json, log 'coordinator-pass-complete'.
    Returns a summary dict. Never crashes on a pool failure."""
    con = connect(db_path)
    try:
        atlas_cfg, pool_cfg = load_configs()
        latest = con.execute(
            "SELECT MAX(recorded_at) FROM pool_stats").fetchone()[0]
        poll_due = force_poll or latest is None or (_now() - latest) >= POOL_STATS_POLL_INTERVAL_S
        poll_result = {"ok": None, "skipped": True}
        if poll_due:
            poll_result = poll_pool_stats(con, pool_cfg=pool_cfg, opener=opener)
        # Master Mission 6 (§9): ONE guarded reward-engine sub-step.
        # settle_due_batches() never raises; this wrapper is belt-and-
        # braces so an engine failure (e.g. an import error) can NEVER
        # fail the coordinator pass. On the live DB there are no batches,
        # so this is a no-op reporting {"batches_due": 0}. No new cron.
        rewards_result = {"batches_due": 0}
        try:
            import atlas_rewards
            rewards_result = atlas_rewards.settle_due_batches(con)
        except Exception as exc:  # noqa: BLE001 — pass must continue
            rewards_result = {"batches_due": 0, "error": str(exc)}
            try:
                con.execute("BEGIN IMMEDIATE")
                log_decision(con, "reward-pass-failed",
                             f"reward engine sub-step failed: {exc}")
                con.execute("COMMIT")
            except Exception:
                con.rollback()  # no-op if no transaction is active
        expired_closed = close_expired_sessions(con)
        activation_results = []
        for row in con.execute(
                "SELECT id FROM workers WHERE status = 'registered'").fetchall():
            activation_results.append(verify_worker_active(con, row["id"], atlas_cfg=atlas_cfg))
        payload = coordinator_status(con)
        summary = {
            "pool_poll": poll_result,
            "rewards": rewards_result,
            "expired_sessions_closed": expired_closed,
            "activations_checked": len(activation_results),
            "activations_activated": sum(1 for r in activation_results if r["activated"]),
            "workers": payload["workers"],
            "shares": payload["shares"],
            "sessions_active": payload["sessions_active"],
        }
        # Log pass-complete BEFORE exporting, so the exported
        # last_coordinator_pass_at reflects this pass (design §6.2:
        # null only until a pass has run), then export once with the
        # completed pass included. The export is cheap and derived.
        con.execute("BEGIN IMMEDIATE")
        log_decision(con, "coordinator-pass-complete",
                     "coordinator pass complete: pool poll "
                     f"{'ok' if poll_result.get('ok') else ('skipped (not due)' if poll_result.get('skipped') else 'failed')}; "
                     f"{expired_closed} expired session(s) closed; "
                     f"{len(activation_results)} activation(s) checked, "
                     f"{summary['activations_activated']} activated; "
                     f"{payload['workers']['total']} worker(s), "
                     f"{payload['shares']['pool_accepted']} pool share(s) accepted, "
                     f"{payload['shares']['local_test_accepted']} local-test share(s) accepted")
        con.execute("COMMIT")
        _, payload = export_coordinator_json(con, export_path=export_path)
        # Master Mission 6 (§10): refresh the separate rewards export
        # (data/rewards.json) from the same pass, derived from the DB.
        # Guarded: an export failure never fails the pass. The path is
        # derived from the coordinator export path so tests writing to
        # /tmp stay in /tmp.
        try:
            import atlas_rewards
            rewards_path = os.path.join(
                os.path.dirname(export_path) or ".", "rewards.json")
            atlas_rewards.export_rewards_json(con, export_path=rewards_path)
        except Exception:  # noqa: BLE001 — export failure never fails pass
            pass
        # Master Mission 7 (Lane C): ONE guarded dashboard sub-step.
        # export_dashboard_json() is a read-only derivation (no ledger
        # rows, no decisions, no shares); a failure (e.g. an import
        # error) can NEVER fail the coordinator pass, and no decision is
        # logged per pass for this (the pass already logs
        # coordinator-pass-complete). The path is derived from the
        # coordinator export path so tests writing to /tmp stay in /tmp.
        try:
            import atlas_dashboard
            dashboard_path = os.path.join(
                os.path.dirname(export_path) or ".", "dashboard.json")
            atlas_dashboard.export_dashboard_json(con, export_path=dashboard_path)
        except Exception:  # noqa: BLE001 — export failure never fails pass
            pass
        # Master Mission 8 (Lane C): ONE guarded admin sub-step.
        # export_admin_json() is a read-only derivation (no ledger rows,
        # no decisions, no shares); a failure (e.g. an import error) can
        # NEVER fail the coordinator pass, and no decision is logged per
        # pass for this (the pass already logs coordinator-pass-complete).
        # The path is derived from the coordinator export path so tests
        # writing to /tmp stay in /tmp.
        try:
            import atlas_admin
            admin_path = os.path.join(
                os.path.dirname(export_path) or ".", "admin.json")
            atlas_admin.export_admin_json(con, export_path=admin_path)
        except Exception:  # noqa: BLE001 — export failure never fails pass
            pass
        # Master Mission 9 (Lane C): ONE guarded profitability sub-step.
        # export_profitability_json() is a read-only derivation (no
        # ledger rows, no decisions, no shares); a failure (e.g. an
        # import error) can NEVER fail the coordinator pass, and no
        # decision is logged per pass for this (the pass already logs
        # coordinator-pass-complete). The path is derived from the
        # coordinator export path so tests writing to /tmp stay in /tmp.
        # A live-fetch failure inside the module falls back to the last
        # recorded inputs (STALE, never fabricated), so the export is
        # still written.
        try:
            import atlas_profitability
            profitability_path = os.path.join(
                os.path.dirname(export_path) or ".", "profitability.json")
            atlas_profitability.export_profitability_json(
                con, export_path=profitability_path)
        except Exception:  # noqa: BLE001 — export failure never fails pass
            pass
        # Master Mission 10 (Lane C): ONE guarded security sub-step.
        # export_security_json() is a read-only derivation (no ledger
        # rows, no decisions, no shares); a failure (e.g. an import
        # error) can NEVER fail the coordinator pass, and no decision is
        # logged per pass for this (the pass already logs
        # coordinator-pass-complete). The path is derived from the
        # coordinator export path so tests writing to /tmp stay in /tmp.
        # It re-exports the last recorded scale results plus fresh
        # security derivations; it never runs a load test.
        try:
            import atlas_security
            security_path = os.path.join(
                os.path.dirname(export_path) or ".", "security.json")
            atlas_security.export_security_json(
                con, export_path=security_path)
        except Exception:  # noqa: BLE001 — export failure never fails pass
            pass
        summary["exported_at"] = payload["exported_at"]
        summary["last_coordinator_pass_at"] = payload["last_coordinator_pass_at"]
        return summary
    finally:
        con.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _open():
    return connect(DB)


def cmd_status(_args):
    con = _open()
    try:
        payload = coordinator_status(con)
    finally:
        con.close()
    print(json.dumps(payload, indent=2))
    print("Hashrate: not measured (Gate 1 unmeasured — no probe measurement exists)")
    return 0


def cmd_export(_args):
    path, payload = export_coordinator_json()
    print(f"Exported {path} (exported_at {payload['exported_at']}, "
          f"workers {payload['workers']['total']}, "
          f"pool_stats_last_recorded_at {payload['pool_stats_last_recorded_at']})")
    return 0


def cmd_pass(args):
    summary = run_pass(force_poll=args.force_poll)
    print(json.dumps(summary, indent=2))
    return 0


def cmd_register(args):
    con = _open()
    try:
        result = register_worker(con, args.user_id, args.type, args.name,
                                 xmrig_version=args.xmrig_version,
                                 xmrig_sha256=args.xmrig_sha256)
    except CoordinatorError as exc:
        print(f"registration refused: {exc}", file=sys.stderr)
        return 1
    finally:
        con.close()
    print(f"Worker registered: id {result['id']}, name {result['name']!r}, "
          f"type {result['worker_type']}, status {result['status']}")
    if result["worker_type"] == "desktop":
        print("TOKEN (shown once — paste it into the worker agent config, "
              "then store it securely; it will never be shown again):")
        print(result["token"])
        if not args.xmrig_sha256:
            print("NOTE: xmrig binary unverified (no --xmrig-sha256 supplied).")
    else:
        print("Browser worker: no token (identity is name + owner; "
              "work is validated by the pool, not by a token).")
    print("Status is 'registered'. The worker becomes Active only after the "
          "pool shows accepted shares for it — local hashrate never activates it.")
    return 0


def cmd_rotate_token(args):
    con = _open()
    try:
        result = rotate_token(con, args.worker_id)
    except CoordinatorError as exc:
        print(f"rotate refused: {exc}", file=sys.stderr)
        return 1
    finally:
        con.close()
    print(f"Token rotated for worker {result['name']!r} (id {result['id']}). "
          "The old token is invalid immediately.")
    print("NEW TOKEN (shown once — it will never be shown again):")
    print(result["token"])
    return 0


def cmd_revoke_worker(args):
    con = _open()
    try:
        result = revoke_worker(con, args.worker_id)
    except CoordinatorError as exc:
        print(f"revoke refused: {exc}", file=sys.stderr)
        return 1
    finally:
        con.close()
    print(f"Worker {result['name']!r} (id {result['id']}) revoked. "
          "Reports with the old token are rejected.")
    print("You must ALSO stop the miner locally — revocation does not stop "
          "a running XMRig process.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="ATLAS coordinator (Master Mission 5) — simulation only.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="print derived coordinator state")
    p_pass = sub.add_parser("pass", help="one coordination pass")
    p_pass.add_argument("--force-poll", action="store_true",
                        help="poll pool stats even if the last row is < 10 min old")
    sub.add_parser("export", help="write data/coordinator.json (atomic)")

    p_reg = sub.add_parser("register", help="register a worker (host-side only)")
    p_reg.add_argument("--user-id", type=int, required=True)
    p_reg.add_argument("--type", choices=("browser", "desktop"), required=True)
    p_reg.add_argument("--name", required=True)
    p_reg.add_argument("--xmrig-version", default=None)
    p_reg.add_argument("--xmrig-sha256", default=None)

    p_rot = sub.add_parser("rotate-token", help="rotate a desktop worker token")
    p_rot.add_argument("--worker-id", type=int, required=True)

    p_rev = sub.add_parser("revoke-worker", help="revoke a worker")
    p_rev.add_argument("--worker-id", type=int, required=True)

    args = parser.parse_args(argv)
    handlers = {"status": cmd_status, "pass": cmd_pass, "export": cmd_export,
                "register": cmd_register, "rotate-token": cmd_rotate_token,
                "revoke-worker": cmd_revoke_worker}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
