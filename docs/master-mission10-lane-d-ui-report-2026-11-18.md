# ATLAS Master Mission 10 — Lane D (UI build) SPECIFICATION

**Mission:** Master Mission 10 (security and scale testing).
**Design:** `docs/master-mission10-design.md` (binding, D-M10-1–D-M10-13).
**Baseline:** `docs/master-mission10-baseline.md` (PASS usable, not all-green).
**Host build:** `core/atlas_security.py` + `core/test_atlas_security.py`
(18/18) + diagnostics tests 27/28 (28/28) — Lane C complete.
**Artifact:** `atlas-command-center` (current build `2131aa37`, Mission 9).
**Status:** SPECIFICATION — build-ready for the artifact edit lane. Nothing
in this document is built yet.

## 0. Binding inputs and ground truth

### 0.1 Deviations from the parent task / design (flagged, none concealed)

1. **The mirror cannot independently re-derive the six security counts
   from its own tables.** The design §7 assumes a mirror-vs-host
   comparison on security counts, but the artifact mirror holds no
   `workers`/`shares` tables — the counts live only in the host export
   and in the M8 admin mirror (log tables + ledger mirror). The spec
   therefore defines the comparison as follows (§2.2): the
   mirror-derived security counts are re-derived from the EXISTING M8
   admin mirror tables (`mining_admin_decisions`, `mining_admin_events`,
   `mining_ledger`, `mining_reward_batches`) using the M8 §4 definitions
   wherever the mirror holds the underlying rows; any count the mirror
   cannot derive is reported as `null` with the verbatim reason
   "Not derivable from the mirror — host figure shown" and is EXCLUDED
   from the mismatch comparison (never silently equal, never silently
   mismatched). The ledger totals ARE fully derivable from the existing
   M6 mirror rows and are compared exactly (integers only, no float
   rounding — the M9 lesson).
2. **The M9 step-9 lesson applies to this ingest from the start.** The
   security export nests scale figures under `scale.l1` / `scale.l2` /
   `scale.l3` / `scale.l4` / `scale.l5` and the test records under
   `security_tests[]` — it does NOT have the flat top-level arrays an
   ingest action might assume. §3.3 gives the EXACT export → ingest
   mapping (field-for-field, with the nested paths spelled out) so the
   builder does not repeat the M9 step-9 failure. The M9 step-9
   transform itself is still owed and is NOT fixed by this spec (§7).
3. **Migration number 0011 is assumed, to be verified at build time.**
   M9 used 0010 (journal idx 9). The build lane must check the drizzle
   journal and use the next free number; if 0011 is taken, use the next
   free one and record the deviation.
4. **L2 (mirror ingest timing) is NOT_RUN in the host export** with the
   verbatim reason "Mirror ingest timing not measured — sandbox
   unavailable". The panel shows that verbatim reason (§1.3 panel 3).
   The Lane D sandbox suite (§5.2) measures ingest timing on its own
   fixtures and records it as evidence; it does not back-fill the host
   figure.
5. **The design §8.2 panel 5 "Honest nulls" is rendered from the
   export's `honest_nulls[]` array** (4 entries, verified live — §0.2),
   not hardcoded in the component. If the export ever carries different
   nulls, the panel shows those.

### 0.2 Ground truth (verified read-only by this lane from the live host)

- `data/security.json` exists, parses, `exported_at` 1795062669,
  `emergency_stop` true, `mode` "simulation-only", `mining_enabled`
  false, `source_db_user_version` 3.
- `security_tests`: 9 records, keys exactly
  `id, name, result, evidence, duration_ms`; results S1–S9 all PASS.
  S1 evidence (verbatim, first record): "fixture settled 5 entries,
  chain PASS; tampered entry 4 named by verifier (entry 4: entry_hash
  mismatch (row was modified after commit)); reversal entry 6 +
  corrected entry 8; chain PASS; originals visible; balances alice
  15000000000, bob 300000000001; live chain trivially valid, 0 entries
  (ledger empty — chain trivially valid)".
- `security_counts`: all six 0 (suspicious_workers, invalid_shares,
  duplicate_shares, account_abuse, auth_failures, payout_anomalies).
- `host_verified_totals`: ledger_entries 0, batches_settled 0,
  total_user_rewards_piconero 0, total_atlas_share_piconero 0.
- `scale.run_at` 1795062216, `run_duration_s` 452.1, `stale` false.
  Levels: 1× baseline (0 workers / 0 shares, run_pass_s 7.476,
  db_size_bytes 376832); 100 workers / 10,000 shares (run_pass_s 6.407,
  record_shares_per_s 1855.1, record_shares_total_s 5.39,
  db_size_bytes 1253376); 1,000 workers / 100,000 shares (run_pass_s
  8.296, record_shares_per_s 250.7, record_shares_total_s 398.917,
  db_size_bytes 10199040). `l5.bottleneck`:
  "record_shares_total_s exceeds its limit at 1,000 workers /
  100,000 shares (398.917s)", `first_bottleneck_load`:
  "1,000 workers / 100,000 shares". `l2`: result NOT_RUN, reason
  "Mirror ingest timing not measured — sandbox unavailable". `l3`:
  live_s 21.7, live_under_120s true, live diagnostics 28 pass / 0 fail,
  temp_s null with reason "Diagnostics suite runs against the live DB
  only — temp-ledger full-suite timing not measured",
  temp_db_checks_s 0.229. `l4`: bytes_per_row shares 96.26, ledger
  318.26, decisions 45.06, metrics 45.06; base 376832; projections
  (ESTIMATE) 10,000 → 1,339,432 B, 100,000 → 10,002,832 B,
  1,000,000 → 96,636,832 B.
- `redaction`: patterns_checked 6, files_checked 6 (admin, security,
  rewards, dashboard, coordinator, profitability), files_missing [],
  hits 0, hits_by_file all 0.
- `enforcement`: emergency_stop true, mode "simulation-only",
  mining_enabled false, real_mode_batches_refused 0,
  payout_calls_refused 0, mining_start "Mining is not active — no start
  path exists while the emergency stop is ON", sources map present.
- `honest_nulls`: 4 entries (Gate 1 unmeasured; no live workers; rendered
  Mining-tab check not established; mirror contents cannot be verified
  from the host).
- `format_valid_line`: "Format valid — ownership not verified".
  `ownership_line`: "Validation checks the address format only. It does
  not prove who owns the address."
- `scope`: "Security & scale status — test evidence only. Passing these
  checks does not guarantee the system is secure — it proves these
  specific attacks were detected or refused in testing."
- Live DB (read-only check by this lane): ledger 0, reward_batches 0,
  payouts 0, shares 0, workers 0, users 0; integrity ok, user_version 3.
- Configs unchanged (sha256 short `46d3d12c` / `b01a22ad`, matching the
  M10 baseline).

## 1. New component — `client/src/SecurityScaleStatus.tsx`

### 1.1 Identity and placement

- Component `SecurityScaleStatusSection`, file
  `client/src/SecurityScaleStatus.tsx`. Rendered by ONE line in
  `Mining.tsx` directly below `ProfitabilityIntelligenceSection`, above
  Settings. Tab order otherwise unchanged. No new tab.
- Zero buttons/inputs/links/forms. Start/Stop untouched. No hardcoded
  displayed figures (grep-enforced, §5.2). XMR to 6 decimals from
  integer piconero where money appears (only the reused
  confirmed-earnings block, which is 0 / SIMULATION-tagged on the live
  system). Test counts as integers with numerator and denominator
  ("9/9 security checks passed"). Timings in ms or s with units. Sizes
  in bytes/KB/MB with the raw byte figure beside them. No fiat.
- The section reuses the dashboard earnings block by import (M8
  pattern) and must never show a different earnings number than the
  user dashboard.
- Export-missing state: when `securityExportMissing` is true, the
  section renders the verbatim line "Security data not synced yet —
  the host security export has not been ingested" and nothing else (no
  zeros, no invented figures).

### 1.2 Section header (verbatim)

- Scope line (top of section, verbatim from the export's `scope`):
  "Security & scale status — test evidence only. Passing these checks
  does not guarantee the system is secure — it proves these specific
  attacks were detected or refused in testing."
- Header line (verbatim): "N/M security checks passed" with N and M as
  integers from the live block (live: "9/9 security checks passed").
- STALE tag (verbatim, design §6): when the export is > 1 h old,
  "STALE — security export NN min old" (NN = whole minutes). When the
  scale results are older than 24 h, the scale panel carries the
  verbatim tag "Scale results stale — last run over 24 hours ago".

### 1.3 The panels (verbatim headings, labels, and empty-state copy)

1. **"Security tests"** — one row per check S1–S9, in export order:
   check id + name, result (PASS / FAIL / NOT_RUN), evidence string,
   duration in ms. A FAIL row renders in the section's alert styling
   with its evidence string. A NOT_RUN row renders the verbatim reason
   from the export. The panel header shows the "N/M security checks
   passed" line (§1.2).
2. **"Live security counts"** — the six M8 §4 counts, each with its
   count and the verbatim empty state "No events recorded" when 0.
   Counts are host-verified (from the stored export); on mismatch the
   host figure is shown with the §2.4 note. Each count row names its
   source ("host export" or "mirror-derived" per §2.2).
3. **"Scale test results"** — the last on-demand scale run, all figures
   from the stored export, labelled with the run timestamp:
   - Load-level table: workers, shares, DB size, `run_pass` wall time,
     shares/second, `record_shares` total seconds, slowest step — one
     row per tested level (live: 3 rows).
   - Diagnostics runtime: live suite seconds + pass/fail counts
     (live: 21.7 s, 28 pass / 0 fail), with the verbatim
     "under 120 s" judgement from the export (`live_under_120s`).
   - Size projection table (labelled ESTIMATE, verbatim): 10,000 /
     100,000 / 1,000,000 shares with projected bytes, plus the formula
     "size ≈ base + rows × bytes_per_row" and the bytes-per-row figures.
   - First-bottleneck finding (verbatim from `l5.bottleneck`) and the
     load at which it appears (`l5.first_bottleneck_load`).
   - L2 row: result NOT_RUN with the verbatim reason from the export.
   - When no scale run exists (`scale.run_at` null), the verbatim empty
     state "No scale test run yet — run the on-demand scale test from
     the host to populate this panel" — no button, no invented number.
   - Scale results older than 24 h carry the §1.2 stale tag.
4. **"Enforcement status"** — emergency stop (ON/OFF with the export
   timestamp), mode (simulation-only), real-mode batches refused
   (count of refusals logged), payout-shaped calls refused (count),
   mining start (verbatim from the export's `mining_start`). Each line
   names its source from the export's `enforcement.sources` map.
5. **"Honest nulls"** — every entry of the export's `honest_nulls[]`
   array, rendered verbatim, one per line. Plus the S5 ownership line
   (verbatim): "Validation checks the address format only. It does not
   prove who owns the address." And the format-valid line (verbatim):
   "Format valid — ownership not verified" — shown beside the S5 row
   in panel 1, not as a standalone claim.
6. **"Redaction check"** — the export's `redaction` block: patterns
   checked (6), files checked (6, named), hits (0), with the verbatim
   line "0 credential-pattern hits across 6 host exports" when hits
   are 0. A non-zero hit count renders as a FAIL row with the file
   names (never the matched values).

## 2. `getMining` security block — computed server-side from the ALREADY-MIRRORED singleton row

### 2.1 Field names (must match the host export)

The `security` block in `getMining` carries (all names camelCase, mapped
from the export per §3.3):

- `securityExportMissing: boolean`, `exportedAt: number | null`,
  `securitySyncedAt: number | null`, `stale: boolean`,
  `staleReason: string | null`
- `securityTests: [{ id, name, result, evidence, durationMs }]`
  (verbatim from the export, in export order)
- `securityCounts: { suspiciousWorkers, invalidShares, duplicateShares,
  accountAbuse, authFailures, payoutAnomalies }` (host-verified, from
  the stored export)
- `mirrorDerivedCounts: { suspiciousWorkers, invalidShares,
  duplicateShares, accountAbuse, authFailures, payoutAnomalies }`
  (derived per §2.2; a count that cannot be derived is `null`)
- `hostVerifiedTotals: { ledgerEntries, batchesSettled,
  totalUserRewardsPiconero, totalAtlasSharePiconero }` (from the stored
  export)
- `mirrorDerivedTotals: { ledgerEntries, batchesSettled,
  totalUserRewardsPiconero, totalAtlasSharePiconero }` (derived from the
  existing M6 mirror rows — `mining_ledger` / `mining_reward_batches`)
- `mismatch: boolean`, `mismatchDetails: string[]` (field names, §2.4)
- `scale: { runAt, runDurationS, stale, levels: [{ label, workers,
  shares, sessions, sharesInserted, dbSizeBytes, runPassS,
  recordSharesPerS, recordSharesTotalS, attributionWeightsS,
  verifyChain10000S, slowestStep }], l2: { result, reason }, l3:
  { liveS, liveUnder120s, liveDiagnosticsSummary, tempS, tempReason,
  tempDbChecksS }, l4: { bytesPerRow, baseBytes, formula,
  projectionShares, label, note }, l5: { bottleneck,
  firstBottleneckLoad } }` (verbatim from the export; `runAt` null
  when never run)
- `enforcement: { emergencyStop, mode, miningEnabled,
  realModeBatchesRefused, payoutCallsRefused, miningStart, sources }`
- `redaction: { patternsChecked, filesChecked, filesMissing, hits,
  hitsByFile }`
- `honestNulls: string[]`, `formatValidLine: string`,
  `ownershipLine: string`, `scopeLine: string`
- `confirmedEarnings` — reused from the dashboard block by import,
  never recomputed (M8 pattern).

### 2.2 Derivation rules (server-side, in `getMining`)

- `securityTests`, `securityCounts`, `hostVerifiedTotals`, `scale`,
  `enforcement`, `redaction`, `honestNulls`, `formatValidLine`,
  `ownershipLine`, `scopeLine` are read verbatim from the stored
  singleton payload. No recomputation, no rounding, no unit conversion.
- `mirrorDerivedTotals` are derived from the existing M6 mirror rows:
  `ledgerEntries` = COUNT of `mining_ledger`; `batchesSettled` =
  COUNT of `mining_reward_batches` with status settled;
  `totalUserRewardsPiconero` = SUM over `mining_ledger` where
  entry_type = 'user_allocation'; `totalAtlasSharePiconero` = SUM
  where entry_type = 'atlas_share'. Integers only.
- `mirrorDerivedCounts` are derived from the existing M8 admin mirror
  tables using the M8 §4 definitions, wherever the mirror holds the
  underlying rows:
  - `accountAbuse` = COUNT of `mining_admin_events` where kind =
    'abuse'; `authFailures` = COUNT where kind = 'auth_failure'.
  - `payoutAnomalies` = COUNT of mirrored payouts with status failed
    (from the rewards mirror, if the table exists) + COUNT of
    `mining_ledger` rows with entry_type = 'reversal'; if the payouts
    mirror is absent, this count is `null` with the verbatim reason.
  - `suspiciousWorkers`, `invalidShares`, `duplicateShares` cannot be
    derived from the mirror (no workers/shares mirror tables) — they
    are `null` with the verbatim reason "Not derivable from the mirror
    — host figure shown".
- STALE: `stale` is true when the stored export's `exported_at` is
  more than 3,600 s old at read time; `staleReason` names the export
  ("security export NN min old"). `scale.stale` is true when
  `scale.runAt` is more than 86,400 s old (or null → the panel shows
  the §1.3 empty state, not a stale tag).
- `securitySyncedAt` is the ingest timestamp of the stored row; it
  advances only when a new export is stored (identical re-ingest
  leaves it untouched, §3.3).

### 2.3 Expected live values of the block (today — the acceptance baseline)

- `securityExportMissing: false`, `exportedAt` 1795062669 (or newer
  after a later coordinator pass — the value must be fresh, age < 600 s
  at check time), `stale: false`, `securityTests`: 9 records, all
  PASS, S1 evidence as in §0.2. `securityCounts`: all six 0.
  `mirrorDerivedCounts`: accountAbuse 0, authFailures 0,
  payoutAnomalies 0 (or null with the verbatim reason if the payouts
  mirror is absent), suspiciousWorkers / invalidShares /
  duplicateShares null with the verbatim reason.
  `hostVerifiedTotals` == `mirrorDerivedTotals` (all 0) →
  `mismatch: false`, `mismatchDetails: []`. `scale.runAt`
  1795062216, `stale` false, levels as in §0.2, L5 bottleneck verbatim
  as in §0.2. `enforcement`: stop true, mode simulation-only,
  refusals 0/0. `redaction.hits` 0. `honestNulls`: 4 entries verbatim.
  `confirmedEarnings` identical to the dashboard block (0 /
  SIMULATION-tagged).

### 2.4 MISMATCH MECHANISM (binding, D-M10-11 — design §7, M7 §6 / M8 §7 / M9 §7 carried)

- Compare `mirrorDerivedTotals` against `hostVerifiedTotals` field by
  field (integers, exact equality — no tolerance, no rounding: the M9
  lesson does not apply here because no floats are involved).
- Compare each non-null `mirrorDerivedCounts` entry against the
  corresponding `securityCounts` entry (integers, exact equality).
- On ANY disagreement: `mismatch: true`; `mismatchDetails` names each
  disagreeing field exactly (e.g. `"ledgerEntries"`,
  `"securityCounts.accountAbuse"`); the displayed figures switch to
  the HOST-VERIFIED values; the section shows the verbatim note
  "Mirror mismatch — figures under investigation".
- Null mirror-derived counts (not derivable) are NEVER a mismatch and
  NEVER silently equal — they render with the verbatim reason.
- The mismatch proof (§5.2) must use a non-zero fixture: tamper one
  mirrored ledger total (e.g. add a fake ledger row in the sandbox)
  and assert `mismatch: true`, the field named, and the display
  switching to host-verified. Zeros alone do not prove the rule.

## 3. Migrations — additive migration 0011 + `ingestSecurityState`

### 3.1 Why a singleton row (M7 migration-0007 pattern, design D-M10-1)

The security export is one document per host, replaced wholesale on
each ingest. A singleton row (payload JSON) is the established pattern
(M7 dashboard, M9 profitability). No per-row mirror tables are needed:
the test records and scale levels live inside the payload.

### 3.2 Migration 0011 — `drizzle/0011_security_mirror.sql`

- Creates table `mining_security` with a singleton CHECK (exactly one
  row, id = 1), columns: `id INTEGER PRIMARY KEY CHECK (id = 1)`,
  `payload TEXT NOT NULL` (the full export JSON, secret-pattern-free
  by construction — the host export contains no credential strings),
  `exported_at INTEGER NOT NULL`, `synced_at INTEGER NOT NULL`.
- Journal entry idx 10 (verify at build time; M9 used idx 9). The
  migration must validate on in-memory SQLite (§5.2): singleton CHECK
  enforced (second-row insert rejected), journal well-formed.

### 3.3 `ingestSecurityState` (extend the existing ingest pattern — no new refresh step)

- New action `ingestSecurityState`, on the `ingestProfitabilityState`
  pattern. It takes the host export as its argument and maps it
  EXPLICITLY to the stored payload — the mapping below is binding, and
  is the direct answer to the M9 step-9 failure (do not assume the
  export already has flat top-level arrays; it does not):
  - `exportedAt` ← export.`exported_at`
  - `securityTests[]` ← export.`security_tests[]`, each
    `{id, name, result, evidence, durationMs}` ←
    `{id, name, result, evidence, duration_ms}`
  - `securityCounts` ← export.`security_counts` (snake → camelCase,
    six fields, §2.1 names)
  - `hostVerifiedTotals` ← export.`host_verified_totals` (snake →
    camelCase, four fields)
  - `scale` ← export.`scale` verbatim (nested `l1`–`l5` kept nested;
    the ingest does NOT flatten them; the component reads the nested
    shape per §2.1)
  - `enforcement` ← export.`enforcement` (snake → camelCase, including
    the `sources` map)
  - `redaction` ← export.`redaction` (snake → camelCase)
  - `honestNulls[]` ← export.`honest_nulls[]`
  - `formatValidLine` ← export.`format_valid_line`,
    `ownershipLine` ← export.`ownership_line`,
    `scopeLine` ← export.`scope`
  - `confirmedEarnings` is NOT in the export and NOT stored here — it
    is reused from the dashboard block at `getMining` time (M8
    pattern).
- Missing export (file absent / unparsable) →
  `securityExportMissing: true`, stores nothing, never fabricates.
- Identical re-ingest (same `exported_at` and same payload hash) →
  `upToDate: true`, `synced_at` untouched.
- Newer export → upsert the singleton row, `synced_at` = now.
- The refresh rides the existing refresh flow as its next numbered
  step (M8/M9 pattern). No new ingest action, no new cron, no new
  refresh step. The refresh-task instruction for this step must quote
  the §3.3 mapping (export → ingest payload) verbatim — it must NOT
  say "mapped field-for-field from security.json" without the mapping,
  because the export shape and the ingest shape differ in nesting
  (the M9 step-9 failure, recorded here so it is not repeated).

### 3.4 What this does NOT do (hard limits)

- No repair of any carried issue (M9 mismatch, step-9 transform, M6
  finding 1, stale "no miner yet" copy, refresh-button failure).
- No change to any other section, tab, or action. `Mining.tsx`
  changes by import + one render line only. `RewardAccounting.tsx`,
  `ProfitabilityIntelligence.tsx`, `AdminCommandCenter.tsx`,
  `UserDashboard.tsx` untouched. Start/Stop untouched.
- No token/session/password hash is ever mirrored (the export carries
  none; the ingest stores the payload as-is and the §5.2 grep proves
  it).

## 4. Refresh — rides the existing flow (D-M10-13, D-M10-10)

- The ingest rides the existing `refreshAtlasData` flow as its next
  numbered step (after the profitability step). No new action, no new
  cron, no new refresh step.
- The refresh-task instruction for this step must include the §3.3
  mapping in full (the export nests scale under `scale.l1`–`l5` and
  tests under `security_tests[]`; the ingest payload uses the §2.1
  camelCase names). If the refresh task is ever rewritten, the mapping
  goes with it — the M9 step-9 failure was caused by exactly this
  omission.
- STALE is computed at `getMining` time from the stored
  `exported_at` (§2.2), never from the refresh attempt's own clock.

## 5. Exact file change list and verification

### 5.1 File change list (create/edit, with paths)

- CREATE `client/src/SecurityScaleStatus.tsx` —
  `SecurityScaleStatusSection`, 6 panel groups per §1.3, zero
  buttons/inputs/links/forms, all verbatim strings from §1.2/§1.3
  and the export.
- EDIT `client/src/Mining.tsx` — import + ONE render line directly
  below `ProfitabilityIntelligenceSection`, above Settings. Nothing
  else touched.
- CREATE `server/src/security.ts` — pure derivation/comparison/block-
  assembly (§2.2 rules, mismatch mechanism §2.4), STALE naming,
  host-verified-first display. (M9 pattern: pure module so the sandbox
  proofs run the real code.)
- EDIT `server/src/schema.ts` + CREATE
  `drizzle/0011_security_mirror.sql` + journal idx 10 — singleton
  `mining_security` row (§3.2).
- EDIT `server/src/actions.ts` — `ingestSecurityState` (§3.3),
  `getMining` security block (§2.1/§2.2), `refreshAtlasData` next
  step (§4). No new cron, no new refresh action.

### 5.2 Typecheck + sandbox verification steps (build lane, before handoff to Lane E)

- Typecheck: PASS, exit 0, zero errors (client + server).
- Migration 0011: PASS on in-memory SQLite — singleton CHECK enforced,
  journal idx 10 well-formed.
- Sandbox suite (real `getMining`/`ingestSecurityState` handlers
  invoked end-to-end, in-memory SQLite; live `app.db` never touched;
  durable rows unchanged): minimum 10 tests —
  (a) null export → `securityExportMissing: true`, nothing stored;
  (b) ingest of the real live export shape (use the §0.2 ground-truth
  values as the fixture) → stored, `getMining` returns the §2.3
  expected block, `mismatch: false`;
  (c) identical re-ingest → `upToDate: true`, `synced_at` unmoved;
  (d) mismatch proof (non-zero fixture): add a fake ledger row to the
  sandbox mirror → `mismatch: true`, field named exactly, displayed
  figures switch to host-verified;
  (e) mirror-count mismatch proof: tamper one stored admin-mirror
  event kind → the corresponding count mismatches, field named;
  (f) stale proof: stored export 73 min old → "STALE — security export
  73 min old"; scale run 25 h old → "Scale results stale — last run
  over 24 hours ago";
  (g) NOT_RUN proof: scale `l2` renders the verbatim reason; empty
  scale (`runAt` null) renders the §1.3 empty state;
  (h) FAIL proof: one security test result flipped to FAIL in the
  fixture → the row renders in alert styling with its evidence, and
  the header reads "8/9 security checks passed";
  (i) ingest timing: measure the wall time to ingest a synthetic
  export with 10,000 test-evidence rows (L2 evidence — record the
  measured ms, never invent it);
  (j) confirmed-earnings identity: the security block's earnings equal
  the dashboard block's earnings on the same fixture.
- Grep checks: PASS — zero interactive elements in the new component
  (no `<button`, no `<input`, no `<a `, no `<form`, no `onClick`
  that navigates); zero hardcoded figure literals in the component
  (no `9/9`, no `398.917`, no `1855.1`, no `0 XMR` literals — every
  figure comes from the block); zero secret patterns
  (`token_hash` / `token_salt` / `wallet` / `password` / `seed` /
  `private_key`); all verbatim strings from §1.2/§1.3 present.
- Desktop probe: static render of the real component with a real
  block — 6 panels in order, verbatim copy, zero controls, no
  currency-marked amount, scale table with 3 level rows, L5 bottleneck
  line verbatim, honest-nulls lines verbatim.

## 6. Verification checklist — Lane E (acceptance; execute after deployment)

### 6.1 Rendered checks (fresh interactive audit — desktop 1440 px + mobile 390 px)

- Mining tab selects with zero console errors; the Security & Scale
  section renders directly below the Profitability section, above
  Settings; all 6 panels in order with verbatim copy; zero controls;
  390 px overflow 0.
- The rendered Mining-tab check is the 7th-consecutive-mission gap:
  if the live render cannot be established, record it as NOT
  established with the evidence — do not claim it from the desktop
  probe alone.

### 6.2 Action-layer re-verification (independent, sandbox + live read-only)

- Re-run the §5.2 sandbox suite independently with non-zero fixtures.
- Live `getMining` (coordinator's own check): security block present,
  values match §2.3, `mismatch: false`, `stale: false`,
  `securitySyncedAt` fresh; identical re-ingest `upToDate: true`.
- Secret grep on the live mirror payload: 0 hits.

### 6.3 Explicitly NOT acceptance criteria for this build

- The M9 live mirror mismatch (a different section) is NOT fixed by
  this build and is NOT an acceptance criterion for it.
- The refresh-button failure is NOT fixed by this build.
- The rendered Mining-tab check is NOT claimed by the builder's own
  verification; it is established only by an independent inspection
  with evidence (§6.1).

## 7. Known issues carried (NOT fixed by this spec — D-M10-13)

- M9 live mirror `mismatch: true` (calibration defect) — repair NOT
  authorized.
- Refresh-task step-9 canonical transform (M9 finding 8) — repair NOT
  authorized. This spec's §3.3/§4 mapping exists so the security
  ingest does not repeat the same failure; it does not fix step 9.
- M6 finding 1 (hardcoded zero literals in `RewardAccounting.tsx`) —
  latent, repair NOT authorized.
- Stale "no miner yet" copy (Mining.tsx:234, :1204) — repair NOT
  authorized.
- Refresh-button failure — repair NOT authorized.
- Referral rate 5% unconfirmed; minimum payout null; SupportXMR URL
  unconfirmed; treasury never deposited; Gate 1 unmeasured; rendered
  Mining-tab check not established (7th consecutive mission if not
  established here).
- Host memory above the 70% cap (standing); daemon pid churn
  (standing); mempool.space flapping (standing); `config/atlas.json`
  mempool.space label stale (decision owed).
- The `record_shares` O(n²) bottleneck (M10 scale finding L5) is
  reported, NOT fixed — fixing it needs separate authorization (it is
  a code change to the coordinator's conflict check, not a test).

## 8. Handoff checklist (what the build lane receives, and what is owed onward)

- This spec (§0–§7), the design doc, the live export
  (`data/security.json`, `exported_at` 1795062669 — re-read it live
  before building; a newer coordinator pass may have regenerated it),
  and the §0.2 ground truth.
- The build lane delivers: the §5.1 file changes, the §5.2
  verification results (typecheck, migration, sandbox suite with
  counts, grep checks, desktop probe), the build id, and a deviations
  list (none concealed).
- Owed onward: Lane E independent verification (§6), the coordinator's
  own live `getMining` check (§6.2), and the final mission report.

## 9. Build record (Lane D execution — TO BE FILLED BY THE BUILD LANE)

### 9.1 Files changed (exactly the §5.1 list, or deviations recorded)

- CREATE `client/src/SecurityScaleStatus.tsx` — `SecurityScaleStatusSection`,
  6 panels per §1.3, zero buttons/inputs/links/forms.
- EDIT `client/src/Mining.tsx` — import + ONE render line directly below
  `ProfitabilityIntelligenceSection`, above Settings. Nothing else touched.
- CREATE `server/src/security.ts` — explicit export→payload mapping
  (`mapSecurityExport`), block assembly (`buildSecurityBlock`), exact-integer
  mismatch mechanism (§2.4), STALE naming, singleton upsert.
- EDIT `server/src/schema.ts` + CREATE `drizzle/0012_security_mirror.sql`
  (see deviation 1) — singleton `mining_security` row per §3.2.
- EDIT `server/src/actions.ts` — `ingestSecurityState` (§3.3; takes the raw
  host export and maps it explicitly server-side), `getMining` security
  block (§2.1/§2.2), `refreshAtlasData` step 10 quoting the §3.3 mapping
  in full (§4). No new cron, no new refresh action.
- EDIT `DATA-PLAN.md` — Mission 10 mirror entry with provenance.

### 9.2 Verification results

- Typecheck: PASS, exit 0 (client + server, zero errors).
- Migration: PASS on in-memory SQLite — all 12 migrations apply in order;
  `mining_security` columns per §3.2 (payload/exported_at/synced_at NOT
  NULL); singleton CHECK enforced (id=2 insert rejected, duplicate id=1
  rejected). Journal entry syncs at artifact build (idx 11).
- Sandbox suite (real `getMining`/`ingestSecurityState` handlers,
  in-memory SQLite, live app.db never touched): **43/43 PASS** —
  (a) null export → `securityExportMissing: true`, nothing stored;
  (b) real live export ingest → §2.3 block (see deviation 2 for the two
  re-based values), `mismatch: false`, response schema validates;
  (c) identical re-ingest → `upToDate: true`, `synced_at` unmoved;
  (d) non-zero mismatch proof: fake mirrored ledger row (+5,000,000,000
  piconero user_allocation) → `mismatch: true`, `totalUserRewardsPiconero`
  and `ledgerEntries` named, display switched to host-verified (0);
  (e) count mismatch proof: tampered admin-mirror event kind →
  `securityCounts.accountAbuse` named, host figure (0) still shown;
  (f) stale proofs: 73-min-old export → "STALE — security export 73 min
  old"; 25-h-old scale run → scale stale true;
  (g) null scale and null `run_at` states carried (panel empty state is
  render-proven below);
  (h) FAIL proof: S3 flipped to FAIL → carried with evidence, 8/9 passed;
  (i) L2 sandbox evidence: ingest of a synthetic export with 10,000
  test-evidence rows measured at ~19–41 ms wall time across runs
  (sandbox measurement, recorded as evidence only — never back-filled
  into the host figure, which stays NOT_RUN with its verbatim reason);
  (j) confirmed-earnings identity: security block earnings == dashboard
  block earnings (5,000,000,000 piconero) on the non-zero fixture.
- Render probe (real component, real block from the real handlers,
  react-dom/server): **29/29 PASS** — 6 panels in order; scope line,
  "9/9 security checks passed", "No events recorded", not-derivable
  reason, L5 bottleneck, L2 reason, honest nulls, ownership line,
  format-valid line beside S5, enforcement sources, ESTIMATE projections
  (1,339,432 B / 96,636,832 B), "0 credential-pattern hits across 6 host
  exports" (constructed from block values), 0.000000 XMR confirmed
  earnings — all verbatim; FAIL render shows "8/9 security checks
  passed" + alert styling; missing render shows the verbatim
  not-synced line and no panels; empty-scale render shows the verbatim
  scale empty state; stale render shows both stale tags verbatim;
  rendered HTML contains zero interactive elements.
- Grep checks: PASS — component source: zero `<button`/`<input`/`<a `/`<form`/
  `onClick`; zero hardcoded figure literals (no 9/9, 398.917, 1855.1,
  projection bytes, run timestamps); zero secret patterns; all §1.2/§1.3
  verbatim strings present. Stored payload credential-pattern grep
  (secret-key literals + Monero address-shaped values, the host S6
  pattern classes): 0 hits. Note: the payload contains the bare English
  word "Wallet" once — it is the host's own S5 test name ("Wallet-address
  input validation (full Monero rule set)"), verbatim evidence, not a
  secret or an address.
- Live ground-truth note: the host regenerated `data/security.json`
  after this spec was written (exported_at 1795063157, S1 duration
  901 ms; scale run and all other §0.2 values unchanged, 9/9 PASS).

### 9.3 Deviations (all flagged in §0.1, none concealed)

1. **Migration number 0012, not 0011** (§0.1.3 anticipated): 0011 was
   taken by `0011_smith_research_capacity.sql` (Smith Research capacity
   card, built after this spec), so the next free number was used —
   `drizzle/0012_security_mirror.sql`, journal idx 11.
2. **Two §0.2 ground-truth values re-based**: the live export was
   regenerated by a newer host pass before the build (exported_at
   1795062669 → 1795063157; S1 duration_ms 256 → 901). The sandbox suite
   asserts these two against the fixture's own values; every other
   §0.2/§2.3 value is asserted verbatim and passes.
3. **`ingestSecurityState` takes the raw host export** and performs the
   §3.3 mapping server-side (`mapSecurityExport`), rather than the
   refresh task pre-mapping to camelCase: the step-10 instruction passes
   the file verbatim and quotes the mapping in full. This is the direct
   structural answer to the M9 step-9 failure (the mapping lives in
   tested code, not only in task prose) and matches §3.3's wording
   ("takes the host export as its argument and maps it EXPLICITLY to
   the stored payload").
4. **Ledger totals display**: the four cross-checked totals are shown
   in panel 1 under "Ledger totals — mirror cross-check" as raw
   piconero counts (per §1.1, XMR formatting appears only in the
   reused confirmed-earnings row), so the §2.4 display switch to
   host-verified figures is visible in the section.

### 9.4 Open items owed onward

- Lane E independent verification (§6); coordinator live `getMining`
  check; final mission report.
- The rendered Mining-tab check remains Lane E's to establish (§6.1) —
  the builder's render probe is a server-side render of the real
  component, not a live-tab inspection.
