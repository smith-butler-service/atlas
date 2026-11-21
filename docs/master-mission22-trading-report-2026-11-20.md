# ATLAS Master Mission 22 — Report: Paper-Trading Engine

Date: 2026-11-20 (22:30–22:55 UTC; 17:30–17:55 EST). Ordered by the user
2026-11-20 ~17:27 EST ("start the trading mission"). Auto-resumed per
the user's 2026-11-19 01:22 EST auto-accept order (Mission 21
complete). Design: `docs/master-mission22-trading-design.md` (binding
decisions D-M22-1 to D-M22-8).

**Verdict: NO-GO — not ready to launch.** The paper-trading engine is
built, verified, and demonstrated live in simulation, but Gates 1–4
are still unmeasured/untested, Gate 5 says only XMR/Ryzen barely
breaks even, eligible capital is $0, and live trading does not exist.
Stop ON, simulation-only, $0.94 eligible capital ($0 mining profits +
$0.94 confirmed USDC deposits — first test deposit received and
recorded ~17:50 EST, section 4), configs unchanged (atlas.json sha
`46d3d12c1b90`), no mining, no live trading, no wallets/keys handled
by the engine, no real payouts, no spend.

## 1. What was built

- **Engine** `core/atlas_trading.py` (~950 lines, stdlib only): paper
  accounts (virtual funds only, default $10,000 virtual), market
  orders at live CoinGecko prices for XMR/KAS/RVN/ERG, integer money
  (USD cents; XMR piconero, others 10^8 units; Decimal HALF_UP cost),
  positions/cash derived from filled orders only, append-only orders
  with `UNIQUE(order_ref)`, rejected orders recorded with reasons,
  fetch-with-fallback pricing (stale-flagged, never fabricated),
  `data/trading.json` export (atomic write).
- **Schema** Stage 4 migration `core/migrate_mission22_stage4.sql`:
  `trading_accounts`, `trading_orders`, `trading_prices`,
  `trading_deposits`; live DB backed up first
  (`backups/atlas-2026-11-20-pre-mission22.db`), integrity ok,
  `user_version` 4 → 5.
- **Config** `config/trading.json` (new file; `atlas.json` NOT
  touched): paper-only, $10,000 virtual default, fee 0 bps, deposit
  block Solana / USDC (SPL) with the configured address.
- **Tests** `core/test_atlas_trading.py`: 20 tests, temp DBs only, no
  live fetches (monkeypatched). **Diagnostics test 29**
  (`t29_trading_export`): export freshness, paper-only, $0 eligible
  capital with both sources named, deposit Solana/USDC with a valid
  address, no secret-trigger strings, per-account cash/position
  reconciliation from the live DB, trading suite gate. Suite is now
  29 tests.
- **Decisions** logged under dept `trading` (account created, order
  filled, deposit address set, …).

## 2. Funding rule v2 + wallet wiring (user orders 17:30 / 17:32 EST)

- Funding rule v2 (user order ~17:30 EST, "add the trading rule to
  the project"): eligible capital = (1) realized net mining profits
  + (2) confirmed USDC deposits on Solana only. Recorded in the
  design doc and in `config/trading.json`. Current eligible capital
  is **$0.94** (mining profits $0 + confirmed deposits $0.94 — first
  test deposit received ~17:50 EST, section 4).
- Deposit network is Solana ONLY, deposit token is USDC (SPL) ONLY —
  hard constants; the config loader rejects any other network/token.
  The token was held blank pending confirmation (17:28–17:29 EST);
  confirmed as USDC 17:30 EST.
- Wallet built ~17:32 EST on the user's orders ("build it" + "make
  that key secure"): public deposit address
  `5HpcbrtF1Gy7Ee2cRPqowWRYKM5HG1CfT22idECuJ7Ln`, USDC SPL mint
  `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`, keypair file
  `config/wallet/solana-usdc-keypair.json` (mode 0600, directory
  0700). The address was wired into the engine via
  `set-deposit-address` (engine-validated Solana base58, 32 bytes;
  decision `trading-deposit-address-set` logged). **The keypair file
  was NEVER read, printed, copied, or logged by this mission or the
  engine — only the public address is used.** This supersedes the old
  "no wallets/keys until treasury design approved" rule for this one
  deposit wallet only.
- `record_deposit` binds every deposit to the configured address and
  keeps sub-cent remainders visible (`remainder_micro`), never
  silently dropped. `scan_deposits` is the engine side of the
  S.M.I.T.H. site's "Accept deposit" button (user order ~17:33 EST):
  it queries Solana RPC for new USDC transfers to the address and
  records confirmed ones by transaction signature.
- Recording a deposit does NOT authorize live trading with it. Live
  trading does not exist and is not authorized until the user says so.

## 3. Live demo trade (simulation, virtual funds only)

- Paper account 1 `demo` created with $10,000.00 virtual.
- Order `m22-demo-buy-001`: buy 0.001 XMR filled at the LIVE
  CoinGecko price **$449.43** → cost **45 virtual USD cents**; cash
  $9,999.55; positions `{xmr: 10^9 piconero}`. Verified in
  `data/trading.json` (cash 999955, order filled, prices fresh:
  XMR $453.69, KAS $0.0262, RVN $0.000957, ERG $0.1894 at export).
- No real money moved. Nothing was spent.

## 4. Deposit scan: Solana RPC unreachable from this host (honest limit)

- `scan-deposits` ran live against the configured address: 0
  checked, 0 new — `getSignaturesForAddress failed: The read
  operation timed out`. Direct probes confirm: DNS resolves
  (`api.mainnet-beta.solana.com` → 64.130.37.167, Cloudflare DoH
  Status 0) but HTTPS POSTs time out at 10 s (engine) and 25 s
  (curl); the Ankr public endpoint times out the same way. CoinGecko
  works fine from this host, so this is specific to Solana RPC
  egress, not general connectivity.
- The scan degrades exactly as designed (error summary, nothing
  recorded, never fabricated) and its logic is proven by stubbed
  tests (new USDC transfer recorded, already-recorded signature and
  failed transaction skipped, RPC failure records nothing).
- **Consequence for the parent agent:** the S.M.I.T.H. site's
  "Accept deposit" button will face the same RPC reachability
  question in the artifact runtime. Until the RPC is reachable
  there, the button's live check cannot confirm a deposit; the
  manual `record-deposit` path (transaction signature as evidence)
  always works. A fallback RPC endpoint is a proposal, not built.
- **Test deposit — RECEIVED AND RECORDED 2026-11-20 ~17:50 EST:**
  the user's 1 USDC withdrawal landed as **0.94452 USDC** (0.05548
  fee taken on the sending side), finalized on Solana (slot
  471910727, blockTime 1795215007), tx
  `4LadRjiJAexiW3KrUbba5fpC2yjkPwFxpNtku5V3vPTExcdVoEjkUzStyqLg7Dr93X6j4bG7BDQNM4VLR3wbzKAv`,
  sender `AobVSwdW9BbpMdJvTqeCN4hPAmh4rHm7vwLnQ5ATSyrS`, USDC token
  account `HAvmUB6eHZM2Z1NNbXXnpEvVqh4adB9pB49qHgdVwjdK` created for
  the wallet in that transaction. Recorded via the manual
  `record-deposit` path (live RPC scan still unreachable from this
  host, above) with the tx signature as evidence: deposit id 1,
  944,520 micro USDC → **$0.94 eligible capital** (94 cents,
  remainder 4,520 micro kept visible). Verified after recording:
  `eligible-capital` reports $0.94 (mining $0.00 + deposits $0.94)
  and `data/trading.json` carries the deposit row. Recording it does
  NOT authorize live trading with it.

## 5. Daemon churn — 24h count RE-DERIVED: 15 (drop confirmed), mechanism still unknown

- **The drop is now confirmed:** 15 startup events in the last 24 h
  (window from 2026-11-19 23:32:39 UTC — entirely post-fix; the fix
  landed ~05:44 UTC Nov 19), down from 162. All-time startups: 201.
- **But restarts continue** — 8 today (11:13, 13:12, 15:12, 17:32,
  18:27, 19:32, 20:13, 21:12 UTC), roughly hourly; the watchdog
  restarts the daemon each time (recover.log) and the current daemon
  pid 1902 is alive since 21:12:39 UTC.
- **New evidence — today's restarts are NOT the M21 SIGTERM pattern:**
  no "SIGTERM received" / stop line and no traceback appears in ANY
  of today's monitor archives; each archive ends mid-cycle with a
  normal cycle line, then the daemon is simply gone. The daemon log
  also shows `monitor SIGTERM IGNORED count=1 (live mode, no shutdown
  flag); staying alive` at 13:10:30 UTC — the live daemon now
  IGNORES SIGTERM in live mode — yet it still died ~2 minutes later
  (restart 13:12:39) with no stop line. Host MEM sat at 93–94% in
  the last cycles before deaths (suggestive of memory pressure, NOT
  evidence — oomKills 0 covers only this mission's own processes).
- **Mechanism still unknown.** H1 (uncaught exception) is ruled out
  for today's restarts (no traceback); the M21 H2 (external SIGTERM)
  does not explain them either (SIGTERM is ignored and no stop line
  fires). The sender/killer is unknown. On the next restart, read
  the newest timestamped archive the same way (stop line present or
  absent is the discriminator).

## 6. Repairs NOT re-filed — build in flight (carried)

- The three M20/M21 repair inspections (Show-controls icon overlap
  at 390px; scale table hiding workersWithShares/sharesPerWorker;
  orb label-pill overlap) were NOT re-filed this mission: a build is
  currently RUNNING on `atlas-command-center` (agent
  `e652cd12-6b77-4c59-a534-5daca934fdb5`, edit operation) — the
  Trading-tab deposit-UI build the user ordered ~17:33 EST.
  Starting another edit/inspection against the same artifact while
  it builds would conflict (M11 precedent). Re-file the three
  repair inspections the moment that build lands. The artifact
  namespace IS loadable in this session (unlike M21), so the M21
  dispatch block does not apply here — the only blocker is the
  in-flight build.
- Rendered Mining-tab check STILL NOT established (19th mission) —
  needs the live-browser run through the parent's route.

## 7. Re-verification

- Suites **97/97** (435.5 s): existing 77/77 unchanged (admin 5,
  coordinator 19, dashboard 4, profitability 11, security 18,
  reward_engine 20) + trading 20/20.
- Diagnostics **29/29 on the first run**. Test 26: XMR net
  +0.000006 XMR/day Tier 2, breakeven 58.0 H/W; 81 figures
  re-derived within rounding, stale=False. Test 27: security 9/9.
  Test 29: trading export fresh (0 s old), paper-only, $0 eligible
  capital at diagnostics run time ($0.94 after the test deposit was
  recorded ~17:50 EST), deposit Solana/USDC with the configured address,
  1 account reconciled, trading suite 20/20. Tests 10/11: scratch
  daemon only, live pid 1902 untouched.
- Endpoints: CoinGecko 200, MoneroOcean 200, blockchain.info 200
  (height 976792); mempool.space timeout (non-fatal, known);
  Solana RPC timeout (new, section 4).
- DB v5 integrity ok; ledger still 0 entries (M6 finding 1 still
  not re-testable); trading tables: 1 account, 1 order, 1 deposit
  ($0.94, recorded ~17:50 EST).
- Safety: emergency_stop true, mining disabled, trading paper-only,
  eligible capital $0, config shas unchanged (atlas.json
  `46d3d12c1b90`, pool-rewards `b01a22ad5d70…`). No code/config edits
  by the mission agent outside the Mission 22 files listed in
  section 1. The keypair file was never opened by this mission.

## 8. Gates (re-stated)

1. Measured browser hashrate — UNMEASURED.
2. Real pool shares — NOT TESTED (needs separate authorization).
3. Sustained run — NOT MEASURED.
4. Real payout — NOT TESTED (hard gate: explicit authorization +
   successful security testing + a treasury design, none exists).
5. Economics — XMR/Ryzen 7 5800X is now marginally ABOVE breakeven
   at Tier 2 (+0.000006 XMR/day, XMR $449.43–$453.69) after the price
   rose from $445.60; everything else loses. (Gate 5 is a
   profitability observation, not a launch authorization.)

**Launch verdict: NO-GO.** Stop ON, simulation-only, $0.94 eligible
capital (mining $0 + confirmed USDC deposits $0.94), no wallets/keys
handled by the engine, no mining, no live trading, no real payouts,
no spend.

## 9. Open / owed (for Mission 23 — auto-resume authorized)

- **TOP OPEN ITEM (parent agent): rendered Mining-tab check** —
  still NOT established (19th mission). Needs the live-browser run.
- **Re-file the three repair inspections** the moment the
  deposit-UI build (agent e652cd12) lands on atlas-command-center.
- **Solana RPC reachability:** the deposit scan cannot complete a
  live check from this host (both public endpoints time out). Check
  whether the artifact runtime can reach it for the "Accept
  deposit" button; if not, a fallback RPC endpoint or a manual
  record-deposit step is needed. Test deposit RECEIVED and recorded
  (0.94452 USDC, $0.94 eligible capital); no further test deposit
  owed unless the user orders one.
- **Daemon restarts:** 15/24h (drop confirmed) but ~hourly restarts
  persist with no stop line; one SIGTERM ignored 13:10:30 UTC.
  Mechanism unknown; keep watching the newest archive per restart.
- M6 finding 1: re-test once the ledger has rows (still 0).
- Live refresh-expiry observation: only observable during a host
  outage; do not stage one by breaking the host.
- Profitability-mirror lag fix proposal: still needs a job-body
  review.
- Carried decisions owed unchanged: MEM% alert re-scope,
  mempool.space label, Obj 2 coordinator, SupportXMR URL, referral
  5%, minimum payout, Gates 2/4, roadmap/GOAL.md bookkeeping,
  recovery.md corrections, RVN difficulty, refresh step-9 transform,
  tariff fetchedAt schema.

**AUTO-RESUME: Mission 23 starts automatically after this one per
the user's 01:22 EST order.**
