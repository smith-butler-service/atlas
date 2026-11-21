# ATLAS Mission 2 — Lane M2.3: Network Data Validation

- **Lane:** M2.3 (read-only investigation; no files edited, no endpoints changed, no API writes)
- **Date/time of checks:** 2026-11-18, 02:05–02:24 EST (07:05–07:24 UTC)
- **Method:** `curl -m 10` and Python `urllib` (the same method `core/diagnostics.py` t14 uses), `User-Agent: ATLAS/0.1`, 10 s timeout. DNS verdicts via Cloudflare DoH.
- **Baseline referenced:** 01:52 EST hourly report — diagnostics 15/15 PASS; DB ok; snapshot fresh; emergency stop ACTIVE; mining DISABLED; trading PAPER ONLY; capital $0.

## 0. What the code actually fetches (exact URLs from source)

`core/atlas_monitor.py` makes **no network calls at all** (reads `/proc` only).
`core/atlas_core.py` makes **no network calls** (no `urllib`/`requests`/URL strings found).
The only endpoint list in code is `core/diagnostics.py` t14 (`_t14_network`):

| Source in code | Exact URL |
|---|---|
| CoinGecko | `https://api.coingecko.com/api/v3/ping` |
| MoneroOcean | `https://api.moneroocean.stream/pool/stats` |
| blockchain.info | `https://blockchain.info/q/getblockcount` |

**mempool.space is NOT in any code file.** It was removed from t14 on 2026-11-17 after repeated unreachable verdicts and replaced by blockchain.info; `config/atlas.json` still records `mempool_space: "unreachable-from-this-host"`. It was tested here only because the task and the 01:52 EST hourly report asked for it — see §7.

**Critical consequence:** t14 asserts **HTTP 200 only** — it does not parse any response field. No ATLAS code reads `pool_statistics`, prices, block heights, or any other field from these endpoints today. So there is **no field-level breakage risk to running code** from any API shape change; the field checklists below are for future consumers, not for a current dependency.

## 1. Per-endpoint results

All times are per-request response times. "Round" = one full pass over all endpoints.

| Endpoint (exact URL) | R1 ~02:05 | R2 ~02:07 | R3 ~02:08 | R4 02:24 | Best time | Verdict |
|---|---|---|---|---|---|---|
| `https://api.coingecko.com/api/v3/ping` | 200 (34 B) | 200 | 200 | 200 | 0.53 s | **PASS — live** |
| `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,monero&vs_currencies=usd` *(supplementary, not in code)* | 200 (48 B) | 200 | 200 | 200 | 0.34 s | **PASS — live** |
| `https://api.moneroocean.stream/pool/stats` | 000 (transient, see §6) | 200 | 200 (12,269 B) | 200 (12,294 B) | 1.05 s | **PASS — live** |
| `https://api.moneroocean.stream/api/stats` *(known-bad, check only)* | 000 (transient) | — | **404** | — | 0.82 s | **404 confirmed — DO NOT USE** |
| `https://blockchain.info/q/getblockcount` | 000 (transient) | 200 | 200 (`976396`) | 200 (`976397`) | 0.71 s | **PASS — live** |
| `https://mempool.space/api/blocks/tip/height` | 000 (transient) | 200 | 200 (`976396`) | 200 (`976397`) | 0.80 s | **PASS — live** |
| `https://mempool.space/api/v1/fees/recommended` *(supplementary)* | 000 (transient) | 200 | 200 | 200 | 0.60 s | **PASS — live** |
| `https://blockstream.info/api/blocks/tip/height` *(cross-check only)* | 000 (transient) | 200 | 200 (`976396`) | 200 (`976397`) | 0.74 s | **PASS — live** |

Round 1 was run with `curl -o <file>`; its per-request timing failed (`bc` not installed on this VM) and is not reported. Rounds 2–4 timings are from `curl -w %{time_total}` / `urllib` and are reliable.

## 2. Response excerpts (Round 3, 02:08 EST unless noted)

- **CoinGecko ping:** `{"gecko_says":"(V3) To the Moon!"}` (34 B, exact)
- **CoinGecko price:** R1 `{"bitcoin":{"usd":64629},"monero":{"usd":506.3}}` → R3 `{"bitcoin":{"usd":64694},"monero":{"usd":505.84}}` — values moved between rounds: live, not cached.
- **MoneroOcean `/pool/stats` (12,269 B):** `{"pool_list":["pplns"],"pool_statistics":{"hashRate":261612310.925,"miners":4944,"totalHashes":1.4717822001588153e+23,"lastBlockFoundTime":1794984803,"lastBlockFound":3808886,"totalBlocksFound":51954,"totalMinersPaid":44042,"totalPayments":101665,"roundHashes":732777334987.8054,"totalAltBlocksFound":...`
- **blockchain.info:** plain text `976396` (R3) → `976397` (R4)
- **mempool.space tip height:** plain text `976396` (R3) → `976397` (R4); tip hash `00000000000000000000a5c3b44a233d73fadbbb86e97edd055acd648d3fa0d1`
- **mempool.space fees:** `{"fastestFee":2,"halfHourFee":1,"hourFee":1,"economyFee":1,"minimumFee":1}` (R3) → fastestFee `1` (R4) — live, moving.
- **Blockstream tip height:** `976396` (R3) → `976397` (R4)

## 3. Response-structure / required-field checklists

### CoinGecko `/api/v3/ping`
- Code reads: **nothing** (status only). Response: single field `gecko_says` (string) — present, unchanged shape. ✅ No change.

### CoinGecko `/api/v3/simple/price` (supplementary; NOT used by any code)
- `bitcoin.usd` (number) ✅, `monero.usd` (number) ✅, no nulls. Values move run-to-run. ✅

### MoneroOcean `/pool/stats` — full field audit (R3 body)
- Top-level keys: `pool_list`, `pool_statistics`, `last_payment` — all present. ✅
- `pool_statistics` keys (28): `activePort`, `activePortProfit`, `activePorts`, `altBlocksFound`, `coinComment`, `coinProfit`, `coins`, `currentEfforts`, `hashRate`, `lastBlockFound`, `lastBlockFoundTime`, `minBlockRewards`, `miners`, `pending`, `portCoinAlgo`, `portHash`, `portMinerCount`, `pplnsPortShares`, `pplnsWindowTime`, `price`, `roundHashes`, `totalAltBlocksFound`, `totalBlocksFound`, `totalHashes`, `totalMinersPaid`, `totalPayments`, `updatedAt` — all present, **zero nulls**. ✅
- Key values (R3): `hashRate` 261,612,310.925 (float, ~261.6 MH/s); `miners` 4944 (int); `lastBlockFound` 3808886 (int); `lastBlockFoundTime` 1794984803 (int) = 2026-11-18T06:53:23Z, ~31 min before the check (plausible pool block interval); `updatedAt` 1794986569 = ~07:22 UTC, minutes old; `totalBlocksFound` 51954; `totalPayments` 101665; `price.usd` 504.72 (XMR).
- XMR sub-figures: port 18081 (`coins['18081']`): `hashrate` 238,728,752.55, `miners` 4751, `active` true, `algo` `rx/0`, `pplnsShare` 0.9122.
- Cross-check vs lane M2-obj3 findings (same day): hashRate 266.5 MH/s / 4,926 miners / last block 3,808,866 then vs 261.6 MH/s / 4,944 miners / last block 3,808,886 now — block advanced by 20, figures moved: live data, consistent. ✅
- **No field renamed, moved, or disappeared** vs the documented shape. ✅

### blockchain.info `/q/getblockcount`
- Code reads: **nothing** (status only). Response: plain-text integer, no JSON. ✅ Parses as int.

### mempool.space `/api/blocks/tip/height`
- Not used by any code. Response: plain-text integer. ✅ Parses as int.

### mempool.space `/api/v1/fees/recommended` (supplementary)
- Fields `fastestFee`, `halfHourFee`, `hourFee`, `economyFee`, `minimumFee` — all present, all integers, no nulls. ✅

## 4. Data timestamps / cross-source block-height comparison

| Source | Height R3 (~02:08) | Height R4 (02:24) |
|---|---|---|
| blockchain.info `/q/getblockcount` | 976396 | 976397 |
| mempool.space `/api/blocks/tip/height` | 976396 | 976397 |
| Blockstream `/api/blocks/tip/height` | 976396 | 976397 |

**All three agree exactly, and all three advanced by 1 block in ~16 minutes** — consistent with the ~10 min Bitcoin block interval. No source is stale or on a fork. ✅

- MoneroOcean `lastBlockFoundTime` 2026-11-18T06:53:23Z (~31 min old at check) and `updatedAt` ~07:22 UTC (minutes old): pool data current. ✅
- CoinGecko prices moved between rounds (BTC $64,629 → $64,694; XMR $506.30 → $505.84): live, not cached. ✅
- XMR price cross-check: CoinGecko $505.84 vs MoneroOcean pool `price.usd` $504.72 — ~0.2% apart, different sources/timing: consistent. ✅

## 5. Data freshness verdict

**All data is LIVE, not stale/cached:** block heights advance in lockstep across three independent sources; prices and fees move between rounds minutes apart; MoneroOcean `updatedAt` is minutes old and its last pool block is ~31 min old.

## 6. Unexpected API changes

**None.** No field changed name, moved, or disappeared in any response vs what the code/docs expect. CoinGecko ping shape unchanged (`gecko_says`); MoneroOcean `/pool/stats` shape matches the documented structure (28 `pool_statistics` keys, all present); blockchain.info still returns a bare integer.

**One anomaly, investigated, not an API change:** in Round 1 (~02:05 EST) all five non-CoinGecko hosts returned curl `000` simultaneously while both CoinGecko calls returned 200. Rounds 2–4 (starting ~2 min later) returned 200 for every host with ~0.6–1.0 s response times, and DNS (Cloudflare DoH) resolves all five hosts correctly (Status 0). Pattern = a brief egress-proxy blip affecting new CONNECT tunnels, not per-host blocking and not an API change. All five hosts recovered together without any intervention. Flagged for awareness only: if a future diagnostics run shows a simultaneous multi-host 000, retry before concluding any host is down.

## 7. mempool.space verdict — GENUINELY REACHABLE NOW

- **Confirmed 200 on three consecutive rounds over ~17 minutes** (R2 ~02:07, R3 ~02:08, R4 02:24 EST), via both `curl` and Python `urllib`:
  - `https://mempool.space/api/blocks/tip/height` → 200, `976396` → `976397`
  - `https://mempool.space/api/v1/fees/recommended` → 200, live fee data
  - `https://mempool.space/api/blocks/tip/hash` → 200 (R3)
- DNS resolves via Cloudflare DoH (Status 0, 8 A records).
- This reverses the standing "unreachable from this host" verdict (confirmed dead 3× on 2026-11-17, and 000 once in Round 1 today as part of the transient blip in §6). The 01:52 EST hourly report's 200 is corroborated.
- Likely cause of the change: **the VM was replaced at ~01:00 EST** — the new VM's network path no longer blocks mempool.space. This is a network-path change, not an API change.
- **Recommendation (no code change made):** `config/atlas.json` still says `mempool_space: "unreachable-from-this-host"`. That record is now stale and should be updated to `verified-200` by whoever owns config — I did NOT change it (read-only lane). Re-adding mempool.space to diagnostics t14 is a decision for the parent/coordinator, not this lane; blockchain.info remains a valid primary either way.

## 8. MoneroOcean endpoint preservation

- **Working endpoint preserved: `https://api.moneroocean.stream/pool/stats` → 200.** ✅
- **Dead endpoint confirmed: `https://api.moneroocean.stream/api/stats` → HTTP 404** (R3, 0.82 s). Do NOT replace `/pool/stats` with `/api/stats`. No replacement of any working endpoint is proposed.

## 9. Anything needing a code change?

**No code change is required by these findings.** All four endpoints return 200 with live, well-formed data; no field the code reads is missing or changed (and the code reads no fields at all — t14 is status-only).

Two bookkeeping items for the parent/coordinator (not done by this lane — read-only):
1. **Stale config record:** `config/atlas.json` → `blockchain_apis.mempool_space` says `"unreachable-from-this-host"`; it is now verified 200 (three consecutive rounds). Update the record if config accuracy matters.
2. **Optional:** consider re-adding mempool.space to diagnostics t14 (it was removed 2026-11-17 when unreachable) now that the new VM reaches it — or leave blockchain.info as the single BTC-height source. Either is fine; do not add it without also keeping blockchain.info until mempool.space proves stable over days, given its history of blocking on this host and the Round 1 transient.

## Appendix — DNS (Cloudflare DoH, R2)

| Host | DoH Status | Answers |
|---|---|---|
| `api.moneroocean.stream` | 0 | 104.21.39.74, 172.67.143.168 |
| `blockchain.info` | 0 | 104.16.118.55, 104.16.117.55 |
| `mempool.space` | 0 | 103.165.192.201–208 (8 addrs) |
| `blockstream.info` | 0 | 23.155.96.128 |
| `api.coingecko.com` | 0 | 172.66.172.219, 104.20.41.132 |

All resolve. (Note: the sandbox system resolver returns sink IPs for unresolvable domains, so DoH was used for verdicts per workspace TOOLS.md.)
