# ATLAS MASTER MISSION 4 — GATE 5: COST ACCOUNTING (WALL-WATT ECONOMICS)

**Lane C — Cost Accounting. Read-only research and computation.**
Date: 2026-11-18, 03:33–03:45 EST. Status: RESEARCH ONLY — no mining, no
trading, no wallets, no keys, no purchases, no config changes, no artifact or
daemon changes.

## 0. REALIZED vs PROJECTED — READ THIS FIRST

- **Realized mining revenue: $0.** ATLAS has no mining hardware, mining is
  DISABLED, and there is no authorization to mine on the current host.
  Nothing in this document is income, capital, or a promise.
- **Every figure below is a projection, never capital.** Projected earnings
  are NOT available funds, NOT trading capital, and NOT a forecast of what
  ATLAS will earn.
- **No guaranteed profits.** Prices, difficulty, and network hashrate move
  daily. A figure that is positive today can be negative tomorrow.
- **No wall-watt figure in this document is measured.** Every watt figure is
  either CARRIED from a published benchmark (Obj 4) or an ESTIMATE. A physical
  wall-watt measurement on user hardware is OWED (§4) and is not claimed here.

### Labelling discipline (inherited from Mission 1 §4.3 and Obj 4)

- **VERIFIED** — freshly measured from a live API or page in this session,
  with source + time.
- **CARRIED** — taken from Mission 1 or Obj 4, not re-verified in this
  session. Never presented as fresh.
- **ESTIMATE** — computed from the formula (shown), or an assumption with its
  source stated.

---

## 1. VERIFIED INPUTS (fresh checks, 2026-11-18 ~03:33 EST)

| Input | Value | Source | Time (EST) | Label |
|---|---|---|---|---|
| XMR price | **$501.26 USD** (−1.10% 24 h); CAD $718.17 | CoinGecko `simple/price` (monero, usd+cad) | 03:33 | VERIFIED |
| XMR price, cross-check | $498.00 USD | MoneroOcean `/pool/stats` price.usd | 03:33 | VERIFIED |
| Monero network difficulty | **787,074,505,719** | MoneroOcean `/network/stats` (port 18081) | 03:33 | VERIFIED |
| Monero network hashrate | **6.559 GH/s** (787,074,505,719 ÷ 120 s) | Derived from VERIFIED difficulty, 120 s block time | 03:33 | ESTIMATE (from VERIFIED difficulty) |
| Monero block reward | **0.6 XMR** tail emission; last block value 0.60540582 XMR incl. fees | MoneroOcean `/network/stats` `value` = 605,405,820,000 atomic units; tail emission 0.6 XMR | 03:33 | VERIFIED (last-block value); 0.6 base ASSUMPTION per Obj 4 |
| Chain height | 3,808,948 | MoneroOcean `/network/stats` | 03:33 | VERIFIED |
| Blocks/day | 720 (120 s block time) | Protocol constant | — | ASSUMPTION (protocol) |
| Daily emission | 432 XMR/day (720 × 0.6) | Computed | — | ESTIMATE |
| Pool fee (MoneroOcean) | **0%** | Obj 4, hashrate.no / pool guides | — | CARRIED |
| MoneroOcean pool hashrate | 263.2 MH/s, 4,959 miners (XMR port 18081: 242.5 MH/s, 4,764 miners) | MoneroOcean `/pool/stats` | 03:33 | VERIFIED |
| USD/CAD | **1.4327** | CoinGecko `exchange_rates` (CAD 92,599.233 ÷ USD 64,630.689 per BTC) | 03:33 | VERIFIED |
| Hydro-Québec Rate D Tier 1 | **7.065¢ CAD/kWh** (first 40 kWh/day) | Multiple independent Nov 2026 sources citing HQ official 2026 Electricity Rates, eff. Apr 1, 2026 (see §2) | 03:35 | VERIFIED* (see note) |
| Hydro-Québec Rate D Tier 2 | **11.142¢ CAD/kWh** (above 40 kWh/day) | Same as Tier 1 | 03:35 | VERIFIED* (see note) |
| HQ Tier 2 in USD | **7.777¢ USD/kWh** (11.142 ÷ 1.4327) | Computed from VERIFIED inputs | 03:33 | ESTIMATE |
| HQ Tier 1 in USD | **4.931¢ USD/kWh** (7.065 ÷ 1.4327) | Computed from VERIFIED inputs | 03:33 | ESTIMATE |
| US average residential | **17.23¢ USD/kWh** | EIA Form EIA-861 final 2025 data | — | CARRIED (Obj 4) |
| System access charge (HQ) | 46.154¢ CAD/day | HQ Rate D | — | CARRIED (excluded — fixed household charge, see §2) |

\* **Hydro-Québec verification note:** the direct hydroquebec.com rates pages
returned HTTP 404 from this host (site restructure), so the rates were NOT
re-verified on hydroquebec.com itself. They ARE confirmed by multiple
independent November 2026 sources all citing the same official document
(Hydro-Québec 2026 Electricity Rates, effective April 1, 2026): tslna.com
(checked Nov 7, 2026), solarenergies.ca, wealthnorth.ca, cgkrealties.com,
airgreen.ca, guidetoartificialintelligence.com — all agree on 7.065¢ /
11.142¢ and the 46.154¢/day access charge. Treated as VERIFIED via
corroborated secondary sources; a direct HQ-page re-check is still owed if
the rate is ever used for a billing decision.

### Endpoint note (for the testing lane)

- Working: `https://api.moneroocean.stream/pool/stats` (HTTP 200) and
  `https://api.moneroocean.stream/network/stats` (HTTP 200).
- **Do NOT use `/api/stats`** — it 404s. The task instruction is confirmed
  by the Obj 4 source list, which used `/pool/stats` and `/network/stats`.
- The network-stats payload is keyed by port; XMR is port **18081**
  (`difficulty`, `height`, `value`, `main_height`).

### What changed since Obj 4 (~01:00 EST, ~2.5 h earlier)

| Input | Obj 4 | Now | Change |
|---|---|---|---|
| XMR price | $507.17 | $501.26 | −1.2% |
| Network hashrate | 6.44 GH/s | 6.56 GH/s | +1.9% |
| Block reward | 0.6 XMR | 0.6 XMR (last block 0.6054) | — |
| USD/CAD | 1.4316 | 1.4327 | +0.1% |
| Pool hashrate / miners | 266.5 MH/s, 4,926 | 263.2 MH/s, 4,959 | flat |

The economics conclusion does not depend on any of these moves: all are
~2% or less, and every case below is decided by an order of magnitude or by
a margin smaller than the hashrate assumption's own uncertainty.

---

## 2. ELECTRICITY PRICES

### Hydro-Québec Rate D (residential), effective April 1, 2026

- **Tier 1: 7.065¢ CAD/kWh** for the first 40 kWh/day (per billing period).
- **Tier 2: 11.142¢ CAD/kWh** above 40 kWh/day.
- System access charge: 46.154¢ CAD/day — **excluded** from the marginal
  mining cost, because the household already pays it whether it mines or not.
- **Base case is Tier 2.** A mining rig's power is MARGINAL consumption on
  top of the household's base load. In a Quebec home with electric heat the
  household is far above 40 kWh/day in winter, so the rig's kWh land in
  Tier 2. Tier 1 is shown only as the optimistic bound, never as the base case.
- **The proposed 19.5¢/kWh Quebec blockchain tariff is PENDING, NOT in
  effect.** Proposed February 2026, awaiting Régie de l'énergie approval.
  It is NOT included in any base-case figure in this document. It is a real
  regulatory risk: if it ever took effect, every Quebec case below would lose
  money by a wide margin (at 19.5¢ CAD = 13.61¢ USD/kWh, the 10 kH/s desktop
  case nets −$0.23/day).

### United States — comparison

- **17.23¢ USD/kWh** (EIA Form EIA-861 final 2025 data, released Oct 7, 2026)
  — CARRIED from Obj 4, not re-verified this session. EIA Short-Term Energy
  Outlook (Oct 2026) projects 18.21¢ for 2026.
- At the US average, **every** worker case in this document loses money,
  including the native desktop.

---

## 3. FORMULA

```
daily coins  = (your hashrate / network hashrate) × blocks/day × block reward × (1 − pool fee)
gross $/day  = daily coins × XMR price
electricity $/day = wall watts × 24 / 1000 × price per kWh
net $/day    = gross − electricity          (whole-system net, before the 75/25 split)
```

With the fresh inputs (network 6,558,954,214 H/s; 720 blocks/day; 0.6 XMR;
0% fee; $501.26/XMR):

- **$0.03302/day per kH/s** of hashrate (gross).
- **$0.000033016/day per H/s** of hashrate (gross).
- Electricity cost per wall watt: **$0.0018665/day per W** at HQ Tier 2
  (7.777¢ USD/kWh); **$0.0041352/day per W** at the US average (17.23¢).
- **Breakeven efficiency: 56.5 H/s per wall watt at HQ Tier 2;
  125.2 H/s per wall watt at the US average.** Any worker below that line
  loses money on electricity alone, before any split, fee, or hardware cost.
  This is the single number gate 5 hands to the testing lane: the prototype
  must beat 56.5 H/W at Tier 2 just to break even.

### The 75/25 split

ATLAS's planned split (Mission 1 §6): distributions are calculated only from
**actual confirmed pool rewards** — never from estimated hashrate. The user
keeps **75% of net distributable rewards** (gross after the 0% pool fee);
ATLAS keeps 25%. Electricity is paid by the user out of their own pocket —
it is NOT deducted by ATLAS before the split. So the user's real position is:

```
user gross share $/day = 0.75 × gross $/day
user net position $/day = 0.75 × gross − electricity $/day
worker-days to earn $1 (gross share) = 1 ÷ (0.75 × gross $/day)
```

Note the consequence: the split pushes the marginal desktop case underwater
for the user even where the whole-system net is positive (§5, case c).

---

## 4. WALL-WATT MEASUREMENT PROTOCOL (GATE 5)

### What "wall watts" means

Wall watts = the extra AC power drawn from the wall socket while mining,
minus the same machine's idle draw, measured at the plug. It includes PSU
losses, motherboard, RAM, fans, and everything else the meter sees. It is the
ONLY power number that can be multiplied by the electricity price to get a
true cost.

### Protocol (for the testing lane, on user hardware)

1. **Instrument:** a physical plug-in power meter (Kill-A-Watt style) between
   the wall socket and the machine's power supply. Record make/model.
2. **Baseline:** machine idle, miner stopped, same apps open as during the
   test, 10 minutes settled — record idle watts.
3. **Mining run:** start the miner (browser tab, or native XMRig for the
   desktop case), let hashrate settle, then record watts every 5 minutes for
   **at least 60 minutes sustained** (a 5-minute burst is not a measurement —
   RandomX dataset generation, thermal throttling, and tab throttling all
   move the number).
4. **Wall watts = mean mining watts − mean idle watts.** Report the mean, the
   min/max over the run, and the hashrate measured over the same window.
5. **Record alongside:** machine make/model, CPU, thread count, browser and
   version (browser case), ambient temperature if available, and whether the
   tab was visible/foregrounded the whole run (a hidden/backgrounded tab is
   throttled — see Mission 1 §4.1 — and its watts are not comparable).
6. **Repeat** on a second day if the first run's hashrate or watts drifted
   >10% — RandomX performance is thermally sensitive.

### What is NOT wall watts (label discipline)

- **Software power estimates are NOT wall watts.** OS power APIs, CPU
  package-power readings (RAPL, `powerstat`, Task Manager "power usage"),
  and TDP-based estimates (e.g. "105 W CPU") measure the chip, not the wall.
  They exclude PSU losses (~10–20%), motherboard, RAM, and fans, and they
  understate true cost by roughly 20–40%. Any figure from such a source must
  be labelled **ESTIMATE — software power, not measured wall watts**, and
  must NEVER be presented as a measured wall-watt figure.
- **TDP is not power draw.** A "105 W TDP" CPU can draw 110 W under RandomX
  and 171 W at the wall as a system (Obj 4, cpumining.pro). TDP is a thermal
  design number, not a meter reading.

### What CANNOT be measured on the Muse VM host — OWED, not claimed

- **No mining is run on the Muse VM host** (no authorization; mining is
  DISABLED). No hashrate, no power draw, and no wall-watt figure in this
  document comes from the host.
- **The host has no physical power meter and no wall socket.** It is a shared
  virtual machine (1.5 shared CPUs, 6 GB cell cap). There is nothing to plug
  a meter into, and host "power" numbers would be meaningless even if they
  existed.
- **Therefore a physical wall-watt measurement is OWED on user hardware.**
  Every watt figure in §5 is CARRIED from published benchmarks or an
  ESTIMATE range, and the economics in §5 must be re-run with measured watts
  once the testing lane performs the protocol above. Gate 5 does not pass on
  estimates alone — it passes when a measured wall-watt number exists next to
  a measured hashrate.

---

## 5. COMPUTED ECONOMICS

Inputs: XMR $501.26 (VERIFIED), network 6.559 GH/s (ESTIMATE from VERIFIED
difficulty), 720 blocks/day, 0.6 XMR reward, MoneroOcean 0% fee.
Electricity: HQ Tier 2 = 7.777¢ USD/kWh, HQ Tier 1 = 4.931¢ USD/kWh
(ESTIMATE from VERIFIED CAD rates + VERIFIED USD/CAD), US avg = 17.23¢
USD/kWh (CARRIED).

Hashrate sources: (a) and (b) CARRIED from Mission 1 §4.1 (Monerica,
Oct 2026); (c) CARRIED from Obj 4 §4 (XMRig benchmark, Kryptex,
cpumining.pro). Watt figures: (a) 30–60 W ESTIMATE range (Mission 1 §4.3);
(b) 35–70 W ESTIMATE range (implied by Mission 1 §4.3's $0.15–0.30/day at
~$0.18/kWh); (c) 171 W CARRIED from Obj 4 (cpumining.pro measured wall watts).

### 5.1 Headline table — whole-system net (before split)

| Worker | Hashrate | Wall W | Gross $/day | Net $/day HQ Tier 2 | Net $/day US avg | Efficiency (H/W) | Verdict |
|---|---|---|---|---|---|---|---|
| (a) Laptop browser | 200 H/s | 45 (30–60) | $0.0066 | **−$0.077** (−$0.049 to −$0.105) | **−$0.180** (−$0.118 to −$0.242) | 4.4 | Loses ~12× its revenue |
| (b) 32-thread desktop browser | 850 H/s | 50 (35–70) | $0.0281 | **−$0.065** (−$0.037 to −$0.103) | **−$0.179** (−$0.117 to −$0.261) | 17.0 | Loses ~2–3× its revenue |
| (c) Ryzen 7 5800X native, 10 kH/s | 10,000 H/s | 171 | $0.3302 | **+$0.011** | **−$0.377** | 58.5 | Barely breakeven at Tier 2 only |
| (c) Ryzen 7 5800X native, 12,445 H/s | 12,445 H/s | 171 | $0.4109 | **+$0.092** | **−$0.296** | 72.8 | Positive at Tier 2 only |
| (c) Ryzen 7 5800X native, 8,245 H/s | 8,245 H/s | 171 | $0.2722 | **−$0.047** | **−$0.435** | 48.2 | Loses even at Tier 2 |
| (d) Prototype (MEASURED) | H_meas | W_meas | — | — | — | H_meas ÷ W_meas | TO BE FILLED by testing lane |

Midpoint watts shown; ranges in parentheses use the low/high watt ends.
All net figures are ESTIMATE (computed from VERIFIED price/difficulty and
CARRIED/ESTIMATE hashrate and watts), BEFORE hardware cost.

Detail (ESTIMATE):

| Worker | Gross | Elec T2 | Net T2 | Elec T1 | Net T1 | Elec US | Net US |
|---|---|---|---|---|---|---|---|
| (a) 200 H/s, 45 W | $0.0066 | $0.0840 | −$0.0774 | $0.0533 | −$0.0467 | $0.1861 | −$0.1795 |
| (b) 850 H/s, 50 W | $0.0281 | $0.0933 | −$0.0653 | $0.0592 | −$0.0311 | $0.2068 | −$0.1787 |
| (c) 10 kH/s, 171 W | $0.3302 | $0.3192 | +$0.0110 | $0.2024 | +$0.1278 | $0.7071 | −$0.3770 |
| (c) 12,445 H/s, 171 W | $0.4109 | $0.3192 | +$0.0917 | $0.2024 | +$0.2085 | $0.7071 | −$0.2962 |
| (c) 8,245 H/s, 171 W | $0.2722 | $0.3192 | −$0.0469 | $0.2024 | +$0.0698 | $0.7071 | −$0.4349 |

Breakeven electricity price (whole-system, before split): (a) 0.61¢/kWh;
(b) 2.34¢/kWh; (c) 10 kH/s 8.04¢/kWh; (c) 12,445 H/s 10.01¢/kWh;
(c) 8,245 H/s 6.63¢/kWh. No realistic residential rate is below 2.34¢/kWh,
so both browser cases lose at any real price. The desktop case only survives
below ~8–10¢/kWh — i.e. only at Quebec Tier 1/Tier 2, never at the US average.

### 5.2 The 75/25 split effect (user's share)

| Worker | Gross $/day | User keeps (75%) | ATLAS keeps (25%) | Worker-days to earn $1 (user gross share) | User net position, HQ Tier 2 | User net position, US avg |
|---|---|---|---|---|---|---|
| (a) Laptop browser, 200 H/s | $0.0066 | $0.0050/day | $0.0017/day | **202 days** | **−$0.079/day** | **−$0.181/day** |
| (b) Desktop browser, 850 H/s | $0.0281 | $0.0210/day | $0.0070/day | **48 days** | **−$0.072/day** | **−$0.186/day** |
| (c) 5800X native, 10 kH/s | $0.3302 | $0.2476/day | $0.0825/day | **4.0 days** | **−$0.072/day** | **−$0.460/day** |
| (c) 5800X native, 12,445 H/s | $0.4109 | $0.3082/day | $0.1027/day | **3.2 days** | **−$0.011/day** | **−$0.399/day** |
| (c) 5800X native, 8,245 H/s | $0.2722 | $0.2042/day | $0.0681/day | **4.9 days** | **−$0.115/day** | **−$0.503/day** |
| (d) Prototype (MEASURED) | — | 0.75 × gross | 0.25 × gross | 1 ÷ (0.75 × gross) | 0.75 × gross − elec | 0.75 × gross − elec |

Key finding: **the split pushes even the marginal desktop case underwater
for the user.** At 10 kH/s the whole system nets +$0.011/day at Tier 2, but
the user's 75% share ($0.2476) does not cover their own $0.3192 electricity
bill — the user nets −$0.072/day. Only at Tier 1 (optimistic bound) does the
user come out ahead on the desktop case (+$0.045/day at 10 kH/s). The browser
cases are negative for the user at every rate: the laptop browser user pays
~$0.08/day to "earn" $0.005/day.

Time to the MoneroOcean 0.003 XMR minimum payout (gross coins, before split):
(a) **228 days (~7.5 months)**; (b) 54 days; (c) 10 kH/s 4.6 days. The
browser user's payout, when it finally arrives after 7+ months, is worth
~$1.50 at today's price — while they paid ~$19 in electricity to earn it
(228 days × $0.084/day at Tier 2).

### 5.3 Case (d) — prototype placeholder (testing lane to fill)

Do NOT invent a number. When the testing lane measures the prototype, fill
this row with the formula:

```
H_meas  = measured hashrate (H/s) over the sustained run (§4)
W_meas  = measured extra wall watts over the same run (§4)
coins/day   = H_meas ÷ 6,558,954,214 × 720 × 0.6 × (1 − pool fee)
gross $/day = coins/day × [live XMR price — re-verify at fill time, do not reuse $501.26]
electricity $/day = W_meas × 24 ÷ 1000 × [live $/kWh — re-verify at fill time]
net $/day   = gross − electricity
user share  = 0.75 × gross ; user net = 0.75 × gross − electricity
efficiency  = H_meas ÷ W_meas  →  must exceed 56.5 H/W at HQ Tier 2 (125.2 H/W at US avg) to break even
```

Worked reference points (ESTIMATE, same inputs as §5.1 — for scale only,
not a prediction of what the prototype will do):

| If the prototype measures… | Gross $/day | Net $/day at Tier 2, 45 W | Net $/day at Tier 2, 20 W |
|---|---|---|---|
| 200 H/s (laptop-browser class) | $0.0066 | −$0.077 | −$0.038 |
| 850 H/s (desktop-browser class) | $0.0281 | −$0.065 | −$0.019 |
| 2,000 H/s | $0.0660 | −$0.018 | +$0.029 |
| 6,300 H/s (native laptop class) | $0.2080 | +$0.124 | +$0.171 |

A browser prototype would need roughly **2,500+ H/s at 45 W** (or ~1,100 H/s
at 20 W) just to reach zero at Tier 2. Mission 1's measured browser
hashrates (200–850 H/s) are 3–12× short of that.

---

## 6. HARDWARE COST — THE SEPARATE LINE THAT KILLS THE MARGINAL CASE

Hardware cost is EXCLUDED from all net figures in §5. It is shown here
separately because it decides whether the one near-breakeven case is worth
anything at all.

- **Reference system: ~$500** for a Ryzen 7 5800X-based system (Obj 4:
  $400–600 to build/buy).
- At the whole-system net of **+$0.011/day** (10 kH/s, HQ Tier 2, fresh
  inputs), payback is **$500 ÷ $0.011/day ≈ 45,000 days ≈ 124 years**.
  At Tier 1 (+$0.1278/day) it is ~10.7 years. At 12,445 H/s Tier 2
  (+$0.0917/day) it is ~14.9 years. Obj 4's ~65-year figure used the older
  price/network; the fresh inputs make the Tier 2 case worse, not better.
- **Plain statement: hardware cost kills the marginal desktop case.** No
  hardware purchase is justified by this model. A $500 system bought to mine
  Monero at Quebec Tier 2 rates would take over a century to pay for itself
  at the reference hashrate — and the CPU would be obsolete decades before
  that.
- The only honest framing for hardware: if the user **already owns** the
  machine (sunk cost), hardware does not enter the marginal decision — only
  electricity vs revenue matters (§5). Buying hardware to mine is a separate,
  unjustifiable decision.
- Browser cases need no new hardware, but that does not save them: they lose
  $0.05–0.11/day at Tier 2 on electricity alone, every day they run.

---

## 7. VERDICT (GATE 5)

1. **Browser mining loses money at every electricity price in this model.**
   Laptop browser: −$0.077/day at HQ Tier 2 (midpoint), −$0.180/day at the
   US average. Desktop browser: −$0.065/day at Tier 2, −$0.179/day at US
   average. The user pays 12× (laptop) to 3× (desktop browser) more in
   electricity than the mining earns, before the 75/25 split; after the split
   the user is further underwater.
2. **Native desktop CPU mining barely breaks even, only at Quebec rates, and
   only before the split and before hardware cost.** +$0.011/day whole-system
   at 10 kH/s / Tier 2; the user nets −$0.072/day after the 75/25 split;
   a $500 system needs ~124 years to pay back. The sign flips with the
   hashrate assumption (8,245 H/s loses even at Tier 2).
3. **The prototype's gate is a number, not a hope: 56.5 H/s per wall watt**
   at HQ Tier 2 (125.2 H/W at the US average). Mission 1's measured browser
   hashrates deliver 4.4–17 H/W. Unless the testing lane measures something
   dramatically better, the prototype will confirm the browser-miner verdict
   from Mission 1 §4.3: **IMPRACTICAL as an earner; participation/demo
   framing only.**
4. **What is measured vs estimated vs owed:**
   - MEASURED (VERIFIED) in this session: XMR price $501.26, network
     difficulty 787,074,505,719 (→ 6.559 GH/s), last-block value 0.6054 XMR,
     pool hashrate/miners, USD/CAD 1.4327.
   - CARRIED (not re-verified): pool fee 0%, US average 17.23¢/kWh, 171 W
     desktop wall power, browser hashrates 200/850 H/s, desktop hashrate
     range 8,245–12,445 H/s.
   - ESTIMATE: every net/gross figure in §5 (computed, formula shown), the
     30–60 W and 35–70 W browser power ranges, Tier 1/Tier 2 USD conversions.
   - OWED: a physical wall-watt measurement on user hardware (§4 protocol),
     and the prototype's measured hashrate (case d). Neither exists yet.
     Gate 5's accounting is complete as a model; it is NOT complete as a
     measurement until those two arrive.

---

## 8. SOURCES

- XMR price, USD/CAD: CoinGecko `api/v3/simple/price?ids=monero&vs_currencies=usd,cad`
  and `api/v3/exchange_rates`, fetched 2026-11-18 ~03:33 EST.
- Monero network + pool: `api.moneroocean.stream/network/stats`,
  `api.moneroocean.stream/pool/stats`, fetched 2026-11-18 ~03:33 EST.
  (Note: `/api/stats` 404s — use `/pool/stats` and `/network/stats`.)
- Hydro-Québec Rate D: Hydro-Québec 2026 Electricity Rates, eff. Apr 1, 2026,
  as cited Nov 2026 by tslna.com, solarenergies.ca, wealthnorth.ca,
  cgkrealties.com, airgreen.ca, guidetoartificialintelligence.com. Direct
  hydroquebec.com pages returned 404 from this host — re-check owed for any
  billing decision.
- US average: U.S. EIA Form EIA-861 final 2025 (17.23¢/kWh), via Obj 4.
- Prior models: Mission 1 inspection report
  (`docs/master-mission1-inspection-report-2026-11-18.md`, §4.1–4.3, §6) and
  Infrastructure Mission 2 Obj 4 (`docs/mission2-obj4-findings.md`).
- Hashrates/watts: Monerica browser mining (Oct 2026); XMRig public
  benchmark (Ryzen 7 5800X 12,445 H/s); Kryptex (10,000 H/s @ 105 W);
  cpumining.pro (8,245 H/s, 110 W CPU / 171 W wall) — all via Obj 4 / Mission 1.
