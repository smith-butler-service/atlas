# ATLAS Recovery Procedure

## What survives a deployment replacement
- Everything under `~/workspace/atlas`: code (`core/`), config (`config/atlas.json`),
  database (`data/atlas.db`), snapshots (`data/snapshot.json`), logs (`logs/`), docs.
- Nothing else: running processes are stopped when the VM is replaced. This is a
  platform property, not a bug. Recovery is a restore, not a continuation.

## Restore (manual, ~30 s)
```sh
~/workspace/atlas/core/recover.sh
python3 ~/workspace/atlas/core/atlas_core.py status
```
`recover.sh` starts the monitor daemon only if it is not already running
(flock-guarded, idempotent). `atlas_core.py status` prints the live state and
the last snapshot time — if the snapshot is fresh (under ~2 min old), ATLAS is back.

## Automatic restore
- A cron watchdog runs `recover.sh` every 5 minutes (job: atlas-watchdog-5m).
  If the daemon died, the next run restarts it.
- A systemd user unit is provided at `config/atlas-monitor.service` for hosts
  with a running user manager (`systemctl --user enable --now atlas-monitor`).
  On this VM the cron watchdog is the active mechanism.

## Internal database recovery (Mission 1.1, 2026-11-18)
The monitor daemon now heals database failures itself instead of crashing:
- Every write is wrapped. On failure it logs the error, checks integrity,
  and retries. The live snapshot keeps being written even while the DB is down.
- A locked database is treated as transient (never as corrupt) and retried.
- A corrupt database is QUARANTINED, never deleted or overwritten: it is
  renamed to `data/atlas-corrupt-<UTC timestamp>-<pid>.db` (journal files move
  alongside), a fresh database is created, and writes resume only after the
  fresh database passes an integrity check plus a rolled-back test write.
- The emergency stop is read from `config/atlas.json` on every cycle and is
  never changed by the monitor or by recovery.
- All of this is logged with timestamps in `logs/monitor.log` (1 MB rotation,
  one backup kept). Before this change the daemon printed nothing, which is
  why `logs/monitor.log` was empty.
If you find a `data/atlas-corrupt-*.db` file, the database was corrupt and was
preserved for inspection. Do not delete it without checking what it holds.
1. `pgrep -f atlas_monitor.py` — a pid must be listed.
2. `cat ~/workspace/atlas/data/snapshot.json` — `ts` within the last 2 minutes.
3. `sqlite3 ~/workspace/atlas/data/atlas.db "SELECT COUNT(*) FROM metrics;"` — count grows.
4. `python3 ~/workspace/atlas/core/atlas_core.py status` — emergency stop ON,
   mining DISABLED, trading paper-only.

## Restore on a different Linux machine
1. Copy `~/workspace/atlas` to the new host (Python 3.11+ required).
2. Run `core/recover.sh`.
3. Run `core/diagnostics.py` — all 15 tests must PASS before any further stage work.
