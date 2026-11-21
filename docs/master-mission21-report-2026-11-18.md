# ATLAS Master Mission 21 — Report

Date: 2026-11-19 (07:22–07:45 UTC; 02:22–02:45 EST). Auto-resumed per the user's 2026-11-19
01:22 EST auto-accept order (Mission 20 complete, auto-resume authorized).
Design: `docs/master-mission21-design.md` (binding decisions D-M21-1
to D-M21-8).

**Verdict: NO-GO — not ready to launch.** Gates 1–4 unmeasured/untested;
Gate 5 only XMR/Ryzen barely breaks even (+0.000026 XMR/day Tier 2,
MoneroOcean, XMR $504.72 in the captured live getMining; host
diagnostics test 26 gave 1.9e-05 at its run — same verdict). Stop ON,
simulation-only, $0, configs unchanged (sha `46d3d12c1b90`), no
mining/trading/wallets/payouts/spend.

## 1. Rendered Mining-tab check — NOT established (18th mission)

Inspection 8e031703-bdf1-42f5-a401-edfab74a0c66 (repair_authorized:
false) was filed for the Mining-tab check, the subcomponent text
search, and re-confirmation of the two M20 minor findings. Its
headline: **the check was not performed in the captured evidence.**
The latest audit (2026-11-19T07-09-12Z) renders only the Overview tab
at 1440x900 and 390x844, Mining present but unselected; the 06-31-48Z,
05-01-31Z and 04-43-05Z audits checked likewise all show Overview
[selected]. No Mining-tab screenshot, no console/overflow measurement
with the tab open, no reload capture exists in the evidence bundle.
The live mining_security payload itself states the honest null:
"Rendered Mining-tab check — not established by this mission".

What the inspection did establish about the tab:
- **Reload behaviour — code-determined reset, not live-observed.**
  Full read of App.tsx (1,052 lines): tab state is
  `const [tab, setTab] = useState<Tab>("overview")` with
  `onClick={() => setTab(t.id)}` and no localStorage, sessionStorage,
  or URL-param persistence for the selected tab. A reload is therefore
  expected to return to Overview. No rendered reload capture exists.
- **Console/overflow with Mining open — NOT captured.** The audit's
  0 console errors / 0 px mobile overflow are Overview-only
  (console_warnings are only THREE.Clock deprecation x2 and
  software-WebGL fallback deprecation x2). They cannot be claimed for
  the Mining tab, which mounts different components.

**Top open item for the parent agent (unchanged):** the rendered
Mining-tab check needs a live-browser run — click Mining on desktop
1440x900 and mobile 390x844, screenshot Security & Scale, capture
console/overflow with the tab open, reload test. A subagent cannot run
a live browser. Do NOT claim it established unless a captured run
actually selects the Mining tab. If the reload test confirms the
reset and the user wants persistence, add tab persistence as a
separate ordered change — do not implement it unasked.

## 2. Live getMining captured — mismatch false, all three

One live `getmining` response was captured this mission (via the
artifact's own action, ~07:24 UTC) — the item M20 left owed:
- **profitability.mismatch: false**, mismatchDetails: []
- **security.mismatch: false**, mismatchDetails: []
- **admin mismatch: false**, mismatchDetails: []
- XMR price $504.72 (CoinGecko input, fetchedAt 1795071655, stale
  false); XMR network hashrate 6,569,017,756.925 H/s; MoneroOcean
  pool hashrate 285,506,839 H/s, miners 4,967, height 3,809,591.
- Pool fees: MoneroOcean 0% net 0.000026 XMR/day Tier 2, SupportXMR
  0.6% net 0.000022, P2Pool 0% net 0.000026.
- Scale data re-confirmed in the live payload: `scale.levels` and
  `scale.l1.levels` each carry workersWithShares / sharesPerWorker
  (baseline null/null, 100-worker 100/100, 1,000-worker 1000/100).
- Admin network block: daemonRestarts24h 162 (as captured ~07:24
  UTC, before the new single in section 5), daemonRestartsAllTime
  178, hashrate not-measured, all share/worker/ledger counts 0.
- Security honestNulls still include verbatim: "Rendered Mining-tab
  check — not established by this mission".

## 3. Refresh failure — landed branch proven live; expiry branch still not live-observed

Staged deliberately this mission. Sequence (all UTC):
- 07:24:11 — `refreshatlasdata` landed snapshot 07:24:11.
- 07:25:11 — second call landed snapshot 07:25:11 (calls straddled
  a daemon cycle; no stuck record).
- 07:26:37 — two parallel calls both landed the same snapshot
  07:26:11 (concurrent calls read the same pre-landing baseline, so
  both land — parallel staging does not work).
- 07:28:00 — fresh snapshot written (ts 1795073280).
- 07:28:3x — `refreshatlasdata` landed 07:28:00; an immediate
  second call returned **"Refresh started — this page confirms here
  as soon as the new snapshot lands."**
- Stored record confirmed via getdashboard: state **"started"**,
  baselineTs 1795073280, landedTs null, startedAt 1795073317623
  (07:28:37 UTC).
- 07:29:15 — the record **landed**: state "landed", baselineTs
  1795073280, landedTs 1795073355, startedAt preserved. The daemon's
  next snapshot (07:29:15) landed it 38 seconds after staging.

What this proves, and what it does not:
- **Proven live:** a duplicate refresh sits in "started" only until
  the next daemon snapshot lands it (~38 s here). The strict
  landed-only-on-newer-snapshot rule and the background mirror sync
  both work as designed.
- **Not proven live:** the 5-minute expiry to "failed". The expiry
  branch can only fire if no newer snapshot is ingested for 5
  minutes — i.e. during a host outage — because the background sync
  lands every started refresh within ~60 s whenever the host is
  healthy. It was not staged by breaking the live host reader
  (that would disrupt monitoring; the fix-any-issue authorization
  does not cover it). The expiry mechanism remains code-verified
  only (M19/M20: `REFRESH_TIMEOUT_MS = 5*60_000`,
  `getRefreshStatusFresh()` persists started >5 min to "failed").
  The live-expiry observation is carried as "only observable during
  a host outage; do not stage one by breaking the host".

Two staging-helper subagents (spawned to fire the action
simultaneously) both failed before acting: the `artifact` namespace
is not loadable in their sessions ("no deferred namespaces matched").
They took no other action. The staging was done directly instead.

## 4. "no miner yet" — ABSENT everywhere; text search CLOSED

Inspection 8e031703 read in full: Coordinator.tsx (552 lines),
RewardAccounting.tsx (434), UserDashboard.tsx (692),
AdminCommandCenter.tsx (820) and MinerPrototype.tsx (443). The exact
phrase **"no miner yet" occurs in none of them**. Nearest verbatim
wordings: Coordinator — "No workers registered yet. The coordinator
is running in simulation only — there is nothing to coordinate." and
"No coordinator pass has run yet"; RewardAccounting — "No reward
entries yet — simulation only, 0 workers, 0 shares.";
UserDashboard — "No mining activity yet. The dashboard is running in
simulation only — there is nothing to show but honest zeros." and "No
workers registered yet."; AdminCommandCenter — "No users yet", "No
workers yet", "No shares yet", "No payouts yet"; MinerPrototype —
"No measurement yet — the prototype has not been run." Combined with
M20's full Mining.tsx read, the phrase is now confirmed absent from
the whole Mining-tab surface. **This item is CLOSED — do not
re-propose it.** (Preservation note from the inspection: the honest
zero wording must stay untouched; the absent phrase must not be
inserted as a fix — there is no defect there.)

## 5. Daemon churn — H1 RULED OUT, H2 CONFIRMED as mechanism, sender unknown

**The first new daemon single since the M14 fix, and the H1/H2
discriminator fired.** At 07:26:56 UTC the live daemon pid 33757
received SIGTERM and exited; recover.sh restarted it at 07:27:58 UTC
as pid 890. New startup event id 179 (ts 1795073278). Watchdog
07:28:44: "FIXED daemon pid 33757 died SIGTERM 07:26:56Z, restarted
pid 890, snapshot ts 1795073280 age 33s".

The discriminator evidence — the newest timestamped monitor archive
`logs/monitor-20261119-072758.log` (pid 33757's full lifetime,
05:43:54–07:26:56 UTC) — ends:
```
2026-11-19T07:26:11Z cycle ts=1795073171 cpu=49.92 mem=82.11 db=ok stop=True
2026-11-19T07:26:56Z monitor STOP SIGTERM received, exiting
```
- **H1 (uncaught exception) is RULED OUT for this single:** the M14
  SIGTERM handler fired and logged a clean stop line; there is no
  traceback, and cycles were normal right up to the signal.
- **H2 (external signal kill) is CONFIRMED as the mechanism:** the
  daemon was killed by a SIGTERM sent from outside itself.
- **The sender is NOT established.** What is ruled out: the
  watchdog / recover.sh did not kill it (recover.log shows only
  no-op lines until the 07:27:58 restart); the coordinator did not
  (passes at 07:20:52 and 07:30:55, not at 07:26:56 — the M14
  coordinator correlation does not explain this single); the M21
  diagnostics run did not (tests 10/11 scratch, live pid verified
  untouched, run finished ~07:24); no M21 exec command sends
  signals (reads, sleeps, greps only); no M21 artifact action sends
  signals. The SIGTERM arrived at 07:26:56, inside the window when
  the M21 inspection and refresh staging were running — correlation
  only, no mechanism. OOM is not the cause (OOM sends SIGKILL, not
  SIGTERM; exec resource reports show oomKills 0).
- **Lifetime record:** pid 33757 lived 1h43m02s (05:43:54–07:26:56
  UTC) — the longest daemon lifetime since the M14 fix, well past
  the M13 median (513 s).
- **New daemon:** pid 890 started 07:27:58, cycles normal
  (07:28:15, 07:29:16 … 07:43:20), snapshot age 42.6 s at 07:44:01,
  events total 179, metrics 1712, decisions 624, pool_stats 77.
- **24h count:** NOT re-derived this mission. One new startup
  (07:27:58) since M20's 162, but the earliest meaningful
  re-derivation of the drop toward ~24 is still ~05:44 UTC
  2026-11-20 (~22 h away at mission end). Do not present a
  re-derived count as the drop verdict before then.
- The M14 retention + SIGTERM-handler fix worked exactly as
  designed: without it this death would have been another silent
  unexplained single; instead the cause class is now known.

## 6. Two M20 minor findings — CONFIRMED, repairs BLOCKED at dispatch

Inspection 8e031703 re-confirmed both:
- **(a) Show-controls icon overlap at 390px — CONFIRMED visually.**
  In the latest mobile screenshot (390px, 2x DPR) the sliders icon
  sits on the right end of the "Ring 2 — Mining" legend pill,
  covering its final letters ("Ring 2 — Mi[icon]ng"). The audit
  harness itself listed clipped: [] and unreachable_controls: [] —
  it did not flag this overlap.
- **(b) Security & Scale table hides the two fields — CONFIRMED.**
  `SecurityScaleStatus.tsx` renders the Load-levels DataTable with
  exactly 8 heads (Level, Workers, Shares, DB size, run_pass,
  Shares/s, record_shares total, Slowest step) and `levelCells()`
  returns 8 cells; neither workersWithShares nor sharesPerWorker is
  rendered, although the scale payload carries them (100/100 and
  1000/100; baseline null/null).
- **Extra finding (new, from the same inspection):** in the
  06-31-48Z mobile capture the floating orb label pills ("Mining",
  "Account") overlap the ORBS legend row ("Centre — …",
  "Ring 1 — Researc…") on the narrow viewport.

**Repairs attempted and BLOCKED — none applied, none claimed
fixed.** Three repair-authorized inspections were filed (one per
defect: icon overlap, table columns, label-pill overlap). All three
first calls timed out at dispatch (180 s, nothing registered —
`artifact.status` confirmed no build running). Retries then failed
deterministically with: "failed to start edit builder for web
artifact 'atlas-command-center': subagent bootstrap is no longer
authorized. The edit was not started." Three consecutive identical
failures across two different repair requests — the block is
systemic to this session, not request-specific. No ordinary
`artifact.edit` was used for repair (forbidden by the standing
artifact-ownership rule). **Carried to Mission 22: re-file the
three repair inspections (presumably from a fresh session / the
parent route); the defects are confirmed and the repair
authorization (user order 01:22 EST) still stands.**

## 7. M6 finding 1 reward display — NOT re-tested (ledger still 0 rows)

Ledger still 0 entries, 0 settled batches, 0 shares, 0 payouts
(live getMining: ledger [], rewards totals all 0; host diagnostics
test 23: verify_chain PASS, 0 entries). The defect is not currently
observable. Still open; re-test once the ledger has rows.

## 8. Re-verification

- Suites **77/77** (78.3 s): admin 5, coordinator 19, dashboard 4,
  profitability 11, security 18, reward_engine 20.
- Diagnostics **28/28 on the first run**. Test 26: XMR net 1.9e-05
  XMR/day Tier 2, breakeven 56.8 H/W; 81 figures re-derived within
  rounding, stale=False. Test 27: security 9/9. Tests 10/11:
  scratch daemon only, live pid 33757 untouched (at run time).
- Security export: **9/9**.
- Endpoints **4/4 200** (diagnostics test 18, direct): CoinGecko
  200 (XMR $504.72 in mirror; $504.07–$504.84 across the mission
  window), MoneroOcean /pool/stats 200, blockchain.info 200
  (height 976548), mempool.space 200 (height 976548). Note: the
  dashboard still stores mempool.space as "unreachable-from-this-
  host" (stale label — decision owed, unchanged).
- DB v4 integrity ok, mining tables all 0 (metrics 1712, decisions
  624, events 179, pool_stats 77 at mission end).
- Safety: emergency_stop true, mining disabled, trading paper-only,
  eligible capital $0, config sha `46d3d12c1b90` (unchanged from
  M13–M20). No code/config edits by the mission agent itself.
- Five M19 fixes re-confirmed where observable: Show-controls toggle
  (40px transparent right-pinned icon — with the 390px overlap
  caveat in section 6); mirror scale mapping (14 fields/level in
  live getMining — with the table-hiding caveat); live-code tamper
  proof (now with a captured live getMining: mismatch false on all
  three blocks); refresh failure (landed branch proven live, expiry
  branch still code-only); stale "no miner yet" copy (text search
  now CLOSED).

## 9. Gates (re-stated)

1. Measured browser hashrate — UNMEASURED.
2. Real pool shares — NOT TESTED (needs separate authorization).
3. Sustained run — NOT MEASURED.
4. Real payout — NOT TESTED (hard gate: explicit authorization +
   successful security testing + a treasury design, none exists).
5. Economics — only XMR on Ryzen 7 5800X barely breaks even
   (+0.000026 XMR/day Tier 2 MoneroOcean, XMR $504.72); everything
   else loses.

**Launch verdict: NO-GO.** Stop ON, simulation-only, $0, no
wallets/keys, no mining, no trading, no real payouts, no spend.

## 10. Open / owed (for Mission 22 — auto-resume authorized)

- **TOP OPEN ITEM (parent agent): rendered Mining-tab check** —
  still NOT established (18th mission). Needs the live-browser run.
- **Re-file the three repair inspections** (icon overlap at 390px;
  scale-table columns; orb label-pill overlap) — dispatch was
  blocked this session ("subagent bootstrap is no longer
  authorized"); defects confirmed, repair authorization stands.
- **Daemon SIGTERM sender:** H1 ruled out, H2 confirmed as
  mechanism for the 07:26:56 UTC single; the sender is unknown.
  Watch for a repeat; if another SIGTERM single occurs, check the
  same archive line first and look for a sender (audit harness,
  watchdog, platform) with timestamps.
- Daemon 24h startup count: re-derive after a full post-fix day
  (earliest ~05:44 UTC 2026-11-20); on the next single, read the
  newest timestamped monitor archive BEFORE the following restart
  (H1/H2 discriminator — now proven to work).
- Live refresh-expiry observation: only observable during a host
  outage; do not stage one by breaking the host.
- M6 finding 1: re-test once the ledger has rows.
- Carried decisions owed unchanged: MEM% alert re-scope,
  mempool.space label, Obj 2 coordinator, SupportXMR URL, referral
  5%, minimum payout, Gates 2/4, roadmap/GOAL.md bookkeeping,
  recovery.md corrections, RVN difficulty, refresh step-9 transform,
  tariff fetchedAt schema.
- Fixed and CLOSED in M19 (do not re-propose): Show-controls toggle,
  mirror scale mapping, live-code tamper proof, refresh failure,
  stale "no miner yet" copy — the last of these is now closed as a
  text search too (section 4).

**AUTO-RESUME: Mission 22 starts automatically after this one per
the user's 01:22 EST order.**
