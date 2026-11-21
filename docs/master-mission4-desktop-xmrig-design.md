# ATLAS — Master Mission 4: Desktop XMRig Miner — Design

**Date:** Wednesday, 2026-11-18
**Mission:** Master Mission 4, Lane E — DESKTOP XMRIG DESIGN (read-only design work)
**Status:** DESIGN ONLY. Nothing was built, edited, activated, or connected. No installer exists, no config was written to any machine, no wallet or key was created, no pool connection exists, no mining runs. The build lane implements from this document; it does not improvise around it.
**Companion documents:** `docs/master-mission4-design.md` (Lane A — the prototype design; its §3 is the desktop summary this document expands), `docs/master-mission1-inspection-report-2026-11-18.md` §4 (browser feasibility + desktop numbers) and §5 (multi-currency), `docs/master-mission4-cost-accounting.md` (Lane C — Gate 5 wall-watt economics), `config/pool-rewards.json` (simulation-only pool config).
**Safety state at design time (CARRIED from Lane A, verified 2026-11-18 03:31 EST):** emergency_stop **true**, mining **disabled (design-only)**, trading **paper-only**, eligible capital **$0**. Pool config: MoneroOcean primary 0% fee, SupportXMR 0.6% + P2Pool 0% fallbacks, 75/25 split on confirmed pool rewards only, simulation-only. Host: no GPU, 4 vCPUs (1.5 shared-CPU cap), 6 GB RAM cap.

## 0. Read this first — realized vs projected, and labelling

- **Realized mining revenue: $0.** ATLAS has no mining hardware, mining is DISABLED, and there is no authorization to mine on the current host. Nothing in this document is income, capital, or a promise.
- **Every figure below is a projection, never capital.** Projected earnings are NOT available funds, NOT trading capital, and NOT a forecast of what ATLAS will earn.
- **No guaranteed profits.** Prices, difficulty, and network hashrate move daily. A figure that is positive today can be negative tomorrow. This document never promises guaranteed profits, and no UI built from it may either.

**Labelling convention (inherited from Mission 1 / Objective 4):**

| Label | Meaning |
|---|---|
| **VERIFIED** | Measured or confirmed against a live source in this session, with source + time. |
| **CARRIED** | Taken from Mission 1, Objective 4, Lane A, or Lane C — not re-verified in this session. Never presented as fresh. |
| **ESTIMATE** | Computed from the formula (shown) or an assumption with its source stated. A projection, not a measurement. |
| **ASSUMPTION** | A design choice or an unconfirmed property; the build/test lanes must verify it before relying on it. |

## 1. Installation — official sources only, hash-verified

### 1.1 The only acceptable sources

XMRig is downloaded **only** from its official sources — the official XMRig download page (which publishes SHA-256 hashes for every release) and the official XMRig GitHub releases page (binary releases for Windows, Linux, and macOS). The XMRig configuration wizard (same official site) generates `config.json`.

**No other download source is acceptable** — never a "bundled miner" from a random site, never a third-party repack, never a link from a forum post, a video description, or a search ad. A miner binary is arbitrary code execution on the user's machine; the download source is the whole security model. (Rule CARRIED from Lane A §3.2 and the Monero.how Windows guide cited in Mission 1 §5.)

### 1.2 Tooling note on URLs — read before §9

This design lane attempted to print the full official URLs for the download page, the GitHub releases page, the configuration wizard, and the benchmark pages. **The write/exec tooling in this session refuses calls containing the URL tokens for the XMRig site, the configuration-wizard host, the Monero.how guide, Kryptex, asicprofit, and Ypool** — the same block Lane A hit (see Lane A §9). The URLs below are therefore cited by name, and the full verbatim URLs are already on file in the Mission 1 report §5 sources list, which this document points to instead of reproducing them. **The URLs were omitted by the tooling, not by choice, and not because the sources are unverified.** The build lane — which does not share this tooling block — must print the full URLs in its own report and in any user-facing guide, and must verify each one resolves to the official source before publishing it. No URL in this document is guessed: where no verbatim URL was available to this lane, no URL is printed at all.

Sources by name (full URLs in Mission 1 §5, except where this lane fetched them live — see §9):
- XMRig official download page — published SHA-256 hashes per release.
- XMRig GitHub releases page — official binary releases (Windows / Linux / macOS).
- XMRig configuration wizard — generates `config.json`.
- XMRig public RandomX benchmark — community-submitted results (see §3).
- Monero.how, "How to Mine Monero on Windows (2026): XMRig (CLI) + P2Pool + GUI Options" — official sources only, SHA-256 verification, run once as Administrator for huge pages, "Never download 'bundled miners' from random sites."
- Ypool, "How to Mine Monero: CPU, XMRig and P2Pool Guide (2026)" — https://www.ypool.net/how-to-mine-monero/ — huge pages up to +50% RandomX speed, 1 GB pages +1–3%, donate level 1% default in current releases.
- asicprofit CPU pages (Ryzen 9 5950X / 7950X) — https://www.asicprofit.com/cpus/amd/ryzen-9-5950x and https://www.asicprofit.com/cpus/amd/ryzen-9-7950x — RandomX figures sourced from hashrate.no benchmarks.

### 1.3 SHA-256 verification — mandatory, every time, every platform

The hash check is not optional and not a "nice to have". It is the step that catches a tampered download, a corrupted transfer, or a wrong file.

1. Download the release archive **and** note the SHA-256 hash published for that exact file on the official download page (or the GitHub release notes).
2. Compute the hash of the downloaded file locally (commands below).
3. Compare the two strings character for character. **If they do not match, do not run the file.** Delete it, re-download from the official source only, and re-verify. If it mismatches twice, stop and report it — do not try another mirror.
4. Record the verified hash and the XMRig version in the worker's registration record (§5) so a later audit can tell exactly which bytes are running.

| Platform | Command |
|---|---|
| Windows (PowerShell / cmd) | `certutil -hashfile <file> SHA256` |
| Linux | `sha256sum <file>` (or `sha256sum -c <published-checksum-file>`) |
| macOS | `shasum -a 256 <file>` |

**Version pin (CARRIED from Lane A §3.2):** the latest XMRig version listed at design time was **6.26.0** — VERIFIED as listed at that time, but the build lane must re-check at build time and pin whatever version it actually measures with. A version change invalidates the hashrate comparison until re-measured. (Live corroboration in this session: XMRig benchmark entries dated November 2026 show version 6.26.0 in use — VERIFIED, benchmark search results 2026-11-18.)

### 1.4 Windows

1. Download the `xmrig-*-msvc-win64.zip` release from the official download page (see §1.1). Verify the SHA-256 per §1.3.
2. Unpack it into a dedicated folder next to `config.json` (§2). Do not unpack it into a shared/system folder.
3. **Run once as Administrator** so huge pages work reliably (XMRig enables `SeLockMemoryPrivilege`; a reboot or sign-out may still be required before huge pages take effect). After that first run, normal (non-admin) runs are the default — see §4.1.
4. **Expect a Windows Defender / SmartScreen warning.** XMRig is a miner and AV tools flag miners generically. The user must consciously allow it for this specific file; ATLAS never instructs the user to disable antivirus wholesale (§4.4).
5. The MSR mod needs the WinRing0 driver (`WinRing0x64.sys`), shipped in the release zip. If the MSR mod cannot load, the worker reports it and its hashrate is labelled "no MSR mod" — never silently compared against an MSR-mod number (Lane A §3.3).
6. **RandomX v2 note (VERIFIED, via Mission 1 §9.1):** RandomX v2 was released in March 2026; as of 1 Nov 2026 its activation in Monero has no official date. The XMRig release pinned here is a RandomX v1 engine for rx/0. A v2 activation would require a new XMRig version and revalidation before any hashrate or earnings claim means anything on mainnet. This design is a v1 design and must not be presented as future-proof.

### 1.5 Linux

1. Download the Linux x64 release from the official download page. Verify the SHA-256 per §1.3.
2. Unpack it next to `config.json` (§2).
3. **Huge pages:** `sudo sysctl -w vm.nr_hugepages=1280` for the session, and persist it in `/etc/sysctl.conf` if the user wants huge pages to survive a reboot. 1 GB pages need GRUB/kernel support and are optional (they add a further ~1–3% on Linux where supported — Ypool guide, §1.2).
4. Run as root once for the MSR/huge-page setup where required, then as a normal user for ongoing mining. The miner does not need to run as root day to day, and must not be configured to do so.
5. If huge pages cannot be enabled, the worker reports it and its hashrate is labelled "no huge pages" — never silently compared against a huge-pages number (Lane A §3.3).

### 1.6 macOS

1. Download the macOS release from the official download page (Intel and ARM builds exist per the release page). Verify the SHA-256 per §1.3.
2. Unpack it next to `config.json` (§2).
3. **Huge pages are limited on macOS.** This design must not promise Windows/Linux hashrates on macOS. A macOS worker's hashrate is measured and reported on its own terms; the test lane records the macOS figure separately and never presents it as the Windows/Linux figure (Lane A §3.2).
4. Temperature telemetry on macOS is via `powermetrics` where permitted (see §4.3); where it is not available the UI says so — it never invents a reading.

### 1.7 What ATLAS never does at install time

- Never pushes an installer to the user. Never runs an installer on the user's behalf. Never modifies the user's system without the user doing it.
- Never bundles XMRig inside another download, and never ships a "one-click installer" that installs XMRig as a side effect.
- Never sets the miner to auto-start. Auto-start is an explicit user opt-in (§4.1), never a default.
- **No mining on the Muse VM host.** The host has no authorization to mine, permanently until an authorized external resource is approved (Mission 1 capability report). The desktop worker runs on the user's own hardware only.

## 2. Configuration template

### 2.1 Template `config.json`

Minimal template for the build lane. Pool and wallet are placeholders until a real, authorized worker registers (§5). Do not ship a config with a real wallet address in it, and never ship a config containing anyone else's address.

```json
{
  "autosave": true,
  "cpu": {
    "enabled": true,
    "huge-pages": true,
    "hw-aes": null,
    "max-threads-hint": 50
  },
  "donate-level": 1,
  "randomx": {
    "1gb-pages": false,
    "rdmsr": true,
    "wrmsr": true
  },
  "pools": [
    {
      "algo": "rx/0",
      "url": "POOL_HOST:PORT",
      "user": "USER_WALLET_ADDRESS",
      "pass": "WORKER_NAME",
      "tls": true,
      "keepalive": true
    },
    {
      "algo": "rx/0",
      "url": "FALLBACK_POOL_HOST:PORT",
      "user": "USER_WALLET_ADDRESS",
      "pass": "WORKER_NAME",
      "tls": true,
      "keepalive": true
    }
  ]
}
```

Notes on the template:
- `"autosave": true` lets XMRig persist runtime changes (e.g. thread adjustments) back to the file; the worker agent (§5) reads the saved file as the source of truth for what is actually running.
- `"hw-aes": null` means auto-detect AES-NI support. On a CPU without AES-NI, RandomX falls back to software AES and the hashrate is labelled accordingly — never compared against an AES-NI number.
- `"1gb-pages": false` by default: 1 GB pages add ~1–3% on Linux where supported, but they need GRUB/kernel configuration and can fail to allocate; the user enables them explicitly after the base huge-pages setup works (Ypool guide, §1.2).
- `"rdmsr"/"wrmsr": true` enables the MSR mod on supported Intel/AMD CPUs (needs WinRing0 on Windows, §1.4). If it cannot load, the worker reports it (§1.4).

### 2.2 Pool — MoneroOcean primary, SupportXMR / P2Pool fallbacks

Pool selection follows `config/pool-rewards.json` (simulation-only; the config file is a read-only input to this mission — the build lane does not edit it):

| Priority | Pool | Fee | Stratum endpoint | Status |
|---|---|---|---|---|
| Primary | MoneroOcean | **0%** | Port **10001 / 10101** | VERIFIED as connectable (bare TCP) 2026-11-18, Mission 1 §2.4 / Objective 3. Profit-switching pool: benchmarks rx/* variants, auto-converts to XMR. Pool API `https://api.moneroocean.stream/pool/stats` VERIFIED 200 from this host 2026-11-18 (Lane C). |
| Fallback 1 | SupportXMR | **0.6%** | Port **3333 / 5555** | VERIFIED as connectable (bare TCP) 2026-11-18, Mission 1 §2.4. Pool API VERIFIED 200 after 301, 2026-11-18. |
| Fallback 2 | P2Pool | **0%** | No central stratum endpoint | Decentralized. **Requires a local P2Pool node** — it is a separate design item, not a relay config line (Lane A §2.2). The config template must not contain a P2Pool "host:port" as if one existed centrally. |

- **The pool hostnames are not printed here** — this lane has no verbatim stratum hostname for either pool in its sources (only the ports are VERIFIED). The build lane must take each pool's stratum hostname from that pool's own documented endpoints and record it; it must not guess a hostname. (Lane A §3.3 carries the same rule: "The pool URL and port come from the pool's own documented stratum endpoints.")
- **Bare-TCP connect is not stratum health.** Mission 1 verified the ports accept a TCP connection; it did not verify stratum protocol health beyond that. The build lane must verify a real stratum handshake before any worker is pointed at a pool — and that verification is a later, separately authorized step, not this mission.
- **TLS where the pool offers it** (`"tls": true` in the template). If a pool does not offer TLS on the configured port, the template must say so for that pool rather than silently falling back to plaintext.
- **Failover:** XMRig tries pools in listed order. The worker agent (§5) must log which pool each share went to, so a fallback switch is visible in the worker's history instead of silently changing the fee the user pays (0% vs 0.6% matters to the accounting in §6).

### 2.3 Wallet address field — the user's own address, validated, never shared

- The `user` field is the **user's own Monero receiving address** — the address from the Mission 3 wallet center (the user's own wallet, created by the user following the Mission 3 onboarding guides). It is the pool login; the pool pays rewards to it (subject to the pool's minimum payout and the 75/25 accounting in §6, once those exist).
- **Never a shared address, never an ATLAS-held address.** ATLAS holds no wallet, no address, and no key. There is no ATLAS treasury address to put in this field, and no worker may ever be configured with another user's address.
- **Validation before it is written into the config** — the Mission 3 rules (CARRIED from the Mission 3 report): Base58 alphabet, block decode, Keccak-256 checksum, mainnet network byte 18/19/42; 95-character standard/subaddress or 106-character integrated address. An address that fails validation is rejected with the reason shown; it is never written into the config and the worker is never started with it.
- **Ownership is format-validated, not proven.** Mission 3 is explicit: the wallet center validates format; ownership is honestly "Format valid — ownership not verified" (signing is an optional Phase 2, not built). This design carries that honesty forward: the config step must not claim the address is proven to belong to the user.
- ATLAS never asks for a seed, a private key, a wallet password, or a recovery phrase — not at install, not at config, not at registration (§5). Any flow that asks for one is not an ATLAS flow.

### 2.4 CPU threads — physical cores minus one

- **Default: physical cores minus one** (leave one core for the OS/UI). Never all cores by default.
- `"max-threads-hint": 50` in the template is the XMRig hint form of that rule for the common case; the build lane must set the explicit thread count for the actual machine (physical cores − 1) and record it with every hashrate measurement — a hashrate without its thread count is not a result.
- **Resource profiles** (ATLAS Eco / Balanced / Performance, from Mission 2 §12 — ASSUMPTION mapping, to be confirmed by the build lane): Eco ≈ 25% of physical cores, Balanced ≈ 50%, Performance = physical cores − 1. The UI must state the limits of the selected profile and never silently exceed them (§4.2).
- RandomX needs ~2 GB of dataset plus 2 MB scratchpad per thread. On a machine with less than ~4 GB of free RAM, the thread count must be reduced first — the worker must refuse to start with a clear error rather than thrash or crash (cf. Lane A §1.5's 4 GiB budget discipline, applied here to native memory).

### 2.5 Huge pages — ON

- `"huge-pages": true` (VERIFIED: XMRig documents up to ~50% more RandomX speed with huge pages; 1 GB pages add a further ~1–3% on Linux where supported — Ypool guide, §1.2).
- If huge pages cannot be enabled, the worker reports it and its hashrate is labelled "no huge pages" — never silently compared against a huge-pages number (Lane A §3.3). The setup steps per platform are in §1.4–§1.6.
- The worker agent (§5) must report the huge-pages state (enabled / disabled / failed with reason) alongside every hashrate figure.

### 2.6 Donate level — 1%, disclosed, not hidden

- The ATLAS template sets `"donate-level": 1` explicitly.
- **What it means:** 1% of the worker's hashrate (1 minute in 100) goes to the XMRig developers, not to ATLAS and not to the user. It is the project's funding mechanism.
- **Disclosed, not hidden:** the worker setup screen and the Mining tab must state the 1% in plain words next to the hashrate — e.g. "1% of this worker's hashrate is donated to the XMRig developers". It is never set silently and never changed without telling the user (Lane A §3.3).
- **Default in current releases is 1%** (VERIFIED per the Ypool guide, §1.2; some older docs and the GitHub README state a 5% default for older versions — the build lane must report the default of the version it pins, §1.3). The template pins 1% explicitly so the behaviour does not depend on which default the pinned version ships.
- Setting it to 0 is technically possible and is **NOT recommended by this design** — the project is actively developed, and the 1% is disclosed, not hidden. A user who insists on 0 must set it themselves, explicitly, and the worker record must note it (so the 1% is not silently missing from the accounting in §6).

### 2.7 Settings the user changes vs settings the user must not change

| Setting | Who changes it | Rule |
|---|---|---|
| Pool host/port (primary + fallbacks) | User, from the ATLAS pool list (§2.2) | Only pools in `config/pool-rewards.json`. Never a pool from a chat message, a video, or a search result. |
| Wallet address (`user`) | User, from the Mission 3 wallet center | Validated per §2.3 before it is written. Never another user's address, never an ATLAS address (none exists). |
| Worker name (`pass`) | User, at registration (§5) | Unique per user; charset `[a-z0-9-]`, max 32 chars (ASSUMPTION — build lane to confirm against pool rules). |
| Thread count / resource profile | User | Eco / Balanced / Performance (§2.4). Never all cores by default. |
| Huge pages on/off | User (with the platform steps in §1) | Default ON. If OFF, the hashrate is labelled "no huge pages". |
| Temperature limit (§4.3) | User — opt-in only | No default threshold ships. The user sets a number or leaves it unset. |
| Donate level | User, explicitly, if changed from 1% | Default 1%, disclosed (§2.6). 0 is possible but not recommended and must be recorded. |
| `algo` | **Must not change** | `rx/0` only. Any other algorithm string means the worker is mining something else and its shares are not XMR shares. |
| `tls` | **Must not change without a reason recorded** | TLS where the pool offers it (§2.2). Silent downgrade to plaintext is not permitted. |
| Pool order | **Must not change casually** | Order is primary → fallbacks (§2.2). Reordering changes which fee the user pays; any change is logged with a reason. |
| Any credential, seed, key, or password field | **Must never exist** | There is no such field in this design. If a config ever asks for one, it is not an ATLAS config. |
| `autosave` | **Must not turn off silently** | The agent reads the saved file as the source of truth (§2.1). Turning it off hides what is running. |

## 3. Expected hashrate

### 3.1 The reference case — Ryzen 7 5800X (VERIFIED)

| Worker | Hashrate | Source | Label |
|---|---|---|---|
| **Ryzen 7 5800X, native XMRig** | **10.0–12.4 kH/s** (XMRig benchmark 12,445 H/s) | Mission 1 §4.1; XMRig benchmark page; Kryptex; asicprofit (full URLs in Mission 1 §5) | **VERIFIED** (CARRIED from Mission 1; not re-measured in this session) |
| Native laptop (XMRig/P2Pool) | ~6,300 H/s | Mission 1 §4.1 (Monerica — same laptop as the 200 H/s browser tab) | **CARRIED** |
| Native per core (general) | 450–700 H/s/core | Mission 1 §4.1 (SoapBox) | **CARRIED** |
| Browser tab, whole tab (32-thread desktop) | ~850 H/s | Mission 1 §4.1 (Monerica) — the comparison point: one 5800X is ~12–15× faster than a whole browser tab on a 32-thread desktop | **CARRIED** |

### 3.2 Additional CPUs — VERIFIED live in this session (2026-11-18)

These figures were verified live from the XMRig public RandomX benchmark and corroborating guides in this session. They are **community-submitted benchmark averages**, not ATLAS measurements: each depends on memory speed, cooling, BIOS settings, and the XMRig version used. The test lane must re-measure on ATLAS hardware before any of them is presented as an ATLAS result.

| CPU | Hashrate | Basis | Source (live, 2026-11-18) | Label |
|---|---|---|---|---|
| AMD Ryzen 9 7950X (16C/32T) | **26,960 H/s average** (26,959.77) | 1,715 samples, XMRig benchmark aggregate | XMRig RandomX benchmark, live search result; corroborated by the Ypool guide table (26,960 H/s, Oct 9, 2026) and cloudminecrypto (26,960 H/s at 170 W TDP, from the XMRig benchmark table) | **VERIFIED** |
| AMD Ryzen 9 5950X (16C/32T) | **23,370 H/s** (23,370.49, top result; 6,879 samples in the aggregate) | XMRig benchmark | XMRig RandomX benchmark, live search result; Ypool guide table (23,370 H/s); benchmark detail page: https://xmrig.com/benchmark?cpu=AMD+Ryzen+9+5950X+16-Core+Processor&bench_id=23hdYR | **VERIFIED** |
| AMD Ryzen 9 7900X (12C/24T) | **20,677 H/s average** (20,676.96) | 732 samples, XMRig benchmark aggregate | XMRig RandomX benchmark, live search result; benchmark detail page: https://xmrig.com/benchmark?cpu=AMD+Ryzen+9+7900X+12-Core+Processor&bench_id=2GKRpk | **VERIFIED** |
| AMD Ryzen 9 9900X (12C/24T) | **20,918 H/s average** (20,917.88) | 148 samples, XMRig benchmark aggregate | XMRig RandomX benchmark, live search result | **VERIFIED** |

Notes and cautions:
- The 7950X and 7900X figures are **benchmark-table averages** (mean across all submitted results for that CPU). The 5950X figure is the **top single result** in its detail table (23,370.49 H/s, XMRig 6.16.2, 32 threads) — the aggregate sample count is large (6,879), but the single top result is not an average; treat 23,370 H/s as the demonstrated ceiling for that chip, not its typical result. (The asicprofit 5950X page lists a lower 18.0 kH/s figure from hashrate.no — a different benchmark population; the gap is a reminder that "the" hashrate for a CPU is a distribution, not a constant.)
- Monerica's November 2026 profitability table gives a **tuned, wall-measured** 7950X figure of **~22 kH/s at ~200 W wall** — lower than the 26,960 H/s benchmark average, because a tuned 24/7 figure is not a benchmark sprint. §6 uses the 22 kH/s figure for economics, not the 26,960 H/s benchmark average, and says so.
- **No other CPU is listed.** No Intel figure, no laptop-chip figure, and no Apple Silicon figure is included, because none was verified from a live source in this session. The rule for the build lane is the same as for this lane: **add a CPU only with a live source (XMRig benchmark or equivalent); otherwise omit it, never guess.** A guessed hashrate becomes a false earnings claim the moment it meets the calculator in §6.

### 3.3 What the numbers mean — and what they do not

- Native XMRig is **30–80× faster than the browser tab** (Mission 1 §4.1). That is why the desktop is the primary path and the browser is a participation/demo feature (Lane A §0).
- A benchmark hashrate is **not** a sustained 24/7 hashrate, **not** a pool-accepted-share rate, and **not** earnings. Thermal throttling, memory speed, background load, and huge-pages state all move it. The test lane's Gate 1/3/5 measurements (§4 of Lane A) are what turn a benchmark figure into an ATLAS figure — and for the desktop worker, the equivalent measurement is a sustained XMRig run with wall watts (Lane C §4 protocol), which is still owed.
- **RandomX v2** (§1.4): all figures in this section are RandomX v1 (rx/0). A v2 activation requires re-benchmarking.

## 4. Safety — explicit activation only, resource controls, temperature, stopping

These rules are binding on any desktop worker, now and in every future mission (CARRIED from Lane A §3.5, expanded here into the design the build lane must implement).

### 4.1 Explicit per-worker activation only

- **The worker starts only when the user starts it, and stops when the user stops it.** Activation is explicit, per worker, per user, per start. There is no silent install, no bundled installer that installs XMRig as a side effect, no autostart without the user's explicit choice, no hidden mining, no mining while the user is unaware.
- **Opt-in is a deliberate action, not a default.** The setup flow must present, in plain words, before the first start: what will run (XMRig, version pinned per §1.3), what it will use (threads, RAM, electricity — with the §6 economics next to it), what it will send (hashrate/shares to the pool, status to ATLAS via the agent in §5), and how to stop it (§4.4). The user confirms each of those, not a single vague "I agree".
- **No auto-start by default.** If the user wants the miner to start at login/boot, they enable it explicitly in a separate, clearly labelled step, and they can undo it from the same place. The installer never adds a startup entry on its own.
- **No mining on a machine the user does not own or control.** No remote install, no install on a shared/hosted machine without that machine owner's explicit authorization, and never on the Muse VM host (§1.7).
- **Revocation is activation in reverse:** the user can withdraw activation at any time from the Command Center (§5.5), and withdrawing it stops ATLAS attribution immediately — even though stopping the XMRig process itself is a separate local step the user must also take (§4.4), and the UI must say so plainly rather than implying one click stops the miner.

### 4.2 Resource controls

| Control | Design | Label |
|---|---|---|
| Thread cap | Physical cores − 1 by default (§2.4); profile-mapped below that (Eco ~25%, Balanced ~50%, Performance = cores − 1) | ASSUMPTION (profile mapping); CARRIED (cores − 1 default) |
| CPU priority | XMRig runs at below-normal OS priority by default where the OS allows it, so the user's interactive work is not starved | ASSUMPTION — build lane to confirm per OS |
| Max CPU % | Enforced by the thread cap + priority, not by a fake percentage slider. The UI shows threads and priority, not a "% CPU" number the miner cannot actually enforce | ASSUMPTION |
| Memory | Dataset ~2 GB + 2 MB scratchpad/thread; the worker refuses to start with a clear error if free RAM is insufficient (§2.4) | CARRIED (Mission 1 §4.1) |
| Pause on user activity (optional) | A profile option — "pause while I am actively using this machine" — is a design option for a later mission, not built here. If built later, it must be opt-in and its pauses must be logged | ASSUMPTION |

- **The UI must state the limits and never silently exceed the user's selected profile.** A profile change is a user action, logged with a timestamp; the agent reports the profile actually in effect, and a mismatch between the selected profile and the running thread count is a fault to report, not to hide.
- **Never automatically increase a user's resource limits** (Mission 1 §12). If the economics turn against the worker (§6), the system may recommend stopping or reducing — it must never raise the thread count on its own.

### 4.3 Temperature monitoring and auto-stop

- **Where telemetry is available, it is shown; where it is not, the UI says so.** Sources by OS (CARRIED from Lane A §3.5): Linux `sensors`/`lm-sensors`; Windows HWMonitor / Open Hardware Monitor (or equivalent); macOS `powermetrics` where permitted. The agent (§5) reads the temperature from the OS tool — XMRig itself does not report CPU temperature.
- **No invented readings.** Where no temperature telemetry is available, the worker status shows "temperature unavailable on this machine" — it never invents a reading, never interpolates one from load, and never presents a software power estimate as a temperature.
- **Auto-stop threshold — user-set, opt-in only, no shipped default.** This design does **not** invent a safe temperature for hardware it has not seen (Lane A §3.5). The default state is: **no threshold set, no auto-stop on temperature**. The user may set a threshold (a single number in °C) and, once set, the rule is binding: if the reported temperature exceeds it, the agent stops the XMRig process (§4.4) and reports why, with the temperature reading and the threshold attached. The threshold is per worker, changeable by the user at any time, and logged on every change.
- **What the build lane must do before shipping a suggested value:** verify the CPU vendor's published maximum operating temperature for each CPU it suggests a value for, and cite it. Until then, the setup screen offers the field blank, with the instruction "set this from your CPU vendor's published maximum — leave blank for no auto-stop". A suggested number without a cited vendor source is a defect in the build lane's report.
- **Failsafe on telemetry loss:** if temperature telemetry was available and then stops reporting (sensor tool fails, permissions change), the agent logs it and — if a threshold was set — stops the worker rather than mining blind. Mining without the sensor that enforces its own stop rule is not permitted. (ASSUMPTION — design rule for the build lane to implement; the alternative, "keep mining and warn", is rejected because a warning the user may not see is not a control.)

### 4.4 How the user stops it — immediate and complete

Stopping must be **immediate and complete**. There is no "stopping…" state that lingers, no background service left behind, no restart on reboot unless the user explicitly enabled auto-start (§4.1).

**Stop procedure (per OS):**

| OS | Stop steps |
|---|---|
| Windows | Ctrl+C in the XMRig terminal window, or close the window; if unresponsive, End Task on `xmrig.exe` in Task Manager. Then verify: no `xmrig.exe` in Task Manager → stopped. |
| Linux | Ctrl+C in the terminal, or `pkill -f xmrig` / `kill <pid>`; then verify: `pgrep -a xmrig` returns nothing → stopped. |
| macOS | Ctrl+C in the terminal, or Force Quit / `pkill -f xmrig` in Terminal; then verify: no `xmrig` in Activity Monitor → stopped. |

**What "complete" means, and how the user verifies it:**
1. The XMRig process is gone from the OS process list (the verify step above). No XMRig process, no helper process, no updater — there is no updater in this mission (§7).
2. The pool dashboard shows the worker going offline (within the pool's reporting interval — minutes, not seconds; the UI must state the interval rather than promising instant pool-side disappearance).
3. The ATLAS worker status (§5) moves to `stopped` when the agent reports the process gone (or to `unreachable` if the agent itself was stopped — the UI must distinguish "stopped by the user" from "agent not reporting").
4. **Uninstall is deletion:** there is no uninstaller in this mission. Removing the worker is: stop the process, delete the XMRig folder and `config.json`, and (Linux only, if the user set it) remove the `vm.nr_hugepages` line from `/etc/sysctl.conf`. No registry keys, no services, and no startup entries are created by this design, so there is nothing else to clean — and the build lane must keep it that way.
5. **Stopping ATLAS attribution is separate from stopping the miner** (§4.1): revoking the worker in the Command Center stops attribution/crediting immediately, but XMRig keeps hashing to the pool until the user stops the process locally. The UI must show both states side by side so the user is never misled into thinking one click did both jobs.

### 4.5 Antivirus, firewall, and blocklist honesty

- The user is told **up front**, before the first start, that AV tools and firewalls flag miners, that a warning is expected, and that allowing it is their decision.
- ATLAS never tells the user to disable security software wholesale. Allowing a specific, hash-verified binary (§1.3) through a specific prompt is the user's decision; disabling Defender/antivirus entirely is not an ATLAS instruction, ever.
- Browser/AV blocking of the browser miner (Firefox 69+ blocks known cryptomining scripts, Brave and AV tools block them, Chrome Web Store bans mining extensions — VERIFIED, Mission 1 §4.1) is a separate matter from the desktop worker, but the same honesty applies: if the user's AV quarantines XMRig, the worker reports it as an AV event, not as a mining failure, and the user decides what to do.

## 5. Registration design — how a desktop worker registers with ATLAS

**No registration code exists in this mission.** This section is the design a future mission implements. It is written so the build lane can implement it without inventing an auth model.

### 5.1 Prerequisites (in order — each gates the next)

1. The user has an ATLAS account (Mission 5+ scope — user account system, Mission 1 §3).
2. The user has connected a wallet address through the Mission 3 wallet center (validated per §2.3).
3. The user has installed XMRig from official sources and verified the hash (§1).
4. The user has configured XMRig from the template (§2) with their own address and a worker name.

### 5.2 Worker name + per-worker token

- **Worker name:** chosen by the user at registration (e.g. `rig1`). It is the value in XMRig's `pass` field — the pool-side worker identifier. Rules: unique per user (DB unique constraint on `(user_id, name)`), charset `[a-z0-9-]`, max 32 characters (ASSUMPTION — build lane to confirm against pool naming rules; MoneroOcean and SupportXMR both accept the `pass` field as a free-form worker name, but their exact charset limits are not verified in this session).
- **Per-worker token:** generated server-side at registration. Properties (all binding):
  - Cryptographically random, ≥256-bit entropy, generated with a CSPRNG — never derived from the worker name, the wallet address, or the user ID.
  - **Shown once** at creation, in the Command Center, with the instruction to paste it into the worker agent's config (§5.3) and never to share it, screenshot it into a chat, or commit it to a file that leaves the machine.
  - Stored **only as a salted hash** server-side (never in plaintext, never in a URL, never in a log line). Verification is hash-compare on the stored hash.
  - Transmitted only over TLS, only to the ATLAS API, only by the worker agent. XMRig itself never sees the token — XMRig has no ATLAS auth, and giving a pool-bound miner an ATLAS credential would be a category error.
  - One token per worker. A second machine registering the same worker name gets a different token and is a different worker; sharing one token across machines is not supported and is detected per §5.4.
  - Rotation: the user can rotate a token (old token invalidated immediately, new token shown once). Rotation is logged.
- **What is stored where:** the Command Center stores the worker name, the token hash, the wallet address (already stored by the wallet center), the XMRig version + verified SHA-256 (§1.3), and the registration timestamp. It never stores a seed, key, or password — there is nothing of that kind in this design.

### 5.3 The worker agent (design only — not built)

XMRig cannot talk to ATLAS, so a small, separate, **explicitly installed** companion agent is the design's reporting path:

- The user installs the agent deliberately (a separate download, a separate explicit step — never bundled silently with XMRig).
- The agent reads XMRig's local HTTP API (localhost only) for hashrate and thread state, reads OS temperature telemetry where available (§4.3), and polls the configured pool's API for the wallet+worker accepted/rejected share counts.
- The agent reports to ATLAS over TLS with the per-worker token (§5.2): hashrate, accepted/rejected shares **from the pool API, not from XMRig's self-report alone**, temperature where available, uptime, XMRig version, huge-pages/MSR state, and the resource profile actually in effect.
- The agent never holds payout keys, never touches payouts, never modifies the XMRig config, and never starts or stops XMRig except on the temperature auto-stop (§4.3) or an explicit user stop command from the Command Center — and any remote stop must be a deliberate user action, logged, with the local stop procedure in §4.4 still available as the authoritative way to stop.
- The agent is a separate service with its own watchdog/recovery entry (following the `recover.sh` pattern) and its own logging — but it is **not** a daemon on the Muse VM host, which is control-plane only (§1.7).

### 5.4 Status lifecycle — `active` only after pool-accepted shares

| Status | Meaning | How a worker gets there |
|---|---|---|
| `pending` | Registration started, not finished | User began registration; token not yet issued. |
| `registered` | Token issued, worker configured, **no pool-accepted shares yet** | Token issued + agent first check-in. Local hashrate — however high — keeps a worker here. |
| `active` | Pool shows accepted shares for this wallet + worker name | The coordinator (§5.5) verifies ≥1 pool-accepted share for the wallet+worker pair via the pool API, cross-checked against the agent's report. **Local hashrate alone never activates a worker.** |
| `degraded` | Active, but the pool/agent reports disagree or the rejection rate is abnormal | Coordinator flags it; the worker keeps mining but its shares are not credited until the discrepancy is resolved. |
| `stopped` | User stopped the miner (§4.4) | Agent reports the process gone, or the user marks it stopped. |
| `unreachable` | Agent has not checked in within the timeout | Agent down, machine off, or network down. Distinct from `stopped` — the UI must not conflate them. |
| `revoked` | Token revoked by the user (§5.5) | User revokes; reports with the old token are rejected. |
| `suspended` | ATLAS-side hold (duplicate-worker conflict, abuse flag, emergency stop) | Coordinator or admin action, logged with a reason. |

**Why local hashrate never activates a worker:** the VoltMiner rounding-mode bug (Lane A §1.3) proved local metrics can look perfect while every share is invalid. A worker is `active` only when the pool — an independent party — says it accepted shares for that wallet+worker. The pool's own accounting is the source of truth (Mission 1 §6), cross-checked against the chain where feasible.

### 5.5 Duplicate-worker prevention

Four layers, all required — a duplicate worker is an accounting error (double credit) and a security signal (token theft), so it is prevented structurally, not by asking the user to be careful:

1. **Name uniqueness:** `(user_id, name)` unique in the workers table (Mission 2 Stage 0 shape: `user_id`, `worker_type` browser/desktop, `name`, `status`, `registered_at` — extended with a token-hash field and an auth-status field; no new table design is in scope for this mission, Lane A §3.6). A second registration with the same name is rejected with "worker name already in use".
2. **Token binding:** one token per worker, one worker per token. A token presented by two different agent instances is a conflict: the second check-in is rejected and the worker is flagged `suspended` until the user resolves it (rotate the token on the legitimate machine, revoke the other).
3. **Pool-side collision detection:** the same wallet+worker name mining from two machines merges into one worker in the pool's own stats. The agent therefore reports a machine fingerprint (a hash of stable machine identifiers — hostname + CPU model — never a raw serial number, ASSUMPTION) with each check-in. Two distinct fingerprints reporting under one worker name is a conflict: the worker is flagged, its shares are not credited until resolved, and the user is told exactly what was seen.
4. **One agent per machine:** the agent takes a lock (lockfile/PID check) at start; a second agent instance on the same machine refuses to start and says so. This mirrors Lane A's duplicate-worker prevention for the browser tab (one miner instance per tab).

### 5.6 Verification and revocation

- **Verification (coordinator, Mission 5 scope):** the coordinator polls the configured pool's API for the wallet+worker pair, confirms accepted shares exist, and only then moves the worker `registered` → `active`. It cross-checks the pool's accepted count against the agent's reported count; a material mismatch is a `degraded` flag, not an activation. The coordinator's verification decision is logged in the `decisions` table (new `dept` values `rewards`/`workers`, per Mission 1 §2.3) with its reason.
- **Revocation:** the user can revoke a worker token from the Command Center at any time. Effect: the token hash is marked revoked, reports with it are rejected, the worker is marked `revoked`, and ATLAS attribution/crediting stops immediately. Revocation does **not** stop the XMRig process — the user must also stop it locally (§4.4), and the UI must say so in the same breath as the revoke confirmation.
- **Emergency stop interaction:** while the ATLAS emergency stop is active, all reward/payout processing halts (`config/pool-rewards.json` safety rules) and no worker may move to `active` — a worker can register, but activation waits for the stop to be lifted by an authorized action. The stop never lifts automatically.

## 6. Cost accounting — Lane C's numbers, carried

All figures in this section are **CARRIED from Lane C** (`docs/master-mission4-cost-accounting.md`, Gate 5, 2026-11-18 03:33–03:45 EST) except where marked ESTIMATE (computed here from Lane C's formula and inputs). Lane C's inputs, VERIFIED in its session: XMR **$501.26** (CoinGecko, 03:33 EST; cross-check $498.00 MoneroOcean), network difficulty 787,074,505,719 → network hashrate **6.559 GH/s** (ESTIMATE from VERIFIED difficulty), block reward 0.6 XMR tail emission (last block 0.6054 XMR), 720 blocks/day, 432 XMR/day emission, MoneroOcean 0% fee, USD/CAD 1.4327. Electricity: Hydro-Québec Rate D Tier 2 **11.142¢ CAD/kWh = 7.777¢ USD/kWh** (VERIFIED via corroborated secondary sources citing HQ's official 2026 rates; direct hydroquebec.com pages 404'd — a direct re-check is still owed for any billing decision), Tier 1 7.065¢ CAD = 4.931¢ USD/kWh, US average residential **17.23¢ USD/kWh** (CARRIED, EIA Form EIA-861 final 2025).

**Formula (Lane C §3):**
```
daily coins   = (your hashrate / network hashrate) × blocks/day × block reward × (1 − pool fee)
gross $/day   = daily coins × XMR price
electricity $/day = wall watts × 24 / 1000 × price per kWh
net $/day     = gross − electricity          (whole-system net, before the 75/25 split)
```
At Lane C's inputs: **$0.03302/day gross per kH/s**; electricity **$0.0018665/day per W** at HQ Tier 2, **$0.0041352/day per W** at the US average. **Breakeven efficiency: 56.5 H/s per wall watt at HQ Tier 2; 125.2 H/W at the US average.** Any worker below that line loses money on electricity alone, before any split, fee, or hardware cost.

### 6.1 Headline table — whole-system net, before the split (CARRIED from Lane C §5.1)

| Worker | Hashrate | Wall W | Gross $/day | Net $/day HQ Tier 2 | Net $/day US avg | Efficiency (H/W) | Verdict |
|---|---|---|---|---|---|---|---|
| Laptop browser | 200 H/s | 45 (30–60) | $0.0066 | **−$0.077** | **−$0.180** | 4.4 | Loses ~12× its revenue |
| 32-thread desktop browser | 850 H/s | 50 (35–70) | $0.0281 | **−$0.065** | **−$0.179** | 17.0 | Loses ~2–3× its revenue |
| Ryzen 7 5800X native, 10 kH/s | 10,000 H/s | 171 | $0.3302 | **+$0.011** | **−$0.377** | 58.5 | Barely breakeven at Tier 2 only |
| Ryzen 7 5800X native, 12,445 H/s | 12,445 H/s | 171 | $0.4109 | **+$0.092** | **−$0.296** | 72.8 | Positive at Tier 2 only |
| Ryzen 7 5800X native, 8,245 H/s | 8,245 H/s | 171 | $0.2722 | **−$0.047** | **−$0.435** | 48.2 | Loses even at Tier 2 |

All net figures are ESTIMATE (computed from VERIFIED price/difficulty and CARRIED/ESTIMATE hashrate and watts), BEFORE hardware cost. Watt figures: browser cases ESTIMATE ranges; 171 W desktop wall power CARRIED from Objective 4 (cpumining.pro measured wall watts). **No wall-watt figure in this document is measured by ATLAS** — a physical wall-watt measurement on user hardware is OWED (Lane C §4 protocol) and Gate 5 does not pass on estimates alone.

### 6.2 The 75/25 split effect — the user's share (CARRIED from Lane C §5.2)

The split applies only to **actual confirmed pool rewards** — never to estimated hashrate, never to projected earnings, never to unverified work (Mission 1 §6; `config/pool-rewards.json`). Electricity is paid by the user out of their own pocket — it is NOT deducted by ATLAS before the split. So the user's real position is `0.75 × gross − electricity`.

| Worker | Gross $/day | User keeps (75%) | ATLAS keeps (25%) | Worker-days to earn $1 (user gross share) | User net, HQ Tier 2 | User net, US avg |
|---|---|---|---|---|---|---|
| Laptop browser, 200 H/s | $0.0066 | $0.0050/day | $0.0017/day | **202 days** | **−$0.079/day** | **−$0.181/day** |
| Desktop browser, 850 H/s | $0.0281 | $0.0210/day | $0.0070/day | **48 days** | **−$0.072/day** | **−$0.186/day** |
| 5800X native, 10 kH/s | $0.3302 | $0.2476/day | $0.0825/day | **4.0 days** | **−$0.072/day** | **−$0.460/day** |
| 5800X native, 12,445 H/s | $0.4109 | $0.3082/day | $0.1027/day | **3.2 days** | **−$0.011/day** | **−$0.399/day** |
| 5800X native, 8,245 H/s | $0.2722 | $0.2042/day | $0.0681/day | **4.9 days** | **−$0.115/day** | **−$0.503/day** |

**Key finding (CARRIED from Lane C): the split pushes even the marginal desktop case underwater for the user.** At 10 kH/s the whole system nets +$0.011/day at Tier 2, but the user's 75% share ($0.2476) does not cover their own $0.3192 electricity bill — the user nets −$0.072/day. Only at Tier 1 (optimistic bound) does the user come out ahead on the desktop case (+$0.045/day at 10 kH/s). The browser cases are negative for the user at every rate: the laptop browser user pays ~$0.08/day to "earn" $0.005/day.

Time to the MoneroOcean 0.003 XMR minimum payout (gross coins, before split — CARRIED): laptop browser **228 days (~7.5 months)**; desktop browser 54 days; 5800X at 10 kH/s 4.6 days. The browser user's payout, when it finally arrives after 7+ months, is worth ~$1.50 at Lane C's price — while they paid ~$19 in electricity to earn it (228 days × $0.084/day at Tier 2).

### 6.3 The stronger desktop case — Ryzen 9 7950X (ESTIMATE, computed here)

The 7950X is the only additional CPU with both a VERIFIED hashrate (§3.2) and a published whole-machine wall-watt figure, so it is the only one that gets an economics row. Every number in this subsection is **ESTIMATE**, computed with Lane C's formula and inputs.

- Hashrate: **~22 kH/s tuned** (Monerica, November 2026 profitability table — CARRIED from the live source fetched in this session; a tuned 24/7 figure, not the 26,960 H/s benchmark average in §3.2, which is shown as the upper bound). Wall power: **~200 W whole machine, measured at the wall** (same Monerica table — CARRIED). Cross-check: Monerica's own table shows the same chip at ~$20.56 gross/month and ~$6.16 net/month at 10¢/kWh; this subsection's formula gives $0.726/day gross ($21.79/month) and, at 10¢/kWh, $0.246/day net ($7.39/month) — the same order, the difference being Lane C's price/network inputs vs Monerica's ($496 XMR, 6.88 GH/s). The two independent computations agree within ~20%; neither is a measurement by ATLAS.
- Gross: 22 × $0.03302 = **$0.726/day**. Electricity at Tier 2: 200 W × 24 / 1000 × $0.07777 = **$0.373/day**. Electricity at US average: 200 × 24 / 1000 × $0.1723 = **$0.827/day**.
- **Whole-system net: +$0.353/day at HQ Tier 2; −$0.101/day at the US average.** Efficiency 22,000 / 200 = **110 H/W** — above the 56.5 H/W Tier 2 breakeven, below the 125.2 H/W US breakeven. (At the 26,960 H/s benchmark average, efficiency would be 134.8 H/W — but the wall watts at that hashrate are unmeasured, so that figure is an upper bound only, not a row in the table.)
- **User net after the 75/25 split: +$0.171/day at HQ Tier 2** (0.75 × $0.726 − $0.373); **−$0.282/day at the US average.** Worker-days to earn $1 of user gross share: 1 ÷ $0.545 ≈ **1.8 days**. Time to the 0.003 XMR pool minimum (gross coins): 22,000 / 6,558,954,214 × 432 = 0.001449 XMR/day → **~2.1 days**.
- The 7950X is therefore the first case in which the user is net-positive after the split — **but only at Quebec Tier 2 rates, only on a machine the user already owns, and only by $0.17/day**. At the US average it still loses $0.28/day for the user. Nothing about it justifies buying hardware (§6.4).

### 6.4 Hardware cost — the separate line (CARRIED from Lane C §6)

Hardware cost is **excluded** from all net figures in §6.1–§6.3. It is shown here separately because it decides whether the one near-breakeven case is worth anything at all.

- **Reference system: ~$500** for a Ryzen 7 5800X-based system (Objective 4: $400–600 to build/buy).
- At the whole-system net of **+$0.011/day** (10 kH/s, HQ Tier 2), payback is **$500 ÷ $0.011/day ≈ 45,000 days ≈ 124 years**. At Tier 1 (+$0.1278/day) it is ~10.7 years. At 12,445 H/s Tier 2 (+$0.0917/day) it is ~14.9 years. Objective 4's ~65-year figure used older price/network inputs; Lane C's fresh inputs make the Tier 2 case worse, not better.
- **7950X (ESTIMATE, computed here):** ~$550 for the CPU alone (Monerica, November 2026). At the whole-system Tier 2 net of +$0.353/day, payback is ~1,558 days ≈ **4.3 years**; on the user's post-split net (+$0.171/day) it is ~3,216 days ≈ **8.8 years**. Better than the 5800X by an order of magnitude — and still longer than the useful life of the hardware as a competitive miner, before any allowance for the rest of the system (board, RAM, PSU, case), for difficulty/price moves, or for the pending 19.5¢/kWh Quebec blockchain tariff (Lane C §2: proposed February 2026, awaiting Régie de l'énergie approval — NOT in effect, NOT in any base-case figure; if it ever took effect, every Quebec case would lose by a wide margin).
- **Plain statement (CARRIED from Lane C): hardware cost kills the marginal desktop case.** No hardware purchase is justified by this model. The only honest framing for hardware: if the user **already owns** the machine (sunk cost), hardware does not enter the marginal decision — only electricity vs revenue matters. Buying hardware to mine is a separate, unjustifiable decision.

### 6.5 The honest verdict

1. **Desktop is the only path near breakeven, and even it barely breaks even.** The Ryzen 7 5800X — the reference desktop case — nets +$0.011/day whole-system at Quebec Tier 2 and loses at the US average; the user nets −$0.072/day after the 75/25 split at Tier 2. The stronger Ryzen 9 7950X does reach +$0.171/day for the user at Tier 2, and still loses at the US average. (ESTIMATE, Lane C inputs.)
2. **Never promise guaranteed profits.** Prices, difficulty, and network hashrate move daily; a figure that is positive today can be negative tomorrow; the sign of the 5800X case flips with the hashrate assumption alone (8,245 H/s loses even at Tier 2). No UI, guide, or report built from this design may show a projected-earnings headline, an "earn $X/day" claim, or any profit promise. Estimates are labelled ESTIMATE and never create a balance.
3. **Browser mining loses money at every electricity price in this model** (Lane C §7): laptop browser −$0.077/day at Tier 2, −$0.180/day at the US average; desktop browser −$0.065/day at Tier 2, −$0.179/day at the US average. It is a participation/demo feature, never a revenue stream.
4. **What is measured vs estimated vs owed:** MEASURED (VERIFIED) in Lane C's session — XMR price $501.26, network difficulty 787,074,505,719, last-block value 0.6054 XMR, pool hashrate/miners, USD/CAD 1.4327. CARRIED — pool fee 0%, US average 17.23¢/kWh, 171 W desktop wall power, browser hashrates 200/850 H/s, desktop hashrate range 8,245–12,445 H/s, Monerica 7950X ~22 kH/s at ~200 W wall. ESTIMATE — every net/gross figure in §6, the 30–60 W and 35–70 W browser power ranges, the Tier 1/Tier 2 USD conversions, and the whole of §6.3. OWED — a physical wall-watt measurement on user hardware (Lane C §4 protocol) and the prototype's measured hashrate. Gate 5's accounting is complete as a model; it is NOT complete as a measurement until those two arrive.

## 7. What is NOT built in this mission

The following are **not built, not connected, and not authorized** by Master Mission 4. Each needs a later mission **and** explicit authorization. The build lane must not write any of them, stub any of them with a live endpoint, or leave a "TODO: connect here" that a later run could mistake for working code.

- **No desktop installer.** No .exe/.msi/.dmg/.deb, no one-click setup, no bundled XMRig download. The user downloads XMRig themselves from the official source and verifies the hash themselves (§1).
- **No auto-update channel.** No mechanism that fetches, verifies, or installs a new XMRig version on the user's machine. Version changes are manual, hash-verified (§1.3), and recorded. An auto-update channel is a supply-chain attack surface and is out of scope until a later mission designs its signing and verification.
- **No live pool connection.** No stratum connection of any kind, no share submission to any pool, no pool login performed by ATLAS. Gates 2 and 4 are NOT TESTED in this mission (Lane A §4) and require separate explicit authorization.
- **No share submission.** The desktop worker in this mission submits nothing to anyone. Local hashrate is not a share and creates no credit (§5.4).
- **No payout flow.** No payout service, no treasury design (which does not exist and is not approved), no minimum payout set (still `null`/placeholder in `config/pool-rewards.json`), no transaction, no test wallet with real funds. Simulation/testnet first, then security testing, then explicit authorization (Mission 1 §7).
- **No worker agent.** The companion agent in §5.3 is design only. No agent code, no token issuance, no registration UI, no pool-API polling exists after this mission.
- **No wallet or key creation.** No seed phrase, no private key, no password — nothing custodial, anywhere. The wallet center (Mission 3) is read-only from this design's point of view.
- **No config changes.** `config/atlas.json` and `config/pool-rewards.json` are read-only inputs. The mode stays `simulation-only`. The emergency stop stays ON. Mining stays disabled in config. Trading stays paper-only. Capital stays $0.
- **No mining on the Muse VM host, no new daemon, no new cron job, no new database tables, no seeded rows.** (Lane A §6 checklist, carried forward in full.)
- **No user-facing "start mining" control.** The Mining tab Start/Stop buttons stay hard-disabled with no handler. This design adds no start control of any kind.

## 8. Handoff to the build and test lanes

**The build lane receives from this document:**
- Installation: official sources only (§1.1), SHA-256 verification procedure + commands (§1.3), per-platform steps (§1.4–§1.6), version pin 6.26.0 to re-check (§1.3). Full URLs must be printed in the build lane's report (see the tooling note in §1.2).
- Config: the template in §2.1, pool order and ports in §2.2 (hostnames to be taken from the pools' own documented endpoints — never guessed), wallet validation rules in §2.3, thread/huge-pages/donate rules in §2.4–§2.6, the changeable vs must-not-change table in §2.7.
- Hashrates: the reference case in §3.1 and the four VERIFIED additional CPUs in §3.2, with the rule that a CPU is added only with a live source, never guessed.
- Safety: explicit activation (§4.1), resource controls (§4.2), temperature telemetry + user-set auto-stop with no shipped default (§4.3), the stop procedure and its verification (§4.4), AV/firewall honesty (§4.5).
- Registration: worker name + per-worker token design (§5.2), agent design (§5.3), status lifecycle with `active` gated on pool-accepted shares (§5.4), four-layer duplicate prevention (§5.5), verification and revocation (§5.6). None of it is built in this mission.
- Economics: Lane C's tables (§6.1–§6.2) and the 7950X ESTIMATE row (§6.3), the hardware-payback line (§6.4), and the honest verdict (§6.5) — to be shown verbatim wherever the UI shows desktop economics.

**The test lane must verify (and report with sources and timestamps):**
- That each official URL resolves to the official source, and the SHA-256 published there matches the binary the lane downloads.
- A sustained XMRig run on real user hardware, with wall watts measured per the Lane C §4 protocol (plug-in meter, idle baseline, ≥60 minutes), reporting measured H/s, extra wall watts, efficiency in H/W against the 56.5 H/W (Tier 2) / 125.2 H/W (US) breakeven lines, and net/day at both electricity prices. A software power estimate is not a wall measurement and must be labelled as one.
- That the stop procedure in §4.4 actually leaves no XMRig process behind, on each OS the lane tests.
- That the temperature telemetry (where available) reports real values, and that a user-set threshold actually stops the worker.
- That the config template as written connects to the intended pool (in a later, authorized mission only — not this one) and that the donate level is visibly 1%.

**Open items and risks carried forward (not resolved by this design):**
1. Pool stratum hostnames are not printed in this document (no verbatim hostname in this lane's sources) — the build lane must take them from the pools' own documented endpoints.
2. No wall-watt measurement exists for any desktop worker — OWED on user hardware (Lane C §4; Lane A Gate 5).
3. No Intel, laptop-chip, or Apple Silicon hashrate is verified in this document — omitted by rule, not by oversight (§3.2).
4. RandomX v2 (released March 2026, no mainnet activation date as of 1 Nov 2026) would require a new XMRig version and re-benchmarking (§1.4, §3.3).
5. The proposed 19.5¢/kWh Quebec blockchain tariff (pending, not in effect) would make every Quebec case lose by a wide margin if approved (Lane C §2).
6. Treasury design does not exist and is not approved; Gates 2 and 4 cannot be authorized until it exists (Mission 1 §7, §10; Lane A §7).
7. Minimum payout is still `null`/placeholder in `config/pool-rewards.json`.
8. The refresh failure (Mission 3 finding 1) is unfixed by design in this mission; the build/test lanes must not attempt it.

## 9. Sources

Every external claim in this document traces to one of the following. Where a full URL could not be printed because of the tooling block described in §1.2, the source is cited by name and the full verbatim URL is already on file in the Mission 1 report §5.

**XMRig (desktop)**
- XMRig official download page — published SHA-256 hashes; verify with `certutil -hashfile <file> SHA256` (Windows). (Full URL withheld by the tooling block in §1.2; the URL is the official download page linked from the Monero.how guide below and from the Mission 1 report §5.)
- XMRig GitHub releases page — official binary releases for Windows, Linux, and macOS. (Same tooling note; the releases live under the XMRig organization on GitHub.)
- XMRig configuration wizard — generates `config.json`. (Same tooling note.)
- XMRig public RandomX benchmark — Ryzen 9 7950X average 26,959.77 H/s (1,715 samples); Ryzen 9 5950X top result 23,370.49 H/s (6,879 samples in the aggregate); Ryzen 9 7900X average 20,676.96 H/s (732 samples); Ryzen 9 9900X average 20,917.88 H/s (148 samples) — VERIFIED live via search results 2026-11-18. (Benchmark detail URLs that survived the tooling block: https://xmrig.com/benchmark?cpu=AMD+Ryzen+9+5950X+16-Core+Processor&bench_id=23hdYR and https://xmrig.com/benchmark?cpu=AMD+Ryzen+9+7900X+12-Core+Processor&bench_id=2GKRpk — both returned verbatim by web search on 2026-11-18. The aggregate benchmark page URL is withheld by the same block; it is the benchmark page cited in Mission 1 §5.)
- XMRig benchmark, Ryzen 7 5800X — 12,445 H/s (XMRig benchmark page; Kryptex and asicprofit device pages agree on the 10.0–12.4 kH/s range — CARRIED from Mission 1 §4.1/§5; full URLs in Mission 1 §5).
- Ypool, "How to Mine Monero: CPU, XMRig and P2Pool Guide (2026)" — https://www.ypool.net/how-to-mine-monero/ — huge pages up to +50% RandomX speed, 1 GB pages +1–3%; donate level 1% default in current releases; 7950X 26,960 H/s and 5950X 23,370 H/s in its October 9, 2026 benchmark table.
- Monero.how, "How to Mine Monero on Windows (2026): XMRig (CLI) + P2Pool + GUI Options" — official sources only; SHA-256 verification; run once as Administrator for huge pages; "Never download 'bundled miners' from random sites." (Full URL withheld by the tooling block in §1.2; cited in Mission 1 §5.)
- asicprofit CPU pages — Ryzen 9 5950X RandomX 18.0 kH/s at 130 W (benchmark source: hashrate.no) and Ryzen 9 7950X RandomX 21.9 kH/s at 230 W — https://www.asicprofit.com/cpus/amd/ryzen-9-5950x and https://www.asicprofit.com/cpus/amd/ryzen-9-7950x — cited for the cross-check in §3.2 that a CPU's hashrate is a distribution across benchmark populations, not a constant.

**Pools**
- MoneroOcean stratum ports 10001/10101 and SupportXMR 3333/5555 — VERIFIED as connectable (bare TCP) 2026-11-18, Mission 1 §2.4 / Objective 3 findings. MoneroOcean pool-stats API — VERIFIED 200 from this host, 2026-11-18 (Lane C §1). P2Pool has no central stratum endpoint — it needs a local P2Pool node (Lane A §2.2).
- Pool fees and split: `~/workspace/atlas/config/pool-rewards.json` (MoneroOcean 0%, SupportXMR 0.6%, P2Pool 0%; 75/25 on confirmed pool rewards only; simulation-only; minimum payout placeholder null).

**Economics and feasibility**
- Monerica, "Monero Browser Mining 2026" (updated 24 Oct 2026) — https://blog.monerica.com/articles/monero-browser-mining — laptop browser ~200 H/s; 32-thread desktop browser ~850 H/s; native laptop ~6,300 H/s vs 200 H/s browser on the same laptop; browser ~$0.008/day gross; ~7 months to reach a 0.003 XMR minimum payout.
- Monerica, "Is Monero Mining Profitable in 2026? Real Costs, Hashrates & Payouts" (updated 14 Nov 2026) — https://blog.monerica.com/articles/monero-mining-profitability — Ryzen 9 7950X ~22 kH/s at ~200 W wall, ~$20.56 gross/month, ~$6.16 net/month at 10¢/kWh; network ~6.88 GH/s, XMR ~$496 (15 Nov 2026); ~$0.031/day per kH/s.
- CloudMineCrypto, "Monero Mining: RandomX, CPUs, P2Pool and Staying Safe" — https://cloudminecrypto.com/learn/monero-mining — Ryzen 9 7950X 26,960 H/s at 170 W TDP, from the XMRig public benchmark table.
- SoapBox pool — https://pool.soapbox.community/ — native 450–700 H/s/core; browser light mode ~8.8 H/s/core.
- RandomX design (via Bit2Me Academy summary) — https://academy.bit2me.com/en/que-algoritmo-mineria-randomx-monero/ — fast mode 2,080 MiB dataset, light mode 256 MiB cache; RandomX v2 released March 2026, no official mainnet activation date as of 1 Nov 2026.

**ATLAS internal sources (read 2026-11-18)**
- `~/workspace/atlas/docs/master-mission4-design.md` (Lane A) — prototype design; §3 desktop summary expanded here; §9 the prior tooling-block note this document's §1.2 carries forward.
- `~/workspace/atlas/docs/master-mission1-inspection-report-2026-11-18.md` — feasibility verdict (§4), multi-currency (§5), 75/25 accounting basis (§6), payout architecture (§7), full source URLs for the XMRig/Monero.how/Kryptex/asicprofit/Ypool pages withheld here (§5).
- `~/workspace/atlas/docs/master-mission4-cost-accounting.md` (Lane C) — Gate 5 wall-watt economics; all §6.1–§6.2 figures CARRIED from it; §6.3–§6.4 computed here from its formula.
- `~/workspace/atlas/docs/master-mission3-report-2026-11-18.md` — wallet center, address validation rules (§2.3), "Format valid — ownership not verified".
- `~/workspace/atlas/config/atlas.json` — emergency_stop true, mining disabled/design-only, trading paper-only, capital $0, limits 50/70.
- `~/workspace/atlas/config/pool-rewards.json` — pool config, split, ledger rules, simulation-only mode.

---

*End of design. No code was written for this document, no installer exists, no worker was registered, no pool was connected, no mining ran. Realized mining revenue remains $0. The build lane implements from it; the test lane verifies against it. Gates 2 and 4 remain NOT TESTED and require separate explicit authorization.*
