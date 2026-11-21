# ATLAS — Master Mission 10: Security and Scale Testing — Design

**Mission:** Master Mission 10 (security and scale testing).
**Authorized:** User authorized Master Mission 10 on 2026-11-18 ~22:01 EST
("Yep, do it" in the ATLAS side chat).
**Artifact:** `atlas-command-center` (current build `2131aa37`, Mission 9).
**Status:** DESIGN — binding on the build (Lane C), UI (Lane D), and
verification (Lane E) lanes. Nothing in this document is built yet.

## 0. Grounding — what this design rests on

- **Mission 6** (`docs/master-mission6-design.md`, `core/atlas_rewards.py`):
  the 75/25 reward engine — integer-piconero split, append-only ledger with
  SHA-256 hash chain (`verify_chain()`, 5-step), share dedupe on
  `(worker_id, external_id)` + NULL-`external_id` exclusion, batch
  exactly-once via `UNIQUE(pool_name, source_ref)` + `UNIQUE(share_id)`,
  payout idempotency keys (`payouts.idempotency_key` UNIQUE INDEX),
  referrals 5% from the ATLAS 25% only, simulation batches settle while the
  stop is ON, real-mode batches REFUSED while the stop is ON or mode is
  `simulation-only`, payout-shaped calls refused with a logged refusal
  (Gate 4 closed). M6 test-8 deviation (documented, carried): the design's
  literal sequence (tamper a committed row, then add reversal + corrected
  entry, then expect `verify_chain()` PASS) is impossible — a hash-mismatched
  row can never verify. The correct test asserts FAIL naming the tampered
  entry, then runs reversal + correction on a fresh temp DB.
- **Mission 5** (`core/atlas_coordinator.py`): per-worker tokens — scrypt
  hash + per-worker salt stored only, token returned once at registration,
  `verify_worker_token()` with `hmac.compare_digest`; browser workers get no
  token (`token_hash`/`token_salt` NULL); `session_token_hash` stores the
  marker `none:browser-probe` for browser probes (D-M5-1, carried).
- **Mission 3** (`docs/master-mission3-validation-spec.md` §1f): the full
  Monero address validation rule set — 95 chars (`4` standard / `8`
  subaddress) or 106 chars (`4` integrated); Monero Base58 alphabet (reject
  `0`/`O`/`I`/`l`); Monero block-wise Base58 (8 bytes → 11 chars);
  decoded 69 or 77 bytes; network byte 18/19/42 mainnet only (53/54/63
  testnet, 24/25/36 stagenet rejected); checksum = first 4 bytes of
  **Keccak-256 (original Keccak, NOT NIST SHA3-256)** over all preceding
  bytes. Validation proves format only, never ownership (M3 §1g).
- **Mission 8** (`core/atlas_admin.py`, D-M8-3/D-M8-4): no private data ever
  — aggregates only, defensive redaction (§1.2) of decisions/events
  messages, security counts per binding §4 definitions, 0 renders the
  verbatim empty state "No events recorded".
- **Mission 9** (`core/atlas_profitability.py`): the guarded coordinator
  sub-step pattern (read-only derivation, never fails the pass, logs no
  decision of its own), the atomic export pattern (temp + `os.replace`),
  the mirror-mismatch rule, and the STALE rule.
- **Carried state (M9 report):** live ledger 0 rows, reward_batches 0,
  payouts 0, shares 0, workers 0, users 0; emergency stop ON;
  `config/pool-rewards.json` mode `simulation-only`; diagnostics 26 tests;
  rendered Mining-tab check still NOT established (6th consecutive mission);
  live M9 mirror `mismatch: true` (calibration defect, NOT repaired here);
  refresh-task step-9 mapping stale (NOT repaired here); M6 finding 1
  (hardcoded zero literals) latent; stale "no miner yet" copy; refresh-button
  failure; referral rate 5% unconfirmed; minimum payout null; SupportXMR URL
  unconfirmed; Gate 1 unmeasured (hashrate "not measured").

## Decisions (binding on the build lane)

- **D-M10-1:** Host is the system of record; artifact tables are a read-only
  display mirror. Security and scale figures are DERIVED by the host module
  from live reads + temp-DB test fixtures at export time — no new stored
  truth. **No new host DB tables.** One new host export,
  `data/security.json` (atomic write). One new artifact mirror singleton
  row (migration 0011 — verify the next free number at build time; M9 used
  0010).
- **D-M10-2:** Estimated vs confirmed (M7 §3 / M8 §3 / M9 §3, carried
  verbatim): every profitability figure is an ESTIMATE; confirmed earnings =
  ledger `SUM`, SIMULATION-tagged, reused from the dashboard export by
  import, never recomputed. Estimate and confirmed are never combined.
  Security test results are TEST EVIDENCE, not earnings: a pass/fail count
  is a count of checks run, never a balance, never a promise.
- **D-M10-3:** **No fiat in the panel.** Timings in milliseconds/seconds;
  sizes in bytes/KB/MB; XMR to 6 decimals from integer piconero where a
  money figure appears at all (the security section shows no money figures
  except the reused confirmed-earnings block, which is 0 / SIMULATION-tagged
  on the live system). Test counts are integers. No percentage is ever shown
  without its numerator and denominator beside it.
- **D-M10-4:** Security test definitions (§4, binding). Each security check
  is a named, repeatable check with a defined pass condition, a defined
  fixture, and a recorded evidence string. Checks that mutate state run on
  TEMP DBs only, never the live DB. Checks that read live state are
  read-only (grep, COUNT/SUM, config read). No check ever creates a wallet,
  key, token, or payout on the live system.
- **D-M10-5:** Tamper-evidence semantics (M6 test-8 deviation, carried):
  tampering a committed ledger row MUST make `verify_chain()` FAIL and name
  the tampered entry. A correction is only ever a `reversal` entry plus a
  new corrected entry on a fresh fixture; the tampered row itself is never
  edited back into validity. The test asserts FAIL first, then the
  reversal path on a fresh temp DB.
- **D-M10-6:** Scale testing is ON-DEMAND (CLI), never inside the
  coordinator pass. The synthetic load runs on temp DBs only, is marked
  synthetic in every row it creates, and is destroyed afterwards (temp
  files in `/tmp`, removed at test end). The coordinator sub-step only
  re-exports the last recorded scale results plus fresh security
  derivations; it never runs a load test. The 10-minute pass must never
  grow a load test.
- **D-M10-7:** Address validation — the full M3 §1f rule set, in order,
  fail fast. Keccak-256 is implemented in pure Python inside the host
  module (stdlib only); NIST SHA3-256 (`hashlib.sha3_256`) is FORBIDDEN for
  this purpose and the module must assert the Keccak test vector
  Keccak-256("") =
  `c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470`
  at import/test time. Validation proves format only, never ownership
  (M3 §1g) — the UI says so verbatim.
- **D-M10-8:** Redaction — no `token_hash`, `token_salt`, `wallet`,
  `password`, `seed`, or `private_key` string appears in any host export,
  in `data/security.json`, or in the UI. Grep-enforced in the module tests,
  in the diagnostics test, and in the Lane D sandbox checks. The admin
  §1.2 defensive redaction is carried for any decision/event text the
  security export repeats.
- **D-M10-9:** Stop/mode enforcement — real-mode batch recording,
  payout-shaped calls, and mining start are all REFUSED while the emergency
  stop is ON; real-mode settlement is additionally refused while mode is
  `simulation-only`. Every refusal is logged as a decision with reason.
  The test asserts the refusal, never performs the refused action.
- **D-M10-10:** STALE rules (M8 §6 pattern) — the section is STALE when the
  security export is > 1 h old, with the tag naming the stale export;
  "Not computed yet" when the export has never been written; identical
  re-ingest reports "already up to date" and never advances `syncedAt`.
- **D-M10-11:** MIRROR-MISMATCH rule (M7 §6 / M8 §7 / M9 §7, carried) — on
  any disagreement between mirror-derived security counts and
  host-verified counts, show the HOST-VERIFIED counts plus the verbatim
  "Mirror mismatch — figures under investigation" note, never silently
  present mirror rows as real. No hardcoded figure literal is permitted in
  the section (grep-enforced). The rule must be tested with non-zero
  fixtures, not zeros alone.
- **D-M10-12:** Placement directly below the Profitability section, above
  Settings; no new tab; zero buttons/inputs/links/forms; Start/Stop
  untouched.
- **D-M10-13:** No new cron; the export rides the coordinator pass as a
  guarded sub-step; every figure carries its provenance; this design does
  NOT repair any carried issue (M9 mismatch, step-9 transform, M6 finding
  1, stale "no miner yet" copy, refresh-button failure, referral rate,
  minimum payout, SupportXMR URL, Gate 1).

## 1. Data rules — derived only; no new host tables

- The host module `core/atlas_security.py` (stdlib-only) derives everything
  from: live DB reads (COUNT/SUM, `verify_chain()` on the live ledger),
  live config reads (`config/atlas.json`, `config/pool-rewards.json`),
  live export greps, and temp-DB fixtures it builds and destroys itself.
- **No new host DB tables. No migration.** The module writes no ledger
  rows, no decisions, no shares, no batches, no payouts — its only write
  is the atomic `data/security.json` export (temp + `os.replace`).
- The export carries: `exported_at`, `emergency_stop`, `mode`,
  `security_tests` (one record per check: id, name, result PASS/FAIL/
  NOT_RUN, evidence string, duration_ms), `security_counts` (the six M8 §4
  counts, re-derived live), `scale` (last recorded scale-test results +
  the run's timestamp, or null + verbatim reason when never run),
  `host_verified_totals` (ledger/batches/payouts counts + SUMs, for the
  mirror comparison), `redaction` (grep result: 0 hits, with the pattern
  list), and `provenance` (module version, DB `user_version`, config
  sha256 short hashes).
- Scale-test results are recorded, not recomputed: the export stores the
  last on-demand scale run's figures verbatim, with its timestamp. A scale
  run older than 24 h is labelled STALE in the panel (verbatim
  "Scale results stale — last run over 24 hours ago") but is still shown;
  it is never silently presented as fresh.

## 2. Data flow and provenance

- Host: `security_status(con, export_dir)` runs the security battery and
  returns the export dict; `export_security_json()` writes it atomically;
  CLI `status | export | run-tests | run-scale`.
- `run-tests` (the security battery) is safe to run on the live DB because
  every mutating check uses its own temp DB; the live-DB checks are
  read-only. `run-scale` (the load test) ALWAYS uses a temp DB, never the
  live DB, even when invoked with a live path — the module refuses a
  non-temp path for scale runs.
- Coordinator: one guarded security sub-step in `run_pass()`, placed after
  the profitability sub-step (M6/M7/M8/M9 pattern, +~12 lines): it calls
  `export_security_json()` inside try/except, logs no decision of its own,
  and can never fail the pass. It does NOT run `run-tests` fixtures that
  take measurable time beyond the export itself; the battery is fast
  (target: the whole export, battery included, under 5 s on the live DB
  with the live ledger empty; the scale load is never in the pass —
  D-M10-6).
- Artifact: `ingestSecurityState` mirrors the export into the singleton
  `mining_security` row; `getMining` gains a `security` block; the refresh
  rides the existing refresh flow as its next numbered step (M8/M9
  pattern). No new cron, no new refresh action.
- Provenance: every figure in the panel names its source (host export,
  mirror derivation, or temp-DB fixture). Fixture-derived figures are
  labelled "test fixture — not live data" wherever they appear.

## 3. Estimated vs confirmed — the hard rule (M7 §3, M8 §3, M9 §3, carried verbatim)

- Estimated earnings are null with the verbatim reason "Cannot estimate —
  hashrate not measured" while Gate 1 is unmeasured. Confirmed earnings =
  ledger `SUM`, SIMULATION-tagged, reused from the dashboard export by
  import, never recomputed. The security section reuses the dashboard
  earnings block by import (M8 pattern) and must never show a different
  earnings number than the user dashboard.
- Security test results are not earnings and are never combined with
  earnings. A "12/12 security checks passed" line is a test count, not a
  safety guarantee: the panel carries the verbatim line "Passing these
  checks does not guarantee the system is secure — it proves these
  specific attacks were detected or refused in testing."

## 4. Security test definitions (binding)

Each check: id, name, fixture, pass condition, evidence recorded.

### S1 — Ledger tamper-evidence (hash chain)
- Fixture (temp DB): record a simulation batch via `atlas_rewards`
  (1 XMR, 2 users, one referred — the M6 scenario-1 shape), settle it,
  assert `verify_chain()` PASS and 5 ledger entries.
- Tamper: UPDATE one committed entry's `amount_piconero` by +1 on the
  temp DB copy. Assert `verify_chain()` FAILs and the error names the
  tampered entry id.
- Correction path (fresh temp DB, same fixture): record a `reversal`
  entry for one entry via `record_reversal()`, then a corrected entry;
  assert `verify_chain()` PASSes, the original entry is still visible,
  and balances reflect the reversal. (M6 test-8 deviation, D-M10-5.)
- Live check (read-only): `verify_chain()` on the live DB — expected
  trivial PASS, 0 entries ("ledger empty — chain trivially valid").

### S2 — Share dedupe
- Fixture (temp DB): register a worker, record a share with
  `external_id` "share-A" via `record_shares()`; record the identical
  `(worker_id, external_id)` again; assert the second is rejected (not
  inserted, counted as duplicate) and attribution weights count the
  share once. Record a NULL-`external_id` pool share; assert it is
  excluded from attribution and counted. Record the same `external_id`
  under a different worker; assert it is treated as a separate share
  (dedupe key includes worker_id) — or, if the engine dedupes globally,
  record the actual behaviour and assert it matches the engine's
  documented rule; do not assert a behaviour the code does not have.
- Live check (read-only): duplicate-share count from live SQL (M8 §4
  definition) — expected 0 on the live system.

### S3 — Payout idempotency
- Fixture (temp DB): create a user with a settled allocation (reuse the
  S1 fixture); call `request_payout()` twice with the same idempotency
  key; assert exactly one payout row exists and the second call returns
  the same result without a new row. Call `settle_batch()` twice on the
  same settled batch; assert the second is a no-op (no new ledger
  entries, same result). Directly insert a duplicate idempotency key on
  a temp DB copy; assert the UNIQUE constraint rejects it.
- Live check (read-only): payouts count 0 on the live DB.

### S4 — Per-worker token handling
- Fixture (temp DB): `register_worker()` with a token; assert the token
  is returned exactly once (the return value), the DB stores only
  `token_hash` (64-hex scrypt) + `token_salt`, and a grep of the temp DB
  file for the plaintext token finds 0 hits. `verify_worker_token()`
  accepts the correct token and rejects a wrong token and an empty
  token. `rotate_token()` invalidates the old token (old fails, new
  passes). Browser worker registration stores NULL hash/salt.
- Live check (read-only): workers count 0 on the live DB; no token
  material exists on the live system.

### S5 — Wallet-address input validation (full Monero rule set)
- Pure-Python Keccak-256 in the host module; the module asserts the
  Keccak-256("") test vector at test time (D-M10-7).
- Test vectors (constructed, not copied from any live user): build a
  valid standard address from chosen payload bytes (network byte 18 +
  64 key bytes + Keccak-256 checksum, Monero block-wise Base58 encode)
  and assert ACCEPT; build a valid subaddress (byte 42) and a valid
  integrated address (byte 19 + 8-byte payment id) and assert ACCEPT.
- Rejections (each asserted with its exact reason string): wrong length
  (94 / 96 / 105 chars); forbidden characters `0`, `O`, `I`, `l`;
  first-char/length mismatch (95 chars starting `9` — testnet shape);
  testnet network byte 53; stagenet network byte 24; decoded length not
  69/77; checksum mismatch (one character flipped in a valid address).
- The UI carries the verbatim line "Format valid — ownership not
  verified" (M3, carried) and the verbatim line "Validation checks the
  address format only. It does not prove who owns the address."

### S6 — Admin data redaction
- Live check (read-only): grep `data/admin.json`, `data/security.json`,
  `data/rewards.json`, `data/dashboard.json`, `data/coordinator.json`,
  `data/profitability.json` for `token_hash`, `token_salt`, `wallet`,
  `password`, `seed`, `private_key` — assert 0 hits in every file.
- Fixture: feed the admin redaction function a decision reason
  containing a fake 64-hex token and a fake wallet-shaped string;
  assert both are replaced by `[redacted — possible credential]` and
  the row is still counted.
- Live check: the six M8 §4 security counts re-derived from live SQL
  match the counts in `data/admin.json`.

### S7 — Emergency-stop enforcement
- With the live config (`emergency_stop: true`, read-only): assert
  `record_batch(..., mode="real")` on a temp DB is REFUSED (raises or
  returns a refusal — assert the actual refusal path, do not perform
  the recording); assert a payout-shaped call (`request_payout()`) on a
  temp DB is REFUSED with a logged refusal; assert mining cannot start
  (`config/atlas.json` `mining.enabled` is false and no start handler
  exists — assert the config value and that no `start_mining` entry
  point exists in the coordinator/monitor code by grep).
- Live check: `emergency_stop` true in `data/snapshot.json` and in the
  config; no mining process running.

### S8 — Simulation-only enforcement
- Read `config/pool-rewards.json` (read-only): assert `mode` is
  `"simulation-only"`. On a temp DB, assert a real-mode settle attempt
  is REFUSED while mode is simulation-only. Assert `minimum_payout` is
  null (undecided — recorded as a fact, not a pass/fail).
- Live check: no real-mode batch exists on the live DB (batches 0).

### S9 — No private data leaves the host
- The security export itself is grepped (S6 patterns) — 0 hits.
- Assert the export contains no wallet address, no token, no session
  value, no key material — only counts, timings, test results, and
  derived totals. Assert no export file in `data/` contains a value
  matching a Monero address shape (95/106-char Base58) — a wallet
  address must never appear in an export.
- Honest null: the module cannot prove what the artifact mirror
  contains; the UI mirror check (Lane D sandbox + coordinator live
  `getMining`) covers the mirror side.

## 5. Scale test definitions (binding)

All scale runs are on-demand CLI (`run-scale`), temp DB only, synthetic
data marked synthetic, destroyed after (D-M10-6). The export records the
last run's figures with its timestamp; the panel never recomputes them.

### L1 — Coordinator pass under load
- Fixture (temp DB): N synthetic workers (1,000) and M synthetic
  accepted shares (100,000) across them, plus 100 synthetic sessions.
- Measure: `run_pass()` wall time on the temp DB; `record_shares()`
  throughput (shares/second for a 1,000-share batch); `attribution_weights()`
  time; `verify_chain()` time on a temp ledger with 10,000 entries.
- Report per load level: workers, shares, DB file size, pass time,
  slowest step. The load levels are 1× (current live: 0 workers, 0
  shares — the honest baseline), 100 workers / 10,000 shares, and
  1,000 workers / 100,000 shares. Do not claim a level was tested if it
  was not run.

### L2 — Mirror ingest time with large exports
- Fixture: a synthetic `security.json`-shaped export with 10,000 test
  evidence rows (generated, marked synthetic) — measure the time to
  parse + mirror it in the Lane D sandbox (the artifact side, not the
  host). If the sandbox cannot be run, record NOT_RUN with the verbatim
  reason "Mirror ingest timing not measured — sandbox unavailable" —
  never invent a number.

### L3 — Diagnostics runtime as the ledger grows
- Measure the full diagnostics suite wall time on (a) the live DB and
  (b) a temp DB with a 10,000-entry ledger. Report both. The suite must
  complete in under 120 s on the live DB; on the temp ledger the time is
  recorded as evidence, not a pass/fail gate.

### L4 — DB size growth projection
- Measure bytes-per-row for shares, ledger entries, decisions, metrics
  from the temp fixtures; project DB size at 10,000 / 100,000 /
  1,000,000 shares with the formula shown in the export
  (`size ≈ base + rows × bytes_per_row`). Projection only — labelled
  ESTIMATE, never a measurement.

### L5 — First bottleneck
- Identify the first bottleneck and the load at which it appears: the
  step whose time grows super-linearly with load, or the first load
  level where `run_pass()` exceeds 60 s (10% of the 10-minute budget)
  or any single step exceeds 30 s. If no bottleneck appears at the
  tested loads, record verbatim "No bottleneck found up to 1,000
  workers / 100,000 shares — not tested beyond that load" — never claim
  the system scales beyond the tested load.

## 6. STALE rules (M8 §6 pattern, D-M10-10)

- Section STALE when the security export is > 1 h old; the tag names the
  stale export ("STALE — security export 73 min old"). "Not computed yet"
  when the export has never been written (the section renders its honest
  export-missing state). Scale results older than 24 h carry the verbatim
  "Scale results stale — last run over 24 hours ago" tag and are still
  shown, never silently fresh.
- Identical re-ingest reports "already up to date" and never advances
  `syncedAt`. Missing export → `securityExportMissing: true`, stores
  nothing, never fabricates.

## 7. MIRROR-MISMATCH rule (M7 §6 / M8 §7 / M9 §7, carried — D-M10-11)

- On any disagreement between mirror-derived security counts/totals and
  host-verified counts/totals, show the HOST-VERIFIED figures plus the
  verbatim "Mirror mismatch — figures under investigation" note. The
  disagreeing fields are named exactly in `mismatchDetails`.
- The host-verified totals are recomputed server-side from the mirrored
  rows only for the display comparison; the host export's figures are
  authoritative.
- No hardcoded figure literal is permitted in the section (grep-enforced
  in Lane D). The mismatch proof must use a non-zero fixture (a tampered
  mirror count), not zeros alone.
- Note the M9 lesson: rounding and unit differences are mismatch causes,
  not display errors. The security section compares integers only
  (counts, piconero) — no float rounding is involved — so a mismatch
  here means a real disagreement, and the host figure wins.

## 8. UI spec — Security & Scale status section in the Mining tab (exact, build-ready)

### 8.1 Placement and rules

- Component `client/src/SecurityScaleStatus.tsx`,
  `SecurityScaleStatusSection`. Rendered by ONE line in `Mining.tsx`
  directly below `ProfitabilityIntelligenceSection`, above Settings.
  Tab order otherwise unchanged. No new tab.
- Zero buttons/inputs/links/forms. Start/Stop untouched. No hardcoded
  displayed figures (grep-enforced). XMR to 6 decimals from integer
  piconero where money appears (only the reused confirmed-earnings
  block). Test counts as integers with numerator and denominator.
  Timings in ms or s with units. No fiat.
- Scope line (verbatim, top of section): "Security & scale status —
  test evidence only. Passing these checks does not guarantee the system
  is secure — it proves these specific attacks were detected or refused
  in testing."
- Mirror: `server/src/schema.ts` + additive migration
  `drizzle/0011_security_mirror.sql` (verify the next free number at
  build time; M9 used 0010) adding the singleton `mining_security` row
  (payload JSON, no secret columns). `ingestSecurityState` on the
  `ingestProfitabilityState` pattern (missing export →
  `securityExportMissing: true`, stores nothing; identical re-ingest →
  `upToDate`, `synced_at` untouched). `getMining` gains the `security`
  block computed server-side from the mirrored row only, with
  `mirrorDerivedTotals`, `hostVerifiedTotals`, `mismatch` boolean +
  `mismatchDetails`. The refresh rides the existing refresh flow as its
  next numbered step (M8/M9 pattern). No new ingest action, no new
  cron, no new refresh step.
- The section reuses the dashboard earnings block by import (M8
  pattern) and must never show a different earnings number than the
  user dashboard.

### 8.2 Panels (verbatim headings, labels, empty states)

1. **"Security tests"** — one row per check S1–S9: check id + name,
   result (PASS / FAIL / NOT_RUN), evidence string, duration. Header
   line: "N/M security checks passed" (N and M as integers, e.g.
   "9/9 security checks passed"). A FAIL row renders in the section's
   alert styling with its evidence string. A NOT_RUN row renders the
   verbatim reason (e.g. "Not run — fixture unavailable").
2. **"Live security counts"** — the six M8 §4 counts (suspicious
   workers, invalid shares, duplicate shares, account abuse, auth
   failures, payout anomalies), each with its count and the verbatim
   empty state "No events recorded" when 0. Counts are host-verified;
   on mismatch the host figure is shown with the §7 note.
3. **"Scale test results"** — the last on-demand scale run: run
   timestamp, load levels tested (workers/shares), `run_pass()` wall
   time per level, slowest step, DB size per level, diagnostics runtime
   (live DB and 10,000-entry temp ledger), size projection table
   (10k / 100k / 1M shares, labelled ESTIMATE), and the first-bottleneck
   finding (verbatim, §5 L5). When no scale run exists, the verbatim
   empty state "No scale test run yet — run the on-demand scale test
   from the host to populate this panel" (the panel never invents a
   number; there is no button to run it from the UI — zero controls).
   Scale results older than 24 h carry the §6 stale tag.
4. **"Enforcement status"** — emergency stop (ON/OFF with timestamp),
   mode (simulation-only), real-mode batches refused (count of refusals
   logged, 0 on the live system), payout-shaped calls refused (count),
   mining start (verbatim "Mining is not active — no start path exists
   while the emergency stop is ON" when disabled). Each line names its
   source (config, snapshot, or decision log).
5. **"Honest nulls"** — every check that could not run, with its verbatim
   reason: e.g. "Gate 1 unmeasured — hashrate not measured, so no
   load-based earnings projection exists"; "No live workers — token,
   share, and payout tests run on test fixtures only, not live data";
   "Rendered Mining-tab check — not established by this mission" (carried
   honestly if the live render is not independently established).

## 9. Carried issues — NOT fixed by this design (D-M10-13)

- M9 live mirror `mismatch: true` (calibration defect: host rounding vs
  1e-9 tolerance, GPU units, GPU null-scope, browser split rows) — needs
  a repair-authorized inspection + edit. NOT repaired here.
- Refresh-task step-9 canonical transform (M9 finding 8) — the hourly
  refresh job needs the hand mapping, or the mirror goes stale. NOT
  repaired here. Note for Lane D: the security ingest must use the same
  canonical-transform approach the coordinator used for M9 (map the
  export shape to the ingest action's shape explicitly); if the refresh
  task's step numbering assumes a shape the export does not have, record
  it as a finding, do not silently reshape the export.
- M6 finding 1 (hardcoded zero literals in `RewardAccounting.tsx`) —
  latent, repair NOT authorized.
- Stale "no miner yet" copy (Mining.tsx:234, :1204) — repair NOT
  authorized.
- Refresh-button failure (the in-app refresh button + background task
  remains the broken path; the hourly fallback works) — repair NOT
  authorized.
- Referral rate 5% unconfirmed; minimum payout null; SupportXMR URL
  unconfirmed; treasury never deposited; Gate 1 unmeasured; rendered
  Mining-tab check not established (6th consecutive mission — this
  mission does not claim it either, unless Lane E or an independent
  inspection establishes it with evidence).
- Host memory above the 70% cap (standing); daemon pid churn (standing);
  mempool.space flapping (standing); `config/atlas.json` mempool.space
  label stale (decision owed).

## 10. Verification requirements (binding on the build/test lanes)

- **Lane C (host build):** `core/atlas_security.py` (stdlib-only) +
  `core/test_atlas_security.py` — every §4 check as a test (S1–S9) plus
  the §5 scale tests (L1–L5, on-demand); `security_status()` +
  `export_security_json()` + CLI `status | export | run-tests |
  run-scale`; one guarded coordinator sub-step after the profitability
  sub-step (M6–M9 pattern, +~12 lines, logs no decision, never fails
  the pass); diagnostics tests **27** ("security export": file parses,
  fresh, security counts match fresh live SQL, host-verified totals
  match, no secret strings, all S1–S9 results present) and **28**
  ("scale smoke": temp-DB load of 100 workers / 10,000 shares runs and
  the export's scale block is populated or honestly null with the
  verbatim reason — the full L1–L5 run is on-demand, the diagnostics
  test asserts only the smoke level). Full diagnostics suite must pass
  (28/28) on the final run. All unit suites re-run unmodified
  (coordinator 19/19, rewards 20/20, dashboard 4/4, admin 5/5,
  profitability 11/11 — total 59/59 + the new security suite).
- **Lane D (UI):** typecheck PASS; migration 0011 validated on in-memory
  SQLite (singleton CHECK, journal idx well-formed); sandbox suite with
  real handlers (ingest + getMining end-to-end, non-zero fixtures);
  mismatch proof (tampered mirror count → `mismatch: true`, field
  named, display switches to host-verified); stale proof; null-export
  proof; identical re-ingest `upToDate`; grep checks (zero interactive
  elements, zero hardcoded figure literals, zero secret patterns, all
  verbatim strings present); desktop probe (static render of the real
  component with a real block).
- **Lane E (independent host verification):** re-derive every
  `security.json` figure from fresh SQL/temp fixtures with its own
  scripts (no import of the module); re-run all suites + diagnostics
  independently; verify the coordinator sub-step guard on a temp DB
  (decisions exactly +1 per pass, all six exports fresh); verify no
  writes by the security module (no decisions/ledger/shares/batches on
  the live DB attributable to it); secret grep on live + temp exports;
  verify the scale figures by re-running the scale smoke independently.
- **Coordinator's own live check:** `getMining` security block after
  seeding the mirror with the real host export — record `mismatch`,
  `stale`, `securitySyncedAt`, and every panel's live values verbatim.
- **Report:** `docs/master-mission10-report-2026-11-18.md` with the
  verdict, build id, test-evidence table, safety verification, files
  changed, deviations, unresolved findings, and authorization needed.
  **STOP after Mission 10; do NOT start Mission 11.**
