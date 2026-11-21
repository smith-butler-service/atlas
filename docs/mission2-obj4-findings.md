# PROJECT ATLAS — MISSION 2, OBJECTIVE 4: MINING INTELLIGENCE MODEL
## Comparative mining research (read-only)
Date: 2026-11-18 ~01:00 EST. Status: RESEARCH ONLY — no mining, no trading,
no wallets, no keys, no purchases. All figures are projections, never capital.

## 0. REALIZED vs PROJECTED — READ THIS FIRST
- **Realized mining revenue: $0.** ATLAS has no mining hardware, mining is
  DISABLED, and there is no authorization to mine on the current host.
  Nothing in this document is income, capital, or a promise.
- **Eligible trading capital: $0.** Trading may only ever use realized net
  mining profits. Projected earnings in this model are NOT available capital,
  NOT trading funds, and NOT a forecast of what ATLAS will earn.
- Every number below is labeled **VERIFIED** (measured from a live API or page
  on 2026-11-18, with source + time), **ESTIMATE** (computed — formula shown),
  or **ASSUMPTION** (stated, with its source). If a figure could not be
  verified, it says so.

## 1. METHOD
Daily coins = (your hashrate / network hashrate) x blocks per day x block reward
x (1 - pool fee). Gross revenue = daily coins x price. Power cost = wall kW x
24 h x rate. Net = gross - power cost. Hardware purchase cost is EXCLUDED from
net (see §8 for the payback illustration). Prices are in USD unless marked CAD.
All live data was fetched 2026-11-18 between 00:55 and 01:00 EST.

Reference setups (one unit each — a deliberately small, honest baseline):
- CPU: 1x AMD Ryzen 7 5800X (8C/16T) for Monero RandomX.
- GPU: 1x NVIDIA GeForce RTX 3060 Ti (8 GB) for Kaspa, Ravencoin and Ergo.
- Wall power = card/CPU power + 50 W system overhead (motherboard, idle CPU,
  RAM, fans, PSU losses) — ASSUMPTION, stated.

## 2. ELECTRICITY RATES (inputs to every calculation)
### Quebec — Hydro-Québec Rate D (residential), effective April 1, 2026 — VERIFIED
Source: Hydro-Québec electricity rates chart (hydroquebec.com), confirmed by
multiple 2026 rate summaries.
- Tier 1: **7.065¢ CAD/kWh** for the first 40 kWh/day.
- Tier 2: **11.142¢ CAD/kWh** above 40 kWh/day.
- System access charge: 46.154¢ CAD/day (fixed household charge — excluded
  from the marginal mining cost, because the household already pays it).
- A mining rig's power is MARGINAL consumption on top of the household's base
  load. In a Quebec home with electric heat the household is far above
  40 kWh/day in winter, so the rig's kWh land in Tier 2. Tier 1 is shown as
  the optimistic case only.
- Regulatory note: a 19.5¢/kWh Quebec blockchain tariff was PROPOSED in
  February 2026 and is pending Régie de l'énergie approval — NOT in effect,
  NOT used as a cost input, but a real regulatory risk for any future
  Quebec mining.
### United States — EIA average residential — VERIFIED
Source: U.S. Energy Information Administration, Form EIA-861 final 2025 data
(released Oct 7, 2026).
- **17.23¢ USD/kWh** (2025 final average). EIA Short-Term Energy Outlook
  (Oct 2026) projects 18.21¢ for 2026.
### Currency conversion — VERIFIED
USD/CAD = **1.4316** (CoinGecko exchange_rates API, 2026-11-18).
Quebec Tier 2 = 11.142 / 1.4316 = **7.783¢ USD/kWh**.
Quebec Tier 1 = 7.065 / 1.4316 = **4.935¢ USD/kWh**.

## 3. POOL FEES (named pools) — VERIFIED
| Pool | Coins in this model | Fee | Model | Min payout | Source |
|---|---|---|---|---|---|
| MoneroOcean | XMR | **0%** (donations optional) | PPLNS + auto-switch | 0.003 XMR | hashrate.no 0.00%; 2026 pool guides |
| 2Miners | KAS, RVN, ERG | **1%** | PPLNS | 10 RVN (RVN) | hashrate.no 1.00%; 2026 pool guides |
| P2Pool (XMR) | XMR | **0%** | PPLNS, decentralized | none (direct) | 2026 pool guides |
| HeroMiners | KAS, RVN | ~1% | PPLNS | — | 2026 comparison table |
MoneroOcean also auto-switches to the most profitable RandomX coin and pays in
XMR; that upside is NOT modeled (the model uses straight XMR mining). P2Pool is
the decentralized 0% alternative for XMR.

## 4. MONERO (XMR) — RandomX, CPU
Algorithm: RandomX (rx/0). ASIC-resistant, CPU-optimized by design.
Reference hardware: 1x AMD Ryzen 7 5800X.
- Hashrate **10,000 H/s — ASSUMPTION** (mid-range of published benchmarks:
  XMRig public benchmark average 12,445 H/s; Kryptex 10,000 H/s @ 105 W;
  asicprofit 11,100 H/s @ 105 W; cpumining.pro sustained 8,245 H/s @ 110 W CPU.
  Sensitivity at 8,245 and 12,445 H/s is shown below.)
- Wall power **171 W — VERIFIED** (cpumining.pro: CPU 110 W, total system
  171 W from the wall). 4.104 kWh/day.
Network (VERIFIED, MoneroOcean network stats API, 2026-11-18 ~00:56 EST):
- Difficulty **772,656,444,936**; height 3,808,871.
- Network hashrate = 772,656,444,936 / 120 s = **6.44 GH/s** (cross-check:
  ypool reported ~6.27 GH/s on Oct 9, 2026).
- Block reward **0.6 XMR** (tail emission; last block value 0.6045 XMR
  including fees, MoneroOcean network stats).
- Block time 120 s → 720 blocks/day → daily emission 432 XMR/day.
- Price **$507.17 USD** (CoinGecko, 2026-11-18 ~00:55 EST; +1.52% 24 h;
  MoneroOcean pool price $506.73).
- Pool: MoneroOcean, 0% fee. Pool hashrate 266.5 MH/s, 4,926 miners
  (MoneroOcean pool stats API) — ~4.1% of the network.
Arithmetic (ESTIMATE):
- Share = 10,000 / 6,438,803,708 = 1.5531e-6.
- Daily coins = 1.5531e-6 x 432 = **0.000671 XMR/day** (after 0% fee: same).
- Gross revenue = 0.000671 x $507.17 = **$0.3403/day**.
- Power cost: Quebec Tier 2 $0.3194/day; Tier 1 $0.2025/day; US $0.7071/day.
- **Net/day: Quebec Tier 2 +$0.0209; Tier 1 +$0.1377; US -$0.3668.**
- Monthly net (Quebec Tier 2): +$0.63. Annual: +$7.61.
- Breakeven electricity price: $0.3403 / 4.104 kWh = **8.29¢ USD/kWh**.
Sensitivity (ESTIMATE): at 8,245 H/s gross is $0.2806/day, net at Tier 2
-$0.0389/day; at 12,445 H/s gross is $0.4235/day, net at Tier 2 +$0.1041/day.
The result straddles breakeven — the hashrate assumption decides the sign.
Notes: Monero is the ONLY network in this model that is near breakeven at
Quebec rates, and only because Quebec power is cheap and the pool fee is 0%.
At US average rates it loses money at every published hashrate.

## 5. KASPA (KAS) — kHeavyHash, GPU
Algorithm: kHeavyHash. GPU-mineable in principle, but the network is dominated
by kHeavyHash ASICs (IceRiver KS-series); a GPU is a rounding error.
Reference hardware: 1x NVIDIA GeForce RTX 3060 Ti.
- Hashrate **480 MH/s @ 100 W card — ASSUMPTION** (WhatToMine LHR 480 MH/s @
  100 W; asicprofit 491 MH/s @ 119 W; minerstat 491.3 MH/s @ 119 W).
  Wall power 150 W (100 + 50 system). 3.600 kWh/day.
Network (VERIFIED, two independent sources, 2026-11-18 ~00:56 EST):
- Network hashrate **313–317 PH/s**: api.kaspa.org /info/hashrate = 313,102
  TH/s (313.1 PH/s); 2Miners node networkhashps = 317,016,508,646,590,909 H/s
  (317.0 PH/s). Calculation uses 317.0 PH/s.
- Difficulty 31,344,111,208,331,531 (2Miners node). api.kaspa.org
  /info/difficulty returned "Not Found" — not available from that endpoint.
- Block reward **1.94454365 KAS/block — VERIFIED by two sources**:
  api.kaspa.org /info/blockreward AND 2Miners node blockReward 194,454,365
  sompis (1.94454365 KAS). Reward declines monthly (chromatic schedule).
- Block time 0.1 s (10 blocks/sec) → 864,000 blocks/day → daily emission
  1,680,086 KAS/day.
- Price **$0.02727563 USD** (CoinGecko, 2026-11-18; +1.02% 24 h).
  Market cap $757.4M (api.kaspa.org).
- Pool: 2Miners, 1% fee. Pool hashrate 3.96 PH/s, 714 miners.
Arithmetic (ESTIMATE):
- Share = 480,000,000 / 3.1702e17 = 1.5141e-9.
- Daily coins = 1.5141e-9 x 1,680,086 x (1 - 0.01) = **0.002518 KAS/day**.
- Gross revenue = 0.002518 x $0.02727563 = **$0.000069/day** (seven
  hundred-thousandths of a dollar — effectively zero).
- Power cost: Quebec Tier 2 $0.2802/day; Tier 1 $0.1777/day; US $0.6203/day.
- **Net/day: Quebec Tier 2 -$0.2801; Tier 1 -$0.1776; US -$0.6202.**
- Monthly net (Quebec Tier 2): -$8.40. Annual: -$102.25.
- Breakeven electricity price: ~$0.00002/kWh — no realistic power price
  makes this profitable.
Notes: independent calculators agree (asicprofit: KHeavyHash income $0.00/day;
WhatToMine 3060 Ti LHR on Kaspa: -$0.12/day at $0.05/kWh). GPU Kaspa mining
is effectively dead; the ASIC share of the network is the cause. A single GPU
is 1.5 billionths of the network.

## 6. RAVENCOIN (RVN) — KawPow, GPU
Algorithm: KawPow. Designed for general-purpose GPUs; ASIC-resistant by design.
Reference hardware: 1x NVIDIA GeForce RTX 3060 Ti.
- Hashrate **27 MH/s @ 190 W card — ASSUMPTION** (WhatToMine 27 MH/s @ 190 W;
  minerstat 29.63 MH/s @ 149 W tuned; asicprofit 30.5 MH/s @ 149 W).
  Wall power 240 W (190 + 50 system). 5.760 kWh/day.
- DAG size 6.25 GB (2Miners node dagSize 6,249,510,272) — needs an 8 GB+
  GPU; 6 GB cards cannot mine RVN.
Network (VERIFIED, two independent sources, 2026-11-18 ~00:56 EST):
- Network hashrate **534–552 GH/s**: 2Miners node networkhashps =
  533,882,597,021 H/s (533.9 GH/s); MoneroOcean difficulty 33,098,427,129,147
  / 60 s = 551.6 GH/s. Calculation uses 533.9 GH/s.
- Difficulty **33,098,427,129,147** (MoneroOcean network stats); height 4,630,530.
- Block reward **1,250 RVN/block — VERIFIED**: second halving Jan 15–18,
  2026 at block 4,200,000 cut the reward from 2,500 to 1,250 RVN (multiple
  2026 sources); MoneroOcean last-block value 1,250.05 RVN. Next halving at
  block 6,300,000 (~2030) cuts it to 625 RVN.
- Block time 60 s (2Miners measured avg 57.30 s) → 1,440 blocks/day →
  daily emission 1,800,000 RVN/day (matches published post-halving issuance).
- Price **$0.00110692 USD** (CoinGecko, 2026-11-18; +0.72% 24 h; down ~25%
  over the prior 30 days per CoinMarketCap data Nov 16, 2026).
- Pool: 2Miners, 1% fee. Pool hashrate 241.9 GH/s, 1,559 miners, min payout
  10 RVN.
Arithmetic (ESTIMATE):
- Share = 27,000,000 / 533,882,597,021 = 5.0573e-5.
- Daily coins = 5.0573e-5 x 1,800,000 x (1 - 0.01) = **90.12 RVN/day**.
- Gross revenue = 90.12 x $0.00110692 = **$0.0998/day**.
- Power cost: Quebec Tier 2 $0.4483/day; Tier 1 $0.2843/day; US $0.9924/day.
- **Net/day: Quebec Tier 2 -$0.3486; Tier 1 -$0.1845; US -$0.8927.**
- Monthly net (Quebec Tier 2): -$10.46. Annual: -$127.22.
- Breakeven electricity price: $0.0998 / 5.760 kWh = **1.73¢ USD/kWh**.
Notes (risks, VERIFIED): August 2026 consensus exploit forced a ~3-day chain
rollback (pools rebuilt from block 4,487,775; fix published as v4.8.0);
delistings by KuCoin (Oct 2026), Upbit and Bitvavo; network hashrate fell from
a published ~3.09 TH/s (April 2026) to ~0.54 TH/s measured live today — an
~82% decline. RVN is the weakest network in this model on both economics and
network health.

## 7. ERGO (ERG) — Autolykos v2, GPU (bonus third GPU network)
Algorithm: Autolykos v2. Memory-hard, GPU-mineable.
Reference hardware: 1x NVIDIA GeForce RTX 3060 Ti.
- Hashrate **137 MH/s @ 82 W card — VERIFIED** (asicprofit, Nov 18, 2026;
  benchmark sources hashrate.no / whattomine / minerstat / 2cryptocalc).
  Wall power 132 W (82 + 50 system). 3.168 kWh/day.
Network (VERIFIED, two independent sources, 2026-11-18 ~00:57 EST):
- Network hashrate **693–713 GH/s**: 2Miners node networkhashps =
  713,237,332,484 H/s (713.2 GH/s); MoneroOcean difficulty 69,338,556,006,399
  / 100 s = 693.4 GH/s. Calculation uses 713.2 GH/s.
- Difficulty **69,338,556,006,400** (identical in both sources); height 1,919,265.
- Block reward **3 ERG/block — VERIFIED**: Ergo explorer API
  (api.ergoplatform.com) shows minerReward 3,000,000,000 nanoERG on two
  consecutive blocks (1,919,263 and 1,919,264).
- Block time 97.22 s measured (2Miners avgBlockTime; nominal 120 s) →
  888.7 blocks/day → daily emission 2,666.1 ERG/day.
- Price **$0.205371 USD** (CoinGecko, 2026-11-18; +7.06% 24 h).
- Pool: 2Miners, 1% fee. Pool hashrate 254.7 GH/s, 291 miners.
Arithmetic (ESTIMATE):
- Share = 137,000,000 / 713,237,332,484 = 1.9208e-4.
- Daily coins = 1.9208e-4 x 2,666.1 x (1 - 0.01) = **0.5070 ERG/day**.
- Gross revenue = 0.5070 x $0.205371 = **$0.1041/day**.
- Power cost: Quebec Tier 2 $0.2466/day; Tier 1 $0.1563/day; US $0.5458/day.
- **Net/day: Quebec Tier 2 -$0.1424; Tier 1 -$0.0522; US -$0.4417.**
- Monthly net (Quebec Tier 2): -$4.27. Annual: -$51.99.
- Breakeven electricity price: $0.1041 / 3.168 kWh = **3.29¢ USD/kWh**.
Cross-check: asicprofit lists the same card on Autolykos/ERG at $0.11/day
income — matches this model's $0.1041/day gross. Notes: Ergo is the best of
the three GPU networks modeled, and it still loses money at every rate in
this model. Its block reward declines over time as emission runs down.

## 8. COMPARISON TABLE (one reference unit each, ESTIMATE)
| Network | Algo | Ref. hardware | Hashrate | Wall W | Gross $/day | Net $/day QC T2 | Net $/day QC T1 | Net $/day US | Breakeven ¢/kWh |
|---|---|---|---|---|---|---|---|---|---|
| XMR | RandomX | Ryzen 7 5800X | 10 kH/s | 171 | $0.3403 | **+$0.021** | +$0.138 | -$0.367 | 8.29 |
| KAS | kHeavyHash | RTX 3060 Ti | 480 MH/s | 150 | $0.0001 | -$0.280 | -$0.178 | -$0.620 | ~0.00 |
| RVN | KawPow | RTX 3060 Ti | 27 MH/s | 240 | $0.0998 | -$0.349 | -$0.185 | -$0.893 | 1.73 |
| ERG | Autolykos2 | RTX 3060 Ti | 137 MH/s | 132 | $0.1041 | -$0.142 | -$0.052 | -$0.442 | 3.29 |
All net figures are BEFORE hardware cost. Annual net at Quebec Tier 2:
XMR +$7.61; KAS -$102.25; RVN -$127.22; ERG -$51.99.

## 9. WHAT THE NUMBERS MEAN
1. Only Monero on a mid-range CPU is near breakeven, and only at Quebec
   residential rates — and only barely (+$0.02/day at Tier 2, +$0.14/day at
   Tier 1). The sign flips with the hashrate assumption (8,245 H/s loses
   money even at Tier 2). At US average rates Monero loses $0.37/day.
2. GPU mining of Kaspa, Ravencoin and Ergo loses money at ALL THREE rates
   in this model, including the cheapest Quebec tier. The GPU's revenue
   ($0.00–$0.10/day) does not cover its power at any realistic residential
   rate. Kaspa is the worst: the GPU earns $0.00007/day because ASICs own
   the network.
3. Hardware cost is excluded above, and it kills the one marginal case:
   a Ryzen 7 5800X system costs roughly $400–600 to build/buy; at +$7.61/year
   net (Quebec Tier 2) the payback is ~65 years. A used RTX 3060 Ti lists at
   ~$422 (asicprofit, Nov 18, 2026) and never pays back on KAS/RVN/ERG at
   these rates. No hardware purchase is justified by this model.
4. The same GPU earns far more on OTHER algorithms than on the three modeled
   GPU networks: asicprofit lists the RTX 3060 Ti's best algorithm as
   PearlHash (PRL, 59.6 TH/s @ 94 W, $1.16/day gross, Nov 18, 2026) — an
   observation, not a recommendation; algorithm selection matters more than
   the coin, and any future model must rank algorithms, not just coins.
5. Scale does not fix a negative unit margin: ten GPUs losing $0.28/day each
   lose $2.80/day. The only path to positive mining profit in this model is
   (a) cheaper power than Quebec Tier 2, (b) a much better hashrate-per-watt
   (newer CPU/GPU or ASIC), or (c) a much higher coin price — none of which
   exists today.
6. Ravencoin carries the most network risk (August 2026 exploit + rollback,
   delistings, ~82% hashrate decline since April 2026). Kaspa carries the
   most structural risk for GPUs (ASIC dominance + monthly reward decline).
   Monero carries the least structural risk (CPU-only, stable hashrate,
   0%-fee pools, no halving — tail emission is fixed at 0.6 XMR/block).

## 10. LIMITATIONS AND WHAT WOULD CHANGE THE ANSWER
- Prices move daily; a 2x XMR price would make the CPU case clearly positive
  at Quebec rates (+~$0.36/day at Tier 2), while a 2x KAS price would still
  leave GPU Kaspa at ~-$0.28/day. Re-run the model with live prices before
  any decision.
- Difficulty and network hashrate move with price and with ASIC deployment;
  the model is a snapshot of 2026-11-18, not a forecast.
- The 50 W system overhead and the reference hashrates are assumptions;
  measured hardware will differ. The XMR result is sensitive to the hashrate
  assumption (see §4 sensitivity).
- Pool fees, minimum payouts and payout delays are modeled only as the fee
  percentage; orphan/stale rates, pool luck and withdrawal fees are not
  modeled (they would make results slightly worse).
- Follow-ups NOT computed here (no verified data gathered in this session):
  higher-end CPUs (Ryzen 9 7950X, ~18–20 kH/s published), kHeavyHash ASICs
  (IceRiver KS-series — the hardware that actually mines Kaspa), and
  alternative algorithms (PearlHash, QPoW, ProgPow) where the same GPU earns
  more. Any of these needs its own verified data before it enters the model.

## 11. SOURCES (all fetched 2026-11-18)
Prices: CoinGecko simple/price + exchange_rates APIs
(api.coingecko.com/api/v3/simple/price, /exchange_rates).
Monero network + pool: MoneroOcean APIs (api.moneroocean.stream/pool/stats,
/network/stats) — difficulty, height, block value, pool hashrate, miners.
Kaspa network: api.kaspa.org /info/hashrate, /info/blockreward, /info/marketcap;
2Miners API (kas.2miners.com/api/stats) — networkhashps, difficulty,
blockReward, pool hashrate, miners.
Ravencoin network: 2Miners API (rvn.2miners.com/api/stats); MoneroOcean
network stats (difficulty, height, value); halving confirmed by
blockchainreporter.net, brefcrypto.com, theccpress.com, BTCC (Jan 15–18, 2026,
block 4,200,000, 2,500 → 1,250 RVN); exploit/rollback/delistings per
theccpress.com and blockchainreporter.net.
Ergo network: 2Miners API (erg.2miners.com/api/stats); Ergo explorer API
(api.ergoplatform.com/api/v1/blocks) — minerReward 3 ERG on blocks 1,919,263
and 1,919,264; MoneroOcean network stats (difficulty, height).
Pool fees: hashrate.no XMR pools (MoneroOcean 0.00%, 2Miners 1.00%);
2026 pool guides (bt-miners.com, blog.monerica.com).
Hardware benchmarks: XMRig public benchmark (via cloudminecrypto.com and
ypool.net, Ryzen 7 5800X 12,445 H/s); Kryptex (10,000 H/s @ 105 W);
cpumining.pro (8,245 H/s, 110 W CPU / 171 W wall); asicprofit.com
(11,100 H/s; RTX 3060 Ti per-algorithm table, Nov 18, 2026); WhatToMine RTX
3060 Ti pages (kHeavyHash 480 MH/s @ 100 W; KawPow 27 MH/s @ 190 W);
minerstat RTX 3060 Ti vs 4060 Ti comparison (KHeavyHash 491.3 MH/s @ 119 W;
KAWPOW 29.63 MH/s @ 149 W).
Electricity: Hydro-Québec electricity rates chart (hydroquebec.com) via search
(Rate D, April 1, 2026: 7.065¢ / 11.142¢ CAD/kWh, 46.154¢/day);
U.S. EIA Form EIA-861 final 2025 (17.23¢ USD/kWh) and EIA Short-Term Energy
Outlook Oct 2026 (18.21¢ projected 2026) via search.
