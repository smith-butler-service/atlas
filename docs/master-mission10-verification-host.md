# ATLAS Master Mission 10 — Host Verification (Lane E, independent)

- **Lane:** E (independent host verification) — read-only except running the
  existing test suites and diagnostics (the established method) and temp-DB
  checks in `/tmp`. No host file, config, or database row was edited; the
  artifact was not touched.
- **Verification window:** 2026-11-19 04:31:46–04:55:42 UTC (2026-11-18
  23:31:46–23:55:42 EST).
- **Verifier note:** nothing from Lane C was taken on trust. Every
  `data/security.json` figure was re-derived from fresh SQL / temp fixtures
  with this lane's own scripts (which do not import `atlas_security`); the
  Keccak-256 implementation and the Monero address validation are this
  lane's own code, written from the Keccak spec and the M3 §1f rule set.
  The scale figures were re-measured on this lane's own temp DBs, and the
  O(n²) claim was checked with this lane's own `EXPLAIN QUERY PLAN`.
  Two exports were examined: Lane C's export (`exported_at` 1795062669,
  read in full at 04:32 UTC) and the export re-issued by my own
  diagnostics run (`exported_at` 1795063315) — the battery evidence
  strings are identical between the two.
- **Overall verdict: PASS — 9/9 areas pass, zero mismatches, zero defects
  in the delivered state.** Two observations (L5 test fragility on a much
  faster host; pre-existing unit-suite temp files in `/tmp`) and two
  carried issues (host memory above the 70% cap; rendered Mining-tab check
  still not established); none is a defect in Mission 10's delivery. One
  defect WAS found during Lane C's own work (a scale-test failure, run 3)
  and fixed before delivery — see §9 and Observation 1; my independent
  run of the fixed code passes.

## Summary

| Area | Verdict | Headline evidence |
|---|---|---|
| 1. Daemon | PASS | Exactly 1 pid at every check (14586 → 15593 → 16136, all by-design diagnostics restarts); snapshot fresh (age 43–59 s), emergency_stop true |
| 2. DB integrity | PASS | `integrity_check` ok, `user_version` 3; all mining tables 0; decisions 449 → 459, events 151 → 155, metrics 1503 → 1516, pool_stats 65 → 66 — every delta explained (§2) |
| 3. No writes by the security module | PASS | 0 decisions mentioning security/scale ever; source audit: the module's only UPDATE/INSERT/DELETE sites target temp-DB connections (`tcon`); live `con` is never written; 0 `atlas-m10-*.db` temp files left |
| 4. Configs unchanged | PASS | sha256 `46d3d12c…` / `b01a22ad…` — exact match to baseline |
| 5. Re-derive every security.json figure | PASS | Own Keccak-256 verifies the test vector and differs from SHA3-256; own address validation accepts constructed standard/subaddress/integrated and rejects all documented cases (Part 1: 40/40); S1–S9 re-derived on own temp fixtures (Part 2: 50/50), including exact reproduction of the S1 evidence numbers (tampered entry 4; balances alice 15000000000, bob 300000000001); all live counts/totals/provenance re-derived (Part 3+4 script: 56/57 — the one miss was my first L4 replication with shorter synthetic IDs; exact-shape replication: 96.67 vs 96.26, 0.4%) |
| 6. Scale re-verification | PASS | Own smoke: 100 workers / 10,000 shares in 2.74 s (3,651.7 shares/s) vs Lane C 1,855.1/s — same order of magnitude; diagnostics test 28 on my run: 1,813.2/s; `EXPLAIN QUERY PLAN` confirms a full index SCAN per share (O(n²)); L4 bytes-per-row reproduced exactly with matching fixture shapes (96.67 vs 96.26, 0.4%); L5 clause-1 breach re-derived by hand from the recorded levels |
| 7. Full test suites + diagnostics | PASS | Security **18/18 OK** (357.354 s, my run); other suites **59/59 OK** (22.9 s); diagnostics **28/28 PASS** (25.8 s, first run — no 14/18 flapping) |
| 8. Coordinator sub-step guarded | PASS | Temp-DB `run_pass`: decisions exactly +1 (`coordinator-pass-complete`); all six exports fresh; security export stamped seconds after the other five (expected skew, §8); scale block preserved across re-export (carry-over, run_at 1795062216) |
| 9. Deviations + secrets + STALE | PASS | D-M10-C1–C5 all confirmed; L5 rule fix confirmed (see §9); t27 stricter than design confirmed; secret grep 0 hits on live + temp exports; 0 address-shaped values in any export |

## 1. Daemon — PASS

- `pgrep -a -f 'python3 core/atlas_monitor.py'` = **1 pid at every check**:
  **14586** at lane start (04:32:00 UTC), **15593** before my diagnostics
  run, **16136** at close (04:55:42 UTC). The pid changes are the
  by-design restarts from diagnostics tests 10/11 (my security suite's
  L3 leg, then my diagnostics run). (A bare `pgrep -c` count of 2 during
  one check was my own shell wrapper matching, as the M10 baseline
  warns; `pgrep -a` confirmed exactly 1 daemon pid.)
- `data/snapshot.json` fresh throughout: ts 1795062661 (age 59 s) at
  start; ts 1795063299 (age 43 s) at close. `mining: "disabled"`,
  `trading: "disabled-paper-only"`, `emergency_stop: true`, `gpu: null`.
  Memory 84.78–88.29% used (above the 70% cap — standing carried issue,
  not new).

## 2. DB integrity — PASS

Read-only (`mode=ro`) checks at 04:32, 04:54, and 04:55 UTC:

| Check | 04:32 (start) | 04:55 (close) |
|---|---|---|
| `PRAGMA integrity_check` | ok | ok |
| `PRAGMA user_version` | 3 | 3 |
| DB size | 376,832 B | 380,928 B (metrics/decisions rows only) |
| users / workers / shares / sessions | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| ledger / reward_batches / reward_batch_shares | 0 / 0 / 0 | 0 / 0 / 0 |
| payouts / referrals / achievements | 0 / 0 / 0 | 0 / 0 / 0 |
| pool_stats | 65 | 66 |
| decisions | 449 | 459 |
| events | 151 | 155 |
| metrics | 1503 | 1516 |

- Decisions 449 → 459 = **+10, fully explained, none from the security
  module:** +4 — my security suite's L3 diagnostics leg, test 07
  (decide-pass quartet); +2 — coordinator pass 04:40:56 UTC (ids 454
  `pool-stats-polled` + 455 `coordinator-pass-complete`); +4 — my
  diagnostics run, test 07 (ids 456–459, the standard hold quartet,
  04:54:56 UTC).
- Events 151 → 155 = +2 (my suite's L3 leg, tests 10/11) +2 (my
  diagnostics run, tests 10/11) — all `startup` events from by-design
  restarts. Metrics 1503 → 1516 = daemon ~60 s cycles. pool_stats
  65 → 66 = the 04:40:56 poll.
- Latest decision at close, id 459: `scheduler, no-throttle-needed`
  (ts 1795063296). No miner processes (checked via the S7 /proc scan in
  Part 2 and diagnostics test 15 PASS).

## 3. No writes by the security module — PASS

- `SELECT COUNT(*) FROM decisions WHERE decision LIKE '%security%' OR
  decision LIKE '%scale%' OR reason LIKE '%security%' OR reason LIKE
  '%scale%'` = **0 — ever.** No decision row mentions security or scale
  at all.
- `ledger` = 0, `reward_batches` = 0, `payouts` = 0, `shares` = 0,
  `workers` = 0, `users` = 0 at every check (before, during, and after
  my diagnostics run and the temp-DB checks, which used `/tmp` DBs).
- Decisions in Lane C's window (04:16–04:31 UTC, scale runs + export)
  are only the standard coordinator/scheduler quartets and
  `pool-stats-polled` / `coordinator-pass-complete` rows (ids 423–449);
  none is attributable to the security module.
- Source audit of `core/atlas_security.py`: the only UPDATE/INSERT/
  DELETE statements in the module target the temp-DB connection
  (`tcon`) — fixture setup, the S1 tamper, the S3 idempotency insert,
  the scale synthetic load. No `con.execute(...)` write against the
  live connection exists. The module's only live-DB operations are
  `SELECT COUNT/SUM` reads, config reads, and file greps; its only
  write is the atomic `data/security.json` export (temp + `os.replace`).
- Temp-file check: **0 files matching `atlas-m10-*.db`** in `/tmp`
  (the module's `_temp_db_copy` prefix) — every temp DB it created was
  removed. See Observation 2 for the unrelated `/tmp` leftovers.

## 4. Configs unchanged — PASS

```
46d3d12c1b907c048f2876755ce0d22a01316899d894561c6f86da67bfacab26  config/atlas.json
b01a22ad5d703765a84b3fd7daa1b3b624bdfc3b4b9ea0238d1da3e95ad13464  config/pool-rewards.json
```

Exact match to the baseline hashes (`46d3d12c…` / `b01a22ad…`).
`emergency_stop` still true. The export's provenance short hashes are
the first 16 hex chars of these two digests (verified: `46d3d12c1b907c04`
/ `b01a22ad5d703765`).

## 5. Re-derive every security.json figure — PASS

Independent scripts `/tmp/m10e_part1_keccak.py` (own Keccak-256 +
Monero Base58 + address validation, written from the spec — it does
not import `atlas_security`), `/tmp/m10e_part2_s1s9.py` (own S1–S9
fixtures on temp DBs, engine modules only), `/tmp/m10e_part34_scale.py`
(live re-derivation + scale re-measurement).

**Part 1 — Keccak + addresses: 40/40 PASS.**
- Own Keccak-256 verifies the binding test vector
  Keccak-256("") =
  `c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470`,
  and Keccak-256("abc") =
  `4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45`;
  both differ from NIST SHA3-256 (`hashlib.sha3_256`). (One bug found
  in my own first draft — the Rho rotation offset must be indexed by
  the source lane, not the destination lane — fixed and re-verified;
  the module's vector passes either way and was never used as the
  reference.)
- Base58 block-wise round-trip verified for 1–8, 16, 32, 69, 77 bytes.
- Constructed valid addresses from chosen payload bytes (network byte
  + 64 key bytes + Keccak-256 checksum): standard 95 chars starting
  `4`, subaddress 95 chars starting `8`, integrated 106 chars starting
  `4` — all ACCEPT by my own validator. (Correction to my first draft:
  integrated addresses start with `4`, per design §0 — `4` integrated
  — not `9`; testnet standard is the `9` shape.)
- All rejections asserted with reasons: wrong length 94/96/105,
  forbidden `0`/`O`/`I`/`l`, first-char/length mismatch (95 chars
  starting `9`; 106 chars starting `8`), checksum mismatch (one char
  flipped); network bytes 53/54/63 (testnet) and 24/25/36 (stagenet)
  rejected at the decoded-payload level; decoded length 68 rejected at
  the payload level (a 94-char string decodes to 68 bytes).

**Part 2 — S1–S9 re-derivation on own temp DBs: 50/50 PASS.** Every
check re-run with my own fixture code against the engine modules:

| Check | Independent result |
|---|---|
| S1 | Fixture settles 5 entries, chain PASS; tamper +1 on entry **4** → FAIL naming entry 4 (`entry 4: entry_hash mismatch (row was modified after commit)`); reversal (id 6) + correction (id 8) → chain PASS, originals visible, balances **alice 15000000000, bob 300000000001** — identical to the export evidence string. Decomposition derived: alice 450,000,000,000 alloc − 450,000,000,000 reversal + 15,000,000,000 referral (5% of bob's 300,000,000,000 alloc); bob 300,000,000,000 + 1 correction delta |
| S2 | Duplicate (worker, external_id) rejected, counted once (weight 10); null-external-id pool share inserted/counted (1), excluded from rewards attribution (weight 10); same external_id under a different worker → batch rejected, worker suspended |
| S3 | Payout-shaped calls refused 2/2, 0 payout rows, 2 logged refusals; re-settle is a no-op (5 entries unchanged); duplicate idempotency key rejected by UNIQUE, exactly 1 row kept |
| S4 | Token returned once, stored as 64-hex hash + salt only, 0 hits for the plaintext token in the temp DB file; correct accepted, wrong/empty rejected; rotation invalidates old, new passes; browser worker stores NULL hash/salt |
| S5 | Keccak vector + constructed accepts + all rejections (see Part 1) |
| S6 | Secret-pattern grep 0 hits across all 6 export files; fake 64-hex credential and fake address-shaped string both replaced by the verbatim `[redacted — possible credential]`; row still counted; six live counts match `admin.json` |
| S7 | Stop ON in config + snapshot; real-mode batch refused with logged refusal; payout-shaped call refused with logged refusal; `mining.enabled` false; no `start_mining` in coordinator/monitor code; no miner process in /proc scan |
| S8 | Mode `simulation-only`; real-mode settle refused while simulation-only (0 ledger entries); `minimum_payout` null; live real-mode batches 0 |
| S9 | 0 secret-pattern hits in the security payload; 0 address-shaped values in the payload and in any export file; no secret key names in the payload; live counts re-derived (all 0) |

**Part 3 — live re-derivation of the export: 56/57 checks pass in the
script, plus 1/1 in the exact-shape L4 replication** (the single miss
was my first L4 replication using shorter synthetic IDs — 82.33 vs
96.26 B/share — superseded by the exact-shape replication at 96.67;
see §6).
- Header: `exported_at` fresh, `user_version` 3, stop true, mode
  `simulation-only`, `mining_enabled` false; scope / format-valid /
  ownership lines verbatim; 9 tests S1–S9, all PASS.
- `security_counts`: all six re-derived from fresh live SQL — 0 == 0
  on every count (suspicious, invalid, duplicate, abuse, auth
  failures, payout anomalies).
- `host_verified_totals`: ledger 0, settled batches 0, user rewards 0,
  ATLAS share 0 — all match fresh live SQL.
- `enforcement`: `real_mode_batches_refused` 0 == live
  `reward-batch-refused` decisions (0); `payout_calls_refused` 0 ==
  live `reward-payout-refused` decisions (0); mining-start line verbatim.
- `redaction`: re-grep of all six files — 0 hits, `hits_by_file` all 0,
  `patterns_checked` 6, `files_checked` the six export files,
  `files_missing` [].
- `provenance`: `module_version` `1.0.0-mission10`, `db_user_version`
  3, config short hashes = first 16 hex of the live sha256 digests.
- Scale block: `run_at` 1795062216 matches the run-scale2 log;
  `run_duration_s` 452.1; `stale` false; `levels` == `l1.levels`;
  per-second/total consistency holds within rounding
  (10,000/5.39 s → 1,855.3/s vs recorded 1,855.1/s;
  100,000/398.917 s → 250.7/s); L2 NOT_RUN + verbatim reason; L3
  live 21.7 s < 120 s, summary 28/0/0, temp NOT_RUN + verbatim reason,
  `temp_db_checks_s` 0.229; L4 base 376,832 == live DB size at the run,
  projections re-derived exactly (10k → 1,339,432; 100k → 10,002,832;
  1M → 96,636,832), label ESTIMATE; L5 re-derived by hand from the
  recorded levels — see §6.
- Notes on my own script (not module defects): my first draft compared
  the provenance hashes against 20 hex chars (the export stores 16) and
  stringified `sqlite3.Row` objects instead of their tuples for the
  EXPLAIN check — both fixed, both re-run green.

## 6. Scale re-verification — PASS

Own temp-DB measurements (`/tmp/m10e_part34_scale.py`,
`/tmp/m10e_l4_exact.py`), engine `record_shares` only:

| Measurement | Lane C claim | My re-measurement | Assessment |
|---|---|---|---|
| Smoke 100 workers / 10,000 shares (own temp DB) | 1,855.1 shares/s, 1,253,376 B | 3,651.7 shares/s (2.74 s), 1,081,344 B (first run: 2,544.4/s) | Same order of magnitude; host-load variance, see note |
| Diagnostics test 28 smoke (my run) | 3,758.8 shares/s, 2.66 s (Lane C's diagnostics detail) | **1,813.2 shares/s, 5.515 s**, temp DB 1,282,048 B | Same order of magnitude; 2% from Lane C's recorded 1,855.1/s |
| O(n²) root cause | cross-worker conflict check does a full SCAN per share | `EXPLAIN QUERY PLAN`: **`SCAN shares USING COVERING INDEX idx_shares_worker_external`** on a 10,000-share temp DB | **Confirmed.** The query `WHERE external_id = ? AND worker_id != ?` cannot use the `(worker_id, external_id)` index (external_id is the second column, worker_id is an inequality), so SQLite scans the whole covering index once per share → O(n²) total. Note it scans the index, not the table — cheaper per row than a table scan, but still linear per share |
| L4 bytes-per-row (shares) | 96.26 | **96.67 with exact fixture shapes** (0.4%); 82.33 with my shorter synthetic IDs (−14.5%) | **Confirmed.** The figure reproduces exactly when the synthetic ID lengths match Lane C's (`scale-l4-shares-{seq}`, 10 workers, 500-share batches, live-DB copy base). It is shape-sensitive, as the export's own note discloses ("measured approximation, not exact") |
| L4 projections | 1,339,432 / 10,002,832 / 96,636,832 | Re-derived exactly from `base + rows × 96.26` (§5) | Confirmed (arithmetic exact; ESTIMATE label present) |
| L5 | `record_shares_total_s` exceeds limit at 1,000 workers / 100,000 shares (398.917 s) | Hand-applied the fixed rule to the recorded levels: clause 1 first breach is `record_shares_total_s` 398.917 > 30 s at the 1,000-worker level; recorded string matches the clause-1 output format exactly | Confirmed for the recorded run |

- **Run-to-run variance (honest note, not a defect):** Lane C's own
  scale runs varied widely — total 452.1 s (recorded) vs 755.1 s,
  683.9 s, 803.4 s on the other runs; 100-worker throughput 3,314.1/s
  (run 1) vs 1,855.1/s (recorded); 1,000-worker throughput 146.2/s
  (run 1) vs 250.7/s (recorded). My runs add 2,544–3,652/s at the smoke
  level. The recorded run was the fastest of Lane C's four. The figures
  are one run's measurements, honestly stamped with `run_at`, and the
  L5 conclusion is robust to this variance because the clause-1 breach
  has a >13× margin (398.917 s vs the 30 s limit; the per-share time
  would need to drop below ~3,333 shares/s at the big level for the
  breach to disappear — observed 146–251/s). See Observation 1 for the
  one fragility this leaves.
- The 1× level `db_size_bytes` 376,832 == the live DB size, and the
  level DB sizes (1,253,376 / 10,199,040 B) are the same order as my
  smoke DB (1,081,344 B at 10,000 shares).

## 7. Full test suites + diagnostics — PASS

Run by this lane (temp DBs only for the unit suites):

| Suite | Result |
|---|---|
| `test_atlas_security` | **18/18 OK** (357.354 s — includes the on-demand scale test; log `/tmp/m10e-security-suite.log`) |
| `test_atlas_coordinator` | **19/19 OK** |
| `test_reward_engine` | **20/20 OK** |
| `test_atlas_dashboard` | **4/4 OK** |
| `test_atlas_admin` | **5/5 OK** |
| `test_atlas_profitability` | **11/11 OK** |
| **Other suites total** | **59/59 OK** (22.9 s, one command) |
| `core/diagnostics.py` | **28/28 PASS, 0 FAIL** (my run 04:54:30–04:54:56 UTC, 25.8 s; log `/tmp/m10e-diagnostics.log`) |

- **No endpoint flapping on my run:** tests 14 and 18 both PASS
  (coingecko/moneroocean/blockchain.info 200; mempool.space 200 in
  test 18). No re-run was needed. Test 14 probes 3 endpoints by design
  (mempool.space is covered in test 18) — the detail string is accurate.
- Test 27 detail (my run): "security.json fresh (1s old), 9/9 checks
  passed; host-verified totals match live DB: 0 ledger entries, 0
  settled batch(es); security counts match live SQL: 0 suspicious, 0
  invalid, 0 duplicate, 0 abuse, 0 auth failures, 0 payout anomalies;
  no secret string in file".
- Test 28 detail (my run): "smoke load ran: 100 workers / 10,000
  shares inserted in 5.515s (1813.2 shares/s), temp DB 1282048 bytes;
  scale block populated (last run 1795062216, 3 levels)".
- "Unmodified" — stated honestly, as in M8/M9: no reference hashes for
  the older suites exist to hash against. What I verified instead: all
  77 tests pass with the expected counts and the expected test names
  (the security suite's 18 are exactly the §10 plan: S1–S9, battery,
  export/scale-preserved, run_pass sub-step, scale L1–L5, scale
  refusal, scale smoke, writes-nothing, Keccak vectors, Base58
  round-trip), and the suites run against temp DBs in `/tmp` only.
  (The pre-existing `ResourceWarning`s about unclosed files in the
  coordinator/rewards/security suites are cosmetic; all tests pass.)

## 8. Coordinator sub-step guarded — PASS

Independent temp-DB run (this lane's own script,
`/tmp/m10e_part5_pass.py`, fresh temp DB from the pre-migration backup
+ Stage 1/2 migrations, recent `pool_stats` row seeded so no network
poll, previous `security.json` seeded with the live scale block):

- Decisions before/after `run_pass`: **76 → 77, delta exactly +1**;
  last decision `coordinator-pass-complete`; ledger, reward_batches,
  payouts, shares, workers, users all unchanged at 0.
- All six exports written in the temp dir, all fresh (age < 60 s at
  check; the pass took 6.0 s): `coordinator.json`, `rewards.json`,
  `dashboard.json`, `admin.json`, `profitability.json`, `security.json`.
- The five non-security exports share one `exported_at` (the pass
  instant, == the `run_pass` summary `exported_at`); the security
  export is stamped seconds later, when the battery runs inside the
  pass — a 5 s skew on my temp pass. This explains the live 15 s skew
  between `security.json` (1795062669) and the other five exports
  (1795062654): the security export is stamped when its battery runs,
  not at the pass instant (and on live it was re-issued 10 s later by
  diagnostics test 27). Expected behaviour, not a defect.
- **Scale block preserved across re-export (carry-over works):** the
  temp security export carries the seeded scale block verbatim
  (`run_at` 1795062216, levels identical, `stale` false recomputed).
  The live export shows the same carry-over (my diagnostics run
  re-issued `security.json` at 1795063315 with `run_at` 1795062216
  intact).
- D-M10-C3 verified directly: a 501-share batch is refused
  ("exceeds the 500 limit"), a 500-share batch is accepted (500
  inserted).
- No file landed in the live `data/` dir from this check.

## 9. Deviations, secrets, STALE semantics — PASS

**D-M10-C1 — CONFIRMED.** `request_payout()` takes no idempotency key
(signature `(con, user_id, amount_piconero)`) and Gate 4 refuses every
call with a logged refusal. My S3 re-derivation matches the deviation
exactly: 2 calls refused, 0 payout rows, 2 logged refusals, plus the
UNIQUE idempotency constraint proven by direct insert on a temp DB.
The design's literal sequence cannot run; the deviation is the honest
recording of the actual refusal path.

**D-M10-C2 — CONFIRMED.** A naturally-encoded testnet address (byte
53, 95 chars starting `9`) is caught by the first-char/length rule at
the string level in my validator, exactly as the deviation states; the
network-byte rule (53/54/63, 24/25/36) and the decoded-length rule
(68 bytes from a 94-char string) are verified at the decoded-payload
level, where they are reachable. The first-char/length mismatch vector
is a 77-byte payload with network byte 42 (106 chars starting `8`) —
verified rejected by my validator.

**D-M10-C3 — CONFIRMED.** 1,000-share throughput measured in 2×500
batches because `record_shares` refuses >500 (verified directly, §8);
the L1 note records this.

**D-M10-C4 — CONFIRMED.** L3 temp leg is NOT_RUN with the verbatim
reason "Diagnostics suite runs against the live DB only — temp-ledger
full-suite timing not measured", plus the supplementary
`temp_db_checks_s` 0.229 timing. The diagnostics suite is indeed bound
to the live DB path (it restarts the daemon and logs live decisions by
design — observed in my own runs), so a full-suite temp-ledger timing
cannot be measured without misrepresenting it.

**D-M10-C5 — CONFIRMED.** L2 is NOT_RUN with the design's verbatim
reason "Mirror ingest timing not measured — sandbox unavailable" —
never an invented number. (Mirror ingest timing is Lane D / artifact
side; this lane has no artifact tools, so L2 remains NOT_RUN here too.)

**L5 rule fix — CONFIRMED.** The module's `_first_bottleneck`
implements two clauses in order: (1) absolute thresholds — first level
where `run_pass` > 60 s or any single step > 30 s
(`record_shares_total_s` counts as a step); (2) super-linear growth
(>12× for a 10× load), candidates ranked by absolute time at the big
level, with the `record_shares` per-share candidate included. The
history in `/tmp` shows why the fix exists: run 1 (03:49, 755.1 s) and
run 3 (04:01, 683.9 s) used the ratio-only rule and reported
`attribution_weights_s` as the bottleneck; run 3 **FAILED** the
scale test (`assertIn("record_shares", ...)` — log
`/tmp/m10-l1l5-run3.log`). After the fix, run 4 (04:16, 803.4 s, OK),
run-scale2 (04:23, 452.1 s, recorded) and **my independent run**
(357.354 s suite, OK) all report `record_shares`. The recorded L5
matches the fixed clause-1 output for the recorded levels (§6). The
fix is disclosed in the code docstring and is a reasonable reading of
design §5 L5 ("the step whose time grows super-linearly … **or** the
first load level where `run_pass()` exceeds 60 s or any single step
exceeds 30 s").

**t27 stricter than design — CONFIRMED.** Design §10 requires test 27
to check the export "parses, fresh, security counts match fresh live
SQL, host-verified totals match, no secret strings, all S1–S9 results
present". The implemented test 27 additionally asserts every check is
PASS (not merely present), none is NOT_RUN, `emergency_stop` is true,
and mode is `simulation-only`. Stricter in the safe direction, and
disclosed in the test docstring ("and every check passed").

**Secret grep — PASS.** `grep` over the live `data/security.json`
(and the temp-DB export from my Part 5 run): `token_hash` 0,
`token_salt` 0, `wallet` 0, `password` 0, `seed` 0, `private_key` 0.
**Address-shape grep — PASS.** The regex
`[1-9A-HJ-NP-Za-km-z]{95}|[1-9A-HJ-NP-Za-km-z]{106}` finds 0 hits in
all six live export files and in the temp-DB export. No
wallet-address-shaped value appears in any export.

## Observations (not defects)

1. **L5 test assertion is host-speed-dependent (latent fragility).**
   The scale test asserts `"record_shares" in l5["bottleneck"]`. On
   this host that holds with a >13× margin (record_shares_total_s
   398.917 s vs the 30 s clause-1 limit at the big level; observed
   big-level throughput 146–251 shares/s, and the breach would need
   >3,333 shares/s to disappear). But on a host ~15× faster at
   `record_shares`, clause 1 would not fire and clause 2 could again
   pick `attribution_weights_s` (as it did in runs 1 and 3 pre-fix),
   failing the test even though nothing regressed. The delivered state
   passes on this host (3 consecutive post-fix runs: run 4, run-scale2,
   mine). A future lane running the suite on faster hardware should
   expect this and treat it as a test-robustness issue, not a scale
   regression.
2. **`/tmp` still holds 40 named temp DBs from the M5/M6 unit suites**
   (`atlas-m5-test-*.db`, `atlas-m6-test-*.db`, 04:24 UTC). These are
   left by the older suites' named-tempfile pattern on every run of
   those suites (including mine) — pre-existing behaviour, not
   introduced by Mission 10, and not the security module's files: the
   security module's own `atlas-m10-*.db` files are 0, and its test
   suite's `atlas-m10-sec-*` tempdirs are also gone. Lane C's "no temp
   files left" holds for the security module's own files; the M5/M6
   leftovers are a standing suite-hygiene item, not a Mission 10
   defect.
3. **Host memory above the 70% cap (standing, carried):** 84.78–88.29%
   used across this window. Unchanged in kind from M7/M8/M9/M10
   baseline. The daemon itself is tiny (RSS ~10–14 MB); the pressure
   is host-wide, not the daemon.
4. **Scale timings are host-load-dependent, not stable constants**
   (§6): four Lane C scale runs took 452–803 s; throughputs varied
   2× between runs. The recorded figures are one run's measurements
   with their `run_at` stamp, which is the honest presentation. Do not
   quote 1,855.1 shares/s or 452.1 s as a stable benchmark.
5. **Rendered Mining-tab check — NOT established (7th consecutive
   mission, carried).** This lane has no artifact tools; the live
   `getMining` security block was not re-read. The host side is
   verified here; a lane with artifact access must re-read the live
   artifact before treating the mirror as current.

## Files and evidence

- This report: `~/workspace/atlas/docs/master-mission10-verification-host.md`
- Check scripts (scratch, not part of the repo):
  `/tmp/m10e_part1_keccak.py` (40/40),
  `/tmp/m10e_part2_s1s9.py` (50/50),
  `/tmp/m10e_part34_scale.py` (56/57 — the one miss was the first L4
  replication with shorter synthetic IDs),
  `/tmp/m10e_l4_exact.py` (96.67 vs 96.26 B/share),
  `/tmp/m10e_part5_pass.py` (25/25),
  `/tmp/m10e-security-suite.log` (18/18 OK, 357.354 s),
  `/tmp/m10e-diagnostics.log` (28/28 PASS, 25.8 s)
- Lane C run logs read (not written by this lane):
  `/tmp/m10-run-scale.log` (run 1, 755.1 s, attribution L5),
  `/tmp/m10-l1l5-run3.log` (run 3, 683.9 s, FAILED — pre-fix L5),
  `/tmp/m10-l1l5-run4.log` (run 4, 803.4 s, OK),
  `/tmp/m10-run-scale2.log` (run 2, 452.1 s, recorded),
  `/tmp/m10-security-full.log` (18/18 OK, 538.009 s)
- Live state at close (04:55:42 UTC): daemon pid 16136 (exactly 1);
  `data/security.json` `exported_at` 1795063315 (re-issued by my
  diagnostics run; scale `run_at` 1795062216 preserved);
  `data/diagnostics.json` ts 1795063322, 28/28 PASS; decisions 459,
  events 155, metrics 1516, pool_stats 66;
  ledger/reward_batches/payouts/users/workers/shares/sessions all 0;
  configs sha256 unchanged; emergency_stop true.

## Sign-off

Mission 10 host verification is complete: every `security.json`
figure re-derives from fresh live SQL and independent temp fixtures
(S1–S9 50/50, Keccak/addresses 40/40, live figures 56/57 in-script
plus the exact-shape L4 replication at 0.4%); the scale
figures re-measure on independent temp DBs (smoke same order of
magnitude, O(n²) root cause confirmed by `EXPLAIN QUERY PLAN`,
bytes-per-row reproduced to 0.4% with matching fixture shapes, L5
re-derived by hand); the suites are 18/18 + 59/59 and diagnostics
28/28 on my own runs; the coordinator sub-step is guarded (+1 decision
per pass, all six exports fresh, scale carry-over works); all seven
documented deviations are confirmed against evidence; and no decisions,
ledger rows, shares, batches, payouts, or secrets were written by the
security module. The one failure in Lane C's history (scale run 3) was
found by Lane C's own testing and fixed before delivery, and my
independent run of the fixed code passes. Mission 10's host side is
verified; Mission 11 still requires separate user authorization and
must not start on the strength of this report alone.
