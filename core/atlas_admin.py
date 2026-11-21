#!/usr/bin/env python3
"""ATLAS HOST ADMIN MODULE — Master Mission 8, Lane C (host-side,
stdlib only).

A READ-ONLY derivation of the admin command-center state from the live
DB and the sibling host exports. It writes no ledger rows, no
decisions, no shares, no batches, no sessions, no user rows — the only
write this module ever performs is the atomic export of
``data/admin.json`` itself (temp file + os.replace, same pattern as
the coordinator, rewards, and dashboard exports).

Derivation rules (binding, docs/master-mission8-design.md):
  - Network reuses coordinator_status() (workers, shares, hashrate,
    pool stats) and the dashboard export's earnings block by import —
    never recomputed, so the admin section can never show a different
    earnings number than the user dashboard (D-M8-2).
  - Mining figures are ledger SUMs via reward_totals()/balances()
    from atlas_rewards (imported, never duplicated). Pending rewards
    are the gross piconero of open/held (unsettled) batches; they
    contribute nothing to confirmed earnings.
  - Infrastructure comes from the latest metrics row + PRAGMA checks
    + table counts + the latest pool_stats row + diagnostics.json +
    snapshot.json + the watchdog log's last line.
  - Security counts use the binding definitions in design §4.
  - Operational logs are the latest-50 window of decisions/events,
    with the §1.2 defensive redaction applied to every message before
    it enters the export.
  - Queue lengths are UNAVAILABLE (no queue system exists) and daemon
    uptime is UNAVAILABLE (no start time is recorded) — both with
    their verbatim reasons, never guessed.
  - Worker rows select id, worker_type, status, registered_at,
    last_seen_at ONLY — a SELECT * over workers in this module is a
    defect. No user rows at all (count only).
  - All money is integer piconero (1 XMR = 10^12 piconero), never float.

Usage:
    python3 core/atlas_admin.py status
    python3 core/atlas_admin.py export

Stdlib only. Portable by copying ~/workspace/atlas.
"""
import argparse
import calendar
import json
import os
import re
import sqlite3
import sys
import time

BASE = os.path.expanduser("~/workspace/atlas")
CFG_ATLAS = os.path.join(BASE, "config", "atlas.json")
CFG_POOL = os.path.join(BASE, "config", "pool-rewards.json")
DB = os.path.join(BASE, "data", "atlas.db")
EXPORT = os.path.join(BASE, "data", "admin.json")
DATA_DIR = os.path.join(BASE, "data")

STALE_EXPORT_S = 3600         # source exports older than this are stale
STALE_METRICS_S = 600         # latest metrics row older than this is stale
DAEMON_FRESH_S = 180          # snapshot younger than this: daemon "Running"
WATCHDOG_FRESH_S = 300        # watchdog log line younger than this is fresh
MEM_CAP_PCT = 70              # memory cap (config limits.max_mem_pct)
BUSY_TIMEOUT_MS = 5000
LOG_WINDOW = 50               # latest-50 decisions/events window (design §1.1)

SCOPE_LINE = ("Admin view — aggregates and operational data only. "
              "No login exists yet — this section is not access-controlled.")
QUEUE_REASON = ("No queue system exists — the coordinator runs "
                "synchronously in the 10-minute pass")
DAEMON_UPTIME_REASON = "Daemon start time is not recorded"
REDACTED = "[redacted — possible credential]"
NO_EVENTS = "No events recorded"
MEM_ABOVE_CAP_NOTE = "Above the 70% cap"
DB_INTEGRITY_NOTE = ("Database integrity check failed — "
                     "figures under investigation")
WINDOW_NOTE_TEMPLATE = ("Showing latest 20 of 50 mirrored rows — "
                        "{total} total on host")
NOT_POLLED_YET = "Not polled yet"
NO_ABUSE_NOTE = "No abuse events recorded"
NO_AUTH_FAILURE_NOTE = "No auth-failure events recorded"
BLOCKCHAIN_APIS_NOTE = "recorded claim, not a live measurement"

# Design §1.2 (binding): a message matching a credential pattern, or
# containing a run of 20+ base58/hex characters that is not a known pool
# external_id/job_id shape, is replaced, never shown.
CREDENTIAL_WORD_RE = re.compile(
    r"(?i)(token|secret|password|seed|private.?key|bearer|api.?key)")
LONG_RUN_RE = re.compile(r"[A-Za-z0-9]{20,}")

TABLES = ("users", "workers", "shares", "sessions", "ledger",
          "reward_batches", "payouts", "pool_stats", "decisions",
          "events", "metrics")


def _now():
    return int(time.time())


def _fmt_duration(seconds):
    """Seconds as 'Xd Yh Zm' (design §5, monitoring uptime)."""
    seconds = max(int(seconds), 0)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m"


def _fmt_age(seconds):
    """Seconds as a short age string ('45s', '1m 40s', '2h 5m')."""
    seconds = max(int(seconds), 0)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def _read_json_file(path):
    """Parsed JSON dict from a file, or None when missing/unparseable."""
    try:
        with open(path) as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else None
    except (OSError, ValueError):
        return None


def _read_export_ts(export_dir, filename):
    """exported_at (or diagnostics-style ts) from a sibling export
    file, or None when the file is missing, unparseable, or carries no
    integer timestamp."""
    payload = _read_json_file(os.path.join(export_dir, filename))
    if payload is None:
        return None
    for key in ("exported_at", "ts"):
        ts = payload.get(key)
        if isinstance(ts, int) and not isinstance(ts, bool):
            return ts
    return None


def _load_configs():
    """Read both configs fresh on every call — never cached across passes."""
    with open(CFG_ATLAS) as f:
        atlas_cfg = json.load(f)
    with open(CFG_POOL) as f:
        pool_cfg = json.load(f)
    return atlas_cfg, pool_cfg


def _redact_message(message, known_ids):
    """Design §1.2 defensive redaction. A message matching a credential
    pattern, or containing a 20+ character run that is not a known pool
    external_id/job_id shape, is replaced with the verbatim redacted
    string. The row is still counted. None stays None."""
    if message is None:
        return None
    if CREDENTIAL_WORD_RE.search(message):
        return REDACTED
    for run in LONG_RUN_RE.findall(message):
        if run not in known_ids:
            return REDACTED
    return message


def _known_share_ids(con):
    """Pool-assigned external_id/job_id values — the only long runs
    that are NOT credentials under §1.2."""
    known = set()
    for row in con.execute(
            "SELECT external_id, job_id FROM shares "
            "WHERE external_id IS NOT NULL OR job_id IS NOT NULL").fetchall():
        if row["external_id"]:
            known.add(row["external_id"])
        if row["job_id"]:
            known.add(row["job_id"])
    return known


def _suspicious_workers(con):
    """Design §4: workers with status suspended/revoked, OR pool-origin
    rejected shares >= 10 AND rejected / (accepted + rejected) > 0.5.
    Rows carry id + type + status + timestamps only — never token fields."""
    suspicious_ids = set()
    for row in con.execute(
            "SELECT id FROM workers WHERE status IN ('suspended','revoked')").fetchall():
        suspicious_ids.add(row["id"])
    for row in con.execute(
            """SELECT worker_id,
                      SUM(CASE WHEN accepted = 0 THEN 1 ELSE 0 END) AS rejected,
                      SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) AS accepted
               FROM shares WHERE origin = 'pool' GROUP BY worker_id""").fetchall():
        rejected = row["rejected"] or 0
        accepted = row["accepted"] or 0
        total = rejected + accepted
        if rejected >= 10 and total > 0 and rejected / total > 0.5:
            suspicious_ids.add(row["worker_id"])
    rows = []
    for row in con.execute(
            "SELECT id, worker_type, status, registered_at, last_seen_at "
            "FROM workers ORDER BY id").fetchall():
        if row["id"] in suspicious_ids:
            rows.append({
                "id": row["id"],
                "worker_type": row["worker_type"],
                "status": row["status"],
                "registered_at": row["registered_at"],
                "last_seen_at": row["last_seen_at"],
            })
    return rows


def _duplicate_shares(con):
    """Design §4: groups sharing the same non-null external_id (or, when
    external_id is null, the same worker_id + job_id) with count > 1.
    Count = duplicate rows beyond the first per group. Rows shown are
    the duplicate rows (all but the first by id per group)."""
    duplicate_rows = []
    count = 0
    groups = con.execute(
        "SELECT external_id, COUNT(*) AS n FROM shares "
        "WHERE external_id IS NOT NULL GROUP BY external_id HAVING n > 1"
    ).fetchall()
    for group in groups:
        count += group["n"] - 1
        rows = con.execute(
            "SELECT id, worker_id, external_id, job_id, submitted_at "
            "FROM shares WHERE external_id = ? ORDER BY id",
            (group["external_id"],)).fetchall()
        for row in rows[1:]:
            duplicate_rows.append({
                "id": row["id"], "worker_id": row["worker_id"],
                "external_id": row["external_id"], "job_id": row["job_id"],
                "submitted_at": row["submitted_at"],
            })
    null_groups = con.execute(
        "SELECT worker_id, job_id, COUNT(*) AS n FROM shares "
        "WHERE external_id IS NULL AND job_id IS NOT NULL "
        "GROUP BY worker_id, job_id HAVING n > 1"
    ).fetchall()
    for group in null_groups:
        count += group["n"] - 1
        rows = con.execute(
            "SELECT id, worker_id, external_id, job_id, submitted_at "
            "FROM shares WHERE external_id IS NULL AND worker_id = ? "
            "AND job_id = ? ORDER BY id",
            (group["worker_id"], group["job_id"])).fetchall()
        for row in rows[1:]:
            duplicate_rows.append({
                "id": row["id"], "worker_id": row["worker_id"],
                "external_id": row["external_id"], "job_id": row["job_id"],
                "submitted_at": row["submitted_at"],
            })
    duplicate_rows.sort(key=lambda r: r["id"])
    return count, duplicate_rows


def _parse_diagnostics_endpoints(diag):
    """Endpoint outcomes from diagnostics.json tests 14 and 18.

    Test 14 detail: 'coingecko:200, moneroocean:200, blockchain.info:200'.
    Test 18 detail: 'name: HTTP 200, ... | name: HTTP 200, ...' segments.
    Returns (endpoints dict, test-14 detail, test-18 detail). An endpoint
    with no live outcome stays absent — never invented."""
    endpoints = {}
    test14_detail = None
    test18_detail = None
    if not diag:
        return endpoints, test14_detail, test18_detail
    for result in diag.get("results", []):
        name = result.get("test", "")
        detail = result.get("detail", "")
        if name.startswith("14 "):
            test14_detail = detail
            for part in detail.split(","):
                part = part.strip()
                if ":" not in part:
                    continue
                host, _, status = part.partition(":")
                host = host.strip()
                status = status.strip()
                if host and status:
                    endpoints.setdefault(host, {})["test_14_status"] = status
        elif name.startswith("18 "):
            test18_detail = detail
            for segment in detail.split(" | "):
                match = re.match(r"^(\S+): HTTP (\d+|None)\b", segment.strip())
                if match:
                    host, status = match.group(1), match.group(2)
                    endpoints.setdefault(host, {})["test_18_status"] = status
    return endpoints, test14_detail, test18_detail


def _watchdog_last_line(export_dir):
    """Last non-empty line of logs/refresh-attempts.log (the log lives
    next to the data dir) plus its UTC timestamp age, or Nones when the
    log is missing/empty/unparseable."""
    log_path = os.path.join(
        os.path.dirname(os.path.abspath(export_dir)), "logs",
        "refresh-attempts.log")
    try:
        with open(log_path) as f:
            lines = [line.rstrip("\n") for line in f if line.strip()]
    except OSError:
        return None, None
    if not lines:
        return None, None
    last = lines[-1]
    try:
        stamp = last.split()[0]
        log_ts = calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, IndexError):
        return last, None
    return last, _now() - log_ts


def admin_status(con, export_dir=None):
    """Derive the admin state object from the tables + sibling exports.

    Read-only: performs SELECTs and PRAGMA reads only (plus the config
    and export reads inside coordinator_status / dashboard_status /
    reward_totals). ``export_dir`` is where the sibling coordinator.json
    / rewards.json / dashboard.json / diagnostics.json / snapshot.json
    exports live; it defaults to the live data dir."""
    if export_dir is None:
        export_dir = DATA_DIR
    atlas_cfg, pool_cfg = _load_configs()
    user_version = con.execute("PRAGMA user_version").fetchone()[0]
    now = _now()
    mode = pool_cfg.get("mode", "simulation-only")
    simulation_only = mode == "simulation-only"

    # Network — coordinator state reused, never recomputed (D-M8-1).
    coord = _coordinator_status(con, atlas_cfg, pool_cfg)
    # Mining — dashboard earnings block reused verbatim by import (D-M8-2).
    dash = _dashboard_status(con, export_dir=export_dir)
    # Reward totals + balances — reused, never recomputed here.
    totals = _reward_totals(con)

    users_count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    # Worker rows: the five columns only — never SELECT * (design §1.2).
    worker_rows = [{
        "id": row["id"],
        "worker_type": row["worker_type"],
        "status": row["status"],
        "registered_at": row["registered_at"],
        "last_seen_at": row["last_seen_at"],
    } for row in con.execute(
        "SELECT id, worker_type, status, registered_at, last_seen_at "
        "FROM workers ORDER BY id").fetchall()]

    # Monitoring uptime = metrics span; daemon restarts from startup events.
    metrics_span = con.execute(
        "SELECT MIN(ts), MAX(ts), COUNT(*) FROM metrics").fetchone()
    metrics_first_ts, metrics_last_ts, metrics_count = metrics_span
    if metrics_first_ts is not None and metrics_last_ts is not None:
        uptime_seconds = metrics_last_ts - metrics_first_ts
    else:
        uptime_seconds = 0
    restarts_24h = con.execute(
        "SELECT COUNT(*) FROM events WHERE kind = 'startup' AND ts >= ?",
        (now - 86400,)).fetchone()[0]
    restarts_all = con.execute(
        "SELECT COUNT(*) FROM events WHERE kind = 'startup'").fetchone()[0]

    # Mining — pending is the gross of open/held (unsettled) batches;
    # it contributes nothing to confirmed earnings (design §3).
    pending_piconero = con.execute(
        "SELECT COALESCE(SUM(gross_piconero), 0) FROM reward_batches "
        "WHERE status IN ('open', 'held')").fetchone()[0]
    payout_rows = [{
        "id": row["id"],
        "amount_piconero": row["amount_piconero"],
        "status": row["status"],
        "created_at": row["created_at"],
    } for row in con.execute(
        "SELECT id, amount_piconero, status, created_at "
        "FROM payouts ORDER BY id").fetchall()]
    failed_payouts = sum(1 for r in payout_rows if r["status"] == "failed")

    # Infrastructure — latest metrics row (RECORDED, with its timestamp).
    latest_metrics = con.execute(
        "SELECT * FROM metrics ORDER BY ts DESC LIMIT 1").fetchone()
    if latest_metrics is None:
        resources = {
            "latest_ts": None, "cpu": None, "mem_used_pct": None,
            "disk_used_pct": None, "load1": None, "load5": None,
            "load15": None, "net_rx_bytes": None, "net_tx_bytes": None,
            "stale": True, "memory_note": None,
        }
    else:
        mem = latest_metrics["mem_used_pct"]
        resources = {
            "latest_ts": latest_metrics["ts"],
            "cpu": latest_metrics["cpu"],
            "mem_used_pct": mem,
            "disk_used_pct": latest_metrics["disk_used_pct"],
            "load1": latest_metrics["load1"],
            "load5": latest_metrics["load5"],
            "load15": latest_metrics["load15"],
            "net_rx_bytes": latest_metrics["net_rx_bytes"],
            "net_tx_bytes": latest_metrics["net_tx_bytes"],
            "stale": (now - latest_metrics["ts"]) > STALE_METRICS_S,
            "memory_note": (MEM_ABOVE_CAP_NOTE
                            if mem is not None and mem > MEM_CAP_PCT else None),
        }

    # DB health — integrity_check + user_version + table counts.
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    table_counts = {}
    for table in TABLES:
        table_counts[table] = con.execute(
            f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    db_health = {
        "integrity_check": integrity,
        "user_version": user_version,
        "table_counts": table_counts,
        "note": (None if integrity == "ok" else DB_INTEGRITY_NOTE),
    }

    # Connectivity — last pool poll + last diagnostics endpoint tests.
    diag = _read_json_file(os.path.join(export_dir, "diagnostics.json"))
    endpoints, test14_detail, test18_detail = _parse_diagnostics_endpoints(diag)
    connectivity = {
        "pool_stats_latest": coord["pool_stats_latest"],
        "pool_stats_note": (None if coord["pool_stats_latest"] is not None
                            else NOT_POLLED_YET),
        "diagnostics_ts": diag.get("ts") if diag else None,
        "diagnostics_test_14": test14_detail,
        "diagnostics_test_18": test18_detail,
        "endpoints": endpoints,
        "blockchain_apis": {
            "statuses": atlas_cfg.get("blockchain_apis", {}),
            "note": BLOCKCHAIN_APIS_NOTE,
        },
    }

    # Service status — snapshot freshness + coordinator last pass +
    # watchdog last line. No pid is shown (none is recorded).
    snap = _read_json_file(os.path.join(export_dir, "snapshot.json"))
    if snap is not None and isinstance(snap.get("ts"), int):
        snap_age = now - snap["ts"]
        daemon_status = ("Running" if snap_age < DAEMON_FRESH_S
                         else f"Stale — last seen {_fmt_age(snap_age)} ago")
    else:
        snap_age = None
        daemon_status = "Stale — last seen unknown ago"
    last_pass_at = coord["last_coordinator_pass_at"]
    watchdog_line, watchdog_age = _watchdog_last_line(export_dir)
    if watchdog_line is not None and watchdog_age is not None:
        watchdog_status = ("Running" if watchdog_age < WATCHDOG_FRESH_S
                           and "PASS" in watchdog_line
                           else f"Stale — last seen {_fmt_age(watchdog_age)} ago")
    elif watchdog_line is not None:
        watchdog_status = "Unknown — last line has no parseable timestamp"
    else:
        watchdog_status = "Unknown — no watchdog log line"
    services = {
        "daemon": {"status": daemon_status, "snapshot_age_s": snap_age},
        "coordinator_pass": {
            "last_coordinator_pass_at": last_pass_at,
            "last_decision_id": coord["last_decision_id"],
            "age_s": (now - last_pass_at) if last_pass_at is not None else None,
        },
        "watchdog": {
            "status": watchdog_status,
            "last_line": watchdog_line,
            "age_s": watchdog_age,
        },
    }

    # Security — binding definitions, design §4.
    suspicious_rows = _suspicious_workers(con)
    invalid_shares = con.execute(
        "SELECT COUNT(*) FROM shares WHERE origin = 'pool' AND accepted = 0"
    ).fetchone()[0]
    duplicate_count, duplicate_rows = _duplicate_shares(con)
    abuse_count = con.execute(
        "SELECT COUNT(*) FROM events WHERE kind = 'abuse'").fetchone()[0]
    auth_failure_count = con.execute(
        "SELECT COUNT(*) FROM events WHERE kind = 'auth_failure'").fetchone()[0]
    reversal_rows = [{
        "id": row["id"],
        "amount_piconero": row["amount_piconero"],
        "reference": row["reference"],
        "created_at": row["created_at"],
    } for row in con.execute(
        "SELECT id, amount_piconero, reference, created_at FROM ledger "
        "WHERE entry_type = 'reversal' ORDER BY id").fetchall()]
    failed_payout_rows = [r for r in payout_rows if r["status"] == "failed"]
    payout_anomalies = failed_payouts + len(reversal_rows)
    security = {
        "suspicious_workers": {
            "count": len(suspicious_rows),
            "empty_state": NO_EVENTS if not suspicious_rows else None,
            "rows": suspicious_rows,
        },
        "invalid_shares": {
            "count": invalid_shares,
            "empty_state": NO_EVENTS if invalid_shares == 0 else None,
        },
        "duplicate_shares": {
            "count": duplicate_count,
            "empty_state": NO_EVENTS if duplicate_count == 0 else None,
            "rows": duplicate_rows,
        },
        "account_abuse": {
            "count": abuse_count,
            "empty_state": NO_EVENTS if abuse_count == 0 else None,
            "note": NO_ABUSE_NOTE if abuse_count == 0 else None,
        },
        "auth_failures": {
            "count": auth_failure_count,
            "empty_state": NO_EVENTS if auth_failure_count == 0 else None,
            "note": NO_AUTH_FAILURE_NOTE if auth_failure_count == 0 else None,
        },
        "payout_anomalies": {
            "count": payout_anomalies,
            "empty_state": NO_EVENTS if payout_anomalies == 0 else None,
            "failed_payout_rows": failed_payout_rows,
            "reversal_rows": reversal_rows,
        },
    }

    # Operational logs — latest-50 window each, redacted (design §1.1/§1.2).
    known_ids = _known_share_ids(con)
    decisions_total = con.execute(
        "SELECT COUNT(*) FROM decisions").fetchone()[0]
    events_total = con.execute(
        "SELECT COUNT(*) FROM events").fetchone()[0]
    decision_rows = []
    dept_counts = {}
    for row in con.execute(
            "SELECT id, ts, dept, decision, reason FROM decisions "
            "ORDER BY id DESC LIMIT ?", (LOG_WINDOW,)).fetchall():
        decision_rows.append({
            "id": row["id"], "ts": row["ts"], "dept": row["dept"],
            "decision": row["decision"],
            "reason": _redact_message(row["reason"], known_ids),
        })
        dept_counts[row["dept"]] = dept_counts.get(row["dept"], 0) + 1
    event_rows = []
    kind_counts = {}
    for row in con.execute(
            "SELECT id, ts, kind, message FROM events "
            "ORDER BY id DESC LIMIT ?", (LOG_WINDOW,)).fetchall():
        event_rows.append({
            "id": row["id"], "ts": row["ts"], "kind": row["kind"],
            "message": _redact_message(row["message"], known_ids),
        })
        kind_counts[row["kind"]] = kind_counts.get(row["kind"], 0) + 1
    logs = {
        "decisions": {
            "total": decisions_total,
            "window": LOG_WINDOW,
            "window_note": WINDOW_NOTE_TEMPLATE.format(total=decisions_total),
            "dept_counts": dept_counts,
            "rows": decision_rows,
        },
        "events": {
            "total": events_total,
            "window": LOG_WINDOW,
            "window_note": WINDOW_NOTE_TEMPLATE.format(total=events_total),
            "kind_counts": kind_counts,
            "rows": event_rows,
        },
    }

    # Sync — coordinator / rewards / dashboard / diagnostics freshness.
    coordinator_exported_at = _read_export_ts(export_dir, "coordinator.json")
    rewards_exported_at = _read_export_ts(export_dir, "rewards.json")
    dashboard_exported_at = _read_export_ts(export_dir, "dashboard.json")
    diagnostics_exported_at = _read_export_ts(export_dir, "diagnostics.json")
    stale = any(
        ts is None or (now - ts) > STALE_EXPORT_S
        for ts in (coordinator_exported_at, rewards_exported_at,
                   dashboard_exported_at, diagnostics_exported_at))

    return {
        "exported_at": now,
        "source_db_user_version": user_version,
        "mode": mode,
        "emergency_stop": bool(atlas_cfg.get("emergency_stop")),
        "scope": SCOPE_LINE,
        "network": {
            "users": users_count,
            "workers": coord["workers"],
            "worker_rows": worker_rows,
            "hashrate": coord["hashrate"],
            "shares": coord["shares"],
            "monitoring_uptime": {
                "seconds": uptime_seconds,
                "display": _fmt_duration(uptime_seconds),
                "metrics_first_ts": metrics_first_ts,
                "metrics_last_ts": metrics_last_ts,
                "metrics_rows": metrics_count,
            },
            "daemon_restarts_24h": restarts_24h,
            "daemon_restarts_all_time": restarts_all,
            "daemon_uptime": {"value": None, "reason": DAEMON_UPTIME_REASON},
        },
        "mining": {
            # Earnings block reused verbatim from the dashboard export
            # (D-M8-2) — never recomputed here.
            "earnings": dash["earnings"],
            "xmr_mined_piconero": totals["total_user_rewards_piconero"],
            "confirmed_piconero": totals["total_user_rewards_piconero"],
            "pending_piconero": pending_piconero,
            "pending_note": ("Gross piconero of open/held (unsettled) "
                             "batches; contributes nothing to confirmed "
                             "earnings"),
            "user_allocations_piconero": totals["total_user_rewards_piconero"],
            "referral_rewards_piconero": totals["total_referral_rewards_piconero"],
            "atlas_revenue_piconero": totals["total_atlas_share_piconero"],
            "pool_fees_piconero": totals["total_pool_fees_piconero"],
            "payout_volume_piconero": totals["total_payouts_piconero"],
            "payouts_count": len(payout_rows),
            "failed_payouts": failed_payouts,
            "batches": {
                "open": totals["batches_open"],
                "settled": totals["batches_settled"],
                "held": totals["batches_held"],
            },
            "balances": dash["balances"],
            "lifetime": dash["lifetime"],
            "host_verified_totals": dash["host_verified_totals"],
        },
        "infrastructure": {
            "resources": resources,
            "db_health": db_health,
            "queues": {"value": None, "reason": QUEUE_REASON},
            "connectivity": connectivity,
            "services": services,
        },
        "security": security,
        "logs": logs,
        "sync": {
            "coordinator_exported_at": coordinator_exported_at,
            "rewards_exported_at": rewards_exported_at,
            "dashboard_exported_at": dashboard_exported_at,
            "diagnostics_exported_at": diagnostics_exported_at,
            "admin_exported_at": now,
            "stale": stale,
        },
        "provenance": {
            "network": "RECORDED (coordinator.json + dashboard.json)",
            "mining": "DERIVED (host) — ledger SUMs, SIMULATION-tagged",
            "infrastructure": "RECORDED (latest metrics row, PRAGMA, "
                              "pool_stats, diagnostics.json, snapshot.json, "
                              "watchdog log)",
            "security": "DERIVED (host) — design §4 definitions",
            "logs": "RECORDED (decisions / events latest-50 window)",
        },
    }


def _coordinator_status(con, atlas_cfg, pool_cfg):
    import atlas_coordinator
    return atlas_coordinator.coordinator_status(
        con, atlas_cfg=atlas_cfg, pool_cfg=pool_cfg)


def _dashboard_status(con, export_dir=None):
    import atlas_dashboard
    return atlas_dashboard.dashboard_status(con, export_dir=export_dir)


def _reward_totals(con):
    import atlas_rewards
    return atlas_rewards.reward_totals(con)


def connect(db_path=DB):
    """Open a connection with manual transaction control (autocommit mode),
    same pattern as atlas_coordinator.connect()."""
    con = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000.0)
    con.isolation_level = None
    con.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def export_admin_json(con=None, db_path=DB, export_path=EXPORT):
    """Write data/admin.json by atomic write (.tmp -> os.replace),
    the same pattern as the coordinator, rewards, and dashboard
    exports. The file is a derived export: deleting it loses nothing,
    it regenerates from the DB. The sibling source exports are read
    from the export path's own directory, so temp-DB exports in /tmp
    never read live files. Returns (path, payload)."""
    own_con = False
    if con is None:
        con = connect(db_path)
        own_con = True
    try:
        export_dir = os.path.dirname(os.path.abspath(export_path))
        payload = admin_status(con, export_dir=export_dir)
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

def _open():
    return connect(DB)


def cmd_status(_args):
    con = _open()
    try:
        payload = admin_status(con)
    finally:
        con.close()
    print(json.dumps(payload, indent=2))
    print("Hashrate: not measured (Gate 1 unmeasured — no probe measurement exists)")
    print("Estimated earnings: none (Cannot estimate — hashrate not measured)")
    return 0


def cmd_export(_args):
    path, payload = export_admin_json()
    print(f"Exported {path} (exported_at {payload['exported_at']}, "
          f"users {payload['network']['users']}, "
          f"workers {payload['network']['workers']['total']}, "
          f"suspicious {payload['security']['suspicious_workers']['count']}, "
          f"sync stale={payload['sync']['stale']})")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="ATLAS host admin (Master Mission 8) — read-only derivation, simulation only.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="print derived admin state")
    sub.add_parser("export", help="write data/admin.json (atomic)")

    args = parser.parse_args(argv)
    handlers = {"status": cmd_status, "export": cmd_export}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
