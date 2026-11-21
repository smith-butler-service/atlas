# Master Mission 20 — Design

Date: 2026-11-19 (07:15–07:21 UTC). Auto-resumed per the user's 2026-11-19
01:22 EST auto-accept order (Mission 19 complete, auto-resume
authorized). Scope: rendered Mining-tab check (live-browser route via
parent); daemon-churn follow-through; M6 finding 1 re-test; re-verify
the five M19 fixes still hold; full re-verification. AUTO-RESUME:
Mission 21 starts automatically after this one (user order 01:22 EST).

## D-M20-1 — Rendered Mining-tab check NOT established (17th mission)

Inspection 7ea7bb34-88f5-44e2-9247-f5cc22bbcf84 (repair_authorized:
false) was filed for the Mining-tab check plus re-confirmation of the
five M19 fixes. Headline: the check was **not performed in the
captured evidence**. The latest audit (2026-11-19T07-09-12Z) renders
only the Overview tab at 1440x900 and 390x844, with Mining present but
unselected; no Mining-tab screenshot, no console/overflow measurement
with the tab open, and no reload capture exists. The security payload
itself states the honest null: "Rendered Mining-tab check — not
established by this mission". The audit's 0 console errors / 0 px
mobile overflow are Overview-only and cannot be claimed for Mining.

Reload behaviour is **code-determined, not live-observed**: `App.tsx`
keeps the tab only in `useState<Tab>("overview")` with `onClick`
`setTab` — no localStorage, sessionStorage, URL hash, or query-param
persistence for the tab anywhere in `App.tsx` (localStorage is used
only for mining resource-profile settings in `Mining.tsx`). A reload
therefore resets to Overview.

Binding decision: the check is carried to Mission 21 / the parent
agent as the TOP OPEN ITEM, to be run through the parent's live-browser
route (click Mining on desktop 1440x900 + mobile 390x844, screenshot
Security & Scale, console/overflow with the tab open, reload test).
Do NOT claim it established unless a captured run actually selects the
Mining tab. If the reload test confirms the reset and the user wants
persistence, add tab persistence (localStorage or URL hash) as a
separate ordered change — do not implement it unasked.

## D-M20-2 — Mission 19 fixes re-confirmed, with caveats

(a) **Show controls — CONFIRMED.** `Orb.tsx` renders a fixed 40x40px
(`h-10 w-10`) button, top-1/2, right `max(8px,
env(safe-area-inset-right))`, background transparent, border none, no
label text, aria-label "Show controls", sliders icon only; visible in
both desktop and mobile screenshots, not a centred pill. **New minor
finding:** on the mobile screenshot the fixed icon overlaps the
"Ring 2 — Mining" legend pill. The inspection notes this does not
violate the spec, but on short viewports the icon can sit on top of
page content while scrolling. Carried as a proposed nudge fix for
Mission 21; not dispatched this mission.

(b) **Mirror scale mapping — CONFIRMED in data.** From the isolated
mining_security row (exported_at 1795071659, synced_at 1795072189):
`scale.levels` and `scale.l1.levels` each have 3 levels, each carrying
exactly 14 fields; values baseline null/null, 100-worker 100/100,
1,000-worker 1000/100 in both arrays. The zod shape
`securityScaleLevelShape` in `actions.ts` declares both fields. Host
side independently re-confirmed: `data/security.json` levels carry the
same 14 fields (workers_with_shares [null, 100, 1000],
shares_per_worker [null, 100, 100]). **Caveat (new finding):** the
rendered Security & Scale table (`levelCells` in
`SecurityScaleStatus.tsx`) displays only 8 columns and does not render
workersWithShares/sharesPerWorker — the fields are present in the
data, hidden in the table. Carried as a proposed display change for
Mission 21; not dispatched this mission.

(c) **Live-code tamper proof — security derivable false; profitability
only spot-supported.** Security mismatch is derivable as false (all
host and mirror counts/totals are 0, non-derivable counts explicitly
null). Profitability: the stored payload has no mismatch field (it is
computed at getMining read time and no getMining response was
captured); one spot re-derivation matches (XMR Ryzen 10,000 H/s vs
network 6,569,017,756.925 H/s, 0.6 XMR x 720 blocks/day → 0.000658
XMR/day gross, Tier 2 net 0.000026 XMR/day after 171 W at 11.142
cents/kWh), and host diagnostics test 26 reports "81 figures
re-derived from recorded inputs within rounding; stale=False". A full
81-figure artifact-side check and a tampered-figure regression were
not re-run in this evidence. **Owed:** capture one live getMining
response and read profitability.mismatch / security.mismatch directly.

(d) **Refresh failure — mechanism confirmed in code; no live expiry
instance captured.** `server/src/actions.ts` defines
`REFRESH_TIMEOUT_MS = 5*60_000`; `getRefreshStatusFresh()` persists a
"started" refresh past the timeout to "failed" with message "Refresh
did not land — no newer snapshot was stored within 5 minutes. Stored
data is unchanged."; `storeSnapshotBundle` flips to "landed" only for
a NEW snapshot row with ts strictly greater than baselineTs, and
`App.tsx` mirrors the strict rule (`refreshLandedStrict`) and the
5-minute timeout text. The only stored refresh_status is state
"failed" from a spawn failure ("Refresh could not start: Web artifact
inference failed.", startedAt 1795072667833, baselineTs 1795072631,
landedTs null) — not a 5-minute expiry. The latest audit's live status
line shows the other branch: "Refresh finished without a newer
snapshot — still showing the snapshot from Nov 19, 07:07:09 AM."
(landed-not-strict). **Owed:** stage or wait out a started refresh
past 5 minutes to observe the stored record flip to failed.

(e) **Stale "no miner yet" copy — NOT FOUND in Mining.tsx.** Full
read of `client/src/Mining.tsx` (1,277 lines) finds no "no miner yet"
text; empty-worker copy now reads "No workers are registered. Worker
registration arrives with the coordinator (Master Mission 5)...".
Also absent from full reads of `ProfitabilityIntelligence.tsx` and
`SecurityScaleStatus.tsx` and from the Overview document-text.
**Caveat:** subcomponents Coordinator, RewardAccounting, UserDashboard,
AdminCommandCenter and MinerPrototype were only partially read, so a
rendered Mining-tab text search is still owed (it needs the Mining-tab
check from D-M20-1).

## D-M20-3 — Daemon churn follow-through (root cause still NOT established)

Live daemon pid 33757 alive 1h31m at mission start (started 05:43:53
UTC), well past the M13 median lifetime (513 s). Cycles normal,
snapshot age 24–51 s. Zero startups since 05:43:54 UTC; events total
still 178.
24h startup count re-derived at mission start: **162** — identical to
M19, no change at all (first in window still 2026-11-18 06:26:33 UTC,
ts 1794986793). The drop toward ~24 is NOT confirmable yet: only
~1.5 h of post-fix runtime had elapsed. Earliest meaningful
re-derivation is ~05:44 UTC on 2026-11-20 — ~22.4 h away at mission
end.
Singles in the last 24h by the strict 10-second-pair rule: **24** —
the same list as M19; 1 is the known M14 scratch contamination
(05:37:28, pid 31660) and 2 are M14's deliberate SIGTERM-test restarts
(05:43:38, 05:43:54), leaving **21 unexplained singles** (unchanged).
No new single since the fix, so the H1/H2 discriminator (read the
newest timestamped monitor archive BEFORE the following restart) is
still untested in the wild. The scratch-daemon change was exercised
again by this mission's diagnostics run: live pid 33757 untouched
(tests 10/11 scratch). Zero live restarts caused by any M20 work.
Live hypotheses, unchanged: H1 uncaught exception in an unguarded
loop call (traceback now preserved by the timestamped archives); H2
external signal kill.

## D-M20-4 — M6 finding 1 (reward display) — NOT re-tested, still open

M6 finding 1 (rendered reward section self-contradictory when the
ledger has rows) was in scope, but the ledger still has 0 entries, 0
settled batches, 0 shares, 0 payouts, so the defect is not currently
observable and was not re-tested this mission. It remains open: it can
only be verified once the ledger has rows (simulation settlement) or
by a targeted inspection with ledger rows present.

## D-M20-5 — New minor findings (proposed, NOT dispatched)

Two new findings from inspection 7ea7bb34, recorded as proposals for
Mission 21 / the parent agent — no repair was dispatched this mission
(the inspection report itself does not authorize repair; the
fix-any-issue rule covers defects found by this mission's checks, and
both items below are cosmetic/presentation, not functional defects):
1. Nudge the fixed Show-controls icon so it cannot overlap the orb
   legend on a 390px viewport (it overlaps the "Ring 2 — Mining"
   legend pill on mobile).
2. Surface workersWithShares/sharesPerWorker in the rendered scale
   table (the data carries them in all 14-field levels; the table
   shows only 8 columns).

## D-M20-6 — Re-verification (this mission)

- Suites: 77/77 — admin 5, coordinator 19, dashboard 4,
  profitability 11, security 18, reward_engine 20; all OK
  (`python3 -m unittest discover -s core -p "test_*.py"`, 79.6 s).
- Diagnostics: **28/28 on the first run** (no re-run needed). Live
  daemon untouched by the run (tests 10/11 scratch); events rows
  unchanged at 178. Test 26: XMR net 2.3e-05 XMR/day Tier 2,
  breakeven 56.5 H/W; 81 figures re-derived within rounding,
  stale=False. Test 27: security 9/9.
- Endpoints (direct curl): CoinGecko 200 (XMR $504.07), MoneroOcean
  /pool/stats 200, blockchain.info 200 (height 976548), mempool.space
  200 (height 976548).
- Safety: emergency_stop true, mining disabled, trading paper-only,
  eligible capital $0, config sha 46d3d12c1b90 (unchanged from
  M13–M19). DB user_version 4, integrity ok. Mining tables all 0
  (metrics 1684, decisions 603, events 178, pool_stats 75 at mission
  start).
- Live getMining: NOT captured this mission — the M19 post-repair live
  figures (mismatch false both, XMR $504.84) stand un-re-captured;
  host-side figures agree (XMR $504.07 live).
- XMR $504.07 at mission end (CoinGecko). Only XMR/Ryzen barely
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

## Carried to Mission 21 (auto-resume authorized 01:22 EST)

- **TOP OPEN ITEM (parent agent): rendered Mining-tab check** — still
  NOT established (17th mission). Needs a live-browser run through the
  parent's browser route; do not claim established without a captured
  run that selects the Mining tab.
- Capture one live getMining response; read profitability.mismatch and
  security.mismatch directly.
- Stage or wait out a started refresh past 5 minutes to observe the
  stored record flip to "failed".
- Full-text search of the Mining-tab subcomponents for "no miner yet"
  (needs the Mining-tab render).
- Proposed (not dispatched): nudge the Show-controls icon off the orb
  legend on 390px; surface workersWithShares/sharesPerWorker in the
  rendered scale table.
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
  mission with the caveats in D-M20-2): Show-controls toggle, mirror
  scale mapping, live-code tamper proof, refresh failure, stale "no
  miner yet" copy.
