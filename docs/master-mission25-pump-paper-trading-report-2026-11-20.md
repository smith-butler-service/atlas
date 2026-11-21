# Master Mission 25 — Report: pump.fun PAPER Trading

Date: 2026-11-20 (~18:38–18:45 EST). Ordered by the user 2026-11-20
~18:37–18:38 EST (voice: "stop trading" then immediately reversed —
"start it... start on pump"). Mission 24 (KuCoin live build) was
CANCELLED at the stop order and is NOT restarted. This mission is
paper-only: read-only prices, simulated trades, NO real money, NO
keys, NO live orders, NO KuCoin work.

## What was built (D-M25)

- **Price source:** pump.fun has no API-key trading; the engine prices
  pump.fun tokens from Dexscreener's public token API (no key,
  read-only, `https://api.dexscreener.com/latest/dex/tokens/<mint>`).
  Verified live from the sandbox 2026-11-20 ~18:40 EST: FIONA
  $0.001165, Buttcoin $0.006207 (PumpSwap pairs, SOL quote). The
  pump.fun frontend API (`frontend-api.pump.fun`) returned empty from
  the sandbox — unreachable there — so Dexscreener is the route.
  pump.fun's own homepage (browser.open) returned live coin data and
  cross-checked the same coins/prices (FIONA $0.001195, Buttcoin
  $0.006272 on a ~9-min-old crawl at 23:29 UTC).
- **Coins:** FIONA (Fiona the Hippo,
  `B34nXKzCgsJb9ChLuSHPRpXLE3WFSWyeT8Cqkzzmpump`, ~$1.2M market cap,
  HOT on pump.fun) and Buttcoin
  (`Cm6fNnMk7NfzStP9CZpsQA2v3jjzbcYGAxdJySmHpump`, ~$6.27M market
  cap). Both mints verified on-chain via Solana `getAccountInfo`
  (exist, 6 decimals, supplies ~984.15B / ~999.73B). Both trade on
  PumpSwap (graduated from the pump.fun bonding curve) per Dexscreener.
- **Engine change (minimal):** `core/atlas_trading.py` — new
  `PUMP_COINS` map (symbol → mint), `DEXSCREENER_TOKEN_URL`,
  `_fetch_pump_price()` (first Solana pair whose base token is the
  mint; positive-finite validation, never fabricates), `get_price()`
  branches to Dexscreener for pump coins and CoinGecko for the four
  original coins; `COINS` / `COIN_LABELS` / `COIN_DECIMALS` extended
  (6 decimals for both pump coins). Export / mark-to-market iterate
  `COINS` generically, so pump positions value automatically.
- **Schema change (Stage 6, `core/migrate_mission25_stage6.sql`):**
  the Stage 4 CHECK constraints (`coin IN
  ('xmr','kas','rvn','erg')`) on `trading_orders` and
  `trading_prices` rejected the new coins, so both tables were rebuilt
  with the widened CHECK (identical columns/rows, indexes recreated).
  Live DB backed up first
  (`backups/atlas-2026-11-20-pre-mission25.db`); before: version 5,
  integrity ok, 2 orders / 4 prices / 2 deposits; after: version 6,
  integrity ok, same counts, same rows. Test fixture updated to run
  migrations 1–4 + 6 and assert version 6. Mission 24's Stage 5
  migration was NOT applied (cancelled mission).
- **Tests:** 2 new tests in `core/test_atlas_trading.py`
  (`test_pump_buy_fills_at_dexscreener_price`,
  `test_pump_price_failure_rejects_or_falls_back_stale`). Trading
  suite 27/27. Full suites after the change: trading 27/27, live,
  admin, coordinator, dashboard, profitability, security,
  reward_engine — all OK; diagnostics 29/29 PASS (run 2026-11-20
  ~18:44 EST).

## Budget (user orders, applied by the parent)

- Virtual budget is **$100 everywhere** (user order 2026-11-20
  ~18:41 EST, repeated twice). Demo account 1 initial cut $10,000 →
  $100 (past XMR buys still counted: cash $98.64, 0.003 XMR held).
- Pump account 2 'pump': $100.00 virtual. **All pump.fun paper buys
  are on account 2 only.**

## Paper trades (account 2 'pump', virtual)

Buy time: 2026-11-20 ~18:42:38 EST (export 1795218158 UTC).

| # | Coin | Qty | Buy price | Cost (virtual) | Ref |
|---|------|-----|-----------|----------------|-----|
| 3 | FIONA | 862 | $0.001168 | $1.01 | m25-fiona-001 |
| 4 | Buttcoin | 161 | $0.006205 | $1.00 | m25-buttcoin-001 |

- FIONA fill price $0.001168 is the live Dexscreener price at order
  time (it had ticked up from $0.001160 at the pre-buy check seconds
  earlier — memecoins move fast). Cost 101 virtual cents.
- Buttcoin fill $0.006205, cost 100 virtual cents.
- Total paper spend: $2.01 virtual. Account 2 cash after buys:
  $97.99 of $100.00. Demo account 1 untouched by this mission
  ($98.64 cash, 0.003 XMR).

## P&L — final check 2026-11-20 ~18:46 EST (buy ~18:42 EST)

Autopilot sell (PAPER AUTOPILOT RULE, user order 2026-11-20 ~18:44
EST — "paper-trade ALL tokens without asking; buy coins making
profit, sell when they drop"):

| # | Coin | Action | Qty | Price | Amount (virtual) | Ref |
|---|------|--------|-----|-------|------------------|-----|
| 5 | FIONA | SELL | 862 | $0.001155 | $1.00 proceeds | m25-fiona-sell-001 |

- FIONA at sell time: $0.001155, m5 -1.59%, h1 -5.02%, below the buy
  price — dropping on every timeframe, so the rule says sell. Sold.
- FIONA realized P&L: bought $1.01, sold $1.00 = **-$0.01**.
- Buttcoin: bought $0.006205, last price $0.006223 (h1 +3.12%, m5
  +0.31%) — rising, so the rule says hold. Unrealized value $1.00
  (161 × $0.006223 = $1.0019) vs $1.00 cost = **~$0.00**.
- Momentum check for a new buy (Dexscreener, ~18:45 EST): NIO h1
  -8.05% (dropping), DCTY h1 +7.96% but m5 -1.48% (fading), HOGE h1
  -4.1% / m5 +1.83% (mixed), mihao no Dexscreener data returned. No
  clean riser — **no new buy this run**. Buttcoin is the only clean
  riser and it is already held.
- Account 2 'pump' final: cash $98.99, holdings 161 Buttcoin
  (~$1.00), **total $99.99 of $100.00 = -$0.01 virtual**.

## Verdict: NOT making a profit so far — down 1 virtual cent

After ~4 minutes and $2.01 of paper trades, the pump account is at
$99.99 — essentially flat, 1 cent down. The autopilot rule did what
it says (sold the dropping coin, held the rising one), but this is
minutes of data on two $1 trades: it proves the engine can price,
buy, sell, and track pump.fun coins, and it proves nothing about
whether pump.fun paper trading can make money. Any profit claim
from this sample would be a lie. The rule stands for future runs:
keep paper-trading without asking, buy risers, sell droppers, paper
only, $100 pump account, never real money, never touch keys.

## What this is NOT

- No real money moved, no real order placed, no wallet signed, no
  key read. The Solana keypair file was never touched.
- The user's Pump wallet (Google login on pump.fun, $0.00) is
  separate from the ATLAS deposit wallet and plays no part here.
- Paper P&L is virtual only — it proves the engine can price and
  simulate pump.fun coins; it proves nothing about future real
  profits. Memecoins routinely lose most of their value; a paper
  gain over minutes is noise, not a strategy.

## Verification

- Trading suite 27/27; full suites (trading, live, admin,
  coordinator, dashboard, profitability, security, reward_engine)
  all OK; diagnostics 29/29 PASS (2026-11-20 ~18:44 EST).
- Live DB migration verified: version 5 → 6, integrity ok, row
  counts unchanged (2 orders / 4 prices / 2 deposits before, same
  after); backup `backups/atlas-2026-11-20-pre-mission25.db`.
- All three paper orders verified in the live DB with Dexscreener
  prices, timestamps, and costs (see tables above).
- Keypair file never touched; no real order, no real funds, no
  signing; Mission 24 untouched (still cancelled).
- [Diagnostics + full-suite result to be filled.]

## Carried open items (unchanged)

- Three M20/M21 repair inspections STILL BLOCKED (site build
  running); rendered Mining-tab check still not established;
  profitability-mirror lag fix review still owed; ledger still 0
  rows; daemon-churn mechanism still unknown.
- The site's accept-deposit scan still shows only deposit 1 (same
  blind spot Mission 24 was fixing in the engine; the engine-side
  fix exists in the M24 code/tests but the mission was cancelled
  before landing — NOT claimed as done here).
- Mission 24 (KuCoin live build) CANCELLED — do not restart without
  a new user order.
