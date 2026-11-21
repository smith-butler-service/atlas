# ATLAS Master Mission 20 — Report

Date: 2026-11-19 (07:15–07:21 UTC). Auto-resumed per the user's 2026-11-19
01:22 EST auto-accept order (Mission 19 complete, auto-resume authorized).
Design: `docs/master-mission20-design.md` (binding decisions D-M20-1
to D-M20-6).

**Verdict: NO-GO — not ready to launch.** Gates 1–4 unmeasured/untested;
Gate 5 only XMR/Ryzen barely breaks even (+0.000023 XMR/day Tier 2,
XMR $504.07). Stop ON, simulation-only, $0, configs unchanged (sha
`46d3d12c1b90`), no mining/trading/wallets/payouts/spend.

## 1. Rendered Mining-tab check — NOT established (17th mission)

Inspection 7ea7bb34-88f5-44e2-9247-f5cc22bbcf84 (repair_authorized: false)
was filed for the Mining-tab check plus re-confirmation of the five
Mission 19 fixes. Its headline finding: **the rendered Mining-tab check
was not performed in the captured evidence.** The latest audit
(2026-11-19T07-09-12Z) renders only the Overview tab at 1440x900 and
390x844, with Mining present but unselected; no Mining-tab screenshot,
no console/overflow measurement with the tab open, and no reload
capture exists in the evidence bundle. The security payload itself
states the honest null: "Rendered Mining-tab check — not established
by this mission".

What the inspection did establish about the tab:
- **Reload behaviour — code-determined reset.** `App.tsx` keeps the tab
  only in `useState<Tab>("overview")` with `onClick` `setTab` — no
  localStorage, sessionStorage, URL hash, or query-param persistence
  for the tab anywhere in `App.tsx` (localStorage is used only for
  mining resource-profile settings in `Mining.tsx`). A reload therefore
  resets to Overview. No rendered reload capture exists, so this is
  code-determined, not live-observed.
- **Console/overflow with Mining open — NOT captured.** The audit's
  0 console errors / 0 px mobile overflow are Overview-only and cannot
  be claimed for the Mining tab.

**Top open item for the parent agent:** the rendered Mining-tab check
needs a live-browser run — click Mining on desktop 1440x900 and mobile
390x844, screenshot the Security & Scale section with the tab open,
record console errors and horizontal overflow with the tab open, reload
with Mining selected and record which tab is selected after reload. A
subagent cannot run a live browser. If the reload test confirms the
reset to Overview and the user wants persistence, add tab persistence
(localStorage or URL hash) as a separate ordered change — do not
implement it unasked.

## 2. Mission 19 fixes — re-confirmed, with caveats

**(a) "Show controls" toggle — CONFIRMED.** `Orb.tsx` renders the
toggle as a fixed 40x40px (`h-10 w-10`) button, top-1/2, right
`max(8px, env(safe-area-inset-right))`, background transparent, border
none, no label text, aria-label "Show controls", sliders icon only.
Desktop (1440x900) and mobile (390x844) screenshots show the small
sliders icon pinned to the right edge mid-height. Not a centred pill.
**New minor finding:** in the mobile screenshot the fixed icon overlaps
the "Ring 2 — Mining" legend pill. The inspection notes this does not
violate the 40px/transparent/right-edge spec, but on short viewports
the icon can sit on top of page content while scrolling. Carried to
Mission 21 as a proposed nudge fix, not dispatched this mission.

**(b) Mirror scale mapping — CONFIRMED in data.** From the isolated
mining_security row (exported_at 1795071659, synced_at 1795072189):
`scale.levels` and `scale.l1.levels` each have 3 levels, each level
carrying exactly 14 fields (label, workers, workersWithShares,
sharesPerWorker, shares, sessions, sharesInserted, dbSizeBytes,
runPassS, recordSharesPerS, recordSharesTotalS, attributionWeightsS,
verifyChain10000S, slowestStep). Values match the spec exactly in both
arrays: baseline workers 0, workersWithShares null, sharesPerWorker
null; 100-worker level 100/100; 1,000-worker level 1000/100. The
server zod shape `securityScaleLevelShape` in `actions.ts` declares
both fields. Host side re-confirmed independently this mission:
`data/security.json` levels carry the same 14 fields with
workers_with_shares [null, 100, 1000] and shares_per_worker
[null, 100, 100]. **Caveat (new finding):** the rendered Security &
Scale table (`levelCells` in `SecurityScaleStatus.tsx`) displays only
8 columns and does not render workersWithShares/sharesPerWorker — the
fields are present in the data, hidden in the table. Carried to
Mission 21 as a proposed display change, not dispatched this mission.

**(c) Live-code tamper proof — security derivable false; profitability
only spot-supported.** Security: host counts are all 0
(suspicious/invalid/duplicate/abuse/auth failures/payout anomalies 0)
and mirror-derived totals are all 0 (ledger 0 rows, workers 0, shares
0, reward batches 0), with the three non-derivable counts explicitly
null — never a mismatch, and no "Mirror mismatch" text can arise from
these values. Profitability: the stored payload has no mismatch field
(it is computed at getMining read time and no getMining response was
captured); one spot re-derivation matches (XMR Ryzen 10,000 H/s vs
network 6,569,017,756.925 H/s, 0.6 XMR x 720 blocks/day gives 0.000658
XMR/day gross, Tier 2 net 0.000026 XMR/day after 171 W at 11.142
cents/kWh), and host diagnostics test 26 reports "81 figures
re-derived from recorded inputs within rounding; stale=False". A full
81-figure artifact-side check and a tampered-figure regression were
not re-run in this evidence. **Owed:** capture one live getMining
response and read profitability.mismatch / security.mismatch directly.

**(d) Refresh failure — mechanism confirmed in code; no live expiry
instance captured.** `server/src/actions.ts` defines
`REFRESH_TIMEOUT_MS = 5*60_000` and `getRefreshStatusFresh()` persists
a "started" refresh past the timeout to "failed" with message "Refresh
did not land — no newer snapshot was stored within 5 minutes. Stored
data is unchanged."; `storeSnapshotBundle` flips to "landed" only for
a NEW snapshot row with ts strictly greater than baselineTs, and
`App.tsx` mirrors the strict rule (`refreshLandedStrict`) and the
5-minute timeout text. The only stored refresh_status in the isolated
DB is state "failed", startedAt 1795072667833, baselineTs 1795072631,
landedTs null, message "Refresh could not start: Web artifact
inference failed." — a spawn failure, not a 5-minute expiry. The
latest audit's live status line shows the other branch: "Refresh
finished without a newer snapshot — still showing the snapshot from
Nov 19, 07:07:09 AM." (landed-not-strict). **Owed:** stage (or wait
out) a started refresh past 5 minutes to observe the stored record
flip to failed.

**(e) Stale "no miner yet" copy — NOT FOUND in Mining.tsx.** A full
read of `client/src/Mining.tsx` (1,277 lines) finds no "no miner yet"
text. The empty-worker copy now reads "No workers are registered.
Worker registration arrives with the coordinator (Master Mission
5)..."; other empty states read "No mining sessions recorded", "No
reward entries", "No payouts exist". The phrase was also absent from
full reads of `ProfitabilityIntelligence.tsx` and
`SecurityScaleStatus.tsx` and from the Overview document-text.
**Caveat:** subcomponents Coordinator, RewardAccounting, UserDashboard,
AdminCommandCenter and MinerPrototype were only partially read, so a
rendered Mining-tab text search is still owed (it needs the Mining-tab
check from section 1).

## 3. Daemon churn — noise gone, drop NOT yet measurable, cause NOT established

- Live daemon pid 33757 alive 1h31m at mission start (started 05:43:53
  UTC), well past the M13 median lifetime (513 s). Cycles normal,
  snapshot age 24–51 s. Zero startups since 05:43:54 UTC; events
  total still 178.
- 24h startup count re-derived at mission start: **162** — identical
  to M19, no change at all (first in window still 2026-11-18 06:26:33
  UTC, ts 1794986793). The drop toward ~24 is NOT confirmable yet:
  only ~1.5 h of post-fix runtime had elapsed. Earliest meaningful
  re-derivation is ~05:44 UTC on 2026-11-20 — ~22.4 h away at mission
  end.
- Singles in the last 24h by the strict 10-second-pair rule: **24** —
  the same list as M19; of those, 1 is the known M14 scratch
  contamination (05:37:28, pid 31660) and 2 are M14's deliberate
  SIGTERM-test restarts (05:43:38, 05:43:54), leaving **21 unexplained
  singles** (unchanged).
- No new single since the fix, so the H1/H2 discriminator (read the
  newest timestamped monitor archive BEFORE the following restart)
  is still untested in the wild. The scratch-daemon change was
  exercised again by this mission's diagnostics run: live pid 33757
  untouched (tests 10/11 scratch). Zero live restarts caused by any
  M20 work.

## 4. M6 finding 1 reward display — NOT re-tested (ledger still 0 rows)

M6 finding 1 (rendered reward section self-contradictory when the
ledger has rows) was in scope, but the ledger still has 0 entries, 0
settled batches, 0 shares, 0 payouts, so the defect is not currently
observable and was not re-tested this mission. It remains open; it can
only be verified once the ledger has rows (simulation settlement) or
by a targeted inspection with ledger rows present.

## 5. Re-verification

- Suites **77/77** (79.6 s): admin 5, coordinator 19, dashboard 4,
  profitability 11, security 18, reward_engine 20.
- Diagnostics **28/28 on the first run** (no re-run needed). Test 26:
  XMR net 2.3e-05 XMR/day Tier 2, breakeven 56.5 H/W; 81 figures
  re-derived within rounding, stale=False. Test 27: security 9/9.
- Security export: **9/9**.
- Endpoints **4/4 200** (direct curl): CoinGecko 200 (XMR $504.07),
  MoneroOcean /pool/stats 200, blockchain.info 200 (height 976548),
  mempool.space 200 (height 976548).
- DB v4 integrity ok, mining tables all 0 (metrics 1684, decisions
  603, events 178, pool_stats 75 at mission start; 1686 metrics during
  diagnostics).
- Safety: emergency_stop true, mining disabled, trading paper-only,
  eligible capital $0, config sha `46d3d12c1b90` (unchanged from
  M13–M19).
- Live getMining: NOT captured this mission (see section 2c) — the
  M19 post-repair live figures (mismatch false both, XMR $504.84)
  stand un-re-captured; host-side figures agree (XMR $504.07 live).

## 6. Gates (re-stated)

1. Measured browser hashrate — UNMEASURED.
2. Real pool shares — NOT TESTED (needs separate authorization).
3. Sustained run — NOT MEASURED.
4. Real payout — NOT TESTED (hard gate: explicit authorization +
   successful security testing + a treasury design, none exists).
5. Economics — only XMR on Ryzen 7 5800X barely breaks even
   (+0.000023 XMR/day Tier 2); everything else loses.

**Launch verdict: NO-GO.** Stop ON, simulation-only, $0, no
wallets/keys, no mining, no trading, no real payouts, no spend.

## 7. Open / owed (for Mission 21 — auto-resume authorized)

- **TOP OPEN ITEM (parent agent): rendered Mining-tab check** — still
  NOT established (17th mission). Needs a live-browser run: click
  Mining on desktop 1440x900 + mobile 390x844, screenshot Security &
  Scale, capture console/overflow with the tab open, reload test.
  A subagent cannot run a live browser. If the reload test confirms
  the tab resets to Overview (code-determined, `useState("overview")`)
  and the user wants persistence, add tab persistence explicitly in
  a separate ordered change.
- Capture one live getMining response; read profitability.mismatch
  and security.mismatch directly (M19's tamper proof stands, but the
  live booleans were not re-captured this mission).
- Stage or wait out a started refresh past 5 minutes to observe the
  stored record flip to "failed" (live expiry instance still owed).
- Full-text search of the Mining-tab subcomponents (Coordinator,
  RewardAccounting, UserDashboard, AdminCommandCenter,
  MinerPrototype) for "no miner yet" — needs the Mining-tab render.
- New minor findings (proposed, not dispatched): nudge the fixed
  Show-controls icon so it cannot overlap the orb legend on a 390px
  viewport; surface workersWithShares/sharesPerWorker in the
  rendered scale table (data carries them, table hides them).
- Daemon 24h startup count: re-derive after a full post-fix day
  (earliest ~05:44 UTC 2026-11-20); on the next single, read the
  newest timestamped monitor archive BEFORE the following restart
  (H1/H2 discriminator).
- M6 finding 1 reward display: re-test once the ledger has rows.
- Carried decisions owed unchanged: MEM% alert re-scope,
  mempool.space label, Obj 2 coordinator, SupportXMR URL, referral
  5%, minimum payout, Gates 2/4, roadmap/GOAL.md bookkeeping,
  recovery.md corrections, RVN difficulty, refresh step-9 transform,
  tariff fetchedAt schema.
- Fixed and CLOSED in M19 (do not re-propose; re-confirmed this
  mission with the caveats in section 2): Show-controls toggle,
  mirror scale mapping, live-code tamper proof, refresh failure,
  stale "no miner yet" copy.

**AUTO-RESUME: Mission 21 starts automatically after this one per
the user's 01:22 EST order.**
