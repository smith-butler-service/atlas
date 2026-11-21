# ATLAS Master Mission 4 — Miner Prototype: Host-Side Test Report (Lane F)

**Date:** Wednesday, 2026-11-18 (checks run 09:04–09:06 UTC; diagnostics 09:04:48 UTC)
**Lane:** F — HOST-SIDE TESTING (read-only; nothing changed, nothing fixed, no config edited, no daemon restart outside the diagnostics suite's own design)
**Artifact:** `atlas-command-center` (build card `web-artifact-build-completed-45872587-bad1-4073-b58e-c93ce33226c1` per parent handoff; rendered Mining-tab check and Gates 1/3 probe measurements are a separate inspection lane — this report is host side only)
**Gates 2 and 4:** NOT TESTED in this mission (no pool connection, no real payout) — not attempted here.

## Verdict

**HOST SIDE PASS.** Daemon healthy (exactly one process), snapshot fresh, database intact, all safety settings unchanged, diagnostics **22/22 PASS**, no miner process, no wallet/key/seed material anywhere under `~/workspace/atlas`, all 9 Mission 2 Stage 0 tables still at 0 rows (no demo data seeded by the prototype build). Two standing issues carried forward, neither new: host MEM% above the 70% cap (87.72–89.64%) and mempool.space unreachable from this host on this run (DISPUTED — see §6). The Mission 3 refresh failure remains a known issue, not fixed, not touched (§8).

## 1. Daemon

| Item | Measured value |
|---|---|
| Process | `python3 core/atlas_monitor.py` — exactly **1** instance |
| PID at start of this lane | **15103**, elapsed **11:16**, %CPU 0.0, %MEM 0.1, RSS 9,620 KB |
| PID after diagnostics run | **17482**, elapsed **00:40** at re-check, %CPU 0.0, %MEM 0.1, RSS 14,460 KB |
| Why the PID changed | Diagnostics tests 10/11 restart the daemon twice **by design** (expected churn, not a failure). Original pid 15103 was stopped on SIGTERM and restarted; recover.sh then restarted it again after a kill. Final state: exactly one daemon, alive. |
| Daemon resources (diagnostics test 13/16) | RSS **14.1 MB** (< 50 MB limit), lifetime CPU **1.98%** — no unexpected resources held |
| Host uptime at check | 1 h 25 min; load average 0.75 / 1.31 / 1.39 |
| `pgrep -c` note | A raw `pgrep -c -f atlas_monitor.py` returned 2 because the checking shell command itself contains the pattern; `ps` confirms exactly one real daemon process (pid 17482). No manual restart was needed — the daemon was never dead. `recover.sh` was **not** invoked by this lane. |

## 2. Snapshot (`~/workspace/atlas/data/snapshot.json`)

Read twice; values below are the latest read (ts 1794992694, cycle 2026-11-18T09:04:54Z):

| Field | Value |
|---|---|
| `ts` | 1794992694 |
| Age at read | **40.1 s** (earlier read: ts 1794992666, age 14 s — fresh on both reads; 60 s monitor cycle) |
| `cpu_pct` | **43.75%** (earlier read 44.55%) |
| `mem_used_pct` | **89.64%** (earlier read 87.72%) — **above the 70% cap; standing pre-existing issue** (design §7.6), not caused by this mission |
| `mem_total_kb` / `mem_avail_kb` | 8,124,900 / 842,016 |
| `load` | [0.65, 1.26, 1.37] (earlier [0.96, 1.37, 1.41]) |
| `disk_used_pct` | **19.05%** (30,672,027,648 / 161,043,427,328 B used; 130,145,828,864 B free) |
| `net_rx_bytes` / `net_tx_bytes` | 13,140,578 / 2,382,501 |
| `gpu` | null |
| `mining` | **"disabled"** ✓ |
| `trading` | **"disabled-paper-only"** ✓ |
| `emergency_stop` | **true** ✓ |

Monitor log last line at check: `2026-11-18T09:04:54Z cycle ts=1794992694 cpu=43.75 mem=89.64 db=ok stop=True`.

## 3. Database (`~/workspace/atlas/data/atlas.db`)

| Check | Result |
|---|---|
| `PRAGMA integrity_check` | **ok** |
| `PRAGMA user_version` | **1** |
| File size | **172,032 bytes** (168.0 KB per diagnostics) |
| metrics rows | **290** (288 before the diagnostics run; +2 from monitor cycles during the run) |
| decisions rows | **64** (60 before; +4 logged by diagnostics test 07's decide pass, latest `no-throttle-needed`) |
| events rows | **37** (35 before; +2 from the diagnostics-driven daemon restarts) |
| Tables present | achievements, decisions, events, ledger, metrics, payouts, pool_stats, referrals, sessions, shares, sqlite_sequence, users, workers |

Mission 2 Stage 0 tables — **all 0 rows, no demo data seeded by the prototype build:**

| Table | Rows |
|---|---|
| users | 0 |
| workers | 0 |
| shares | 0 |
| ledger | 0 |
| payouts | 0 |
| referrals | 0 |
| achievements | 0 |
| pool_stats | 0 |
| sessions | 0 |

## 4. Safety

### Config — `~/workspace/atlas/config/atlas.json` (verified unchanged)

- `emergency_stop`: **true** ✓
- `mining.enabled`: **false** (status `design-only`; reason: no authorization to mine on shared host infrastructure) ✓
- `trading.mode`: **paper-only**; `trading.enabled` false; futures/leverage/margin/options all false ✓
- `trading.eligible_capital_usd`: **0** ✓
- `limits.max_cpu_pct`: **50**, `limits.max_mem_pct`: **70** — unchanged ✓
- `monitor_interval_s`: 60; `version`: 0.1.0-stage2; `host_role`: worker-1-bootstrap

### Config — `~/workspace/atlas/config/pool-rewards.json` (verified unchanged)

- `mode`: **simulation-only** ✓
- `minimum_payout.xmr`: **null**; `minimum_payout.piconero`: null; status "placeholder — not set" ✓
- Primary pool MoneroOcean 0% fee, `stats_endpoint` `/pool/stats`; fallbacks SupportXMR 0.6%, P2Pool 0%; reward split 75/25 on confirmed pool rewards only ✓
- `safety.emergency_stop`: honoured; `safety.secrets`: no wallet credentials, seed phrases, private keys, or wallet passwords stored anywhere in this config or in ATLAS ✓

### Miner processes — none

- `pgrep -x xmrig`, `pgrep -x minerd`, `pgrep -x cpuminer`, `pgrep -x XMRig`: **no matches** (exit 1).
- `ps aux | grep -iE 'xmrig|minerd|cpuminer'` (excluding the grep itself): **no miner process confirmed**. (An earlier `pgrep -af` with the pattern in the command line matched only the checking shell itself — a self-match, not a miner.)

### Wallet / key / seed files — none

- `find ~/workspace/atlas` for `*wallet*`, `*seed*`, `*.key`, `*private*`, `*.pem` (excluding node_modules/.git): **NONE FOUND**.
- Diagnostics test 15 independently confirms: no key material, no miner processes, config not world-writable, emergency stop ON, mining + trading disabled.

## 5. Diagnostics — `python3 ~/workspace/atlas/core/diagnostics.py` (run once)

**Result: 22 PASS, 0 FAIL, 0 NOT TESTED (of 22). Exit 0.** Run 2026-11-18 09:04:48 UTC; results in `~/workspace/atlas/data/diagnostics.json` (ts 1794992727).

| # | Test | Result |
|---|---|---|
| 01 | Python services | PASS — Python 3.12.3; atlas_monitor + atlas_core compile and import |
| 02 | Monitoring daemon | PASS — running pid 15103, state S |
| 03 | CPU and memory monitoring | PASS — CPU 44.55%, MEM 87.72% used, snapshot 23 s old |
| 04 | Disk and network monitoring | PASS — disk 19.05% used, net rx 13,083,724 B / tx 2,309,282 B |
| 05 | SQLite database integrity | PASS — integrity_check ok; 13 tables listed |
| 06 | Database persistence | PASS — 288 metrics rows, span 16,810 s |
| 07 | Coordinator decision-making | PASS — decide pass logged 4 new decisions |
| 08 | Decision logging | PASS — 5 recent decisions, all with reasons; latest: no-throttle-needed |
| 09 | Emergency stop | PASS — stop ON in config + snapshot; mining + trading disabled; hold decision logged (16x) |
| 10 | Service restart | PASS — daemon pid 15103 stopped on SIGTERM and restarted; fresh snapshot written |
| 11 | Automatic recovery | PASS — recover.sh restarted the daemon after a kill; fresh snapshot written |
| 12 | Deployment persistence | PASS — all essential files present; recovery procedure + script present |
| 13 | Resource consumption | PASS — daemon RSS 14.1 MB, lifetime CPU 1.98% |
| 14 | Network connectivity | PASS — coingecko:200, moneroocean:200, blockchain.info:200 |
| 15 | Security and permission controls | PASS — no key material, no miner processes, config not world-writable, stop ON, mining + trading disabled |
| 16 | Memory pressure | PASS — daemon RSS 14.1 MB (< 50 MB), DB 168.0 KB (< 100 MB), host MEM 89.64% (informational only) |
| 17 | Snapshot freshness | PASS — snapshot ts age 5 s (< 180 s) |
| 18 | API data validity | PASS — coingecko 200 `gecko_says='(V3) To the Moon!'`; moneroocean 200, hashRate=255,459,660 H/s, miners=4,976, lastBlockFound=3,808,963; blockchain.info 200, height=976,408; mempool.space HTTP None (SSL handshake timed out) after retry (non-fatal) |
| 19 | Database write latency | PASS — rolled-back test write 3.1 ms (< 1,000 ms), events rows unchanged at 37 |
| 20 | Daemon health | PASS — exactly 1 daemon (pid 17482, alive); monitor.log last line 30 s old |
| 21 | CPU pressure | PASS — daemon CPU 0.0% over 3 s window (< 25%), host load 0.52/1.17/1.34 (informational only) |
| 22 | Queue delays | PASS — latest metrics gap 2 s (expected ~60 s), newest row 33 s old |

Tests 10/11 restarted the daemon twice by design — expected churn, not a failure. Diagnostics was run **once only**, not looped.

## 6. Endpoints (curl, 10 s timeout each)

| Endpoint | Code | Time | Verdict |
|---|---|---|---|
| `https://api.coingecko.com/api/v3/ping` | **200** | 1.03 s | Reachable |
| `https://api.moneroocean.stream/pool/stats` | **200** | 1.34 s | Reachable (correct path — `/api/stats` 404s per prior record; not re-tested) |
| `https://blockchain.info/ticker` | **200** | 0.71 s | Reachable |
| `https://mempool.space/api/blocks/tip/height` | **000** | 10.06 s (timeout) | **DISPUTED — not settled** |
| mempool.space retry | **000** | 10.00 s (timeout) | Same — retried once before concluding, per instructions |

**mempool.space — DISPUTED, do not assert either way.** It was reachable at 01:52 and 02:25, returned 000 on recent attempts, and returned 000 twice in this run (curl, 10 s timeout) plus an SSL handshake timeout in diagnostics test 18 (after retry, non-fatal). The config still records it as `unreachable-from-this-host`. This run adds two more 000 data points; it does not settle the question.

## 7. Deviation cross-check — build note vs design

Read `docs/master-mission4-build-note.md` (§6 + §8 addendum) against `docs/master-mission4-design.md`.

**Note on count:** the task brief said "the 6 documented deviations"; the build note actually documents **7** — D1–D6 in §6 plus **D7** in the §8 addendum (coordinator deploy pass). All seven are recorded below and each is consistent with the design section it departs from.

| Deviation | Design reference | Build-note record | Consistent? |
|---|---|---|---|
| **D1** — Relay transport is an in-page Web Worker, not WebSocket | §2.1 specifies same-origin WebSocket relay | §6 D1: space runtime exposes no raw WebSocket endpoint; protocol shape, `local-test` markers, and validation (independent single-thread re-hash + exact 256-bit difficulty check) identical; pool-facing relay remains design-only | Yes |
| **D2** — Prebuilt WASM, not reproducible build | §1.2/R1 requires reproducing the VoltMiner recipe (RandomX-bonanza @ f9848e3, Emscripten 4.0.10, overlay patches) | §6 D2: no Emscripten in sandbox; mitigated by SHA-256 verification against published SHA256SUMS (mt `c42908af…`, st `0b73579e…`), overlay-patch hash verification of the `__thread` fix, and the reference-vector check on shipped single-thread bytes | Yes |
| **D3** — Bisect runs in light mode | §1.3 R3: accept-everything-target bisect, 1 vs 2 vs 4 threads | §6 D3: bisect is the pre-test gate, runs light mode because the rounding-mode bug lives in the VM execution path, not the dataset; keeps the gate fast; timed run uses the requested mode | Yes |
| **D4** — `client/build.mjs` extended with a worker build step | §8 handoff assumes the standard build | §6 D4: `Bun.build` does not bundle `new Worker(...)` references; step runs after the unchanged `buildClient()` call; if the platform pipeline ever stops executing `build.mjs`, the hook fails loudly | Yes |
| **D5** — Probe code ships inside the main bundle | §4.1: test-flag-gated probe hook, inert without the flag | §6 D5: platform bundler inlines the dynamic `import("./miner/probe")` (no code-splitting); code is present but inert — `installAtlasMinerTest` is never called without `?atlas-miner-test=1`, so no hook, no worker, no WASM fetch | Yes |
| **D6** — Content-Type / CSP platform-controlled | §1.4: `application/wasm` serving + `script-src 'self' 'wasm-unsafe-eval'` / `connect-src 'self'` CSP | §6 D6: this lane cannot set or verify them; worker treats JIT enablement as best-effort (falls back to interpreter and reports it); test lane to record live headers/CSP behaviour | Yes |
| **D7** — Workers + glue embedded, spawned from Blob URLs; only `.wasm` binaries as static assets | (Deploy fix — no design section; platform constraint) | §8 addendum: platform serves exactly one JavaScript bundle; first build failed ("expected exactly one JS bundle … found 5"); `build.mjs` now bundles the two workers + two vendor glue scripts as string constants in `client/src/miner/embedded.generated.ts`, probe spawns workers from Blob URLs with a one-time `bootstrap` message; `.wasm` copied to `client/dist/assets/vendor/randomx/` and served as static assets (verified present in platform build output); probe's loud-refusal check now HEADs the two `.wasm` assets; platform build after the fix: PASS | Yes — recorded in the addendum, consistent with the platform constraint |

**Undocumented deviations found: none.** No deviation was found in the build note, design, or host-side evidence that is not already recorded above. Two host-side limits on this cross-check:

- The artifact-side facts of D7 (embedded Blob-URL spawn, `.wasm` assets served) cannot be verified from the host — they belong to the rendered/inspection lane on the deployed build.
- One internal tension in the build note (not a deviation): the header still says "BUILT IN SOURCE — NOT YET DEPLOYED" while the §8 addendum records the platform build as PASS after the D7 fix. The parent handoff states the prototype is deployed (build card `web-artifact-build-completed-45872587-bad1-4073-b58e-c93ce33226c1`); the header was evidently not updated after the deploy pass. Flagged for the coordinator to reconcile, not a host-side finding.

## 8. Known issue carried forward — refresh failure (Mission 3 finding 1)

**NOT fixed, NOT worked around, NOT touched by this lane** (per design §6 and the mission instructions). The dashboard snapshot goes stale and refresh fails at the platform spawn step; the "Refresh complete" label is misleading when it re-ingests a stored snapshot. Evidence in this run: the snapshot itself was fresh throughout (ages 5–40 s, written by the daemon's 60 s cycle), which is the daemon's own freshness, not the dashboard refresh path — the two must not be conflated. The `logs/refresh-attempts.log` tail shows the last watchdog entries (09:02:39: daemon running pid 15103, snapshot fresh) and an 08:54:16 entry recording a button-retry landing a newer snapshot; neither entry is a repair of the underlying refresh failure. Repair still needs a separate repair-authorized inspection.

## 9. Scope notes

- Gates 2 and 4 were **not tested** (no pool connection, no real payout) — by design, not by omission.
- Gates 1 and 3 (probe-hook hashrate / sustained-run measurements) and the rendered Mining-tab check are the separate inspection lane's job; this report covers the host side only.
- Nothing was changed on the host by this lane except the diagnostics suite's own by-design daemon restarts (tests 10/11) and its normal metrics/decisions/events writes. No config edits, no file edits outside this report, no `recover.sh` invocation, no daemon restart by this lane.
