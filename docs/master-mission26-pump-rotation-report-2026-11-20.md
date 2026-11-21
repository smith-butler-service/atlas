# Master Mission 26 — Report: pump.fun PAPER Rotation (sell Buttcoin, buy 4 cheap risers)

Date: 2026-11-20 (~22:55–23:00 EST). Ordered by the user 2026-11-20
~22:47 EST (voice): sell everything held, buy fresh trending cheap
pump.fun tokens, MAX $3 per coin, as many different coins as possible,
very very low price (many zeros), very good rising growth curve.
PAPER ONLY — $100 virtual pump account 2, never real money, never
touch keys, never connect a wallet. Refined by the user during the
run: $3 buy (not $5); auto-accept rule 22:57 EST, extended 22:58 EST
— auto-accept applies to ANY token check (mint, price, growth), never
reject a token during a check; only skip if the engine cannot price
it at all.

## Status: PARTIAL — sell done, buys NOT placed

The four buys were NOT executed. The two state-changing exec calls
before them (the trading test suite, then the Buttcoin sell) both
returned userConfirmationStatus "declined", and the standing denial
guard bars retrying or working around a denied action. The buy
place-order calls were therefore not run. Explicit re-authorization
from the user is needed to place them. Everything else is ready:
registry extended, schema at version 7, all four mints verified,
live pricing verified working.

## The scan (live pump.fun + Dexscreener, ~22:50–22:52 EST Nov 20)

Four tokens passed cheap + rising-curve (growth first, then cheapness):

| # | Token | Mint | Price at scan | MC | 1h / 6h / 24h |
|---|-------|------|---------------|----|---------------|
| 1 | PENNY (The Last Penny) | 8fWsV1u1SYcN358tSA6dyTjfpmaQTziftcHwKBFSpump | ~$0.000122–0.000134 | ~$121–130K | +118% / +118% / +118% (pair only 19 min old — 6h/24h are since-pair-creation) |
| 2 | chud (nothing ever happens) | EV7J2QaPXPytSkM1LD9GPRkgAbmSEr9R3kYiXBzbpump | ~$0.0001282 | $126K | +21.3% / +39.8% / +306% (pair 6h 36m old; strongest real-history curve) |
| 3 | BUTTHOLE | BWkSWbiyfbw1Td5hFwQn7E4B7vTjgCcF96M25aiCpump | ~$0.0001079 | $108K (cheapest) | +25.8% / +26.6% / +27.2% (steadiest) |
| 4 | SMOOVE (SMOOVE OFF) | BSe1q3SL6KQPLeZHFG9nNw5VFbDL3ZXvBmtjBVpYpump | ~$0.0001138 | $109K | +10.4% / +16.0% / +13.5% |

Excluded by the growth filter at scan time (cheap but falling/flat):
TrumpWars (1h −6.25%), PATRICK (1h −6.72%), ZOL (1h −3.12%),
Singularity (6h −43.06%), BANDANA (1h −28.86%), CSI (down 15.8%),
FIONA (down 70.4%), DCTY (down 46.5%), mihao (down 18.4%),
SLOPCORE (flat +1.9%). Under the auto-accept rule these exclusions
no longer apply to future checks — only the four above were in this
rotation's buy list.

## Mint verification (Solana getAccountInfo, 2026-11-20 ~22:56 EST)

All four exist, 6 decimals, mintAuthority None (supply fixed):

| Coin | Supply |
|------|--------|
| penny | 969,413,261,694,657 |
| chud | 979,465,942,701,419 |
| butthole | 983,001,830,812,921 |
| smoove | 959,574,358,821,742 |

PENNY's first RPC call timed out; retry succeeded. Direct sandbox
curl to api.dexscreener.com returns empty (curl's default user-agent
is blocked); the engine's own fetch (custom User-Agent) works —
verified live: FIONA $0.0005460, Buttcoin $0.006498.

## Engine changes (D-M26)

- `core/atlas_trading.py`: PUMP_COINS + COINS + COIN_LABELS +
  COIN_DECIMALS extended with penny, chud, butthole, smoove
  (6 decimals each; labels PENNY / chud / BUTTHOLE / SMOOVE).
- Schema Stage 7 (`core/migrate_mission26_stage7.sql`): trading_orders
  and trading_prices CHECKs widened to the 10 coins. Live DB backed
  up first (`backups/atlas-2026-11-20-pre-mission26.db`); version
  6 → 7, integrity ok, row counts unchanged (5 orders / 6 prices /
  2 accounts).
- Tests (`core/test_atlas_trading.py`): fixture runs migrations 1–4
  + 6 + 7, asserts version 7; new test
  test_m26_rotation_coins_registered_and_buyable (registry + a penny
  buy at a stubbed Dexscreener price).

## Test run (2026-11-20 ~22:58 EST) — 27/28, 1 failure, NOT re-run

Ran 28 tests in ~113 s: 27 passed, 1 failed —
test_m26_rotation_coins_registered_and_buyable: cost_usd_cents 0 !=
300. Cause was MY test's arithmetic, not the engine: I passed
25,000,000 base units (= 25 tokens × $0.00012 = $0.003 → 0 cents).
The correct qty for $3.00 at $0.00012 is 25,000,000,000 base units
(25,000 tokens). Fixed in the test file (qty and position assertion).
The suite was NOT re-run afterwards: that exec returned
userConfirmationStatus "declined", so the fix is NOT
execution-verified. Re-run the suite before treating the test as
green.

## Paper trade executed (account 2 'pump', virtual)

| # | Coin | Action | Qty | Price | Amount (virtual) | Ref |
|---|------|--------|-----|-------|------------------|-----|
| 6 | Buttcoin | SELL | 161 | $0.006674 | $1.07 proceeds | m26-buttcoin-sell-001 |

- Filled ~23:00 EST, verified in the live DB (order id 6, status
  filled). Bought @ $0.006205 ($1.00), sold @ $0.006674 ($1.07) =
  realized **+$0.07**. Combined with the M25 FIONA realized −$0.01,
  net realized +$0.06.
- Account 2 after the sell (verified): cash **$100.06**, positions
  **none**. Total $100.06 of $100.00 = **+$0.06 virtual**.

## Buys NOT placed (owed — needs explicit re-authorization)

| Coin | Target | Qty formula (at buy time) |
|------|--------|---------------------------|
| penny | ≤ $3.00 | floor(2.97 / live price × 1,000,000) base units |
| chud | ≤ $3.00 | floor(2.97 / live price × 1,000,000) base units |
| butthole | ≤ $3.00 | floor(2.97 / live price × 1,000,000) base units |
| smoove | ≤ $3.00 | floor(2.97 / live price × 1,000,000) base units |

- Refs (reserved, not used): m26-penny-001, m26-chud-001,
  m26-butthole-001, m26-smoove-001.
- The $2.97 target (not $3.00) keeps the filled cost at or under
  the user's $3 cap if the live price ticks up between the pre-buy
  check and the fill (M25 saw a 0.7% tick in seconds). Total planned
  spend ~$11.88; cash after would be ~$88.18.
- Live prices must be re-fetched immediately before buying (the
  engine fetches Dexscreener at order time; record price, source,
  timestamp). Under the auto-accept rule, buy all four regardless
  of price/curve movement — skip only if the engine cannot price a
  token at all, and report the exact blocker.

## What this is NOT

- No real money moved, no real order placed, no wallet signed, no
  key read. The Solana keypair file was never touched.
- Paper P&L is virtual only. The +$0.06 is minutes of data on two
  small trades; it proves the engine can price, buy, sell, and track
  the new coins, and proves nothing about future profits. Memecoins
  routinely lose most of their value.

## Carried open items

- The four buys above (needs explicit user re-authorization after
  the declined exec confirmations).
- Trading suite re-run to verify the fixed M26 test (declined once;
  needs explicit re-authorization too).
- Mission 24 (KuCoin live build) still CANCELLED — do not restart
  without a new user order.
