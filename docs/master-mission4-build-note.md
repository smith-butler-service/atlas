# ATLAS Master Mission 4 — Miner Prototype: Build Note (Lane D)

**Date:** Wednesday, 2026-11-18
**Lane:** D — PROTOTYPE BUILD
**Design:** `docs/master-mission4-design.md` (followed; deviations listed in §6)
**Artifact:** `atlas-command-center` (source in `~/workspace/ts-spaces/atlas-command-center/`)
**Status: DEPLOYED.** Lane D built the prototype in source (verified as far as that lane could verify); the coordinator then ran the platform build via `artifact.edit` on `atlas-command-center`, which SUCCEEDED (build card web-artifact-build-completed-45872587-bad1-4073-b58e-c93ce33226c1; see the §8 addendum for the deploy fix D7 and the builder's verification). The "NOT YET DEPLOYED" state described in §7 was true when Lane D wrote this note and is now superseded by the §8 addendum.

## 1. COOP/COEP probe result (design §1.6)

**Static finding — NEGATIVE (no headers configured):** a search of the space
runtime/serving stack found nothing that sets `Cross-Origin-Opener-Policy`
or `Cross-Origin-Embedder-Policy` — the only matches in the SDK tree are
type definitions that merely name the headers. Nothing in the artifact's own
code sets them either (the artifact cannot set response headers).

**Live finding — NOT ESTABLISHED in this lane:** this subagent has no live
browser and no artifact URL (no `artifact.inspect`/`status`), so it could
not read the live response headers or evaluate `window.crossOriginIsolated`
on the artifact host. The audit capture host (`artifact-capture.invalid`) is
an internal capture, not the live host, and carries no COOP/COEP information.

**Consequence (per design, no workaround authorized or attempted):** the
prototype defaults to the single-threaded WebRandomX fallback. The miner
worker selects the pthread build only when
`typeof SharedArrayBuffer === "function" && crossOriginIsolated === true`;
otherwise it loads the single-thread build and forces 1 thread. The Mining
tab prototype section reads and displays the live `crossOriginIsolated`
value, and the probe hook's `status()` reports it. **The test lane must
confirm the live value in a real browser** — if it is `false`, Gate 1 is
measured single-threaded and that is a valid Gate 1 result; if it is `true`,
the pthread path activates.

## 2. WASM acquisition path + verification evidence

**Path taken: verified prebuilt binaries** from the official VoltMiner
Browser Experiment host (`https://j3r0nim0.github.io/voltminer-web/`), NOT
the reproducible-build recipe — **Emscripten is not available in this
sandbox** (`emcc` not found; no emsdk), so the Docker + Emscripten 4.0.10
rebuild could not be run here. This is deviation D2 (§6).

**Verification evidence (all checked 2026-11-18, this lane):**

| File | Size | SHA-256 (downloaded bytes) | Published SHA256SUMS |
|---|---|---|---|
| `web-randomx-mt.wasm` | 246,091 B | `c42908afbf5481669be4511b75198c7c0df3e4d4d85a62ecc68c6639040c6d51` | match |
| `web-randomx-mt.js` | 39,941 B | `68046e8bf852573b7600a572f7466d7baa9dcf8dc9b51a46611380ebbbf27f00` | match |
| `web-randomx.wasm` | 229,718 B | `0b73579eba1e0ff417465b4ee21434095498fd2c8423628af23f8a5b35fa507f` | match |
| `web-randomx.js` | 25,629 B | `606986395ede1ae0239b31ec462ae43453a7232030221ae5b008f30628136b46` | match |

Published hashes from the project's own SHA256SUMS
(`https://j3r0nim0.github.io/voltminer-web/transparency/SHA256SUMS`,
fetched 2026-11-18 08:43 UTC). The notices page pins the provenance:
RandomX-bonanza @ f9848e3 + Emscripten 4.0.10 + `RandomX-JIT-overlay/`;
WebRandomX @ 780908a + Emscripten 4.0.10 + `WebRandomX-overlay/`.

**Rounding-mode fix (design §1.3 R1) verified in the published overlay:**
`transparency/wasm-patch-jit/src/cpp/wasm_softround.h` (SHA-256
`26b091937dd66d384d34a08f6ae8509b8f2089a4242d4c221217fc45ec673da1`,
matches SHA256SUMS) contains
`extern __thread uint_fast8_t globalRoundingMode;`, and
`transparency/wasm-patch-jit/src/cpp/softfloat.cpp` (SHA-256
`11f903110b00e86398cb1761361f61ac92a58535531a0ab5778ff9cff9b68cf5`,
matches SHA256SUMS) contains
`__thread uint_fast8_t globalDetectTininess` and
`__thread uint_fast8_t globalRoundingMode = round_min;`.
The per-thread rounding-mode fix is therefore in the published overlay that
built the shipped binary. The `against-upstream-f9848e3.patch` file itself
does not contain the `__thread` lines (the fix lives in the overlay's
softfloat sources, not in that patch file) — recorded so a later reader does
not re-derive this.

**Reference-vector check (design §1.3 R4) — single-thread build VERIFIED:**
the shipped `web-randomx.wasm` + glue were executed in Bun (unit-test scale
only: exactly one hash, the official RandomX test vector — seed 32 zero
bytes, blob 76 zero bytes with nonce `01000000` at byte 39, height 1) and
returned `086a612e65232b12f9f5bc5e1c36b1215c51273f46a9a96e70a9d35a150645f3`,
byte-identical to the expected value. No job, no pool, no shares, no
sustained hashing on the host.

**Multi-thread build reference check — NOT run in this lane:** the pthread
build hangs under Bun (its pthread worker spawn deadlocks outside a real
browser worker environment; killed after ~120 s, no hash computed). The
miner worker enforces the same reference-vector check at load in a real
browser and refuses to mine if it fails; the test lane must confirm it there.
The same applies to the accept-everything bisect (R3) — implemented in the
probe hook as a pre-test gate, not yet executed.

**Host-mining note:** the only hashing performed on the Muse VM host was the
single reference-vector hash above (a correctness check, not mining). No
mining session, no timed run, and no dataset generation ran on the host.

## 3. What was built

All paths relative to `~/workspace/ts-spaces/atlas-command-center/`.

### New files

| File | Lines | What it is |
|---|---|---|
| `client/src/miner/vendor/randomx/web-randomx-mt.{js,wasm}` | — | Bundled pthread build (verified §2). Same-origin, never CDN. |
| `client/src/miner/vendor/randomx/web-randomx.{js,wasm}` | — | Bundled single-thread fallback (verified §2). |
| `client/src/miner/miner-worker.ts` | 940 | Classic Web Worker: loads the glue via `importScripts`, reference-vector gate at load, OPFS dataset cache (fast mode opt-in, seed-keyed, stale-seed drop), 4 GiB budget enforcement (refuse fast mode over 3,584 MiB), threads capped at 4, duty-cycle throttle (default 50%), pause/resume, per-solved-share single-thread re-hash self-check (R2) with drop reporting, JIT bring-up best-effort (continues in interpreter if `wasm-unsafe-eval` is blocked). Local-only: hashes only the job the page hands it. |
| `client/src/miner/miner-relay-worker.ts` | 281 | Local-test relay worker: holds the local test job, re-hashes every submitted nonce with the single-thread engine, exact 256-bit difficulty check (`hashDiff = (2^256-1)/le256(hash)`, BigInt), verdicts `accepted-locally` / `rejected-locally` with reasons (`rehash-mismatch`, `below-difficulty`, `stale-job`). Every message carries a `local-test` marker. No socket, no pool, no forwarding. |
| `client/src/miner/probe.ts` | 656 | Test-flag-gated probe hook (`window.__atlasMinerTest`, installed only under `?atlas-miner-test=1`): `startLocalTest` / `stop` / `status`. Validates options structurally (numbers + mode enum only — no hostname/URL/wallet can enter by construction), requires the emergency stop ON, 600 s cap, one session per tab, accept-everything bisect (1 vs 2 vs 4 threads, light mode — see §6 D3) as a pre-test gate, difficulty-10,000 timed run, pause-on-hidden with logging, 1-minute hashrate buckets, JS-heap sampling, full audit log of every call. |
| `client/src/miner/MinerPrototype.tsx` | 443 | "Miner Prototype — Master Mission 4" section: 5 gates with statuses, measured-hashrate panel ("No measurement yet"), published-figures line (labelled as other projects', not ATLAS's), desktop XMRig design summary ("Design — not built"), honest framing verbatim from design §5.5, WASM provenance line with both SHA-256 pins + live `crossOriginIsolated` / threading mode, "Delete cached dataset" control (OPFS only), read-only test-session readout shown only with the test flag. No start control of any kind. |

### Edited files

| File | Change |
|---|---|
| `client/src/Mining.tsx` | +1 import; renders `<MinerPrototypeSection />` after `CalculatorSection` (below the existing sections); +1 `useEffect` that dynamically imports `./miner/probe` and installs the hook **only** when `?atlas-miner-test=1` is present. Wallet center, dashboard, earnings, history, payout, calculator, settings, help — untouched. Start/Stop buttons untouched (still `disabled`, no handler). |
| `client/build.mjs` | After the unchanged `buildClient()` call: builds the two worker entry points with `Bun.build` (format `iife`, deterministic names) into `client/dist/assets/`, and copies the 4 vendor files to `client/dist/assets/vendor/randomx/`. Required because `Bun.build` does not bundle `new Worker(...)` references (verified in scratch). The canonical React bundle step is unchanged. |

### Not touched (verified by file listing)

Orb, refresh, emergency stop, all other tabs, `server/src/*`, `server/src/monero.ts`,
`drizzle/`, `app.db`, `~/workspace/atlas/config/atlas.json`,
`~/workspace/atlas/config/pool-rewards.json`. No new tables, no migrations, no
daemon/cron changes, no seeded rows. Safety state re-verified after the work:
emergency_stop `true`, mining.enabled `false`, trading `paper-only`,
eligible capital `$0`, pool-rewards mode `simulation-only`, minimum payout
still `null`/placeholder.

## 4. Verification results

| Check | Result |
|---|---|
| Client typecheck (`bun x tsc --noEmit -p client/tsconfig.json`) | **PASS, exit 0** (after fixing 22 errors: untyped worker scope, `noUncheckedIndexedAccess` byte indexing, untyped OPFS methods, 2 unused vars) |
| Server typecheck | **PASS, exit 0** (server untouched) |
| Worker build (scratch replica of the `build.mjs` step, exact same `Bun.build` call) | **PASS** — both workers build as classic scripts, `node --check` clean |
| Main bundle build (scratch `bun build` of `client/index.html`, 550 modules) | **PASS** — 1.39 MB; `__atlasMinerTest`, `miner-worker.js`, and "Miner Prototype" all present. (Tailwind `@utility`/`@theme` warnings appear only because the scratch build lacks the SDK's tailwind plugin; the platform build includes it.) |
| Probe hook inert without flag | **By construction** — `Mining.tsx` dynamically imports the probe module only when `?atlas-miner-test=1` is present; without the flag `window.__atlasMinerTest` is never set and no worker is created. Rendered check owed to the test lane (no browser in this lane). |
| Start/Stop still hard-disabled, no handler | **PASS** — both buttons `disabled` + `aria-disabled="true"`; the only `onClick`s in `Mining.tsx` are the pre-existing Retry / wallet submit / calculator presets / settings save. |
| No pool connection code in the miner | **PASS** — miner sources + both built worker bundles grep clean for `stratum`, `moneroocean`, `supportxmr`, `p2pool`, `3333`, `5555`, `10001`, `10101`, and the 95-char Monero address pattern (0 hits). The only "stratum"/"MoneroOcean" hits in the whole main bundle are false positives in pre-existing code: the Orb's GLSL `float stratum` (stratified sampling) and the calculator's "(MoneroOcean)" copy. |
| No seed/key/password field | **PASS** — the new miner files contain no seed-phrase, private-key, or password field (one comment states they are forbidden). |
| No console errors on load | **NOT VERIFIED in this lane** — no browser access; owed to the test lane's rendered check. |
| Reference vector (single-thread build, shipped bytes) | **PASS** — byte-identical (§2). |
| Bisect (R3) + timed run | **NOT RUN** — implemented in the probe hook; execution is the test lane's job in a real browser. |
| COOP/COEP live value | **NOT ESTABLISHED** — see §1; test lane to confirm. |

## 5. Safety checklist (design §6 — confirmed)

- [x] No pool connection for earning. No pool-protocol connection of any kind. No share submission to any pool. (Relay is local-test only; pool-facing relay not built, no code for it exists.)
- [x] No real payout, no payout flow, no test wallet with real funds.
- [x] No wallet/key/seed/password creation anywhere.
- [x] No spending of any kind.
- [x] No config changes (`atlas.json`, `pool-rewards.json` read-only in this lane; verified unchanged).
- [x] No lifting the emergency stop; stop stays ON; mining stays disabled in config; trading paper-only; capital $0.
- [x] No mining on the Muse VM host beyond the single reference-vector correctness hash (§2).
- [x] No live trading, no capital, no financial transaction.
- [x] No new daemon, service, cron, or scheduled job.
- [x] No new DB migration/tables/seeded rows.
- [x] No user-facing "start mining" control. Start/Stop stay hard-disabled. Only start mechanism is the test-flag-gated probe hook.
- [x] No background/hidden-tab mining — pause-on-hidden implemented page-side (visibilitychange → pause/resume, logged); worker does no hashing and no dataset work while paused.
- [x] Wallet center untouched except reading it. Orb, other tabs, emergency stop, diagnostics untouched.
- [x] Refresh failure (Mission 3 finding 1) NOT fixed, NOT worked around, NOT touched.

## 6. Gaps and deviations from the design doc

- **D1 — Relay transport (design §2.1).** The design specifies a same-origin
  WebSocket relay. The space runtime exposes no raw WebSocket endpoint, and
  the mission forbids a persistent host service, so the local-test relay runs
  as a second in-page Web Worker and the page forwards messages between the
  miner worker and the relay worker. Protocol shape (job id, blob, seed,
  target; submit with job id + nonce + result), `local-test` markers, and
  validation (independent single-thread re-hash + exact 256-bit difficulty
  check) are identical to the design; only the transport differs. The
  pool-facing relay remains design-only and unbuilt.
- **D2 — WASM acquisition (design §1.2/R1).** Verified prebuilt binaries
  instead of the reproducible build (no Emscripten in this sandbox). Mitigated
  by hash verification against the publisher's SHA256SUMS, overlay-patch hash
  verification proving the `__thread` fix is in the published overlay, and
  the reference-vector check on the shipped single-thread bytes (§2). A
  future lane with Emscripten can reproduce the build and compare hashes.
- **D3 — Bisect runs in light mode (design §1.3 R3).** The bisect is the
  pre-test gate and runs in light mode; the rounding-mode bug lives in the VM
  execution path (CFROUND + softfloat state), not in the dataset, so light
  mode exercises it, and it keeps the gate fast (a fast-mode bisect would
  first pay the ~minutes dataset generation). The timed run then uses the
  requested mode. If the test lane disagrees, the bisect mode is one line in
  `probe.ts` (`makeLocalTestJob(1)` runs under the light-mode config).
- **D4 — `client/build.mjs` extended (design §8 handoff assumes the standard
  build).** `Bun.build` does not bundle `new Worker(...)` references, so
  without this step the worker files would never reach `client/dist/assets/`
  and the probe hook would refuse to start with a clear "worker bundle
  missing" error. The extension runs after the unchanged `buildClient()`
  call and does not alter the React bundle. If the platform pipeline ever
  stops executing `build.mjs`, the hook fails loudly rather than silently.
- **D5 — Probe code ships inside the main bundle.** The platform bundler
  inlines the dynamic `import("./miner/probe")` (no code-splitting in the
  SDK build), so the probe module's code is present in the initial bundle —
  but it is inert: `installAtlasMinerTest` is never called without the flag,
  so the hook never exists and no worker or WASM fetch ever happens.
- **D6 — Content-Type / CSP (design §1.4).** `application/wasm` serving and
  the `script-src 'self' 'wasm-unsafe-eval'` / `connect-src 'self'` CSP are
  platform-controlled; this lane cannot set or verify them. The worker
  treats JIT enablement as best-effort (falls back to the interpreter and
  reports it) so a CSP without `wasm-unsafe-eval` degrades rather than
  breaks. Test lane to record the live headers/CSP behaviour.
- **Gap — no artifact build id (see §7).** The prototype is built in source
  but not yet deployed as a new artifact version; the rendered checks
  (no console errors, prototype section renders, hook inert without flag,
  live `crossOriginIsolated`) are owed to the test lane on the deployed build.
- **Gap — RandomX v2.** The shipped engine is RandomX v1, as designed; the
  UI says so ("a v2 activation would need a rebuild/revalidation").

## 7. What the coordinator/parent must do next

1. Run the platform build via `artifact.edit` on `atlas-command-center`
   (this lane cannot — see header). Confirm the new version contains
   `client/dist/assets/miner-worker.js`, `miner-relay-worker.js`, and
   `vendor/randomx/*`, and report the build id.
2. Hand to the test lane (Lane E / audit probe) with the design §4
   procedures: COOP/COEP live probe, Gate 1 bisect + reference vector in a
   real browser (Chrome, then Firefox, then Safari desktop), timed runs at
   Balanced (2 threads) and Performance (4 threads), Gate 3 phases A–D,
   Gate 5 wall-watt protocol, and browser/AV behaviour recording. Gates 2
   and 4 stay NOT TESTED.
3. Test lane re-computes the SHA-256 of the served `.wasm` files and compares
   with §2 before trusting any measurement.

## 8. Addendum (coordinator deploy pass, 2026-11-18) — deviation D7

The coordinator's first platform build FAILED: the CVM client build
requires **exactly one JavaScript file** in `client/dist` (every `.js`
file found there is inlined into the single served bundle; the build
aborts with "expected exactly one JS bundle … found 5" — the React bundle
plus `miner-worker.js`, `miner-relay-worker.js`, and the two vendor glue
`.js` files this lane's `build.mjs` emitted). The §3/§7 assumption that
worker and glue scripts could ship as separate served files is therefore
wrong on this platform. Fixed in the deploy pass, protocol unchanged:

- **D7 — workers + glue embedded, spawned from Blob URLs.** `build.mjs`
  now bundles the two workers first, reads them back as text together
  with the two vendor glue scripts, and writes all four as string
  constants into `client/src/miner/embedded.generated.ts` before the
  canonical `buildClient()` runs. `probe.ts` spawns both workers from
  Blob URLs over the embedded sources and sends each a one-time
  `bootstrap` message (vendor base URL + glue source[s]) before any other
  message; each worker builds a Blob URL from its glue source and
  `importScripts` it, and `locateFile` resolves the `.wasm` against the
  bootstrap-provided vendor base. The `.wasm` binaries are not JavaScript
  and still ship as files: copied to `client/dist/assets/vendor/randomx/`
  after the canonical build and served as static assets (verified present
  in the platform build output). The probe's loud-refusal check now HEADs
  the two `.wasm` assets instead of the worker files.
- Platform build after the fix: **PASS** (coordinator, 2026-11-18);
  `client/dist` contains exactly one `.js` bundle; the CVM output inlines
  it and carries both `.wasm` assets.
- New unverifiable-in-lane item for the test lane: whether the platform
  CSP permits `blob:` workers at runtime. If it does not, worker creation
  fails and the hook reports it — the test lane must record the actual
  behaviour alongside the COOP/COEP probe (D6).
