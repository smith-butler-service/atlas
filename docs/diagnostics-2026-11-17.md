# ATLAS Stage 1 Diagnostics — 2026-11-17

Final run: 2026-11-17 23:32:38 EST (2026-11-18 04:32:38 UTC). Script: `core/diagnostics.py`.
Results: `data/diagnostics.json` (ts 1794976365).

## Result: 15 PASS, 0 FAIL, 0 NOT TESTED

| # | Test | Result | Measured evidence |
|---|---|---|---|
| 01 | Python services | PASS | Python 3.12.3; atlas_monitor + atlas_core compile and import |
| 02 | Monitoring daemon | PASS | Running pid 7328, state S |
| 03 | CPU and memory monitoring | PASS | CPU 11.39%, MEM 93.23% used, snapshot 16 s old |
| 04 | Disk and network monitoring | PASS | Disk 18.66% used, net rx 17,238,001 B / tx 2,891,742 B |
| 05 | SQLite database integrity | PASS | `integrity_check` ok; tables decisions, events, metrics, sqlite_sequence |
| 06 | Database persistence | PASS | 9 metrics rows, span 486 s, DB at `~/workspace/atlas/data/atlas.db` |
| 07 | Coordinator decision-making | PASS | `decide` pass logged 4 new decisions |
| 08 | Decision logging | PASS | 5 recent decisions, all with reasons; latest: no-throttle-needed |
| 09 | Emergency stop | PASS | Stop ON in config + snapshot; mining + trading disabled; hold decision logged (3x) |
| 10 | Service restart | PASS | Daemon pid 7328 stopped on SIGTERM and restarted; fresh snapshot written |
| 11 | Automatic recovery | PASS | `recover.sh` restarted the daemon after a kill; fresh snapshot written |
| 12 | Deployment persistence | PASS | All essential files under `~/workspace/atlas`; recovery procedure + script present; processes do not survive VM replacement by platform design — restore is via `recover.sh` |
| 13 | Resource consumption | PASS | Daemon RSS 13.3 MB, lifetime CPU 1.98% |
| 14 | Network connectivity | PASS | coingecko:200, moneroocean:200, blockchain.info:200 |
| 15 | Security and permission controls | PASS | No key material, no miner processes, config not world-writable, emergency stop ON, mining + trading disabled |

## Baseline and fixes applied

Baseline run 23:30 EST: **10 PASS, 5 FAIL**. All 5 failures were test defects or one dead
endpoint — the ATLAS code itself was never at fault. Fixes applied in this loop:

1. **T10 "daemon did not stop on SIGTERM" — false failure.** The daemon DID stop.
   The test's `pgrep -f 'atlas_monitor.py'` matched its own `sh -c` shell (the shell's
   command line contains the pattern), so pgrep never returned empty. Fixed with the
   bracket trick: `pgrep -f 'atlas_[m]onitor.py'` (matches the daemon, not the shell).
2. **T11 "[Errno 3] No such process" — same cause.** It tried to kill the already-dead
   shell's pid returned by the self-matching pgrep. Fixed by the same bracket trick.
3. **T13 "/proc/7267/status missing" — same cause.** It read /proc for the self-matched
   shell pid. Fixed by the bracket trick.
4. **T14 mempool.space unreachable — confirmed dead 3 times** (curl 000 twice, urllib
   TimeoutError). Replaced in T14 with blockchain.info
   (`https://blockchain.info/q/getblockcount`, verified 200). `config/atlas.json`
   updated: `mempool_space: "unreachable-from-this-host"`, `blockchain_info: "verified-200"`.
   CoinGecko + MoneroOcean remain the primary sources.
5. **T15 two false positives.**
   - (a) "private key material in diagnostics.py": the scanner's loose check
     (`"BEGIN"` + `"PRIVATE KEY"` as separate substrings) matched its own source code.
     Fixed with the strict PEM armor regex `-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----`.
   - (b) "miner process running": the same pgrep self-match — the shell command line
     contained `xmrig|minerd|...` verbatim. Fixed with bracketed alternatives:
     `[x]mrig|[m]inerd|[c]puminer|[e]thminer|[t]-rex|[l]olminer`.

Re-run after fixes: **15/15 PASS on the first re-run** (no further re-runs needed).
Post-run verification: daemon running (pid 7490, restarted by T11's `recover.sh`),
snapshot 12 s old at check time.

## Observations (not failures)

- Host memory pressure is high: 91–94% used, ~650 MB free. The daemon itself is light
  (13.3 MB RSS, 1.98% lifetime CPU), so ATLAS is not the cause — but ATLAS must stay
  lightweight (Part 12) and never assume spare RAM.
- A transient CPU spike to ~85% was seen in the snapshot immediately after the
  diagnostic run (restarts + test load). Steady-state daemon CPU is ~2%; the spike is
  the test harness, not the daemon.

## Readiness verdict for Stage 2

**Stage 1 COMPLETE — ATLAS is ready for Stage 2 (Command Center).**
All 15 diagnostic tests pass against the live installation. No mining, no trading, no
wallets, no keys exist; emergency stop is ON; mining and trading remain disabled.
The Command Center build is proceeding separately.
