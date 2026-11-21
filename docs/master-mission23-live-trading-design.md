# Master Mission 23 — Design: Live-Trading Path (KuCoin)

Date: 2026-11-20 (~18:00 EST). Ordered by the user 2026-11-20 ~17:59 EST
("Do live trading"), on top of the 2026-11-19 01:22 EST auto-resume order
(Mission 22 complete). Scope: research the live-trading venue, design the
live execution path and its gates, carry the Mission 22 open items. NO live
order is placed in this mission. NO exchange account is created, NO API keys
are requested or handled, NO funds are moved, NO code is changed. The design
below is approved-for-build only after the gates in D-M23-6 pass; the build
itself (new module, tests, diagnostics test 30) is a follow-on step.

## Funding rule v2 (unchanged)

Eligible capital = (1) realized net mining profits + (2) confirmed USDC
deposits on Solana only. Current eligible capital is **$0.94** (mining
$0.00 + first deposit 0.94452 USDC, recorded ~17:50 EST). A second
withdrawal (under $10) was sent by the user ~17:53 EST and has NOT landed
on-chain as of ~18:00 EST (only the first signature exists); a re-check
cron fires ~17:59 EST. Recording a deposit does NOT authorize live trading
with it — the user has now separately ordered live trading, which is what
this design answers.

## D-M23-1 — Venue: KuCoin (primary, only venue that fits)

Research (web, 2026-11-20 ~18:00 EST; verify on the exchange's own pages
before signup — listings and terms change):

| Exchange | XMR spot | KAS | RVN | ERG | Serves Quebec, Canada? | Verdict |
|---|---|---|---|---|---|---|
| KuCoin | Yes (XMR/USDT; ~55% of tracked XMR volume, ~$61M/24h) | Yes (KAS/USDT) | NO — delisted 8 Oct 2026 | Yes (ERG/USDT, thin ~$26K/24h) | YES — ToS restricts Ontario + BC only; Quebec not restricted | PRIMARY |
| Kraken | Yes, but XMR trading disabled for Canadian clients 2 Sep 2025 | Yes | Yes | No | Yes, but XMR is out | OUT for XMR |
| MEXC | Yes (XMR/USDT, XMR/USDC) | Yes | Yes | Yes | NO — Canada is a Prohibited Jurisdiction in its User Agreement | OUT |
| Gate.io | Futures only (no XMR spot) | Yes | Yes | Yes | NO — Canada restricted in ToS | OUT |
| Binance / OKX / Bybit / Bitget | Futures only or no XMR spot | varies | Yes | varies | NO — Canada restricted | OUT |
| Bitfinex | Yes (XMR/USD, BTC, USDT) | No | No | No | UNCERTAIN — lists Canada as prohibited in some sources; Ontario cut off Mar 2022; not CSA-registered, no FINTRAC entry | OUT (unverified + uncertain) |
| HTX | Yes | — | Yes | — | NOT VERIFIED for Canada in this mission | NOT RECOMMENDED |
| Poloniex | Yes, but XMR withdrawals off | — | — | — | NOT VERIFIED for Canada | NOT RECOMMENDED |

KuCoin facts (base tier VIP 0): spot fees 0.10% maker / 0.10% taker for
Class A pairs; Class B 0.20%, Class C 0.30% — **which class XMR/KAS/ERG
pairs sit in was NOT verified; check the pair's class on KuCoin's fee
page before the first order**. Minimum deposit $1; minimum trade ~$1;
XMR minimum order 0.001 XMR (~$0.46 at $456). Crypto deposits free.
USDC on Solana: withdrawal fee 1 USDC, minimum withdrawal 5 USDC. XMR
withdrawal fee 0.0025 XMR (~$1.13), minimum withdrawal 0.005 XMR
(~$2.28). 24h withdrawal limit at VIP 0 is 1,000,000 USDT. KYC is
required for verified/API use; no-KYC tier exists with limits, but API
trading is a verified-account activity. KuCoin is offshore (Seychelles,
Peken Global Limited), NOT registered with Canadian regulators; the
Ontario Securities Commission published an investor warning about it
(13 Jul 2022). The user lives in Quebec, which KuCoin's ToS does not
restrict — but there is no Canadian investor protection on this venue.
Do NOT use a VPN or a false province: KuCoin asks for proof of address
and freezes accounts that break its terms.

**RVN is deferred.** KuCoin delisted RVN on 8 October 2026 (confirmed by
two sources; no RVN market on KuCoin as of 5 Nov 2026). No Quebec-serving
venue for RVN was verified in this mission. Live trading starts with
XMR / KAS / ERG on KuCoin only. RVN rejoins only if a verified venue
appears — it is NOT traded through an unverified venue.

## D-M23-2 — Funding path (how real money reaches the venue)

1. USDC sits in the ATLAS Solana deposit wallet
   (`5HpcbrtF1Gy7Ee2cRPqowWRYKM5HG1CfT22idECuJ7Ln`) — receive-only.
2. The USER sends USDC from that wallet to his KuCoin USDC deposit
   address on the Solana network, using his own wallet app
   (Phantom/Solflare) after backing the keypair up there. **The engine
   never signs a Solana transaction and never reads the keypair file**
   (`config/wallet/solana-usdc-keypair.json` stays 0600, unread by any
   ATLAS code — same rule as Mission 22).
3. On KuCoin: convert USDC → USDT (USDC/USDT pair, 0.1% fee) — KuCoin
   lists XMR/USDT, KAS/USDT, ERG/USDT; an XMR/USDC pair was NOT
   verified, so the USDT conversion step is part of the path.
4. Trade spot only. No margin, no futures, no leverage — ever, in v1.

## D-M23-3 — Capital reality (honest gate)

- Now: $0.94 — **below KuCoin's $1 minimum deposit**. It cannot be
  deposited as-is.
- After the second (under-$10) deposit lands: roughly $6–$10 total.
  That clears the $1 minimum, but USDC/Solana withdrawals need ≥5 USDC,
  so funds are effectively locked in until the balance grows.
- At this size live trading is a **proof-of-system exercise, not a
  money-maker**: a $1 trade pays ~$0.001–0.003 in fees, while one XMR
  withdrawal costs ~$1.13. Real trading needs $50–$100+ to be
  meaningful. Gate G3 (below) sets the floor at $10 total eligible
  capital before the first live order, and the first order is capped
  at $5.

## D-M23-4 — Live module: `core/atlas_live.py` (new, stdlib only)

- KuCoin REST client using `urllib` only (same stdlib-only rule as
  `atlas_trading.py`): HMAC-SHA256 request signing, API key + secret +
  passphrase, millisecond timestamp, `KC-API-KEY` / `KC-API-SIGN` /
  `KC-API-TIMESTAMP` / `KC-API-PASSPHRASE` headers.
- Endpoints in v1: `GET /api/v1/accounts` (balances),
  `POST /api/v1/orders` (place market order),
  `GET /api/v1/orders/{orderId}` (status),
  `GET /api/v1/fills` (fills for reconciliation).
- **There is NO withdraw function in the module — withdrawals can never
  be placed by code.** Moving funds off the exchange is always the
  user's manual action in the exchange UI.
- Market orders only in v1 (limit orders are a v2 proposal, not built).
- Prices: exchange ticker first, CoinGecko fallback (same
  fetch-with-fallback, never-fabricated rule as D-M22-2); an order with
  no fresh price is refused.
- Money: same integer discipline as D-M22-3 (USD cents; XMR piconero,
  KAS/ERG 10^8 units; Decimal HALF_UP).

## D-M23-5 — Config: `config/live_trading.json` (new file)

`atlas.json` and `config/trading.json` are NOT touched. New file holds:
`exchange: "kucoin"`, `enabled: false` (default; only the user enables
it), `allowed_pairs: ["XMR/USDT", "KAS/USDT", "ERG/USDT"]`,
`per_order_cap_usd_cents: 500` ($5), `daily_loss_limit_usd_cents`,
`min_capital_usd_cents: 1000` ($10), `mode: "live-gated"`. No secret of
any kind lives in this file or any config file.

## D-M23-6 — Gates in code (all must pass or the order is refused)

`place_live_order` refuses (logged refusal, no order) unless ALL hold:
1. `live_trading.json` `enabled` is true (user-enabled, explicit).
2. Emergency stop is OFF (`atlas.json` `emergency_stop` false).
3. Eligible capital ≥ $10 (min capital gate).
4. Order size ≤ $5 per-order cap.
5. Daily loss limit not breached.
6. Pair is in `allowed_pairs` (spot only; RVN is not allowed).
7. Price is fresh (exchange ticker or CoinGecko < 1 h old).
8. API credentials are present (from the Secure Vault via environment,
   never from a file).
- The coordinator keeps logging `stay-paper-only` until the user
  enables live; enabling live does NOT touch mining (mining stays
  disabled, stop stays ON for mining).
- Kill-switch: setting `emergency_stop` true refuses live orders
  immediately; a `live-disable` CLI command flips `enabled` false.

## D-M23-7 — Live ledger (Stage 5 migration, `user_version` 6)

New tables `live_orders`, `live_fills`, `live_balances_snapshot`,
append-only with `UNIQUE(client_order_id)`. After every fill, the
module fetches exchange balances and reconciles them against the
internal ledger; a mismatch halts live trading and logs an alert
decision. Live rows are kept strictly separate from the paper tables
(`trading_*`) — paper and live never share a balance.

## D-M23-8 — Secrets (hard rules)

- API keys are created by the USER on his own device, in his KuCoin
  account: **trade-only permissions, withdrawals DISABLED on the key,
  IP whitelist set**.
- Keys reach the engine ONLY through Muse's Secure Vault (environment
  at run time). They are NEVER typed in chat, NEVER written in code,
  config, logs, memory, or any file.
- Any suspected exposure → rotate the key immediately and re-issue.
- KuCoin sandbox availability for pre-live testing was NOT verified in
  this mission — verify before claiming a sandbox run; the mocked-HTTP
  test suite is the guaranteed pre-live check.

## D-M23-9 — Test plan + first live order protocol

- New suite `core/test_atlas_live.py` (temp DBs, mocked HTTP only):
  signing vector, order placement, every refusal gate in D-M23-6,
  reconciliation mismatch halts trading, no-withdraw-function proof
  (no withdraw endpoint string in the module).
- New diagnostics test 30 (`t30_live_export`): live config parses,
  `enabled` false by default, no secret string in any export, paper
  tables untouched by live code paths.
- **First live order protocol:** the user confirms in chat the exact
  coin, side, size, and max price; ONE tiny order only (e.g. 0.002 XMR
  ≈ $0.91 at $456); verify the fill and the balances on KuCoin;
  then STOP and report before any second order.

## D-M23-10 — Carried open items (scoped, not resolved here)

- **Three M20/M21 repair inspections — STILL BLOCKED, not filed:**
  (1) Show-controls icon overlaps the "Ring 2 — Mining" pill at 390px;
  (2) scale table shows 8 columns, hides workersWithShares /
  sharesPerWorker; (3) floating orb label pills overlap the legend row
  at 390px. A build IS running on `atlas-command-center` (agent
  `1dbcf6c7-a84e-48da-904e-c1f30d1654be`, edit operation — the
  voice-button repair inspection dispatched ~17:52 EST). One artifact
  build at a time: file the three inspections the moment it lands.
  Parent route files them; do not dispatch from a subagent while a
  build runs.
- **Rendered Mining-tab check — STILL NOT established (20th mission).**
  Needs the live-browser run through the parent's route; a subagent
  cannot run a live browser.
- **Daemon churn:** pid 1902 alive since 21:12:39 UTC (~1h50m at
  mission check — longer than the ~hourly restart pattern);
  recover.log shows no-op every 5 min through 22:57 UTC; newest
  monitor archive (211239) ends mid-cycle 21:10:34 UTC with mem
  93–94%, no stop line, no traceback — same pattern as M22.
  Mechanism still unknown; 24h startup count re-derivation is owed
  next mission. MEM 93–94% before deaths remains suggestive only.
- **Profitability-mirror lag fix proposal:** still needs a job-body
  review. Its exact file was NOT located in this mission (GOAL.md
  carries the line; the proposal text was not re-established from the
  docs/crons searched). The review is owed; the parent should point
  at the job body directly.
- **Ledger still 0 rows** (verified this mission) — M6 finding 1 still
  not re-testable.
- Carried decisions owed unchanged: MEM% alert re-scope, mempool.space
  label, Obj 2 coordinator, SupportXMR URL, referral 5%, minimum
  payout, Gates 2/4, roadmap/GOAL.md bookkeeping, recovery.md
  corrections, RVN difficulty, refresh step-9 transform, tariff
  fetchedAt schema.

## Gates (re-stated)

1. Measured browser hashrate — UNMEASURED.
2. Real pool shares — NOT TESTED (needs separate authorization).
3. Sustained run — NOT MEASURED.
4. Real payout — NOT TESTED (hard gate: explicit authorization +
   successful security testing + a treasury design, none exists).
5. Economics — XMR/Ryzen 7 5800X marginally above breakeven at Tier 2
   (+0.000006 XMR/day, XMR $449.43–$456.07 live CoinGecko Nov 20).
   (Gate 5 is a profitability observation, not a launch
   authorization.)

**Launch verdict for LIVE trading: NOT READY — design only.** The
paper engine runs; the live path is designed but NOT built, and no
live order can be placed until gates G1–G8 (report section 5) pass.
Stop ON, mining disabled, no spend, no keys handled.
