#!/usr/bin/env python3
"""ATLAS monitor daemon — Stage 2, first working component.

Collects REAL host metrics every 60 s into SQLite (data/atlas.db) and a JSON
snapshot (data/snapshot.json). Stdlib only. No mining, no network calls, no
external dependencies. Safe to run on the shared bootstrap host: it only reads
/proc and writes local files.

Mission 1.1 hardening (2026-11-18):
- Persistent timestamped logging to logs/monitor.log with 1 MB rotation
  (three rotated copies kept since Mission 14; one before that, so the
  log can never grow without bound).
- Safe internal recovery for database failures: a corrupt database is
  QUARANTINED (renamed with a timestamp, never deleted or overwritten) and
  a fresh database is created only after integrity verification. A locked
  database is treated as transient, never as corrupt.
- The emergency stop is read from config/atlas.json on every cycle and is
  never changed by the monitor or by recovery.
- The monitor never crashes on a database error: it logs, attempts
  recovery, keeps writing the live snapshot, and retries next cycle.
"""
import json
import os
import shutil
import signal
import sqlite3
import sys
import time

BASE = os.path.expanduser("~/workspace/atlas")
DATA = os.path.join(BASE, "data")
LOGS = os.path.join(BASE, "logs")
DB = os.path.join(DATA, "atlas.db")
SNAP = os.path.join(DATA, "snapshot.json")
CONFIG = os.path.join(BASE, "config", "atlas.json")
LOG_FILE = os.path.join(LOGS, "monitor.log")
SHUTDOWN_FLAG = os.path.join(DATA, "shutdown.flag")
SHUTDOWN_FLAG_MAX_AGE = 600  # seconds; a stop request older than this is stale
MAX_LOG_BYTES = 1_048_576  # 1 MB; rotate to monitor.log.1/.2/.3 (three kept)
INTERVAL = 60

_sigterm_ignored = 0

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS metrics(
        ts INTEGER PRIMARY KEY, cpu REAL, mem_used_pct REAL,
        load1 REAL, load5 REAL, load15 REAL,
        disk_used_pct REAL, net_rx_bytes INTEGER, net_tx_bytes INTEGER)""",
    """CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, kind TEXT, message TEXT)""",
    """CREATE TABLE IF NOT EXISTS decisions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, dept TEXT,
        decision TEXT, reason TEXT)""",
]


def log(msg, path=None):
    """Append one timestamped line; rotate when the file exceeds 1 MB.

    Mission 14 retention: keep three rotated copies (.1/.2/.3) instead of
    one, so a traceback is not destroyed by the very next rotation.
    """
    if path is None:
        path = LOG_FILE
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path) and os.path.getsize(path) > MAX_LOG_BYTES:
            for n in (3, 2, 1):
                src = "%s.%d" % (path, n)
                if os.path.exists(src):
                    if n == 3:
                        os.remove(src)
                    else:
                        os.rename(src, "%s.%d" % (path, n + 1))
            os.rename(path, path + ".1")
        line = "%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), msg)
        with open(path, "a") as f:
            f.write(line)
    except Exception:
        # Logging must never break monitoring.
        pass


def _sigterm_handler(signum, frame):
    """Live daemon: a SIGTERM is ignored unless a fresh shutdown flag exists.

    Fix 2026-11-19 (user order "Fix"): the live daemon was SIGTERMed to death
    roughly every 2 h by an unknown sender (one confirmed case: a subagent's
    `pkill -f 'atlas_monitor.py'` smoke test, 2026-11-19 14:17 UTC). The
    watchdog restarted it each time, but every kill cost up to 5 min of
    monitoring plus a restart. Nothing in normal operation SIGTERMs the live
    daemon — recover.sh only starts it when dead, diagnostics kills only
    scratch daemons — so a stray SIGTERM is never legitimate. An operator
    who genuinely wants it stopped touches data/shutdown.flag (fresh, under
    10 min old) and then sends SIGTERM; the handler honors that, consumes
    the flag (one-shot), and exits cleanly. Scratch daemons (started with
    --scratch) keep the old behaviour — exit on SIGTERM — because
    diagnostics tests 10/11 assert exactly that. Raises SystemExit only on
    an authorized stop; otherwise returns and the cycle continues (PEP 475
    retries the interrupted sleep). This does NOT protect against SIGKILL,
    which no process can ignore; the watchdog still covers that case."""
    global _sigterm_ignored
    if "--scratch" in sys.argv:
        log("monitor STOP SIGTERM received, exiting")
        raise SystemExit(0)
    try:
        fresh = (time.time() - os.stat(SHUTDOWN_FLAG).st_mtime) < SHUTDOWN_FLAG_MAX_AGE
    except Exception:
        fresh = False
    if fresh:
        try:
            os.remove(SHUTDOWN_FLAG)
        except Exception:
            pass
        log("monitor STOP SIGTERM received (shutdown flag present), exiting")
        raise SystemExit(0)
    _sigterm_ignored += 1
    log("monitor SIGTERM IGNORED count=%d (live mode, no shutdown flag); staying alive"
        % _sigterm_ignored)


def load_config(path=CONFIG):
    """Read config; return {} on any failure (never crash, never write)."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        log("config READ FAIL %s: %s" % (path, e))
        return {}


def check_integrity(db_path):
    """Return (True, 'ok') or (False, error text). Read-only check.

    A missing file is not corrupt (it will be created). A locked file
    reports its lock error so the caller can treat it as transient.
    """
    if not os.path.exists(db_path):
        return (True, "ok")
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=5)
        try:
            row = con.execute("PRAGMA integrity_check").fetchone()
            return (row[0] == "ok", row[0])
        finally:
            con.close()
    except Exception:
        pass
    try:
        con = sqlite3.connect(db_path, timeout=5)
        try:
            row = con.execute("PRAGMA integrity_check").fetchone()
            return (row[0] == "ok", row[0])
        finally:
            con.close()
    except Exception as e:
        return (False, str(e))


def create_fresh_db(db_path):
    """Create a fresh database with the schema; verify integrity + writability.

    Returns (True, 'ok') or (False, error). Never touches any other file.
    The writability test inserts a row inside a transaction and rolls it
    back, so nothing persists.
    """
    try:
        con = sqlite3.connect(db_path, timeout=5)
        try:
            for stmt in SCHEMA:
                con.execute(stmt)
            con.commit()
            ok, detail = check_integrity(db_path)
            if not ok:
                return (False, "fresh db integrity failed: %s" % detail)
            con.execute("BEGIN")
            con.execute(
                "INSERT INTO events (ts, kind, message) VALUES (?, 'selftest', ?)",
                (int(time.time()), "fresh-db writability check"))
            con.execute("ROLLBACK")
            return (True, "ok")
        finally:
            con.close()
    except Exception as e:
        return (False, str(e))


def recover_database(db_path):
    """Recover a database that failed to write.

    - Integrity ok (or still locked after a retry) -> transient:
      return ('ok', None) so the caller retries the write.
    - Corrupt -> QUARANTINE the file (rename with timestamp, never delete
      or overwrite it, journal files moved alongside), create a fresh
      database, verify it, return ('recovered', quarantine_path).
    - Neither path works -> ('failed', error).
    """
    ok, detail = check_integrity(db_path)
    if not ok and ("locked" in detail.lower() or "busy" in detail.lower()):
        time.sleep(1)
        ok, detail = check_integrity(db_path)
    if ok:
        log("db RECOVER transient failure, integrity ok")
        return ("ok", None)
    if "locked" in detail.lower() or "busy" in detail.lower():
        log("db RECOVER still locked after retry, treating as transient")
        return ("ok", None)
    log("db RECOVER corrupt, integrity: %s" % detail)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    base, _ext = os.path.splitext(db_path)
    quarantine = "%s-corrupt-%s-%d.db" % (base, stamp, os.getpid())
    try:
        os.rename(db_path, quarantine)
        for suffix in ("-journal", "-wal", "-shm"):
            sidecar = db_path + suffix
            if os.path.exists(sidecar):
                os.rename(sidecar, quarantine + suffix)
    except Exception as e:
        log("db QUARANTINE FAIL %s: %s" % (db_path, e))
        return ("failed", str(e))
    log("db QUARANTINE corrupt db preserved at %s (never deleted)" % quarantine)
    good, detail = create_fresh_db(db_path)
    if not good:
        log("db RECOVER fresh db FAIL: %s" % detail)
        return ("failed", detail)
    log("db RECOVER fresh db created and verified at %s" % db_path)
    return ("recovered", quarantine)


def open_db(db_path):
    """Open (creating if needed) and ensure schema; return connection."""
    con = sqlite3.connect(db_path, timeout=5)
    for stmt in SCHEMA:
        con.execute(stmt)
    con.commit()
    return con


def write_metrics(con, row):
    con.execute("INSERT OR REPLACE INTO metrics VALUES (?,?,?,?,?,?,?,?,?)", row)
    con.commit()


def read_cpu():
    with open("/proc/stat") as f:
        vals = [int(x) for x in f.readline().split()[1:]]
    return sum(vals), vals[3]  # total ticks, idle ticks


def cpu_percent(prev):
    total, idle = read_cpu()
    if prev is None:
        return None, (total, idle)
    dt, di = total - prev[0], idle - prev[1]
    pct = 100.0 * (1 - di / dt) if dt else 0.0
    return pct, (total, idle)


def mem():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            info[k] = int(v.split()[0])  # kB
    total, avail = info["MemTotal"], info["MemAvailable"]
    return total, avail, 100.0 * (1 - avail / total)


def disk():
    u = shutil.disk_usage(BASE)
    return u.total, u.used, u.free


def net_bytes():
    rx = tx = 0
    with open("/proc/net/dev") as f:
        for line in f:
            if ":" not in line:
                continue
            rest = line.split(":", 1)[1].split()
            rx += int(rest[0])
            tx += int(rest[8])
    return rx, tx


def main():
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(LOGS, exist_ok=True)
    # Mission 14: log a SIGTERM before dying, so a signal kill leaves a
    # marker in the log (see _sigterm_handler). Guarded: if signal setup
    # is unavailable the daemon runs exactly as before.
    try:
        signal.signal(signal.SIGTERM, _sigterm_handler)
    except Exception:
        pass
    cfg = load_config()
    stop = cfg.get("emergency_stop", True)
    log("monitor START pid=%d db=%s emergency_stop=%s mining=disabled trading=paper-only"
        % (os.getpid(), DB, stop))
    if "--scratch" in sys.argv:
        log("monitor mode=scratch SIGTERM exits (diagnostics t10/t11)")
    else:
        log("monitor mode=live SIGTERM ignored unless data/shutdown.flag is fresh (<10 min)")
    # Open the database; recover first if it is corrupt at startup.
    con = None
    try:
        con = open_db(DB)
        ok, detail = check_integrity(DB)
        if not ok:
            log("db STARTUP integrity FAIL: %s" % detail)
            con.close()
            con = None
            status, info = recover_database(DB)
            if status == "failed":
                log("db STARTUP recovery FAILED: %s; continuing without db writes" % info)
            else:
                con = open_db(DB)
    except Exception as e:
        log("db STARTUP open FAIL: %s" % e)
        if con is not None:
            try:
                con.close()
            except Exception:
                pass
            con = None
        status, info = recover_database(DB)
        if status == "failed":
            log("db STARTUP recovery FAILED: %s; continuing without db writes" % info)
        else:
            try:
                con = open_db(DB)
            except Exception as e2:
                log("db STARTUP reopen FAIL: %s" % e2)
                con = None
    if con is not None:
        try:
            con.execute("INSERT INTO events (ts, kind, message) VALUES (?, 'startup', ?)",
                        (int(time.time()), "atlas_monitor started"))
            con.commit()
        except Exception as e:
            log("db STARTUP event FAIL: %s" % e)

    # Prime the CPU sampler so the first row already carries a real reading.
    prev_cpu = read_cpu()
    time.sleep(1)
    while True:
        ts = int(time.time())
        cpu, prev_cpu = cpu_percent(prev_cpu)
        mt, ma, mu = mem()
        l1, l5, l15 = os.getloadavg()
        dt_, du, df = disk()
        rx, tx = net_bytes()
        if cpu is None:
            cpu = 0.0
        row = (ts, round(cpu, 2), round(mu, 2), round(l1, 2), round(l5, 2),
               round(l15, 2), round(100.0 * du / dt_, 2), rx, tx)
        db_ok = False
        if con is not None:
            try:
                write_metrics(con, row)
                db_ok = True
            except Exception as e:
                log("db WRITE FAIL ts=%d: %s" % (ts, e))
                status, info = recover_database(DB)
                if status == "recovered":
                    try:
                        con.close()
                    except Exception:
                        pass
                    try:
                        con = open_db(DB)
                        write_metrics(con, row)
                        db_ok = True
                        log("db WRITE recovered after quarantine %s" % info)
                    except Exception as e2:
                        log("db WRITE retry FAIL ts=%d: %s" % (ts, e2))
                        con = None
                elif status == "ok":
                    try:
                        write_metrics(con, row)
                        db_ok = True
                        log("db WRITE recovered after transient failure ts=%d" % ts)
                    except Exception as e2:
                        log("db WRITE retry FAIL ts=%d: %s" % (ts, e2))
                else:
                    log("db WRITE recovery FAILED: %s; continuing without db" % info)
                    try:
                        con.close()
                    except Exception:
                        pass
                    con = None
        else:
            # No database connection (startup recovery failed): try again.
            try:
                con = open_db(DB)
                ok, detail = check_integrity(DB)
                if not ok:
                    log("db RECONNECT integrity FAIL: %s" % detail)
                    con.close()
                    con = None
                else:
                    write_metrics(con, row)
                    db_ok = True
                    log("db RECONNECTED ts=%d" % ts)
            except Exception as e:
                log("db RECONNECT FAIL ts=%d: %s" % (ts, e))
                con = None
        # Re-read config each cycle so the stop state stays authoritative.
        cfg = load_config()
        stop = cfg.get("emergency_stop", True)
        snap = {
            "ts": ts,
            "cpu_pct": round(cpu, 2),
            "mem_total_kb": mt, "mem_avail_kb": ma, "mem_used_pct": round(mu, 2),
            "load": [round(l1, 2), round(l5, 2), round(l15, 2)],
            "disk_total": dt_, "disk_used": du, "disk_free": df,
            "disk_used_pct": round(100.0 * du / dt_, 2),
            "net_rx_bytes": rx, "net_tx_bytes": tx,
            "gpu": None,
            "mining": "disabled",
            "trading": "disabled-paper-only",
            "emergency_stop": stop,
        }
        tmp = SNAP + ".tmp"
        with open(tmp, "w") as f:
            json.dump(snap, f)
        os.replace(tmp, SNAP)
        log("cycle ts=%d cpu=%.2f mem=%.2f db=%s stop=%s"
            % (ts, cpu, mu, "ok" if db_ok else "FAIL", stop))
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
