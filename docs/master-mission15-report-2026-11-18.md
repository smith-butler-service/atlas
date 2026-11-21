# Master Mission 15 — Report

Date: 2026-11-19 05:52–06:01 UTC (00:52–01:01 EST). Agent: Mission 15.
Authorized by user voice 2026-11-19 00:52 EST ("accepted and also pass
to the next mission"). Design: `docs/master-mission15-design.md`.
STOP after M15 — no M16 without a new user order.

## Verdict: NO-GO — not ready to launch

Gates 1–4 unmeasured/untested; Gate 5 only XMR/Ryzen barely breaks
even (+0.000027 XMR/day Tier 2, XMR $504.99). Stop ON, simulation-only,
$0, configs unchanged (sha 46d3d12c1b90), no mining, no trading, no
wallets/keys, no real payouts, no spend.

## 1. Rendered Mining-tab check — NOT established (12th mission)

The orb-size edit build (agent 9d5c3350) was STILL running at every
status check in this mission (first check 05:52 UTC, last check
06:00 UTC — 36+ minutes after it started ~05:24 UTC). Per the
standing rule and the M15 brief, no `artifact.inspect` was called
while a build was running. The D-M14-6 inspection was therefore NOT
filed. The mirror itself still carries the honest null: "Rendered
Mining-tab check — not established by this mission" (getMining
`security.honestNulls`, read live this mission). The ready-to-run
verbatim inspection request is in the design file (D-M15-4, carried
verbatim from D-M14-6); file it the moment the orb build lands. The
"Show controls" toggle is likewise still unverified (same inspection).
Reload persistence still fails by design (in-memory tab state) — fix
NOT authorized.

Note on why the build is still running: the user was in a live voice
call issuing further orb orders throughout the mission window (rings,
labels, transparency, shield), each delivered to the running builder
via send_input. The build cannot be expected to land while new orders
keep arriving; do not treat its duration as a builder failure.

## 2. Daemon churn — follow-through: noise gone, drop NOT yet measurable, cause NOT established

Headline: 165 starts/24h at 06:00 UTC (167 at mission start — the
window slid past two old startups; this is window slide, not new
restarts), 178 all-time, unchanged. **Zero startups since 05:43:54
UTC** — the last of M14's two deliberate SIGTERM-test restarts. The
live daemon pid 33757 has now lived 16+ minutes (989 s at 06:00),
already past the M13 median lifetime (513 s), with the watchdog
passing at 05:47, 05:52, 05:57 (all no-op, pid 33757, snapshot fresh).
Snapshot age 25 s at final check; cycles normal every ~60 s.

### What was established

- **Scratch-daemon change re-proven twice over.** Two full
  diagnostics runs (28/28 each) left the live daemon pid 33757
  untouched and the events count at 178: t10 "scratch daemon pid
  37161 stopped on SIGTERM and restarted as 37179; live daemon pid
  33757 untouched"; t11 "recover.sh (scratch mode) restarted scratch
  daemon pid 37193 after a kill; live daemon pid 33757 untouched".
  Zero live restarts were caused by any M15 work. No scratch dirs or
  daemons left behind.
- **The 24h drop toward ~24 is NOT yet confirmed.** Only ~17 minutes
  of post-fix runtime had elapsed by mission end, and the 24h window
  is still dominated by pre-fix pairs. The drop is measurable only
  after a full post-fix day; the next hourly report and the next
  mission should re-derive the 24h count.
- **No new single has occurred since the fix**, so the H1/H2
  discriminator (read the newest timestamped monitor archive BEFORE
  the following restart) is still untested in the wild. It remains
  the standing procedure for the next single.
- **Attribution note (archives read this mission).** Pid 28239's
  archive (`logs/monitor-20261119-054338.log`) shows clean cycles
  through 05:43:24 and ends with no SIGTERM line and no traceback.
  28239 started 05:27:18, before M14's SIGTERM-handler edit, so a
  deliberate SIGTERM by M14 would be silent under the old code —
  consistent with M14's own attribution of "2 deliberate restarts"
  (28239 killed → 33689 at 05:43:38; 33689 killed → 33757 at
  05:43:54, the second kill leaving the proven `STOP SIGTERM
  received` line in `logs/monitor-20261119-054354.log`). This is
  attribution, not independent proof: the archive alone cannot
  distinguish a deliberate M14 kill from a genuine single for 28239.
  The same archive also captures the M14 scratch contamination
  (pid 31660 START 05:37:28 + one cycle) in the live log, matching
  the 1 spurious startup event (ts 1795066648) and 1 spurious
  metrics row (ts 1795066649) already disclosed by M14 and left in
  place.

Live hypotheses, unchanged: H1 uncaught exception in an unguarded
loop call (traceback now preserved by the new timestamped archives);
H2 external signal kill. Do NOT treat the coordinator-pass
correlation (M14: 8/12 long windows) as a cause.

## 3. Mirror scale mapping — re-confirmed live, proposal ready

Host `data/security.json` scale levels carry 14 fields, including
`workers_with_shares` (null / 100 / 1000) and `shares_per_worker`
(null / 100 / 100), from the M12 scale run (run_at 1795064957,
runDurationS 40.8, stale false). Live `getMining`
(`security.scale.levels` AND `security.scale.l1.levels`) carries
exactly 12 fields per level; `workersWithShares` / `sharesPerWorker`
are absent from both. The string `workers_with_shares` appears in the
payload only inside `scale.l1.note`. The drop is in the `getMining` /
`server/src/security.ts` projection, as M13 established.

Proposed addition (NOT authorized, NOT applied — needs a
repair-authorized inspection): add `workersWithShares` +
`sharesPerWorker` (camelCase, null preserved for baseline) to the
level projection in both `scale.levels` and `scale.l1.levels`. Exact
wording in the design file (D-M15-2).

## 4. "Show controls" toggle — NOT verified

Builder-attested but unverified: still a full-size pill centred below
the animation on desktop, not a small transparent icon pinned right.
Blocked on the same running orb build as §1. The check is folded
into the ready-to-run inspection request in the design file (D-M15-4);
fix NOT authorized.

## 5. Live-code tamper proof — proposal ready, NOT executed

M13 proved the R1–R4 rules in a sandbox spec only, not the deployed
TypeScript comparator. This mission re-checked the calibration live
on the current `getMining` payload, all 6 coin/profile rows: daily
figures match after rounding (R1 — XMR 10000 H/s 0.000659, 850 H/s
5.6e-05, 200 H/s 1.3e-05; KAS 0.00251; RVN 98.926231; ERG 0.522549),
KAS/ERG/RVN breakeven match after ÷1e6 (R2 — KAS 13118084451.598156
÷ 1e6 = 13118.084 → host 13118.1; ERG 2418834.887 → 2.419 → host 2.4;
RVN 464487.183 → 0.464 → host 0.5), pool-fee net Tier 2 matches
after rounding (MoneroOcean 0.000027117 → 0.000027; SupportXMR
0.000023165 → 0.000023). Profitability `mismatch: false`,
`mismatchDetails: []`; security `mismatch: false`. The M12 closure
stands. The repair-authorized inspection needed for live-code proof
is specified verbatim in the design file (D-M15-3). Do NOT execute
it from the mission.

## 6. Re-verification

| Check | Result |
|---|---|
| Suites | 77/77 — admin 5, coordinator 19, dashboard 4, profitability 11, security 18, reward_engine 20; all OK (full discover 116.4 s) |
| Diagnostics | 28/28 on re-run (first run 27/28: test 14 failed on transient endpoint timeouts — moneroocean/blockchain.info read timeouts in a slow window; test 18 passed all four endpoints 200 in the same run; clean 20 s later). Live daemon untouched by both runs; events rows unchanged at 178 |
| Security export | 9/9 (diagnostics t27) |
| Endpoints (curl) | CoinGecko 200, MoneroOcean /pool/stats 200, blockchain.info 200, mempool.space 200 |
| Safety | emergency_stop true, mining disabled, trading paper-only, eligible capital $0, config sha 46d3d12c1b90 (unchanged from M13/M14) |
| DB | user_version 4, integrity ok; metrics 1610, decisions 547, events 178, pool_stats 71; ledger/shares/batches/payouts/referrals all 0 |
| Profitability | XMR $504.99 (mirror input, fetchedAt 1795067270); net +0.000027 XMR/day Tier 2 (MoneroOcean 0%); breakeven 56.1 H/W; mismatch false |
| Daemon | pid 33757 (new code), 16+ min alive at final check, snapshot 25 s old; exactly 1 daemon |

Note: the mirror's `admin.network.daemonRestarts24h` read 170 in the
same `getMining` payload while the host-derived count was 167 at
05:52 (165 at 06:00 as the window slid). The two figures use
different windows; the host events-table count is the authority used
in this report. No restarts occurred during the mission either way.

## Gates (re-stated)

1. Measured browser hashrate — UNMEASURED.
2. Real pool shares — NOT TESTED (needs separate authorization).
3. Sustained run — NOT MEASURED.
4. Real payout — NOT TESTED (hard gate: needs explicit authorization
   + successful security testing + a treasury design, none exists).
5. Economics — only XMR on Ryzen 7 5800X barely breaks even
   (+0.000027 XMR/day Tier 2); everything else loses.

Launch verdict: NO-GO.

## Files changed (host-side only)

- `docs/master-mission15-design.md` — new (binding decisions D-M15-1
  to D-M15-4).
- `docs/master-mission15-report-2026-11-18.md` — this file.
- `data/diagnostics.json` — re-run by the diagnostics suite (normal).
- No code edits, no config edits, no artifact edits, no Gates 2/4
  work, no spend. No inspection filed (build still running).

## Decisions owed (carried + new)

Carried (unchanged): M6 finding 1 reward-display repair; refresh
failure repair; stale "no miner yet" copy (2 strings); host MEM%
alert re-scope; `config/atlas.json` mempool.space label; Obj 2
coordinator (2df2ea0f) leave/close/re-dispatch; SupportXMR stats-API
URL; referral rate 5% confirmation; minimum payout; Gates 2/4;
`roadmap.md`/`GOAL.md` stale bookkeeping; `docs/recovery.md`
corrections; RVN difficulty null/schema; refresh step-9 transform;
tariff `fetchedAt` schema.

New/updated from M15:
- Rendered Mining-tab check (12th mission) + Show-controls toggle —
  ready-to-run inspection (D-M15-4), blocked only on the orb build
  landing; file the moment it lands.
- Mirror scale mapping (`workersWithShares`/`sharesPerWorker`) —
  proposal ready (D-M15-2), repair-authorized inspection NOT filed.
- Live-code tamper proof — proposal ready (D-M15-3), inspection NOT
  filed.
- Daemon singles: the 24h startup count can only be confirmed as
  dropped after a full post-fix day — re-derive in the next hourly
  report / next mission; on the next single, read the newest
  timestamped monitor archive BEFORE the following restart (the
  H1/H2 discriminator).
- CLOSED this mission: none new (scratch-daemon proof re-confirmed
  twice over; calibration re-checked live on all 6 rows).
