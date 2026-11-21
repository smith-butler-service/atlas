# Master Mission 9 Repair — Design Note (calibration + canonical transform)

**Authorization:** user order 2026-11-18 ~22:05 EST ("do repair on what need to be done"),
after the Mission 9 report. Two repairs, both authorized. Safety unchanged:
emergency stop ON, simulation-only, no mining/trading/payouts/wallets/keys/spend/config changes.

**Ground truth read:** `docs/master-mission9-report-2026-11-18.md` (full),
`docs/master-mission9-design.md`, `docs/master-mission9-lane-d-ui-report-2026-11-18.md`,
`core/atlas_profitability.py` (rounding sites), `data/profitability.json`
(export 1795057444, live), `/tmp/m9-ingest-payload3.json` (the coordinator's
hand mapping, verified live), cron job `atlas-refresh-health-check-1h` (read
2026-11-19 ~03:10 UTC).

---

## Repair 1 — Live mirror mismatch calibration

### Decision: fix on the MIRROR side (the comparison), not the host

Justification (D-M9-1: host is system of record for FIGURES):

- Every figure is correct on both sides (Lane E re-derived 166/166; the
  coordinator hand-checked the mirror formula). No figure value changes
  anywhere — host export, mirror payload, and displayed figures stay
  byte-identical before and after this repair.
- The comparison is the artifact's calibration layer (Lane D spec §2.4,
  `server/src/profitability.ts` `compareProfitabilityFigures`). It is the
  ONLY place where all four causes can be fixed as pure calibration:
  - Cause 1 could not be fixed host-side without re-rounding the export
    (changes stored values).
  - Cause 2 could not be fixed host-side without changing the displayed
    GPU gate unit/magnitude (MH/W → H/W would show 12,490,264,911 H/W).
  - Cause 3 could not be fixed host-side without nulling host values
    (changes figures).
  - Cause 4 could not be fixed host-side without adding rows (new figures).
- Therefore: calibrate the comparison to compare like-for-like. The mirror
  derivation itself is correct and is NOT changed; only the comparator's
  precision, unit, and scope assumptions change.

### Exact comparison rules (R1–R4)

**R1 — Precision (cause 1: host 6dp rounding vs 1e-9 tolerance).**
Round the mirror value to the host field's display precision BEFORE
comparing, then apply the existing tolerance `max(1e-9, 1e-6·|host|)`.
Precision table — taken from the `_round()` call sites in
`core/atlas_profitability.py` (lines 829–898), verified against the live
export:

| Precision | Fields |
|---|---|
| 6dp | dailyCoinsNative, grossXmrPerDay, netXmrPerDayTier1, netXmrPerDayTier2, netXmrPerDayUsAvg, netXmrPerDayProposedTariff, userShareXmrPerDay, atlasShareXmrPerDay, userNetXmrPerDay, poolFees netXmrPerDayTier2 |
| 1dp | breakevenHwTier2, breakevenHwUsAvg, currentHw |
| 3dp | ratioTier2 (distance_to_breakeven_tier2) |
| 2dp | breakevenCentsPerKwh |
| exact | verdict strings (verdictTier2, verdict) |

This also covers the KAS edge case Lane E noted: KAS gross XMR/day is
≈1.4e-7, which rounds to 0.0 at 6dp on the host; the mirror rounds to 0.0
too, so they agree.

**R2 — Units (cause 2: GPU breakeven gates MH/W host vs H/W mirror).**
For GPU rows (coin KAS/RVN/ERG — profiles whose `hashrate_unit` is MH/s),
convert the mirror's breakeven H/W to MH/W (÷ 1e6) before comparing
against the host's MH/W value. Applies to breakevenHwTier2 and
breakevenHwUsAvg. The comparison normalizes units; no figure changes.
(The host's MH/W is the displayed unit; the mirror's H/W is the §1
formula unit. The display unit question itself is NOT changed here.)

**R3 — Null-scope (cause 3: GPU currentHw/ratioTier2/verdictTier2).**
Design §2.4 (Lane D spec) states `currentHw` is "XMR rows only; null for
GPU rows". The mirror follows the design (null for GPU rows). The host
fills GPU currentHw (in MH/W), ratioTier2, and verdictTier2. Rule: SKIP
currentHw, ratioTier2, and verdictTier2 for GPU rows in the comparison —
these fields are out of the mirror's contract by design; the host's values
there are not compared. The host values remain the displayed figures.
Null-vs-number remains a mismatch for every OTHER field (no silent
equality anywhere else).

**R4 — Split scope (cause 4: host split has 4 rows, mirror computes 6).**
The host `split_projection` emits 4 rows only (`SPLIT_PROFILE_IDS` =
xmr_cpu, kas, rvn, erg); the mirror derivation computes split fields for
all 6 profile rows. Rule: compare userShareXmrPerDay /
atlasShareXmrPerDay / userNetXmrPerDay ONLY on the 4 (coin, profile)
pairs the host emits (XMR / Ryzen 7 5800X, KAS / RTX 3060 Ti,
RVN / RTX 3060 Ti, ERG / RTX 3060 Ti). For browser rows (Laptop /
Desktop browser), where the host value is null, SKIP the split fields —
the mirror's computed browser splits are not compared against a host
null. The host is the system of record for the split projection's scope.

**Unchanged:** the confirmed-earnings secondary check (dashboard is the
authority); the mismatch display rule (on any remaining disagreement show
host-verified figures + verbatim "Mirror mismatch — figures under
investigation"); the STALE rules.

**Expected outcome:** live `getMining` reports `mismatch: false`,
`mismatchDetails: []`, with every figure byte-identical to its
pre-repair value, `stale: false`.

**Regression guard (binding):** the sandbox mismatch proofs must still
pass after this change — a tampered host figure must still produce
`mismatch: true` with the field named. The calibration must not blind
the check. If R1–R4 as written would mask a genuinely tampered figure,
the repair is wrong and must be re-done, not shipped.

---

## Repair 2 — Refresh-task step-9 canonical transform

### Ground truth

The export's real shape (`data/profitability.json`): top-level
`exported_at` / `mode` / `emergency_stop` / `inputs` (object keyed by
coin: xmr/kas/rvn/erg/usd_cad/electricity/pool_fees) / `panel.*`
(coin_comparison, breakeven, sensitivity, pool_fees, split_projection,
your_hardware, inputs, last_sync) / `audit_usd` / `confirmed_earnings` /
`your_hardware` / `stale`. There are NO top-level `inputs[]`/`coins[]`
arrays — the step-9 instruction as written ("mapped field-for-field
from profitability.json") assumes arrays that do not exist, so the next
refresh would ingest nothing / fail validation and the mirror would go
stale. The canonical transform below is the coordinator's hand mapping
(`/tmp/m9-ingest-payload3.json`, verified live with ingest 3), written
as a repeatable rule.

### The transform (panel.* → flat camelCase ingest payload)

1. Read `~/workspace/atlas/data/profitability.json`. If missing or
   unreadable → call `ingestProfitabilityState` exactly once with
   export = null (it reports `profitabilityExportMissing` and stores
   nothing). Never invent figures. Never pass the `audit_usd` block
   anywhere (USD intermediates are audit data only, never rendered).
   Never pass any token, token hash, session token, password hash,
   seed, private key, or wallet address — the export carries none and
   none may be added.
2. `exportedAt` = `exported_at`; `mode`; `emergencyStop` =
   `emergency_stop`.
3. `inputs[]` — 40 rows: 20 live + 20 constants.
   - Live, per coin in {xmr, kas, rvn, erg}, from `inputs.{coin}`:
     `{coin}_price_usd` = `price_usd` (source = `source_price`,
     e.g. "CoinGecko simple/price"); `{coin}_network_hashrate_hps` =
     `network_hashrate_hps` (source = `source_network`);
     `{coin}_difficulty` = `difficulty` (null for RVN — keep null,
     never 0); `{coin}_block_reward` = `block_reward` (source =
     `block_reward_source`); `{coin}_blocks_per_day` =
     `blocks_per_day` (source "Derived from block time (X s)").
     `fetchedAt` = that coin's `fetched_at`. `usd_cad_rate` =
     `inputs.usd_cad.value` (source "CoinGecko exchange_rates",
     `fetchedAt` = `inputs.usd_cad.fetched_at`).
   - Constants, `fetchedAt` = `exported_at`, source string carries
     source + effective date (D-M9-4 gives tariff constants
     `fetched_at: null`; the schema forces integer `fetchedAt`, so the
     export instant is stored and the constant is labelled in its
     source string — the M9 mapping decision, kept verbatim):
     `rate_hq_tier1_cad_per_kwh` 7.065, `rate_hq_tier2_cad_per_kwh`
     11.142 (source "Hydro-Québec Rate D (residential), effective
     2026-04-01"); `rate_us_avg_usd_per_kwh` 17.23 (source "U.S. EIA
     Form EIA-861 final 2025 data, effective 2025");
     `rate_proposed_qc_cad_per_kwh` 19.5 (source "Proposed February
     2026, pending Régie de l'énergie approval — not in effect");
     `fee_moneroocean_bps` 0, `fee_supportxmr_bps` 60,
     `fee_p2pool_bps` 0 (source "config/pool-rewards.json");
     `fee_2miners_bps` 100 (source "Obj 4 (CARRIED)");
     `profile_xmr_ryzen_hashrate_hps` 10000 /
     `profile_xmr_ryzen_wall_watts` 171;
     `profile_kas_gpu_hashrate_hps` 480000000 /
     `profile_kas_gpu_wall_watts` 150;
     `profile_rvn_gpu_hashrate_hps` 27000000 /
     `profile_rvn_gpu_wall_watts` 240;
     `profile_erg_gpu_hashrate_hps` 137000000 /
     `profile_erg_gpu_wall_watts` 132;
     `profile_xmr_laptop_hashrate_hps` 200 /
     `profile_xmr_laptop_wall_watts` 45;
     `profile_xmr_desktop_hashrate_hps` 850 /
     `profile_xmr_desktop_wall_watts` 50
     (profile sources "Obj 4 / M4 CARRIED, ASSUMPTION" /
     "Obj 4 CARRIED, ASSUMPTION" / "M4 CARRIED, ASSUMPTION").
   - Do NOT use the export's `panel.inputs[]` as the source for
     `inputs[]` — it lacks prices and USD/CAD. Use the top-level
     `inputs` object (+ `electricity` / `pool_fees` blocks) above.
4. `coins[]` — 6 rows: join `panel.coin_comparison` +
   `panel.breakeven` + `panel.sensitivity` + `panel.split_projection`
   on (coin, profile).
   - `coin`: uppercase (XMR/KAS/RVN/ERG). `profile`: display name
     mapped from host id — xmr_cpu → "Ryzen 7 5800X", kas/rvn/erg →
     "RTX 3060 Ti", xmr_browser_laptop → "Laptop browser",
     xmr_browser_desktop → "Desktop browser". `algo`: RandomX /
     kHeavyHash / KawPow / Autolykos v2.
   - `hashrateHps`: profile hashrate in H/s (GPU: panel `hashrate`
     in MH/s × 1e6). `wallWatts` as-is.
   - `dailyCoinsNative`, `grossXmrPerDay`, `netXmrPerDayTier2`,
     `verdictTier2`: from `coin_comparison`.
     `netXmrPerDayTier1` / `netXmrPerDayUsAvg` /
     `netXmrPerDayProposedTariff`: from
     `sensitivity.net_xmr_per_day`.
   - `breakevenHwTier2` / `breakevenHwUsAvg`, `currentHw`,
     `ratioTier2` (= `distance_to_breakeven_tier2`),
     `breakevenCentsPerKwh`: from `breakeven`.
   - `userShareXmrPerDay` / `atlasShareXmrPerDay` /
     `userNetXmrPerDay`: from `split_projection` where a row exists;
     NULL for browser rows (the host emits no browser split rows —
     never compute host-figure values into the payload for them; the
     mirror derives them separately).
   - `computed`: true when the panel row `status` == "computed",
     else false with all figure fields null.
5. `poolFees[]` — 3 rows from `panel.pool_fees.rows`: `pool`,
   `feeLabel` = fee_percent formatted ("0%", "0.6%", "0%"),
   `netXmrPerDayTier2`.
6. `yourHardware`: { `measuredHashrateHps`: null,
   `measuredWallWatts`: null, `netXmrPerDay`: null,
   `reason`: `your_hardware_reason` }.
7. `confirmedEarnings`: { `confirmedPiconero`:
   `confirmed_earnings.confirmed_piconero`, `mode` }.

### Where the transform is applied (two places, ONE transform)

- **A. The artifact's `refreshAtlasData` step-9 instruction**
  (`server/src/actions.ts`) — the button path. Replace the as-written
  "mapped field-for-field" text with the canonical transform above.
- **B. The hourly cron job `atlas-refresh-health-check-1h`, step 4
  fallback path** — the agent applies the same transform and calls
  `ingestProfitabilityState` directly when the button refresh fails.
  Evidence this is required: the button path (`refreshatlasdata`)
  failed at 8 of the last 10 hourly runs (11:52, 12:52, 13:52, 15:52,
  16:52, 17:52, 18:52, 20:52 EST; worked only 14:52 and 19:52) and
  the fallback direct ingest is the path that actually runs — and it
  ingests only `snapshot.json`. Without B, the mirror goes stale most
  hours even with A fixed. B is written as step 4b (no renumbering of
  the job's steps 1–10); every other instruction in the job body is
  preserved verbatim.

### Discrepancy recorded (parent task premise corrected)

The repair task as assigned said to write the transform into "the
refresh job's step-9 instruction" via the cron tools. The cron job
`atlas-refresh-health-check-1h` as saved contains NO profitability
step and NO step 9 about profitability (its step 9 is "Log every check
and fix"). The step-9 instruction as written lives in the artifact's
`refreshAtlasData` action (`server/src/actions.ts`, Lane D spec §4).
This repair therefore fixes the transform in BOTH places it is
actually needed (A in the artifact, B in the cron job's fallback
path) and does not invent a step 9 in the cron body. The cron job's
schedule, owner, delivery, title, and all unrelated instructions are
preserved unchanged.

---

## Scope — do NOT touch

- No figure values change anywhere (host export, mirror payload,
  displayed figures all byte-identical).
- Do NOT repair: M6 finding 1 (hardcoded zero literals in
  `RewardAccounting.tsx`), stale "no miner yet" copy, the
  refresh-button failure itself, referral rate, minimum payout,
  SupportXMR URL, tariff `fetchedAt` schema change (the transform
  works around it with `fetchedAt` = export instant, per the M9
  mapping decision; no schema change is made).
- Do NOT modify Mission 10's files (`core/atlas_security.py`, its
  tests) — Mission 10 runs in parallel.
- No new tab/card, no new cron, no new refresh step in the artifact.

## Verification (binding)

- After the repair build lands: live `getMining` → `mismatch: false`,
  `mismatchDetails: []`, every figure byte-identical to its pre-repair
  value, `stale: false`, `profitabilitySyncedAt` fresh.
- Sandbox regression: tampered host figure → `mismatch: true` with the
  field named (the calibration must not blind the check).
- Test refresh (`cron.run` of the updated job): the mirror validates
  (ingest reports `upToDate` or a fresh changed ingest, no validation
  failure) and stays fresh (`stale: false`); the report records the
  path used (button or fallback) and the before/after
  `profitabilitySyncedAt`.
