# PROJECT ATLAS

Autonomous, modular, intelligent computing ecosystem: authorized resource discovery,
CPU/NVIDIA workload optimization, legitimate mining, autonomous decentralized trading
funded **only** by realized net mining profits, and a real-time command center.

## Layout

- `docs/capability-report-2026-11-17.md` — Stage 1 environment assessment (measured, not claimed)
- `docs/roadmap.md` — living stage/roadmap + real financial state
- `core/atlas_monitor.py` — metrics daemon (stdlib only): CPU/RAM/disk/load/network → SQLite + JSON snapshot
- `core/atlas_core.py` — coordinator: config, state, decision log, emergency stop, status CLI
- `config/atlas.json` — immutable-unless-authorized limits
- `data/` — SQLite DB + latest snapshot (created by the daemon; never hand-edited)
- `logs/` — daemon + coordinator logs

## Run

```sh
python3 core/atlas_monitor.py   # daemon, 60 s samples, writes data/atlas.db + data/snapshot.json
python3 core/atlas_core.py status
```

## Safety defaults

- Mining: DISABLED on this host (shared infrastructure, no authorization).
- Trading: DISABLED, paper-only. Eligible capital $0 until real mining profits exist.
- Emergency stop: ON by default. It must be explicitly lifted by the user for any live activity.

## Migration

Copy `~/workspace/atlas` to any Linux host with Python 3.11+ and run the same entry
points. No Muse-specific dependency.
