# ATLAS Master Mission 6 — Lane D (UI build) Report

**Mission:** Master Mission 6 — Reward Accounting (75/25 engine, simulation only)
**Lane:** D (UI build, artifact only)
**Date:** 2026-11-18
**Authorization:** User authorized Master Mission 6 at 11:06 EST, 2026-11-18.
**Verdict:** SOURCE COMPLETE AND TYPECHECKED — **NOT DEPLOYED, rendered check NOT
established** (see §5 — both gaps are tooling limits of this subagent, stated
honestly, not hidden).

## 1. What was built (source, in the ts-space working tree)

Artifact slug `atlas-command-center`. Six files changed, nothing else:

| File | Change |
|---|---|
| `client/src/RewardAccounting.tsx` (new, 17 KB) | `RewardAccountingSection` — the five design §10 panels, zero buttons/inputs/links/forms |
| `client/src/Mining.tsx` | Import + `<RewardAccountingSection m={m} />` directly below `<CoordinatorSection m={m} />` (line 218), above Settings |
| `server/src/schema.ts` | Additive mirror columns on `mining_ledger` (hostLedgerId, entryType, hostBatchId, batchRef, mode, prevHash, entryHash, note, partyLabel, syncedAt) + new `mining_reward_batches` table |
| `drizzle/0006_reward_mirror.sql` (new) | Migration 0006 (additive only) + unique indexes on host ids |
| `drizzle/meta/_journal.json` | Journal entry idx 5 for 0006 |
| `server/src/actions.ts` | `ingestRewardsState` action; `getMining` gains the `rewards` block; `refreshAtlasData` gains step 7 (rewards mirror, rides the existing refresh flow) |

Tab order now: MiningDashboard, WalletCenter, EarningsSection, HistorySections,
PayoutSection, CalculatorSection, MinerPrototypeSection, CoordinatorSection,
**RewardAccountingSection**, SettingsSection, HelpSection. No new tab, no new
card, no other order change. Wallet center (M3), miner prototype (M4),
Coordinator section, orb, refresh, emergency stop, Start/Stop (still
hard-disabled), and all other tabs untouched.

## 2. Design §10 compliance

1. **Reward split — 75/25:** rule line + derived totals (total user rewards,
   total ATLAS share, total pool fees, total referral rewards, total payouts),
   each a `SUM` over the mirrored ledger by entry type (never a stored
   aggregate, never an estimate), each carrying a SIMULATION tag while mode is
   simulation-only.
2. **Methodology (verbatim):** "Rewards come only from confirmed pool payouts,
   never from estimated hashrate. The pool fee is deducted first. 75% goes to
   miners by verified accepted shares; 25% to ATLAS. Referral rewards come
   from the ATLAS 25% only. All amounts in XMR (1 XMR = 10¹² piconero).
   Simulation only — no real earnings yet." Plus the referral-rate note
   (5% / 500 bps — design parameter, to be confirmed before any real-mode
   settlement) and "No guaranteed profits" — no "earn $X/day" copy anywhere.
3. **Ledger table:** newest first — date, type, party (ATLAS / Pool fee /
   username / `User #id`), amount XMR, batch ref (+ short entry hash),
   mode tag (SIMULATION per row). Empty state verbatim: "No reward entries
   yet — simulation only, 0 workers, 0 shares." Tamper-evident note
   ("each entry links to the previous entry's hash") + append-only /
   reversal-only note. Reward batches listed below the table when any exist.
4. **Referrals line:** verbatim "Referral rewards: 0 XMR — no referrals
   yet." (When referrals exist: total paid from the ATLAS 25%, never from
   the users' 75%.)
5. **Honest zero state:** section header states "SIMULATION ONLY — no pool
   rewards, no workers, no shares"; panel 5 shows all balances 0 XMR,
   workers 0, shares 0, batches 0, entries 0, and states calculator
   estimates are never shown here and never added to any balance.

**Data path (design §10, Mission 5 pattern extended, not reinvented):**
`ingestRewardsState` mirrors host `reward_batches` + `ledger` rows into
`mining_reward_batches` / `mining_ledger` mirror columns, deduped on host
batch id / host ledger id (unique indexes in migration 0006 enforce it at
the DB level too). Ledger ingest is insert-only. Re-ingest of unchanged
data reports `upToDate: true`. `getMining` returns the `rewards` block
(mode, referralRateBps defaulting to the 500 bps design parameter,
derived totals, batches, entries, referral count, syncedAt, stale).
Entry hashes ARE mirrored (public audit data, per design §10). **No token,
token hash/salt, session token hash, binary hash, or password hash is ever
mirrored** — the ingest reads host usernames for display only and the
refresh-task text explicitly forbids `password_hash` and all secret columns.
**STALE labelling:** mirrored data older than 1 h gets a STALE tag with its
age; never-synced data gets "Not synced yet" — never presented as fresh
(Mission 3 finding 1, carried, not fixed).

**Host state at build time (read-only check):** `user_version` 2, no
`reward_batches` table yet (Lane C runs in parallel — the refresh step 7
skips cleanly when the tables do not exist yet), ledger 0, users 0,
workers 0, shares 0, referrals 0, payouts 0. The UI therefore defaults to
honest zeros + "Not synced yet", which is the true live state.

## 3. Verification done (source-level)

- `bun run typecheck` (client + server): **PASS, exit 0, zero errors**
  (one error found and fixed during the run: `syncedAt` null-narrowing).
- Migration 0006 syntax validated against an in-memory SQLite DB shaped
  like the pre-0006 schema, including a live insert into both new
  structures; duplicate `host_ledger_id` insert **rejected by the UNIQUE
  index** as designed.
- Grep: **zero** `<button>`, `<input>`, `<a>`, `<form>` in
  `RewardAccounting.tsx`; 18 SIMULATION/Simulation mentions; verbatim
  empty-state / referrals / header strings confirmed present.
- Changed-file sweep confirms only the six files above changed.

## 4. What was NOT touched (hard limits kept)

No host code, host DB, or config (Lane C's job — including the
`referral_rate_bps` config addition, which this lane only displays as a
design parameter). No real payouts, no pool connection, no wallet/key
creation, no spending, no config changes, no mining activation. No fix to
the refresh failure (Mission 3 finding 1) or the stale "no miner yet" copy
(Mission 4 finding 4) — noted as known issues only. No interactive probe
run. No new cron, no new refresh schedule (ingest rides `refreshAtlasData`).

## 5. GAPS — stated plainly (do not present as done)

1. **NO artifact build id — the section is NOT deployed.** This subagent's
   toolset exposes only `artifact.restore` / `artifact.share` /
   `artifact.unshare`; `artifact.edit` (the only route that runs the full
   pipeline — migrations, typecheck, bundle, publish) is **not available**
   to this subagent, and the SDK build guard refuses hand builds
   (`HATCH_SPACES_BUILD_DRIVER` unset). The source changes above are
   complete and typechecked in the ts-space working tree, but the live
   artifact still serves the previous build (v9 lineage). **To deploy, an
   agent with `artifact.edit` must run the edit** (the six files above, as
   specified here) — or confirm whether `artifact.edit` picks up this
   working tree as-is.
2. **Rendered check NOT established.** No live-browser access exists in
   this subagent, and there is no new build to render. Desktop + mobile
   Mining-tab render (scroll to the section, all five panels, zero state,
   SIMULATION tags, no console errors, mobile overflow 0 at 390 px,
   persistence on reload, other tabs/orb/refresh/emergency-stop still
   rendering) is **owed after deployment**, by a fresh interactive audit.
   Source-level verification above is "probable, not proven" for rendering.
   This is the same gap as Missions 2–5, repeated for a tooling reason, not
   skipped silently.
