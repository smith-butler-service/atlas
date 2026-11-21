#!/usr/bin/env python3
"""ATLAS CORE — coordinator skeleton (Stage 2).

Owns: config, operational state, decision log, emergency stop, status CLI.
Enforces the hard rules: mining disabled on this host, trading paper-only with
$0 eligible capital, emergency stop ON by default. Stdlib only.

Usage:
    python3 core/atlas_core.py status    # print real state from data/atlas.db
    python3 core/atlas_core.py decide    # run one coordination pass, log decisions
"""
import json
import os
import sqlite3
import sys
import time

BASE = os.path.expanduser("~/workspace/atlas")
CFG = os.path.join(BASE, "config", "atlas.json")
DB = os.path.join(BASE, "data", "atlas.db")
SNAP = os.path.join(BASE, "data", "snapshot.json")


def load_config():
    with open(CFG) as f:
        return json.load(f)


def log_decision(con, dept, decision, reason):
    con.execute("INSERT INTO decisions (ts, dept, decision, reason) VALUES (?,?,?,?)",
                (int(time.time()), dept, decision, reason))
    con.commit()


def status():
    cfg = load_config()
    print(f"ATLAS CORE v{cfg['version']} — emergency_stop={'ON' if cfg['emergency_stop'] else 'OFF'}")
    print(f"Mining: {'ENABLED' if cfg['mining']['enabled'] else 'DISABLED'} ({cfg['mining']['reason']})")
    print(f"Trading: {cfg['trading']['mode']}; eligible capital ${cfg['trading']['eligible_capital_usd']}")
    if os.path.exists(SNAP):
        with open(SNAP) as f:
            s = json.load(f)
        print(f"Last snapshot {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(s['ts']))}: "
              f"CPU {s['cpu_pct']}% | MEM {s['mem_used_pct']}% | "
              f"load {s['load']} | disk {s['disk_used_pct']}% | GPU {s['gpu']}")
    else:
        print("No snapshot yet — monitor daemon not running.")
    if os.path.exists(DB):
        con = sqlite3.connect(DB)
        n = con.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
        print(f"Metrics rows in DB: {n}")
        for row in con.execute(
                "SELECT ts, dept, decision, reason FROM decisions ORDER BY id DESC LIMIT 5"):
            print("  decision:", time.strftime('%H:%M:%S', time.localtime(row[0])),
                  row[1], "—", row[2], "|", row[3])
        con.close()


def decide():
    """One coordination pass. Every decision is logged with its reason."""
    cfg = load_config()
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS decisions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, dept TEXT,
        decision TEXT, reason TEXT)""")
    if cfg["emergency_stop"]:
        log_decision(con, "core", "hold-all-live-activity",
                     "emergency stop ON: no mining, no trading, monitoring only")
    if not cfg["mining"]["enabled"]:
        log_decision(con, "mining", "stay-disabled",
                     cfg["mining"]["reason"])
    if not cfg["trading"]["enabled"]:
        log_decision(con, "trading", "stay-paper-only",
                     "eligible capital $0; funding rule forbids any other source")
    if os.path.exists(SNAP):
        with open(SNAP) as f:
            s = json.load(f)
        if s["cpu_pct"] > cfg["limits"]["max_cpu_pct"]:
            log_decision(con, "scheduler", "throttle-background-work",
                         f"CPU {s['cpu_pct']}% over {cfg['limits']['max_cpu_pct']}% cap")
        else:
            log_decision(con, "scheduler", "no-throttle-needed",
                         f"CPU {s['cpu_pct']}% within cap")
    con.close()
    print("Coordination pass logged.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
    elif cmd == "decide":
        decide()
    else:
        print("usage: atlas_core.py [status|decide]")
        sys.exit(2)
