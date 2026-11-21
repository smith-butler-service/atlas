# PROJECT ATLAS — MISSION 2, OBJECTIVE 3 FINDINGS
## Direct Blockchain Connectivity (read-only tests only)
Date: 2026-11-18, tests run 05:55–05:58 UTC (00:55–00:58 EST).
All tests were read-only: HTTP(S) GETs, JSON-RPC read calls, and bare TCP
connects. No transactions, no wallet operations, no authentication, no mining,
no account creation. Nothing was purchased, rented, deployed or activated.

Labels: **VERIFIED** = measured by me in this session (command + result shown).
**PUBLISHED** = figure from a named published source (source + date given).
**ESTIMATE** = calculated from measured/published inputs. **ASSUMPTION** = a
stated guess, not measured.

## Host snapshot at test time (VERIFIED)
- Disk: 150 GB volume, 29 GB used, **122 GB free** (19% used).
- Data volume reports as non-rotational (SSD): `/dev/mapper/rv` on vdd,
  ROTA 0. IOPS not measured.
- RAM: 7,934 MB host view, 6 GB cell cap; **available 1,078–1,422 MB** at test
  time (memory pressure is high and worsening through the session).
- CPU: 4 vCPUs visible (AMD EPYC 9D25), shared cell cap 1.5 CPUs.
- Chain tips cross-verified by independent sources at test time:
  Monero height **3,808,873** (top hash 05dbb459d10f30dd…),
  Bitcoin height **976,387**, Ethereum block **26,439,992** (0x1937138).

## 1. Monero public nodes (JSON-RPC) — VERIFIED
Method: `POST /json_rpc {"jsonrpc":"2.0","id":"0","method":"get_info"}`,
plus a parsed re-check. DNS verdicts via Cloudflare DoH.

| Node | Result | Latency | Detail |
|---|---|---|---|
| xmr-node.cakewallet.com:18081 | 200, works | 7.44 s first contact, <1 s after | height 3808873, difficulty 772,719,195,794, synced, mainnet |
| node.sethforprivacy.com:18089 | 200, works | 7.20 s first contact, <1 s after | identical tip: height 3808873, same top hash |
| node.moneroworld.com:18089 | dead | 4.52 s, curl exit 52 (empty reply) | DoH Status 3 = **NXDOMAIN** — the domain no longer exists; the empty reply was the sandbox sinkhole, not the node |
| node.supportxmr.com:18089 | no answer | 10.00 s, curl exit 28 (timeout) | DoH resolves (107.178.98.234) — the RPC port itself does not answer from this host |

Notes:
- Both working nodes returned the identical chain tip, and that tip hash
  (05dbb459d10f30dd…) matches SupportXMR's network/stats hash — three
  independent sources agree, so the Monero tip is cross-verified.
- `get_height` and `getheight` both return JSON-RPC error -32601 "Method not
  found" on these restricted nodes. `get_info` is the working call (it
  includes height, difficulty, and sync state).
- First contact with each working node took ~7 s; subsequent calls answered
  in under 1 s. Usable, but slow to warm up.

## 2. Mining pool APIs (read-only stats) — VERIFIED
| Pool / endpoint | Result | Latency | Measured content |
|---|---|---|---|
| MoneroOcean `api.moneroocean.stream/pool/stats` | 200 | 0.62 s | hashRate 266,542,504 H/s (~266.5 MH/s), 4,926 miners, last block 3,808,866, total blocks 51,952 |
| MoneroOcean `api.moneroocean.stream/network/stats` | 200 | — | per-coin difficulty/height data returned |
| SupportXMR `supportxmr.com/api/pool/stats` | 200 (after a 301 redirect; follow with `-L`) | 1.58 s | hashRate 1,987,406,046 H/s (~1.99 GH/s), 5,398 miners, last block 3,808,862, total blocks 569,655 |
| SupportXMR `supportxmr.com/api/network/stats` | 200 | 1.46 s | difficulty 772,864,657,801, height 3,808,872 |

Both pools' APIs work from this host with no key and no account. The two
pools disagree on hashrate by ~7× (266 MH/s vs 1.99 GH/s) — that is real:
SupportXMR is a much larger pool. Both agree on the Monero chain tip.

## 3. Bitcoin — VERIFIED
| Endpoint | Result | Latency | Measured content |
|---|---|---|---|
| blockchain.info `/latestblock` | 200 | 1.10 s | height 976,387 |
| Blockstream Esplora `blockstream.info/api/blocks/tip/height` | 200 | 0.76 s | height 976,387 (agrees with blockchain.info) |
| mempool.space `/api/blocks/tip/height` | unreachable | 10.00 s, curl exit 28 (timeout) | DoH resolves mempool.space to real IPs (103.165.192.202–204) — so this is a **network-level connect block, not DNS**. Same failure as every prior check. |

Alternatives (VERIFIED working): Blockstream Esplora is a full replacement
for mempool.space's block/tip data from this host. blockchain.info also works.
No mempool.space data is reachable from this host by any route tested.

## 4. Ethereum public RPC (`eth_blockNumber`) — VERIFIED
| Endpoint | Result | Latency | Detail |
|---|---|---|---|
| ethereum.publicnode.com | 200, works | 5.50 s | result `0x1937138` = block 26,439,992 |
| cloudflare-eth.com | 200, but request refused | 4.11 s | JSON-RPC error -32046 "Cannot fulfill request" — endpoint alive, call refused |
| eth.llamarpc.com | 525 (Cloudflare SSL handshake failure) | 6.13 s | unreachable |

One working public Ethereum RPC exists from this host (publicnode.com).
It is slow (5.5 s) and is a third-party gateway, not a direct node
connection — read-only chain-tip reads work; anything heavier would need a
local node or a paid endpoint.

## 5. Mining pool stratum ports (bare TCP connect only) — VERIFIED
No authentication, no login, no shares submitted — a TCP connect and an
immediate close.

| Host:port | Result |
|---|---|
| gulf.moneroocean.stream:10001 (MoneroOcean) | CONNECTED in 0.01 s |
| gulf.moneroocean.stream:10101 (MoneroOcean) | CONNECTED in 0.00 s |
| pool.supportxmr.com:3333 (SupportXMR) | CONNECTED in 0.00 s |
| pool.supportxmr.com:5555 (SupportXMR) | CONNECTED in 0.00 s |

All four stratum ports are reachable from this host. Caveat: a bare TCP
connect proves the port accepts connections (possibly a load balancer), not
that the stratum service behind it is healthy. No stratum traffic was sent.

## 6. Local full-node feasibility — PUBLISHED figures vs this host
Published requirements (sources + dates in the table). Host limits:
122 GB free disk, 6 GB RAM cap, ~1.1 GB RAM available, 1.5 shared CPUs,
SSD data volume.

| Node | Full (unpruned) | Pruned | RAM | Verdict on this host |
|---|---|---|---|---|
| Monero `monerod` | ~230–295 GB (official docs 2026-10-05: 265 GiB chain, 662.5 GiB SSD recommended; xmrlist Oct 2026: ~295 GB) | ~80–105 GB (docs: 105 GiB, 262.5 GiB recommended) | 4 GB min, 8 GB comfortable | **Full: NO** — disk fails outright (122 GB free vs ~250–300 GB). **Pruned: MARGINAL** — disk fits (~80–105 GB) but leaves only ~17–42 GB and is below the docs' recommended headroom; RAM 4 GB wanted vs ~1.1 GB available; sync takes days on 1.5 shared CPUs. Not recommended here. |
| Bitcoin Core | ~740–860 GB (742 GB May 2026; 771–783 GB Sep–Nov 2026; Core 31.1 budgets 856 GiB; grows ~80 GB/yr) | ~7–15 GB (550 MB blocks + ~9–14 GB chainstate) | 2 GB min, 4–8 GB recommended | **Full: NO** — disk fails by ~650 GB and RAM fails. **Pruned: POSSIBLE on disk** (~7–15 GB) but RAM is tight (2 GB min vs ~1.1 GB available) and the initial sync still downloads ~800 GB and is CPU-heavy. Feasible only pruned, with patience; not recommended while memory is this tight. |
| Ethereum full node | 4 TB NVMe SSD, 16 GB RAM (ethereum.org guide, Oct 2026) | — | 16 GB | **NO** — far beyond this host on both disk and RAM. |

Sources: Monero — docs.getmonero.org/running-node/monerod-systemd/
(2026-10-05), xmrlist.com/blog/run-your-own-monero-node-guide (Oct 2026),
monerohelp.com/guides/run-a-monero-node (Aug 2026). Bitcoin —
help.blockstream.com/education/nodes/introduction-and-role/what-is-a-bitcoin-node,
cloudminecrypto.com/learn/bitcoin-node (data 2026-11-16),
offshoreserv.com/docs/vps/bitcoin-monero-node (Sep 2026). Ethereum —
ethereum.org node guide via coindaro.com/learn/blockchain-scalability/
(Oct 2026).
Bandwidth was not measured in this session (ASSUMPTION: the VM has
datacenter-class connectivity based on fast API responses, but no speed test
was run; a Monero sync needs 100 GB+ download, a Bitcoin sync ~800 GB).

## Reachable / unreachable summary
| Service | Status |
|---|---|
| Monero public node (cakewallet) | REACHABLE (get_info, synced) |
| Monero public node (sethforprivacy) | REACHABLE (get_info, synced) |
| Monero public node (moneroworld) | DEAD (NXDOMAIN) |
| Monero public node (supportxmr:18089) | UNREACHABLE (TCP timeout; DNS resolves) |
| MoneroOcean pool API | REACHABLE |
| SupportXMR pool API | REACHABLE (follow the 301) |
| MoneroOcean stratum (10001, 10101) | REACHABLE (TCP) |
| SupportXMR stratum (3333, 5555) | REACHABLE (TCP) |
| blockchain.info | REACHABLE |
| Blockstream Esplora | REACHABLE |
| mempool.space | UNREACHABLE (network-level connect timeout; DNS resolves) |
| Ethereum publicnode.com RPC | REACHABLE (eth_blockNumber) |
| Ethereum cloudflare-eth.com | REACHABLE but refuses the call (-32046) |
| Ethereum eth.llamarpc.com | UNREACHABLE (HTTP 525) |
| Local Monero full node on this host | NOT FEASIBLE (disk + RAM) |
| Local Monero pruned node on this host | MARGINAL (not recommended) |
| Local Bitcoin full node on this host | NOT FEASIBLE (disk + RAM) |
| Local Bitcoin pruned node on this host | POSSIBLE on disk, RAM-tight (not recommended now) |
| Local Ethereum full node on this host | NOT FEASIBLE |

## Alternatives (what ATLAS can use now, without Muse)
- **Monero chain data:** public nodes xmr-node.cakewallet.com:18081 and
  node.sethforprivacy.com:18089 answer `get_info` directly (height,
  difficulty, sync state). No key, no account. Keep both as fallbacks; add a
  third from a public node list, since community nodes disappear
  (moneroworld is already gone).
- **Mining intelligence:** MoneroOcean and SupportXMR public APIs both work
  and agree on the chain tip; SupportXMR is ~7× larger by hashrate.
- **Bitcoin chain data:** Blockstream Esplora replaces mempool.space
  entirely from this host; blockchain.info is a second source.
- **Ethereum chain data:** ethereum.publicnode.com works for read-only RPC.
- **Pool connectivity:** stratum TCP ports for both Monero pools are
  reachable — a miner on authorized external hardware could connect; this
  host itself must not mine (no authorization, no GPU, shared infrastructure).
- **Local nodes:** none fit this host except a marginal pruned Monero node
  and a RAM-tight pruned Bitcoin node. A local node needs authorized external
  hardware (Objective 2's territory) — a small dedicated box or VPS with
  4 GB+ RAM and 150–300 GB SSD for Monero, or 8 GB RAM and ~1 TB SSD for
  Bitcoin full.

## Network restrictions found (VERIFIED)
- mempool.space: DNS resolves, TCP/HTTPS connect times out (10 s) — blocked
  at the network level from this host. Consistent across every check.
- node.supportxmr.com:18089: DNS resolves, TCP connect times out (10 s).
- eth.llamarpc.com: HTTP 525 from Cloudflare.
- cloudflare-eth.com: answers HTTP 200 but refuses JSON-RPC calls (-32046).
- No other endpoint tested was blocked. CoinGecko, MoneroOcean,
  blockchain.info, Blockstream, SupportXMR, Cake Wallet and Seth's node all
  answer normally.

## Method note
Every command above was run from the ATLAS host on 2026-11-18 05:55–05:58 UTC
with `curl -m 10/15` timeouts and Python `socket` connects (8 s timeout).
Nothing in this session sent a transaction, touched a wallet, authenticated,
or mined. The two `getheight` failures were method-name rejections by the
nodes' restricted RPC, not connectivity failures — `get_info` returns the
height on the same nodes.
