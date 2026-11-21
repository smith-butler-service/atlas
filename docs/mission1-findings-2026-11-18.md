# Mission 1 — Step 1 Findings (2026-11-18 00:17 EST)

## Verdict so far: the failure is NOT on the host. The VM produces fresh snapshots every 60 s; the break is inside the Command Center's `refreshatlasdata` action, which reports success without landing a new snapshot. Artifact-side root cause is pending the dispatched builder inspection (started 00:12 EST, still running at 00:17 EST).

## Host side — VERIFIED HEALTHY (all evidence live, 00:15–00:17 EST)

- Monitor daemon: RUNNING, pid 7490, uptime 43:55, RSS 8.7 MB.
- Metrics cadence: exactly 60 s (latest rows ts 1794978826 / 8886 / 8946).
- DB: `data/atlas.db`, 55 metrics rows, 12 decisions, 5 events.
- Schema: `metrics(ts INTEGER PRIMARY KEY, cpu, mem_used_pct, load1, load5, load15, disk_used_pct, net_rx_bytes, net_tx_bytes)`; `events(id, ts, kind, message)`; `decisions(id, ts, dept, decision, reason)`.
- Snapshot file `data/snapshot.json`: ts 1794978946 (00:15:46 EST), CPU 51.91%, MEM 78.45% — byte-identical values to the latest DB row. DB and JSON agree.
- Write path is sound: monitor uses `INSERT OR REPLACE` + `commit` per cycle, and atomic `snapshot.json.tmp` + `os.replace`. Duplicate writes are safe (ts is PRIMARY KEY).
- Config `config/atlas.json`: emergency_stop true, mining disabled, trading paper-only, eligible capital $0, limits maxCpuPct 50 / maxMemPct 70.
- Coordinator `core/atlas_core.py`: clean; `decide()` logs 4 reasoned decisions per pass; `status()` reads live snapshot + DB. Minor cosmetic note: `decide()` uses float `time.time()` for decision ts against an INTEGER column.
- Recovery `core/recover.sh`: flock-guarded, idempotent, restarts daemon only if dead. `logs/recover.log` shows the two known restarts (04:31:20Z pid 7328 diagnostics test; 04:32:40Z pid 7490 current daemon).
- Diagnostics: 15/15 PASS (2026-11-17 23:32 EST).

## Failure evidence (artifact side, measured 00:07–00:12 EST)

- `refreshatlasdata` invoked 00:07 and ~00:10, both returned `ok:true` ("Refresh started — the dashboard updates when the new snapshot lands"), each given 60+ s. Dashboard snapshot stayed frozen at ts 1794978285 (00:04:45 EST) for 7 minutes; history stayed at 3 entries.
- `ingestsnapshot` with the live file contents worked immediately (snapshotId 4, 00:11 EST). Dashboard then showed ts 1794978645 (00:10:45 EST), history grew to 4 entries, receivedAt 05:11:34Z. Direct ingestion path is proven working.
- Daily silent refresh job `atlas-command-center-daily-refresh` is a space_action invoking `refreshAtlasData` daily 08:41:35 EST — it calls the SAME broken action, so it is affected too (silently "succeeding" without landing data).

## Gaps found (host side)

1. `logs/monitor.log` is EMPTY (0 bytes) — the daemon logs nothing: no per-cycle record, no write-failure record. Mission requires every refresh attempt logged; the artifact side must log its attempts, and the daemon should at minimum log write failures.
2. No host-side refresh-attempt log exists yet — to be created in Step 2 (`logs/refresh-attempts.log`), backfilled with tonight's attempts.
3. No duplicate protection is needed on the VM side (PRIMARY KEY + INSERT OR REPLACE + atomic replace already cover it).

## Root-cause hypothesis (UNCONFIRMED — do not treat as fact)

`refreshatlasdata` most likely returns ok before/without a confirmed write — either fire-and-forget with a background ingest that fails silently, or a file read that fails and is swallowed. The dispatched builder inspection will confirm or correct this. Never state it as fact until the handoff arrives.

## Backup (Step 4 prerequisite, done before any modification)

- `/home/hatch/workspace/atlas/backups/atlas-2026-11-18-pre-mission1.db` (20,480 B) — verified: 55 metrics rows, 12 decisions.
- `/home/hatch/workspace/atlas/backups/atlas-2026-11-18-pre-mission1.tar.gz` (17,876 B) — full tree, verified contents (backups + __pycache__ excluded).
- First backup attempt failed (sqlite3 does not expand `~`; then tar `--exclude` placed after positional args) — both fixed, backup re-run and verified. No production file has been modified yet.

## Jobs inspected

- `atlas-refresh-health-check-1h`: verified on disk (cron.view 00:17 EST) — interval 1h, next run Wed 2026-11-18 00:52:28 EST, delivery this chat, owner goal:project-atlas. Fallback step (direct `ingestsnapshot` with live file contents) is saved in the body.
- `atlas-command-center-daily-refresh`: space_action `refreshAtlasData`, daily 08:41:35 EST, owner space:atlas-command-center. Affected by the same defect.
