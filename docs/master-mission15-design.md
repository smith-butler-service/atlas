# Master Mission 15 — Design

Date: 2026-11-19 (05:52–06:xx UTC). Authorized by user voice 2026-11-19 00:52 EST
("accepted and also pass to the next mission").
Scope: the owed list from Mission 14 — file the D-M14-6 inspection once the
orb build lands, daemon-churn follow-through, mirror scale mapping and
live-code tamper proof proposals, full re-verification. STOP after M15; no
M16 without a new user order.

## D-M15-1 — Daemon churn follow-through (FINDINGS, root cause still NOT established)

M14 implemented the scratch-daemon change (D-M14-1), log retention and the
SIGTERM handler (D-M14-2). This mission re-proved the scratch change twice
over: two full diagnostics runs (28/28 each) left the live daemon pid 33757
untouched and the events count at 178 — t10 "scratch daemon pid 37161
stopped on SIGTERM and restarted as 37179; live daemon pid 33757 untouched",
t11 "recover.sh (scratch mode) restarted scratch daemon pid 37193 after a
kill; live daemon pid 33757 untouched". No scratch dirs or daemons left
behind. Zero live restarts were caused by any M15 work.

Counts at mission start (~05:52 UTC): 167 starts/24h, 178 all-time —
identical to M14's end, because the 24h window still covers the pre-fix
churn. Zero startups since 05:43:54 UTC (the last of M14's two deliberate
SIGTERM-test restarts). The live daemon pid 33757 has now lived 15+ minutes
at check time — already past the M13 median lifetime (513 s) — with the
watchdog passing at 05:47, 05:52, 05:57 (all no-op, pid 33757, snapshot
fresh). The 24h count CANNOT yet be confirmed as dropped toward ~24: only
~15 minutes of post-fix runtime had elapsed at mission start, and the
24h window is still dominated by pre-fix pairs. The drop is measurable
only after a full post-fix day; the next hourly report and the next
mission should re-derive the 24h count.

No new single has occurred since the fix, so the H1/H2 discriminator
(read the newest timestamped monitor archive BEFORE the following
restart) is still untested in the wild — it remains the standing
procedure for the next single.

Attribution note (from the archives, read this mission): pid 28239's
archive (`logs/monitor-20261119-054338.log`) shows clean cycles through
05:43:24 and then ends with no SIGTERM line and no traceback. 28239
started 05:27:18, before M14's SIGTERM-handler edit, so a deliberate
SIGTERM by M14 would be silent under the old code — consistent with
M14's own attribution of "2 deliberate restarts" (28239 killed →
33689 at 05:43:38; 33689 killed → 33757 at 05:43:54, the second kill
leaving the proven `STOP SIGTERM received` line in
`logs/monitor-20261119-054354.log`). This is attribution, not
independent proof: the archive alone cannot distinguish a deliberate
M14 kill from a genuine single for 28239. The same archive also
captures the M14 scratch contamination (pid 31660 START 05:37:28 + one
cycle) in the live log, matching the 1 spurious startup event
(ts 1795066648) and 1 spurious metrics row (ts 1795066649) already
disclosed by M14 and left in place.

Live hypotheses, unchanged: H1 uncaught exception in an unguarded loop
call (traceback destroyed by old rotation — now preserved by the new
timestamped archives); H2 external signal kill. Do NOT treat the
coordinator-pass correlation (M14: 8/12 long windows) as a cause.

## D-M15-2 — Mirror scale mapping proposal (NOT authorized, NOT applied)

Re-confirmed live this mission via `getMining` (saved payload):
- Host `data/security.json` scale levels carry 14 fields, including
  `workers_with_shares` (null / 100 / 1000) and `shares_per_worker`
  (null / 100 / 100), from the M12 scale run (run_at 1795064957,
  runDurationS 40.8, stale false).
- Mirror `security.scale.levels` AND `security.scale.l1.levels` carry
  exactly 12 fields; `workersWithShares` / `sharesPerWorker` are absent
  from both. The string `workers_with_shares` appears in the payload
  only inside `scale.l1.note`.
- Mechanism (M13, unchanged): the drop happens in the `getMining` /
  `server/src/security.ts` projection.

Proposed addition (exact, needs a repair-authorized inspection — do NOT
apply by hand): in the level projection in `server/src/security.ts`,
add `workersWithShares` (from host `workers_with_shares`) and
`sharesPerWorker` (from host `shares_per_worker`), camelCase, in both
`scale.levels` and `scale.l1.levels`. Preserve null for the baseline
level (host value is null there), never substitute 0. Verification
after the repair: `getMining` level rows for the 100- and 1,000-levels
must read `workersWithShares: 100/1000` and `sharesPerWorker: 100/100`,
baseline `null/null`.

## D-M15-3 — Live-code tamper proof proposal (NOT authorized, NOT executed)

M13 proved the R1–R4 comparison rules in a sandbox spec only, not the
deployed TypeScript comparator. This mission re-checked the calibration
live on the current `getMining` payload (all 6 coin/profile rows):
daily figures match after rounding (R1 — XMR 10000 H/s 0.000659,
850 H/s 5.6e-05, 200 H/s 1.3e-05; KAS 0.00251; RVN 98.926231;
ERG 0.522549), KAS/ERG/RVN breakeven match after ÷1e6 (R2 — KAS
13118084451.598156 ÷ 1e6 = 13118.084 → host 13118.1; ERG
2418834.887 → 2.419 → host 2.4; RVN 464487.183 → 0.464 → host 0.5),
pool-fee net Tier 2 matches after rounding (MoneroOcean 0.000027117 →
0.000027; SupportXMR 0.000023165 → 0.000023). Profitability
`mismatch: false`, `mismatchDetails: []`; security `mismatch: false`.
The M12 closure stands.

Proposed repair-authorized inspection (verbatim request for the parent
agent to file when authorized — carried verbatim from D-M14-5):
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

## D-M15-4 — Rendered Mining-tab check + "Show controls" toggle (BLOCKED / FILED — see report §1)

The orb-size edit build (agent 9d5c3350-bfa3-43d0-85aa-fb24e1fa103a)
was STILL running at every status check in this mission (last check
see report). Per the standing rule and the M15 brief, no
`artifact.inspect` was called while a build was running — unless the
build landed during the mission, in which case the inspection below
was filed and its result is in the report §1.

Ready-to-run inspection (verbatim request, repair_authorized: false,
carried verbatim from D-M14-6):
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
  profitability 11, security 18, reward_engine 20; all OK
  (full discover 116.4 s).
- Diagnostics: 28/28 on re-run (first run 27/28: test 14 failed on
  transient endpoint timeouts — moneroocean/blockchain.info read
  timeouts in a slow window; test 18 passed all four endpoints 200
  in the same run; clean 20 s later). Live daemon untouched by both
  runs; events rows unchanged at 178.
- Security export: 9/9 (diagnostics t27).
- Endpoints (curl): CoinGecko 200, MoneroOcean /pool/stats 200,
  blockchain.info 200, mempool.space 200.
- Safety: emergency_stop true, mining disabled, trading paper-only,
  eligible capital $0, config sha 46d3d12c1b90 (unchanged from M13/M14).
  DB user_version 4, integrity ok. Mining tables all 0.
- XMR $504.99 (mirror input, fetchedAt 1795067270); net +0.000027
  XMR/day Tier 2 (MoneroOcean 0% pool fee); breakeven 56.1 H/W.
  Only XMR/Ryzen barely breaks even; everything else loses.

## Gates (re-stated, all unchanged)

1. Measured browser hashrate — UNMEASURED.
2. Real pool shares — NOT TESTED (needs separate authorization).
3. Sustained run — NOT MEASURED.
4. Real payout — NOT TESTED (hard gate: needs explicit authorization +
   successful security testing + a treasury design, none exists).
5. Economics — only XMR on Ryzen 7 5800X barely breaks even
   (+0.000027 XMR/day Tier 2); everything else loses.

Launch verdict: NO-GO. Stop ON, simulation-only, $0, no wallets/keys,
no mining, no trading, no real payouts, no spend.
