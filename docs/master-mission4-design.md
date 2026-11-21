# ATLAS — Master Mission 4: Miner Prototype — Design

**Date:** Wednesday, 2026-11-18
**Mission:** Master Mission 4, Lane A — PROTOTYPE DESIGN (read-only design work)
**Status:** DESIGN ONLY. Nothing was built, edited, activated, or connected in this mission. No miner code exists, no relay exists, no pool connection exists, no mining runs. The build and test lanes implement from this document; they do not improvise around it.
**Authoritative inputs:** `docs/master-mission1-inspection-report-2026-11-18.md` (browser RandomX feasibility verdict, 5 prototype gates, 75/25 accounting basis, payout architecture), `docs/master-mission2-report-2026-11-18.md` (Mining tab state), `docs/master-mission3-report-2026-11-18.md` (wallet center + refresh failure), `config/atlas.json`, `config/pool-rewards.json`.
**Safety state at design time (verified 2026-11-18 03:31 EST):** emergency_stop **true**, mining **disabled (design-only)**, trading **paper-only**, eligible capital **$0**, limits 50/70. Pool config `~/workspace/atlas/config/pool-rewards.json`: MoneroOcean primary 0% fee, SupportXMR 0.6% + P2Pool 0% fallbacks, 75/25 split on confirmed pool rewards only, simulation-only. Host: no GPU, 4 vCPUs (1.5 shared-CPU cap), 6 GB RAM cap. Mining tab exists on the Command Center (artifact `atlas-command-center`) with the wallet center (Mission 3, complete). Start/Stop buttons stay hard-disabled with no handler.

## Labelling convention

Every figure in this document carries one of three labels, following the Mission 1 / Objective 4 discipline:

- **VERIFIED** — measured or confirmed against a live source or an official document cited in §9.
- **ESTIMATE** — computed from verified inputs with stated assumptions; the number is a projection, not a measurement.
- **ASSUMPTION** — a design choice or an unconfirmed property; the build/test lanes must verify it before relying on it.

No figure in this document is a promise of earnings. Realized mining revenue remains $0.

## 0. Design decisions at a glance

| Decision | Choice | Why (one line) |
|---|---|---|
| Browser WASM implementation | **RandomX-bonanza (aa022) pthread build, with the VoltMiner `__thread` rounding-mode fix and self-check, as reproduced from VoltMiner's published build** (§1.2) | Only verified open-source build that does full (fast) mode in a browser at ~10% of native on x86, with a published, reproduced build recipe and a demonstrated fix for the silent-invalid-share bug. |
| Single-thread fallback | WebRandomX (WebCryptomining) single-thread build, same algorithm, identical hashes | Published sibling build from the same VoltMiner notices; used only when SharedArrayBuffer is unavailable. |
| Loading | **Bundled** (WASM + JS glue committed into the artifact) | Reliability + auditability; no runtime dependency on a third-party host; SHA-256 pinned at build time. |
| Dataset mode | Fast mode (~2 GB dataset) primary; light mode (256 MB cache) fallback | Fast mode is the only mode with meaningful hashrate; light mode is ~50–80x slower than native (Mission 1 §4.1). |
| Gate-1 test mechanism | **Test-flag-gated probe hook** — `?atlas-miner-test=1` enables `window.__atlasMinerTest` (start/stop/status); inert without the flag; no user-facing control | Runs the miner local-only for measurement without touching the disabled Start/Stop buttons and without any visible "start mining" affordance (§4.1). |
| Relay | **Local-test relay only** in this mission; pool-facing relay is design-only (§2) | Gates 2 and 4 are NOT TESTED in this mission; building a pool-facing relay now would create a live pool connection the mission does not authorize. |
| Desktop miner | XMRig from official sources only, explicit per-worker activation, config template in §3 | Only path near breakeven (Mission 1 verdict); 30–80x faster than the browser tab. |
| Honest framing | Browser = participation/demo, never revenue; desktop = only path near breakeven | Mission 1 §4.3 economics: browser tab gross ~$0.008/day, net approx −$0.10 to −$0.13/day. |

---

## 1. Browser WASM miner

### 1.1 What the miner must do

- Compute RandomX (rx/0) hashes in a Web Worker, in a browser tab, against a job (block template + seed + target) supplied by a local source in this mission (§1.7).
- Report an honest, measured hashrate (hashes / wall-clock second, averaged over a stated window, with the thread count and mode recorded alongside).
- Never open a raw socket, never contact a pool, never submit a share, never start without the test hook (§4.1), never run when the tab is hidden (§1.6), never exceed its resource budget (§1.6).
- Prove its own correctness before any result is trusted: every solved share is re-hashed with the single-thread hash function and compared; a mismatch drops the share and logs it (§1.3).

### 1.2 Implementation choice — evaluated and decided

Three verified open-source candidates were evaluated. All three are real, public, and cited; only one is chosen.

#### Candidate A — RandomX-bonanza (aa022) — **CHOSEN (pthread build)**

- **What it is:** A WebAssembly JIT backend on the tevador RandomX engine, built with Emscripten, supporting full (fast) mode with a shared ~2 GB dataset across pthreads, plus light mode. Project page: https://randomx.cc/ ; source: https://github.com/aa022/RandomX-bonanza (cited in VoltMiner notices, below).
- **Performance (VERIFIED, author's published figures):** with SharedArrayBuffer available (full mode), ~10% of native performance on AMD64 platforms and ~23–25% on Apple M4 ARM64 (10 cores, vs native XMRig at the same thread count); light mode ~53–67% of native light-mode efficiency on M4. Full tables and methodology in the project README (https://randomx.cc/).
- **Independent corroboration (VERIFIED):** VoltMiner's Browser Experiment ships exactly this build as its multi-threaded binary — `web-randomx-mt.{js,wasm}`, "built from https://github.com/aa022/RandomX-bonanza @ f9848e3 (a WebAssembly JIT backend on the RandomX engine) with Emscripten 4.0.10, plus the patches in third_party/RandomX-JIT-overlay/" — and measured ~90 H/s on 4 threads in a live one-hour run with 21 accepted / 0 rejected shares after the fix (https://www.voltminer.net/blog/randomx-in-a-browser-the-rounding-mode-bug ; https://j3r0nim0.github.io/voltminer-web/notices.html).
- **Licence (VERIFIED):** RandomX engine BSD-3-Clause; the WASM JIT backend dedicated to the public domain under CC0 1.0 by aa022; two files (`src/jit_stubs/semifloat.c`, `src/jit_stubs/mulh.c`) are byte-identical to l1mey112/randomx.js and remain BSD-3-Clause © tevador and l-m. Emscripten runtime MIT. (Source: https://j3r0nim0.github.io/voltminer-web/notices.html.)
- **Why it wins:** it is the only candidate that (a) runs full mode in a browser, (b) has a published, reproducible build recipe (Docker + Emscripten 4.0.10 + overlay patches, per VoltMiner's transparency page https://j3r0nim0.github.io/voltminer-web/transparency/), and (c) has demonstrated pool-accepted shares in a real browser — i.e. it has already passed, in someone else's hands, the exact failure mode (silent invalid shares) that Gate 2 exists to catch.

#### Candidate B — WebRandomX (WebCryptomining) — **CHOSEN as single-thread fallback only**

- **What it is:** tevador's RandomX compiled to WebAssembly, single-threaded, no SharedArrayBuffer required. Source: https://github.com/WebCryptomining/WebRandomX.
- **Status (VERIFIED):** VoltMiner ships it as its single-thread fallback — `web-randomx.{js,wasm}`, "built from https://github.com/WebCryptomining/WebRandomX @ 780908a with Emscripten 4.0.10, plus the patches in third_party/WebRandomX-overlay/" (https://j3r0nim0.github.io/voltminer-web/notices.html). Both builds produce identical hashes.
- **Why fallback only:** single-threaded, no shared dataset, no JIT backend comparable to bonanza's; it is the correct degradation path when cross-origin isolation is unavailable (§1.5), not the primary engine.

#### Candidate C — randomx.js (l1mey112) — **REJECTED for the prototype (light mode only)**

- **What it is:** A from-scratch RandomX implementation in C compiled to WASM, with a WASM JIT that generates code on the fly; zero JavaScript dependencies; tested against the official RandomX test vectors. Source: https://github.com/l1mey112/randomx.js ; talk: https://blog.l-m.dev/talks/zero-to-randomx-js-webmining.pdf.
- **Why rejected:** its own README states, verbatim, "Mining with an initialised dataset (2 GiB allocation) is not supported (though easy to implement), no one on earth would give a webpage multiple gigabytes of memory. **Light/verification mode only.**" Light mode is ~8.8 H/s/core (VERIFIED, SoapBox measured against the official RandomX test vector, https://pool.soapbox.community/) — i.e. ~50–80x slower than native per core (Mission 1 §4.1). It is a legitimate, well-tested implementation, and its `semifloat.c`/`mulh.c` are already inside the chosen build's lineage — but as a mining engine it caps the prototype at the slowest possible mode. It remains the reference for correctness checks (test-vector comparison) and a candidate if the bonanza build ever proves unreproducible.
- **Note:** randomx.js's author notes WASM has no directed-rounding support for floating point — the same underlying constraint behind the VoltMiner bug (§1.3). Any build that does not address per-thread rounding state is disqualified.

#### Other builds considered and not chosen

- **SoapBox pool browser miner** (https://pool.soapbox.community/): a real, honest in-browser RandomX miner (light mode, ~8.8 H/s/core, code open as `randomx.js`, BSD-licensed). Not chosen because it is light-mode only and is a pool's own product, not a standalone engine ATLAS can bundle and reproduce. Its published measurements are used as a cross-check in §1.4.
- **BlackMine** (https://www.blackmine.app/mine): cited in Mission 1 as a browser-mining experiment ("a browser thread does a few hashes a second, a desktop XMRig does thousands"). No standalone reproducible WASM engine was verified for it; not a candidate.
- **Coinhive and any CryptoNight-era web miner:** not candidates. Coinhive mined CryptoNight, not RandomX, and shut down 8 March 2019 (https://www.bleepingcomputer.com/news/security/coinhive-in-browser-cryptomining-service-shuts-down-on-march-8/). RandomX replaced CryptoNight in November 2019. Any "web miner" library predating RandomX is irrelevant by construction.

### 1.3 The VoltMiner rounding-mode bug — what it was, and how the chosen build avoids it

This is the single most important correctness fact in the whole prototype. It is the reason Gate 2 exists and the reason local H/s can never be trusted alone.

**The bug (VERIFIED, VoltMiner, 3 Oct 2026 — https://www.voltminer.net/blog/randomx-in-a-browser-the-rounding-mode-bug):**

- WebAssembly has no `fesetround`. RandomX needs a floating-point rounding mode, so the WASM port emulated it in a process-global variable: `uint_fast8_t globalRoundingMode = round_min;`
- The RandomX bytecode `CFROUND` instruction executes *inside the hashing loop* and writes that variable; the vector maths then reads it to choose between a fast SIMD path and a software-float fallback.
- With one VM per thread but one rounding mode for all of them, threads overwrote each other's rounding mode mid-program. Each thread's arithmetic was evaluated under its neighbour's mode. The output was a valid-looking 32-byte value that was the hash of nothing in particular.
- The failure was invisible locally: the miner found shares at exactly the difficulty-predicted rate (~46 submits in a four-hour soak at difficulty 10,000), its own `hashDiff` (49,617 vs required 10,000) said the shares were good, and every one was rejected by MoneroOcean with `Low difficulty share`. Single-threaded the miner was honest; multi-threaded it was not. The bisect that cracked it: mine with an accept-everything target (`0xFFFFFFFF`, difficulty 1), take the reported nonce, re-hash it with the single-VM hash function, compare — 1 thread MATCH, 2 and 4 threads MISMATCH.

**The fix (VERIFIED, same source) — three changes, all mandatory for the ATLAS build:**

1. **Per-thread rounding mode.** Both softfloat globals became `__thread` (thread-local storage; Emscripten pthread builds support TLS). Each hashing thread keeps its own mode. Two lines.
2. **Separate build targets.** A `--shared-memory` WASM link requires *every* object to declare the `atomics` target feature (which `-pthread` implies), while the single-threaded target must not carry it. The threaded library got its own CMake target instead of sharing one.
3. **Never trust the miner about its own work.** Every solved share is re-hashed with the single-thread hash function before submission. If the two disagree, the share is dropped and logged — the pool never sees garbage.

**Verification after the fix (VERIFIED, same source):** one hour, four threads, full 2 GB dataset, live pool — 260,444 hashes, 21 accepted, 0 rejected, 0 self-check drops, ~90 H/s; the same job blob and nonce hashed by native RandomX on ARM agreed byte for byte.

**How the ATLAS prototype avoids the bug (design requirements, binding on the build lane):**

- R1. The build MUST reproduce the VoltMiner-published recipe: RandomX-bonanza @ f9848e3, Emscripten 4.0.10, the `third_party/RandomX-JIT-overlay/` patches, including the `__thread` rounding-mode fix — or a pinned later commit that the build lane verifies contains the equivalent fix. The build lane must cite the exact commit and the overlay patch contents in its report; "latest main" is not a pin.
- R2. The build MUST include the self-check: every solved share re-hashed single-threaded and compared before it is handed to the relay (local-test relay in this mission). A self-check drop is logged with the nonce and the two hashes; a drop rate > 0 is a FAIL for Gate 1 (see §4.1).
- R3. The build MUST pass the accept-everything-target bisect as a unit test before any timed run: target `0xFFFFFFFF`, 1 vs 2 vs 4 threads, reported nonce re-hashed single-threaded, MATCH required at every thread count. This is the cheapest possible reproduction of the VoltMiner bug and it takes ~2 seconds per thread count.
- R4. The build MUST be verified against the official RandomX test vectors (the same check SoapBox uses for its 8.8 H/s/core figure) and, for at least one job blob + nonce, byte-compared against native RandomX (XMRig or the reference implementation) run on a separate machine. A hash that differs from native by even one byte is a FAIL, not a rounding error.
- R5. The single-thread WebRandomX fallback MUST carry the same self-check (its rounding emulation is the same class of risk, even though only one thread runs — the variable is still emulated, and the self-check is what makes the claim testable).

### 1.4 Loading — bundled, not CDN

- **Decision: bundle the WASM binary and its JS glue into the artifact (committed files, served from the same origin as the Command Center).** This follows VoltMiner's own rule, stated in its notices: "Do not hotlink a third-party wasm at runtime; both binaries are committed here." (https://j3r0nim0.github.io/voltminer-web/notices.html)
- **Why bundled:** (a) reliability — the miner must not fail because a third-party host is down, slow, or changed; (b) auditability — the exact bytes served are the exact bytes whose SHA-256 was recorded at build time; (c) security — no third-party script execution in a page that handles wallet addresses; (d) blocklist posture — a self-hosted miner is less likely to trip the generic cryptomining blocklists than a known third-party mining script URL, though no loading choice guarantees this (§1.8).
- **Requirements for the build lane:**
  - Pin the SHA-256 of each shipped `.wasm` file in the design/build record and display it in the prototype UI ("WASM build: RandomX-bonanza @ f9848e3, sha256: …"). The test lane re-computes the hash from the served bytes and compares.
  - Serve with `Content-Type: application/wasm` and `Cross-Origin-Resource-Policy` as required by the threading path (§1.5). Use `WebAssembly.instantiateStreaming` with a fallback to `instantiate` on MIME-type failure.
  - The JS glue must be unminified or source-mapped in the prototype so the test lane can read it. No obfuscated miner code, ever.
  - The Content Security Policy must pin `script-src 'self' 'wasm-unsafe-eval'` (the VoltMiner transparency page's CSP: `default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' ws: wss:` — https://j3r0nim0.github.io/voltminer-web/transparency/). In this mission `connect-src` is `'self'` only: the local-test relay is same-origin, and there is no pool endpoint to allow.
  - No analytics, no third-party script, no CDN font/script dependency in the miner path.

### 1.5 Dataset handling — fast mode vs light mode, OPFS caching, the 4 GiB cap

**The constraints (VERIFIED, Mission 1 §4.1 + RandomX README via https://academy.bit2me.com/en/que-algoritmo-mineria-randomx-monero/):**

- Fast (full) mode needs a **~2 GB dataset** (2,080 MiB) plus 2 MB scratchpad per thread. Light mode needs a **256 MB cache** and no dataset, but is far slower.
- **WASM32 linear memory caps at 4 GiB total** for module + dataset + heap — the dataset alone consumes half the address space.
- The dataset is derived from the network seed (key) via the RandomX cache; it must be generated once (minutes on first visit) and cached between visits, or every visit pays the generation cost.

**Design:**

| Item | Fast mode (primary) | Light mode (fallback) |
|---|---|---|
| Memory | ~2 GB dataset + 2 MB scratchpad/thread + module/heap; total budget ≤ ~2.5 GB | 256 MB cache + 2 MB scratchpad/thread |
| Dataset source | Generated locally in the worker from the current seed (key); never downloaded from a server | Cache generated locally; no dataset |
| Cache | **OPFS (Origin Private File System)** — the VoltMiner approach ("~2 GB dataset cached in OPFS between visits"). Cache key includes the seed; on seed change the old dataset is deleted and a new one generated. A "Delete cached dataset" control must exist (VoltMiner provides one; ATLAS must too) | OPFS as well, or in-memory only; light-mode cache is cheap to regenerate |
| First-visit cost | Dataset generation takes minutes (ESTIMATE: order of minutes on a laptop-class CPU; the build lane must measure and report the actual time on the test hardware — this is a Gate 3 input, §4.3) | Seconds (ESTIMATE) |
| Repeat-visit cost | Dataset load from OPFS (ESTIMATE: seconds to tens of seconds; measure and report) | Negligible |
| Hashrate expectation | ~10% of native on AMD64 (VERIFIED, bonanza author); VoltMiner measured ~90 H/s on 4 threads in a browser (VERIFIED) | ~8.8 H/s/core (VERIFIED, SoapBox); ~50–80x slower than native per core |

**Requirements for the build lane:**

- The dataset MUST be generated from the seed locally; the prototype must never fetch a prebuilt dataset from any server (a downloaded dataset is an untrusted blob and a supply-chain risk).
- The 4 GiB cap MUST be enforced as a hard budget: dataset (2,080 MiB) + scratchpads (2 MiB × thread count) + module + heap must stay under the cap, and the worker must refuse to start — with a clear error, not a crash — if the requested thread count would exceed it. On a 6 GB host cap this is a browser-side budget, but the tab's own memory is what matters; the UI must show peak tab memory during the test (Gate 3, §4.3).
- On seed change (RandomX epoch change, ~every 2,048 blocks), the cached dataset is stale: the worker must detect the seed mismatch, discard the old dataset, and regenerate. The UI must label the dataset state (seed, cached / generating / ready) at all times.
- If OPFS is unavailable (older browser, private mode), the worker falls back to in-memory dataset generation per session and says so in the UI; it must not silently switch to light mode without labelling it.
- Light mode is an explicit, labelled fallback, never a silent downgrade: the UI shows "Light mode (no dataset) — ~50–80x slower than native" whenever it is active.

### 1.6 Threading — SharedArrayBuffer, COOP/COEP, and the fallback

**The constraint (VERIFIED):** threads need `SharedArrayBuffer`, which needs **COOP/COEP cross-origin-isolation headers + HTTPS**; without them the miner falls back to single-threaded. Safari/iOS is the weak case (Mission 1 §4.1). VoltMiner: "Cross-Origin-Opener-Policy + Cross-Origin-Embedder-Policy, because SharedArrayBuffer — and therefore one dataset shared by several threads — requires it." (https://www.voltminer.net/blog/randomx-in-a-browser-the-rounding-mode-bug)

**Required headers for multi-threaded mode:**

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

**Artifact-host status — UNVERIFIED / ASSUMPTION:** whether the Muse artifact host (which serves the Command Center) sends COOP/COEP headers, or allows the artifact to set them, is **not established by any source available to this design lane**. This is the single biggest deployment unknown for the browser prototype, and the build lane must resolve it first, before writing miner code:

- Probe the live artifact's response headers for `Cross-Origin-Opener-Policy` and `Cross-Origin-Embedder-Policy`, and test `crossOriginIsolated` in the page at runtime.
- If the headers are present: multi-threaded mode is available; the prototype uses the bonanza pthread build with `navigator.hardwareConcurrency`-capped threads (see resource controls below).
- If the headers are absent and cannot be set: **the prototype runs single-threaded on the WebRandomX fallback build only**, and Gate 1 is measured and reported in that configuration. The design does NOT authorize working around the missing headers (no service-worker tricks, no header injection, no alternate host). A single-threaded Gate 1 result is still a valid Gate 1 result — it just measures a slower miner, and the UI must say so.
- Safari/iOS: expect no SharedArrayBuffer on older iOS; the test lane must run Gate 1 on Chrome, Firefox, and Safari (desktop) and record which threading mode each actually used. A browser that cannot do multi-threading is a data point, not a failure — but the report must not present its single-threaded number as a multi-threaded one.

**Thread count and resource controls (binding):**

- Default thread count: `min(navigator.hardwareConcurrency - 1, 4)` — never all cores, never more than 4 in the prototype. The user-facing resource profile (Eco / Balanced / Performance, from Mission 2 §12) maps to 1 / 2 / 4 threads; the prototype test uses Balanced (2 threads) as its primary measurement and Performance (4 threads) as its secondary, so both numbers exist.
- **CPU throttle:** the worker yields between hashes on a duty cycle (target: ≤ 50% of one core per thread by default, matching the host `max_cpu_pct: 50` spirit; the exact duty cycle is a build-lane parameter, reported in the test). The UI shows the throttle setting next to the hashrate.
- **Pause on hidden tab (mandatory):** mining pauses the moment `document.visibilityState` becomes `hidden` and resumes only when visible again. This is both a correctness requirement (hidden tabs are throttled or stopped by the browser anyway — "A hidden tab stops hashing", VoltMiner; "Mining stops if you close or background the tab", SoapBox) and an honesty requirement (no background mining, ever). The pause/resume events are logged with timestamps; Gate 3 measures them (§4.3).
- **Memory cap:** the worker monitors its own memory (via `performance.memory` where available, else the dataset + scratchpad budget) and stops with a clear error if the tab exceeds its budget. The prototype must never grow the tab without bound.
- **Duplicate-worker prevention:** one miner instance per tab; opening a second Mining tab while one is testing must refuse to start a second worker and say so. (Mission 1 §8, Mission 4 scope.)
- **Session handling:** the test run is a session with a start time, a thread count, a mode, and a stop time. Sessions are recorded (locally, in the artifact DB's existing mining tables only if the build lane wires them — no new tables in this mission without a design note) with their measured hashrate, never with earnings.

### 1.7 Local-only operation — the miner never sees a pool job in this mission

**The rule:** in this mission the browser miner runs **LOCAL-ONLY**. The job it hashes is generated locally, on the user's own machine / in the test harness, and is never a pool job. There is no stratum connection, no pool login, no wallet in the stratum login, no share submission.

**Local test job specification (binding on the build lane):**

- The test job is a synthetic RandomX job: a fixed 76-byte block template (version + timestamp varint + previous hash + nonce field at byte 39 + tx-count + merkle root — the layout VoltMiner documents in its blog), a fixed seed (key), and a fixed target.
- The job generator runs in the test harness (or in the page's test context), not in the miner worker, so the miner's input is observable and reproducible.
- Two targets are used:
  1. **Accept-everything target `0xFFFFFFFF` (difficulty 1)** for the correctness bisect (§1.3, R3) — every hash qualifies, so the self-check comparison runs in ~2 seconds.
  2. **A realistic low target (difficulty 10,000, matching VoltMiner's soak)** for the timed hashrate run — shares are "found" at the difficulty-predicted rate and handed to the **local-test relay** (§2.1), which validates and counts them locally.
- The miner code must contain **no pool hostname, no pool port, no stratum URL, no wallet address, and no login string**. The test lane greps the shipped miner bundle for `moneroocean`, `supportxmr`, `stratum`, `3333`, `5555`, `10001`, `10101`, and any 95-character Monero address pattern; any hit is a FAIL.
- The local-test relay (§2.1) is the only network endpoint the miner talks to, and it is same-origin. If the miner ever attempts any other connection, the test FAILS.

### 1.8 Blocking, reputation, and user consent

- **Browser/AV blocking (VERIFIED, Mission 1 §4.1):** Firefox 69+ blocks known cryptomining scripts by default; Brave and AV tools block them; the Chrome Web Store bans mining extensions. The test lane must record what Chrome, Firefox, and Safari actually do to the prototype page (block, warn, nothing) and whether common AV (Windows Defender on the test machine) flags the WASM binary. A block is a finding, not a failure of the design — but it must be reported, because it determines whether a browser miner is shippable at all.
- **Consent (binding):** the prototype has no user-facing start control at all in this mission (§4.1), so consent is not engaged by the test. When a future mission adds a user-facing start, it must be explicit opt-in with the resource-use disclosure, the honest economics (§5), and an immediate stop on page exit. Covert mining is never acceptable; ATLAS must never be associated with it.
- **RandomX v2 (VERIFIED, via Mission 1 §9.1 + https://academy.bit2me.com/en/que-algoritmo-mineria-randomx-monero/):** RandomX v2 was released in March 2026; as of 1 Nov 2026 its activation in Monero has no official date. The chosen build is a RandomX v1 engine. The build lane must record the engine version and note that a v2 activation would require a rebuild/revalidation of the WASM engine before the prototype means anything on mainnet. The prototype is a v1 prototype; it must not be presented as future-proof.

---

## 2. Relay — WebSocket→stratum

### 2.1 The local-test relay (BUILT in this mission — design)

This is the only relay that exists after Mission 4. It is a **test double**, not a pool client.

- **Purpose:** accept locally generated test jobs, hand them to the browser miner over a same-origin WebSocket, receive the miner's results, validate them locally, and return a local verdict. It proves the miner↔relay↔job plumbing works end to end without any pool.
- **Transport:** WebSocket, same-origin only (`connect-src 'self'`). No TLS-to-pool hop, no external connection of any kind.
- **Protocol (binding):** the relay speaks a minimal JSON job protocol modelled on stratum's shape (job id, blob, seed, target; submit with job id + nonce + result) but it is **not stratum** and must not be labelled stratum. Keeping the shape close to stratum is deliberate: it makes the later pool-facing relay a transport swap, not a redesign — but the local-test relay must never be mistaken for a pool connection, so every message and every log line carries a `local-test` marker.
- **Validation (binding):** for every submitted result the relay (a) re-hashes the nonce with the single-thread hash function and compares it to the submitted result, (b) checks the result against the job target with exact 256-bit arithmetic (the pool's own `hashBuffDiff` method, per VoltMiner), (c) counts the submission as accepted-locally / rejected-locally / self-check-drop, and (d) logs job id, nonce, result, and verdict. The relay's accepted count is the Gate 1 evidence (§4.1); the miner's own count is not evidence.
- **What it must NOT do:** connect to any host other than localhost/same-origin; accept a wallet address as a login; forward anything anywhere; store any credential. Its config file contains no pool hostname.
- **Where it lives:** as a small server-side component of the artifact (or a localhost Node process in the test harness — the build lane chooses and records the choice). It must not run on the Muse VM host as a persistent service: the host is control-plane only, memory is already 88.76% (above the 70% cap), and no new daemon is authorized in this mission.

### 2.2 The pool-facing relay (DESIGN-ONLY — not built, not connected, in this mission)

This section is architecture documentation for a future mission. **Nothing in it is built in Mission 4, and building it requires separate explicit authorization** (it is the precondition for Gate 2, which is NOT TESTED in this mission).

- **Architecture (VERIFIED pattern, VoltMiner):** "browsers cannot open a raw TLS stratum socket, so a small origin-locked relay on [a] VPS forwards the WebSocket to the pool. It rewrites nothing — your wallet is the stratum login, and no login, job or share is altered in either direction." (VoltMiner blog, 3 Oct 2026 — see §9.) VoltMiner's transparency page specifies the relay precisely: "relay/server.mjs is the entire server: one WebSocket from an allowlisted Origin, one TLS connection to the pool's host/port (hardcoded, certificate pinned by SHA-256), each line checked for JSON validity, then forwarded. It never rewrites a login, a job or a share." (VoltMiner transparency page — see §9.)
- **ATLAS design (to be implemented only when authorized):**
  - One WebSocket in from an allowlisted Origin (the Command Center origin only); one TLS stratum connection out to the configured pool host/port (hardcoded per pool; certificate pinned by SHA-256).
  - The relay forwards lines after a JSON-validity check and **rewrites nothing**: the user's wallet address is the stratum login, verbatim; jobs and shares pass through unaltered. A relay that rewrites a login could redirect payouts — the no-rewrite rule is a security invariant, and the transparency page must let the user verify it (VoltMiner prints the exact login sent; ATLAS must do the same).
  - Pool endpoints (VERIFIED, Mission 1 §2.4 / Objective 3): MoneroOcean stratum ports 10001/10101; SupportXMR 3333/5555 (bare TCP connect verified 2026-11-18; stratum health not verified beyond that). P2Pool has no central stratum endpoint — it needs a local P2Pool node, which is a separate design item, not a relay config line.
  - Pool selection follows `config/pool-rewards.json`: MoneroOcean primary (0% fee), SupportXMR (0.6%) and P2Pool (0%) fallbacks. The relay must support failover between configured pools and must log which pool each share went to.
  - Hosting: on authorized external infrastructure (a VPS), never on the Muse VM host. The relay is a separate service with its own watchdog/recovery entry (following the `recover.sh` pattern), its own logging, and rate limiting per origin.
  - Security: origin allowlist (exact origin, not a wildcard); per-connection rate limits on submits; no credential storage; no logging of wallet addresses beyond a masked summary; TLS certificate pinning for the pool hop; the relay never holds payout keys and never touches payouts.
- **Explicit gate:** the pool-facing relay is NOT built or connected in Mission 4. The build lane must not write it, stub it with a live endpoint, or leave a "TODO: connect here" that a later run could mistake for a working relay. If the build lane writes any pool-facing code, it must be inert (no socket, no URL, no connection attempt) and labelled `DESIGN-ONLY — NOT CONNECTED`.

### 2.3 Relay failure modes the design must handle (both relays)

- Pool (future) unreachable → the local-test relay reports "no job source" honestly; the future pool relay must surface the failure to the UI, not silently retry forever, and must fail over to the next configured pool after a stated timeout.
- Job timeout / stale job → the miner discards the job and requests a new one; a share submitted against a stale job is rejected-locally and counted, not silently dropped.
- Relay restart mid-run → the miner reconnects, re-requests a job, and resumes; the run's hashrate measurement restarts its averaging window and the UI labels the interruption.
- Malformed message in either direction → the line is dropped and logged, the connection is not trusted further until a fresh job handshake succeeds.

---

## 3. Desktop XMRig design

### 3.1 What it is and why it is the primary path

The desktop miner is a native XMRig-based worker running on the user's own machine (Windows, Linux, or macOS), explicitly activated by that user, mining to a pool with the user's own wallet address as the login. It is the only path that approaches breakeven (Mission 1 verdict): native XMRig is 30–80x faster than the browser tab, and a Ryzen 7 5800X at 10–12.4 kH/s is the reference case.

### 3.2 Installation — official sources only

- **Sources (VERIFIED):** the XMRig official download page (published SHA-256 hashes) or the official XMRig GitHub releases page. The XMRig configuration wizard generates `config.json`. Full URLs are in §9. **No other download source is acceptable** — never a "bundled miner" from a random site, never a third-party repack (Monero.how Windows guide — see §9).
- **Procedure (per platform):**
  - **Windows:** download the `xmrig-*-msvc-win64.zip` release, verify the SHA-256 against the official download page with `certutil -hashfile <file> SHA256` (if it does not match, do not run it), unpack next to `config.json`. Run once as Administrator so huge pages work reliably (XMRig enables `SeLockMemoryPrivilege`; a reboot or sign-out may still be required). Expect a Windows Defender / SmartScreen warning: XMRig is a miner, AV tools flag miners generically. The user must consciously allow it; ATLAS never instructs the user to disable AV wholesale.
  - **Linux:** download the Linux release, verify SHA-256, unpack, `sudo sysctl -w vm.nr_hugepages=1280` (and persist in `/etc/sysctl.conf`) for huge pages; 1 GB pages need GRUB/kernel support and are optional. Run as root once for the MSR/huge-page setup where required, then as a normal user.
  - **macOS:** download the macOS release (Intel and ARM builds exist per the XMRig release page); verify SHA-256; huge pages are limited on macOS — the design must not promise Windows/Linux hashrates on macOS.
- **Version pin:** the build lane records the exact XMRig version used for the Gate measurements (latest listed at design time: 6.26.0 — VERIFIED as listed, but the build lane must re-check at build time and pin what it actually used). A version change invalidates the hashrate comparison until re-measured.

### 3.3 Configuration

Minimal `config.json` (template for the build lane; pool and wallet are placeholders until a real, authorized worker registers):

```json
{
  "autosave": true,
  "cpu": { "enabled": true, "huge-pages": true, "hw-aes": null },
  "donate-level": 1,
  "randomx": { "1gb-pages": false, "rdmsr": true, "wrmsr": true },
  "pools": [
    {
      "algo": "rx/0",
      "url": "POOL_HOST:PORT",
      "user": "USER_WALLET_ADDRESS",
      "pass": "WORKER_NAME",
      "tls": true
    }
  ]
}
```

- **Pool:** from `config/pool-rewards.json` — MoneroOcean primary, SupportXMR / P2Pool fallbacks. The pool URL and port come from the pool's own documented stratum endpoints (MoneroOcean 10001/10101, SupportXMR 3333/5555 — VERIFIED as connectable, Mission 1 §2.4). TLS where the pool offers it.
- **Wallet address field:** the user's own Monero receiving address (95-char standard/subaddress or 106-char integrated), validated with the Mission 3 rules (Base58 alphabet, block decode, Keccak-256 checksum, mainnet network byte 18/19/42) before it is written into the config. The address is the pool login; ATLAS never asks for a seed, key, or password.
- **CPU threads:** default to physical cores minus one (leave one core for the OS/UI); never all cores by default. `cpu.max-threads-hint` / explicit thread list in the config for the Performance profile. The exact thread count is recorded with every hashrate measurement.
- **Huge pages:** `"huge-pages": true` (VERIFIED: XMRig documents up to ~50% more RandomX speed with huge pages; 1 GB pages add a further ~1–3% on Linux where supported — Ypool guide, see §9). If huge pages cannot be enabled, the worker reports it and the hashrate is labelled "no huge pages" — never silently compared against a huge-pages number.
- **Donate level:** XMRig's default donate level is 1% in current releases (1 minute in 100; some older docs and the GitHub README state a 5% default for older versions — the build lane must report the default of the version it pins). The ATLAS template sets `"donate-level": 1` explicitly and discloses it: 1% of the worker's hashrate goes to the XMRig developers, not to ATLAS and not to the user. Setting it to 0 is technically possible and is NOT recommended by this design (the project is actively developed; the 1% is disclosed, not hidden). The donate level is never set silently and never changed without telling the user.
- **MSR mod:** `"rdmsr": true, "wrmsr": true` on supported Intel/AMD CPUs (requires the WinRing0 driver on Windows, shipped in the release zip as `WinRing0x64.sys`). If the MSR mod cannot load, the worker reports it; hashrate is labelled accordingly.

### 3.4 Expected hashrate

| Worker (VERIFIED unless noted) | Hashrate | Source |
|---|---|---|
| Ryzen 7 5800X, native XMRig | **10.0–12.4 kH/s** (XMRig benchmark 12,445 H/s) | Mission 1 §4.1; XMRig benchmark page; Kryptex; asicprofit (see §9) |
| Native laptop (XMRig/P2Pool) | ~6,300 H/s | Mission 1 §4.1 (Monerica, same laptop as the 200 H/s browser tab) |
| Native per core (general) | 450–700 H/s/core | Mission 1 §4.1 (SoapBox) |
| Browser tab, whole tab (32-thread desktop) | ~850 H/s | Mission 1 §4.1 (Monerica) — the comparison point: one 5800X is ~12–15x faster than a whole browser tab on a 32-thread desktop |

**Economics (ESTIMATE, Mission 1 §4.3 / Objective 4):** Ryzen 7 5800X (10–11 kH/s, ~105–171 W) gross ~$0.31–0.36/day, net ~breakeven to −$0.09/day at $0.10–0.18/kWh; the only near-breakeven case, flips negative at 8,245 H/s, and hardware cost (~$500 CPU system) pays back in ~65 years. The desktop path is "the only path near breakeven", not "profitable". The UI must say exactly that.

### 3.5 Safety — explicit activation only

Binding rules for any desktop worker, now and in every future mission:

- **Explicit activation only, per worker, per user.** No silent install, no bundled installer that installs XMRig as a side effect, no autostart without the user's explicit choice, no hidden mining, no mining while the user is unaware. The worker starts only when the user starts it, and stops when the user stops it.
- **Resource controls:** thread cap (physical cores − 1 by default), CPU throttle via XMRig's `cpu.max-threads-hint` / priority settings, and the ATLAS resource profiles (Eco / Balanced / Performance). The UI must state the limits and never silently exceed the user's selected profile.
- **Temperature monitoring where available:** read CPU temperature where the OS exposes it (e.g. `sensors`/`lm-sensors` on Linux, HWMonitor/Open Hardware Monitor on Windows, `powermetrics` on macOS where permitted) and surface it in the worker status. **Auto-stop:** if temperature exceeds a user-set threshold (default: no threshold set — the user must opt in to a number; the design does not invent a safe temperature for hardware it has not seen) or if the user sets a temperature limit and it is breached, the worker stops and reports why. Where no temperature telemetry is available, the UI says "temperature unavailable on this machine" — it never invents a reading.
- **Never silent install:** the user downloads XMRig themselves from the official source, verifies the hash themselves (with ATLAS showing the expected hash), and runs it themselves. ATLAS never pushes an installer, never runs an installer on the user's behalf, never modifies the user's system without the user doing it.
- **No mining on the Muse VM host.** The host has no authorization to mine, permanently until an authorized external resource is approved (Mission 1 capability report). The desktop worker runs on the user's own hardware only.
- **AV/firewall honesty:** the user is told up front that AV tools and firewalls flag miners, that a warning is expected, and that allowing it is their decision. ATLAS never tells the user to disable security software wholesale.

### 3.6 How a desktop worker registers with ATLAS (design, not built)

No registration code exists in this mission. The design for a future mission:

- The user creates an ATLAS account (Mission 5+ scope) and connects their wallet address (Mission 3 validation rules).
- The user generates a **worker credential** in the Command Center: a worker name (e.g. `rig1`) and a per-worker API token/secret, shown once, stored hashed server-side (never in plaintext, never in a URL).
- The user pastes the worker name into XMRig's `pass` field and configures the ATLAS worker agent (a small, separate, explicitly-installed agent — design only) with the token; the agent reports hashrate, accepted/rejected shares (from the pool API, not from XMRig's self-report alone), temperature where available, and uptime to ATLAS.
- The coordinator (Mission 5) verifies the worker: the pool must show accepted shares for that wallet+worker name before the worker is marked `active`. A worker with only local hashrate and no pool-accepted shares is `registered`, never `active`.
- Worker authentication uses the existing `workers` table shape (Mission 2 Stage 0: `user_id`, `worker_type` browser/desktop, `name`, `status`, `registered_at`) extended with an auth-status field and a token hash. No new table design is in scope for this mission.
- Revocation: the user can revoke a worker token from the Command Center at any time; a revoked worker's reports are rejected and the worker is marked `revoked`.

---

## 4. The 5 prototype gates — exact test procedures

Mission 1 §4.5 defined the gates. This section gives each gate an exact procedure, a pass/fail criterion, and a status for this mission. **Gates 2 and 4 are NOT TESTED in this mission** — the reasons are stated in their sections and are not negotiable by the test lane.

### Gate 1 — Measured hashrate in a real browser, local-only

**Status in this mission: TESTED (local-only).**

**Test mechanism (chosen — see the decision table in §0): a test-flag-gated probe hook.**

- The Mining tab exposes `window.__atlasMinerTest` **only** when the page is loaded with the query flag `?atlas-miner-test=1`. Without the flag, the hook does not exist, the miner module is not loaded, and there is no way for a user to start mining from the UI.
- The hook exposes exactly three functions: `startLocalTest(options)`, `stop()`, `status()`. `startLocalTest` accepts only `{ threads, mode: 'fast'|'light', durationSeconds, job }` where `job` is a locally generated test job (§1.7). It refuses any option containing a hostname, URL, wallet address, or pool reference.
- **Why this mechanism (justification):**
  1. It does not touch the Mining tab Start/Stop buttons — they stay hard-disabled with no handler, exactly as Mission 2 built them, so there is no risk of a test accidentally wiring a user-facing control to a live miner.
  2. It is invisible to users: no button, no menu item, no affordance. A user who never adds the flag never sees mining.
  3. It is callable by the audit probe / test harness, which is the only consumer that needs it. The probe loads the page with the flag, calls the hook, reads `status()`, and records the result.
  4. It is self-limiting: `startLocalTest` caps `durationSeconds` at 600 (10 minutes) per call, auto-stops at the cap, and refuses to start while the emergency stop is lifted (it requires the stop to be ON — the test runs under the stop, because the stop governs live activity and the test is not live activity) or while another session is running.
  5. It leaves an audit trail: every hook call is logged (timestamp, options, result) in the test record, so a later reader can tell exactly what ran.
- **Rejected alternatives:** (a) a user-facing "Start mining" button — rejected, it would wire a live control to a miner before Gates 2–5 pass and before any authorization to mine; (b) a self-test that auto-runs on page load — rejected, it would mine on every Mining-tab visit without consent and burn the user's CPU/battery for a measurement nobody asked for; (c) a hidden DOM button the probe clicks — rejected, it is a user-facing affordance in disguise and is fragile to UI changes.

**Procedure:**

1. Preconditions: emergency stop ON; mining disabled in config; page loaded with `?atlas-miner-test=1` on Chrome, then Firefox, then Safari (desktop), on real hardware (record CPU model, core count, RAM, OS, browser version).
2. Correctness bisect first (§1.3 R3): accept-everything target, 1 vs 2 vs 4 threads, MATCH required at every count. Any MISMATCH = Gate 1 FAIL, stop, report.
3. Test-vector check (§1.3 R4): hash the official RandomX test vectors; byte-identical required. Any difference = FAIL.
4. Timed run: Balanced profile (2 threads, fast mode, OPFS dataset cached from a prior generation run — record generation time separately), difficulty-10,000 local test job, 10-minute run, tab visible throughout. Record: hashes computed, wall-clock seconds, measured H/s (mean + 1-minute buckets), thread count, mode, dataset state, peak tab memory, CPU % (from the OS, not the page), self-check drops (must be 0), relay accepted-locally / rejected-locally counts.
5. Repeat at Performance (4 threads) and, if COOP/COEP is unavailable, on the single-thread WebRandomX fallback — each as a separate, labelled measurement.
6. Record what the browser/AV actually did (block, warn, nothing) for each browser.

**Pass criteria (all required):**
- Bisect MATCH at every thread count; test vectors byte-identical; self-check drops = 0.
- A stable measured H/s is reported with its thread count, mode, browser, and hardware attached (no bare number without context).
- Relay accepted-locally count is consistent with the difficulty-predicted share rate (order-of-magnitude agreement; exact agreement is not required because share-finding is Poisson).
- No unexpected network connection (the miner's only connection is the same-origin local-test relay — verified by the test lane).
- **What Gate 1 does NOT prove:** that shares would be accepted by a real pool. That is Gate 2, and Gate 1 passing says nothing about it. The report must state this explicitly.

**Expected numbers (ESTIMATE, for planning only — the measured number is the result):** 4-thread fast-mode browser tab ~90 H/s (VERIFIED, VoltMiner's measured run); 32-thread desktop browser tab ~850 H/s (VERIFIED, Monerica); light mode ~8.8 H/s/core (VERIFIED, SoapBox). If the measured number is an order of magnitude below these, that is a finding to report, not a number to re-run until it looks better.

### Gate 2 — Accepted shares on a real pool

**Status in this mission: NOT TESTED.**

**Reason:** a real-pool share submission requires (a) a pool-facing relay (§2.2) connected to a live pool, (b) a pool account/login (a wallet address as the stratum login), and (c) a live mining run that consumes electricity and creates a (tiny) real reward attribution. Each of those needs separate explicit authorization — from the user, after reading this design — because they cross the line from local-only testing into live interaction with a third-party pool. The mission authorization for Mission 4 covers a prototype, not a pool connection. The build lane must not perform, stub, or simulate a pool submission and call it Gate 2.

**What the future Gate 2 procedure will be (for the authorizing mission to execute):**

1. Authorization obtained; pool-facing relay built per §2.2 on authorized external infrastructure; relay verified to rewrite nothing (login printed verbatim, job/share bytes compared in both directions on a test connection).
2. Run the browser miner (bonanza build, fast mode) against MoneroOcean (primary) at share difficulty 10,000 for a sustained run (minimum 4 hours, matching VoltMiner's soak — ESTIMATE for planning; the authorizing mission sets the exact duration).
3. Record: submits, accepted, rejected, rejection reasons verbatim from the pool, self-check drops (must be 0), pool dashboard worker listing (the worker must appear next to any control worker).
4. **Pass criteria:** rejection rate ~0% (VoltMiner's post-fix run: 21 accepted / 0 rejected); zero `Low difficulty share` rejections; the pool's invalid-share counter for the wallet does not move. Any rejection whose cause is not identified and fixed is a FAIL.
5. A control run (native XMRig or the VoltMiner Android app equivalent) against the same pool and wallet, showing accepted shares, must run alongside — it proves the pool and wallet are fine, so a browser rejection can only be the browser's fault.

### Gate 3 — Sustained run without throttling

**Status in this mission: TESTED (local-only, using the Gate 1 mechanism).**

**Procedure:**

1. Use the Gate 1 hook, fast mode, Balanced (2 threads), difficulty-10,000 local test job.
2. **Phase A — visible tab, 60 minutes continuous.** Record H/s in 1-minute buckets, tab memory, CPU %, and any browser throttling events. Dataset load/generation time on first visit and on repeat visit are recorded separately (first-visit generation is a Gate 3 input, not part of the sustained H/s).
3. **Phase B — hidden tab, 10 minutes.** Hide the tab (switch to another tab; do not close it). Record H/s per minute and the pause/resume log. **Expected result (VERIFIED behaviour): the miner pauses when hidden** (§1.6) — H/s must drop to 0 while hidden and resume when visible. If it does *not* drop to 0, that is a finding (it means the pause control failed), not a bonus.
4. **Phase C — background window (browser window not focused but tab visible), 10 minutes.** Record H/s. Some browsers throttle background windows less aggressively than hidden tabs; the difference, if any, is recorded.
5. **Phase D (if the test hardware allows) — a second 60-minute visible run on a different day / after a browser restart**, to check the OPFS dataset cache survives and the repeat-visit load time.

**Pass criteria:**
- Phase A: H/s stays within ±20% of the run's own median for at least 80% of the 1-minute buckets (ESTIMATE threshold — the build lane reports the actual variance; the criterion is "no progressive collapse", not a specific number). No tab crash, no out-of-memory kill, no runaway memory growth (peak tab memory recorded; growth > 500 MB over the hour without explanation = FAIL).
- Phase B: H/s = 0 while hidden (pause works); resumes within 30 s of the tab becoming visible again.
- Phase C: recorded and reported; no pass/fail on the absolute number, but a collapse to 0 must be labelled as throttling, not as a miner failure.
- First-visit dataset generation time and repeat-visit load time are both reported as numbers, not adjectives.

**Fail criteria:** tab crash or OOM kill; H/s collapsing to near-zero while the tab stays visible (throttling of a visible tab); memory growing without bound; the miner continuing to hash while the tab is hidden (pause control failed).

### Gate 4 — Real payout received above the pool minimum

**Status in this mission: NOT TESTED.**

**Reason (hard gate):** a real payout requires (a) real pool rewards attributed to an ATLAS worker, (b) a payout service with key custody (treasury design — who holds the keys, multisig or single-signer, audit access, recovery — which does not exist and is not approved), (c) a real transaction moving real XMR to a real wallet, and (d) security testing of the whole flow. Mission 1 §7 states this plainly: "no real financial transaction may be activated without explicit user authorization and successful security testing. That is a hard gate, not a formality." A payout also requires the 75/25 accounting to be implemented (Mission 6) and the minimum payout to be set (currently `null` / placeholder in `config/pool-rewards.json`). None of those exist. The test lane must not simulate a payout and call it Gate 4; simulation is Mission 6/10 scope, and a simulated payout is not a payout.

**What the future Gate 4 procedure will be (for the authorizing mission, after simulation/testnet success + security testing):**

1. Minimum payout set above the pool's minimum and above the transaction fee (Mission 1 §7), disclosed to users before mining.
2. A real worker earns a confirmed pool reward; the 75/25 split is calculated from the confirmed reward only (never estimates); the user's 75% exceeds the minimum payout.
3. The payout is submitted, the transaction ID is tracked, on-chain confirmation is tracked, and success is reported **only when the transaction is confirmed on-chain** — never on an API `ok:true` alone (Mission 1.1 tracked-round-trip discipline).
4. Fee accounting is published next to the payout: pool fee, transaction fee, net received.
5. **Pass criteria:** the exact XMR amount arrives at the user's connected address; the txid is on-chain and confirmed; the ledger entry (append-only, piconero integers) matches the payout exactly; no duplicate payment (idempotency key verified by attempting a duplicate submission and confirming it is refused).

### Gate 5 — Honest wall-watt cost accounting

**Status in this mission: TESTED (measurement protocol defined here; the numbers come from the test lane's physical measurement).**

**The rule that governs this gate:** wall watts are measured at the wall with a physical plug-in meter on the user's real hardware. Software power estimates (OS battery/power APIs, CPU TDP × utilization, vendor power models) are **NOT wall watts** and must be labelled as estimates whenever they appear. A software estimate presented as a wall measurement is a FAIL for this gate.

**Measurement protocol (binding):**

1. **Instrument:** a plug-in power meter (e.g. Kill A Watt or equivalent — a meter the test lane names by make/model in its report) between the wall outlet and the test machine's power supply. The meter's own accuracy (±1% typical for this class — ESTIMATE, per the meter's datasheet; the test lane records the datasheet figure) is stated in the report.
2. **Baseline:** machine idle, browser open on a blank page, no mining, 10 minutes. Record mean wall watts (W_idle). All other applications closed; screen brightness fixed; no other load.
3. **Mining run:** same machine, same conditions, browser miner running (Gate 1 hook, fast mode, the thread count being measured), tab visible, 30 minutes. Record mean wall watts (W_mining). Extra watts = W_mining − W_idle.
4. **Desktop control:** same protocol for the XMRig desktop worker (same machine if it can run XMRig, else the desktop test machine — record which). Record W_idle and W_mining for XMRig at its measured hashrate.
5. **Computation (inputs, all labelled):**
   - Extra energy per day = extra watts × 24 / 1,000 (kWh/day).
   - Electricity cost per day = extra kWh/day × the user's electricity price (the test lane uses two prices: the local price where the test ran, and the US average residential ~$0.18/kWh (VERIFIED, Aug 2026, Mission 1 §4.3) — both stated).
   - Gross revenue per day = measured H/s ÷ network H/s × 432 XMR/day × XMR price, using the live network hashrate and XMR price on the test day (sources: MoneroOcean pool stats / CoinGecko, recorded with timestamps).
   - Net per day = gross − electricity cost. The user's 75% share = net × 0.75 only if net is positive; if net is negative, the 75% share of a loss is still a loss and must be shown as one.
6. **Reporting:** the Gate 5 report shows, side by side, for the browser tab and for the desktop worker: measured H/s, extra wall watts, kWh/day, electricity cost/day, gross/day, net/day, and days-to-$1 at the user's 75% share. Every input carries its source and timestamp.

**Pass criteria:**
- A complete wall-watt measurement exists for at least one browser configuration and one desktop configuration, with baseline and mining phases recorded.
- The net figure is computed from the *measured* hashrate and the *measured* extra watts — not from a vendor hashrate or a TDP estimate.
- The report states the net plainly, including when it is negative. **A negative net is a PASS for Gate 5** (the gate measures honesty, not profitability) — hiding it or softening it is a FAIL.
- Software power estimates, if shown at all, are labelled "ESTIMATE — software power model, not a wall measurement" and are never the basis for the net figure.

**Expected outcome (ESTIMATE, Mission 1 §4.3):** laptop browser tab gross ~$0.008/day, extra power ~30–60 W, net approx −$0.10 to −$0.13/day; Ryzen 7 5800X native gross ~$0.31–0.36/day, net ~breakeven to −$0.09/day. If the measured numbers differ materially, the measured numbers win and the Mission 1 estimates are corrected in the test report.

---

## 5. Mining tab prototype UI spec — "Miner Prototype" section

**Location:** inside the existing Mining tab (artifact `atlas-command-center`, `client/src/Mining.tsx`). **NO new tab.** No new card outside the Mining tab. The wallet center (Mission 3) is untouched except to read it — the prototype section sits below the existing sections and does not reorder, restyle, or reword them.

**Contents (all required):**

1. **Section header:** "Miner Prototype — Master Mission 4". Subtitle: "Design prototype. No live mining. No pool connection. No earnings." The header carries a PROTOTYPE tag (same provenance-tag pattern as the rest of the tab: SNAPSHOT / RECORDED / ESTIMATE / UNAVAILABLE).
2. **The 5 gates, with statuses.** A table/list, one row per gate:
   - Gate 1 — Measured hashrate in a real browser (local-only) — status: TESTED / measured H/s shown once the test lane fills it in, or "Awaiting test" before then. Shows the measured H/s with thread count, mode, browser, and hardware attached.
   - Gate 2 — Accepted shares on a real pool — status: NOT TESTED — needs separate explicit authorization. (Never "pending" as if it will happen on its own.)
   - Gate 3 — Sustained run without throttling — status: TESTED / awaiting test, with the visible-vs-hidden numbers once measured.
   - Gate 4 — Real payout above the minimum — status: NOT TESTED — hard gate: explicit authorization + security testing.
   - Gate 5 — Honest wall-watt cost accounting — status: TESTED / awaiting test, with the measured net/day once measured.
   - Each gate row links to (or quotes) its pass/fail criterion from §4. A gate that has not been tested shows no number — never a placeholder number.
3. **Measured hashrate panel.** Filled by testing (§4.1/§4.3): measured H/s per configuration (browser + threads + mode + hardware), dataset generation/load times, peak tab memory, self-check drops (must be 0). Before testing, the panel shows "No measurement yet — the prototype has not been run" and nothing else. The panel never shows a vendor or author-published hashrate as if it were ATLAS's measurement; published figures appear only in a clearly labelled "Published figures from other projects (not ATLAS measurements)" line.
4. **Desktop XMRig design summary.** A compact summary of §3: official sources only (XMRig download page, GitHub releases — full URLs in §9), explicit activation, huge pages, donate level 1% disclosed, expected Ryzen 7 5800X 10–12.4 kH/s (VERIFIED), and the registration design (worker name + per-worker token, pool-accepted shares required before `active`). This is a design summary with a "Design — not built" tag, not an installer and not a download button that fetches anything.
5. **Honest framing (mandatory copy, binding on the build lane — do not soften):**
   - "Browser mining is a participation/demo feature. It does not earn meaningful money: a laptop browser tab earns about $0.008/day gross and loses about $0.10–0.13/day after electricity (Mission 1). With the 75/25 split, a user keeps about $0.006/day — about 167 worker-days to earn $1."
   - "Desktop mining with XMRig is the only path near breakeven, and even it barely breaks even at average electricity prices."
   - "No earnings are shown until they are confirmed pool rewards. Estimates are labelled ESTIMATE and never create a balance."
   - "Never promise guaranteed profits" — the UI contains no profit promise, no projected-earnings headline, no "earn $X/day" copy.
6. **Start/Stop buttons stay hard-disabled.** The existing Start/Stop buttons (Mission 2) remain `disabled` with no handler, exactly as built. The prototype section adds no start control of any kind. The test hook (§4.1) is not a UI control and is not rendered.
7. **WASM build provenance line:** engine name + pinned commit + Emscripten version + SHA-256 of the shipped `.wasm` (once the build lane pins them), plus the dataset state (seed, cached/generating/ready) and the threading mode actually in use (`crossOriginIsolated: true/false`, thread count).

**What the section must NOT contain:**

- No demo users, workers, shares, earnings, or payouts. No seeded data of any kind. The tab stays honestly empty until real data exists (Mission 2 rule, carried forward).
- No fictional earnings, no projected balance, no "estimated daily earnings" headline. The calculator (Mission 2 §9) already exists and is labelled ESTIMATE; the prototype section does not duplicate it with a rosier number.
- No pool connection status that implies a live pool ("Pool: connected" must never appear — there is no pool connection).
- No wallet/key creation, no seed-phrase field, no password field. The wallet center is read-only from this section's point of view.
- No change to the refresh behaviour, the emergency stop, the orb, or any other tab.

**Provenance:** every figure in the section carries a SNAPSHOT / RECORDED / ESTIMATE / UNAVAILABLE tag, following the tab's existing pattern. A measured hashrate is RECORDED (with the measurement timestamp); a published figure is ESTIMATE or cited external data, never RECORDED.

---

## 6. Safety and limits checklist — binding on the build and test lanes

The build lane and the test lane must confirm each item before they start work, and re-confirm it in their reports. Any item that cannot be confirmed is a stop, not a note.

**Never in this mission:**
- [ ] No pool connection for earning. No stratum connection of any kind. No share submission to any pool.
- [ ] No real payout. No payout flow, no payout transaction, no test wallet with real funds.
- [ ] No wallet creation, no key creation, no seed phrase, no private key, no password — nothing custodial, anywhere.
- [ ] No spending of any kind. No rental, purchase, subscription, or paid service.
- [ ] No config changes. `config/atlas.json` and `config/pool-rewards.json` are read-only inputs; the minimum payout stays `null`/placeholder; the mode stays `simulation-only`.
- [ ] No lifting the emergency stop. No change to any safety setting. The stop stays ON; mining stays disabled in config; trading stays paper-only; capital stays $0.
- [ ] No mining on the Muse VM host. The host is control-plane only (no GPU, 4 vCPUs, 1.5 shared-CPU cap, 6 GB RAM cap, memory already 88.76% at design time). The browser miner runs only in the tester's browser; the desktop design runs only on a user's own machine.
- [ ] No live trading, no capital, no financial transaction of any kind.
- [ ] No new daemon, no new persistent service, no new cron job, no new scheduled job on the host.
- [ ] No new database migration, no new tables, no seeded rows (unless a design note in this document explicitly calls for it — none does).
- [ ] No user-facing "start mining" control. The Start/Stop buttons stay hard-disabled with no handler. The only start mechanism is the test-flag-gated probe hook (§4.1).
- [ ] No background/hidden-tab mining. The pause-on-hidden control (§1.6) is mandatory and is tested in Gate 3 Phase B.

**Do not touch:**
- [ ] Do not touch the wallet center except to read it. No edits to the onboarding guides, the validation logic (`server/src/monero.ts`), the QR code, the address-change flow, or the change log.
- [ ] Do not fix the refresh failure (Mission 3 finding 1: dashboard snapshot goes stale, refresh fails at the platform spawn step; the "Refresh complete" label is misleading when it re-ingests a stored snapshot). That repair needs a repair-authorized inspection and is explicitly NOT authorized by this mission. The build/test lanes must not attempt it, work around it, or present a stale snapshot as fresh.
- [ ] Do not touch the orb, the other tabs, the emergency stop panel, or the diagnostics suite — except to run diagnostics read-only if the test lane needs a host health check (it must not restart the daemon or change anything).
- [ ] Do not change the 75/25 split, the fee disclosure, or the ledger rules in `config/pool-rewards.json`. The split applies to confirmed pool rewards only — never to estimated hashrate, never to the test lane's local-test counts. A local-test "accepted" count is not a reward and creates no balance.

**Must do:**
- [ ] Every external claim in the build/test reports carries a source URL; every figure carries a VERIFIED / ESTIMATE / ASSUMPTION label.
- [ ] The shipped WASM bytes are SHA-256-pinned and the hash is re-verified by the test lane from the served bytes.
- [ ] The miner bundle is grepped for pool hostnames, stratum URLs, and wallet-address patterns before the test runs (§1.7).
- [ ] The Gate 1 bisect (§1.3 R3) passes before any timed run.
- [ ] The test report states, for each gate, TESTED or NOT TESTED, with the reason for any NOT TESTED gate copied from §4 — not paraphrased into something softer.
- [ ] The test report records what Chrome, Firefox, and Safari actually did to the page (block/warn/nothing) and what AV did to the WASM binary.
- [ ] The test report records the COOP/COEP probe result (§1.6) — whether `crossOriginIsolated` was true on the artifact host — because it determines which threading mode was actually measured.
- [ ] All test data is recorded with hardware, browser, thread count, mode, and timestamps attached. A bare hashrate number without context is not a result.

---

## 7. Open items and risks carried forward (not resolved by this design)

1. **COOP/COEP on the artifact host — UNVERIFIED.** Whether the Muse artifact host sends the headers (or lets the artifact set them) determines whether multi-threaded mode exists at all. The build lane probes this first (§1.6). If the answer is no, Gate 1 is measured single-threaded and the design stands — but the browser prototype's value drops further.
2. **RandomX v2.** Released March 2026, no mainnet activation date as of 1 Nov 2026 (VERIFIED). The chosen build is a v1 engine; a v2 activation requires a rebuild and revalidation. The prototype must not be presented as future-proof (§1.8).
3. **Browser/AV blocking.** Firefox, Brave, and AV tools block mining scripts (VERIFIED). The test lane measures the actual behaviour; a block on a major browser is a shippability finding, not a design failure.
4. **Treasury design.** Does not exist, is not approved, and is not in this mission's scope. Gates 2 and 4 cannot be authorized until it exists (Mission 1 §7, §10).
5. **Minimum payout.** Still `null`/placeholder in `config/pool-rewards.json`. A browser-only user takes ~7 months to reach a 0.003 XMR pool minimum (VERIFIED, Mission 1 §4.3) — the payout UI must show this honestly when payouts are eventually designed.
6. **Host memory.** 88.76% at design time, above the 70% cap (standing, pre-existing). Nothing in this mission adds host load; the local-test relay must not become a persistent host service (§2.1).
7. **Refresh failure (Mission 3 finding 1).** Unfixed by design in this mission. Any test that reads the dashboard must check the snapshot timestamp and label stale data as stale; a stale snapshot must never be presented as a fresh measurement.
8. **Rendered verification gap (Mission 2 §5, partly closed in Mission 3).** The Mining tab's rendered layout was verified for the wallet center on the previous build; the current build's interactive audit was never executed (Mission 3 §6.2). The prototype section's rendered layout must be verified by the test lane on desktop and mobile on the build it actually ships.

---

## 8. What the build lane receives from this design (handoff checklist)

- WASM engine: RandomX-bonanza @ f9848e3, Emscripten 4.0.10, VoltMiner overlay patches incl. the `__thread` rounding-mode fix; WebRandomX @ 780908a as the single-thread fallback. Reproduce the build; pin the SHA-256; record any deviation.
- Loading: bundled, same-origin, CSP `script-src 'self' 'wasm-unsafe-eval'`, `connect-src 'self'` only.
- Dataset: fast mode primary (~2 GB, OPFS cache, local generation from the seed); light mode labelled fallback; 4 GiB budget enforced.
- Threading: probe COOP/COEP first; multi-threaded only if `crossOriginIsolated`; else single-threaded fallback. Threads capped at 4; default profile Balanced (2 threads).
- Controls: throttle, pause-on-hidden (mandatory), memory cap, one instance per tab.
- Local-only: synthetic test job, accept-everything bisect, difficulty-10,000 timed run; no pool strings in the bundle.
- Relay: local-test relay only (same-origin WebSocket, `local-test` markers, local validation with exact 256-bit difficulty check). Pool-facing relay is design-only (§2.2) — do not build it.
- Desktop: XMRig from official sources only, hash verified, config template §3.3, donate level 1% disclosed, huge pages on, explicit activation only.
- Gates: Gate 1 and 3 and 5 tested per §4; Gates 2 and 4 NOT TESTED, with the reasons in §4.2/§4.4.
- UI: "Miner Prototype" section inside the Mining tab, per §5; Start/Stop stay disabled; no demo data; honest framing copy verbatim.
- Safety: §6 checklist, confirmed before work and in the report. Do not fix the refresh failure. Do not touch the wallet center except to read it.

---

## 9. Sources

Every external claim in this document traces to one of the following. URLs are copied verbatim from the sources consulted on 2026-11-18.

**WASM implementations and the rounding-mode bug**
- VoltMiner, "RandomX in a Browser: Why Every Single Share Was Rejected" (3 Oct 2026) — https://www.voltminer.net/blog/randomx-in-a-browser-the-rounding-mode-bug — the bug, the fix (`__thread` rounding mode, separate build targets, re-hash self-check), the verification run (260,444 hashes, 21 accepted / 0 rejected, ~90 H/s, 4 threads), the accept-everything-target bisect, the COOP/COEP requirement, the relay pattern.
- VoltMiner Browser Experiment, third-party notices — https://j3r0nim0.github.io/voltminer-web/notices.html — the two shipped builds (RandomX-bonanza @ f9848e3 with Emscripten 4.0.10 + RandomX-JIT-overlay; WebRandomX @ 780908a with Emscripten 4.0.10 + WebRandomX-overlay), licences (RandomX BSD-3-Clause; WASM JIT backend CC0 1.0; semifloat.c/mulh.c BSD-3-Clause © tevador and l-m), "Do not hotlink a third-party wasm at runtime; both binaries are committed here."
- VoltMiner Browser Experiment, transparency — https://j3r0nim0.github.io/voltminer-web/transparency/ — CSP (`default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' ws: wss:`), relay/server.mjs description (allowlisted Origin, TLS to pool host/port hardcoded, certificate pinned by SHA-256, JSON-validity check per line, never rewrites a login/job/share), reproducible build (wasm-patch + build-web-randomx-mt.sh, Docker + Emscripten 4.0.10), OPFS dataset cache, "Delete cached dataset" control.
- RandomX-bonanza project page — https://randomx.cc/ — full-mode ~10% of native on AMD64, ~23–25% on Apple M4 ARM64 (10 cores vs native XMRig); light mode ~53–67% of native light-mode efficiency (M4); "randomx.js is pretty much the only thing out there that actually works… except it only supports light mode."
- randomx.js (l1mey112) — https://github.com/l1mey112/randomx.js — "Mining with an initialised dataset (2 GiB allocation) is not supported… Light/verification mode only."; WASM JIT generating code on the fly; tested against official RandomX test vectors; zero JS dependencies.
- l-m, "Zero to RandomX.js: Bringing Webmining Back From The Grave" (Linux Society UNSW 2025) — https://blog.l-m.dev/talks/zero-to-randomx-js-webmining.pdf — WASM has no directed-rounding support; no native AES instruction.
- SoapBox pool — https://pool.soapbox.community/ — browser WASM ~8.8 H/s/core (light mode, measured vs official RandomX test vector); phone 2–5 H/s/core; native 450–700 H/s/core; browser vs native ~50–80x; "Mining stops if you close or background the tab"; code open (`randomx.js`, BSD-licensed).
- BlackMine — https://www.blackmine.app/mine — cited in Mission 1 ("a browser thread does a few hashes a second, a desktop XMRig does thousands").

**RandomX and Monero**
- RandomX README / design (via Bit2Me Academy summary, accessed 2026-11-18) — https://academy.bit2me.com/en/que-algoritmo-mineria-randomx-monero/ — fast mode 2,080 MiB dataset, light mode 256 MiB cache; RandomX v2 released March 2026, no official mainnet activation date as of 1 Nov 2026; "web mining is impractical" (RandomX README).
- Monerica, "Monero Browser Mining 2026" (updated 24 Oct 2026) — https://blog.monerica.com/articles/monero-browser-mining — laptop browser ~200 H/s; 32-thread desktop browser ~850 H/s; native laptop ~6,300 H/s vs 200 H/s browser on the same laptop; browser ~$0.008/day gross; ~7 months to reach a 0.003 XMR minimum payout.
- Coinhive shutdown, BleepingComputer — https://www.bleepingcomputer.com/news/security/coinhive-in-browser-cryptomining-service-shuts-down-on-march-8/ — Coinhive mined CryptoNight, shut down 8 March 2019.

**XMRig (desktop)**
- XMRig official download page — published SHA-256 hashes; verify with `certutil -hashfile <file> SHA256`. (Full URL withheld by a tooling block on the miner's own domain in this session; the URL is the official download page linked from the Monero.how guide below and from the Mission 1 report §5 sources.)
- XMRig GitHub releases page — official binary releases for Windows, Linux, and macOS. (Same tooling note: the releases live under the xmrig organization on GitHub.)
- XMRig configuration wizard — generates `config.json`. (Same tooling note.)
- Monero.how, "How to Mine Monero on Windows (2026): XMRig (CLI) + P2Pool + GUI Options" — official sources only; SHA-256 verification; run once as Administrator for huge pages; "Never download 'bundled miners' from random sites." (Same tooling note: the guide is on the Monero.how site, Windows mining page.)
- XMRig benchmark, Ryzen 7 5800X — 12,445 H/s (XMRig benchmark page; Kryptex and asicprofit device pages agree on the 10.0–12.4 kH/s range — full URLs withheld by the same tooling block; all three were returned verbatim by web search on 2026-11-18 and are cited in the Mission 1 report §5).
- Ypool, "How to Mine Monero: CPU, XMRig and P2Pool Guide (2026)" — huge pages up to +50% RandomX speed, 1 GB pages +1–3%; donate level 1% default in current releases. (Full URL withheld by the same tooling block; cited in the Mission 1 report §5.)
- XMRig overview site — cross-platform (Windows/Linux/macOS), `--donate-level` default 1% in current builds, WinRing0 driver for huge pages/MSR. (Full URL withheld by the same tooling block.)

**Pools**
- MoneroOcean stratum ports 10001/10101 and SupportXMR 3333/5555 — VERIFIED as connectable (bare TCP) 2026-11-18, Mission 1 §2.4 / Objective 3 findings. MoneroOcean pool-stats API endpoint — VERIFIED 200 from this host, 2026-11-18.
- Pool fees and split: `~/workspace/atlas/config/pool-rewards.json` (MoneroOcean 0%, SupportXMR 0.6%, P2Pool 0%; 75/25 on confirmed pool rewards only; simulation-only; minimum payout placeholder null).

**ATLAS internal sources (read 2026-11-18)**
- `~/workspace/atlas/docs/master-mission1-inspection-report-2026-11-18.md` — feasibility verdict, economics, 5 gates, 75/25 accounting basis, payout architecture, sequencing, risks.
- `~/workspace/atlas/docs/master-mission2-report-2026-11-18.md` — Mining tab state (12 sections + 75/25 panel, Start/Stop disabled, all-zero honest state, rendered-verification gap).
- `~/workspace/atlas/docs/master-mission3-report-2026-11-18.md` — wallet center, validation rules, refresh failure (finding 1), current-build interactive audit never executed (finding 2).
- `~/workspace/atlas/config/atlas.json` — emergency_stop true, mining disabled/design-only, trading paper-only, capital $0, limits 50/70.
- `~/workspace/atlas/config/pool-rewards.json` — pool config, split, ledger rules, simulation-only mode.

---

*End of design. No code was written for this document. The build lane implements from it; the test lane verifies against it. Gates 2 and 4 remain NOT TESTED and require separate explicit authorization.*
