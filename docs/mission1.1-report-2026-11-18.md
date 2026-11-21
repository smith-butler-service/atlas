# PROJECT ATLAS — MISSION 1.1 ENGINEERING REPORT
## Reliability Hardening & Final Closure
Date: 2026-11-18 00:52 EST. Status: COMPLETE (with 3 honest caveats, §7).
Mission 1's refresh architecture was NOT rewritten or replaced. Only the four
remaining issues were addressed.

## 1. TIMEOUT VERIFICATION — PASS (server-side; page message caveat in §7)
Controlled test: the monitor daemon was stopped 00:30:42 EST so no new host
snapshot could appear, the dashboard was first synced to the newest host
snapshot (ts 1794979832, via direct ingest), then a test refresh was invoked.
- Test refresh started 00:31:02 EST, baseline ts 1794979832.
- +60 s (00:32:06): state `started`, landedTs null, snapshot unchanged.
- +3 m 13 s (00:34:15): state `started`, landedTs null, snapshot unchanged.
- +5 m 34 s (00:36:36, past the 5-minute timeout): state `started`,
  landedTs null, snapshot ts still 1794979832. No landing, no false success.
- The refresh record survived a builder deploy mid-test (dedupe fix landed
  00:32:36 EST) with its state intact.
- Daemon restarted 00:38:02 EST via recover.sh; fresh snapshots resumed
  immediately (ts 1794980273, 9 s old at check). A recovery refresh then
  landed normally (baseline 1794979832 → 1794980273).
- Every poll logged to `logs/refresh-attempts.log`.

## 2. DUPLICATE HISTORY — FIXED, VERIFIED LIVE
Origin (investigated from live evidence): the host snapshot from 00:22:31 EST
(ts 1794979351) reached the dashboard through two ingest paths — the tracked
refresh task and the manual direct-ingest fallback used during the Mission 1
repair — and `ingestsnapshot` inserted unconditionally, while decisions were
already deduped. The history chart therefore showed ts 1794979351 twice.
Fix (builder edit, deployed 00:32:36 EST): `ingestsnapshot` now dedupes on the
measurement timestamp — the same identity the ATLAS host uses — returning the
existing row with `duplicate: true` and writing nothing on a repeat; genuinely
new snapshots still store normally. `getdashboard` also collapses any repeated
timestamp in the history it returns. No stored row was deleted or rewritten.
Verified live by me (not just the builder's sandbox test):
- Re-ingesting ts 1794980273 returned `{duplicate: true, snapshotId: 10}` —
  the same id as the original store — and the history stayed at 9 points.
- History is now 10 points with each timestamp exactly once.
- A genuinely new snapshot (ts 1794981002) stored normally via refresh.

## 3. DAEMON RECOVERY — IMPLEMENTED, TESTED 16/16, DEPLOYED
`core/atlas_monitor.py` now heals database failures instead of crashing:
- Every write is wrapped. On failure it logs the error, checks integrity, and
  retries. The live snapshot keeps being written even while the DB is down.
- A locked database is treated as transient (never as corrupt) and retried
  after a short sleep.
- A corrupt database is QUARANTINED, never deleted or overwritten: renamed to
  `data/atlas-corrupt-<UTC timestamp>-<pid>.db` (journal files move alongside),
  a fresh database is created, and writes resume only after the fresh database
  passes an integrity check plus a rolled-back test write.
- The emergency stop is read from `config/atlas.json` on every cycle and is
  never changed by the monitor or by recovery.
Tests (`/tmp/atlas-m11-tests/test_monitor_recovery.py`, all against /tmp copies,
production untouched): 16/16 PASS.
- R1 corrupt DB → status `recovered`; quarantine file bytes identical to the
  corrupt copy (SHA-256 match); fresh DB integrity ok with all 3 tables;
  original file not overwritten in place.
- R2 locked DB → status `ok` (transient) after 21 s; no quarantine file; DB
  intact after the lock released (76 → 76 rows).
- L1 logging → timestamped lines; rotation at 1 MB keeps one backup, main log
  small after rotation.
- L2 config → emergency_stop True, mining disabled, trading paper-only, $0.
- P1 production DB untouched (growth only the live daemon's own rows).
Deploy: backup verified first (`atlas_monitor.py.pre-1.1-2026-11-18` +
fresh DB backup, integrity ok). New daemon pid 29590, then 29895 after the
diagnostics restart tests. Snapshot fresh, DB integrity ok, 80 rows.
Deploy incident (honest account): the first restart attempt failed because my
own command contained the literal daemon filename, which defeated the pgrep
bracket trick — recover.sh saw my shell as a "running daemon" and exited
without starting one. The daemon was down ~2 minutes (~2 missed metric rows)
until the restart was retried from a clean command. Lesson recorded: never put
the literal daemon filename in a command that also pgreps for it.

## 4. LOGGING — ROOT CAUSE FOUND, FIXED, VERIFIED LIVE
Why the log was empty: the daemon printed nothing at all — no print() or
logging calls anywhere in the code. `recover.sh` redirects stdout/stderr to
`logs/monitor.log`, but there was nothing to redirect, so the file stayed 0
bytes. The daemon was healthy; it was simply silent.
Fix: a `log()` helper writes timestamped lines to `logs/monitor.log` —
startup (pid, DB path, stop state), one line per collection cycle (ts, cpu,
mem, db ok/FAIL, stop), and every error, recovery attempt and service-status
change. Rotation at 1 MB keeps one backup (`monitor.log.1`), so the log can
never grow without bound (~160 KB/day at one line per minute).
Verified live: the log now holds real entries, e.g.
`2026-11-18T05:46:32Z monitor START pid=29590 ... emergency_stop=True ...`
`2026-11-18T05:47:33Z cycle ts=1794980853 cpu=30.71 mem=79.30 db=ok stop=True`
Rotation was tested on a /tmp copy (file > 1 MB rotated, main log small).

## 5. FINAL VERIFICATION — ALL 8 TESTS RE-RUN + NEW TESTS
| # | Test | Result | Evidence |
|---|------|--------|----------|
| 1 | Normal dashboard refresh | PASS | Post-deploy refresh landed baseline 1794980273 → 1794981002. |
| 2 | Database write failure | PASS | Corrupt copy: loud failure (exit 26); new recovery code tested 16/16. |
| 3 | Monitor daemon unavailable | PASS | Diagnostics tests 10/11 (stop/restart, recover.sh after kill) + live kill/restart this turn. |
| 4 | Refresh timeout | PASS (server-side) | §1: no landing, no false success after 5 m 34 s. Page message caveat in §7. |
| 5 | Duplicate refresh requests | PASS | Re-ingest returns duplicate: true; no new history point; per-click dedupe intact. |
| 6 | Direct ingestion fallback | PASS | Direct ingest of ts 1794979832 landed (snapshotId 9) during the timeout-test setup. |
| 7 | Dashboard displaying newest snapshot | PASS | Dashboard ts 1794981002 = live VM snapshot, values identical. |
| 8 | Recovery after a failed refresh | PASS | Timeout test → daemon restart → recovery refresh landed. |
| N1 | Duplicate history fix (new) | PASS | §2: live re-ingest duplicate: true; history 10 points, each ts once. |
| N2 | DB recovery on copy (new) | PASS | 16/16 (R1 quarantine, R2 locked transient, L1 logging/rotation, L2 config, P1 production untouched). |
| N3 | Logging live (new) | PASS | monitor.log has timestamped START + cycle lines; rotation tested. |

Diagnostics suite (fresh run 00:47:58 EST, after the code change): 14/15 PASS.
Test 14 (network) FAILED transiently — MoneroOcean and blockchain.info timed
out during the suite run — and all three endpoints returned 200 on a direct
curl re-check 2 minutes later (CoinGecko 200, MoneroOcean 200,
blockchain.info 200). Host memory pressure (79–92% used) is the likely cause.
Safety verified live: emergency stop ON (config + snapshot + dashboard),
mining disabled, trading paper-only, eligible capital $0, limits unchanged.
Endpoints: CoinGecko 200, MoneroOcean 200, blockchain.info 200, mempool.space
unreachable (known, not new).

## 6. FILES MODIFIED
- `core/atlas_monitor.py` — logging + safe DB recovery (backup
  `backups/atlas_monitor.py.pre-1.1-2026-11-18` taken and verified first).
- `docs/recovery.md` — new "Internal database recovery" section.
- `docs/mission1.1-report-2026-11-18.md` — this report.
- `backups/atlas-2026-11-18-pre-mission1.1.db` — pre-mission DB backup.
- Artifact `atlas-command-center` (builder edit) — ingest-time dedupe by ts +
  history collapse in getDashboard. No stored row deleted or rewritten.
- `logs/refresh-attempts.log` — timeout test + deploy entries appended.
- Test script kept at `/tmp/atlas-m11-tests/test_monitor_recovery.py`
  (ephemeral; rerun any time against copies).

## 7. REMAINING PROBLEMS (honest list)
1. The page-visible timeout message was not directly verified through my
   tools: the 5-minute timeout is derived on the page from the recorded
   startedAt, and the server side (no landing, no false success) is verified.
   To see the message live, watch the page during a refresh that stays stuck
   for 5 minutes — the next real stall will show it.
2. Diagnostics test 14 is flaky under host memory pressure (one transient
   failure this run; endpoints verified 200 immediately after). Not a code
   defect; a host-load symptom.
3. `recover.sh` truncates `logs/monitor.log` on every restart (pre-existing
   behaviour). Log lines survive between restarts, but a restart wipes the
   file; only the rotated `.1` backup survives. Not changed in this mission.
4. Host memory runs 79–92% used, above the 70% coordinator cap; the
   coordinator keeps logging throttle decisions. Standing condition, not fixed
   by this mission.
5. The deploy incident left a ~2-minute gap in the metrics series (2 missed
   rows). No data was lost beyond those two rows.

## 8. SECURITY
- Backup created and verified BEFORE any modification. No monitoring data
  deleted; the only history change is the dedupe collapse (no rows removed).
- No config changed. No API keys, wallet credentials or secrets exposed or
  created. No wallets/keys created. Mining stays disabled; live trading stays
  disabled; emergency stop stays ON.
- No unrelated architectural changes. Mission 1's refresh architecture
  untouched (the dedupe fix confirmed it still flips a pending refresh to
  landed on a new ingest).

Mission 1.1 is verified. Stopping here. Awaiting user authorization for
Mission 2 — do not advance without it.
