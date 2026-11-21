# PROJECT ATLAS — Stage 1 Capability Report

Date: 2026-11-17 23:22 EST. Environment: Muse Linux VM (htch-runtime 7.0.0-44-generic, x86_64).
Measured live by the architect in this session. No capability is claimed without a check.

## What is genuinely available

| Resource | Measured | Verdict |
|---|---|---|
| Linux shell | bash, root (uid 0) | YES |
| CPU | 4 vCPUs visible, AMD EPYC 9D25; cell cap 1.5 shared CPUs | YES, shared/limited |
| RAM | 7,934 MB host view; cell cap 6 GB; 1,066 MB free at probe time | YES, tight |
| Persistent storage | /home/hatch 150 GB volume, 122 GB free; home dir survives VM replacement | YES |
| Disk for data | SQLite 3.45.1, Python 3.12.3, Node v24.22.1 | YES |
| Internet | CoinGecko API 200, MoneroOcean pool API 200 | YES |
| Blockchain APIs | CoinGecko + MoneroOcean reachable; mempool.space probe failed (000) — recheck owed | PARTIAL |
| Background services | systemd 255 (user instance), cron jobs, nohup processes | YES |
| Web deployment | Muse artifacts (static/fullstack), Vercel connector | YES |
| Process supervision | systemd user units supported; VM replaced on deployment — services must self-restore from ~/workspace | YES with caveat |

## What is missing

- **NVIDIA GPU: NONE.** `nvidia-smi` not found, no `/dev/nvidia*`, no GPU in PCI listing. All GPU work (Part 5, GPU mining, GPU inference) requires external authorized resources. Nothing GPU can be built or tested here.
- **No dedicated host.** The VM is a shared cell (1.5 CPU / 6 GB). Uptime at probe: 23 min — the VM is replaced on runtime deployment; only `~` persists.
- **No mining authorization on this host.** This VM is shared Meta infrastructure. Mining cryptocurrency on it would consume shared host compute without authorization. ATLAS rules (Part 3/15) forbid deploying a workload without the resource owner's explicit authorization. **Mining is DISABLED on this host, permanently, until an authorized external resource is approved.**
- **No wallets, no keys, no exchange accounts.** Nothing created. Trading capital is $0: no mining profits exist, so eligible trading capital is $0. Paper trading only.
- **No blockchain node.** No local node software installed. RPC access is via public APIs only, as backup-grade connectivity.

## The 10 questions (Part 18)

1. Computing resources genuinely available: 4 shared vCPUs (1.5 cap), ~6 GB RAM, 122 GB free disk, Python/Node/SQLite, systemd, cron, internet.
2. Persistent Linux environment: YES for `~` (files); NO for running processes (VM replaced on deploy — services must restore from disk).
3. Can install and run software: YES as root; installs outside `~` do not survive replacement — keep everything under `~/workspace/atlas` + reinstall scripts.
4. NVIDIA GPU: NO.
5. Persistent background services: YES via systemd user units + cron watchdog; startup-after-replacement must be verified, not assumed.
6. External blockchain networks: YES via public APIs (CoinGecko, MoneroOcean verified); mempool.space failed once — recheck.
7. Deploy backend + website: YES (artifacts + Vercel).
8. Buildable immediately: Core coordinator, SQLite state, metrics monitor, discovery research (read-only), paper-trading engine, Command Center wired to real local data.
9. Requires external infrastructure: any GPU work, any mining, any real trading, any blockchain node, any 24/7 independent operation.
10. Security/permission/technical limits: no mining on this host; no spending/purchases/subscriptions without user authorization; no wallets/keys until treasury design is approved; financial limits immutable without user authorization; emergency stop defaults ON.

## Architecture decision

ATLAS is plain Python (stdlib) + SQLite + JSON. No Muse-specific dependency, so it can migrate to independent infrastructure by copying `~/workspace/atlas` to any Linux host and running the same entry points. The Command Center is a separate web artifact fed by real monitor snapshots — never fabricated data; every figure is labeled live / snapshot / estimate / unavailable.

## Stage status

- Stage 1 (assessment): DONE — this report.
- Stage 2 (Core): IN PROGRESS — monitor daemon + coordinator skeleton + config.
- Stage 3 (first worker): this host is the first worker (monitoring + research only; mining DISABLED).
- Stages 4–11: blocked on external authorized infrastructure, except paper trading + discovery research which can proceed here.
