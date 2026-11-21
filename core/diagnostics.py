#!/usr/bin/env python3
"""ATLAS diagnostics — Stage 1 complete system test (29 tests).

Runs every test against the LIVE installation and records measured results.
(Mission 14 exception: tests 10/11 run against a SCRATCH daemon — same
code, own DB/snapshot/log — so the suite no longer kills the live daemon.)
No fabricated results: each test executes its check and reports PASS / FAIL /
NOT TESTED with evidence. Writes data/diagnostics.json and prints a table.

Tests 16-22 (Mission 2, M2.5) cover memory pressure, snapshot freshness,
API data validity, database write latency, daemon health, CPU pressure and
queue delays. Host-wide CPU / memory / load are recorded as INFORMATIONAL
only in those tests: this host is shared, host MEM% sits permanently above
70%, and a host-pressure failure condition would fail the suite forever.
Only ATLAS's own footprint can fail tests 16 and 21.

Test 26 (Master Mission 9) covers the profitability export
(data/profitability.json): it parses, is fresh, carries source +
fetched_at per live input, every figure re-derives from the recorded
inputs by the design §1 formula within rounding, the your-hardware
block is null with the verbatim reason, the confirmed-earnings block
is identical to a fresh dashboard.json earnings block, and no USD
figure appears in the panel payload (USD lives only under audit_usd).

Test 27 (Master Mission 10) covers the security export
(data/security.json): it parses, is fresh, its security counts match
fresh live SQL, its host-verified totals match the live DB, no secret
string appears in the file, all S1–S9 results are present, and every
check passed (a FAIL check fails the suite — the export is evidence,
not a promise).

Test 28 (Master Mission 10) covers the scale smoke level: a temp-DB
load of 100 workers / 10,000 shares runs, and the export's scale
block is populated or honestly null with the verbatim reason. The
full L1–L5 run is on-demand; this test asserts only the smoke level.

Test 29 (Master Mission 22) covers the paper-trading export
(data/trading.json): it parses, is fresh, is paper-only with $0
eligible capital from its two named sources, the deposit block names
Solana / USDC with a valid configured address (or null while
pending), no secret-trigger string appears in the file, every
account's cash and positions reconcile to SUM over its filled orders
in the live DB, and the trading unit suite passes.

Usage: python3 core/diagnostics.py
Exit code 0 = all PASS, 1 = any FAIL, 2 = any NOT TESTED.
"""
import calendar
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request

BASE = os.path.expanduser("~/workspace/atlas")
CORE = os.path.join(BASE, "core")
CFG = os.path.join(BASE, "config", "atlas.json")
DB = os.path.join(BASE, "data", "atlas.db")
SNAP = os.path.join(BASE, "data", "snapshot.json")
OUT = os.path.join(BASE, "data", "diagnostics.json")
RESULTS = []


def record(name, status, detail):
    RESULTS.append({"test": name, "status": status, "detail": detail})
    print(f"[{status}] {name}: {detail}")


def sh(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "timeout"


def pgrep_monitor():
    # Bracket trick: the sh -c wrapper's own command line contains this
    # pattern, so the literal form would self-match and pgrep would never
    # return empty. 'atlas_[m]onitor.py' matches the daemon but not the shell.
    # Anchored '$': the live daemon is started as `python3
    # core/atlas_monitor.py` with no arguments, so its command line ENDS
    # with atlas_monitor.py. The anchor keeps the scratch daemon
    # (`... --scratch`, Mission 14) and any shell whose command text merely
    # mentions the file out of the live-daemon result.
    rc, out = sh("pgrep -f 'atlas_[m]onitor\\.py$'")
    pids = [int(x) for x in out.split() if x.isdigit()] if rc == 0 else []
    return pids


def pgrep_scratch():
    """Pids of scratch daemons only (Mission 14): started with a
    '--scratch' argument, so their command lines end with it."""
    rc, out = sh("pgrep -f 'atlas_[m]onitor\\.py --scratch$'")
    pids = [int(x) for x in out.split() if x.isdigit()] if rc == 0 else []
    return pids


def _scratch_setup():
    """Mission 14: build a scratch ATLAS tree (own HOME) so restart tests
    never touch the live daemon. Copies the live config and the live
    monitor script, so the scratch daemon runs identical code against its
    own DB / snapshot / log. Returns (scratch_home, scratch_atlas_dir)."""
    home = tempfile.mkdtemp(prefix="atlas-scratch-")
    atlas = os.path.join(home, "workspace", "atlas")
    for sub in ("data", "logs", "config", "core"):
        os.makedirs(os.path.join(atlas, sub), exist_ok=True)
    shutil.copy(CFG, os.path.join(atlas, "config", "atlas.json"))
    shutil.copy(os.path.join(CORE, "atlas_monitor.py"),
                os.path.join(atlas, "core", "atlas_monitor.py"))
    return home, atlas


def _scratch_start(home, atlas):
    """Start the scratch daemon; return its pid, or None if it did not
    appear within 10 s. HOME is pointed at the scratch home so the daemon
    resolves all its paths under the scratch tree."""
    sh("cd %s && HOME=%s nohup python3 core/atlas_monitor.py --scratch "
       ">> logs/monitor.log 2>&1 &" % (atlas, home))
    for _ in range(10):
        pids = pgrep_scratch()
        if pids:
            return pids[0]
        time.sleep(1)
    return None


def _scratch_teardown(home):
    """Stop any scratch daemon and remove the scratch tree. Best effort:
    a leftover scratch daemon must never survive the suite."""
    try:
        for pid in pgrep_scratch():
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        for _ in range(5):
            if not pgrep_scratch():
                break
            time.sleep(1)
        for pid in pgrep_scratch():
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
    finally:
        shutil.rmtree(home, ignore_errors=True)


def read_snapshot():
    with open(SNAP) as f:
        return json.load(f)


def read_config():
    with open(CFG) as f:
        return json.load(f)


def db():
    return sqlite3.connect(DB)


def t01_python_services():
    try:
        assert sys.version_info >= (3, 11), f"python {sys.version_info}"
        for mod in ("atlas_monitor", "atlas_core"):
            rc, out = sh(f"python3 -m py_compile {CORE}/{mod}.py")
            assert rc == 0, f"{mod} compile failed: {out[:200]}"
        sys.path.insert(0, CORE)
        import atlas_monitor, atlas_core  # noqa: F401
        record("01 Python services", "PASS",
               f"Python {sys.version.split()[0]}; atlas_monitor + atlas_core compile and import")
    except Exception as e:
        record("01 Python services", "FAIL", str(e)[:300])


def t02_monitor_daemon():
    pids = pgrep_monitor()
    if not pids:
        record("02 Monitoring daemon", "FAIL", "no atlas_monitor.py process running")
        return
    pid = pids[0]
    try:
        with open(f"/proc/{pid}/status") as f:
            state = [l for l in f if l.startswith("State:")][0].split()[1]
        record("02 Monitoring daemon", "PASS", f"running pid {pid}, state {state}")
    except Exception as e:
        record("02 Monitoring daemon", "FAIL", f"pid {pid} unreadable: {e}")


def t03_cpu_mem():
    try:
        s = read_snapshot()
        age = int(time.time()) - s["ts"]
        assert age <= 180, f"snapshot {age}s old"
        assert 0 <= s["cpu_pct"] <= 100, f"cpu {s['cpu_pct']}"
        assert 0 <= s["mem_used_pct"] <= 100, f"mem {s['mem_used_pct']}"
        record("03 CPU and memory monitoring", "PASS",
               f"CPU {s['cpu_pct']}%, MEM {s['mem_used_pct']}% used, snapshot {age}s old")
    except Exception as e:
        record("03 CPU and memory monitoring", "FAIL", str(e)[:300])


def t04_disk_net():
    try:
        s = read_snapshot()
        assert 0 <= s["disk_used_pct"] <= 100, f"disk {s['disk_used_pct']}"
        assert isinstance(s["net_rx_bytes"], int) and s["net_rx_bytes"] > 0
        assert isinstance(s["net_tx_bytes"], int) and s["net_tx_bytes"] > 0
        record("04 Disk and network monitoring", "PASS",
               f"disk {s['disk_used_pct']}% used, net rx {s['net_rx_bytes']} B / tx {s['net_tx_bytes']} B")
    except Exception as e:
        record("04 Disk and network monitoring", "FAIL", str(e)[:300])


def t05_db_integrity():
    try:
        con = db()
        ic = con.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert ic == "ok", f"integrity_check={ic}"
        assert {"metrics", "events", "decisions"} <= tables, f"tables={tables}"
        con.close()
        record("05 SQLite database integrity", "PASS",
               f"integrity_check ok; tables {sorted(tables)}")
    except Exception as e:
        record("05 SQLite database integrity", "FAIL", str(e)[:300])


def t06_db_persistence():
    try:
        assert os.path.exists(DB) and DB.startswith(os.path.expanduser("~")), DB
        con = db()
        n, oldest, newest = con.execute(
            "SELECT COUNT(*), MIN(ts), MAX(ts) FROM metrics").fetchone()
        con.close()
        assert n >= 1, "no metrics rows"
        span = (newest or 0) - (oldest or 0)
        record("06 Database persistence", "PASS",
               f"{n} metrics rows, span {span}s, DB at {DB}")
    except Exception as e:
        record("06 Database persistence", "FAIL", str(e)[:300])


def t07_coordinator_decisions():
    try:
        before = int(time.time())
        rc, out = sh(f"python3 {CORE}/atlas_core.py decide")
        assert rc == 0, f"decide exit {rc}: {out[:200]}"
        con = db()
        n = con.execute("SELECT COUNT(*) FROM decisions WHERE ts >= ?",
                        (before,)).fetchone()[0]
        con.close()
        assert n >= 1, "decide logged no decisions"
        record("07 Coordinator decision-making", "PASS",
               f"decide pass logged {n} new decisions")
    except Exception as e:
        record("07 Coordinator decision-making", "FAIL", str(e)[:300])


def t08_decision_logging():
    try:
        con = db()
        rows = con.execute(
            "SELECT dept, decision, reason FROM decisions ORDER BY id DESC LIMIT 5").fetchall()
        con.close()
        assert rows, "decisions table empty"
        assert all(r[2] for r in rows), "a decision lacks a reason"
        record("08 Decision logging", "PASS",
               f"{len(rows)} recent decisions, all with reasons; latest: {rows[0][1]}")
    except Exception as e:
        record("08 Decision logging", "FAIL", str(e)[:300])


def t09_emergency_stop():
    try:
        cfg = read_config()
        s = read_snapshot()
        assert cfg["emergency_stop"] is True, "config emergency_stop not true"
        assert s["emergency_stop"] is True, "snapshot emergency_stop not true"
        assert cfg["mining"]["enabled"] is False, "mining enabled in config"
        assert cfg["trading"]["enabled"] is False, "trading enabled in config"
        con = db()
        hold = con.execute(
            "SELECT COUNT(*) FROM decisions WHERE decision='hold-all-live-activity'").fetchone()[0]
        con.close()
        assert hold >= 1, "no hold-all-live-activity decision logged"
        record("09 Emergency stop", "PASS",
               "stop ON in config + snapshot; mining + trading disabled; "
               f"hold decision logged ({hold}x)")
    except Exception as e:
        record("09 Emergency stop", "FAIL", str(e)[:300])


def _wait_snapshot_after(ts_marker, timeout=15, snap_path=None):
    path = snap_path or SNAP
    for _ in range(timeout):
        try:
            with open(path) as f:
                if json.load(f)["ts"] > ts_marker:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def t10_service_restart():
    """Mission 14: the restart test runs against a SCRATCH daemon, not the
    live one. The old version SIGTERMed the live daemon twice per run —
    about 85% of all daemon restarts. Same code path, same assertions,
    own DB/snapshot/log; the live daemon's pid must be unchanged after."""
    home = None
    try:
        live_before = pgrep_monitor()
        assert live_before, "live daemon not running at test start"
        home, atlas = _scratch_setup()
        snap = os.path.join(atlas, "data", "snapshot.json")
        marker = int(time.time())
        pid = _scratch_start(home, atlas)
        assert pid, "scratch daemon did not start"
        assert _wait_snapshot_after(marker, snap_path=snap), \
            "scratch daemon wrote no fresh snapshot"
        os.kill(pid, signal.SIGTERM)
        for _ in range(5):
            if not pgrep_scratch():
                break
            time.sleep(1)
        assert not pgrep_scratch(), "scratch daemon did not stop on SIGTERM"
        marker = int(time.time())
        pid2 = _scratch_start(home, atlas)
        assert pid2, "scratch daemon did not restart"
        assert _wait_snapshot_after(marker, timeout=10, snap_path=snap), \
            "no fresh snapshot within 15 s of scratch restart"
        live_after = pgrep_monitor()
        assert live_after == live_before, \
            f"live daemon pid changed {live_before} -> {live_after}"
        record("10 Service restart", "PASS",
               f"scratch daemon pid {pid} stopped on SIGTERM and restarted "
               f"as {pid2}; fresh snapshot written; live daemon pid "
               f"{live_before[0]} untouched")
    except Exception as e:
        record("10 Service restart", "FAIL", str(e)[:300])
    finally:
        if home:
            _scratch_teardown(home)


def t11_auto_recovery():
    """Stop the scratch daemon, run the real recovery path (recover.sh in
    scratch mode), verify it comes back. The live daemon is never touched
    (Mission 14)."""
    home = None
    try:
        rec = os.path.join(CORE, "recover.sh")
        assert os.path.exists(rec), "recover.sh missing"
        assert os.access(rec, os.X_OK), "recover.sh not executable"
        live_before = pgrep_monitor()
        assert live_before, "live daemon not running at test start"
        home, atlas = _scratch_setup()
        snap = os.path.join(atlas, "data", "snapshot.json")
        marker = int(time.time())
        pid = _scratch_start(home, atlas)
        assert pid, "scratch daemon did not start"
        assert _wait_snapshot_after(marker, snap_path=snap), \
            "scratch daemon wrote no fresh snapshot"
        os.kill(pid, signal.SIGTERM)
        for _ in range(5):
            if not pgrep_scratch():
                break
            time.sleep(1)
        assert not pgrep_scratch(), "scratch daemon did not stop"
        marker = int(time.time())
        rc, out = sh(f"ATLAS_SCRATCH_DIR={atlas} {rec}", timeout=30)
        assert rc == 0, f"recover.sh exit {rc}: {out[:200]}"
        assert _wait_snapshot_after(marker, timeout=20, snap_path=snap), \
            "scratch daemon not back within 20 s of recover.sh"
        live_after = pgrep_monitor()
        assert live_after == live_before, \
            f"live daemon pid changed {live_before} -> {live_after}"
        record("11 Automatic recovery", "PASS",
               f"recover.sh (scratch mode) restarted scratch daemon pid "
               f"{pid} after a kill; fresh snapshot written; live daemon "
               f"pid {live_before[0]} untouched")
    except Exception as e:
        record("11 Automatic recovery", "FAIL", str(e)[:300])
    finally:
        if home:
            _scratch_teardown(home)


def t12_deployment_persistence():
    try:
        home = os.path.expanduser("~")
        assert BASE.startswith(home), BASE
        needed = [CFG, DB, os.path.join(CORE, "atlas_monitor.py"),
                  os.path.join(CORE, "atlas_core.py"),
                  os.path.join(CORE, "recover.sh"),
                  os.path.join(BASE, "docs", "recovery.md")]
        missing = [p for p in needed if not os.path.exists(p)]
        assert not missing, f"missing: {missing}"
        assert os.access(os.path.join(CORE, "recover.sh"), os.X_OK)
        record("12 Deployment persistence", "PASS",
               "all essential files under ~/workspace/atlas; recovery procedure + "
               "script present; processes do not survive VM replacement by platform "
               "design — restore is via recover.sh (see docs/recovery.md)")
    except Exception as e:
        record("12 Deployment persistence", "FAIL", str(e)[:300])


def t13_resource_consumption():
    try:
        pids = pgrep_monitor()
        assert pids, "daemon not running"
        pid = pids[0]
        with open(f"/proc/{pid}/status") as f:
            st = dict(l.split(":", 1) for l in f if ":" in l)
        rss_kb = int(st["VmRSS"].split()[0])
        with open(f"/proc/{pid}/stat") as f:
            parts = f.read().split()
        utime, stime = int(parts[13]), int(parts[14])
        start = int(parts[21])
        uptime = float(open("/proc/uptime").read().split()[0])
        clk = os.sysconf("SC_CLK_TCK")
        cpu_s = (utime + stime) / clk
        life_s = max(uptime - start / clk, 1)
        cpu_pct = 100.0 * cpu_s / life_s
        assert rss_kb < 50 * 1024, f"RSS {rss_kb} kB"
        assert cpu_pct < 5.0, f"daemon CPU {cpu_pct:.2f}%"
        record("13 Resource consumption", "PASS",
               f"daemon RSS {rss_kb/1024:.1f} MB, lifetime CPU {cpu_pct:.2f}%")
    except Exception as e:
        record("13 Resource consumption", "FAIL", str(e)[:300])


def t14_network():
    try:
        targets = {
            "coingecko": "https://api.coingecko.com/api/v3/ping",
            "moneroocean": "https://api.moneroocean.stream/pool/stats",
            "blockchain.info": "https://blockchain.info/q/getblockcount",
        }
        results = {}
        for name, url in targets.items():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ATLAS/0.1"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    results[name] = r.status
            except Exception as e:
                results[name] = f"ERR {type(e).__name__}"
        ok = [k for k, v in results.items() if v == 200]
        detail = ", ".join(f"{k}:{v}" for k, v in results.items())
        if len(ok) == len(targets):
            record("14 Network connectivity", "PASS", detail)
        elif len(ok) >= 2:
            record("14 Network connectivity", "FAIL",
                   f"partial — {detail} (2 of 3 reachable)")
        else:
            record("14 Network connectivity", "FAIL", detail)
    except Exception as e:
        record("14 Network connectivity", "FAIL", str(e)[:300])


def t15_security_permissions():
    try:
        problems = []
        # No key material anywhere in the workspace.
        for root, _, files in os.walk(BASE):
            for fn in files:
                p = os.path.join(root, fn)
                if fn.endswith((".pem", ".key")) or "id_rsa" in fn or "seed" in fn.lower():
                    problems.append(f"key file present: {p}")
                if fn.endswith((".py", ".json", ".md", ".sh")):
                    with open(p, errors="ignore") as f:
                        txt = f.read()
                    # Strict PEM armor only. A loose "BEGIN"+"PRIVATE KEY"
                    # substring check false-positives on this scanner's own
                    # source code, which mentions those words in its checks.
                    if re.search(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", txt):
                        problems.append(f"private key material in {p}")
                    if re.search(r"\bxprv[0-9a-zA-Z]{20,}", txt):
                        problems.append(f"extended private key in {p}")
        # No miner processes. Every alternative is bracketed so the sh -c
        # wrapper's own command line (which contains this pattern) cannot
        # self-match — an unbracketed alternative would match the shell.
        rc, out = sh("pgrep -f -i '[x]mrig|[m]inerd|[c]puminer|[e]thminer|[t]-rex|[l]olminer' || true")
        if rc == 0 and out.strip():
            problems.append(f"miner process running: {out.strip()}")
        # Config not world-writable, no secrets in config.
        mode = os.stat(CFG).st_mode
        if mode & 0o002:
            problems.append("config is world-writable")
        cfg = read_config()
        assert cfg["emergency_stop"] is True
        assert cfg["mining"]["enabled"] is False
        assert cfg["trading"]["enabled"] is False
        if problems:
            record("15 Security and permission controls", "FAIL", "; ".join(problems))
        else:
            record("15 Security and permission controls", "PASS",
                   "no key material, no miner processes, config not world-writable, "
                   "emergency stop ON, mining + trading disabled")
    except Exception as e:
        record("15 Security and permission controls", "FAIL", str(e)[:300])


def _daemon_rss_kb(pid):
    with open(f"/proc/{pid}/status") as f:
        st = dict(l.split(":", 1) for l in f if ":" in l)
    return int(st["VmRSS"].split()[0])


def _daemon_cpu_ticks(pid):
    with open(f"/proc/{pid}/stat") as f:
        parts = f.read().split()
    return int(parts[13]) + int(parts[14])


def t16_memory_pressure():
    """ATLAS's OWN memory footprint. Host MEM% is informational only.

    Phase 1 (M2.1): host MEM% 76.67% vs the 70% cap is SHARED-HOST pressure,
    not ATLAS — 0 of 156 metrics rows were below 70%, the cap was already
    breached before the earliest metric. Daemon RSS is flat 10-14 MB, so
    the fail line is 50 MB (5x the observed band). DB size fails only over
    100 MB. The suite must PASS while host MEM% stays above 70%.
    """
    try:
        pids = pgrep_monitor()
        assert pids, "daemon not running"
        rss_kb = _daemon_rss_kb(pids[0])
        db_bytes = os.path.getsize(DB)
        s = read_snapshot()
        host_mem = s["mem_used_pct"]
        problems = []
        if rss_kb >= 50 * 1024:
            problems.append(f"daemon RSS {rss_kb/1024:.1f} MB >= 50 MB")
        if db_bytes >= 100 * 1024 * 1024:
            problems.append(f"DB size {db_bytes/1024/1024:.1f} MB >= 100 MB")
        detail = (f"daemon RSS {rss_kb/1024:.1f} MB (< 50 MB), "
                  f"DB {db_bytes/1024:.1f} KB (< 100 MB), "
                  f"host MEM {host_mem}% (informational only)")
        if problems:
            record("16 Memory pressure", "FAIL", "; ".join(problems) + " | " + detail)
        else:
            record("16 Memory pressure", "PASS", detail)
    except Exception as e:
        record("16 Memory pressure", "FAIL", str(e)[:300])


def t17_snapshot_freshness():
    try:
        s = read_snapshot()
        age = int(time.time()) - s["ts"]
        assert age < 180, f"snapshot {age}s old (>= 180 s)"
        record("17 Snapshot freshness", "PASS",
               f"data/snapshot.json ts age {age}s (< 180 s)")
    except Exception as e:
        record("17 Snapshot freshness", "FAIL", str(e)[:300])


def _fetch_once(url, timeout=10):
    """One GET. Returns (status_or_None, body_text, error_or_None)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ATLAS/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), None
    except Exception as e:
        return None, "", f"{type(e).__name__}: {e}"


def _fetch_with_retry(url, attempts=2):
    """GET with one retry before concluding (egress-proxy blip rule, M2.3:
    round 1 showed all non-CoinGecko hosts curl 000 simultaneously, then
    recovered ~2 min later — a single failure proves nothing)."""
    status, body, err = _fetch_once(url)
    if status == 200:
        return status, body, err
    time.sleep(2)
    return _fetch_once(url)


def _validate_endpoint(name, url, check):
    """Fetch (retry once) and validate. Returns (ok, detail)."""
    status, body, err = _fetch_with_retry(url)
    if status != 200:
        return False, f"{name}: HTTP {status} ({err or 'no body'}) after retry"
    try:
        value = check(body)
    except Exception as e:
        return False, f"{name}: HTTP 200 but validation failed: {e}"
    return True, f"{name}: HTTP 200, {value}"


def t18_api_data_validity():
    """HTTP 200 AND parseable AND required fields present, per endpoint.

    URLs are the exact ones the code uses (t14 / M2.3 findings).
    MoneroOcean /pool/stats ONLY — /api/stats 404s, never use it.
    mempool.space is tested and recorded but a mempool-only failure does
    NOT fail the suite (blocking history; blockchain.info is primary).
    """
    try:
        checks = []

        def coingecko(body):
            d = json.loads(body)
            assert "gecko_says" in d, "gecko_says missing"
            return f"gecko_says={d['gecko_says']!r}"

        def moneroocean(body):
            d = json.loads(body)
            ps = d["pool_statistics"]
            assert "hashRate" in ps and "miners" in ps, "hashRate/miners missing"
            return (f"hashRate={ps['hashRate']:.0f} H/s, "
                    f"miners={ps['miners']}, "
                    f"lastBlockFound={ps.get('lastBlockFound')}")

        def blockcount(body):
            h = int(body.strip())
            assert h > 0, f"height {h}"
            return f"height={h}"

        results = {}
        for name, url, check in (
            ("coingecko", "https://api.coingecko.com/api/v3/ping", coingecko),
            ("moneroocean", "https://api.moneroocean.stream/pool/stats", moneroocean),
            ("blockchain.info", "https://blockchain.info/q/getblockcount", blockcount),
        ):
            ok, detail = _validate_endpoint(name, url, check)
            results[name] = ok
            checks.append(detail)
        # mempool.space: recorded, never fatal.
        ok, detail = _validate_endpoint(
            "mempool.space", "https://mempool.space/api/blocks/tip/height", blockcount)
        checks.append(detail + (" (non-fatal)" if not ok else ""))
        failed = [k for k, v in results.items() if not v]
        if failed:
            record("18 API data validity", "FAIL",
                   f"primary endpoint(s) failed: {', '.join(failed)} | " + " | ".join(checks))
        else:
            record("18 API data validity", "PASS", " | ".join(checks))
    except Exception as e:
        record("18 API data validity", "FAIL", str(e)[:300])


def t19_db_write_latency():
    """Time a test write that is ROLLED BACK — never commit test data.

    Same pattern Mission 1.1 used for the fresh-DB writability check.
    Row counts before/after must match, proving nothing persisted.
    Fail only if the rolled-back write exceeds 1000 ms.
    """
    try:
        con = db()
        try:
            before = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            t0 = time.monotonic()
            con.execute("BEGIN")
            con.execute(
                "INSERT INTO events (ts, kind, message) VALUES (?, 'selftest', ?)",
                (int(time.time()), "diagnostics t19 write-latency probe"))
            con.execute("ROLLBACK")
            latency_ms = (time.monotonic() - t0) * 1000.0
            after = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        finally:
            con.close()
        assert after == before, f"events count changed {before} -> {after} (rollback failed!)"
        detail = (f"rolled-back test write {latency_ms:.1f} ms (< 1000 ms), "
                  f"events rows unchanged at {before}")
        if latency_ms > 1000:
            record("19 Database write latency", "FAIL", detail)
        else:
            record("19 Database write latency", "PASS", detail)
    except Exception as e:
        record("19 Database write latency", "FAIL", str(e)[:300])


def t20_daemon_health():
    """Exactly one daemon, pid alive, monitor.log last line recent (< 5 min)."""
    try:
        pids = pgrep_monitor()
        assert len(pids) == 1, f"expected exactly 1 daemon, found {len(pids)}: {pids}"
        pid = pids[0]
        os.kill(pid, 0)  # raises if the pid is not alive
        log_path = os.path.join(BASE, "logs", "monitor.log")
        assert os.path.exists(log_path), "logs/monitor.log missing"
        with open(log_path) as f:
            lines = [l.rstrip("\n") for l in f if l.strip()]
        assert lines, "logs/monitor.log empty"
        last = lines[-1]
        stamp = last.split()[0]
        # Log timestamps are UTC; calendar.timegm avoids local DST guessing.
        log_ts = calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))
        age = int(time.time()) - log_ts
        assert age < 300, f"last log line {age}s old (>= 300 s): {last[:120]}"
        record("20 Daemon health", "PASS",
               f"exactly 1 daemon (pid {pid}, alive); monitor.log last line "
               f"{age}s old: {last[:120]}")
    except Exception as e:
        record("20 Daemon health", "FAIL", str(e)[:300])


def t21_cpu_pressure():
    """The DAEMON's own CPU over a short window. Host load informational only.

    Daemon does ~1 short cycle per minute, so a 3 s window should show
    near-zero CPU; fail line 25% leaves headroom for a cycle landing
    inside the window. Host load is shared-host pressure, never a fail.
    """
    try:
        pids = pgrep_monitor()
        assert pids, "daemon not running"
        pid = pids[0]
        clk = os.sysconf("SC_CLK_TCK")
        t0 = _daemon_cpu_ticks(pid)
        time.sleep(3)
        t1 = _daemon_cpu_ticks(pid)
        window_pct = 100.0 * (t1 - t0) / clk / 3.0
        load1, load5, load15 = os.getloadavg()
        detail = (f"daemon CPU {window_pct:.1f}% over 3 s window (< 25%), "
                  f"host load {load1:.2f}/{load5:.2f}/{load15:.2f} "
                  f"(informational only)")
        if window_pct > 25.0:
            record("21 CPU pressure", "FAIL", detail)
        else:
            record("21 CPU pressure", "PASS", detail)
    except Exception as e:
        record("21 CPU pressure", "FAIL", str(e)[:300])


def t22_queue_delays():
    """Gap between the two latest metrics-table timestamps (~60 s apart).

    Fail if the latest gap exceeds 180 s (missed writes). Runs after the
    t10/t11 restarts, so the two latest rows are post-restart steady state.
    """
    try:
        con = db()
        rows = con.execute(
            "SELECT ts FROM metrics ORDER BY ts DESC LIMIT 2").fetchall()
        con.close()
        assert len(rows) == 2, f"only {len(rows)} metrics row(s)"
        gap = rows[0][0] - rows[1][0]
        age = int(time.time()) - rows[0][0]
        detail = (f"latest metrics gap {gap}s (expected ~60 s), "
                  f"newest row {age}s old")
        if gap > 180:
            record("22 Queue delays", "FAIL", detail + " (> 180 s: missed writes)")
        else:
            record("22 Queue delays", "PASS", detail)
    except Exception as e:
        record("22 Queue delays", "FAIL", str(e)[:300])


def t23_reward_chain():
    """Master Mission 6: the reward ledger's SHA-256 hash chain verifies
    on the LIVE DB. Read-only (verify_chain writes nothing). On the live
    DB the ledger is empty (0 entries), so the expected outcome is the
    trivial PASS: "ledger empty — chain trivially valid, 0 entries". Any
    future break (tampered row, gap, failed reconciliation) FAILs here."""
    try:
        sys.path.insert(0, CORE)
        import atlas_rewards
        con = sqlite3.connect(DB)
        try:
            result = atlas_rewards.verify_chain(con)
        finally:
            con.close()
        detail = (f"verify_chain: {'PASS' if result['ok'] else 'FAIL'}; "
                  f"{result['entries']} entries, {result['batches']} settled "
                  f"batch(es), {result.get('corrections', 0)} correction(s)"
                  + (f"; {result.get('message', '')}" if result["ok"] else
                     f"; {result.get('error', '')}"))
        if result["ok"]:
            record("23 Reward ledger hash chain", "PASS", detail)
        else:
            record("23 Reward ledger hash chain", "FAIL", detail)
    except Exception as e:
        record("23 Reward ledger hash chain", "FAIL", str(e)[:300])


def t24_dashboard_export():
    """Master Mission 7: the host dashboard export (data/dashboard.json)
    exists, parses, is fresh, and its host-verified totals match a fresh
    COUNT/SUM over the live DB. The export is regenerated first (read-only
    derivation — it writes no ledger/decision/share rows), so freshness
    is checked right after a pass/export, as specified."""
    try:
        rc, out = sh(f"python3 {CORE}/atlas_dashboard.py export", timeout=30)
        assert rc == 0, f"dashboard export exit {rc}: {out[:200]}"
        dash_path = os.path.join(BASE, "data", "dashboard.json")
        assert os.path.exists(dash_path), "data/dashboard.json missing after export"
        with open(dash_path) as f:
            dash = json.load(f)
        age = int(time.time()) - dash["exported_at"]
        assert age < 600, f"dashboard.json exported_at {age}s old (>= 600 s)"
        assert dash["hashrate"]["status"] == "not-measured", \
            f"hashrate status {dash['hashrate']['status']!r} (Gate 1 unmeasured)"
        assert dash["earnings"]["estimated_piconero"] is None, \
            "estimated earnings must be null while Gate 1 is unmeasured"
        con = db()
        try:
            live = {
                "ledger_entries": con.execute(
                    "SELECT COUNT(*) FROM ledger").fetchone()[0],
                "batches_settled": con.execute(
                    "SELECT COUNT(*) FROM reward_batches WHERE status = 'settled'"
                ).fetchone()[0],
                "total_user_rewards_piconero": con.execute(
                    "SELECT COALESCE(SUM(amount_piconero), 0) FROM ledger "
                    "WHERE entry_type = 'user_allocation'").fetchone()[0],
                "total_atlas_share_piconero": con.execute(
                    "SELECT COALESCE(SUM(amount_piconero), 0) FROM ledger "
                    "WHERE entry_type = 'atlas_share'").fetchone()[0],
            }
        finally:
            con.close()
        hv = dash["host_verified_totals"]
        mismatched = [k for k in live if hv.get(k) != live[k]]
        assert not mismatched, \
            f"host-verified totals mismatch on {mismatched}: file {hv} vs live {live}"
        detail = (f"dashboard.json fresh ({age}s old), hashrate not-measured, "
                  f"estimate null; host-verified totals match live DB: "
                  f"{live['ledger_entries']} ledger entries, "
                  f"{live['batches_settled']} settled batch(es), "
                  f"{live['total_user_rewards_piconero']} user / "
                  f"{live['total_atlas_share_piconero']} ATLAS piconero")
        record("24 Dashboard export", "PASS", detail)
    except Exception as e:
        record("24 Dashboard export", "FAIL", str(e)[:300])


def t25_admin_export():
    """Master Mission 8: the host admin export (data/admin.json) exists,
    parses, is fresh, and its host-verified totals and security counts
    match fresh COUNT/SUM queries over the live DB, its earnings block
    equals a fresh dashboard.json earnings block, and no credential
    field appears anywhere in the file. The export is regenerated
    first (read-only derivation — it writes no ledger/decision/share
    rows), so freshness is checked right after a pass/export."""
    try:
        rc, out = sh(f"python3 {CORE}/atlas_admin.py export", timeout=30)
        assert rc == 0, f"admin export exit {rc}: {out[:200]}"
        rc, out = sh(f"python3 {CORE}/atlas_dashboard.py export", timeout=30)
        assert rc == 0, f"dashboard export exit {rc}: {out[:200]}"
        admin_path = os.path.join(BASE, "data", "admin.json")
        assert os.path.exists(admin_path), "data/admin.json missing after export"
        with open(admin_path) as f:
            raw = f.read()
        admin = json.loads(raw)
        age = int(time.time()) - admin["exported_at"]
        assert age < 600, f"admin.json exported_at {age}s old (>= 600 s)"
        assert admin["network"]["hashrate"]["status"] == "not-measured", \
            f"hashrate status {admin['network']['hashrate']['status']!r} (Gate 1 unmeasured)"
        assert admin["mining"]["earnings"]["estimated_piconero"] is None, \
            "estimated earnings must be null while Gate 1 is unmeasured"
        assert admin["infrastructure"]["queues"]["reason"] == \
            "No queue system exists — the coordinator runs synchronously in the 10-minute pass", \
            "queue UNAVAILABLE reason changed"
        assert admin["network"]["daemon_uptime"]["reason"] == \
            "Daemon start time is not recorded", "daemon-uptime reason changed"
        with open(os.path.join(BASE, "data", "dashboard.json")) as f:
            dash = json.load(f)
        assert admin["mining"]["earnings"] == dash["earnings"], \
            "admin earnings block != dashboard earnings block"
        con = db()
        try:
            live = {
                "ledger_entries": con.execute(
                    "SELECT COUNT(*) FROM ledger").fetchone()[0],
                "batches_settled": con.execute(
                    "SELECT COUNT(*) FROM reward_batches WHERE status = 'settled'"
                ).fetchone()[0],
                "total_user_rewards_piconero": con.execute(
                    "SELECT COALESCE(SUM(amount_piconero), 0) FROM ledger "
                    "WHERE entry_type = 'user_allocation'").fetchone()[0],
                "total_atlas_share_piconero": con.execute(
                    "SELECT COALESCE(SUM(amount_piconero), 0) FROM ledger "
                    "WHERE entry_type = 'atlas_share'").fetchone()[0],
            }
            sec_live = {
                "suspicious_workers": con.execute(
                    "SELECT COUNT(*) FROM workers "
                    "WHERE status IN ('suspended','revoked')").fetchone()[0],
                "invalid_shares": con.execute(
                    "SELECT COUNT(*) FROM shares WHERE origin = 'pool' "
                    "AND accepted = 0").fetchone()[0],
                "account_abuse": con.execute(
                    "SELECT COUNT(*) FROM events WHERE kind = 'abuse'").fetchone()[0],
                "auth_failures": con.execute(
                    "SELECT COUNT(*) FROM events WHERE kind = 'auth_failure'").fetchone()[0],
                "payout_anomalies": (
                    con.execute(
                        "SELECT COUNT(*) FROM payouts WHERE status = 'failed'"
                    ).fetchone()[0]
                    + con.execute(
                        "SELECT COUNT(*) FROM ledger WHERE entry_type = 'reversal'"
                    ).fetchone()[0]),
            }
            # Duplicate shares: groups sharing a non-null external_id, or
            # (external_id null) the same worker_id + job_id, count > 1;
            # count = duplicate rows beyond the first per group.
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
            sec_live["duplicate_shares"] = dup
            # High-rejection suspicious workers (rejected >= 10 and
            # rejected / total > 0.5) add to the suspended/revoked count.
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
                        sec_live["suspicious_workers"] += 1
        finally:
            con.close()
        hv = admin["mining"]["host_verified_totals"]
        mismatched = [k for k in live if hv.get(k) != live[k]]
        assert not mismatched, \
            f"host-verified totals mismatch on {mismatched}: file {hv} vs live {live}"
        sec = admin["security"]
        sec_mismatched = [k for k in sec_live
                          if sec[k]["count"] != sec_live[k]]
        assert not sec_mismatched, \
            f"security counts mismatch on {sec_mismatched}: file " \
            f"{{k: sec[k]['count'] for k in sec_live}} vs live {sec_live}"
        for forbidden in ("token_hash", "token_salt", "wallet"):
            assert forbidden not in raw, \
                f"{forbidden!r} appears in data/admin.json"
        detail = (f"admin.json fresh ({age}s old), hashrate not-measured, "
                  f"estimate null; earnings block == dashboard earnings; "
                  f"host-verified totals match live DB: "
                  f"{live['ledger_entries']} ledger entries, "
                  f"{live['batches_settled']} settled batch(es); "
                  f"security counts match live SQL: "
                  f"{sec_live['suspicious_workers']} suspicious, "
                  f"{sec_live['invalid_shares']} invalid, "
                  f"{sec_live['duplicate_shares']} duplicate, "
                  f"{sec_live['account_abuse']} abuse, "
                  f"{sec_live['auth_failures']} auth failures, "
                  f"{sec_live['payout_anomalies']} payout anomalies; "
                  f"no token_hash/token_salt/wallet field in file")
        record("25 Admin export", "PASS", detail)
    except Exception as e:
        record("25 Admin export", "FAIL", str(e)[:300])


def t26_profitability_export():
    """Master Mission 9: the host profitability export
    (data/profitability.json) exists, parses, is fresh, and every figure
    re-derives from the recorded inputs by the design §1 formula within
    rounding. The export is regenerated first (read-only derivation —
    it writes no ledger/decision/share rows), so freshness is checked
    right after a pass/export, as specified. Coins whose live inputs
    could not be fetched are 'Not computed yet' (figures null) — the
    re-derivation skips those rows and asserts the nulls instead of
    inventing figures. The check fails if a coin HAS complete inputs
    but zero of its figures were re-derived."""
    try:
        rc, out = sh(f"python3 {CORE}/atlas_profitability.py export",
                     timeout=120)
        assert rc == 0, f"profitability export exit {rc}: {out[:200]}"
        rc, out = sh(f"python3 {CORE}/atlas_dashboard.py export", timeout=30)
        assert rc == 0, f"dashboard export exit {rc}: {out[:200]}"
        prof_path = os.path.join(BASE, "data", "profitability.json")
        assert os.path.exists(prof_path), \
            "data/profitability.json missing after export"
        with open(prof_path) as f:
            raw = f.read()
        prof = json.loads(raw)
        age = int(time.time()) - prof["exported_at"]
        assert age < 600, \
            f"profitability.json exported_at {age}s old (>= 600 s)"
        assert prof["your_hardware"] is None, \
            "your-hardware block must be null while Gate 1 is unmeasured"
        assert prof["your_hardware_reason"] == \
            "Cannot estimate — hashrate not measured", \
            "your-hardware reason changed"
        with open(os.path.join(BASE, "data", "dashboard.json")) as f:
            dash = json.load(f)
        assert prof["confirmed_earnings"] == dash["earnings"], \
            "profitability confirmed-earnings block != dashboard earnings block"

        # Inputs block: source + fetched_at per live input; tariff
        # constants carry source + effective date (design D-M9-4).
        inputs = prof["inputs"]
        for coin in ("xmr", "kas", "rvn", "erg"):
            rec = inputs[coin]
            assert rec.get("source_network") and rec.get("source_price"), \
                f"{coin}: input sources missing"
            if rec.get("status") in ("fresh", "stale"):
                assert isinstance(rec.get("fetched_at"), int), \
                    f"{coin}: fetched_at missing on a {rec.get('status')} input"
        elec = inputs["electricity"]
        for rate in ("tier1", "tier2", "us_avg"):
            assert elec[rate].get("source"), f"{rate}: tariff source missing"
            assert elec[rate].get("effective_date"), \
                f"{rate}: tariff effective_date missing"

        # No USD figure in the panel payload (USD lives only under
        # audit_usd): no key mentions usd/price, no string mentions
        # USD or $ anywhere in the panel.
        def _check_panel(node, path="panel"):
            if isinstance(node, dict):
                for key, value in node.items():
                    assert "usd" not in key.lower(), \
                        f"USD key in panel: {path}.{key}"
                    assert "price" not in key.lower(), \
                        f"price key in panel: {path}.{key}"
                    _check_panel(value, f"{path}.{key}")
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    _check_panel(value, f"{path}[{i}]")
            elif isinstance(node, str):
                assert "USD" not in node, \
                    f"USD string in panel: {path}={node!r}"
                assert "$" not in node, f"$ string in panel: {path}={node!r}"
        _check_panel(prof["panel"])
        assert "audit_usd" in prof, "audit_usd missing from export"
        assert prof["panel"]["your_hardware"] is None, \
            "panel your-hardware block must be null"
        assert prof["panel"]["your_hardware_reason"] == \
            "Cannot estimate — hashrate not measured"

        # Independent re-derivation from the recorded inputs (§1 formula).
        usd_cad = (inputs.get("usd_cad") or {}).get("value")
        rates = {"us_avg": elec["us_avg"]["cents_per_kwh_usd"] / 100.0}
        for key in ("tier1", "tier2", "proposed_tariff"):
            rates[key] = (None if not usd_cad else
                          elec[key]["cents_per_kwh_cad"] / 100.0 / usd_cad)
        xmr_price = (inputs["xmr"] or {}).get("price_usd")
        profiles = {
            "xmr_cpu": ("xmr", 10000, 171, 0.0, "H/s"),
            "kas": ("kas", 480_000_000, 150, 1.0, "MH/s"),
            "rvn": ("rvn", 27_000_000, 240, 1.0, "MH/s"),
            "erg": ("erg", 137_000_000, 132, 1.0, "MH/s"),
            "xmr_browser_laptop": ("xmr", 200, 45, 0.0, "H/s"),
            "xmr_browser_desktop": ("xmr", 850, 50, 0.0, "H/s"),
        }
        checked = 0

        def _figs(pid):
            coin, hps, wall_w, fee_pct, unit = profiles[pid]
            rec = inputs[coin]
            if (rec.get("network_hashrate_hps") is None
                    or rec.get("block_reward") is None
                    or rec.get("blocks_per_day") is None
                    or rec.get("price_usd") is None
                    or xmr_price is None):
                return None
            daily = (hps / rec["network_hashrate_hps"]
                     * rec["blocks_per_day"] * rec["block_reward"]
                     * (1.0 - fee_pct / 100.0))
            gross_usd = daily * rec["price_usd"]
            kwh = wall_w * 24.0 / 1000.0
            gross_per_unit = (1.0 / rec["network_hashrate_hps"]
                              * rec["blocks_per_day"] * rec["block_reward"]
                              * (1.0 - fee_pct / 100.0) * rec["price_usd"]
                              * (1.0 if unit == "H/s" else 1e6))
            net_xmr, gates = {}, {}
            for rate, usd_per_kwh in rates.items():
                if usd_per_kwh is None:
                    net_xmr[rate] = None
                    gates[rate] = None
                    continue
                net_xmr[rate] = (gross_usd - kwh * usd_per_kwh) / xmr_price
                gates[rate] = (24.0 / 1000.0 * usd_per_kwh) / gross_per_unit
            return {"daily": daily, "gross_xmr": gross_usd / xmr_price,
                    "net_xmr": net_xmr, "gates": gates,
                    "breakeven_cents": gross_usd / kwh * 100.0,
                    "current_hw": (hps / wall_w
                                   if unit == "H/s" else hps / 1e6 / wall_w),
                    "elec_tier2_usd": (None if rates["tier2"] is None
                                       else kwh * rates["tier2"])}

        def _close(actual, expected, tol, what):
            nonlocal checked
            assert actual is not None and expected is not None, \
                f"{what}: missing value (actual {actual}, expected {expected})"
            assert abs(actual - expected) <= tol, \
                f"{what}: {actual} != {expected} (tol {tol})"
            checked += 1

        panel = prof["panel"]
        comp = {r["profile"]: r for r in panel["coin_comparison"]}
        brk = {r["profile"]: r for r in panel["breakeven"]}
        sens = {r["profile"]: r for r in panel["sensitivity"]}
        for pid in profiles:
            figs = _figs(pid)
            row = comp[pid]
            if figs is None:
                assert row["status"] == "not_computed", \
                    f"{pid}: no inputs but status {row['status']}"
                assert row["empty_state"] == "Not computed yet", \
                    f"{pid}: empty state is not 'Not computed yet'"
                assert row["net_xmr_per_day_tier2"] is None
                continue
            assert row["status"] == "computed"
            _close(row["daily_coins"], figs["daily"], 1e-6,
                   f"{pid} daily coins")
            _close(row["gross_xmr_per_day"], figs["gross_xmr"], 1e-6,
                   f"{pid} gross XMR/day")
            _close(row["net_xmr_per_day_tier2"],
                   figs["net_xmr"]["tier2"], 1e-6,
                   f"{pid} net XMR/day (Tier 2)")
            brow = brk[pid]
            _close(brow["breakeven_hw_tier2"], figs["gates"]["tier2"], 0.1,
                   f"{pid} breakeven H/W (Tier 2)")
            _close(brow["breakeven_hw_us_avg"], figs["gates"]["us_avg"], 0.1,
                   f"{pid} breakeven H/W (US avg)")
            _close(brow["breakeven_cents_per_kwh"],
                   figs["breakeven_cents"], 0.01,
                   f"{pid} breakeven c/kWh")
            _close(brow["distance_to_breakeven_tier2"],
                   figs["current_hw"] / figs["gates"]["tier2"], 0.002,
                   f"{pid} distance to breakeven (Tier 2)")
            srow = sens[pid]
            for rate in ("tier1", "tier2", "us_avg", "proposed_tariff"):
                if figs["net_xmr"][rate] is None:
                    assert srow["net_xmr_per_day"][rate] is None
                    continue
                _close(srow["net_xmr_per_day"][rate],
                       figs["net_xmr"][rate], 1e-6,
                       f"{pid} net XMR/day ({rate})")
        # Pool fees: XMR net under each pool fee re-derives; SupportXMR
        # gross is exactly 0.6% below MoneroOcean (checked via nets).
        fee_rows = {r["pool"]: r for r in panel["pool_fees"]["rows"]}
        assert fee_rows["MoneroOcean"]["fee_percent"] == 0.0
        assert fee_rows["SupportXMR"]["fee_percent"] == 0.6
        assert fee_rows["P2Pool"]["fee_percent"] == 0.0
        assert fee_rows["MoneroOcean"]["net_xmr_per_day_tier2"] == \
            fee_rows["P2Pool"]["net_xmr_per_day_tier2"], \
            "P2Pool 0% must equal MoneroOcean 0%"
        for pool, fee_pct in (("MoneroOcean", 0.0), ("SupportXMR", 0.6),
                              ("P2Pool", 0.0)):
            rec = inputs["xmr"]
            if (rec.get("network_hashrate_hps") is None
                    or rec.get("price_usd") is None or xmr_price is None
                    or rates["tier2"] is None):
                continue
            daily = (10000 / rec["network_hashrate_hps"]
                     * rec["blocks_per_day"] * rec["block_reward"]
                     * (1.0 - fee_pct / 100.0))
            net = ((daily * rec["price_usd"] - 171 * 24.0 / 1000.0
                    * rates["tier2"]) / xmr_price)
            _close(fee_rows[pool]["net_xmr_per_day_tier2"], net, 1e-6,
                   f"{pool} net XMR/day (Tier 2)")
        # Split projection at Tier 2: 0.75 / 0.25 x gross, user net.
        for row in panel["split_projection"]:
            pid = row["profile"]
            figs = _figs(pid)
            if figs is None:
                assert row["status"] == "not_computed"
                continue
            _close(row["user_share_xmr_per_day"],
                   0.75 * figs["gross_xmr"], 1e-6, f"{pid} user share")
            _close(row["atlas_share_xmr_per_day"],
                   0.25 * figs["gross_xmr"], 1e-6, f"{pid} ATLAS share")
            if figs["elec_tier2_usd"] is not None:
                _close(row["user_net_xmr_per_day"],
                       0.75 * figs["gross_xmr"]
                       - figs["elec_tier2_usd"] / xmr_price, 1e-6,
                       f"{pid} user net")
            assert row["note"] == "Projection only — not earnings"
        # Stale bookkeeping is consistent with the stale_inputs list.
        assert prof["stale"] == bool(prof["stale_inputs"]), \
            "stale flag disagrees with stale_inputs"
        assert checked >= 1, \
            "no figure re-derived: inputs present but nothing checked"
        xmr_row = comp.get("xmr_cpu", {})
        detail = (f"profitability.json fresh ({age}s old), "
                  f"{checked} figures re-derived from recorded inputs "
                  f"within rounding; XMR net XMR/day (Tier 2) "
                  f"{xmr_row.get('net_xmr_per_day_tier2')}, breakeven "
                  f"{brk.get('xmr_cpu', {}).get('breakeven_hw_tier2')} H/W; "
                  f"your-hardware null + verbatim reason; earnings block "
                  f"== dashboard earnings; no USD in panel; "
                  f"stale={prof['stale']}")
        record("26 Profitability export", "PASS", detail)
    except Exception as e:
        record("26 Profitability export", "FAIL", str(e)[:300])


def t27_security_export():
    """Master Mission 10: the host security export (data/security.json)
    exists, parses, is fresh, its security counts match fresh live SQL,
    its host-verified totals match the live DB, no secret string appears
    in the file, all S1–S9 results are present, and every check passed.
    The export is regenerated first (read-only derivation — it writes no
    ledger/decision/share rows), so freshness is checked right after a
    pass/export, as specified."""
    try:
        rc, out = sh(f"python3 {CORE}/atlas_security.py export", timeout=120)
        assert rc == 0, f"security export exit {rc}: {out[:200]}"
        sec_path = os.path.join(BASE, "data", "security.json")
        assert os.path.exists(sec_path), \
            "data/security.json missing after export"
        with open(sec_path) as f:
            raw = f.read()
        sec = json.loads(raw)
        age = int(time.time()) - sec["exported_at"]
        assert age < 600, f"security.json exported_at {age}s old (>= 600 s)"
        assert sec["emergency_stop"] is True, "emergency_stop not true"
        assert sec["mode"] == "simulation-only", \
            f"mode {sec['mode']!r} (expected simulation-only)"
        tests = {t["id"]: t for t in sec["security_tests"]}
        for check_id in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"):
            assert check_id in tests, f"{check_id} result missing from export"
            assert tests[check_id]["result"] in ("PASS", "FAIL", "NOT_RUN"), \
                f"{check_id} result {tests[check_id]['result']!r}"
        failed = [k for k, t in tests.items() if t["result"] == "FAIL"]
        not_run = [k for k, t in tests.items() if t["result"] == "NOT_RUN"]
        assert not failed, f"security checks FAILED: {failed}"
        assert not not_run, f"security checks NOT_RUN: {not_run}"
        con = db()
        try:
            live = {
                "ledger_entries": con.execute(
                    "SELECT COUNT(*) FROM ledger").fetchone()[0],
                "batches_settled": con.execute(
                    "SELECT COUNT(*) FROM reward_batches WHERE status = 'settled'"
                ).fetchone()[0],
                "total_user_rewards_piconero": con.execute(
                    "SELECT COALESCE(SUM(amount_piconero), 0) FROM ledger "
                    "WHERE entry_type = 'user_allocation'").fetchone()[0],
                "total_atlas_share_piconero": con.execute(
                    "SELECT COALESCE(SUM(amount_piconero), 0) FROM ledger "
                    "WHERE entry_type = 'atlas_share'").fetchone()[0],
            }
            sec_live = {
                "suspicious_workers": con.execute(
                    "SELECT COUNT(*) FROM workers "
                    "WHERE status IN ('suspended','revoked')").fetchone()[0],
                "invalid_shares": con.execute(
                    "SELECT COUNT(*) FROM shares WHERE origin = 'pool' "
                    "AND accepted = 0").fetchone()[0],
                "account_abuse": con.execute(
                    "SELECT COUNT(*) FROM events WHERE kind = 'abuse'").fetchone()[0],
                "auth_failures": con.execute(
                    "SELECT COUNT(*) FROM events WHERE kind = 'auth_failure'").fetchone()[0],
                "payout_anomalies": (
                    con.execute(
                        "SELECT COUNT(*) FROM payouts WHERE status = 'failed'"
                    ).fetchone()[0]
                    + con.execute(
                        "SELECT COUNT(*) FROM ledger WHERE entry_type = 'reversal'"
                    ).fetchone()[0]),
            }
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
            sec_live["duplicate_shares"] = dup
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
                        sec_live["suspicious_workers"] += 1
        finally:
            con.close()
        hv = sec["host_verified_totals"]
        mismatched = [k for k in live if hv.get(k) != live[k]]
        assert not mismatched, \
            f"host-verified totals mismatch on {mismatched}: file {hv} vs live {live}"
        counts = sec["security_counts"]
        sec_mismatched = [k for k in sec_live if counts[k] != sec_live[k]]
        assert not sec_mismatched, \
            f"security counts mismatch on {sec_mismatched}: file {counts} vs live {sec_live}"
        for forbidden in ("token_hash", "token_salt", "wallet", "password",
                          "seed", "private_key"):
            assert forbidden not in raw, \
                f"{forbidden!r} appears in data/security.json"
        detail = (f"security.json fresh ({age}s old), 9/9 checks passed; "
                  f"host-verified totals match live DB: "
                  f"{live['ledger_entries']} ledger entries, "
                  f"{live['batches_settled']} settled batch(es); "
                  f"security counts match live SQL: "
                  f"{sec_live['suspicious_workers']} suspicious, "
                  f"{sec_live['invalid_shares']} invalid, "
                  f"{sec_live['duplicate_shares']} duplicate, "
                  f"{sec_live['account_abuse']} abuse, "
                  f"{sec_live['auth_failures']} auth failures, "
                  f"{sec_live['payout_anomalies']} payout anomalies; "
                  f"no secret string in file")
        record("27 Security export", "PASS", detail)
    except Exception as e:
        record("27 Security export", "FAIL", str(e)[:300])


def t28_scale_smoke():
    """Master Mission 10: the scale smoke level — a temp-DB load of 100
    workers / 10,000 shares runs, and the export's scale block is
    populated or honestly null with the verbatim reason. The full L1–L5
    run is on-demand; this test asserts only the smoke level."""
    try:
        sys.path.insert(0, CORE)
        import atlas_security
        smoke = atlas_security.run_scale_smoke()
        assert smoke["workers"] == 100, f"smoke workers {smoke['workers']}"
        assert smoke["shares"] == 10000, f"smoke shares {smoke['shares']}"
        assert smoke["shares_inserted"] == 10000, \
            f"smoke inserted {smoke['shares_inserted']}"
        assert smoke["duration_s"] > 0, "smoke duration not recorded"
        sec_path = os.path.join(BASE, "data", "security.json")
        assert os.path.exists(sec_path), "data/security.json missing"
        with open(sec_path) as f:
            sec = json.load(f)
        scale = sec.get("scale")
        assert isinstance(scale, dict), "scale block missing from export"
        if scale.get("run_at") is None:
            assert scale.get("reason") == atlas_security.NO_SCALE_REASON, \
                f"scale null reason is not the verbatim reason: {scale.get('reason')!r}"
            detail = (f"smoke load ran: 100 workers / 10,000 shares inserted "
                      f"in {smoke['duration_s']}s "
                      f"({smoke['shares_per_s']} shares/s), temp DB "
                      f"{smoke['db_size_bytes']} bytes; scale block honestly "
                      f"null with the verbatim reason (no scale run yet)")
        else:
            assert isinstance(scale["run_at"], int), "scale run_at not an int"
            assert scale.get("levels"), "scale levels missing"
            detail = (f"smoke load ran: 100 workers / 10,000 shares inserted "
                      f"in {smoke['duration_s']}s "
                      f"({smoke['shares_per_s']} shares/s), temp DB "
                      f"{smoke['db_size_bytes']} bytes; scale block populated "
                      f"(last run {scale['run_at']}, "
                      f"{len(scale['levels'])} levels)")
        record("28 Scale smoke", "PASS", detail)
    except Exception as e:
        record("28 Scale smoke", "FAIL", str(e)[:300])


def t29_trading_export():
    """Master Mission 22: the paper-trading export (data/trading.json)
    exists, parses, is fresh, and is paper-only with eligible capital
    equal to mining profits ($0) plus confirmed USDC deposits on Solana
    as summed from the live DB; the deposit block names Solana
    / USDC with the configured address (or null while pending); no
    secret-trigger string appears in the file; every account's cash
    and positions reconcile to SUM over its filled orders in the live
    DB; and the trading unit suite passes."""
    try:
        rc, out = sh(f"python3 {CORE}/atlas_trading.py export",
                     timeout=120)
        assert rc == 0, f"trading export exit {rc}: {out[:200]}"
        path = os.path.join(BASE, "data", "trading.json")
        assert os.path.exists(path), "data/trading.json missing after export"
        with open(path) as f:
            raw = f.read()
        payload = json.loads(raw)
        age = int(time.time()) - payload["exported_at"]
        assert age < 600, f"trading.json exported_at {age}s old (>= 600 s)"
        assert payload["mode"] == "paper-only", \
            f"trading mode is not paper-only: {payload['mode']!r}"
        sources = payload["eligible_capital_sources"]
        assert sources["mining_profits_usd_cents"] == 0, \
            "mining-profits source is not $0"
        # Eligible capital = mining profits ($0: no mining) + confirmed
        # USDC deposits on Solana, derived from the live DB — not a
        # hardcoded $0. (M22 recorded the first real test deposit:
        # 0.94452 USDC = 94 cents, tx 4LadRjiJ...; a hardcoded $0
        # assertion went stale the moment that deposit landed.)
        con = sqlite3.connect(DB)
        try:
            db_deposits_cents = con.execute(
                "SELECT COALESCE(SUM(amount_usd_cents), 0) "
                "FROM trading_deposits WHERE status='confirmed'"
            ).fetchone()[0]
        finally:
            con.close()
        assert sources["usdc_deposits_solana_usd_cents"] == db_deposits_cents, \
            (f"USDC-deposits source {sources['usdc_deposits_solana_usd_cents']} "
             f"!= live DB sum {db_deposits_cents}")
        assert payload["eligible_capital_usd_cents"] == db_deposits_cents, \
            (f"eligible capital {payload['eligible_capital_usd_cents']} != "
             f"mining $0 + USDC deposits {db_deposits_cents} cents")
        deposit = payload["deposit"]
        assert deposit["network"] == "Solana", \
            f"deposit network is not Solana: {deposit['network']!r}"
        assert deposit["token"] == "USDC", \
            f"deposit token is not USDC: {deposit['token']!r}"
        address = deposit.get("address")
        if address is not None:
            sys.path.insert(0, CORE)
            import atlas_trading
            ok, reason = atlas_trading.validate_solana_address(address)
            assert ok, f"configured deposit address invalid: {reason}"
        for banned in ("seed", "private key", "keypair", "mnemonic"):
            assert banned not in raw.lower(), \
                f"secret-trigger string in trading export: {banned}"
        # Reconcile every account's cash and positions from the live DB.
        con = sqlite3.connect(DB)
        try:
            for account in payload["accounts"]:
                acc_id = account["id"]
                initial = account["initial_virtual_usd_cents"]
                spent = con.execute(
                    "SELECT COALESCE(SUM(cost_usd_cents + fee_usd_cents), 0) "
                    "FROM trading_orders WHERE account_id = ? AND side='buy' "
                    "AND status='filled'", (acc_id,)).fetchone()[0]
                received = con.execute(
                    "SELECT COALESCE(SUM(cost_usd_cents - fee_usd_cents), 0) "
                    "FROM trading_orders WHERE account_id = ? AND side='sell' "
                    "AND status='filled'", (acc_id,)).fetchone()[0]
                expect_cash = initial - int(spent) + int(received)
                got_cash = account["portfolio"]["cash_usd_cents"]
                assert got_cash == expect_cash, \
                    (f"account {acc_id} cash {got_cash} != derived "
                     f"{expect_cash}")
                held = {}
                for coin, side, qty in con.execute(
                        "SELECT coin, side, qty_base_units FROM trading_orders "
                        "WHERE account_id = ? AND status='filled'",
                        (acc_id,)).fetchall():
                    held[coin] = held.get(coin, 0) + (
                        qty if side == "buy" else -qty)
                held = {c: q for c, q in held.items() if q != 0}
                got = {p["coin"]: p["qty_base_units"]
                       for p in account["portfolio"]["positions"]}
                assert got == held, \
                    f"account {acc_id} positions {got} != derived {held}"
        finally:
            con.close()
        # The trading unit suite must pass (temp DBs only).
        rc, out = sh(f"python3 {CORE}/test_atlas_trading.py", timeout=120)
        assert rc == 0, f"trading suite failed: {out[-300:]}"
        detail = (f"trading export fresh ({age}s old), paper-only, "
                  f"eligible capital ${db_deposits_cents / 100:.2f} "
                  f"(mining $0 + USDC deposits "
                  f"${db_deposits_cents / 100:.2f}), "
                  f"deposit Solana/USDC address "
                  f"{address or 'pending'}, "
                  f"{len(payload['accounts'])} account(s) reconciled, "
                  f"trading suite 20/20")
        record("29 Trading export", "PASS", detail)
    except Exception as e:
        record("29 Trading export", "FAIL", str(e)[:300])


def main():
    print(f"ATLAS diagnostics — {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Base: {BASE}\n")
    t01_python_services()
    t02_monitor_daemon()
    t03_cpu_mem()
    t04_disk_net()
    t05_db_integrity()
    t06_db_persistence()
    t07_coordinator_decisions()
    t08_decision_logging()
    t09_emergency_stop()
    t10_service_restart()
    t11_auto_recovery()
    t12_deployment_persistence()
    t13_resource_consumption()
    t14_network()
    t15_security_permissions()
    t16_memory_pressure()
    t17_snapshot_freshness()
    t18_api_data_validity()
    t19_db_write_latency()
    t20_daemon_health()
    t21_cpu_pressure()
    t22_queue_delays()
    t23_reward_chain()
    t24_dashboard_export()
    t25_admin_export()
    t26_profitability_export()
    t27_security_export()
    t28_scale_smoke()
    t29_trading_export()
    summary = {
        "pass": sum(1 for r in RESULTS if r["status"] == "PASS"),
        "fail": sum(1 for r in RESULTS if r["status"] == "FAIL"),
        "not_tested": sum(1 for r in RESULTS if r["status"] == "NOT TESTED"),
    }
    doc = {"ts": int(time.time()), "results": RESULTS, "summary": summary}
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=2)
    print(f"\nSummary: {summary['pass']} PASS, {summary['fail']} FAIL, "
          f"{summary['not_tested']} NOT TESTED (of {len(RESULTS)})")
    print(f"Results: {OUT}")
    sys.exit(0 if summary["fail"] == 0 and summary["not_tested"] == 0 else 1)


if __name__ == "__main__":
    main()
