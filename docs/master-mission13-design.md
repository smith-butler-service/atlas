# ATLAS MASTER MISSION 13 — DESIGN

**Authorization:** User authorized by voice 2026-11-19 00:20 EST:
"do start the next mission." (Mission 12 STOP lifted by that order.)

**Mission report:** `docs/master-mission13-report-2026-11-18.md`
(this file's companion; design decisions D-M13-1–D-M13-6 below)

**Scope (from the task):** in priority order —
1. Rendered Mining-tab check (10th attempt) — run `artifact.inspect`
   (repair_authorized:false) once the S.M.I.T.H. rename build landed.
2. Post-repair profitability tamper regression — sandbox proof ONLY.
3. Mirror scale mapping gap — investigate, propose the mapping
   addition, do not edit the artifact.
4. Daemon churn root cause — investigate from logs/diagnostics.
5. Re-verify suites/diagnostics/security/endpoints/safety; re-state
   the five go/no-go gates.

## D-M13-1 — Rendered check: inspection run, NOT established (10th mission)

The rename build landed 2026-11-19 05:23 UTC (build
`28979037-5726-4328-b870-e5ac7eb25015`); inspection `de848332`
ran against it and returned a diagnosis (not a repair):
no captured audit ever selects the Mining tab in the current
S.M.I.T.H. build; the latest audit (05:19 UTC) loads on Overview
with 0 probe interactions; no screenshot at any width shows the
Security & Scale section or the Mission 10/11 scale figures.
Reload persistence fails BY DESIGN: tab state is in-memory
`useState("overview")` with no localStorage/URL persistence, so
a reload always returns to Overview. The clean console (0 errors)
and 0px mobile overflow in the bundle were measured on Overview
only and must never be presented as Mining-tab evidence.
Code and data are intact (section wired as 13th of 15 Mining
sections; `mining_security` row populated, 9/9 PASS, scale figures
live); an older Nov 18 mobile audit proves the Mining tab rendered
in the pre-rename build, but never the Security & Scale section.
**Binding:** the check stays open. The recommended targeted
check (select Mining on desktop 1440x900 + mobile 390x844,
screenshot the Security & Scale section, record console/overflow
with the tab open, then reload) is owed; if reload persistence of
the Mining tab is required, persist the selected tab
(localStorage or URL hash) — that change is NOT authorized by
this mission and is proposed, not executed. The builder-attested
"Show controls" toggle finding (full-size pill centered below the
animation on desktop, not a small transparent icon pinned right;
mobile places it right but at full pill size) was NOT covered by
this inspection and is carried as builder-attested, unverified.

## D-M13-2 — Tamper regression: CLOSED as a spec proof, live-code proof still owed

The calibrated comparator R1–R4 (M9 repair design) was replicated
in pure Python (`/tmp/m13_tamper_proof.py`, ephemeral) and run
against COPIES of the live `getMining` host/mirror figures
(export 1795065057). Baseline reproduces M12 exactly: 78 checked,
15 skipped (R3/R4), 0 residual diffs. Material tampers flag
`mismatch: true` with the field named (XMR daily +10%, KAS
breakeven 12458.4→13000, 1-ulp daily change, pool-fee +10%,
verdict flip, mirror-side gross ×1.5, and a 2e-9-above-floor
change). Known blind spots, all BY DESIGN in R1–R4: GPU
`currentHw`/`ratioTier2` tampers are invisible (R3 skip), a
mirror-side browser-split tamper while the host stays null is
invisible (R4 skip), and a host tamper within the 1e-9 tolerance
floor is invisible. One correction to the M12 framing: a HOST-side
browser-split tamper DOES flag, because the R4 skip is keyed on
the host value being null — once the host emits a value it is
compared. **Binding limitation:** this proves the R1–R4 rules AS
SPECIFIED, not the deployed TypeScript comparator itself. A
live-code proof still needs a repair-authorized inspection; it is
proposed, NOT executed, and NOT claimed here. The live mirror was
never tampered.

## D-M13-3 — Mirror scale mapping gap: mechanism established, repair proposed not applied

Host export (`data/security.json`) carries `workers_with_shares`
and `shares_per_worker` on every scale level (100/1000-worker
levels: 100/1000 and 100/100). The live `getMining` scale levels
carry exactly the 12 fields enumerated in the M10 lane report
§2.1 (label, workers, shares, sessions, sharesInserted,
dbSizeBytes, runPassS, recordSharesPerS, recordSharesTotalS,
attributionWeightsS, verifyChain10000S, slowestStep) — the two
M12 fields are absent from BOTH `scale.levels` and
`scale.l1.levels`, while `scale.l1.note` (host text) DOES mention
`workers_with_shares`, which is consistent with the stored
singleton payload holding the new fields verbatim (§3.3) and the
drop happening in the `getMining` / `server/src/security.ts`
projection. The stored payload itself cannot be verified from
the host; a repair-authorized inspection can confirm which layer
drops them. **Proposed addition (NOT authorized, NOT applied):**
add `workersWithShares` and `sharesPerWorker` (camelCase, null
preserved for the baseline level where the host is null) to the
scale-level projection in `scale.levels` AND `scale.l1.levels`,
and to the §2.1 field list; no schema change is needed if the
payload is stored verbatim — only the projection changes. No
artifact edit was made by this mission.

## D-M13-4 — Daemon churn: root cause NOT established; decomposition quantified

Last-24h `startup` events (DB, the source of the admin
restarts count): 164 at analysis time (168 by report time,
all-time 175 after this mission's own diagnostics run).
70 of the 94 daemon lifetimes end in a 2–3 s pair of starts —
the diagnostics suite's own tests 10/11 (SIGTERM kill + restart,
twice per run) — i.e. 140 of 164 starts (85%) are
diagnostics-designed kills. 24 starts are singles (15%) with no
paired kill; their preceding daemon lifetimes run 36 s–59 min
(median of all lifetimes 513 s, max 3,591 s — no daemon lived an
hour in 24 h). The hourly refresh job's diagnostics alone
accounts for ~24 runs/day (48 restarts); the remainder are
mission-agent and other diagnostics bursts (M11/M12 ran the suite
repeatedly; this mission's own run added one pair, and a second
`recover.sh` restart 25 s later suggests a concurrent diagnostics
run interleaving kills). No crash traceback survives anywhere:
`monitor.log` keeps one backup rotation, so any spontaneous
crash's output is already overwritten; the two rotations read
show clean START + cycles then a silent stop (signal kill, not
an in-loop exception). **Binding:** do NOT claim a crash cause,
an OOM kill, or a host-kill cause — none is evidenced. The
quantified decomposition above is the finding. A durable fix
would need either (a) diagnostics tests 10/11 to stop killing
the live daemon (run against a scratch daemon instead), or (b)
a longer monitor-log retention so a spontaneous death leaves a
trace — both are proposals, NOT authorized, NOT executed.

## D-M13-5 — No new schema, no config change

Mission 13 changes no schema (`user_version` stays 4), no config
(`atlas.json` / `pool-rewards.json` hashes unchanged:
`46d3d12c…` / `b01a22ad…`), no coordinator/rewards/dashboard/
security code. Only the report, this design file, the re-run
`data/diagnostics.json`, and the GOAL.md Mission 13 line change.
The tamper-proof script lives at `/tmp/m13_tamper_proof.py`
(ephemeral; its full output is reproduced in the report §2).

## D-M13-6 — Gates re-stated, not re-decided

Mission 13 does not authorize Gate 1 (browser hashrate probe),
Gate 2 (real pool shares), Gate 3 (sustained run), or Gate 4
(real payout / treasury). The launch verdict is re-stated from
measured evidence only; a NO-GO on any gate stays NO-GO. No
mining, trading, wallet, payout, spend, or subscription in this
mission. A NEW edit build on `atlas-command-center` (agent
`9d5c3350…`) was running at report time — this mission did not
start it, steer it, or interfere with it.
