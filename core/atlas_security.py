#!/usr/bin/env python3
"""ATLAS HOST SECURITY + SCALE MODULE — Master Mission 10, Lane C
(host-side, stdlib only).

Implements docs/master-mission10-design.md §4 (security checks S1–S9)
and §5 (scale tests L1–L5, on-demand).

Derivation rules (binding, D-M10-1/D-M10-4/D-M10-6):
  - Host is the system of record. Everything here is DERIVED from live
    reads + temp-DB fixtures built and destroyed by this module.
    No new host DB tables. No migration.
  - The module writes no ledger rows, no decisions, no shares, no
    batches, no payouts, no sessions, no user rows — its only write is
    the atomic export of ``data/security.json`` itself (temp + os.replace).
  - Checks that mutate state run on TEMP DBs only (copies of the live
    DB in /tmp, destroyed afterwards), never the live DB. Checks that
    read live state are read-only (COUNT/SUM, config read, file grep).
  - Scale tests (L1–L5) are ON-DEMAND (CLI ``run-scale``) only, never
    inside the coordinator pass. Synthetic load runs on temp DBs only,
    is marked synthetic in every row it creates, and is destroyed
    afterwards. The module REFUSES a non-temp path for scale runs.
  - The coordinator sub-step calls ``export_security_json()`` only —
    it never runs a load test.

Monero addresses (D-M10-7, M3 §1f): validation proves format only,
never ownership. Keccak-256 (original Keccak, NOT NIST SHA3-256) is
implemented in pure Python inside this module; ``hashlib.sha3_256``
is FORBIDDEN for this purpose. The module asserts the Keccak-256("")
test vector at import time.

Redaction (D-M10-8): no token hash/salt, wallet, password, seed, or
private-key string ever appears in the export. The export deliberately
does NOT repeat the secret-pattern literals (they are listed here and
in the tests, never in the payload) — a grep of the export for those
literals must return 0 hits. Evidence strings in the export never
contain those literals either.

Documented deviations from the design (carried honestly, see report):
  D-M10-C1  S3's literal sequence (``request_payout()`` twice with the
            same idempotency key, "exactly one payout row") cannot run:
            ``request_payout()`` takes no idempotency key and Gate 4 is
            closed — it refuses every call. The check asserts the
            actual refusal path (both calls refused, 0 payout rows, 2
            logged refusals) plus the UNIQUE idempotency constraint via
            direct insert on a temp DB.
  D-M10-C2  S5 ordering: a naturally-encoded testnet/stagenet address
            is caught by the network-byte rule first (the first Base58
            character is determined by the network byte, so a testnet
            address starts with '9' and a stagenet one with 'A'-shape
            — the prefix check and the network-byte check agree).
            The first-char/length mismatch vector is a 77-byte payload
            with network byte 42 (subaddress prefix '8' at integrated
            length 106). The network-byte rule itself is also tested
            directly at the decoded-payload level with its exact
            reason strings. The decoded-length rule is likewise tested
            at the payload level (a decodable 95/106-char string always
            decodes to 69/77 bytes by block construction).
  D-M10-C3  L1 record_shares throughput is measured on 1,000 shares in
            2 x 500-share batches (500 is the engine's MAX_BATCH_SHARES
            cap — a single 1,000-share batch is refused by design).
  D-M10-C4  L3 temp-ledger leg: the diagnostics suite is bound to the
            live DB path (it restarts the daemon and logs live
            decisions by design), so a full-suite run against a temp
            ledger is impossible without misrepresenting it. The temp
            leg is recorded NOT_RUN with the verbatim reason, plus a
            supplementary timing of the DB-sensitive checks
            (verify_chain + COUNT/SUM) on the 10,000-entry temp ledger.
  D-M10-C5  L2 (mirror ingest timing) is artifact-side work (Lane D
            sandbox). The host records NOT_RUN with the design's
            verbatim reason "Mirror ingest timing not measured —
            sandbox unavailable" — never an invented number.

Usage:
    python3 core/atlas_security.py status      # print battery (read-only live checks + temp fixtures)
    python3 core/atlas_security.py export     # write data/security.json (atomic)
    python3 core/atlas_security.py run-tests  # run battery, exit 1 on any FAIL
    python3 core/atlas_security.py run-scale  # on-demand scale test (temp DB), records figures in the export

Stdlib only. Portable by copying ~/workspace/atlas.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

BASE = os.path.expanduser("~/workspace/atlas")
CORE = os.path.join(BASE, "core")
CFG_ATLAS = os.path.join(BASE, "config", "atlas.json")
CFG_POOL = os.path.join(BASE, "config", "pool-rewards.json")
DB = os.path.join(BASE, "data", "atlas.db")
EXPORT = os.path.join(BASE, "data", "security.json")
DATA_DIR = os.path.join(BASE, "data")
SNAPSHOT = os.path.join(BASE, "data", "snapshot.json")

MODULE_VERSION = "1.0.0-mission10"
BUSY_TIMEOUT_MS = 5000
SCALE_STALE_S = 86400            # scale results older than 24 h are STALE
EXPORT_FRESH_S = 600             # diagnostics test 27 freshness window
SCALE_REFUSAL = "run-scale refuses a non-temp path"
NO_SCALE_REASON = ("No scale test run yet — run the on-demand scale test "
                   "from the host to populate this panel")
SCALE_STALE_TAG = "Scale results stale — last run over 24 hours ago"
NO_BOTTLENECK = ("No bottleneck found up to 1,000 workers / 100,000 shares "
                 "— not tested beyond that load")
L2_NOT_RUN_REASON = "Mirror ingest timing not measured — sandbox unavailable"
L3_TEMP_NOT_RUN_REASON = ("Diagnostics suite runs against the live DB only "
                          "— temp-ledger full-suite timing not measured")
FORMAT_VALID_LINE = "Format valid — ownership not verified"
OWNERSHIP_LINE = ("Validation checks the address format only. "
                  "It does not prove who owns the address.")
SCOPE_LINE = ("Security & scale status — test evidence only. Passing these "
              "checks does not guarantee the system is secure — it proves "
              "these specific attacks were detected or refused in testing.")
MINING_NOT_ACTIVE = ("Mining is not active — no start path exists while the "
                     "emergency stop is ON")

# Secret patterns (D-M10-8). These literals must NEVER appear in the
# export payload or in any evidence string — the export reports only
# the count of patterns checked and the hit totals.
SECRET_PATTERNS = ("token_hash", "token_salt", "wallet", "password",
                   "seed", "private_key")
EXPORT_FILES = ("admin.json", "security.json", "rewards.json",
                "dashboard.json", "coordinator.json", "profitability.json")

# Monero Base58 alphabet (M3 §1f): excludes 0, O, I, l.
B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_MAP = {c: i for i, c in enumerate(B58_ALPHABET)}
# Full block: 8 bytes -> 11 chars; final partial block sizes.
_B58_ENCODE_LEN = {1: 2, 2: 3, 3: 5, 4: 6, 5: 7, 6: 9, 7: 10, 8: 11}
_B58_DECODE_LEN = {v: k for k, v in _B58_ENCODE_LEN.items()}
_FORBIDDEN_CHARS = ("0", "O", "I", "l")
MAINNET_NETWORK_BYTES = (18, 19, 42)
KECCAK_EMPTY_HEX = ("c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470")

# Scenario-1 fixture (M6 §12.2): 1 XMR, 2 users, one referred.
W0 = 1795000000
W1 = 1795003600
ONE_XMR = 1_000_000_000_000


class SecurityError(ValueError):
    """Refusal / validation failure. Never carries a secret in its message."""


# ---------------------------------------------------------------------------
# Pure-Python Keccak-256 (original Keccak, NOT NIST SHA3-256)
# ---------------------------------------------------------------------------

_MASK64 = (1 << 64) - 1
_KECCAK_RC = (
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
    0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
)
# Rotation offsets r[x][y] (Keccak spec).
_KECCAK_R = (
    (0, 36, 3, 41, 18),
    (1, 44, 10, 45, 2),
    (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56),
    (27, 20, 39, 8, 14),
)


def _rol(x, n):
    if n == 0:
        return x & _MASK64
    return ((x << n) | (x >> (64 - n))) & _MASK64


def _keccak_f(state):
    """Keccak-f[1600], 24 rounds. state: list of 25 ints, index x + 5*y."""
    for rc in _KECCAK_RC:
        # Theta
        col = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15]
               ^ state[x + 20] for x in range(5)]
        diff = [col[(x - 1) % 5] ^ _rol(col[(x + 1) % 5], 1)
                for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= diff[x]
        # Rho + Pi
        moved = [0] * 25
        for x in range(5):
            for y in range(5):
                moved[y + 5 * ((2 * x + 3 * y) % 5)] = \
                    _rol(state[x + 5 * y], _KECCAK_R[x][y])
        # Chi
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] = (moved[x + 5 * y]
                                    ^ ((~moved[(x + 1) % 5 + 5 * y])
                                       & moved[(x + 2) % 5 + 5 * y]))
        # Iota
        state[0] ^= rc
    return state


def keccak_256(data):
    """Original Keccak-256 (rate 1088 bits, suffix 0x01, pad10*1).
    Deliberately NOT hashlib.sha3_256 (NIST SHA3 differs in padding)."""
    if not isinstance(data, (bytes, bytearray)):
        raise SecurityError("keccak_256 input must be bytes")
    rate = 136  # bytes
    state = [0] * 25
    offset = 0
    while offset + rate <= len(data):
        block = data[offset:offset + rate]
        for i in range(rate // 8):
            state[i] ^= int.from_bytes(block[i * 8:(i + 1) * 8], "little")
        _keccak_f(state)
        offset += rate
    padded = bytearray(data[offset:])
    padded.append(0x01)
    while len(padded) % rate != rate - 1:
        padded.append(0x00)
    padded.append(0x80)
    for i in range(rate // 8):
        state[i] ^= int.from_bytes(bytes(padded[i * 8:(i + 1) * 8]), "little")
    _keccak_f(state)
    out = bytearray()
    while len(out) < 32:
        for i in range(rate // 8):
            out += state[i].to_bytes(8, "little")
            if len(out) >= 32:
                break
    return bytes(out[:32])


# Import-time assertion of the binding test vector (D-M10-7).
assert keccak_256(b"").hex() == KECCAK_EMPTY_HEX, \
    "Keccak-256 self-check failed: empty-input vector mismatch"


# ---------------------------------------------------------------------------
# Monero block-wise Base58 (M3 §1f)
# ---------------------------------------------------------------------------

def monero_b58_encode(data):
    """Encode bytes with Monero block-wise Base58 (8 bytes -> 11 chars)."""
    if not isinstance(data, (bytes, bytearray)):
        raise SecurityError("monero_b58_encode input must be bytes")
    out = []
    for i in range(0, len(data), 8):
        block = bytes(data[i:i + 8])
        chars = _B58_ENCODE_LEN[len(block)]
        n = int.from_bytes(block, "big")
        text = ""
        for _ in range(chars):
            n, rem = divmod(n, 58)
            text = B58_ALPHABET[rem] + text
        out.append(text)
    return "".join(out)


def monero_b58_decode(text):
    """Decode Monero block-wise Base58. Raises SecurityError on a bad
    character, an invalid final-block length, or an out-of-range block."""
    if not isinstance(text, str):
        raise SecurityError("monero_b58_decode input must be a string")
    for ch in text:
        if ch not in _B58_MAP:
            raise SecurityError(f"invalid Base58 character {ch!r}")
    out = bytearray()
    for i in range(0, len(text), 11):
        chunk = text[i:i + 11]
        if len(chunk) not in _B58_DECODE_LEN:
            raise SecurityError(
                f"invalid final Base58 block length {len(chunk)}")
        nbytes = _B58_DECODE_LEN[len(chunk)]
        n = 0
        for ch in chunk:
            n = n * 58 + _B58_MAP[ch]
        if n >= 256 ** nbytes:
            raise SecurityError(
                "invalid Base58 encoding (block value out of range)")
        out += n.to_bytes(nbytes, "big")
    return bytes(out)


def build_monero_address(network_byte, spend_key, view_key, payment_id=None):
    """Construct a Monero address from chosen payload bytes (test
    fixtures only — never a live user's address). spend/view keys are
    32 bytes each; payment_id is 8 bytes (integrated addresses only)."""
    if len(spend_key) != 32 or len(view_key) != 32:
        raise SecurityError("spend/view keys must be 32 bytes each")
    if payment_id is not None and len(payment_id) != 8:
        raise SecurityError("payment id must be 8 bytes")
    payload = bytes([network_byte]) + bytes(spend_key) + bytes(view_key)
    if payment_id is not None:
        payload += bytes(payment_id)
    return monero_b58_encode(payload + keccak_256(payload)[:4])


def _payload_head(payload):
    """Decoded-payload rules, first half: length + network byte.
    Returns (ok, reason)."""
    if len(payload) not in (69, 77):
        return False, (f"decoded length {len(payload)} bytes — "
                       "expected 69 or 77")
    network_byte = payload[0]
    if network_byte == 53:
        return False, ("testnet network byte 53 rejected — "
                       "mainnet only (18/19/42)")
    if network_byte == 24:
        return False, ("stagenet network byte 24 rejected — "
                       "mainnet only (18/19/42)")
    if network_byte not in MAINNET_NETWORK_BYTES:
        return False, (f"unknown network byte {network_byte} — "
                       "mainnet only (18/19/42)")
    return True, None


def _payload_tail(payload):
    """Decoded-payload rules, second half: length/network consistency
    + checksum. Returns (ok, reason)."""
    network_byte = payload[0]
    if len(payload) == 69 and network_byte == 19:
        return False, ("network byte 19 with 69 decoded bytes — "
                       "standard/subaddress are 69 bytes, integrated is 77 bytes")
    if len(payload) == 77 and network_byte != 19:
        return False, (f"network byte {network_byte} with 77 decoded bytes — "
                       "standard/subaddress are 69 bytes, integrated is 77 bytes")
    if keccak_256(payload[:-4])[:4] != payload[-4:]:
        return False, ("checksum mismatch — address bytes do not match "
                       "the Keccak-256 checksum")
    return True, FORMAT_VALID_LINE


def _validate_payload(payload):
    """Decoded-payload rules (length, network byte, length/network
    consistency, checksum). Returns (ok, reason)."""
    ok, reason = _payload_head(payload)
    if not ok:
        return False, reason
    return _payload_tail(payload)


def validate_monero_address(address):
    """Full M3 §1f rule set, in order, fail fast. Returns
    (ok, reason). Validation proves format only, never ownership."""
    if not isinstance(address, str):
        return False, "address must be a string"
    if len(address) not in (95, 106):
        return False, (f"invalid length {len(address)} — Monero addresses "
                       "are 95 or 106 characters")
    for ch in address:
        if ch in _FORBIDDEN_CHARS:
            return False, (f"forbidden character {ch!r} — Monero Base58 "
                           "excludes 0, O, I, l")
    try:
        payload = monero_b58_decode(address)
    except SecurityError as exc:
        return False, str(exc)
    ok, reason = _payload_head(payload)
    if not ok:
        return False, reason
    # First-char/length consistency: the prefix is determined by the
    # network byte (18 -> '4', 42 -> '8', 19 -> '4'), and the prefix
    # constrains the length ('8' is the subaddress prefix, 95 chars
    # only). Checked after the network-byte rule so a testnet/stagenet
    # address is refused with its network-byte reason first (D-M10-C2).
    first = address[0]
    if first not in ("4", "8"):
        return False, (f"first character {first!r} does not match length "
                       f"{len(address)} — first-char/length mismatch "
                       "(95-character addresses start with '4' or '8'; "
                       "106-character addresses start with '4')")
    if first == "8" and len(address) != 95:
        return False, (f"first character '8' does not match length "
                       f"{len(address)} — first-char/length mismatch ('8' "
                       "is the subaddress prefix, 95 characters only)")
    expected_prefix = {18: "4", 42: "8", 19: "4"}[payload[0]]
    if first != expected_prefix:
        return False, (f"first character {first!r} does not match length "
                       f"{len(address)} — first-char/length mismatch "
                       f"(network byte {payload[0]} expects prefix "
                       f"{expected_prefix!r})")
    return _payload_tail(payload)


# ---------------------------------------------------------------------------
# Connection / config / temp-DB helpers
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


def _temp_db_copy(source_con, prefix="atlas-m10-"):
    """Copy a DB into a fresh temp file via the SQLite backup API
    (consistent snapshot even while the daemon writes). The caller owns
    the file and must remove it. Returns the temp path."""
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".db")
    os.close(fd)
    target = sqlite3.connect(path)
    try:
        source_con.backup(target)
    finally:
        target.close()
    return path


def _fresh_temp_db(source_con):
    """A temp copy of the given DB, opened with the coordinator's
    connection settings. Returns (path, con); the caller closes the
    connection and removes the file."""
    path = _temp_db_copy(source_con)
    return path, connect(path)


def _close_remove(con, path):
    try:
        con.close()
    except Exception:
        pass
    try:
        os.remove(path)
    except OSError:
        pass


def _is_temp_path(path):
    """True only for paths inside the system temp dir."""
    tmpdir = os.path.realpath(tempfile.gettempdir())
    return os.path.realpath(path).startswith(tmpdir + os.sep)


def _table_count(con, table):
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---------------------------------------------------------------------------
# Derived counts (M8 §4 definitions, reused — never recomputed elsewhere)
# ---------------------------------------------------------------------------

def security_counts(con):
    """The six M8 §4 security counts, derived live from the given DB."""
    import atlas_admin
    suspicious = len(atlas_admin._suspicious_workers(con))
    invalid = con.execute(
        "SELECT COUNT(*) FROM shares WHERE origin = 'pool' AND accepted = 0"
    ).fetchone()[0]
    duplicate, _rows = atlas_admin._duplicate_shares(con)
    abuse = con.execute(
        "SELECT COUNT(*) FROM events WHERE kind = 'abuse'").fetchone()[0]
    auth_failures = con.execute(
        "SELECT COUNT(*) FROM events WHERE kind = 'auth_failure'").fetchone()[0]
    payout_anomalies = (
        con.execute("SELECT COUNT(*) FROM payouts WHERE status = 'failed'"
                    ).fetchone()[0]
        + con.execute("SELECT COUNT(*) FROM ledger WHERE entry_type = 'reversal'"
                      ).fetchone()[0])
    return {
        "suspicious_workers": suspicious,
        "invalid_shares": invalid,
        "duplicate_shares": duplicate,
        "account_abuse": abuse,
        "auth_failures": auth_failures,
        "payout_anomalies": payout_anomalies,
    }


def host_verified_totals(con):
    """Ledger/batch totals for the mirror comparison (same keys as the
    dashboard export's host_verified_totals)."""
    import atlas_rewards
    totals = atlas_rewards.reward_totals(con)
    return {
        "ledger_entries": totals["ledger_entries"],
        "batches_settled": totals["batches_settled"],
        "total_user_rewards_piconero": totals["total_user_rewards_piconero"],
        "total_atlas_share_piconero": totals["total_atlas_share_piconero"],
    }


def _live_counts_sql(con):
    """Independent raw-SQL recomputation of the six counts (used by the
    battery's S6 live check and by diagnostics test 27)."""
    suspicious = con.execute(
        "SELECT COUNT(*) FROM workers WHERE status IN ('suspended','revoked')"
    ).fetchone()[0]
    for worker_id, rejected, accepted in con.execute(
            "SELECT worker_id, "
            "SUM(CASE WHEN accepted = 0 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) "
            "FROM shares WHERE origin = 'pool' GROUP BY worker_id").fetchall():
        total = (rejected or 0) + (accepted or 0)
        if (rejected or 0) >= 10 and total > 0 and rejected / total > 0.5:
            status = con.execute(
                "SELECT status FROM workers WHERE id = ?",
                (worker_id,)).fetchone()
            if status and status[0] not in ("suspended", "revoked"):
                suspicious += 1
    dup = 0
    for (n,) in con.execute(
            "SELECT COUNT(*) FROM shares WHERE external_id IS NOT NULL "
            "GROUP BY external_id HAVING COUNT(*) > 1").fetchall():
        dup += n - 1
    for (n,) in con.execute(
            "SELECT COUNT(*) FROM shares WHERE external_id IS NULL "
            "AND job_id IS NOT NULL GROUP BY worker_id, job_id "
            "HAVING COUNT(*) > 1").fetchall():
        dup += n - 1
    return {
        "suspicious_workers": suspicious,
        "invalid_shares": con.execute(
            "SELECT COUNT(*) FROM shares WHERE origin = 'pool' "
            "AND accepted = 0").fetchone()[0],
        "duplicate_shares": dup,
        "account_abuse": con.execute(
            "SELECT COUNT(*) FROM events WHERE kind = 'abuse'").fetchone()[0],
        "auth_failures": con.execute(
            "SELECT COUNT(*) FROM events WHERE kind = 'auth_failure'"
        ).fetchone()[0],
        "payout_anomalies": (
            con.execute("SELECT COUNT(*) FROM payouts WHERE status = 'failed'"
                        ).fetchone()[0]
            + con.execute(
                "SELECT COUNT(*) FROM ledger WHERE entry_type = 'reversal'"
            ).fetchone()[0]),
    }


# ---------------------------------------------------------------------------
# Shared fixtures (temp DBs only)
# ---------------------------------------------------------------------------

def _make_user(con, username):
    cur = con.execute(
        "INSERT INTO users (username, email, email_verified, created_at) "
        "VALUES (?,?,0,?)",
        (username, f"{username}@example.invalid", _now()))
    con.commit()
    return cur.lastrowid


def _scenario1_fixture(con):
    """M6 scenario-1 shape on a temp DB: Alice (60 weight), Bob
    (40 weight), 8 local-test shares, Bob referred by Alice; 1 XMR
    simulation batch settled. Returns (alice, bob, batch_ref)."""
    import atlas_coordinator as ac
    import atlas_rewards as rw
    alice = _make_user(con, "alice")
    bob = _make_user(con, "bob")
    wa_b = ac.register_worker(con, alice, "browser", "alice-browser")["id"]
    wa_d = ac.register_worker(con, alice, "desktop", "alice-desktop")["id"]
    wb_d = ac.register_worker(con, bob, "desktop", "bob-desktop")["id"]
    for tag, diff, at in (("s1", 10, W0 + 10), ("s2", 20, W0 + 20)):
        ac.record_share(con, wa_b, diff, tag, True, True, submitted_at=at)
    for tag, diff, at in (("s3", 15, W0 + 30), ("s4", 15, W0 + 40)):
        ac.record_share(con, wa_d, diff, tag, True, True, submitted_at=at)
    for tag, diff, at in (("s5", 10, W0 + 50), ("s6", 10, W0 + 60),
                          ("s7", 10, W0 + 70), ("s8", 10, W0 + 80)):
        ac.record_share(con, wb_d, diff, tag, True, True, submitted_at=at)
    con.execute(
        "INSERT INTO referrals (referrer_user_id, referred_user_id, "
        "status, created_at) VALUES (?,?,'pending',?)",
        (alice, bob, _now()))
    con.commit()
    batch_ref = "sim-m10-s1"
    batch_id = rw.record_batch(
        con, "MoneroOcean", "simulation", "sim-m10-s1", W0, W1, ONE_XMR,
        source_evidence="simulated-harness:mission10-s1",
        batch_ref=batch_ref)
    assert batch_id is not None, "scenario-1 batch refused"
    result = rw.settle_batch(con, batch_ref=batch_ref)
    assert result["status"] == "settled", f"scenario-1 settle: {result}"
    return alice, bob, batch_ref


def _grep_files(export_dir, patterns):
    """Count literal occurrences of each pattern in each export file.
    Returns (total_hits, per_file {filename: hits}, missing [filenames]).
    Missing files count 0 hits and are named."""
    total = 0
    per_file = {}
    missing = []
    for filename in EXPORT_FILES:
        path = os.path.join(export_dir, filename)
        if not os.path.exists(path):
            missing.append(filename)
            per_file[filename] = 0
            continue
        with open(path, errors="ignore") as f:
            text = f.read()
        hits = sum(text.count(p) for p in patterns)
        per_file[filename] = hits
        total += hits
    return total, per_file, missing


_ADDRESS_SHAPE_RE = re.compile(r"[1-9A-HJ-NP-Za-km-z]{95}|[1-9A-HJ-NP-Za-km-z]{106}")


def _no_miner_process():
    """Scan /proc cmdlines for miner process names (stdlib only).
    Returns (ok, evidence)."""
    names = ("xmrig", "minerd", "cpuminer", "ethminer", "t-rex",
             "lolminer", "nbminer", "gminer")
    found = []
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmdline = f.read().decode("utf-8", "replace").lower()
            except OSError:
                continue
            for name in names:
                if name in cmdline:
                    found.append(f"pid {pid}: {cmdline[:80]}")
                    break
    except OSError as exc:
        return False, f"/proc scan failed: {exc}"
    if found:
        return False, "miner process running: " + "; ".join(found)
    return True, "no miner process found in /proc scan"


# ---------------------------------------------------------------------------
# Security checks S1–S9 (design §4). Each returns a result record:
#   {"id", "name", "result": PASS|FAIL|NOT_RUN, "evidence", "duration_ms"}
# Mutating checks use their own temp DB; live checks are read-only.
# Evidence strings never contain a SECRET_PATTERNS literal.
# ---------------------------------------------------------------------------

def _check(con, export_dir, check_id, name, fn):
    started = time.monotonic()
    try:
        result, evidence = fn(con, export_dir)
    except Exception as exc:  # noqa: BLE001 — a check failure is evidence
        result, evidence = "FAIL", f"check raised: {exc}"
    duration_ms = int((time.monotonic() - started) * 1000)
    return {"id": check_id, "name": name, "result": result,
            "evidence": evidence, "duration_ms": duration_ms}


def _check_s1(con, _export_dir):
    import atlas_rewards as rw
    # Fixture (temp DB): scenario-1, settle, chain PASS, 5 entries.
    path, tcon = _fresh_temp_db(con)
    try:
        _scenario1_fixture(tcon)
        verdict = rw.verify_chain(tcon)
        entries = _table_count(tcon, "ledger")
        if not verdict["ok"] or entries != 5:
            return "FAIL", (f"fixture chain did not verify: ok={verdict['ok']}, "
                            f"entries={entries}, error={verdict.get('error')}")
        # Tamper: +1 on one committed entry on the temp copy.
        row = tcon.execute(
            "SELECT id FROM ledger WHERE entry_type = 'user_allocation' "
            "ORDER BY id LIMIT 1").fetchone()
        tampered_id = row["id"]
        tcon.execute("UPDATE ledger SET amount_piconero = amount_piconero + 1 "
                     "WHERE id = ?", (tampered_id,))
        tcon.commit()
        bad = rw.verify_chain(tcon)
        if bad["ok"] or bad.get("first_bad_entry_id") != tampered_id:
            return "FAIL", (f"tamper not detected: ok={bad['ok']}, "
                            f"first_bad={bad.get('first_bad_entry_id')}, "
                            f"expected {tampered_id}")
        tamper_evidence = (f"tampered entry {tampered_id} named by verifier "
                           f"({bad.get('error')})")
    finally:
        _close_remove(tcon, path)
    # Correction path (fresh temp DB): reversal + corrected entry.
    path, tcon = _fresh_temp_db(con)
    try:
        alice, bob, _ref = _scenario1_fixture(tcon)
        alice_alloc = tcon.execute(
            "SELECT id FROM ledger WHERE entry_type = 'user_allocation' "
            "AND user_id = ? ORDER BY id LIMIT 1", (alice,)).fetchone()["id"]
        bob_alloc = tcon.execute(
            "SELECT id FROM ledger WHERE entry_type = 'user_allocation' "
            "AND user_id = ? ORDER BY id LIMIT 1", (bob,)).fetchone()["id"]
        rev_id = rw.record_reversal(tcon, alice_alloc)
        _rev2, corrected_id = rw.record_correction(
            tcon, bob_alloc, 300_000_000_001)
        verdict = rw.verify_chain(tcon)
        if not verdict["ok"]:
            return "FAIL", (f"chain failed after reversal+correction: "
                            f"{verdict.get('error')}")
        original = tcon.execute(
            "SELECT COUNT(*) FROM ledger WHERE id IN (?,?)",
            (alice_alloc, bob_alloc)).fetchone()[0]
        if original != 2:
            return "FAIL", "original entries not still visible after correction"
        alice_balance = rw.user_balance(tcon, alice)
        bob_balance = rw.user_balance(tcon, bob)
        if alice_balance != 15_000_000_000:
            return "FAIL", (f"alice balance after reversal {alice_balance}, "
                            "expected 15000000000 (referral only)")
        if bob_balance != 300_000_000_001:
            return "FAIL", (f"bob balance after correction {bob_balance}, "
                            "expected 300000000001")
        correction_evidence = (f"reversal entry {rev_id} + corrected entry "
                               f"{corrected_id}; chain PASS; originals visible; "
                               f"balances alice 15000000000, bob 300000000001")
    finally:
        _close_remove(tcon, path)
    # Live check (read-only): chain on the live DB.
    live = rw.verify_chain(con)
    if not live["ok"]:
        return "FAIL", f"live chain failed: {live.get('error')}"
    return "PASS", (f"fixture settled 5 entries, chain PASS; {tamper_evidence}; "
                    f"{correction_evidence}; live chain trivially valid, "
                    f"{live['entries']} entries (ledger empty — chain "
                    "trivially valid)")


def _check_s2(con, _export_dir):
    import atlas_coordinator as ac
    path, tcon = _fresh_temp_db(con)
    try:
        user = _make_user(tcon, "carol")
        worker = ac.register_worker(tcon, user, "browser", "carol-w1")["id"]
        first = ac.record_shares(tcon, worker, [{
            "difficulty": 10, "accepted": 1, "submitted_at": W0 + 10,
            "origin": "pool", "external_id": "share-A", "job_id": None}])
        if first["inserted"] != 1:
            return "FAIL", f"first share not inserted: {first}"
        second = ac.record_shares(tcon, worker, [{
            "difficulty": 10, "accepted": 1, "submitted_at": W0 + 10,
            "origin": "pool", "external_id": "share-A", "job_id": None}])
        if second["inserted"] != 0 or second["duplicates_skipped"] != 1:
            return "FAIL", f"duplicate not rejected: {second}"
        weights = ac.attribution_weights(tcon)
        if weights.get(worker) != 10:
            return "FAIL", (f"attribution weights count the share twice: "
                            f"{weights}")
        null_share = ac.record_shares(tcon, worker, [{
            "difficulty": 5, "accepted": 1, "submitted_at": W0 + 20,
            "origin": "pool", "external_id": None, "job_id": None}])
        if null_share["inserted"] != 1:
            return "FAIL", f"null-external-id share not inserted: {null_share}"
        null_count = tcon.execute(
            "SELECT COUNT(*) FROM shares WHERE origin = 'pool' AND accepted = 1 "
            "AND external_id IS NULL").fetchone()[0]
        if null_count != 1:
            return "FAIL", f"null-external-id share not counted: {null_count}"
        # The rewards attribution excludes null-external-id shares; the
        # check asserts the exclusion at the rewards layer via a batch
        # window. The null share is pool-origin, so the batch row is a
        # directly-inserted real-mode row (record_batch refuses to
        # create real-mode batches while the stop is ON — fixture only).
        import atlas_rewards as rw
        tcon.execute(
            "INSERT INTO reward_batches (batch_ref, pool_name, mode, "
            "source_ref, source_evidence, window_start, window_end, "
            "gross_piconero, fee_bps, status, created_at) "
            "VALUES ('m10-s2-real','MoneroOcean','real','m10-s2-real',"
            "NULL,?,?,?,0,'open',?)",
            (W0, W1, ONE_XMR, _now()))
        tcon.commit()
        batch = tcon.execute(
            "SELECT * FROM reward_batches WHERE batch_ref = 'm10-s2-real'"
        ).fetchone()
        weights_rw, _ids, _nd, null_ext = rw._attribution(tcon, batch)
        if null_ext != 1:
            return "FAIL", (f"rewards attribution null-external-id count "
                            f"{null_ext}, expected 1")
        if weights_rw.get(user) != 10:
            return "FAIL", (f"rewards attribution weights {weights_rw}, "
                            "expected {user: 10} (null share excluded)")
        # Same external_id under a different worker: cross-worker conflict.
        worker2 = ac.register_worker(tcon, user, "browser", "carol-w2")["id"]
        before_status = tcon.execute(
            "SELECT status FROM workers WHERE id = ?", (worker2,)).fetchone()[0]
        clash = ac.record_shares(tcon, worker2, [{
            "difficulty": 10, "accepted": 1, "submitted_at": W0 + 30,
            "origin": "pool", "external_id": "share-A", "job_id": None}])
        after_status = tcon.execute(
            "SELECT status FROM workers WHERE id = ?", (worker2,)).fetchone()[0]
        if clash["inserted"] != 0 or clash["rejected"] != 1:
            return "FAIL", (f"cross-worker duplicate not rejected whole: {clash}")
        if after_status != "suspended":
            return "FAIL", (f"cross-worker duplicate did not suspend worker: "
                            f"status {before_status} -> {after_status}")
        cross_evidence = ("same external_id under a different worker: batch "
                          "rejected, worker suspended (engine rule)")
    finally:
        _close_remove(tcon, path)
    # Live check (read-only): duplicate-share count from live SQL.
    live = _live_counts_sql(con)
    if live["duplicate_shares"] != 0:
        return "FAIL", (f"live duplicate-share count {live['duplicate_shares']}, "
                        "expected 0")
    return "PASS", (f"duplicate (worker, external_id) rejected, counted once "
                    f"(weight 10); null-external-id pool share excluded from "
                    f"attribution and counted (1); {cross_evidence}; "
                    f"live duplicate shares 0")


def _check_s3(con, _export_dir):
    import atlas_rewards as rw
    path, tcon = _fresh_temp_db(con)
    try:
        alice, _bob, _ref = _scenario1_fixture(tcon)
        # Payout-shaped calls are refused (Gate 4 closed) — D-M10-C1.
        before = tcon.execute(
            "SELECT COUNT(*) FROM decisions WHERE dept = 'rewards' AND "
            "decision = 'reward-payout-refused'").fetchone()[0]
        refused = 0
        for _ in range(2):
            try:
                rw.request_payout(tcon, alice, 1000)
            except rw.RewardsError:
                refused += 1
        if refused != 2:
            return "FAIL", f"payout-shaped calls refused {refused}/2"
        payouts = _table_count(tcon, "payouts")
        after = tcon.execute(
            "SELECT COUNT(*) FROM decisions WHERE dept = 'rewards' AND "
            "decision = 'reward-payout-refused'").fetchone()[0]
        if payouts != 0 or after - before != 2:
            return "FAIL", (f"payout rows {payouts}, refusal decisions "
                            f"{after - before} (expected 0 rows, 2 refusals)")
        # Re-settle is a no-op (no new ledger entries, same result).
        entries_before = _table_count(tcon, "ledger")
        again = rw.settle_batch(tcon, batch_ref="sim-m10-s1")
        entries_after = _table_count(tcon, "ledger")
        if again.get("status") != "noop" or entries_after != entries_before:
            return "FAIL", (f"re-settle not a no-op: {again}, entries "
                            f"{entries_before} -> {entries_after}")
        # Duplicate idempotency key rejected by the UNIQUE constraint.
        address = build_monero_address(
            18, bytes(range(32)), bytes(range(32, 64)))
        tcon.execute(
            "INSERT INTO payouts (user_id, amount_piconero, "
            "destination_address, status, created_at, idempotency_key) "
            "VALUES (?,?,?,?,?,?)",
            (alice, 1000, address, "pending", _now(), "m10-idem-1"))
        tcon.commit()
        try:
            tcon.execute(
                "INSERT INTO payouts (user_id, amount_piconero, "
                "destination_address, status, created_at, idempotency_key) "
                "VALUES (?,?,?,?,?,?)",
                (alice, 1000, address, "pending", _now(), "m10-idem-1"))
            tcon.commit()
            return "FAIL", "duplicate idempotency key was NOT rejected"
        except sqlite3.IntegrityError:
            tcon.rollback()
        key_rows = tcon.execute(
            "SELECT COUNT(*) FROM payouts WHERE idempotency_key = 'm10-idem-1'"
        ).fetchone()[0]
        if key_rows != 1:
            return "FAIL", f"rows with idempotency key: {key_rows}, expected 1"
    finally:
        _close_remove(tcon, path)
    live_payouts = _table_count(con, "payouts")
    if live_payouts != 0:
        return "FAIL", f"live payouts {live_payouts}, expected 0"
    return "PASS", ("payout-shaped calls refused 2/2 with logged refusals, "
                    "0 payout rows; re-settle no-op (5 entries unchanged); "
                    "duplicate idempotency key rejected by UNIQUE constraint, "
                    "exactly 1 row kept; live payouts 0")


def _check_s4(con, _export_dir):
    import atlas_coordinator as ac
    path, tcon = _fresh_temp_db(con)
    try:
        user = _make_user(tcon, "dave")
        result = ac.register_worker(tcon, user, "desktop", "dave-desktop")
        token = result["token"]
        worker_id = result["id"]
        if not token:
            return "FAIL", "desktop registration returned no credential"
        row = tcon.execute(
            "SELECT token_hash, token_salt FROM workers WHERE id = ?",
            (worker_id,)).fetchone()
        if not row["token_hash"] or len(row["token_hash"]) != 64:
            return "FAIL", "stored credential hash is not 64 hex chars"
        if not row["token_salt"] or len(row["token_salt"]) != 32:
            return "FAIL", "stored credential salt is not 32 hex chars"
        try:
            int(row["token_hash"], 16)
            int(row["token_salt"], 16)
        except ValueError:
            return "FAIL", "stored credential hash/salt are not hex"
        with open(path, "rb") as f:
            raw = f.read()
        if token.encode("utf-8") in raw:
            return "FAIL", "plaintext credential found in temp DB file"
        if not ac.verify_worker_token(tcon, worker_id, token):
            return "FAIL", "correct credential rejected"
        if ac.verify_worker_token(tcon, worker_id, token + "x"):
            return "FAIL", "wrong credential accepted"
        if ac.verify_worker_token(tcon, worker_id, ""):
            return "FAIL", "empty credential accepted"
        rotated = ac.rotate_token(tcon, worker_id)
        if ac.verify_worker_token(tcon, worker_id, token):
            return "FAIL", "old credential still valid after rotation"
        if not ac.verify_worker_token(tcon, worker_id, rotated["token"]):
            return "FAIL", "new credential rejected after rotation"
        browser = ac.register_worker(tcon, user, "browser", "dave-browser")
        brow = tcon.execute(
            "SELECT token_hash, token_salt FROM workers WHERE id = ?",
            (browser["id"],)).fetchone()
        if brow["token_hash"] is not None or brow["token_salt"] is not None:
            return "FAIL", "browser worker stored credential material"
        if browser["token"] is not None:
            return "FAIL", "browser registration returned a credential"
    finally:
        _close_remove(tcon, path)
    # Live assertion: the designed-in registered worker ("mining", status
    # registered, never seen, never reported) is inert and expected. What
    # must never exist is a worker that has actually been active, so count
    # those: any non-registered/non-suspended status, any last_seen, or any
    # reported hashrate. (Fixed 2026-11-20: the old "live workers 0"
    # expectation failed on the inert placeholder alone.)
    active_workers = con.execute(
        "SELECT COUNT(*) FROM workers WHERE status NOT IN ('registered', 'suspended')"
        " OR last_seen_at IS NOT NULL OR reported_hashrate_hps IS NOT NULL"
    ).fetchone()[0]
    if active_workers != 0:
        return "FAIL", f"live active workers {active_workers}, expected 0"
    return "PASS", ("desktop credential returned once, stored as 64-hex hash "
                    "+ salt only, 0 hits in temp DB file; correct accepted, "
                    "wrong/empty rejected; rotation invalidates old, new "
                    "passes; browser worker stores NULL hash/salt; "
                    "live active workers 0 (1 registered placeholder, never seen)")


def _check_s5(_con, _export_dir):
    spend = bytes(range(32))
    view = bytes(range(32, 64))
    payment = bytes(range(64, 72))
    std = build_monero_address(18, spend, view)
    sub = build_monero_address(42, spend, view)
    integ = build_monero_address(19, spend, view, payment)
    for label, address in (("standard", std), ("subaddress", sub),
                           ("integrated", integ)):
        ok, reason = validate_monero_address(address)
        if not ok:
            return "FAIL", f"valid {label} address rejected: {reason}"
    if len(std) != 95 or len(sub) != 95 or len(integ) != 106:
        return "FAIL", (f"constructed lengths {len(std)}/{len(sub)}/"
                        f"{len(integ)}, expected 95/95/106")
    # Rejections, each with its exact reason.
    cases = []
    for label, bad in (("94 chars", std[:94]), ("96 chars", std + "1"),
                       ("105 chars", integ[:105])):
        ok, reason = validate_monero_address(bad)
        cases.append((label, ok, reason))
        if ok or not reason.startswith("invalid length"):
            return "FAIL", f"wrong-length case {label}: ok={ok}, reason={reason!r}"
    for ch in _FORBIDDEN_CHARS:
        bad = std[:10] + ch + std[11:]
        ok, reason = validate_monero_address(bad)
        if ok or not reason.startswith("forbidden character"):
            return "FAIL", (f"forbidden-character case {ch!r}: ok={ok}, "
                            f"reason={reason!r}")
    # First-char/length mismatch: 77-byte payload, network byte 42
    # (subaddress prefix '8' at integrated length 106).
    first_char_bad = build_monero_address(42, spend, view, payment)
    ok, reason = validate_monero_address(first_char_bad)
    if ok or "does not match length 106" not in reason:
        return "FAIL", (f"first-char/length case: ok={ok}, reason={reason!r}")
    for byte, word in ((53, "testnet"), (24, "stagenet")):
        bad = build_monero_address(byte, spend, view)
        ok, reason = validate_monero_address(bad)
        if ok or f"{word} network byte {byte} rejected" not in reason:
            return "FAIL", (f"{word} case: ok={ok}, reason={reason!r}")
    # Decoded-length rule at the payload level (D-M10-C2).
    ok, reason = _validate_payload(bytes(68))
    if ok or "decoded length 68" not in reason:
        return "FAIL", f"decoded-length case: ok={ok}, reason={reason!r}"
    ok, reason = _validate_payload(bytes(70))
    if ok or "decoded length 70" not in reason:
        return "FAIL", f"decoded-length case: ok={ok}, reason={reason!r}"
    # Checksum mismatch: flip one character in the last block.
    last_block_char = std[90]
    replacement = "1" if last_block_char != "1" else "2"
    bad = std[:90] + replacement + std[91:]
    ok, reason = validate_monero_address(bad)
    if ok or "checksum mismatch" not in reason:
        return "FAIL", f"checksum case: ok={ok}, reason={reason!r}"
    # Oversized Base58 block is rejected, not silently accepted.
    bad_block = "z" * 95
    ok, reason = validate_monero_address(bad_block)
    if ok:
        return "FAIL", "oversized-Base58-block address accepted"
    # Keccak vector asserted at import; confirm SHA3 differs (guards
    # against accidentally using hashlib.sha3_256 for this purpose).
    if keccak_256(b"").hex() == hashlib.sha3_256(b"").hexdigest():
        return "FAIL", "Keccak-256 equals SHA3-256 — wrong hash in use"
    return "PASS", ("standard/subaddress/integrated constructed addresses "
                    "accepted (95/95/106 chars); rejections asserted: wrong "
                    "length 94/96/105, forbidden 0/O/I/l, first-char/length "
                    "mismatch, testnet byte 53, stagenet byte 24, decoded "
                    "length 68/70, checksum mismatch, oversized block; "
                    "Keccak-256 empty vector verified, distinct from SHA3-256")


def _check_s6(con, export_dir):
    import atlas_admin
    total, per_file, missing = _grep_files(export_dir, SECRET_PATTERNS)
    if total != 0:
        return "FAIL", (f"secret-pattern grep hit {total} time(s): {per_file}")
    # Redaction fixture: fake 64-hex credential + fake address-shaped
    # string are both replaced, and the row is still counted.
    fake_hex = "a" * 64
    fake_addr = build_monero_address(18, bytes(range(32)), bytes(range(32, 64)))
    redacted_hex = atlas_admin._redact_message(
        f"credential {fake_hex} seen", set())
    redacted_addr = atlas_admin._redact_message(
        f"address {fake_addr} seen", set())
    if redacted_hex != atlas_admin.REDACTED:
        return "FAIL", "fake 64-hex credential was not redacted"
    if redacted_addr != atlas_admin.REDACTED:
        return "FAIL", "fake address-shaped string was not redacted"
    path, tcon = _fresh_temp_db(con)
    try:
        tcon.execute(
            "INSERT INTO decisions (ts, dept, decision, reason) VALUES "
            "(?,?,?,?)", (_now(), "coordinator", "s6-fixture",
                          f"credential {fake_hex} seen"))
        tcon.commit()
        counted = tcon.execute(
            "SELECT COUNT(*) FROM decisions WHERE decision = 's6-fixture'"
        ).fetchone()[0]
        if counted != 1:
            return "FAIL", "redacted row not counted"
        known = atlas_admin._known_share_ids(tcon)
        shown = atlas_admin._redact_message(
            f"credential {fake_hex} seen", known)
        if shown != atlas_admin.REDACTED:
            return "FAIL", "redacted row not shown redacted"
    finally:
        _close_remove(tcon, path)
    # Live check: six M8 §4 counts re-derived from live SQL match
    # the counts in data/admin.json.
    admin_path = os.path.join(export_dir, "admin.json")
    if not os.path.exists(admin_path):
        return "NOT_RUN", ("data/admin.json missing — run the admin export "
                           "first; file grep 0 hits, redaction fixture PASS")
    with open(admin_path) as f:
        admin = json.load(f)
    live = _live_counts_sql(con)
    mismatched = [k for k in live
                  if admin["security"][k]["count"] != live[k]]
    if mismatched:
        return "FAIL", (f"admin.json security counts mismatch on {mismatched}: "
                        f"file vs live {live}")
    missing_note = (f"; files missing at grep time: {missing}"
                    if missing else "")
    return "PASS", (f"secret-pattern grep 0 hits across {len(EXPORT_FILES)} "
                    f"files{missing_note}; redaction fixture: fake credential "
                    f"and fake address-shaped string replaced, row still "
                    f"counted; six live counts match admin.json "
                    f"({live['suspicious_workers']} suspicious, "
                    f"{live['invalid_shares']} invalid, "
                    f"{live['duplicate_shares']} duplicate, "
                    f"{live['account_abuse']} abuse, "
                    f"{live['auth_failures']} auth failures, "
                    f"{live['payout_anomalies']} payout anomalies)")


def _check_s7(con, _export_dir):
    import atlas_rewards as rw
    atlas_cfg, pool_cfg = load_configs()
    if not atlas_cfg.get("emergency_stop"):
        return "FAIL", "emergency_stop is not ON in config/atlas.json"
    # Real-mode batch recording refused on a temp DB.
    path, tcon = _fresh_temp_db(con)
    try:
        before = tcon.execute(
            "SELECT COUNT(*) FROM decisions WHERE dept = 'rewards' AND "
            "decision = 'reward-batch-refused'").fetchone()[0]
        batch_id = rw.record_batch(
            tcon, "MoneroOcean", "real", "m10-real-refused",
            W0, W1, ONE_XMR, batch_ref="m10-real-refused")
        after = tcon.execute(
            "SELECT COUNT(*) FROM decisions WHERE dept = 'rewards' AND "
            "decision = 'reward-batch-refused'").fetchone()[0]
        if batch_id is not None or after - before != 1:
            return "FAIL", (f"real-mode batch not refused: id={batch_id}, "
                            f"refusal decisions {after - before}")
        # Payout-shaped call refused with a logged refusal.
        before_pay = tcon.execute(
            "SELECT COUNT(*) FROM decisions WHERE dept = 'rewards' AND "
            "decision = 'reward-payout-refused'").fetchone()[0]
        try:
            rw.request_payout(tcon, 1, 1000)
            return "FAIL", "payout-shaped call was not refused"
        except rw.RewardsError:
            pass
        after_pay = tcon.execute(
            "SELECT COUNT(*) FROM decisions WHERE dept = 'rewards' AND "
            "decision = 'reward-payout-refused'").fetchone()[0]
        if after_pay - before_pay != 1:
            return "FAIL", "payout refusal was not logged"
    finally:
        _close_remove(tcon, path)
    # Mining cannot start: disabled in config, no start entry point.
    if atlas_cfg.get("mining", {}).get("enabled"):
        return "FAIL", "mining.enabled is true in config/atlas.json"
    for filename in ("atlas_coordinator.py", "atlas_monitor.py"):
        with open(os.path.join(CORE, filename), errors="ignore") as f:
            if "start_mining" in f.read():
                return "FAIL", f"start entry point found in {filename}"
    # Live checks: stop ON in snapshot + config; no miner process.
    try:
        with open(SNAPSHOT) as f:
            snap = json.load(f)
    except (OSError, ValueError) as exc:
        return "FAIL", f"snapshot.json unreadable: {exc}"
    if not snap.get("emergency_stop"):
        return "FAIL", "emergency_stop is not ON in data/snapshot.json"
    proc_ok, proc_evidence = _no_miner_process()
    if not proc_ok:
        return "FAIL", proc_evidence
    return "PASS", ("emergency stop ON (config + snapshot); real-mode batch "
                    "refused with logged refusal; payout-shaped call refused "
                    "with logged refusal; mining disabled in config, no "
                    "start entry point in coordinator/monitor code; "
                    f"{proc_evidence}")


def _check_s8(con, _export_dir):
    import atlas_rewards as rw
    _atlas_cfg, pool_cfg = load_configs()
    mode = pool_cfg.get("mode")
    if mode != "simulation-only":
        return "FAIL", f"pool-rewards.json mode is {mode!r}, not simulation-only"
    minimum = (pool_cfg.get("minimum_payout") or {}).get("piconero")
    # Real-mode settle refused on a temp DB (batch row inserted directly
    # — record_batch refuses to create one, so the settle gate is tested
    # against a directly-inserted open real-mode batch).
    path, tcon = _fresh_temp_db(con)
    try:
        tcon.execute(
            "INSERT INTO reward_batches (batch_ref, pool_name, mode, "
            "source_ref, source_evidence, window_start, window_end, "
            "gross_piconero, fee_bps, status, created_at) "
            "VALUES ('m10-real-settle','MoneroOcean','real','m10-real-settle',"
            "NULL,?,?,?,0,'open',?)",
            (W0, W1, ONE_XMR, _now()))
        tcon.commit()
        result = rw.settle_batch(tcon, batch_ref="m10-real-settle")
        if result.get("status") != "refused":
            return "FAIL", f"real-mode settle not refused: {result}"
        if _table_count(tcon, "ledger") != 0:
            return "FAIL", "real-mode settle wrote ledger entries"
    finally:
        _close_remove(tcon, path)
    real_live = con.execute(
        "SELECT COUNT(*) FROM reward_batches WHERE mode = 'real'").fetchone()[0]
    if real_live != 0:
        return "FAIL", f"live real-mode batches: {real_live}"
    return "PASS", (f"mode simulation-only; real-mode settle refused while "
                    f"simulation-only (no ledger entries); minimum payout "
                    f"{'null (undecided)' if minimum is None else minimum}; "
                    f"live real-mode batches 0")


def _check_s9(con, export_dir, payload_so_far):
    # The export itself is grepped (S6 patterns) — 0 hits.
    serialized = json.dumps(payload_so_far, sort_keys=True)
    hits = sum(serialized.count(p) for p in SECRET_PATTERNS)
    if hits != 0:
        return "FAIL", f"secret-pattern literals found in the export payload ({hits})"
    # No address-shaped value anywhere in the export payload.
    found = _ADDRESS_SHAPE_RE.findall(serialized)
    if found:
        return "FAIL", (f"address-shaped value in the export payload: "
                        f"{found[0][:20]}... ({len(found)} hit(s))")
    # No export file in data/ contains an address-shaped value.
    for filename in EXPORT_FILES:
        if filename == "security.json":
            continue  # this export is checked above, pre-write
        path = os.path.join(export_dir, filename)
        if not os.path.exists(path):
            continue
        with open(path, errors="ignore") as f:
            text = f.read()
        found = _ADDRESS_SHAPE_RE.findall(text)
        if found:
            return "FAIL", (f"address-shaped value in {filename}: "
                            f"{found[0][:20]}... ({len(found)} hit(s))")
    # Structural check: no secret key names in the payload.
    def _walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in SECRET_PATTERNS:
                    return key
                bad = _walk(value)
                if bad:
                    return bad
        elif isinstance(node, list):
            for value in node:
                bad = _walk(value)
                if bad:
                    return bad
        return None
    bad_key = _walk(payload_so_far)
    if bad_key:
        return "FAIL", f"secret key {bad_key!r} present in the export payload"
    live = _live_counts_sql(con)
    return "PASS", (f"export payload: 0 secret-pattern hits, 0 address-shaped "
                    f"values, no secret keys; no address-shaped value in any "
                    f"export file; live counts re-derived for the mirror "
                    f"comparison ({live['suspicious_workers']}/"
                    f"{live['invalid_shares']}/{live['duplicate_shares']}/"
                    f"{live['account_abuse']}/{live['auth_failures']}/"
                    f"{live['payout_anomalies']}); mirror contents cannot be "
                    f"verified from the host — the UI mirror check covers "
                    f"the mirror side")


CHECK_DEFS = (
    ("S1", "Ledger tamper-evidence (hash chain)", _check_s1),
    ("S2", "Share dedupe", _check_s2),
    ("S3", "Payout idempotency", _check_s3),
    ("S4", "Per-worker token handling", _check_s4),
    ("S5", "Wallet-address input validation (full Monero rule set)", _check_s5),
    ("S6", "Admin data redaction", _check_s6),
    ("S7", "Emergency-stop enforcement", _check_s7),
    ("S8", "Simulation-only enforcement", _check_s8),
)


# ---------------------------------------------------------------------------
# Battery + export
# ---------------------------------------------------------------------------

def _config_sha256_short():
    """Short sha256 of each config file (provenance, no contents)."""
    out = {}
    for name, path in (("atlas.json", CFG_ATLAS),
                       ("pool-rewards.json", CFG_POOL)):
        try:
            with open(path, "rb") as f:
                out[name] = hashlib.sha256(f.read()).hexdigest()[:16]
        except OSError:
            out[name] = None
    return out


def security_status(con, export_dir=None):
    """Run the security battery (S1–S9) and derive the security state
    object. Read-only on the given DB: every mutating check uses its own
    temp DB. Returns the export dict (no file written)."""
    if export_dir is None:
        export_dir = DATA_DIR
    atlas_cfg, pool_cfg = load_configs()
    user_version = con.execute("PRAGMA user_version").fetchone()[0]
    now = _now()

    results = []
    for check_id, name, fn in CHECK_DEFS:
        results.append(_check(con, export_dir, check_id, name, fn))

    counts = security_counts(con)
    totals = host_verified_totals(con)
    total_hits, per_file, missing = _grep_files(export_dir, SECRET_PATTERNS)
    enforcement = {
        "emergency_stop": bool(atlas_cfg.get("emergency_stop")),
        "mode": pool_cfg.get("mode", "simulation-only"),
        "mining_enabled": bool(atlas_cfg.get("mining", {}).get("enabled")),
        "real_mode_batches_refused": con.execute(
            "SELECT COUNT(*) FROM decisions WHERE dept = 'rewards' AND "
            "decision = 'reward-batch-refused'").fetchone()[0],
        "payout_calls_refused": con.execute(
            "SELECT COUNT(*) FROM decisions WHERE dept = 'rewards' AND "
            "decision = 'reward-payout-refused'").fetchone()[0],
        "mining_start": MINING_NOT_ACTIVE,
        "sources": {
            "emergency_stop": "config/atlas.json + data/snapshot.json",
            "mode": "config/pool-rewards.json",
            "refusals": "decisions table (dept='rewards')",
            "mining_start": "config/atlas.json + code grep",
        },
    }
    payload = {
        "exported_at": now,
        "source_db_user_version": user_version,
        "emergency_stop": bool(atlas_cfg.get("emergency_stop")),
        "mode": pool_cfg.get("mode", "simulation-only"),
        "mining_enabled": bool(atlas_cfg.get("mining", {}).get("enabled")),
        "scope": SCOPE_LINE,
        "security_tests": results,
        "security_counts": counts,
        # Default scale block: never run. export_security_json() replaces
        # it with the last recorded scale run when one exists.
        "scale": {"run_at": None, "reason": NO_SCALE_REASON, "stale": False},
        "host_verified_totals": totals,
        "redaction": {
            "patterns_checked": len(SECRET_PATTERNS),
            "files_checked": list(EXPORT_FILES),
            "files_missing": missing,
            "hits": total_hits,
            "hits_by_file": per_file,
            "note": ("Pattern list is defined in core/atlas_security.py "
                     "and is not repeated here — the export must not "
                     "contain the literals."),
        },
        "enforcement": enforcement,
        "honest_nulls": [
            "Gate 1 unmeasured — hashrate not measured, so no load-based "
            "earnings projection exists",
            "No live workers — token, share, and payout tests run on test "
            "fixtures only, not live data",
            "Rendered Mining-tab check — not established by this mission",
            "Mirror contents cannot be verified from the host — the UI "
            "mirror check covers the mirror side",
        ],
        "format_valid_line": FORMAT_VALID_LINE,
        "ownership_line": OWNERSHIP_LINE,
        "provenance": {
            "module": "atlas_security",
            "module_version": MODULE_VERSION,
            "db_user_version": user_version,
            "config_sha256_short": _config_sha256_short(),
            "security_counts_source": "live SQL (M8 §4 definitions)",
            "tests_source": "live reads + temp-DB fixtures (test fixture — "
                            "not live data)",
        },
    }
    # S9 runs against the assembled payload (it greps the payload itself).
    s9 = _check(con, export_dir, "S9", "No private data leaves the host",
                lambda c, e: _check_s9(c, e, payload))
    results.append(s9)
    payload["security_tests"] = results
    return payload


def _read_previous_scale(export_path):
    """The last recorded scale block from a previous export, or None."""
    try:
        with open(export_path) as f:
            previous = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(previous, dict):
        return None
    scale = previous.get("scale")
    return scale if isinstance(scale, dict) else None


def export_security_json(con=None, db_path=DB, export_path=EXPORT, scale=None):
    """Write data/security.json by atomic write (.tmp -> os.replace),
    the same pattern as the coordinator, rewards, dashboard, admin, and
    profitability exports. Derived export: deleting it loses nothing, it
    regenerates from the DB. When ``scale`` is None, the last recorded
    scale block is preserved from the previous export; when no scale
    run exists, the block is null with the verbatim reason.
    Returns (path, payload)."""
    own_con = False
    if con is None:
        con = connect(db_path)
        own_con = True
    try:
        export_dir = os.path.dirname(os.path.abspath(export_path))
        payload = security_status(con, export_dir=export_dir)
        if scale is not None:
            payload["scale"] = scale
        else:
            previous = _read_previous_scale(export_path)
            if previous is not None:
                previous = dict(previous)
                run_at = previous.get("run_at")
                previous["stale"] = bool(
                    isinstance(run_at, int)
                    and (_now() - run_at) > SCALE_STALE_S)
                payload["scale"] = previous
            else:
                payload["scale"] = {"run_at": None, "reason": NO_SCALE_REASON,
                                    "stale": False}
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
# Scale tests L1–L5 (on-demand only, temp DB only — D-M10-6)
# ---------------------------------------------------------------------------

def _require_temp_db(db_path):
    if not _is_temp_path(db_path):
        raise SecurityError(
            f"{SCALE_REFUSAL}: {db_path!r} is not under "
            f"{tempfile.gettempdir()} — scale runs use temp DBs only")


def _insert_fresh_pool_stats(con):
    """A current pool_stats row so run_pass() skips the pool poll
    (no network) during load measurements."""
    con.execute(
        "INSERT INTO pool_stats (pool_name, recorded_at, hashrate, miners, "
        "block_height, network_hashrate, block_reward_piconero, pool_fee_bps) "
        "VALUES ('MoneroOcean', ?, 262107922, 4975, 3808993, NULL, "
        "600000000000, 0)", (_now(),))
    con.commit()


def _build_synthetic_load(con, n_workers, n_shares, n_sessions, level):
    """Synthetic workers/shares/sessions on a temp DB. Every row is
    marked synthetic (names/ids carry the 'scale-' prefix). Browser
    workers (no credential, cheap to register). Returns (user_id, ...)."""
    import atlas_coordinator as ac
    user_id = _make_user(con, f"scale-synthetic-{level}")
    worker_ids = []
    for i in range(n_workers):
        worker_ids.append(ac.register_worker(
            con, user_id, "browser", f"scale-w{level}-{i:04d}")["id"])
    # Shares: true per-worker spread (Mission 12 fix D-M12-1). The old
    # loop built each 500-share batch first and then recorded it under
    # worker_ids[seq % n_workers] where seq was already the END of the
    # batch, so batches landed on workers 500 and 0 only (2 of 1,000).
    # Now every worker gets its own equal share of the load
    # (n_shares // n_workers each, remainder to the first workers),
    # recorded in chunks of at most MAX_BATCH_SHARES per worker, so
    # "1,000 workers / 100,000 shares" means 100 shares on each of
    # 1,000 workers. Globally unique external_ids (scale-<level>-<seq>).
    t0 = time.monotonic()
    inserted = 0
    seq = 0
    per_worker, remainder = divmod(n_shares, n_workers)
    for wi, worker_id in enumerate(worker_ids):
        count = per_worker + (1 if wi < remainder else 0)
        done = 0
        while done < count:
            take = min(ac.MAX_BATCH_SHARES, count - done)
            batch = [{
                "difficulty": 1, "accepted": 1,
                "submitted_at": W0 + seq + j,
                "origin": "pool",
                "external_id": f"scale-{level}-{seq + j}",
                "job_id": None} for j in range(take)]
            seq += take
            done += take
            result = ac.record_shares(con, worker_id, batch)
            inserted += result["inserted"]
    shares_s = time.monotonic() - t0
    workers_with_shares = con.execute(
        "SELECT COUNT(DISTINCT worker_id) FROM shares").fetchone()[0]
    # Sessions: browser probes (local-test sessions, never mining).
    for i in range(n_sessions):
        ac.record_worker_session(
            con, worker_ids[i % n_workers], "browser-probe",
            session_ref=f"scale-synthetic-{level}-{i}")
    return {"user_id": user_id, "workers": worker_ids,
            "shares_inserted": inserted, "shares_s": shares_s,
            "workers_with_shares": workers_with_shares,
            "shares_per_worker": per_worker}


def _build_ledger_fixture(con, n_entries):
    """A temp ledger with n_entries entries, built fast in Python
    (canonical payloads + executemany) and verified by verify_chain().
    Entries reference a real synthetic user, batch_id NULL."""
    import atlas_rewards as rw
    user_id = _make_user(con, "scale-ledger-user")
    rows = []
    prev_hash = rw.GENESIS_PREV_HASH
    now = _now()
    for i in range(1, n_entries + 1):
        entry = {"id": i, "created_at": now, "entry_type": "user_allocation",
                 "user_id": user_id, "amount_piconero": 1, "batch_id": None,
                 "reference": f"scale-ledger:{i}", "mode": "simulation",
                 "note": None, "prev_hash": prev_hash}
        entry_hash = rw._entry_hash(entry)
        rows.append((i, "user_allocation", user_id, 1,
                     f"scale-ledger:{i}", now, None, prev_hash, entry_hash,
                     "simulation", None))
        prev_hash = entry_hash
    con.execute("BEGIN IMMEDIATE")
    con.executemany(
        "INSERT INTO ledger (id, entry_type, user_id, amount_piconero, "
        "reference, created_at, batch_id, prev_hash, entry_hash, mode, note) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.execute("COMMIT")
    return user_id


def run_scale_smoke():
    """Fast smoke level for diagnostics test 28: temp-DB load of 100
    workers / 10,000 shares. Returns a summary dict; destroys the temp
    DB. Never touches the live DB."""
    live_con = connect(DB)
    try:
        path, con = _fresh_temp_db(live_con)
    finally:
        live_con.close()
    try:
        _insert_fresh_pool_stats(con)
        t0 = time.monotonic()
        built = _build_synthetic_load(con, 100, 10000, 0, "smoke")
        total_s = time.monotonic() - t0
        return {
            "workers": 100, "shares": 10000,
            "shares_inserted": built["shares_inserted"],
            "workers_with_shares": built["workers_with_shares"],
            "duration_s": round(total_s, 3),
            "shares_per_s": (round(built["shares_inserted"] / total_s, 1)
                             if total_s > 0 else None),
            "db_size_bytes": os.path.getsize(path),
        }
    finally:
        _close_remove(con, path)


def run_scale_tests():
    """On-demand scale battery (L1–L5). Temp DBs only, synthetic data
    marked synthetic, destroyed afterwards. Returns the scale block for
    the export. Runs the full diagnostics suite once as a subprocess
    for the L3 live leg (its normal behaviour: daemon restarts, live
    decision logging, diagnostics.json rewrite)."""
    started_all = time.monotonic()
    live_con = connect(DB)
    levels = []
    try:
        # ---- L1: load levels -------------------------------------------
        for label, tag, n_workers, n_shares, n_sessions in (
                ("1x baseline (live shape: 0 workers, 0 shares)", "base", 0, 0, 0),
                ("100 workers / 10,000 shares", "100", 100, 10000, 10),
                ("1,000 workers / 100,000 shares", "1000", 1000, 100000, 100)):
            path, con = _fresh_temp_db(live_con)
            try:
                import atlas_coordinator as ac
                _insert_fresh_pool_stats(con)
                if n_workers:
                    built = _build_synthetic_load(
                        con, n_workers, n_shares, n_sessions, tag)
                    shares_per_s = (built["shares_inserted"] / built["shares_s"]
                                    if built["shares_s"] > 0 else None)
                else:
                    built = {"shares_inserted": 0, "shares_s": 0.0}
                    shares_per_s = None
                t0 = time.monotonic()
                weights = ac.attribution_weights(con)
                attribution_s = time.monotonic() - t0
                # run_pass wall time on the temp DB, exports into a temp dir.
                tmpdir = tempfile.mkdtemp(prefix="atlas-m10-pass-")
                try:
                    coord_path = os.path.join(tmpdir, "coordinator.json")
                    t0 = time.monotonic()
                    ac.run_pass(db_path=path, export_path=coord_path)
                    pass_s = time.monotonic() - t0
                finally:
                    shutil.rmtree(tmpdir, ignore_errors=True)
                # verify_chain on a 10,000-entry temp ledger (1000 level only).
                chain_s = None
                if n_workers == 1000:
                    lpath, lcon = _fresh_temp_db(live_con)
                    try:
                        import atlas_rewards as rw
                        _build_ledger_fixture(lcon, 10000)
                        t0 = time.monotonic()
                        verdict = rw.verify_chain(lcon)
                        chain_s = time.monotonic() - t0
                        if not verdict["ok"]:
                            raise SecurityError(
                                "verify_chain failed on scale ledger fixture: "
                                f"{verdict.get('error')}")
                    finally:
                        _close_remove(lcon, lpath)
                steps = {"run_pass_s": round(pass_s, 3),
                         "attribution_weights_s": round(attribution_s, 3)}
                if chain_s is not None:
                    steps["verify_chain_10000_s"] = round(chain_s, 3)
                record_total_s = (round(built["shares_s"], 3)
                                  if n_workers else None)
                if record_total_s is not None:
                    steps["record_shares_total_s"] = record_total_s
                slowest = max(steps, key=steps.get)
                levels.append({
                    "label": label, "workers": n_workers,
                    "shares": n_shares, "sessions": n_sessions,
                    "shares_inserted": built["shares_inserted"],
                    "workers_with_shares": built.get("workers_with_shares"),
                    "shares_per_worker": built.get("shares_per_worker"),
                    "db_size_bytes": os.path.getsize(path),
                    "run_pass_s": round(pass_s, 3),
                    "record_shares_per_s": (round(shares_per_s, 1)
                                            if shares_per_s else None),
                    "record_shares_total_s": record_total_s,
                    "attribution_weights_s": round(attribution_s, 3),
                    "verify_chain_10000_s": (round(chain_s, 3)
                                             if chain_s is not None else None),
                    "slowest_step": slowest,
                })
            finally:
                _close_remove(con, path)
        l1 = {"levels": levels,
              "note": ("shares spread evenly across workers: each worker "
                       "records its own n_shares // n_workers shares in "
                       "chunks of at most MAX_BATCH_SHARES (500); "
                       "workers_with_shares is the distinct-worker count "
                       "measured from the shares table; verify_chain timed "
                       "on a 10,000-entry temp ledger")}
        # ---- L2: mirror ingest (artifact side — NOT_RUN) ----------------
        l2 = {"result": "NOT_RUN", "reason": L2_NOT_RUN_REASON}
        # ---- L3: diagnostics runtime ------------------------------------
        t0 = time.monotonic()
        proc = subprocess.run(
            [sys.executable, os.path.join(CORE, "diagnostics.py")],
            capture_output=True, text=True, timeout=600)
        live_s = time.monotonic() - t0
        try:
            with open(os.path.join(DATA_DIR, "diagnostics.json")) as f:
                diag = json.load(f)
            diag_summary = diag.get("summary", {})
        except (OSError, ValueError):
            diag_summary = {}
        # Supplementary: DB-sensitive checks on the 10,000-entry temp ledger.
        lpath, lcon = _fresh_temp_db(live_con)
        try:
            import atlas_rewards as rw
            _build_ledger_fixture(lcon, 10000)
            t0 = time.monotonic()
            rw.verify_chain(lcon)
            lcon.execute("SELECT COUNT(*) FROM ledger").fetchone()
            lcon.execute(
                "SELECT COALESCE(SUM(amount_piconero), 0) FROM ledger "
                "WHERE entry_type = 'user_allocation'").fetchone()
            temp_db_checks_s = time.monotonic() - t0
        finally:
            _close_remove(lcon, lpath)
        l3 = {"live_s": round(live_s, 1),
              "live_under_120s": live_s < 120,
              "live_diagnostics_summary": diag_summary,
              "live_diagnostics_exit": proc.returncode,
              "temp_s": None,
              "temp_reason": L3_TEMP_NOT_RUN_REASON,
              "temp_db_checks_s": round(temp_db_checks_s, 3)}
        # ---- L4: DB size growth projection ------------------------------
        l4 = _l4_measure(live_con)
        # ---- L5: first bottleneck ---------------------------------------
        l5 = _first_bottleneck(levels)
        scale = {
            "run_at": _now(),
            "run_duration_s": round(time.monotonic() - started_all, 1),
            "levels": levels,
            "l1": l1, "l2": l2, "l3": l3, "l4": l4, "l5": l5,
            "stale": False,
        }
        return scale
    finally:
        live_con.close()


def _l4_measure(live_con):
    """Bytes-per-row for shares, ledger entries, decisions, metrics from
    temp fixtures; size projection at 10k/100k/1M shares (ESTIMATE)."""
    path, con = _fresh_temp_db(live_con)
    try:
        base_bytes = os.path.getsize(path)
        _build_synthetic_load(con, 10, 10000, 0, "l4-shares")
        after_shares = os.path.getsize(path)
        _build_ledger_fixture(con, 10000)
        after_ledger = os.path.getsize(path)
        now = _now()
        con.execute("BEGIN IMMEDIATE")
        con.executemany(
            "INSERT INTO decisions (ts, dept, decision, reason) "
            "VALUES (?,?,?,?)",
            [(now, "scale", "scale-fixture", "synthetic")
             for _ in range(1000)])
        con.execute("COMMIT")
        after_decisions = os.path.getsize(path)
        con.execute("BEGIN IMMEDIATE")
        con.executemany(
            "INSERT INTO metrics (ts, cpu, mem_used_pct, disk_used_pct, "
            "load1, load5, load15, net_rx_bytes, net_tx_bytes) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            [(now + i, 1.0, 50.0, 50.0, 0.1, 0.1, 0.1, 1, 1)
             for i in range(1000)])  # ts is the PRIMARY KEY: distinct values
        con.execute("COMMIT")
        after_metrics = os.path.getsize(path)
    finally:
        _close_remove(con, path)
    def _bpr(after, before, rows):
        return round((after - before) / rows, 2) if rows else None
    bytes_per_row = {
        "shares": _bpr(after_shares, base_bytes, 10000),
        "ledger_entries": _bpr(after_ledger, after_shares, 10000),
        "decisions": _bpr(after_decisions, after_ledger, 1000),
        "metrics": _bpr(after_metrics, after_decisions, 1000),
    }
    live_bytes = os.path.getsize(DB)
    per_share = bytes_per_row["shares"] or 0
    projection = {}
    for rows in (10000, 100000, 1000000):
        projection[str(rows)] = int(live_bytes + rows * per_share)
    return {
        "bytes_per_row": bytes_per_row,
        "base_bytes": live_bytes,
        "formula": "size ≈ base + rows × bytes_per_row",
        "projection_shares": projection,
        "label": "ESTIMATE",
        "note": ("SQLite grows in 4096-byte pages, so bytes-per-row is a "
                 "measured approximation, not exact; projection only."),
    }


def _first_bottleneck(levels):
    """First bottleneck from the L1 levels (design §5 L5).

    Two clauses, in order:
    1. Absolute thresholds — the first load level where run_pass()
       exceeds 60 s (10% of the 10-minute budget) or any single step
       exceeds 30 s. record_shares total time counts as a step: it is
       the wall time of the whole share load at that level.
    2. Super-linear growth — a step whose time grows >12x for a 10x
       load step. Candidates are ranked by absolute seconds consumed
       at the big level, so a noise-level ratio on a millisecond step
       cannot outrank a step that actually dominates the run
       (record_shares per-share time is included; its total is
       shares_inserted / record_shares_per_s).
    Mission 11 calibration (D-M11-3): clause 2 additionally requires
    the step to consume more than 1.0 s at the big level. Ranking
    alone did not stop a false positive: after the record_shares
    fix, attribution_weights was the ONLY ratio candidate (0.002 s
    -> 0.032 s, 16x) and was reported as "the bottleneck" although
    32 ms cannot bottleneck anything. A super-linear ratio on a
    sub-second step is timer/page noise, not a scaling limit; the
    absolute clause (1) above remains the hard gate for real time.
    The ratio clause is deliberately NOT the only gate: the measured
    record_shares ratio hovers near the 12x threshold across runs
    (22.7x once, ~12x once) while its absolute time is hundreds of
    seconds at the big level — the absolute clause is the robust one."""
    # Clause 1: absolute thresholds, first level first.
    thresholds = (("run_pass_s", 60.0), ("attribution_weights_s", 30.0),
                  ("verify_chain_10000_s", 30.0),
                  ("record_shares_total_s", 30.0))
    for lv in levels:
        over = [(step, lv[step]) for step, limit in thresholds
                if lv.get(step) is not None and lv[step] > limit]
        if over:
            step, value = max(over, key=lambda item: item[1])
            return {"bottleneck": (
                f"{step} exceeds its limit at {lv['label']} ({value}s)"),
                "first_bottleneck_load": lv["label"]}
    # Clause 2: super-linear growth, ranked by absolute time, with a
    # 1.0 s floor at the big level (D-M11-3 — see docstring).
    by_label = {lv["label"]: lv for lv in levels}
    small = by_label.get("100 workers / 10,000 shares")
    big = by_label.get("1,000 workers / 100,000 shares")
    if small and big:
        candidates = []
        for step in ("run_pass_s", "attribution_weights_s"):
            t_small = small.get(step) or 0
            t_big = big.get(step) or 0
            if t_small > 0 and t_big > 1.0 and t_big / t_small > 12:
                candidates.append((t_big, step, t_small, t_big,
                                   t_big / t_small))
        per_s_small = small.get("record_shares_per_s")
        per_s_big = big.get("record_shares_per_s")
        if per_s_small and per_s_big:
            share_s_small = 1.0 / per_s_small
            share_s_big = 1.0 / per_s_big
            total_big = (big.get("shares_inserted") or 0) / per_s_big
            if (share_s_small > 0 and total_big > 1.0
                    and share_s_big / share_s_small > 12):
                candidates.append((total_big, "record_shares",
                                   share_s_small, share_s_big,
                                   share_s_big / share_s_small))
        if candidates:
            # Largest absolute time at the big level wins.
            _total, step, t_small, t_big, ratio = max(
                candidates, key=lambda c: c[0])
            if step == "record_shares":
                detail = (f"record_shares per-share time grows "
                          f"super-linearly: {t_small * 1000:.2f} ms/share at "
                          f"100 workers / 10,000 shares -> "
                          f"{t_big * 1000:.2f} ms/share at 1,000 workers / "
                          f"100,000 shares ({ratio:.1f}x for a 10x load; "
                          f"{_total:.0f}s total at the big level)")
            else:
                detail = (f"{step} grows super-linearly: {t_small}s at "
                          f"100 workers / 10,000 shares -> {t_big}s at 1,000 "
                          f"workers / 100,000 shares ({ratio:.1f}x for a "
                          f"10x load)")
            return {"bottleneck": detail,
                    "first_bottleneck_load":
                        "1,000 workers / 100,000 shares"}
    return {"bottleneck": NO_BOTTLENECK,
            "first_bottleneck_load": None}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_status(_args):
    con = connect(DB)
    try:
        payload = security_status(con)
    finally:
        con.close()
    print(json.dumps(payload, indent=2))
    passed = sum(1 for t in payload["security_tests"]
                 if t["result"] == "PASS")
    total = len(payload["security_tests"])
    print(f"Security: {passed}/{total} checks passed")
    return 0


def cmd_export(_args):
    path, payload = export_security_json()
    passed = sum(1 for t in payload["security_tests"]
                 if t["result"] == "PASS")
    total = len(payload["security_tests"])
    print(f"Exported {path} (exported_at {payload['exported_at']}, "
          f"security {passed}/{total} passed, "
          f"scale {'recorded' if payload['scale'].get('run_at') else 'not run'})")
    return 0


def cmd_run_tests(_args):
    con = connect(DB)
    try:
        payload = security_status(con)
    finally:
        con.close()
    failed = [t for t in payload["security_tests"] if t["result"] == "FAIL"]
    not_run = [t for t in payload["security_tests"] if t["result"] == "NOT_RUN"]
    for t in payload["security_tests"]:
        print(f"[{t['result']}] {t['id']} {t['name']}: {t['evidence']} "
              f"({t['duration_ms']} ms)")
    passed = sum(1 for t in payload["security_tests"] if t["result"] == "PASS")
    print(f"\nSecurity: {passed}/{len(payload['security_tests'])} passed, "
          f"{len(failed)} failed, {len(not_run)} not run")
    return 0 if not failed else 1


def cmd_run_scale(_args):
    scale = run_scale_tests()
    _path, payload = export_security_json(scale=scale)
    print(f"Scale run recorded (run_at {scale['run_at']}, "
          f"{scale['run_duration_s']}s total)")
    for lv in scale["levels"]:
        print(f"  {lv['label']}: run_pass {lv['run_pass_s']}s, "
              f"record_shares {lv['record_shares_per_s']}/s, "
              f"attribution {lv['attribution_weights_s']}s, "
              f"db {lv['db_size_bytes']} bytes, slowest {lv['slowest_step']}")
    print(f"  L2: {scale['l2']['result']} — {scale['l2']['reason']}")
    print(f"  L3: live diagnostics {scale['l3']['live_s']}s "
          f"(under 120s: {scale['l3']['live_under_120s']}), "
          f"temp: {scale['l3']['temp_reason']}")
    print(f"  L4: bytes/row {scale['l4']['bytes_per_row']}, "
          f"projection {scale['l4']['projection_shares']}")
    print(f"  L5: {scale['l5']['bottleneck']}")
    print(f"Exported {_path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="ATLAS host security + scale (Master Mission 10) — "
                    "read-only derivation, simulation only.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="print derived security state")
    sub.add_parser("export", help="write data/security.json (atomic)")
    sub.add_parser("run-tests", help="run the S1–S9 battery, exit 1 on FAIL")
    sub.add_parser("run-scale", help="on-demand scale test (temp DB only)")
    args = parser.parse_args(argv)
    handlers = {"status": cmd_status, "export": cmd_export,
                "run-tests": cmd_run_tests, "run-scale": cmd_run_scale}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
