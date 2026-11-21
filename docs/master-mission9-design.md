# ATLAS — Master Mission 9: Profitability Intelligence — Design

**Mission:** Master Mission 9 — Profitability intelligence
**Date:** Wednesday, 2026-11-18
**Author:** Lane A (design — coordinator)
**Status:** DESIGN ONLY. No code, no migration, no config change, no database write,
no artifact change was made by this lane. This document is the binding contract for
the build lane.
**Scope:** Profitability intelligence IN SIMULATION, built on the Mission 2 Obj 4
mining-intelligence model and the Mission 4 Gate 5 cost accounting, and on the
coordinator (Mission 5), reward engine (Mission 6), user dashboard (Mission 7),
and admin command center (Mission 8) outputs. There are no real earnings, no
workers, no shares, no sessions: 0 users, 0 workers, 0 shares, 0 ledger rows.
Every profitability figure is an ESTIMATE computed from stated inputs — a
projection, never a measurement, never a payable balance, never a promise of
profit. Realized mining revenue remains **$0**.

## 0. Grounding — what this design rests on

Read before writing this design (all under `~/workspace/atlas/`):

- Mission 1 inspection report (`docs/master-mission1-inspection-report-2026-11-18.md`)
  §4 (browser hashrate measured 200–850 H/s; RandomX browser verdict IMPRACTICAL
  as an earner), §6 (accounting basis: confirmed pool rewards only, integer
  piconero, attribution by verified accepted shares), §8 Mission 9 row:
  "Profitability intelligence" (the mission this design serves).
- Infrastructure Mission 2 Obj 4 (`docs/mission2-obj4-findings.md`) — the
  comparative mining model: formula, electricity rates, pool fees, reference
  hardware, and the per-coin results. All Obj 4 figures used here are labelled
  CARRIED and are re-derived by the host module from the same formula, not
  copied as literals.
- Master Mission 4 cost accounting (`docs/master-mission4-cost-accounting.md`)
  — Gate 5: breakeven efficiency **56.5 H/s per wall watt at Hydro-Québec
  Tier 2** (125.2 H/W at the US average); the 75/25 split effect on the user's
  net position; the wall-watt measurement protocol (a physical measurement is
  OWED, none exists).
- Mission 7 design (`docs/master-mission7-design.md`) and Mission 8 design
  (`docs/master-mission8-design.md`) — design conventions carried here: host DB
  is system of record, artifact is a read-only display mirror (D-M7-1/D-M8-1);
  integer piconero, never floats (D-M7-2/3 pattern); balances derived by `SUM`,
  never stored; simulation marking everywhere (M6 §8); no new cron, ride the
  existing pass; placement directly below the previous section, no new tab;
  estimated vs confirmed hard rule (M7 §3, M8 §3); STALE rules (M8 §6);
  MIRROR-MISMATCH rule (M7 §6, M8 §7); zero buttons/inputs/links/forms in the
  section; verbatim headings/labels/empty-state copy; provenance tags
  (RECORDED / DERIVED host / DERIVED mirror / ESTIMATE / UNAVAILABLE).
- Mission 8 report (`docs/master-mission8-report-2026-11-18.md`), Unresolved
  findings 1–22 — carried, NOT fixed by this design (see §9). Finding 1 (the
  rendered Mining-tab check never established — now the fifth consecutive
  mission with this gap) and finding 8 (Mission 6 finding 1 latent — hardcoded
  zero literals in `RewardAccounting.tsx`) are the two this design is built to
  not repeat: the profitability section must be designed so that class of
  defect cannot recur silently (§7).

**Safety state (unchanged):** emergency_stop true, mining disabled, trading
paper-only, eligible capital $0. No wallets, keys, or seed material. No real
payouts, no pool connection for earning, no share submission to any pool, no
mining activation, no spending. Gate 4 (a real payout) is a hard gate requiring
explicit authorization + successful security testing + a treasury design — none
exists.

**Baseline facts (verified by the coordinator just before this design was written,
read-only):**

- Live host DB (`data/atlas.db`): `user_version` 3, `integrity_check` ok;
  metrics 1337, decisions 363, events 120, pool_stats 55; users 0, workers 0,
  shares 0, sessions 0, ledger 0, reward_batches 0, payouts 0, referrals 0.
- Live host exports (all fresh at check time): `data/coordinator.json`,
  `data/rewards.json`, `data/dashboard.json`, `data/admin.json` all
  `exported_at` 1795053653; `data/diagnostics.json` 1795053189;
  `data/snapshot.json` ts 1795053898. Emergency stop true in the snapshot.
- Config (`config/atlas.json`): emergency_stop true, mining enabled false
  (design-only), trading paper-only, eligible capital $0, limits max_cpu_pct 50,
  max_mem_pct 70 (immutable without user authorization).
- Pool config (`config/pool-rewards.json`): mode `simulation-only`; primary
  MoneroOcean 0% fee (`/pool/stats`); fallbacks SupportXMR 0.6% (60 bps),
  P2Pool 0%; split 75/25 on confirmed pool rewards only; referral funded from
  the ATLAS 25% only; minimum payout null (placeholder, undecided).
- Artifact (`atlas-command-center`, build `d5e7be84`, Mission 8): Mining tab
  order MiningDashboard, WalletCenter, EarningsSection, HistorySections,
  PayoutSection, CalculatorSection, MinerPrototypeSection, CoordinatorSection,
  RewardAccounting, UserDashboard, AdminCommandCenter, SettingsSection,
  HelpSection. The new **Profitability intelligence** section goes directly
  BELOW AdminCommandCenter, above Settings.

**Labelling convention.** Every figure in this document carries one of four
labels, following the Mission 1 / Mission 4 / Mission 5 / Obj 4 discipline:

- **VERIFIED** — measured or confirmed against a live source, the live host, or an
  official document cited here, in this session.
- **CARRIED** — taken from Mission 1, Obj 4, or Mission 4, not re-verified in
  this session. Never presented as fresh.
- **ESTIMATE** — computed from the formula (shown) or an assumption with its
  source stated; a projection, never a measurement, never a payable balance.
- **ASSUMPTION** — a design choice or an unconfirmed property; the build/test lanes
  must verify it before relying on it.

No figure in this document is a promise of earnings. Realized mining revenue
remains **$0**.

## Decisions (binding on the build lane)

| # | Decision |
|---|---|
| D-M9-1 | Host is the system of record; artifact tables are a read-only display mirror (M5 D1, M6 D-M6-1, M7 D-M7-1, M8 D-M8-1 carried). Profitability figures are DERIVED by the host module from live inputs + carried constants at export time — no new stored truth. **No new host DB tables.** One new host export, `data/profitability.json` (atomic write, §1). One new artifact mirror singleton row (migration 0009, M7 migration-0007 pattern — scalars only, no log tables needed). |
| D-M9-2 | Estimated vs confirmed (M7 §3, M8 §3, binding, carried verbatim): every profitability figure is an ESTIMATE. Confirmed earnings = ledger `SUM`, SIMULATION-tagged while mode is `simulation-only`, and the profitability section REUSES the dashboard export's earnings block by import (never recomputes it) — the profitability section must never show a different confirmed-earnings number than the user dashboard or the admin section. Estimate and confirmed are never combined into one total. |
| D-M9-3 | **No fiat in the panel.** Electricity rates are shown as ¢/kWh INPUTS (they are tariff inputs, not earnings figures). All daily figures are shown in XMR/day to 6 decimal places: gross XMR/day, net XMR/day, user/ATLAS shares XMR/day. Non-XMR coins are compared in XMR/day by converting their projected gross at the live price — the conversion is labelled ESTIMATE and exists only for the comparison; it is never applied to confirmed earnings and never shown as a balance. USD intermediates exist only inside the host export for audit (with provenance) and are never rendered in the panel. Breakeven is shown as H/s per wall watt and as ¢/kWh, never as a dollar figure. |
| D-M9-4 | **Live inputs with source + fetched_at per input, fetch-with-fallback.** At export time the host module fetches: XMR network difficulty/height/block value from MoneroOcean `/network/stats` (port 18081; `/api/stats` 404s — never use it) and XMR price from CoinGecko `simple/price`; KAS/RVN/ERG network stats from the 2Miners `api/stats` endpoints and their prices from the same CoinGecko call; USD/CAD from CoinGecko `exchange_rates`. Each input is recorded with its value, source, and `fetched_at`. Fetch timeout is short (10 s per endpoint); on any failure the module uses the last recorded inputs for that coin and marks that coin STALE with the last-fetch time — never silently fresh, never a guessed input. Electricity rates are tariff constants (HQ Tier 1 7.065¢ CAD/kWh, Tier 2 11.142¢ CAD/kWh, US average 17.23¢ USD/kWh), recorded with source + effective date, re-verified only on a schedule, not per export. |
| D-M9-5 | **Reference profiles only.** The comparison uses exactly the Obj 4 / M4 reference profiles: CPU Ryzen 7 5800X (10,000 H/s @ 171 W wall) for XMR; GPU RTX 3060 Ti for KAS (480 MH/s @ 150 W), RVN (27 MH/s @ 240 W), ERG (137 MH/s @ 132 W); browser workers from M4 (laptop 200 H/s @ 45 W, desktop 850 H/s @ 50 W) for XMR. Hashrate and wall watts are labelled ASSUMPTION (published benchmarks / estimate ranges, not measurements). No other hardware profile is introduced. The user's own hardware estimate is NULL while Gate 1 is unmeasured, with the verbatim reason "Cannot estimate — hashrate not measured" (M7 §3). |
| D-M9-6 | **Breakeven definitions (binding).** Per coin and per rate: breakeven efficiency (H/s per wall watt) = (electricity $/day per wall watt) ÷ (gross $/day per H/s); breakeven electricity price (¢/kWh) = gross $/day ÷ kWh/day. Distance-to-breakeven = current profile H/W ÷ gate H/W, shown as a ratio with the verbatim verdict `Above breakeven` / `Below breakeven` at the stated inputs. No threshold, flag, or `degraded` inference is drawn beyond the arithmetic verdict. |
| D-M9-7 | **Electricity sensitivity (binding).** Net/day is shown at HQ Tier 1, HQ Tier 2, and the US average for every coin/profile. The pending 19.5¢ CAD/kWh Quebec blockchain tariff appears ONLY as a labelled RISK SCENARIO row ("Proposed tariff — not in effect"), never inside any base-case figure. |
| D-M9-8 | **Pool-fee comparison (binding).** XMR net is shown under MoneroOcean 0%, SupportXMR 0.6%, and P2Pool 0% (fee applied to projected gross coins only). KAS/RVN/ERG use 2Miners 1% (Obj 4, CARRIED). Each fee is disclosed beside its figure. Fees apply only to confirmed rewards in the reward engine (M6) — in this panel they apply to the projected gross, labelled ESTIMATE. |
| D-M9-9 | **75/25 split projection (binding).** For each coin at Tier 2 (the base case): user share = 0.75 × gross, ATLAS share = 0.25 × gross, user net position = 0.75 × gross − electricity — all in XMR/day, all ESTIMATE, all under the verbatim note "Projection only — not earnings". The split projection is what the split WOULD be if the projected gross were realized; it is never an earning, never a balance, never added to confirmed earnings. |
| D-M9-10 | **STALE rules (binding, M8 §6 pattern).** The profitability section is STALE when any live input (price or network stats for any coin) is > 1 h old, measured from that input's `fetched_at` to now; the STALE tag names the stale input (`STALE — KAS network stats 73 min old`). "Not computed yet" when a coin has never been computed. A re-ingest of unchanged data reports "already up to date" and does NOT advance `syncedAt` (Mission 3 finding 1, carried). |
| D-M9-11 | **MIRROR-MISMATCH rule (binding, M7 §6 / M8 §7 carried).** On every render, the artifact compares the mirror's figures against the host-verified figures carried in the mirrored profitability export. On any disagreement it shows the HOST-VERIFIED figures plus the verbatim note "Mirror mismatch — figures under investigation", and NEVER silently presents mirror figures as real. **No hardcoded figure literal is permitted anywhere in the profitability section.** A panel whose value is a literal in the component source is a defect, full stop — the build lane's grep check (§10) enforces this. Agreement on today's figures says nothing about the check working — the build lane must test the check with non-zero fixture data on a temp/sandbox mirror, not with zeros alone. |
| D-M9-12 | Placement: a new "Profitability intelligence" section in the Mining tab, directly BELOW the Admin command center section; the existing Mining tab section order is otherwise unchanged; NO new tab; zero buttons, inputs, links, or forms in the profitability section; Start/Stop stay hard-disabled and untouched. |
| D-M9-13 | No token, session token, or password hash is ever mirrored or displayed. No new cron. The profitability export rides the existing coordinator pass as a guarded sub-step (never fails the pass, logs no decision of its own) — same pattern as M6/M7/M8. Every figure carries its provenance (host export vs mirror derivation) — see the data-flow table in §2. A figure with no provenance is a defect, not a display choice. This design does NOT repair any carried issue (§9). |

---

## 1. Data rules — derived only; no new host tables

**No new host tables.** Every profitability figure is derivable from live
inputs fetched at export time plus carried constants, plus one new host export:

| Profitability need | Source |
|---|---|
| XMR network (difficulty, height, block value) | MoneroOcean `/network/stats` (live, per D-M9-4) |
| KAS/RVN/ERG network (hashrate, difficulty, block reward) | 2Miners `api/stats` per coin (live, per D-M9-4) |
| Prices (XMR, KAS, RVN, ERG) + USD/CAD | CoinGecko `simple/price` + `exchange_rates` (live, per D-M9-4) |
| Electricity rates | Tariff constants, recorded with source + effective date (D-M9-4) |
| Pool fees | `config/pool-rewards.json` (XMR pools) + Obj 4 CARRIED 2Miners 1% (D-M9-8) |
| Reference hardware profiles | Obj 4 / M4 CARRIED profiles (D-M9-5) |
| Confirmed earnings (for the reuse rule, never recomputed) | `data/dashboard.json` earnings block by import (D-M9-2) |
| Mode / emergency stop | `config/atlas.json` + `data/snapshot.json` |

**One new host export (derived, not stored).** `data/profitability.json`,
written atomically (temp + `os.replace`) by the new host module
`core/atlas_profitability.py` (stdlib-only), from the sources above at export
time. The export carries: the inputs block (every input with value, source,
`fetched_at`); the per-coin comparison (daily coins native, gross XMR/day,
net XMR/day at Tier 1 / Tier 2 / US avg, verdict); the breakeven block (gate
H/W and breakeven ¢/kWh per coin per rate, current profile H/W, ratio,
verdict); the sensitivity block (net XMR/day at all three rates + the risk
scenario); the pool-fee block (XMR net under the three XMR pools); the split
projection (user share, ATLAS share, user net position per coin at Tier 2);
the your-hardware block (null + verbatim reason while Gate 1 is unmeasured);
and the confirmed-earnings block reused verbatim from the dashboard export.
No new column, no new table, no stored aggregate — every value is recomputed
on every export. The artifact cross-checks it against its own mirrored row
(§7).

**Formula (binding, Obj 4 §1 / M4 §3 — the module implements exactly this):**

```
daily coins  = (your hashrate / network hashrate) × blocks/day × block reward × (1 − pool fee)
gross $/day  = daily coins × price (USD)
electricity $/day = wall watts × 24 / 1000 × price per kWh (USD)
net $/day    = gross − electricity
net XMR/day  = net $/day ÷ XMR price (USD)          [panel unit, D-M9-3]
gross XMR/day (non-XMR coin) = gross $/day ÷ XMR price (USD)   [comparison only, ESTIMATE]
breakeven H/W = (electricity $/day per wall watt) ÷ (gross $/day per H/s)
breakeven ¢/kWh = gross $/day ÷ kWh/day × 100
user share XMR/day = 0.75 × gross XMR/day
user net XMR/day = 0.75 × gross XMR/day − electricity $/day ÷ XMR price
```

Money inside the module is computed in USD (electricity is priced in USD)
and converted to XMR/day only at the final rendering step, at the live XMR
price recorded in the inputs block. The USD intermediates are carried in the
export under `audit_usd` with provenance, never rendered in the panel.

**What is NOT a source.** Pool-wide stats (`pool_stats`: pool hashrate, miner
count, block height) are context only, never profitability inputs for ATLAS's
own figures — the pool's total hashrate says nothing about ATLAS's share of a
reward (M6 §1.2). The Mining tab calculator's output never enters the
profitability section. Local-test shares (`origin='local-test'`) never enter
any profitability figure (they are diagnostics). `workers.reported_hashrate_hps`
is an agent self-report only; it is never a measured hashrate and never feeds
any estimate (M8 §1). `config/atlas.json` endpoint status strings
(`blockchain_apis`) are recorded claims, not live measurements — the section
shows live-fetch outcomes only, never the config strings as measurements.

---

## 2. Data flow and provenance

```
Host (system of record)                              Artifact (display mirror)
─────────────────────────                            ─────────────────────────
Live inputs (fetched at export time,                  drizzle mining_* tables
  with source + fetched_at)                            (mirror of host export,
  MoneroOcean /network/stats                            singleton row,
  2Miners api/stats (KAS/RVN/ERG)                      deduped on export,
  CoinGecko prices + USD/CAD                           re-ingest = "already
        │                                               up to date")
        │ coordinator pass (10-min)                             ▲
        │  guarded profitability sub-step                      │ ingestProfitabilityState
        │  (never fails pass, no decision)                     │ (existing action,
        ▼                                                       │  extended)
data/profitability.json ──► refreshAtlasData ───────────────────┘
data/dashboard.json (earnings block reused)            getMining reads
data/coordinator.json + data/admin.json                 mirror tables only
data/diagnostics.json                                   + profitability block
```

Provenance tags follow the existing tab pattern:

- **RECORDED** — a value read from a live fetch or a host export (with
  `fetched_at` / `exported_at`).
- **DERIVED (host)** — computed by the host module from its inputs at export
  time (every profitability figure).
- **DERIVED (mirror)** — computed by the artifact from the mirrored row (used
  only for the §7 comparison).
- **ESTIMATE** — every profitability figure, additionally (a projection from
  stated inputs; never a measurement).
- **UNAVAILABLE** — the source has no value (null), shown as such, never as 0.

**Figure-by-figure provenance (normative):**

| Profitability figure | Host source | Mirror derivation | Provenance tag shown |
|---|---|---|---|
| Daily coins / gross / net per coin | live inputs + carried constants (§1 formula) | read through the mirrored singleton row | DERIVED (host) + ESTIMATE |
| Breakeven H/W, breakeven ¢/kWh, ratio, verdict | §1 formula from the same inputs | read through | DERIVED (host) + ESTIMATE |
| Sensitivity nets (Tier 1 / Tier 2 / US avg + risk scenario) | §1 formula at each rate | read through | DERIVED (host) + ESTIMATE |
| Pool-fee comparison | §1 formula at each XMR pool fee | read through | DERIVED (host) + ESTIMATE |
| Split projection (user / ATLAS / user net) | §1 formula + 75/25 rule | read through | DERIVED (host) + ESTIMATE |
| Your-hardware estimate | Gate 1 unmeasured → null | read through | UNAVAILABLE (verbatim reason) |
| Confirmed earnings (reuse) | `data/dashboard.json` earnings block by import | none (read through) | DERIVED (host), SIMULATION-tagged |
| Input values (price, difficulty, rates, fees) | live fetch / tariff constant / config | read through | RECORDED (with source + fetched_at) |
| Last sync time | artifact mirror `syncedAt` | none — this IS the mirror state | RECORDED (mirror time) |

---

## 3. Estimated vs confirmed — the hard rule (M7 §3, M8 §3, carried verbatim)

**Estimated figures (D-M9-2, binding).** Every profitability figure is an
ESTIMATE: computed from live inputs and carried constants with the formula in
§1, labelled ESTIMATE, and shown with the verbatim note (once, in the section
header):

> `All figures are estimates from live inputs and stated assumptions — not earnings, not a promise of profit.`

The estimate is never derived from pool-wide hashrate as ATLAS's share, never
a guessed number, never a benchmark figure presented as a measurement, never
back-filled from `workers.reported_hashrate_hps`. The estimate is never added
to a confirmed figure or a balance. **The profitability section reuses the
dashboard export's earnings block by import** — it does not recompute
confirmed earnings, balances, lifetime, or payouts. If the profitability
section and the user dashboard ever disagree on a confirmed-earnings figure,
that is a mismatch (§7), not two views.

**Confirmed earnings (D-M9-2, binding).** Confirmed earnings = ledger `SUM`
over `user_allocation` + `referral_reward` entries (M6 §5.1 sign convention),
SIMULATION-tagged while mode is `simulation-only`. Today: 0 entries →
`0.000000 XMR`. Confirmed earnings come only from settled reward batches. A
simulated figure is never shown without the SIMULATION tag, and the word
"earned" never appears next to a simulated figure without that qualifier
(M6 §8).

**Your-hardware estimate (D-M9-5, binding).** With Gate 1 unmeasured (no probe
hashrate exists anywhere — `coordinator.json` `hashrate.measured_hps` is null)
and 0 shares, NO user-hardware estimate is computable. The field is **null**,
and the panel shows the verbatim reason:

> `Cannot estimate — hashrate not measured`

---

## 4. Reference profiles and carried results (D-M9-5)

The comparison uses exactly these profiles (CARRIED from Obj 4 / M4; the
build lane re-derives the results from the live inputs, it does not copy the
CARRIED results as literals):

| Profile | Coin | Algo | Hashrate | Wall W | H/W |
|---|---|---|---|---|---|
| Ryzen 7 5800X (native) | XMR | RandomX | 10,000 H/s | 171 | 58.5 |
| RTX 3060 Ti | KAS | kHeavyHash | 480 MH/s | 150 | — |
| RTX 3060 Ti | RVN | KawPow | 27 MH/s | 240 | — |
| RTX 3060 Ti | ERG | Autolykos v2 | 137 MH/s | 132 | — |
| Laptop browser | XMR | RandomX | 200 H/s | 45 | 4.4 |
| Desktop browser | XMR | RandomX | 850 H/s | 50 | 17.0 |

CARRIED Obj 4 results at the Obj 4 inputs (for the test lane's regression
check — the module must reproduce these within rounding when fed the Obj 4
inputs): XMR net/day QC T2 +$0.021, T1 +$0.138, US −$0.367; KAS −$0.280 /
−$0.178 / −$0.620; RVN −$0.349 / −$0.185 / −$0.893; ERG −$0.142 / −$0.052 /
−$0.442. Breakeven electricity price (CARRIED): XMR 8.29¢, KAS ~0.00¢,
RVN 1.73¢, ERG 3.29¢. M4 gates (CARRIED): **56.5 H/W at HQ Tier 2**,
125.2 H/W at the US average (XMR); $0.03302/day per kH/s at the M4 inputs.

---

## 5. Breakeven analysis (D-M9-6, binding)

Per coin and per rate (Tier 2 base case + US average; Tier 1 as the optimistic
bound):

- **Breakeven efficiency (H/W):** the hashrate-per-wall-watt at which net = 0.
  A profile above its gate is `Above breakeven`; below it, `Below breakeven`.
  The M4 gate (56.5 H/W at Tier 2) is the XMR reference point; the module
  computes the gate per coin from the live inputs and must reproduce 56.5 H/W
  (within rounding) when fed the M4 inputs.
- **Breakeven electricity price (¢/kWh):** the rate at which the profile's net
  = 0. A profile whose breakeven price is below the rate being paid loses
  money at that rate.
- **Distance-to-breakeven:** ratio (current profile H/W ÷ gate H/W) + the
  verbatim verdict. The ratio is a pure number, never a percentage of profit.

---

## 6. Electricity sensitivity and pool fees (D-M9-7, D-M9-8, binding)

**Sensitivity:** for every coin/profile, net XMR/day at HQ Tier 1 (7.065¢ CAD),
HQ Tier 2 (11.142¢ CAD), and the US average (17.23¢ USD). The pending 19.5¢
CAD/kWh Quebec blockchain tariff appears only as a RISK SCENARIO row with the
verbatim label `Proposed tariff — not in effect`, never inside a base-case
figure.

**Pool fees:** XMR net XMR/day under MoneroOcean 0%, SupportXMR 0.6%, P2Pool
0% — the fee is applied to the projected gross coins only, and each figure
carries its fee beside it (e.g. `SupportXMR 0.6%`). KAS/RVN/ERG carry the
verbatim note `2Miners 1% fee applied` (Obj 4, CARRIED). The fee comparison
never implies a fee is charged on an estimate — fees in the reward engine
apply only to confirmed rewards (M6); here they shape the projection.

---

## 7. MIRROR-MISMATCH rule (D-M9-11, binding — the Mission 6 lesson, carried)

**The rule.** On every render, the artifact compares the mirror's figures
against the host-verified figures carried in the mirrored profitability export
(the same comparison shape as M7 §6 / M8 §7: every numeric figure in the
export, plus the inputs block). On any disagreement:

1. The profitability section shows the **HOST-VERIFIED figures** (from the
   export), not the mirror-derived ones.
2. The section shows the visible verbatim note, in the section header area,
   next to the affected figures:

> `Mirror mismatch — figures under investigation`

3. The mirror row is still listed but labelled as a mirror row under
   investigation — never silently presented as real.
4. The mismatch is logged (artifact-side, in the same honest-failure pattern
   as the refresh flow: surfaced, not swallowed).

**General-case requirement (binding).** The mismatch rule is written for the
general case, not today's figures. The profitability section's figures are
therefore always derived from the export (host-verified first, mirror-derived
for comparison), never hardcoded literals. **No hardcoded figure literal is
permitted anywhere in the profitability section.** Agreement on today's
figures says nothing about the check working — the build lane must test the
check with non-zero fixture data on a temp/sandbox mirror, not with the live
figures alone.

---

## 8. UI spec — Profitability intelligence section in the Mining tab (exact, build-ready)

### 8.1 Placement and rules

- **Location:** inside the existing Mining tab (`client/src/Mining.tsx`,
  artifact `atlas-command-center`). **NO new tab.** The section sits
  **directly below the "Admin command center" section** and above Settings.
  It does not reorder, restyle, or reword any existing section. Current tab
  order, unchanged (M8 §8.1, carried): MiningDashboard, WalletCenter,
  EarningsSection, HistorySections, PayoutSection, CalculatorSection,
  MinerPrototypeSection, CoordinatorSection, RewardAccountingSection,
  UserDashboardSection, AdminCommandCenterSection,
  **[ProfitabilityIntelligenceSection]**, SettingsSection, HelpSection.
- **Component:** new `client/src/ProfitabilityIntelligence.tsx` (export
  `ProfitabilityIntelligenceSection`, taking the same `m` prop shape as
  `AdminCommandCenterSection` — the `getMining` result). Data comes from the
  extended `getMining` action (`profitability` block, §1–§2) reading the
  artifact `mining_profitability` mirror singleton row only. React Query
  refetch: same 30 s cadence as the rest of the Mining tab. No new refresh
  schedule.
- **Estimate note (verbatim, D-M9-2):** directly under the section heading:

> `All figures are estimates from live inputs and stated assumptions — not earnings, not a promise of profit.`

- **Provenance:** every figure carries a RECORDED / DERIVED (host) / ESTIMATE /
  UNAVAILABLE tag plus a SIMULATION tag while mode is `simulation-only`,
  following the existing tab pattern. Nothing is labelled live unless it was
  measured in the current probe/session.
- **Zero controls.** There is no button, input, link, or form anywhere in this
  section: no "recalculate", no "refresh now", no rate input, no hardware
  picker, no settings control. The existing Start/Stop buttons in the Mining
  dashboard stay **hard-disabled with no handler** (Missions 2/4/5/6/7/8) and
  are untouched by this section.
- **Copy that must NOT appear in this section:** any wallet address, token
  hash, session token, password hash, or credential; any per-user identifier
  or row; any hashrate number presented as ATLAS's without a `MEASURED` tag
  and a measurement time; the words "verified", "confirmed", or a checkmark
  next to any worker, address, or hashrate that has only passed format checks
  or self-report; the word "secure" as a verdict; "There is no miner yet"
  (stale copy, Mission 4 finding 4 — carried, §9); any earnings, balance, or
  payout figure derived from shares or hashrate; any USD/fiat figure; any
  combined "total earnings" mixing estimated and confirmed figures; any
  guaranteed-profit wording ("guaranteed", "will earn", "profit" without the
  ESTIMATE tag and the §3 note).
- **Responsive / accessibility (binding, M5 §7.4 carried):** tables/cards
  collapse to stacked cards below ~640 px; no horizontal page overflow at
  390 px (mobile overflow 0); all status text is text, not colour alone
  (a screen reader must hear `Above breakeven` / `Below breakeven` /
  `not measured` / `STALE`, not just a colour).

### 8.2 Panels (verbatim headings, labels, empty states)

**Panel group 1 — Coin comparison** (base case: HQ Tier 2; every figure
ESTIMATE, XMR/day to 6 decimals)

| Panel | Heading (verbatim) | Fields (verbatim labels) | Empty state (verbatim) |
|---|---|---|---|
| 1a | `Profitability — coin comparison` | Per coin: `Coin`; `Reference hardware`; `Hashrate`; `Wall watts`; `Daily coins` (native units, 6 decimals); `Gross XMR/day`; `Net XMR/day (HQ Tier 2)`; `Verdict` (`Above breakeven` / `Below breakeven`) | A coin with no live inputs: `Not computed yet` for that row, with the STALE tag naming the missing input |

**Panel group 2 — Breakeven** (per coin; Tier 2 base case + US average)

| Panel | Heading (verbatim) | Fields (verbatim labels) | Empty state (verbatim) |
|---|---|---|---|
| 2a | `Profitability — breakeven` | Per coin: `Breakeven H/W (HQ Tier 2)`; `Breakeven H/W (US avg)`; `Current H/W`; `Distance to breakeven` (ratio); `Breakeven electricity price (¢/kWh)`; `Verdict` | A coin with no live inputs: `Not computed yet` |

**Panel group 3 — Electricity sensitivity** (net XMR/day per coin/profile)

| Panel | Heading (verbatim) | Fields (verbatim labels) | Empty state (verbatim) |
|---|---|---|---|
| 3a | `Profitability — electricity sensitivity` | Per coin: `Net XMR/day (HQ Tier 1)`; `Net XMR/day (HQ Tier 2)`; `Net XMR/day (US avg)`; `Net XMR/day (proposed tariff)` | Risk-scenario row label (verbatim): `Proposed tariff — not in effect` |

**Panel group 4 — Pool fees** (XMR under the three XMR pools; other coins noted)

| Panel | Heading (verbatim) | Fields (verbatim labels) | Empty state (verbatim) |
|---|---|---|---|
| 4a | `Profitability — pool fees` | Per XMR pool: `Pool`; `Fee`; `Net XMR/day (HQ Tier 2)` | KAS/RVN/ERG note (verbatim): `2Miners 1% fee applied` |

**Panel group 5 — Split projection** (per coin at Tier 2; ESTIMATE, XMR/day)

| Panel | Heading (verbatim) | Fields (verbatim labels) | Empty state (verbatim) |
|---|---|---|---|
| 5a | `Profitability — 75/25 split projection` | Per coin: `User share (75%)`; `ATLAS share (25%)`; `User net position` | Projection note (verbatim): `Projection only — not earnings` |

**Panel group 6 — Your hardware** (null while Gate 1 is unmeasured)

| Panel | Heading (verbatim) | Fields (verbatim labels) | Empty state (verbatim) |
|---|---|---|---|
| 6a | `Profitability — your hardware` | `Measured hashrate`; `Measured wall watts`; `Net XMR/day` | All three: `Cannot estimate — hashrate not measured` |

**Panel group 7 — Inputs and last sync** (provenance for every input)

| Panel | Heading (verbatim) | Fields |
|---|---|---|
| 7a | `Profitability — inputs` | Every input: value, source, `fetched_at` + age; STALE tag naming any stale input (§6 rules) |
| 7b | `Profitability — last sync` | Profitability `syncedAt` + age + tag; coordinator `syncedAt` + age + tag. STALE naming which source is stale. |

---

## 9. Carried issues — NOT fixed by this design (D-M9-12)

1. **Rendered Mining-tab check NOT established** (M7 finding 1, still owed —
   now the fifth consecutive mission with this gap). No captured render ever
   selects the Mining tab on build `d5e7be84`. A repair-authorized Mining-tab
   render capture (select Mining, capture desktop + mobile, console, overflow,
   then reload + re-select Mining) is owed.
2. **Gate 1 still unmeasured** — every hashrate reads "not measured". A fresh
   interactive probe run is owed.
3. **Refresh failure carried** (Mission 3 finding 1, NOT fixed). The
   profitability section labels stale inputs rather than presenting them as
   fresh, but a failed refresh still stalls the mirror.
4. **Stale "no miner yet" copy carried** (Mission 4 finding 4, NOT fixed) —
   exactly two strings in `Mining.tsx`. Repair needs a repair-authorized
   inspection.
5. **Mission 6 finding 1 is latent, not repaired.** The hardcoded zero literals
   in `RewardAccounting.tsx` are still there. The profitability mismatch rule
   detects the shape but the underlying display defect is NOT fixed — repair
   still needs a repair-authorized inspection. It does not bite today: the
   live mirror and live host totals are both 0.
6. **Duration secondary check wiring not independently verified** (M7 finding 6).
   Dormant at 0 sessions; verify the population path before any session exists.
7. **Panel 1 "0 users" wording tension (minor, source-level, M7 finding 7):**
   the dashboard counts distinct user_ids on mirrored ledger entries (0), while
   `mining_users` holds 1 scaffold row (`local-user`, no wallet). Unchanged.
8. **"Derived host" tag wording (minor, M7 finding 8):** when mismatch is false
   the confirmed-figure tag reads "Derived host"; it may confuse. Unchanged.
9. **SupportXMR fallback not implemented** (D-M5-3, carried) — no verified
   stats-API URL; a URL must never be guessed. (The pool-fee panel uses the
   fee from `config/pool-rewards.json` only; no SupportXMR stats fetch is
   attempted.)
10. **Referral rate 5% is a design parameter to confirm** before any real-mode
    settlement (engine defaults to 500 bps; `referral_rate_bps` absent from
    `pool-rewards.json`).
11. **Minimum payout still null/placeholder** — undecided, needed before any
    payout flow.
12. **D-M5-1 (carried):** browser-probe `session_token_hash` stores marker
    `none:browser-probe` instead of NULL. Confirmed in code; no live row to
    inspect (sessions 0).
13. **Host memory above the 70% cap** (standing, pre-existing; 87–93% across
    the day). Re-scope proposal still needs user approval.
14. **mempool.space disputed, not settled.** 000 (timeout) on some attempts,
    200 on others. Flappy. (Not a profitability input; listed because the
    diagnostics endpoint tests still cover it.)
15. **Daemon restarts of undetermined cause** (carried). Watchdog restarts
    continue. Single instance maintained; not a stop condition.
16. **DB file growth, partly unexplained (carried).** The pre-Mission 2 jump
    (36,864 → 163,840 B) remains unexplained at page level.
17. **Diagnostics sensitivity:** the suite is sensitive to endpoint flapping;
    a 23/25 with only tests 14/18 failing is the known stall signature, not a
    regression. Test count grows 25 → 26 in this mission (new test 26, §10).
18. **KAS/RVN/ERG live inputs depend on third-party APIs (2Miners, CoinGecko)**
    that the host has not polled in this mission's baseline yet — if any is
    unreachable from this host, that coin's figures are STALE by rule (D-M9-4),
    never fabricated. The baseline lane reports reachability.

---

## 10. Verification requirements (binding on the build/test lanes)

- **Host module tests** (`core/test_atlas_profitability.py`, temp DBs / fixture
  inputs only): (a) formula regression — fed the Obj 4 inputs, the module
  reproduces the Obj 4 net/day figures for all four coins at all three rates
  within rounding (XMR +$0.021 / +$0.138 / −$0.367; KAS, RVN, ERG as §4);
  (b) breakeven regression — fed the M4 inputs, the XMR gate reproduces
  56.5 H/W at Tier 2 and 125.2 H/W at the US average within rounding, and
  $0.03302/day per kH/s; (c) fee comparison — SupportXMR 0.6% reduces XMR
  gross by exactly 0.6% vs MoneroOcean 0%; P2Pool 0% equals MoneroOcean;
  (d) sensitivity — the US-average rate flips the XMR reference profile
  negative while Tier 2 stays positive (at Obj 4 inputs); (e) stale-input
  handling — an input older than 1 h flags its coin STALE and the export
  carries the last-fetch time, never a fresh timestamp; a failed fetch never
  raises and never fabricates an input; (f) your-hardware null — with Gate 1
  unmeasured the block is null with the verbatim reason; (g) read-only proof
  — all table counts and the decisions table unchanged across status+export,
  the module logs no decision; (h) export idempotence + atomic write (temp +
  `os.replace`, no partial file on failure); (i) `run_pass` sub-step on a temp
  DB — all exports written, exactly +1 decision per pass
  (`coordinator-pass-complete`), profitability export fresh.
- **Diagnostics test 26** ("profitability export": file parses, `exported_at`
  fresh, inputs block present with source + `fetched_at` per input, every
  figure re-derives from the recorded inputs by the §1 formula within
  rounding, your-hardware block null + verbatim reason, confirmed-earnings
  block identical to a fresh `dashboard.json` earnings block, no USD figure
  in the panel payload — USD lives only under `audit_usd`). Suite must be
  26/26.
- **Mismatch proofs (sandbox, not zeros alone):** (a) profitability mismatch —
  mirror figures disagreeing with host export figures returns
  `mismatch: true` with the disagreeing fields named and the displayed figures
  switched to host-verified; (b) stale-input proof — an export with a > 1 h
  old input returns the STALE tag naming that input.
- **Grep checks (build lane, §5-style):** zero `<button>`/`<input>`/`<a>`/`<form>`
  in the new component; zero hardcoded figure literals as displayed values;
  verbatim strings present (§3, §6, §8); no `token_hash`, `token_salt`,
  `password`, `seed`, `private_key`, wallet-address pattern in the component
  or in `data/profitability.json`; no `SELECT *` over `workers` in the host
  module; no USD/fiat figure rendered by the component (rates in ¢/kWh and
  XMR/day only).
- **Live check (coordinator, after the build):** `getMining` profitability
  block present — figures derived from the live export, `mismatch: false`,
  host == mirror figures, mirrors fresh; your-hardware null + verbatim
  reason; confirmed-earnings block identical to the dashboard block; no
  credential field in the mirror.
- **Independent host verification (Lane E):** re-derive every
  `data/profitability.json` figure from the recorded inputs with the §1
  formula and compare; confirm the module wrote no decisions/ledger rows;
  confirm configs unchanged (sha256 vs baseline); confirm the full unit suite
  unmodified and passing; confirm the coordinator sub-step is guarded
  (temp-DB `run_pass` decisions exactly +1).
- **Independent artifact inspection (repair_authorized=false):** implementation
  verified in source + data (placement, panels, zero interactive elements, no
  hardcoded figures, no fiat in the panel, mismatch false, mirrors fresh).
  Render status reported honestly — a render capture is NOT required of this
  lane, but if no Mining-tab capture exists, the report must say so plainly
  (the M7 finding-1 gap is not closed by assertion).
