# GPU Mining Services — Research Record

Researched 2026-11-19 ~13:52 EST at user order (voice call). Research only — no sign-ups, purchases, contacts, or accounts created. ATLAS mining stays DISABLED (emergency stop on). Do NOT act on this without a separate user order.

## The Monero fact first

**None of these services mine Monero.** Monero uses RandomX, which is CPU-mined — GPUs cannot mine it. A GPU only mines GPU coins: Ravencoin (KawPow), Ethereum Classic (Ethash), Kaspa (kHeavyHash), Zcash (Equihash), Ergo (Autolykos). For Monero specifically, the only honest route is buying RandomX **CPU** hashrate on NiceHash or MiningRigRentals. Every verdict below comes from the provider's own terms as read 2026-11-19; where terms are silent, the verdict is UNCLEAR, not allowed.

## NVIDIA Cloud — the direct answer

**NVIDIA DGX Cloud: BANNED, and it has no 4090/5090.** DGX Cloud Agreement §9.8 (and NVIDIA Cloud Agreement cl. 9): "Customer may not use the [NVIDIA DGX Cloud / Cloud Service] for crypto mining, or operating a coin service, exchange or other service for the purposes of generating, distributing, or transacting in digital currencies." Enterprise-only, subscription per node, datacenter GPUs only (A100/H100/B200, via AWS, Google Cloud, Azure, Oracle). GeForce NOW Terms §3.2 also bans crypto mining. **The RTX 4090/5090 cards live on marketplaces, not on NVIDIA's own cloud.**

## GPU rentals and marketplaces

| Service | GPUs / cheapest usable | $/GPU-hr (cheapest) | Mining verdict per own terms | Notes |
|---|---|---|---|---|
| Vast.ai | RTX 3090/4090/5090, H100 etc. | ~$0.067/hr cheapest; RTX 3090 ~$0.19/hr | **BANNED** — Terms of Use v.1 Sep 2026, cl. 22: "you may not engage in any cryptocurrency mining, including but not limited to Bitcoin mining, Ethereum mining" | Card-funded credits; crypto-funded credits a grey area the clause doesn't cover |
| RunPod | RTX 4090/5090, A5000, H100 | 4090 Community $0.34/hr, Secure $0.74–0.89/hr; 5090 Community $0.69/hr, Secure $0.99–1.19/hr | **UNCLEAR** — ToS (updated 2026-03-24, read in full) never mentions cryptocurrency mining; only "mining" hit is "data mining" in the anti-scraping clause | Community hosts set own rules; "Compute Supplemental Terms" referenced but not published anywhere found; aggregators assert a RunPod ban — not RunPod's own words |
| Akash Network | RTX 3090/4090/5090, RTX Pro 6000, A100/H100 | RTX 3090 $0.09–0.17/hr; RTX 5090 $0.58/hr avg | **UNCLEAR** — both ToS docs silent: Network ToS (Jul 1, 2025) only mentions "majority mining / mining attacks" (51% attacks); Homenode ToS (Aug 7, 2026) §4.2 prohibited list has no mining | Providers are third parties — individual provider rules may differ; thin supply (334 GPUs, 58 providers, Q1 2026); $0.50 min card deposit, no KYC for deployment |
| SaladCloud | RTX 4090/5090 + consumer GPUs | 4090 $0.33/hr High, $0.16 batch; 5090 $0.50/hr High, $0.25 batch | **UNCLEAR** — ToS (updated Sep 29, 2026, read in full) has zero "mining" hits; only "crypto" hit is crypto payment | Salad itself runs miners (XMRig, Rigel, T-Rex, lolMiner, GMiner, miniZ, TeamRedMiner) as a backup workload on hosts' PCs — but as a buyer you rent containers and cannot point them at your own pool or pick a coin. Not a mining route |
| **GPU Cloud HQ** | RTX 4090/5090, H100/H200/B200/B300, RTX PRO | 4090 $189/mo ($0.26/hr eff.); 5090 $279/mo ($0.38/hr eff.) | **ALLOWED WITH ADVANCE NOTICE** — AUP v1.0, Oct 16, 2026: "Cryptocurrency mining is permitted on workstation-class GPUs if you tell us in advance, because of its power profile" | **Only explicitly-allowed rental found.** Dedicated bare-metal, monthly billing (30-day cancel notice), crypto payment only (BTC/ETH/USDT), no KYC, small/new vendor |
| Novita AI | RTX 4090/5090, L40S, RTX 6000 Ada, H100 | 4090 $0.33/hr on-demand, $0.17/hr spot; 5090 $0.56/hr | **BANNED** — Acceptable Use Policy, eff. Aug 5, 2026, §6 "CRYPTOCURRENCY MINING AND COMPUTE ABUSE": "You may not use the Services for: (1) Any form of cryptocurrency mining, including but not limited to Bitcoin, Ethereum, or any other digital currency or token mining" | $100 sandbox credits are CPU/RAM only; min top-up >$10, Stripe only, no crypto payments; no free GPU plan |
| Genesis Cloud | RTX 4090, L40S, H100 SXM | 4090 $0.55/hr; H100 SXM $2.59/hr; L40S $0.95/hr (Ginkgo registry snapshot Oct 19, 2026) | **UNCLEAR** — ToS (copy crawled Mar 2026) has zero "mining" hits; AUP not retrieved | Per-second billing, 1-min minimum; not the same company as "Genesis Mining" cloud-mining — do not conflate |
| CUDO Compute | 7 GPU models (H100, A100 etc.) | H100 SXM ~$2.45/hr (comparison source); own pricing quote-only / login-gated | **UNCLEAR** — no mining clause retrieved; GPU hourly pricing not public | Enterprise, quote-based; CudoMiner (desktop mining software on your own hardware) is a separate product, effectively frozen since 2022 |
| io.net | H100/A100 clusters (no 4090/5090 listed) | No public per-GPU table; 8× H100 SXM $28–32/hr (~$3.50–4.00/GPU-hr); 8× A100 80GB $18–22/hr | **UNCLEAR** — ToS (eff. Sep 21, 2026) §3.2 excerpt shows no crypto-mining clause; a third-party page says workers can be blocked for "mining" — unresolved | IO Credits $1 each; card or crypto (USDC/USDT/ETH/BTC/IO); KYC undocumented |
| CoreWeave | H100/B200 enterprise only | Enterprise pricing, not retail | **PERMISSION-GATED** — AUP (Sep 17, 2021): "Mining of Cryptocurrencies: Mining any cryptocurrency without explicit written permission" | No 4090/5090 consumer cards |
| Lambda | Datacenter GPUs | Cheapest ~$0.69/GPU-hr | **BANNED** — ToS/AUP: "You shall not use the Services in support of mining of cryptocurrency including but not limited to BitCoin" | |
| Hostinger | RTX 4090/5090 | 4090 $0.42/hr; 5090 $0.64/hr on-demand | **BANNED** — crypto miners banned (verified earlier) | |
| iRender | RTX cards (render farm) | Not retrieved | **PERMISSION-GATED** — Terms: "The use of the Service for mining cryptocurrencies and cracking passwords is prohibited… only allowed for authorized users who have received prior written consent directly from iRender.net" | |
| Anor Cloud | GPU cloud | Not retrieved | **PERMISSION-GATED** — bans mining "without explicit written permission" | |
| TensorDock | Was a cheap crypto-friendly marketplace | — | **DEAD — verdict moot.** Absorbed into Voltage Park; public hostnode feed empty; 2026 reports of failed VMs, ghost billing, no support; AUP URL now 404s | |
| GPUhub / Database Mart | RTX 4090/5090 | GPUhub 4090 $0.46/hr, 5090 $0.52/hr; Database Mart 4090 $0.51/hr, 5090 $0.58/hr (24-mo reserved) | **UNCLEAR** — comparator prices only; mining clauses not retrieved | |
| E2E (India) | GPUs from ₹49/hr | From ₹49/hr | **UNCLEAR** — mining clause unknown, not re-verified | Carried from Round 2 |
| Oracle | A1 ARM / AMD CPU only (no GPU in free tier) | $0 Always Free; A10 GPU $2.00/GPU-hr | **BANNED** — Cloud Services Agreement §1.3(d) prohibits use "to perform cyber currency or crypto currency mining" | Research only for Smith Research |
| Hetzner / Modal / dstack / Verlex | — | — | **BANNED** (dstack: "expressly prohibited"; Verlex: "strictly prohibited") | Verified earlier |

## Free GPU routes — all banned, none usable for mining

| Route | Free GPU | Verdict |
|---|---|---|
| Google Colab | Free T4, 12-hr sessions | **BANNED** — official FAQ bars mining on all managed runtimes; account termination without warning |
| Kaggle | ~30 GPU-hrs/week, 2× T4 (P100 retired Sep 15, 2026) | **BANNED** — Terms of Use §4.7: "Engages in cryptomining" |
| Databricks Free Edition | Limited serverless GPUs, fair-use quota unpublished | **BANNED** — Free Edition AUP, Prohibited Use 7: "for cryptomining or any similar activity" |
| marimo molab | Free GPU notebooks, RTX Pro 6000 Blackwell 96 GB, 4 CPU/32 GB, 12-hr sessions | **BANNED** — restrictions page (updated June 24, 2026): "mining cryptocurrency" is listed as abuse, account banned without notice |

**No free GPU route allows mining. Verified.**

## Hash-power marketplaces — the Monero-relevant ones (different model: you rent hash power, not a GPU)

| Service | Model | Price (live 2026-11-19) | Mining verdict |
|---|---|---|---|
| NiceHash | Hashrate marketplace — buyers rent hash power, sellers supply it; NiceHash owns no mining equipment | Min order 0.001 BTC (~$65–76). KawPow (Ravencoin) 1 TH/day ~0.058–0.062 BTC (~$4,000–4,600); Scrypt 1 TH/day ~0.0048 BTC (~$333) | **ALLOWED — mining is the entire business. RandomX/Monero IS a supported algorithm** (buying guide lists Monero–RandomX; pools publish NiceHash-compatible RandomX ports) — but that hashrate is CPU hashrate from sellers, not GPU |
| MiningRigRentals | P2P fixed-term rig rentals, ~60 algorithms incl. RandomX, KHeavyHash, KawPow | RandomX 61,212 sat/MH/day ≈ $39.05/MH/day; KHeavyHash 430 sat/TH/day ≈ $0.27/TH/day; 3% renter fee; ~55% of listed rigs idle | **ALLOWED — mining is the entire business** |
| Hiveon | **Not a rental.** Mining OS + mining pool (ETC/RVN, PPS+) | Hiveon OS: first 2 workers free; GPU rig $0.50–$3.00/mo by card count. Hiveon RVN pool ~264–320 GH/s (KawPow), RVN ~$0.0056–0.0058 | N/A — no GPU/rig rental offer exists; it is the pool/OS you would point rented hardware at |

## Profitability honesty

Renting retail GPU time to mine almost never pays — retail markup on hardware/electricity to earn a wholesale return; marketplaces price at or above what the hashrate earns (MRR RandomX +16.9% above pool rate; NiceHash SHA-256 averaged −3.7% vs hashprice over 60 days, i.e. buyers roughly break even before fees).

## Bottom line

**None of them mine Monero — Monero is CPU-only (RandomX), so every GPU option above is irrelevant to ATLAS as it stands, and the only honest Monero route is buying RandomX CPU hashrate on NiceHash or MiningRigRentals.** If a GPU coin were ever authorized, the best two options are (1) **GPU Cloud HQ** — the only rental with an explicit written allow (mining permitted on workstation GPUs with advance notice), RTX 4090 at $189/mo ($0.26/hr effective); and (2) **Akash** — the cheapest raw GPU (RTX 3090 $0.09–0.17/hr, RTX 5090 $0.58/hr) with no central mining ban found in either of its ToS documents, but the verdict is UNCLEAR with provider-level risk and thin supply, so acceptance would need verifying before spending anything. NVIDIA's own cloud is a dead end for this: DGX Cloud bans mining, is enterprise-only, and has no RTX 4090/5090 at all — those cards live on Vast.ai (banned), RunPod (unclear), Akash (unclear), SaladCloud (unclear), Novita (banned), GPU Cloud HQ (allowed with notice), and Genesis Cloud (unclear).

Sources read 2026-11-19: vast.ai/terms; runpod.io/legal/terms-of-service; console.akash.network/terms-of-service; homenode.akash.network/terms-of-service; salad.com/terms/saladcloud; gpucloudhq.com (AUP + pricing pages); novita.ai/legal/acceptable-use-policy; genesiscloud.com/legal/terms-of-service; cudocompute.com; io.net/terms; irendering.net/terms-conditions; molab.marimo.io/pages/molab/restrictions; hiveon.com; nicehash.com/marketplace + buying guide; minercompare.com MRR calculator; kaggle.com/terms §4.7; research.google.com/colaboratory/faq.html; databricks.com/legal/acceptable-use-policy-fe; getdeploying.com comparator prices; ginkgoprotocol.org GPU price registry (Oct 19, 2026 snapshot).
