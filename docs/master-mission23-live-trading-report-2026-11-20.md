# ATLAS Master Mission 23 — Report: Live-Trading Path (Design Only)

Date: 2026-11-20 (~18:00 EST). Ordered by the user 2026-11-20 ~17:59 EST
("Do live trading"). Auto-resumed per the user's 2026-11-19 01:22 EST
order (Mission 22 complete). Design:
`docs/master-mission23-live-trading-design.md` (binding decisions
D-M23-1 to D-M23-10).

**Verdict: NOT READY for live trading — design only, nothing placed.**
The live path is researched and designed, but no live code exists, no
exchange account exists, no API keys exist, and no live order can be
placed until the gates in section 5 pass. Paper trading continues
separately (demo account holds 0.003 XMR after the parent's paper buy
`m22-start-001`: 0.002 XMR at live $456.07, 91 virtual cents). Stop ON,
mining disabled, no spend, no keys handled.

## 1. What was done

- **Exchange research (web, 2026-11-20 ~18:00 EST):** every venue
  checked for XMR/KAS/RVN/ERG spot listings, minimums, fees, and
  Canada/Quebec access. Full table in the design doc (D-M23-1).
- **Recommendation: KuCoin, primary and only venue.** It is the only
  exchange that (a) accepts Quebec residents per its own ToS
  (restricts Ontario + BC only), and (b) lists XMR spot (XMR/USDT,
  ~55% of tracked XMR volume), KAS/USDT, and ERG/USDT. Spot fees
  0.10%/0.10% base (Class A); Class B 0.20%, Class C 0.30% — the
  class of the XMR/KAS/ERG pairs was NOT verified, check before the
  first order. Minimum deposit $1; minimum trade ~$1; XMR minimum
  order 0.001 XMR (~$0.46). USDC/Solana deposits free; USDC/Solana
  withdrawal 1 USDC fee, 5 USDC minimum; XMR withdrawal 0.0025 XMR
  fee (~$1.13), 0.005 XMR minimum (~$2.28).
- **Kraken is OUT for XMR in Canada:** XMR trading disabled for
  Canadian clients 2 Sep 2025 (Kraken's own notice). Kraken lists
  KAS/RVN for Canadians, but that does not serve the XMR-first plan.
- **MEXC, Gate.io, Binance, OKX, Bybit, Bitget: OUT** — Canada is
  restricted in their terms (MEXC names Canada a Prohibited
  Jurisdiction in its User Agreement; Gate.io's ToS lists Canada).
  Gate/Binance/Bybit/Bitget have no XMR spot anyway (futures only).
- **Bitfinex: OUT (uncertain + unverified)** — lists XMR but multiple
  sources list Canada as prohibited / Ontario cut off Mar 2022, and
  it is not CSA-registered with no FINTRAC entry.
- **RVN is deferred:** KuCoin delisted RVN on 8 October 2026
  (confirmed by two sources; no RVN market on KuCoin as of 5 Nov
  2026). No Quebec-serving venue for RVN was verified. Live trading
  starts with XMR/KAS/ERG only.
- **Caveats on KuCoin (stated plainly):** offshore (Seychelles),
  unregistered in Canada, OSC investor warning (13 Jul 2022), no
  Canadian investor protection. Quebec is not restricted by its ToS,
  but the user must confirm eligibility at signup with his real
  province — no VPN, no false address; KuCoin freezes accounts that
  break its terms.
- **Design written:** `docs/master-mission23-live-trading-design.md`
  — live module (`core/atlas_live.py`, stdlib only, KuCoin REST +
  HMAC-SHA256), new config `config/live_trading.json` (enabled false
  by default), 8 in-code refusal gates, kill-switch wired to the
  emergency stop, Stage 5 live ledger (`user_version` 6), secrets
  via Secure Vault only, no withdraw function ever, test plan +
  diagnostics test 30, first-live-order protocol (one tiny order,
  user-confirmed, verify, stop).

## 2. Capital reality

- Eligible capital **$0.94** (mining $0.00 + first deposit 0.94452
  USDC). That is **below KuCoin's $1 minimum deposit** — it cannot be
  deposited as-is.
- Second deposit (under $10, sent ~17:53 EST) has NOT landed on-chain
  as of ~18:00 EST (signature check still shows only the first tx
  `4LadRji…`); the re-check cron fires ~17:59 EST and reports
  separately.
- Even after it lands (~$6–$10 total), live trading at this size is a
  proof-of-system exercise: a $1 trade costs ~$0.001–0.003 in fees
  while one XMR withdrawal costs ~$1.13. Real trading needs $50–$100+.
- Funding path: user sends USDC from the Solana deposit wallet to
  KuCoin (Solana network) from his own wallet app — the engine never
  signs and never reads the keypair — then USDC → USDT on KuCoin,
  then XMR/USDT, KAS/USDT, ERG/USDT spot only. No margin, no
  futures, no leverage.

## 3. State verified this mission (no code changed)

- Engine status: mode paper-only, stop ON, eligible capital $0.94,
  demo account virtual cash $9,998.64, positions 0.003 XMR (includes
  the parent's paper buy `m22-start-001`).
- `config/trading.json`: mode `paper-only`, deposit Solana/USDC,
  address configured. No live mode exists anywhere in code.
- Solana signatures for the deposit address: still 1 (first deposit
  only) as of ~18:00 EST.
- Artifact `atlas-command-center`: a build IS running (agent
  `1dbcf6c7-a84e-48da-904e-c1f30d1654be`, edit — the voice-button
  repair). The three M20/M21 repair inspections were NOT filed.
- Daemon: pid 1902 alive since 21:12:39 UTC (~1h50m — longer than the
  ~hourly pattern); recover.log no-op every 5 min through 22:57 UTC;
  newest archive ends mid-cycle 21:10:34 UTC, mem 93–94%, no stop
  line, no traceback. Mechanism still unknown.
- Ledger: **0 rows** (verified) — M6 finding 1 still not re-testable.
  Trading tables: 1 account, 2 orders, 1 deposit.
- Test suites NOT re-run: no code changed in this mission. M22 state
  stands (97/97, diagnostics 29/29).

## 4. Owed items — status

- Three M20/M21 repair inspections: BLOCKED (build running, above).
  File the moment it lands; parent route.
- Rendered Mining-tab check: STILL NOT established (20th mission).
  Needs the live-browser run; parent route.
- Daemon churn: watch continues; 24h startup count re-derivation
  owed next mission.
- Profitability-mirror lag fix proposal: job-body review STILL owed;
  its exact file was NOT located in this mission — parent should
  point at the job body directly.
- Ledger 0 rows: carried (M6 finding 1).
- Carried decisions owed unchanged: MEM% alert re-scope,
  mempool.space label, Obj 2 coordinator, SupportXMR URL, referral
  5%, minimum payout, Gates 2/4, roadmap/GOAL.md bookkeeping,
  recovery.md corrections, RVN difficulty, refresh step-9 transform,
  tariff fetchedAt schema.

## 5. Gates before ANY real order (all must pass)

- G1: User creates the KuCoin account himself (Quebec, real
  province) and completes KYC on his own device.
- G2: User creates API keys himself — trade-only, withdrawals
  DISABLED, IP whitelist — and hands them over via the Secure Vault
  only (never in chat).
- G3: Funding: total eligible capital ≥ $10 (currently $0.94; the
  second deposit has not landed yet).
- G4: Live module built + mocked-HTTP tests passing + diagnostics
  30/30 (design exists now; build is a follow-on step).
- G5: Paper-trading validation done (demo + `m22-start-001` filled at
  live prices).
- G6: Kill-switch + risk limits configured and refusal-gate tested
  (emergency stop gates live orders).
- G7: User confirms the exact first live order (coin, side, size, max
  price) in chat — one tiny order (~0.002 XMR ≈ $0.91), verify the
  fill and balances, then stop for review.
- G8: Second USDC deposit confirmed on-chain (pending; cron
  re-check ~17:59 EST).

## 6. What is needed from the user

1. **Exchange choice:** KuCoin (recommended — the only venue that
   fits Quebec + XMR/KAS/ERG). Confirm it, or name another venue and
   the research re-runs for it.
2. **Account + KYC:** create the KuCoin account himself and complete
   verification (ID + proof of address, Quebec).
3. **Funding:** deposit USDC (Solana) to KuCoin until total eligible
   capital is ≥ $10 — the $0.94 alone is below the $1 minimum
   deposit, and USDC withdrawals need ≥ 5 USDC.
4. **API keys:** create trade-only keys (withdrawals disabled, IP
   whitelist) and provide them through the Secure Vault flow.
5. **First order:** confirm the exact first live order when G1–G4
   pass (suggested: 0.002 XMR buy, ≈ $0.91).

**AUTO-RESUME: Mission 24 starts automatically after this one per the
user's 01:22 EST order — scope: build the live module (D-M23-4 to
D-M23-9) once G1–G3 move, and re-file the three repair inspections the
moment the atlas-command-center build lands.**
