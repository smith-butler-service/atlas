# Master Mission 14 — Design

Date: 2026-11-19 (05:30–05:55 UTC). Authorized by user voice 2026-11-19 00:30 EST ("Next mission").
Scope: the owed list from Mission 13 — rendered Mining-tab check, daemon
churn singles, mirror scale mapping, "Show controls" toggle, live-code
tamper proof, full re-verification. STOP after M14; no M15 without a new
user order.

## D-M14-1 — Diagnostics tests 10/11 run against a scratch daemon (IMPLEMENTED)

Problem: tests 10/11 SIGTERMed the live daemon twice per diagnostics run.
M13 quantified 164–168 starts/24h, ~85% (140 of 164) from t10/t11 by
design. Every hourly refresh, every mission suite run, and every manual
diagnostics run killed the live daemon twice.

Design (binding):
- `core/diagnostics.py`: t10/t11 now build a scratch ATLAS tree in a
  `tempfile.mkdtemp(prefix="atlas-scratch-")` directory — own HOME, own
  `workspace/atlas/{data,logs,config,core}` — copy the live
  `config/atlas.json` and the live `core/atlas_monitor.py` into it, and
  start the scratch daemon as `python3 core/atlas_monitor.py --scratch`
  with `HOME=<scratch home>` so `expanduser("~")` resolves under the
  scratch tree. The scratch daemon writes its own DB / snapshot / log;
  the live DB is never touched (verified: events rows unchanged at 176
  across the proving run, t19).
- `core/recover.sh`: opt-in scratch mode via `ATLAS_SCRATCH_DIR`. When
  set, ATLAS becomes the scratch tree, the pgrep pattern becomes the
  scratch-only `atlas_monitor\.py --scratch$`, the daemon is launched
  with `--scratch`, and HOME is exported to the scratch home (the
  grandparent of `<scratch>/workspace/atlas`) — without that export the
  scratch daemon resolves its paths from the caller's HOME and writes
  into the LIVE database (found live during manual testing: one spurious
  startup event ts 1795066648 + one spurious metrics row ts 1795066649
  from scratch pid 31660, before the fix; both rows left in place and
  attributed here, never silently deleted).
- `pgrep_monitor()` is now anchored: `atlas_[m]onitor\.py$`. The live
  daemon is started as `python3 core/atlas_monitor.py` with no arguments,
  so its command line ends with `.py`; the anchor keeps the scratch
  daemon (`... --scratch`) and any shell whose command text merely
  mentions the file out of the live result. `pgrep_scratch()` matches
  `atlas_[m]onitor\.py --scratch$` only.
- t10/t11 assert the live daemon pid is identical before and after
  (`live_after == live_before`); a change FAILS the test. Both tests
  tear down in `finally` (`_scratch_teardown`: SIGTERM, then SIGKILL if
  needed, then `shutil.rmtree`).
- Proof (this mission): full suite 28/28 on re-run; t10 "scratch daemon
  pid 32481 stopped on SIGTERM and restarted as 32491; live daemon pid
  28239 untouched"; t11 "recover.sh (scratch mode) restarted scratch
  daemon pid 32512 after a kill; live daemon pid 28239 untouched".
  No scratch dirs or daemons left behind.

Trade-off (accepted, recorded): t10/t11 no longer directly test that
the LIVE daemon restarts. What still covers the live path: t02 (live
daemon running + state), t17 (live snapshot fresh), t20 (exactly 1 live
daemon), and recover.sh itself — the same script, exercised end-to-end
in scratch mode on identical code. The live daemon's restartability is
now proven only when the watchdog actually restarts it (which the
singles provide ~1×/hour of evidence for). If a future mission wants a
direct live-restart test again, it must accept the two restarts it
causes and say so in its report.

Expected effect: diagnostics restarts drop to zero. Future 24h startup
counts should fall from ~167 to ~the singles rate (~24/24h) plus any
real deaths. The next hourly report can confirm the drop.

## D-M14-2 — Monitor-log retention + SIGTERM discriminator (IMPLEMENTED)

Problem: a spontaneous death's traceback survived exactly one rotation
(recover.sh moved `monitor.log` to `monitor.log.1`, destroying the
previous `.1`), and the next restart — minutes away — destroyed it.
M13 found no traceback in the two surviving rotations because both were
diagnostics kills, not singles.

Design (binding):
- `core/recover.sh`: rotation is now timestamped archives,
  `logs/monitor-<YYYYMMDD-HHMMSS>.log`, newest 10 kept
  (`ls -t | tail -n +11 | xargs -r rm -f`). No-op runs do not rotate.
- `core/atlas_monitor.py` `log()`: in-process 1 MB rotation keeps
  `.1/.2/.3` (was one backup).
- `core/atlas_monitor.py`: a SIGTERM handler (`_sigterm_handler`) logs
  `monitor STOP SIGTERM received, exiting` and raises SystemExit(0).
  Guarded install in `main()` (failure leaves prior behaviour). Purpose:
  the line is the discriminator for future singles — present means an
  external signal kill, a traceback means an uncaught exception, neither
  means SIGKILL / power loss / cell replacement.
- Proof: deliberate SIGTERM of the new-code daemon (pid 33689) left
  `2026-11-19T05:43:52Z monitor STOP SIGTERM received, exiting` as the
  last line of archive `logs/monitor-20261119-054354.log`, which survived
  the restart that followed. Live daemon now pid 33757 (new code).

Files backed up before editing: `backups/diagnostics-2026-11-18-mission14.py`,
`backups/recover.sh-2026-11-18-mission14`,
`backups/atlas_monitor-2026-11-18-mission14.py`.

## D-M14-3 — Daemon churn: singles investigation (FINDINGS, no root cause)

M13: 164 starts/24h, 85% t10/t11, 24 singles unexplained, no daemon
lived an hour. M14 re-derived on the window ending ~05:30 UTC:
167 starts/24h, 178 all-time; the same 24 singles (window slid, set
unchanged in substance).

Established this mission:
1. All 24 singles were restarted by `recover.sh` — exact-second match
   between the startup event and a `recover: restarted` line (99 such
   lines in ~25h). At least one case is explicitly logged by the
   watchdog as `FIXED daemon was down` (14:02:43, pid 1933; death window
   13:57:39–14:02:44, no diagnostics run inside it).
2. Death windows are bounded by the metrics table: 12 singles have a
   metrics gap >90 s (down-time 94–297 s, i.e. watchdog detection
   interval ≤5 min); the other 12 died <90 s before restart. No metrics
   gap >300 s and no watchdog gap >15 min in 24h — the daemon was never
   down long, and the watchdog ran continuously.
3. The daemon main loop has NO exit path except an uncaught exception,
   and six unguarded calls that can raise on a transient /proc or
   filesystem hiccup: `read_cpu()` (IndexError on a short /proc/stat
   line), `mem()` (KeyError/ValueError), `net_bytes()` (IndexError),
   `disk()` / `os.getloadavg()` (OSError), snapshot `os.replace`
   (OSError). Any of them kills the daemon WITH a traceback — which the
   old one-backup rotation then destroyed. There is no SIGTERM handler
   in the old code (added now, D-M14-2), so a signal kill was silent.
4. Correlation lead, NOT a cause: 8 of the 12 long down-windows contain
   a coordinator pass (pool_stats recorded_at ~:00:55/:10:55/:20:55/
   :30:55/:40:55/:50:55, anchored 05:40:49 EST Nov 18, every 10 min).
   Expected by chance for ~200 s windows on a 600 s grid is ~4/12;
   observed 8/12 (binomial p≈0.014) is suggestive but there is NO kill
   mechanism in coordinator code (verified by grep: no kill/SIGTERM/
   pgrep/recover reference outside a docstring), and the pattern is
   confounded by the hourly-diagnostics timing (daemons restarted by
   the :52–:57 hourly pair tend to die ~5–10 min later, and :00:55
   falls inside that window). The 12 short-window singles contain a
   pass in only 2/12, exactly chance. Do NOT treat the coordinator
   pass as the cause.
5. One single IS explained: 03:21:32 follows the cell/VM boot at
   ~03:20:25 UTC (from /proc/uptime 7876 s at 05:31:41) by 67 s.
6. The 10:28–10:33 burst (three deaths in ~5 min, recover restarts
   131 s / 109 s / 79 s apart — shorter than the 5-min watchdog) is
   consistent with concurrent diagnostics runs interleaving kills, not
   with a spontaneous crash (no diagnostics lines in
   refresh-attempts.log for that window, so the runs were mission-agent
   runs, not the hourly job).

Verdict: root cause NOT established. Live hypotheses, in order:
H1 — uncaught exception in an unguarded loop call on a transient
/proc or FS hiccup (traceback destroyed by old rotation).
H2 — external signal kill (diagnostics interleaving, host/OOM,
cell replacement) — silent under old code.
Discriminating test going forward (now possible): on the next single,
read the newest timestamped archive BEFORE the following restart; a
`STOP SIGTERM` line proves H2-signal, a traceback proves H1, neither
proves H2-SIGKILL/cell. The t10/t11 change (D-M14-1) removes the 85%
noise, so the next 24h of startups will be almost purely singles and
the rate will be measurable.

## D-M14-4 — Mirror scale mapping proposal (NOT authorized, NOT applied)

Re-confirmed live this mission via `getMining`:
- Host `data/security.json` scale levels carry 14 fields, including
  `workers_with_shares` (null / 100 / 1000) and `shares_per_worker`
  (null / 100 / 100), from the M12 scale run (run_at 1795064957:
  record_shares 1.28 s, 78,123.1/s, 1,000/1,000 workers).
- Mirror `security.scale.levels` AND `security.scale.l1.levels` carry
  exactly 12 fields; `workersWithShares` / `sharesPerWorker` are absent
  from both. The string `workers_with_shares` appears in the payload
  only inside `scale.l1.note`. `getMining` returns no
  `workersWithShares` anywhere.
- Mechanism (M13, unchanged): the drop happens in the
  `getMining` / `server/src/security.ts` projection.

Proposed addition (exact, needs a repair-authorized inspection — do NOT
apply by hand):
- In the level projection in `server/src/security.ts`, add
  `workersWithShares` (from host `workers_with_shares`) and
  `sharesPerWorker` (from host `shares_per_worker`), camelCase, in both
  `scale.levels` and `scale.l1.levels`. Preserve null for the baseline
  level (host value is null there), never substitute 0.
- Verification after the repair: `getMining` level rows for the 100-
  and 1,000-levels must read `workersWithShares: 100/1000` and
  `sharesPerWorker: 100/100`, baseline `null/null`.

## D-M14-5 — Live-code tamper proof proposal (NOT authorized, NOT executed)

M13 proved the R1–R4 comparison rules in a sandbox spec only
(`/tmp/m13_tamper_proof.py`, ephemeral), not the deployed TypeScript
comparator. The M12 closure of the profitability mismatch flag stands
(78 fields, 15 skipped, 0 diffs on two exports), and this mission
re-checked the calibration live: KAS breakeven mirror 12920302181 ÷ 1e6
= host 12920.3; XMR daily mirror 0.000665006… → host 0.000665.

Proposed repair-authorized inspection (verbatim request for the parent
agent to file when authorized):
"Verify the deployed profitability comparator in the ATLAS Command
Center actually applies the R1–R4 calibration from
docs/master-mission9-repair-design.md (R1 round mirror figures to host
precision before comparing, R2 compare KAS breakeven after ÷1e6,
R3 skip GPU currentHw/ratioTier2, R4 skip browser-split when host is
null), by tampering a COPY of the live mirror figures — XMR daily
+10%, KAS breakeven 12458.4→13000, pool-fee +10%, verdict flip — and
confirming the deployed comparator flags mismatch: true with the field
named, while the un-tampered live figures still read mismatch: false.
Do not change any live figure or stored data; report the exact
comparator code location and the tamper results."

## D-M14-6 — Rendered Mining-tab check + "Show controls" toggle (BLOCKED)

The orb-size edit build (agent 9d5c3350-bfa3-43d0-85aa-fb24e1fa103a:
orb 25% bigger, centred, centre 50% more transparent) ran for the
whole M14 window (still running at 05:50 UTC, ~25 min). Per the
standing rule and the M14 brief, no `artifact.inspect` was called
while a build was running. The rendered Mining-tab check is therefore
NOT established for the 11th consecutive mission, and the "Show
controls" toggle (builder-attested full-size pill centred below the
animation on desktop, not a small transparent icon pinned right)
remains unverified.

Ready-to-run inspection (verbatim request, repair_authorized: false,
file once the orb build has landed):
"On the ATLAS Command Center (now S.M.I.T.H.), select the Mining tab
on desktop 1440x900 AND on mobile 390x844, screenshot the Security &
Scale section on both, and record any console errors and any mobile
horizontal overflow with the Mining tab open. Then reload the page and
report whether the Mining tab selection persists. Separately, on
desktop, check the 'Show controls' toggle: is it a small transparent
icon pinned to the right side of the screen, or a full-size pill
centred below the animation? Report exactly what you find with
screenshots; do not change anything."

If a render defect is found, propose a repair-authorized inspection —
do not dispatch it from the mission.

## Re-verification (this mission)

- Suites: 77/77 — admin 5, coordinator 19, dashboard 4,
  profitability 11, security 18, reward_engine 20; all OK.
- Diagnostics: 28/28 on re-run (first run 26/28: tests 14/18 failed on
  transient endpoint timeouts — moneroocean/blockchain.info/mempool.space
  read timeouts during a slow window; re-run 34 s later passed clean).
- Security export: 9/9 (diagnostics t27).
- Endpoints (curl): CoinGecko 200, MoneroOcean /pool/stats 200,
  blockchain.info 200, mempool.space 200.
- Safety: emergency_stop true, mining disabled, trading paper-only,
  eligible capital $0, config sha 46d3d12c1b90 (unchanged from M13).
  DB user_version 4, integrity ok. Mining tables all 0.
- XMR $504.21 (mirror input, fetchedAt 1795066257); net +0.000033
  XMR/day Tier 2 (MoneroOcean host poolFees; re-derived 3.1e-05 by
  diagnostics t26); breakeven 55.6–55.7 H/W. Only XMR/Ryzen barely
  breaks even; everything else loses.

## Gates (re-stated, all unchanged)

1. Measured browser hashrate — UNMEASURED.
2. Real pool shares — NOT TESTED (needs separate authorization).
3. Sustained run — NOT MEASURED.
4. Real payout — NOT TESTED (hard gate: needs explicit authorization +
   successful security testing + a treasury design, none exists).
5. Economics — only XMR on Ryzen 7 5800X barely breaks even
   (+0.000033 XMR/day Tier 2); everything else loses.

Launch verdict: NO-GO. Stop ON, simulation-only, $0, no wallets/keys,
no mining, no trading, no real payouts, no spend.
