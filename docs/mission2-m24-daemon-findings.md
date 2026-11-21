# ATLAS Mission 2 — Lane M2.4: Daemon Reliability Findings

- **Lane:** M2.4 (Daemon reliability) — read-only investigation, no files edited, no process touched, no config changed.
- **Investigated:** 2026-11-18 02:03–02:06 EST (07:03–07:06 UTC).
- **Scope:** `~/workspace/atlas/` — daemon `core/atlas_monitor.py`, restart `core/recover.sh`, config `config/atlas.json`, logs `logs/monitor.log` / `logs/recover.log` / `logs/refresh-attempts.log`, data `data/atlas.db` / `data/snapshot.json`.
- **Verdict in one line:** Exactly one daemon runs and it is healthy right now; zero unplanned exits, zero DB write failures in surviving evidence; three metrics gaps, all with known planned causes; two real defects found (log truncation destroys crash evidence on every restart; VM-replacement auto-restore unverified and lost a ~5 min race to a manual restart).

## 1. Current daemon — exactly one instance

| Item | Value |
|---|---|
| PID | **9711** (only PID returned by `pgrep -af 'atlas_[m]onitor.py'`) |
| Command | `python3 core/atlas_monitor.py` |
| PPID | 1, state S, RSS 10,892 KB |
| Started | **2026-11-18 06:52:48 UTC = 01:52:48 EST** |
| Uptime at final check (02:05:52 EST) | 13 min 03 s |
| Started by | `recover.sh` (see `logs/recover.log` last line) during the 01:52 EST hourly diagnostics run — diagnostics tests 10/11 (see §2) |

Duplicate/stale check: `ps` shows one Python process on the host (`python3 core/atlas_monitor.py`, pid 9711). No pidfile mechanism exists — discovery is by `pgrep` only. No second, stale, or zombie daemon instance exists.

**Flock:** pid 9711 holds fd 9 → `data/recover.lock` (inherited from `recover.sh`, which does `exec 9>lock; flock -n 9` and then backgrounds the daemon, so the daemon keeps the lock for its whole lifetime). No other process holds the lock. Consequence: while the daemon is alive, any later `recover.sh` run exits silently at the `flock -n` step without ever reaching its `pgrep` check — correct as a duplicate-guard, but it also means `recover.sh` can never detect or restart a *hung-but-alive* daemon, and it logs nothing when it no-ops. If the daemon dies, its fds close and the lock releases, so the next `recover.sh` run can restart it.

**Note — this is NOT the baseline PID.** The 01:52 EST hourly report recorded pid 2193 (restarted 01:05 EST after the VM replacement). Pid 2193 was stopped by the hourly diagnostics tests 10/11 at 01:52:46–01:52:48 EST and replaced by pid 9711. That is a planned restart, not a crash (see §2).

## 2. Restart / exit history — 9 `recover.sh` restarts, 16 startup events, 0 crashes

### `logs/recover.log` (complete file, 9 lines)

```
2026-11-18T04:31:20Z recover: restarted atlas_monitor pid 7328
2026-11-18T04:32:40Z recover: restarted atlas_monitor pid 7490
2026-11-18T05:22:30Z recover: restarted atlas_monitor pid 24673
2026-11-18T05:36:52Z recover: restarted atlas_monitor pid 27651
2026-11-18T05:46:32Z recover: restarted atlas_monitor pid 29590
2026-11-18T05:48:01Z recover: restarted atlas_monitor pid 29895
2026-11-18T05:53:00Z recover: restarted atlas_monitor pid 30608
2026-11-18T06:04:57Z recover: restarted atlas_monitor pid 2193
2026-11-18T06:52:48Z recover: restarted atlas_monitor pid 9711
```

### What each restart was (cross-checked against `logs/refresh-attempts.log`, `data/atlas.db` events table, `docs/mission1.1-report-2026-11-18.md`, `core/diagnostics.py`)

| # | Time (UTC / EST) | PID | Cause |
|---|---|---|---|
| 1 | 04:31:20Z / 23:31:20 EST Nov 17 | 7328 | Early Stage-2 bring-up restart (no surviving detail; pre-dates refresh log) |
| 2 | 04:32:40Z / 23:32:40 EST | 7490 | Diagnostics test 11 (auto-recovery) — test 10 restarted the daemon directly 2 s earlier (see paired events below) |
| 3 | 05:22:30Z / 00:22:30 EST | 24673 | Diagnostics tests 10/11 during hourly health run (`refresh-attempts.log`: "daemon restarted by tests 10/11 as designed") |
| 4 | 05:36:52Z / 00:36:52 EST | 27651 | Restart after the **controlled timeout test**: daemon deliberately stopped 05:30:42Z, refresh-timeout verified over 5 m 34 s, then restarted via `recover.sh` |
| 5 | 05:46:32Z / 00:46:32 EST | 29590 | Mission 1.1 hardened-deploy recovery — first restart attempt failed (see §4, gap 2); daemon had been down ~2 min |
| 6 | 05:48:01Z / 00:48:01 EST | 29895 | Diagnostics test 11 (test 10 restarted directly 2 s earlier) |
| 7 | 05:53:00Z / 00:53:00 EST | 30608 | Diagnostics test 11 (test 10 restarted directly 2 s earlier) |
| 8 | 06:04:57Z / 01:04:57 EST | 2193 | **VM replacement ~01:00 EST** — manual `recover.sh` restore after ~5 min downtime (see §4, gap 3) |
| 9 | 06:52:48Z / 01:52:48 EST | 9711 | Diagnostics tests 10/11 during the 01:52 EST hourly report (test 10 restarted directly at 01:52:46, test 11 via `recover.sh` at 01:52:48) — **current daemon** |

### Paired startup events — benign, not duplicates

The `events` table holds 16 `startup` rows; restarts via `recover.sh` account for 9 of them. The other 7 are diagnostics test 10, which restarts the daemon **directly** (`diagnostics.py` t10: `os.kill(pid, SIGTERM)` then `(nohup python3 core/atlas_monitor.py > logs/monitor.log 2>&1 &)`), followed ~2 s later by test 11 killing it again and restarting via `recover.sh`. Paired events 2 s apart:

```
04:32:38 + 04:32:40   05:22:28 + 05:22:30   05:47:59 + 05:48:01
05:52:58 + 05:53:00   06:52:46 + 06:52:48
```

Each pair is two *sequential* short-lived incarnations (the first lives ~2 s, writes one metrics row and one startup event, then is SIGTERMed by test 11). The metrics table confirms this: five 2-second intervals between consecutive rows, one per pair. No two daemons ever ran concurrently.

Two startup events have no matching `recover.log` line because the daemon was started directly, not via `recover.sh`: 04:23:53Z (very first start; wrote no metrics row in its 22 s life before being replaced at 04:24:15Z — cause not recoverable from surviving logs) and the test-10 direct restarts above. The `refresh-attempts.log` line "monitor DEPLOYED hardened atlas_monitor.py pid 28762" (05:45:31Z) is the deploy-process PID, not a daemon PID — no startup event or metrics row exists for 28762, and the Mission 1.1 report confirms the daemon was down at that point (failed restart attempt, §4 gap 2).

### Unexpected exits

**None found.** No traceback, no crash, no `db WRITE FAIL`, no `QUARANTINE`, no `CORRUPT`/`LOCKED` line exists in any surviving log. Every exit in the record is accounted for above (diagnostics tests, controlled timeout test, Mission 1.1 deploy, VM replacement). Caveat: this claim covers only surviving evidence — see Finding F1 (§7): `monitor.log` is truncated on every restart, so a crash in any incarnation before the current one would have had its log lines destroyed.

## 3. Duplicate processes — none

- `pgrep -af 'atlas_[m]onitor.py'` → exactly one line: `9711 python3 core/atlas_monitor.py`.
- `ps` → exactly one Python process on the host.
- Flock on `data/recover.lock` held by pid 9711 only (fd 9).
- No stale PID files exist (none are used anywhere).

## 4. Missed scheduled tasks — metrics gaps

Metrics table at final check (02:05:52 EST): **158 rows**, first ts `1794975856` (2026-11-18 04:24:16 UTC), last ts `1794985550` (07:05:50 UTC), span 9,694 s = 161.6 min. `PRAGMA integrity_check` = `ok`. Interval distribution: 128 × 60 s, 13 × 61 s, plus phase-shift intervals (2 s × 5 from the paired diagnostics restarts; 17/27/42/45/57/65 s from restart phase shifts). Normal cycle is 60–61 s (60 s sleep + ~1 s work).

**Exactly three gaps > 90 s in the whole history:**

| # | Gap (UTC) | Gap (EST) | Length | Missed rows | Cause |
|---|---|---|---|---|---|
| 1 | 05:30:32 → 05:36:53 | 00:30:32 → 00:36:53 | **381 s (6 m 21 s)** | ~5 | **Planned controlled timeout test.** Daemon stopped 05:30:42Z, refresh-timeout verified (no false success after 5 m 34 s), restarted 05:36:52Z via `recover.sh` (pid 27651). Documented in `refresh-attempts.log`. |
| 2 | 05:43:53 → 05:46:33 | 00:43:53 → 00:46:33 | **160 s (2 m 40 s)** | ~2 | **Mission 1.1 deploy incident (documented, known).** Old daemon killed ~05:43:53 for the hardened-binary deploy; the first restart attempt failed because the operator's own command contained the literal daemon filename, defeating the `pgrep` bracket trick — `recover.sh` saw the shell as a "running daemon" and exited without starting one. Daemon down ~2 min until the retry from a clean command succeeded at 05:46:32Z (pid 29590). Source: `docs/mission1.1-report-2026-11-18.md` §3, "Deploy incident (honest account)". |
| 3 | 06:00:01 → 06:04:58 | 01:00:01 → 01:04:58 | **297 s (4 m 57 s)** | ~4 | **VM replacement ~01:00 EST.** All processes stopped by the platform replacement; daemon restored by manual `recover.sh` at 06:04:57Z (pid 2193). The 5-minute watchdog (`atlas-watchdog-5m`, per `docs/recovery.md`) did **not** beat the manual restart. |

Gap accounting: ~11 metrics rows not written, all during the three known downtimes above. **Zero rows lost to DB errors.**

### The 06:52:48 restart produced no gap

Rows around it: `06:51:02, 06:52:02 (pid 2193, last), 06:52:47 (new daemon #1), 06:52:49 (new daemon #2), 06:53:49 …` — test 10/11 swapped daemons inside one cycle, so no minute was missed.

### Hourly refresh attempts (`logs/refresh-attempts.log`)

No missed hourly run is visible: health-check entries at 05:21, 05:55 and 06:55 UTC are exactly 1 h apart (the 06:55 entry is the 01:52 EST hourly report: diagnostics 15/15 PASS, metrics 147 at that time). Entries between 05:05–05:38 are test-driven (refresh FAILs at 05:07/05:10 during the dashboard-stuck incident, fixed by direct ingest at 05:11:34; timeout-test polls 05:30–05:38), not scheduled runs. The log starts at 05:05 UTC, so hourly runs before that cannot be checked from this file.

### Watchdog — unverified from inside the VM (Finding F2)

`docs/recovery.md` states a cron watchdog runs `recover.sh` every 5 minutes (job `atlas-watchdog-5m`). From inside this VM that cannot be confirmed: `crontab` is not installed here (cron is platform-managed). The VM-replacement gap ended at 01:04:58 EST, ~3 s before a :05 watchdog tick would have fired — so the 4 m 57 s downtime is *consistent with* a working 5-minute watchdog that simply had not ticked yet, and equally consistent with a watchdog that is not running at all. The evidence cannot distinguish the two. The coordinator should verify the `atlas-watchdog-5m` job exists and last fired, via the cron tooling — not from the VM.

## 5. Database write failures — none observed

- Current incarnation (`logs/monitor.log`, 15 lines at final check): **15/15 cycles `db=ok`**, zero `db WRITE FAIL`, zero `db RECOVER`, zero `QUARANTINE`, zero `STARTUP ... FAIL` lines.
- Full-filesystem grep for `FAIL|ERROR|Traceback|QUARANTINE|CORRUPT|LOCKED|WRITE FAIL|RECOVER` across `logs/` and `data/diagnostics.json` returns only the word "recover" inside `recover.log` restart lines and the test names in `diagnostics.json` — no genuine error lines.
- No quarantine files exist anywhere under `~/workspace/atlas/` (`atlas-corrupt-*.db`: none). The Mission 1.1 quarantine path has therefore never fired on the live DB.
- `PRAGMA integrity_check` = `ok` at every check during this investigation (metrics 156 → 157 → 158 rows across checks, growing one row per cycle).
- `decisions` 28 rows, `events` 16 rows — both consistent with the restart history (§2).
- The Mission 1.1 recovery code itself was tested 16/16 against a corrupt *copy* (per the Mission 1.1 report) — the live path has never been exercised, which is good news, not a gap.

**Write-failure count: 0.** **Rows lost to DB errors: 0.** (Caveat again F1: pre-01:52 EST `monitor.log` evidence is gone; the claim rests on the current incarnation's clean log plus metrics continuity, integrity `ok`, and zero quarantine files.)

## 6. Snapshot generation — healthy

`data/snapshot.json` at final check (02:05:52 EST):

```json
{"ts": 1794985550, "cpu_pct": 70.68, "mem_total_kb": 8124900, "mem_avail_kb": 1224960,
 "mem_used_pct": 77.55, "load": [2.44, 2.14, 2.24], "disk_total": 161043427328,
 "disk_used": 30539649024, "disk_free": 130275192832, "disk_used_pct": 18.96,
 "net_rx_bytes": 14739932, "net_tx_bytes": 2648245, "gpu": null,
 "mining": "disabled", "trading": "disabled-paper-only", "emergency_stop": true}
```

- Snapshot `ts` advances every cycle (~60 s): `…5430, 5490, 5550` in the last three cycles. Age at checks: 2 s (final), ~10 s and ~42 s at intermediate checks depending on phase within the minute — always < 60 s.
- `emergency_stop: true`, `mining: disabled`, `trading: disabled-paper-only` on every cycle; config re-read each cycle per code (`load_config()` in the loop) and confirmed unchanged (`config/atlas.json`: `emergency_stop: true`, mining `enabled: false`, trading `paper-only`, `eligible_capital_usd: 0`).
- `atlas_core.py status` at 02:04 EST agrees: emergency_stop ON, mining DISABLED, trading paper-only, capital $0, metrics 157 rows and growing, last snapshot fresh.
- Daemon is still writing the snapshot: mtime tracks the latest cycle to the second.

## 7. Logging and error handling

### What works

- `monitor.log` is written **every cycle**: one `START` line plus one `cycle ts=… cpu=… mem=… db=ok stop=True` line per minute. Current incarnation (full file at 02:03 EST, 12 cycles):

```
2026-11-18T06:52:48Z monitor START pid=9711 db=/home/hatch/workspace/atlas/data/atlas.db emergency_stop=True mining=disabled trading=paper-only
2026-11-18T06:52:49Z cycle ts=1794984769 cpu=23.06 mem=76.67 db=ok stop=True
2026-11-18T06:53:49Z cycle ts=1794984829 cpu=28.65 mem=79.14 db=ok stop=True
2026-11-18T06:54:49Z cycle ts=1794984889 cpu=11.41 mem=81.37 db=ok stop=True
2026-11-18T06:55:50Z cycle ts=1794984949 cpu=15.87 mem=83.78 db=ok stop=True
2026-11-18T06:56:50Z cycle ts=1794985010 cpu=17.80 mem=84.77 db=ok stop=True
2026-11-18T06:57:50Z cycle ts=1794985070 cpu=14.62 mem=86.13 db=ok stop=True
2026-11-18T06:58:50Z cycle ts=1794985130 cpu=18.69 mem=88.44 db=ok stop=True
2026-11-18T06:59:50Z cycle ts=1794985190 cpu=20.74 mem=90.82 db=ok stop=True
2026-11-18T07:00:50Z cycle ts=1794985250 cpu=48.58 mem=87.24 db=ok stop=True
2026-11-18T07:01:50Z cycle ts=1794985310 cpu=30.70 mem=83.99 db=ok stop=True
2026-11-18T07:02:50Z cycle ts=1794985370 cpu=54.70 mem=85.17 db=ok stop=True
2026-11-18T07:03:50Z cycle ts=1794985430 cpu=35.98 mem=84.92 db=ok stop=True
```

- Rotation code exists in `atlas_monitor.py` (`MAX_LOG_BYTES = 1_048_576`, rotate to `monitor.log.1`, one backup kept) and the Mission 1.1 docstring claims it. At ~82 bytes/cycle it would trigger only after ~8–9 days of continuous uptime (~118 KB/day), so **rotation has never fired in practice** — no `monitor.log.1` exists, and the claim is untested live.
- Error handling in code (read, not executed): every DB write wrapped; LOCKED treated as transient with retry; CORRUPT quarantined (rename, never delete) with fresh-DB integrity check + rolled-back test write; snapshot keeps being written while the DB is down; config load failures logged, never fatal; `log()` itself swallows exceptions. No logged-but-unhandled error was found in surviving logs.

### Finding F1 — log truncation destroys crash evidence on every restart (needs a fix)

`core/recover.sh` starts the daemon with `nohup python3 core/atlas_monitor.py > logs/monitor.log 2>&1 &` — the `>` **truncates `monitor.log` on every restart**. `core/diagnostics.py` test 10 does the same (`> logs/monitor.log 2>&1`). Result: `monitor.log` only ever contains the *current* incarnation (1,222 bytes / 15 lines at final check). Every previous incarnation's cycles — and any traceback from a crash — are wiped at the moment of restart, which is exactly when that evidence is most needed. This is why the 04:23:53Z stillborn incarnation (22 s, zero rows) and any pre-01:52 EST DB errors cannot be investigated from logs at all. The in-daemon 1 MB rotation is moot while restarts truncate first. **Fix (for the coordinator/owner, not done here): append (`>>`) instead of truncate, or rotate-then-truncate in `recover.sh` and in diagnostics test 10 — e.g. move the old log to `monitor.log.<timestamp>` before starting.**

### Observation (not a daemon defect)

Host memory runs hot in the daemon's own readings: `mem_used_pct` 76–91% across cycles (84.92% at 02:03 EST, 77.55% at 02:05 EST), above the config `max_mem_pct: 70` cap; CPU spiked to 54–72% in several cycles (config `max_cpu_pct: 50`). The daemon itself is light (RSS ~10.8 MB). The coordinator already logged `throttle-background-work` at 06:52:46Z (CPU 56.08% over cap). This is host load, not daemon misbehaviour, but it is the context in which the daemon must keep running — worth watching, not a reliability failure.

## 8. Things that need a fix (reported, not fixed — read-only lane)

1. **F1 — `monitor.log` truncation on restart (highest value).** `recover.sh` and diagnostics test 10 both use `> logs/monitor.log`. Change to append/rotate-before-start so crash evidence survives the restart that follows it. Without this, the next real crash will again be uninvestigable from logs.
2. **F2 — Verify the 5-minute watchdog actually exists and fires.** `docs/recovery.md` claims cron job `atlas-watchdog-5m`; it cannot be confirmed from inside the VM (`crontab` not installed; cron is platform-managed), and the VM-replacement gap (4 m 57 s) shows no watchdog restart beat the manual one. Coordinator: list the cron jobs and confirm the watchdog's last run. If it is missing, the daemon has no automatic restore after a VM replacement — every replacement costs ~5 min of monitoring until a human restarts it.
3. **F3 — Rotation untested.** The 1 MB rotation in `atlas_monitor.py` has never fired (log never reaches 1 MB between truncations). After F1 is fixed, rotation will actually matter; verify it fires once rather than assuming.
4. **Minor — no pidfile / no `already-running` logging.** `recover.sh` exits silently (no log line) when the daemon is already running or when `flock -n` fails, so watchdog activity is invisible. Logging the no-op outcome would make F2 auditable from the logs.
5. **Minor — diagnostics tests 10/11 restart the daemon twice within ~2 s on every hourly run.** Harmless (no gap, no lost rows — the second restart lands inside the same minute), but it is the reason for the paired startup events and 2-second metric intervals, and it churns the daemon hourly. If the hourly run keeps doing this, consider whether test 10's direct restart plus test 11's `recover.sh` restart both need to run every hour.

## 9. Answers to the task questions (summary)

- **Exactly one daemon runs?** Yes — pid **9711** only, started 01:52:48 EST, uptime 13 m 03 s at 02:05:52 EST, PPID 1, state S, RSS ~10.8 MB. No duplicates, no stale PIDs. Flock on `data/recover.lock` held by pid 9711 only.
- **Restart/exit history?** 9 `recover.sh` restarts (04:31–06:52 UTC), 16 startup events (7 extra are diagnostics test-10 direct restarts). Causes: diagnostics tests 10/11 (×4 pairs), controlled timeout test, Mission 1.1 deploy incident, VM replacement, early bring-up. **Zero unplanned exits, zero crashes, zero tracebacks in surviving evidence.**
- **Metrics gaps?** Three, all known/planned: 381 s (timeout test, 00:30:32–00:36:53 EST), 160 s (Mission 1.1 deploy incident, 00:43:53–00:46:33 EST), 297 s (VM replacement, 01:00:01–01:04:58 EST). ~11 rows not written, all during known downtime. No other gap > 90 s in 161.6 min of history.
- **DB write failures?** **0.** 15/15 cycles `db=ok` in the current incarnation; no `WRITE FAIL` / `RECOVER` / `QUARANTINE` / `CORRUPT` / `LOCKED` lines anywhere; integrity `ok`; no quarantine files; 0 rows lost to DB errors.
- **Snapshot generation?** Healthy — `ts` advances every ~60 s, age 2 s at final check, `emergency_stop: true`, mining disabled, trading paper-only, capital $0. Daemon still writing it.
- **Needs a fix?** F1 (log truncation destroys crash evidence — fix `>` → append/rotate in `recover.sh` and diagnostics t10), F2 (verify the 5-min watchdog exists/fires via cron tooling), F3 (rotation untested), plus minors F4/F5 above. None of these were fixed by this lane (read-only).

## Appendix — raw evidence used

- `pgrep -af 'atlas_[m]onitor.py'` → `9711 python3 core/atlas_monitor.py`
- `ps -o pid,ppid,etime,start,stat,rss,cmd -p 9711` → `9711 1 13:03 06:52:48 S 10892 python3 core/atlas_monitor.py`
- `/proc/9711/fd` → `0→/dev/null, 1→logs/monitor.log, 2→logs/monitor.log, 3→data/atlas.db, 9→data/recover.lock`
- `logs/recover.log`: 9 lines (quoted in §2); `logs/monitor.log`: 15 lines at final check (quoted in §7); `logs/refresh-attempts.log`: 37 lines, last entry `06:55:18Z daemon PASS pid=2193 uptime=47m48s … diagnostics PASS 15/15`
- `data/atlas.db` (read-only queries): metrics 158 rows (04:24:16Z–07:05:50Z), decisions 28, events 16, `integrity_check ok`, 0 duplicate metric timestamps
- `data/snapshot.json`: ts 1794985550 at 02:05:52 EST, age 2 s
- `config/atlas.json`: `emergency_stop: true`, mining `enabled: false`, trading `paper-only`, `eligible_capital_usd: 0` — unchanged
- `core/diagnostics.py` t10 (lines ~210–227): SIGTERM + direct `(nohup python3 core/atlas_monitor.py > logs/monitor.log 2>&1 &)`; t11 (lines ~230–252): SIGTERM + `recover.sh`; `pgrep_monitor()` uses the bracket trick with a comment explaining it
- `docs/mission1.1-report-2026-11-18.md` §3: deploy incident (literal-filename pgrep self-match, daemon down ~2 min, ~2 missed rows)
- `docs/recovery.md`: cron watchdog `atlas-watchdog-5m` every 5 min; systemd unit present but not the active mechanism on this VM
- `atlas_core.py status` (02:04 EST): emergency_stop ON, mining DISABLED, trading paper-only, $0, metrics 157 rows and growing
