# Master Mission 22 — Design: Paper-Trading Engine

Date: 2026-11-20 (22:30–23:30 UTC; 17:30–18:30 EST). Ordered by the user
2026-11-20 ~17:27 EST ("start the trading mission"). Auto-resumed per the
user's 2026-11-19 01:22 EST auto-accept order (Mission 21 complete).
Scope: design and build the ATLAS paper-trading engine (simulation-only
trading priced and executed against live market data with a paper
ledger), wired into the existing ATLAS core (config, SQLite DB,
coordinator decisions, diagnostics) the same way the mining /
profitability pieces are; carry the Mission 21 open items.

## Funding rule v2 (user order 2026-11-20 ~17:30 EST)

The project trading rule is now: **funding sources = (1) realized net
mining profits, (2) USDC deposits on Solana only.** Everything else stays
paper-only / $0 until the user authorizes otherwise. This supersedes the
v1 rule (mining profits only). Deposit network is Solana ONLY; deposit
token is USDC (SPL) ONLY — confirmed by the user 17:30 EST after the
token was held blank pending confirmation (17:28–17:29 EST). The
deposit address was provided during this mission via the Solana wallet
build the user ordered at ~17:32 EST ("build it" + "make that key
secure"): public address
`5HpcbrtF1Gy7Ee2cRPqowWRYKM5HG1CfT22idECuJ7Ln`, wired into the engine
(see D-M22-4). No address was invented — it came from the wallet the
user ordered built.

Current eligible capital is still **$0**: realized net mining profits
are $0 (mining disabled, confirmed earnings 0) and confirmed USDC
deposits are $0 (no address configured, no deposit recorded).

## D-M22-1 — Paper-only engine; funding rule enforced in code

- New module `core/atlas_trading.py`, stdlib only, same patterns as
  `atlas_profitability.py` / `atlas_rewards.py` (configs read fresh on
  every call, manual transactions, decisions logged with reasons).
- Mode is always `"paper"`. There is NO live mode in code: no exchange
  client, no API keys, no order submission to any venue, no wallet /
  key / seed handling of any kind.
- Paper accounts hold VIRTUAL funds only (`source='virtual-simulation'`,
  default $10,000 virtual = 1,000,000 USD cents, from
  `config/trading.json`). Virtual funds are labeled virtual at every
  layer (account rows, order rows, export, status output). They are not
  capital, cannot be withdrawn, cannot be converted, and cannot be
  counted as eligible capital. There is no code path from a virtual
  balance to eligible capital.
- `create_account` refuses any `source` other than
  `'virtual-simulation'` (TradingError + logged refusal).
- `eligible_capital_usd_cents()` reads `config/atlas.json`
  `trading.eligible_capital_usd` fresh (mining profits, $0) and adds
  SUM of confirmed USDC deposits from `trading_deposits` ($0). Both
  sources are named; any other source has no representation in code.
- `fund_from_capital` (CLI) always refuses: paper accounts are
  virtual-only by definition, and eligible capital can only fund live
  trading, which does not exist. The refusal is logged as a
  `trading-capital-funding-refused` decision naming the rule.
- `place_order` refuses any `mode != 'paper'` (defensive; only paper
  exists).

## D-M22-2 — Pricing: live CoinGecko, fetch-with-fallback, never fabricated

- Same four coins as profitability (XMR, KAS, RVN, ERG), CoinGecko
  `simple/price`, 10 s timeout, same validation (positive finite
  number only).
- Last recorded prices live in `trading_prices` (coin PK). A failed
  fetch falls back to the last recorded price, marked stale with the
  original `fetched_at` preserved — never re-stamped fresh. Prices
  older than 1 h are STALE (`price_stale_after_s = 3600`).
- An order with NO price at all (never fetched) is REJECTED with
  reason `no-live-price`. A stale price still executes but the order
  row carries `price_stale = 1` and the status output warns.
- Every filled order records `price_usd` (Decimal string, exact),
  `price_source`, `price_fetched_at`, `price_stale`.

## D-M22-3 — Money: integers only; positions and cash derived

- Cash is integer USD cents. Coin amounts are integer base units: XMR
  piconero (10^12), KAS/RVN/ERG 10^8 units.
- Order cost is computed with `Decimal` and rounded HALF_UP to integer
  cents: `cost_cents = qty_base * price_usd * 100 / 10^decimals`.
- Fee: `fee_bps` from `config/trading.json`, default 0 in v1 (no fee
  model invented). Fee is computed the same integer way and recorded
  per order.
- Positions and cash are DERIVED from filled orders only
  (`positions()`, `cash_balance_cents()`): cash = initial virtual −
  Σ buy costs − Σ fees + Σ sell proceeds; holdings per coin = Σ buys
  − Σ sells. Nothing is stored as a balance.
- Orders are append-only with idempotency: `UNIQUE(order_ref)` on
  `trading_orders`. Rejected orders are recorded too (status
  `rejected`, `reject_reason` set, cost NULL) so refusals are auditable.
- Order validation (each a refusal with reason, never an exception
  escaping as a fill): unknown account, inactive account, unknown coin,
  bad side, qty ≤ 0 or non-integer, buy exceeding virtual cash, sell
  exceeding holdings, no price, duplicate `order_ref`.

## D-M22-4 — Deposit slot: Solana only, USDC only, address empty

- New config `config/trading.json` (atlas.json is NOT touched — its
  sha stays `46d3d12c1b90`). Deposit block: network `"Solana"`, token
  `"USDC"`, token standard `"SPL"`, address `null`, status
  `"address-pending"`.
- `DEPOSIT_NETWORK = "Solana"` and `DEPOSIT_TOKEN = "USDC"` are hard
  constants. `load_trading_config()` rejects a config whose deposit
  network is not Solana or whose deposit token is not USDC — there is
  no parameter anywhere to select another network or token for
  deposits. No multi-chain deposit support exists, by design.
- `set_deposit_address(address)`: validates a Solana address (base58
  alphabet, decodes to exactly 32 bytes; implemented in stdlib, no
  external base58 library) and stores the receive-only address
  atomically; logs a `trading-deposit-address-set` decision (a receive
  address is public, safe to log). Called in this mission:
  2026-11-20 ~17:32 EST the user ordered the Solana wallet built and
  the key secured; the public address
  `5HpcbrtF1Gy7Ee2cRPqowWRYKM5HG1CfT22idECuJ7Ln` (USDC on Solana,
  SPL mint `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`) was wired
  into the engine via this function and verified by the engine's own
  validation. The keypair file
  (`config/wallet/solana-usdc-keypair.json`, mode 0600) is NEVER read,
  printed, copied, or logged by the trading engine or this mission —
  only the public address is used. This supersedes the old
  "no wallets/keys until treasury design approved" rule for this one
  deposit wallet only.
- `clear_deposit_address()`: clears the slot back to null, logs the
  decision. No key, seed phrase, or private key is accepted, stored,
  or handled anywhere in this module — the address is receive-only.
- Deposits do NOT fund trading automatically: the engine never
  watches the chain continuously and never credits a deposit on its
  own. Confirmed deposits are recorded ONLY through the explicit
  operator command `record-deposit` or the explicit on-demand
  `scan-deposits` check (D-M22-5), both bound to the configured
  address. Until the address exists and a deposit is recorded with
  a transaction signature as evidence, confirmed deposits are $0
  and eligible capital stays $0.

## D-M22-5 — Confirmed USDC deposits (the second funding source)

- Table `trading_deposits`: one row per confirmed deposit.
  `tx_signature` UNIQUE (a transaction counts once),
  `deposit_address` (the Solana address the transfer went to — must
  equal the configured deposit address), `amount_usdc_micro` integer
  (USDC has 6 decimals), `amount_usd_cents` integer (floored),
  `remainder_micro` (the sub-cent remainder, kept visible — never
  silently dropped), `confirmed_at`, `source` always `'solana-usdc'`,
  `status` always `'confirmed'`, `note`.
- `record_deposit(tx_signature, amount_usdc_micro, note=None)`:
  validates the signature (base58, decodes to exactly 64 bytes — the
  Solana transaction-signature shape), requires a positive amount,
  resolves the destination address from the configured deposit
  address (refuses when none is configured — a deposit cannot be
  recorded against an unconfigured address), converts to USD cents
  by flooring (`usd_cents = micro // 10000`, remainder kept in
  `remainder_micro` — real transfers can carry sub-cent amounts, so
  they are recorded with their remainder, not refused), refuses
  duplicates and non-positive amounts, logs a
  `trading-deposit-recorded` decision with the signature, address,
  and amount. The recording IS the confirmation: it is an explicit
  operator action with the transaction signature as evidence.
  Automatic on-chain verification is the scan below; a fully
  automatic treasury watcher is NOT built — it belongs to a future
  treasury design, which does not exist yet.
- `scan_deposits(con, limit=10)` — the engine side of the S.M.I.T.H.
  site's "Accept deposit" button (user order 2026-11-20 ~17:33 EST):
  queries the Solana public RPC for recent signatures for the
  configured deposit address (`getSignaturesForAddress`), fetches
  each unrecorded transaction parsed (`getTransaction`, jsonParsed),
  and sums the post-minus-pre token-balance delta for the USDC mint
  (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`) owned by the
  deposit address; a positive delta is recorded via `record_deposit`
  with the signature as evidence. Failed transactions and
  transactions with no USDC delta are skipped; an RPC failure
  returns an error summary and records nothing — never fabricates.
  CLI: `scan-deposits [--limit N]`. The scan only ever records
  deposits TO the configured address, Solana/USDC only; it takes no
  network/token arguments.
- `record_deposit` and `scan_deposits` take no network/token
  arguments: Solana/USDC is the only shape they can record. Any
  other chain or token has no representation in code and cannot be
  recorded.
- Recording a deposit does NOT authorize live trading with it. It
  only grows the eligible-capital figure. Live trading does not
  exist and is not authorized until the user says so.

## D-M22-6 — Schema: Stage 4 migration, user_version 5

- `core/migrate_mission22_stage4.sql`: creates `trading_accounts`,
  `trading_orders`, `trading_prices`, `trading_deposits`; sets
  `PRAGMA user_version = 5`. Applied to the live DB only after a
  backup (`backups/atlas-2026-11-20-pre-mission22.db`), integrity +
  version verified before and after, single transaction. Live ledger
  is 0 rows; the new tables start empty.
- Test fixtures build temp DBs from the pre-mission5 backup +
  migrations 1–4 and assert `user_version == 5`.

## D-M22-7 — Wiring into the core

- Decisions: dept `trading` — `trading-account-created`,
  `trading-order-filled`, `trading-order-rejected`,
  `trading-deposit-recorded`, `trading-deposit-address-set`,
  `trading-deposit-address-cleared`, `trading-capital-funding-refused`,
  `trading-export`.
- Export: `data/trading.json`, atomic write (temp + os.replace),
  same pattern as profitability/rewards: `mode`, `emergency_stop`,
  `eligible_capital_usd_cents` (+ its two named sources),
  `deposit` block (network/token/address/status), per-account virtual
  balances, positions, mark-to-market value with price freshness,
  recent orders, price table. `export` CLI + function.
- Diagnostics: new test 29 (`t29_trading_export`) — the export
  parses, is fresh, mode is paper-only, eligible capital is $0 with
  both sources named, deposit network is Solana / token USDC / address
  null-or-valid-Solana, no secret string appears in the file, derived
  cash reconciles to SUM over filled orders, and a seeded temp-DB
  paper trade (buy + sell at fixture prices) fills and reconciles.
  Suite becomes 29/29; tests 1–28 unchanged.
- Test suite: new `core/test_atlas_trading.py` (temp DBs only, never
  the live DB; live fetches never attempted except monkeypatched to
  fail). Target: existing 77/77 unchanged + new trading tests all
  passing.
- `atlas.json` is NOT modified. No coordinator code change: the
  coordinator's `decide()` already logs `stay-paper-only`; trading
  decisions are logged by the trading module itself.

## D-M22-8 — Carried open items (from Mission 21)

- **TOP OPEN ITEM (parent agent): rendered Mining-tab check** — still
  NOT established (19th mission). Needs a live-browser run through
  the parent's browser route; a subagent cannot run a live browser.
  Do not claim it established without a captured run that selects the
  Mining tab.
- **Re-file the three repair inspections** (Show-controls icon overlap
  at 390px; scale-table hiding workersWithShares/sharesPerWorker; orb
  label-pill overlap) — M21 dispatch was blocked ("subagent bootstrap
  is no longer authorized"); defects confirmed, repair authorization
  stands. This session's artifact namespace is likewise not loadable
  by a subagent; re-file from the parent route.
- **Daemon SIGTERM sender:** H1 ruled out, H2 confirmed as mechanism
  for the 2026-11-19 07:26:56 UTC single; sender unknown. M22
  re-derives the 24h startup count (first full post-fix day: fix
  ~05:44 UTC Nov 19; count now covers a full post-fix window).
- Live refresh-expiry observation: only observable during a host
  outage; do not stage one by breaking the host.
- M6 finding 1 reward display: re-test once the ledger has rows
  (ledger still 0 rows at M22 start).
- Carried decisions owed unchanged: MEM% alert re-scope,
  mempool.space label, Obj 2 coordinator, SupportXMR URL, referral
  5%, minimum payout, Gates 2/4, roadmap/GOAL.md bookkeeping,
  recovery.md corrections, RVN difficulty, refresh step-9 transform,
  tariff fetchedAt schema.
- Profitability-mirror lag fix proposal: still needs a job-body
  review (site mirror lagged twice on Nov 20 and needed manual
  re-ingest; host export itself is fresh).

## Gates (re-stated, all unchanged)

1. Measured browser hashrate — UNMEASURED.
2. Real pool shares — NOT TESTED (needs separate authorization).
3. Sustained run — NOT MEASURED.
4. Real payout — NOT TESTED (hard gate: explicit authorization +
   successful security testing + a treasury design, none exists).
5. Economics — only XMR on Ryzen 7 5800X barely breaks even
   (latest host diagnostics: XMR net −2e-06 XMR/day Tier 2 at
   $445.60, 13:52 EST Nov 20 — below breakeven at Tier 2; see report).

Launch verdict: NO-GO. Stop ON, simulation-only, $0 eligible capital,
no wallets/keys, no mining, no live trading, no real payouts, no spend.

## AUTO-RESUME

Mission 23 starts automatically after this one per the user's 01:22 EST
order (2026-11-19), unless the user orders otherwise.
