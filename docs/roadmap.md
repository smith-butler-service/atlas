# PROJECT ATLAS — Roadmap

Living roadmap. Updated after every meaningful milestone. Status words: DONE / IN PROGRESS / BLOCKED / NOT STARTED.

## Stages (Part 16)

| Stage | Scope | Status | Notes |
|---|---|---|---|
| 1 | Environment assessment | DONE 2026-11-17 | `docs/capability-report-2026-11-17.md` |
| 2 | ATLAS CORE (coordinator, DB, knowledge, config, monitoring) | IN PROGRESS | Monitor daemon + coordinator skeleton this session |
| 3 | First authorized worker | IN PROGRESS | This host = worker 1, monitoring/research only. Mining DISABLED here |
| 4 | Computing + NVIDIA intelligence | BLOCKED | No GPU on this host; needs authorized external resource |
| 5 | Mining operations | BLOCKED | No authorized mining host. Monero RandomX design ready, not deployed |
| 6 | Command Center | NOT STARTED | Fullstack artifact, real data via monitor snapshots, after Stage 2 |
| 7 | Blockchain connectivity | NOT STARTED | Public APIs verified; node + wallets need user-approved treasury design |
| 8 | Trading intelligence | NOT STARTED | Paper trading only; real trades need realized mining profits ($0 now) |
| 9 | Controlled autonomous trading | BLOCKED | Needs Stage 5 profits + Stage 8 tests passing |
| 10 | Distributed expansion | BLOCKED | Needs authorized external workers |
| 11 | Evolution + independence | NOT STARTED | Migration = copy `~/workspace/atlas` to independent Linux host |

## Financial state (Part 12 — real figures only)

- Gross mining revenue: $0 (no mining running)
- Confirmed mining proceeds: $0
- Operating expenses: $0
- Eligible trading capital: $0
- Realized trading profit: $0
- Emergency stop: ON (default; trading + mining disabled)

## Master directive stages (ordered 2026-11-17 23:29 EST)

| Stage | Scope | Status | Notes |
|---|---|---|---|
| 1 | Complete system testing (15 diagnostics) | DONE 2026-11-17 23:32 EST | 15/15 PASS after fixes; report `docs/diagnostics-2026-11-17.md` |
| 2 | Command Center | IN PROGRESS | Fullstack artifact `atlas-command-center` building; orb at top |
| 3 | Autonomous infrastructure discovery | NOT STARTED | |
| 4 | Mining intelligence | NOT STARTED | Design-only until authorized hardware |
| 5 | Direct blockchain connectivity | NOT STARTED | CoinGecko/MoneroOcean/blockchain.info verified; mempool.space unreachable from host |
| 6 | Secure wallet architecture | NOT STARTED | No wallets/keys exist yet |
| 7 | Paper trading engine | NOT STARTED | |
| 8 | Mining-to-trading integration | BLOCKED | Needs mining profits ($0) |
| 9 | Autonomous coordinator improvements | NOT STARTED | |
| 10 | Security, resilience and recovery | IN PROGRESS | recover.sh + recovery.md + diagnostics live |
| 11 | Controlled live-operation readiness | BLOCKED | Needs Stages 5–8 + user authorization |

## Hard rules (Part 15/17)

- Never mine on this host. Never spend, subscribe, or purchase without user authorization.
- Never create wallets/keys without an approved treasury design.
- Never report estimates as realized income. Every figure labeled live / snapshot / estimate / unavailable.
- Financial + security limits immutable without user authorization.
