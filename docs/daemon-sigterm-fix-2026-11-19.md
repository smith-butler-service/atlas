# Daemon SIGTERM fix — 2026-11-19 (user order "Fix")

## Problem
The ATLAS monitor daemon died roughly every 2 h all day 2026-11-19 (8 deaths;
lifetimes 1h48m–2h15m; restarts 70/24h, 188 all-time at the 20:52 EST hourly
report). Three deaths left a `monitor STOP SIGTERM received` line (14:17,
19:40, 01:31 UTC); the rest died silently (no STOP line, no traceback).
One SIGTERM death is confirmed: a Smith Research pack agent's
`pkill -f 'atlas_monitor.py'` smoke test, 2026-11-19 14:17:31 UTC. The sender
of the other kills is still unknown. No system cron/timer kills it (checked
crontab, /etc/cron.d, systemd timers — only e2scrub/apt), no OOM in dmesg,
no job body instructs a kill, the daemon has no self-limit (plain
`while True` loop), and recover.log shows the 5-min watchdog running straight
through every death — so each death is a discrete kill of just the daemon,
not a VM outage. A fresh data point: the new-code daemon pid 7654 died
silently ~03:30 UTC 2026-11-20, minutes after the runtime service restarted
twice — consistent with runtime/service restarts SIGKILLing the daemon
(SIGKILL leaves no log line; the 17:36 UTC death was a cell reboot).

## Fix (core/atlas_monitor.py)
- Live daemon now IGNORES a stray SIGTERM and logs
  `monitor SIGTERM IGNORED count=N (live mode, no shutdown flag); staying
  alive`, then keeps cycling. Nothing in normal operation SIGTERMs the live
  daemon (recover.sh only starts it when dead; diagnostics kills only
  scratch daemons), so a stray SIGTERM is never legitimate.
- Authorized stop still works: touch `data/shutdown.flag` (fresh, <10 min
  old), then SIGTERM — the handler consumes the flag (one-shot) and exits
  cleanly. Stale flags are ignored.
- Scratch daemons (`--scratch`) keep the old behaviour — exit on SIGTERM —
  because diagnostics tests 10/11 assert exactly that.
- Startup logs the policy line (`mode=live SIGTERM ignored unless
  data/shutdown.flag is fresh (<10 min)`).

## Root-cause guard (the proven killer)
- Smith Research job body (`smith-research-max-2h`, via cron.update) and the
  research charter (`smith-research-charter-2026-11-18.md`, "Never:" list):
  never kill/pkill/SIGTERM/SIGKILL/restart the live daemon; restart tests use
  the scratch daemon only. The watchdog job body already says "do NOT kill
  anything" — unchanged.

## Verification (2026-11-19 ~21:28–21:34 EST)
- `python3 -m py_compile` OK.
- Throwaway daemon, temp HOME, live path: survived SIGTERM, logged IGNORED
  count=1; with a fresh shutdown flag it exited and consumed the flag.
- Same, `--scratch` path: exited on SIGTERM (diagnostics behaviour kept).
- Deployed live: old pid 1781 SIGTERMed (old code, clean exit), recover.sh
  restarted as pid 7654 with the new code (policy line in log, snapshot 8 s
  old, stop True). pid 7654 later died silently ~03:30 UTC in the service
  restart (see above); watchdog/manual recover restarted it as pid 1782,
  new code, cycling, snapshot fresh.
- Full diagnostics suite re-run after the fix (background, log at
  `~/workspace/goals/project-atlas/hidden_files/diagnostics-after-sigterm-fix.log`):
  26/28 PASS. Tests 10/11 PASS — scratch daemon stopped on SIGTERM and
  restarted, live daemon pid 1782 untouched (the exact behaviour this fix
  must preserve). The 2 FAILs are tests 14/18, both network timeouts
  (MoneroOcean + blockchain.info timed out after retry; CoinGecko 200) —
  unrelated to the code change; a direct curl re-check also returned 000
  for MoneroOcean, so the endpoints were genuinely unreachable at the time,
  not a test artifact.

## Still owed / limits of this fix
- SIGKILL cannot be ignored by any process. If the ~2h killer is the
  runtime reaping the daemon (service/cell restarts), silent deaths will
  continue at ~2h intervals and the watchdog restarts the daemon within
  5 min. **Proof window CLOSED 2026-11-20 ~05:51 UTC**: pid 1782 (new code,
  started 03:32:01 UTC) died SILENTLY — last log line a normal cycle at
  05:51:17 UTC, no STOP line, ZERO `SIGTERM IGNORED` lines in its whole
  log. The killer never sent a SIGTERM the new code could ignore, so the
  SIGTERM-ignore path remains UNTESTED in the wild. Watchdog recovered it
  as pid 1707 at 05:52:41 UTC (~84 s gap). Conclusion: in-process fixes
  cannot stop these deaths; the watchdog is the only cover, and it works.
- Daemon SIGTERM sender still unknown (other than the one pack-agent pkill).
