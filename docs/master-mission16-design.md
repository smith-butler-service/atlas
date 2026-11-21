# Master Mission 16 — Design

Date: 2026-11-19 (06:02–06:08 UTC). Authorized by user voice 2026-11-19 01:02 EST
("And also next mission if any come up.").
Scope: the owed list from Mission 15 — file the D-M15-4 inspection once the
orb build lands, daemon-churn follow-through, mirror scale mapping and
live-code tamper proof proposals, full re-verification. STOP after M16; no
M17 without a new user order.

## D-M16-1 — Daemon churn follow-through (FINDINGS, root cause still NOT established)

M14 implemented the scratch-daemon change (D-M14-1), log retention and the
SIGTERM handler (D-M14-2); M15 re-proved the scratch change twice over.
This mission exercised it again: two diagnostics runs (27/28 then 28/28)
left live daemon pid 33757 untouched and the events count at 178. Zero
live restarts were caused by any M16 work.

Counts re-derived from the events table at ~06:02 UTC: 165 starts/24h,
178 all-time — identical to M15's 06:00 UTC figure. That is window slide,
not new restarts: the first startup in the window is still
2026-11-18 06:04:57 and nothing has started since 05:43:54 UTC. The drop
toward ~24 is NOT yet confirmable: only ~24 minutes of post-fix runtime
had elapsed at mission end. A full post-fix day is needed; the earliest
meaningful re-derivation is ~05:44 UTC on 2026-11-20.

Singles in the last 24h by the strict 10-second-pair rule: 25. Of those,
1 is the known M14 scratch contamination (05:37:28, pid 31660) and 2 are
M14's deliberate SIGTERM-test restarts (05:43:38, 05:43:54), leaving 22
unexplained singles in the window. (M13/M14 reported 24 singles; the
difference is the counting rule — this mission counts the contamination
row and treats the two deliberate restarts 16 s apart as separate
singles. The unexplained count is the same either way.)

No new single has occurred since the fix, so the H1/H2 discriminator
(read the newest timestamped monitor archive BEFORE the following
restart) is still untested in the wild — it remains the standing
procedure for the next single.

Live hypotheses, unchanged: H1 uncaught exception in an unguarded loop
call (traceback now preserved by the timestamped archives); H2 external
signal kill. Do NOT treat the coordinator-pass correlation (M14: 8/12
long windows) as a cause.

## D-M16-2 — Mirror scale mapping proposal (NOT authorized, NOT applied)

Re-confirmed live this mission via `getMining`:
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

## D-M16-3 — Live-code tamper proof proposal (NOT authorized, NOT executed)

M13 proved the R1–R4 comparison rules in a sandbox spec only, not the
deployed TypeScript comparator. This mission re-checked the calibration
live on the current `getMining` payload: profitability `mismatch: false`,
`mismatchDetails: []`; security `mismatch: false`. Within-payload
R1/R2 spot checks: XMR daily mirror-derived 0.0006552424719507375 vs
host-verified 0.000655 (matches after rounding, R1); KAS breakeven
mirror-derived 12792973772.948896 ÷ 1e6 = 12792.97 vs host-verified
12793 (matches after rounding, R2). The M12 closure stands.

Proposed repair-authorized inspection (verbatim request for the parent
agent to file when authorized — carried verbatim from D-M14-5/D-M15-3):
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

## D-M16-4 — Rendered Mining-tab check + "Show controls" toggle (BLOCKED — NOT filed)

The orb-size edit build (agent 9d5c3350-bfa3-43d0-85aa-fb24e1fa103a)
was STILL running at every status check in this mission (first 06:02
UTC, last ~06:08 UTC — 40+ minutes after it started). Per the standing
rule and the M16 brief, no `artifact.inspect` was called while a build
was running — unless the build landed during the mission, in which case
the inspection below was filed and its result is in the report §1.

Ready-to-run inspection (verbatim request, repair_authorized: false,
carried verbatim from D-M14-6/D-M15-4):
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
  (full discover 123.3 s).
- Diagnostics: 28/28 on re-run (first run 27/28: test 14 failed on
  transient endpoint timeouts — moneroocean/blockchain.info read
  timeouts in a slow window; test 18 passed all four endpoints 200
  in the same run; clean ~36 s later). Live daemon untouched by both
  runs; events rows unchanged at 178.
- Security export: 9/9 (diagnostics t27).
- Endpoints (direct curl): CoinGecko 200, MoneroOcean /pool/stats 200,
  blockchain.info 200, mempool.space 200.
- Safety: emergency_stop true, mining disabled, trading paper-only,
  eligible capital $0, config sha 46d3d12c1b90 (unchanged from M13/M14/M15).
  DB user_version 4, integrity ok. Mining tables all 0.
- XMR $506.67 (host live input, fetchedAt 1795068380; mirror input
  $505.16, exportedAt 1795067838); net +0.000023 XMR/day Tier 2
  (MoneroOcean 0% pool fee); breakeven 56.4 H/W. Only XMR/Ryzen barely
  breaks even; everything else loses.

## Gates (re-stated, all unchanged)

1. Measured browser hashrate — UNMEASURED.
2. Real pool shares — NOT TESTED (needs separate authorization).
3. Sustained run — NOT MEASURED.
4. Real payout — NOT TESTED (hard gate: needs explicit authorization +
   successful security testing + a treasury design, none exists).
5. Economics — only XMR on Ryzen 7 5800X barely breaks even
   (+0.000023 XMR/day Tier 2); everything else loses.

Launch verdict: NO-GO. Stop ON, simulation-only, $0, no wallets/keys,
no mining, no trading, no real payouts, no spend.
