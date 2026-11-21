# ATLAS — Master Mission 2: Mining Tab — Report

**Date:** Wednesday, 2026-11-18 (work 02:33–02:48 EST)
**Authorization:** user tapped "Yes, build Master Mission 2" at 02:33 EST.
**Scope:** Stage 0 (safety + database scaffolding) + a full Mining tab UI on the ATLAS Command Center. NO live mining in this mission. Stop after this mission; authorization required before Master Mission 3.

## 1. What was built

### Stage 0 — host-side (lane agent 3b90206c, independently verified by the coordinator)
- Safety confirmed before any change (see §6).
- Database backed up first: `~/workspace/atlas/backups/atlas-2026-11-18-pre-mission2.db` (36,864 B, integrity ok, row counts matched live exactly at backup time).
- Migration applied in a single transaction, no rollback needed. Migration file: `~/workspace/atlas/core/migrate_mission2_stage0.sql`. Schema version `PRAGMA user_version` 0 → 1.
- 9 new tables, all `id INTEGER PRIMARY KEY AUTOINCREMENT`, timestamps Unix epoch integers, FKs declared, 16 indexes on FK + time columns, all 0 rows:
  - **users**: username UNIQUE, email UNIQUE, email_verified (0/1), password_hash (placeholder only), xmr_address NULL, created_at
  - **workers**: user_id FK, worker_type CHECK(browser/desktop), name, status (default `registered`), registered_at
  - **shares**: worker_id FK, difficulty, accepted CHECK(0/1), submitted_at
  - **ledger** (append-only): entry_type CHECK(user_allocation/atlas_share/fee/payout), user_id FK NULL, amount_piconero INTEGER, reference, created_at
  - **payouts**: user_id FK, amount_piconero INTEGER, destination_address, status CHECK(pending/confirmed/failed), txid NULL, created_at
  - **referrals**: referrer_user_id FK, referred_user_id FK, status (default `pending`), created_at
  - **achievements**: user_id FK, achievement_key, awarded_at
  - **pool_stats**: pool_name, recorded_at, hashrate, miners, block_height, network_hashrate, block_reward_piconero INTEGER, pool_fee_bps INTEGER
  - **sessions**: user_id FK, session_token_hash, created_at, expires_at
  - All money fields are integer piconero (1 XMR = 10^12); pool fee stored as integer basis points, never a float percent.
- Existing tables **not altered** (metrics, decisions, events — counts unchanged at migration instant).
- New config file (added scope from the Mission 1 spec, Stage 0 row): `~/workspace/atlas/config/pool-rewards.json` — valid JSON, `config/atlas.json` untouched. Contents: primary pool MoneroOcean (api.moneroocean.stream, `/pool/stats`, 0% fee); fallbacks SupportXMR (0.6%) and P2Pool (0%); split 75% users / 25% ATLAS applied only to actual confirmed pool rewards (never estimates/unverified work; attribution = pool-accepted shares, difficulty-weighted; referral rewards funded from the ATLAS 25% only); fee disclosure; minimum payout = placeholder, null, not set; mode **simulation-only**; ledger rules (append-only, reversing-entry corrections, batch dedupe, payout idempotency keys); safety gate (no real payouts/pool connection/mining until authorized after simulation/testnet + security testing; emergency stop honoured). No credentials, secrets, or wallet addresses anywhere.
- recover.sh log-truncation fix **verified in place** (not re-done): `>>` append, log rotation to `monitor.log.1`, plus the `9>&-` flock fix.

### Mining tab — website (artifact `atlas-command-center`, builder agent a64317be)
- A dedicated MINING tab now sits between Compute Power and Activity. `client/src/App.tsx` (tab type/nav/render chain) + new `client/src/Mining.tsx` + new `getMining` / `setMiningWallet` actions + drizzle migration `0004_mining_data_model.sql`. Build `c77461f9-6c3a-494a-bf84-fb086158d6fe`.
- All 12 requested sections present, plus an extra "Reward split — 75 / 25" panel:
  1. Mining dashboard (0 H/s, 0 shares, no workers — recorded zeros)
  2. Start mining button — **disabled**, no handler
  3. Stop mining button — **disabled**, no handler
  4. Wallet setup & connection — one combined panel (receiving-address field with Monero format validation; address only; never seed phrases/private keys; full onboarding center noted as Mission 3)
  5. Earnings dashboard (all balances 0 XMR from the empty ledger)
  6. Mining history (empty state)
  7. Reward history (empty state)
  8. Payout center (states no payouts exist; real payouts gated on authorization plus security testing)
  9. Mining calculator (Mission 1-verified inputs: XMR $507.17, network 6.44 GH/s, block reward 0.6 XMR, 720 blocks/day, 0% pool fee; labelled ESTIMATE / not guaranteed; honest note that laptop-browser mining loses ~$0.10–0.13/day after electricity; never credits a balance)
  10. User settings — device-local resource profile
  11. Help & tutorials
  12. (Reward split panel: 75% users / 25% ATLAS, applied only to confirmed pool rewards)
- The tab states "MINING IS NOT ACTIVE" and "No mining runs in this mission — there is no miner yet"; the Start caption reads "Start mining — activates after Master Mission 4 + explicit authorization". No miner, Web Worker, pool client, or mining loop exists in the tab. The Request payout button is likewise disabled.
- Every figure carries a SNAPSHOT / RECORDED / ESTIMATE / UNAVAILABLE provenance tag.
- Existing features untouched: Overview, Compute Power, Activity, Roadmap tabs; orb; refresh (tracked and auto); emergency stop; diagnostics. No other tab or card added. No new refresh schedule; the Mining tab reads stored rows only; the existing daily refresh job is unchanged.

## 2. Files changed
- Host: `core/migrate_mission2_stage0.sql` (new), `config/pool-rewards.json` (new), `data/atlas.db` (9 tables added, `user_version` 1), `backups/atlas-2026-11-18-pre-mission2.db` (backup).
- Artifact: `client/src/Mining.tsx` (new), `client/src/App.tsx` (tab wiring), `server/src/actions.ts` (`getMining`, `setMiningWallet`), `server/src/schema.ts`, `drizzle/0004_mining_data_model.sql` (new; artifact tables mining_users, mining_workers, mining_shares, mining_ledger, mining_payouts, mining_referrals, mining_achievements, mining_pool_stats, mining_sessions — all 0 rows).

## 3. Tests performed and evidence
- **Stage 0 verification (lane + coordinator's independent re-check):** backup integrity ok + counts matched; migration in one transaction; integrity ok before and after; new tables 0 rows; existing counts unchanged at migration instant; snapshot advanced a full 60 s cycle during the wait; recover.sh `>>` verified; pool-rewards.json valid JSON, simulation-only; safety confirmed. Coordinator re-check after the lane: integrity ok, `user_version` 1, all 12 tables present, snapshot age 12 s, daemon pid 1976 (single instance), safety values as in §6.
- **Diagnostics:** lane run 20/22 PASS — tests 14 (network) and 18 (API validity) failed on transient timeouts (MoneroOcean + blockchain.info + mempool.space timed out; CoinGecko 200), re-verified as 200s by direct curl immediately after. Coordinator's clean re-run: **22/22 PASS, 0 FAIL, exit 0** — test 14 all three endpoints 200; test 18 PASS (mempool.space timeout is non-fatal by design); test 19 DB write latency 0.7 ms (< 1000 ms); test 20 exactly 1 daemon; test 16 daemon RSS 14.1 MB; test 17 snapshot age 4 s.
- **Builder verification (artifact):** typecheck + migration 0004 applied. Exercised the actions on the sandbox DB: `getMining` returned all-zero balances, zero shares, empty workers/ledger/payouts/sessions/achievements, user null — the honest empty state. `setMiningWallet` accepted a valid-format 95-char test address (stored on the scaffold `local-user` account; balances stayed 0) and rejected a malformed address with clear schema errors. Test writes went to the sandbox database only. Client wiring verified by code inspection: Mining tab added to the tab type/nav/render chain without touching Overview, Compute Power, Activity, Roadmap, orb, refresh, or emergency-stop code; Start/Stop and payout-request buttons disabled in markup.
- **Independent inspection (707a54ab, diagnosis submitted, confidence probable):** source confirms all 12 sections present in `Mining.tsx`; Start/Stop rendered `disabled` + `aria-disabled='true'` + opacity-50 with no onClick handler; no miner code; mining tables 0 rows so `getMining` derives every balance as 0 XMR; no console errors on page load in every audit reviewed (only THREE.Clock deprecation and software-WebGL fallback warnings); existing features present in the captured Overview render (live orb with controls, "HELD — MONITORING ONLY", Refresh button, emergency stop ON, 22/22 PASS diagnostics, $0 trading/mining figures); artifact state confirms `emergency_stop='true'` and `refresh_status='landed'`.
- **Final safety check (coordinator, after both workstreams):** stop True, mining False, trading paper-only, capital 0; daemon pid 2939 (single instance), snapshot age 1 s; DB integrity ok, `user_version` 1, new tables 0 rows; diagnostics 22/22; pool-rewards mode simulation-only.

## 4. What was NOT built and why
- No live mining: Start/Stop are disabled; the miner prototype is Master Mission 4 and needs explicit authorization per worker.
- No wallet onboarding center (Master Mission 3) — only the address-field scaffold with format validation.
- No coordinator, reward engine, user dashboard beyond the tab's zero-state earnings, admin console, profitability intelligence, referral/achievement logic, or payout flow (Missions 5–11).
- No demo users, workers, shares, earnings, or payouts were seeded — the tab is honestly empty.
- No pool connection, no stratum client, no WASM miner, no treasury design, no real payouts.
- No changes to `config/atlas.json` and no config edits of any kind.

## 5. Unresolved findings and open items (honest)
- **RENDERED VERIFICATION GAP (the main one):** no captured browser run ever opened the Mining tab — every audit aria snapshot shows Overview selected, and the interaction screenshots show only orb controls. The tab's rendered layout on desktop/mobile, disabled-button behaviour under a real click, and wallet/calculator/settings interactions were never exercised in a browser in the available evidence. Source + data verification is strong (inspection confidence: probable), but rendered verification is **NOT established**. Recommended next step (from the inspection): a targeted harness audit that actually selects the Mining tab on desktop and mobile, captures full-page screenshots of every Mining section, attempts the disabled Start/Stop and Request payout buttons, submits invalid then valid-format XMR addresses, changes a calculator preset, and clicks through the other tabs plus Refresh. No product code change is indicated; do not "fix" the tab by enabling anything or seeding demo data. The user can also verify directly by tapping the Mining tab on their phone.
- **Refresh intermittency in one audit run (07:40 UTC):** "Refresh could not start: Web artifact inference failed", a stale 14-minute snapshot, mobile settled=false with 1 request in flight. A later render capture showed "✓ Refresh complete — snapshot from Nov 18, 07:44:42 AM". Likely a transient harness/agent-spawn failure rather than a product defect, but no retry evidence for that specific failure is in the bundle.
- **Catalog `construction_status='failed'` in evidence.json** is unexplained; build manifests exist and audits return nav 200 with ok:true — possibly a stale builder status.
- **Stage 0 incident:** an exec service restart aborted the lane's second diagnostics re-run mid-test-10 (daemon SIGTERMed, test 11 could not restart it); the lane recovered the daemon via `recover.sh` only (pid 1976 at the time). No data lost. Separately, the website builder's first exit_build was interrupted by a service restart; it resubmitted to complete the build.
- **Inspection tooling limit:** the repair-authorized inspection attempt failed ("subagent bootstrap is no longer authorized" — no edit builder could start); inspection-only succeeded. No repair was attempted, and none is indicated — the gap is evidential, not a code defect.

## 6. Safety verification (final)
- emergency_stop: true; mining.enabled: false (status design-only); trading.mode: paper-only, eligible_capital_usd: 0, enabled false, futures/leverage/margin/options all false; limits 50/70 unchanged. Dashboard state: `emergencyStop: true`, mining "disabled", trading "disabled-paper-only". Live host: exactly 1 daemon, snapshot age seconds, DB integrity ok. Nothing mined, traded, spent, or created; no wallets or keys; no config change; emergency stop never lifted.

## 7. Stop
Master Mission 2 is complete except for the rendered-verification gap in §5. **STOP — awaiting authorization before Master Mission 3. Do not start Mission 3.**
