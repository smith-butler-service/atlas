#!/usr/bin/env python3
"""ATLAS HOST DASHBOARD MODULE — Master Mission 7, Lane C (host-side,
stdlib only).

A READ-ONLY derivation of the dashboard state from the live DB. It writes
no ledger rows, no decisions, no shares, no batches, no sessions — the
only write this module ever performs is the atomic export of
``data/dashboard.json`` itself (temp file + os.replace, same pattern as
the coordinator and rewards exports).

Derivation rules (binding):
  - Reuses coordinator_status() and reward_totals()/balances() from the
    existing modules — their logic is imported, never duplicated.
  - Every hashrate figure is "not measured" until a real Gate 1 probe
    measurement exists. ``current_hps`` / ``average_hps`` are always
    None in this mission; estimated earnings are NEVER computed — not
    from pool-wide hashrate, not from any guess. estimated_piconero is
    always None while Gate 1 is unmeasured.
  - Confirmed earnings are ledger SUMs only (user allocations), and are
    labelled SIMULATION ONLY while config mode is simulation-only.
  - All money is integer piconero (1 XMR = 10^12 piconero), never float.
    The one float in this module is the pool-share acceptance ratio
    (a ratio, not money).
  - Efficiency counts POOL shares only (origin='pool'). Local-test
    shares are diagnostics, never earnings evidence, never efficiency.
  - Duration counts DESKTOP-AGENT worker sessions only (kind='worker',
    browser-probe sessions excluded — design D-M7-4): ended sessions
    contribute ended_at - created_at (degenerate rows 0); open sessions
    contribute now - created_at, up to the export time. Same formula as
    coordinator_status() worker_sessions_duration_seconds.
  - ``sync.stale`` is true when either source export (coordinator.json
    or rewards.json, read from the same directory as the dashboard
    export) is missing or older than 3600 s.

Usage:
    python3 core/atlas_dashboard.py status
    python3 core/atlas_dashboard.py export

Stdlib only. Portable by copying ~/workspace/atlas.
"""
import argparse
import json
import os
import sqlite3
import sys
import time

BASE = os.path.expanduser("~/workspace/atlas")
CFG_ATLAS = os.path.join(BASE, "config", "atlas.json")
CFG_POOL = os.path.join(BASE, "config", "pool-rewards.json")
DB = os.path.join(BASE, "data", "atlas.db")
EXPORT = os.path.join(BASE, "data", "dashboard.json")
DATA_DIR = os.path.join(BASE, "data")

STALE_AFTER_S = 3600          # source exports older than this are stale
BUSY_TIMEOUT_MS = 5000

HASHRATE_NOTE = "Gate 1 unmeasured — no probe measurement exists"
ESTIMATE_REASON = "Cannot estimate — hashrate not measured"
CONFIRMED_NOTE_SIMULATION = "SIMULATION ONLY — no pool rewards"
CONFIRMED_NOTE_LIVE = "Live — confirmed pool rewards only"
EFFICIENCY_NO_SHARES_REASON = "Cannot compute — no pool shares yet"


def _now():
    return int(time.time())


def _read_export_ts(export_dir, filename):
    """exported_at from a sibling export file, or None when the file is
    missing, unparseable, or carries no integer exported_at."""
    path = os.path.join(export_dir, filename)
    try:
        with open(path) as f:
            payload = json.load(f)
        ts = payload.get("exported_at")
        if isinstance(ts, bool) or not isinstance(ts, int):
            return None
        return ts
    except (OSError, ValueError):
        return None


def dashboard_status(con, export_dir=None):
    """Derive the dashboard state object from the tables + configs.

    Read-only: performs SELECTs only (plus the config reads inside
    coordinator_status / reward_totals). ``export_dir`` is where the
    sibling coordinator.json / rewards.json exports live; it defaults
    to the live data dir and is the directory of the dashboard export
    path when called via export_dashboard_json()."""
    if export_dir is None:
        export_dir = DATA_DIR
    atlas_cfg, pool_cfg = _load_configs()
    user_version = con.execute("PRAGMA user_version").fetchone()[0]
    now = _now()
    mode = pool_cfg.get("mode", "simulation-only")
    simulation_only = mode == "simulation-only"

    # Coordinator state (workers + shares) — reused, not recomputed.
    coord = _coordinator_status(con, atlas_cfg, pool_cfg)
    shares = coord["shares"]
    workers = coord["workers"]

    # Duration over desktop-agent worker sessions only (design D-M7-4,
    # binding — same formula as coordinator_status): kind='worker' AND
    # NOT a browser probe; open sessions contribute up to now;
    # degenerate ended rows contribute 0.
    import atlas_coordinator as _ac
    total_seconds = 0
    active_sessions = 0
    for row in con.execute(
            "SELECT created_at, ended_at, expires_at, session_token_hash "
            "FROM sessions WHERE kind = 'worker'").fetchall():
        if row["session_token_hash"] == _ac.NO_CREDENTIAL_MARKER:
            continue  # browser probe — a local-test session, not mining
        created_at = row["created_at"]
        ended_at = row["ended_at"]
        expires_at = row["expires_at"]
        if ended_at is not None:
            total_seconds += max(ended_at - created_at, 0)
        else:
            total_seconds += max(now - created_at, 0)
            if expires_at is not None and expires_at > now:
                active_sessions += 1

    # Reward totals + balances — reused, never recomputed here.
    totals = _reward_totals(con)
    user_balances = _balances(con)

    # Payouts (Gate 4 is closed: no payout flow exists, so rows are 0
    # on the live DB; the table is still reported honestly).
    payout_rows = [{
        "id": row["id"],
        "user": row["user_id"],
        "amount": row["amount_piconero"],
        "status": row["status"],
        "ts": row["created_at"],
    } for row in con.execute(
        "SELECT id, user_id, amount_piconero, status, created_at "
        "FROM payouts ORDER BY id").fetchall()]
    payout_total = sum(r["amount"] for r in payout_rows)

    # Efficiency: pool shares only (local-test shares excluded).
    pool_accepted = shares["pool_accepted"]
    pool_rejected = shares["pool_rejected"]
    pool_total = pool_accepted + pool_rejected
    if pool_total == 0:
        efficiency = {"acceptance_rate": None,
                      "reason": EFFICIENCY_NO_SHARES_REASON}
    else:
        efficiency = {"acceptance_rate": pool_accepted / pool_total,
                      "reason": None}

    # Sync: source-export freshness from the same directory.
    coordinator_exported_at = _read_export_ts(export_dir, "coordinator.json")
    rewards_exported_at = _read_export_ts(export_dir, "rewards.json")
    pool_stats_recorded_at = con.execute(
        "SELECT MAX(recorded_at) FROM pool_stats").fetchone()[0]
    stale = (
        coordinator_exported_at is None
        or rewards_exported_at is None
        or (now - coordinator_exported_at) > STALE_AFTER_S
        or (now - rewards_exported_at) > STALE_AFTER_S
    )

    return {
        "exported_at": now,
        "source_db_user_version": user_version,
        "mode": mode,
        "emergency_stop": bool(atlas_cfg.get("emergency_stop")),
        "hashrate": {
            "status": "not-measured",
            "current_hps": None,
            "average_hps": None,
            "note": HASHRATE_NOTE,
        },
        "shares": shares,
        "duration": {
            "total_session_seconds": total_seconds,
            "active_sessions": active_sessions,
            "note": ("Desktop-agent worker sessions only (browser probes "
                     "excluded); ended sessions contribute "
                     "ended_at - created_at, open sessions contribute "
                     "now - created_at"),
        },
        "workers": workers,
        "earnings": {
            "estimated_piconero": None,
            "estimated_reason": ESTIMATE_REASON,
            "confirmed_piconero": totals["total_user_rewards_piconero"],
            "confirmed_note": (CONFIRMED_NOTE_SIMULATION if simulation_only
                               else CONFIRMED_NOTE_LIVE),
            "mode": mode,
        },
        "balances": user_balances,
        "lifetime": {
            "lifetime_user_rewards_piconero":
                totals["total_user_rewards_piconero"],
            "lifetime_referral_rewards_piconero":
                totals["total_referral_rewards_piconero"],
            "lifetime_atlas_share_piconero":
                totals["total_atlas_share_piconero"],
            "lifetime_pool_fees_piconero":
                totals["total_pool_fees_piconero"],
            "lifetime_payouts_piconero":
                totals["total_payouts_piconero"],
            "lifetime_reversals_piconero":
                totals["total_reversals_piconero"],
        },
        "payouts": {
            "count": len(payout_rows),
            "total_piconero": payout_total,
            "rows": payout_rows,
        },
        "efficiency": efficiency,
        "sync": {
            "coordinator_exported_at": coordinator_exported_at,
            "rewards_exported_at": rewards_exported_at,
            "pool_stats_recorded_at": pool_stats_recorded_at,
            "dashboard_exported_at": now,
            "stale": stale,
        },
        "host_verified_totals": {
            "ledger_entries": totals["ledger_entries"],
            "batches_settled": totals["batches_settled"],
            "total_user_rewards_piconero":
                totals["total_user_rewards_piconero"],
            "total_atlas_share_piconero":
                totals["total_atlas_share_piconero"],
        },
    }


def _load_configs():
    """Read both configs fresh on every call — never cached across passes."""
    with open(CFG_ATLAS) as f:
        atlas_cfg = json.load(f)
    with open(CFG_POOL) as f:
        pool_cfg = json.load(f)
    return atlas_cfg, pool_cfg


def _coordinator_status(con, atlas_cfg, pool_cfg):
    import atlas_coordinator
    return atlas_coordinator.coordinator_status(
        con, atlas_cfg=atlas_cfg, pool_cfg=pool_cfg)


def _reward_totals(con):
    import atlas_rewards
    return atlas_rewards.reward_totals(con)


def _balances(con):
    import atlas_rewards
    return atlas_rewards.balances(con)


def connect(db_path=DB):
    """Open a connection with manual transaction control (autocommit mode),
    same pattern as atlas_coordinator.connect()."""
    con = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000.0)
    con.isolation_level = None
    con.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def export_dashboard_json(con=None, db_path=DB, export_path=EXPORT):
    """Write data/dashboard.json by atomic write (.tmp -> os.replace),
    the same pattern as the coordinator and rewards exports. The file is
    a derived export: deleting it loses nothing, it regenerates from
    the DB. The sibling source exports are read from the export path's
    own directory, so temp-DB exports in /tmp never read live files.
    Returns (path, payload)."""
    own_con = False
    if con is None:
        con = connect(db_path)
        own_con = True
    try:
        export_dir = os.path.dirname(os.path.abspath(export_path))
        payload = dashboard_status(con, export_dir=export_dir)
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
        payload = dashboard_status(con)
    finally:
        con.close()
    print(json.dumps(payload, indent=2))
    print("Hashrate: not measured (Gate 1 unmeasured — no probe measurement exists)")
    print("Estimated earnings: none (Cannot estimate — hashrate not measured)")
    return 0


def cmd_export(_args):
    path, payload = export_dashboard_json()
    print(f"Exported {path} (exported_at {payload['exported_at']}, "
          f"confirmed {payload['earnings']['confirmed_piconero']} piconero, "
          f"sync stale={payload['sync']['stale']})")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="ATLAS host dashboard (Master Mission 7) — read-only derivation, simulation only.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="print derived dashboard state")
    sub.add_parser("export", help="write data/dashboard.json (atomic)")

    args = parser.parse_args(argv)
    handlers = {"status": cmd_status, "export": cmd_export}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
