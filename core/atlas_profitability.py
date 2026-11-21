#!/usr/bin/env python3
"""ATLAS HOST PROFITABILITY MODULE — Master Mission 9, Lane C (host-side,
stdlib only).

A READ-ONLY derivation of profitability intelligence from live inputs
fetched at export time plus carried constants (Mission 2 Obj 4 model,
Mission 4 Gate 5 cost accounting). It writes no ledger rows, no
decisions, no shares, no batches, no sessions, no user rows — the only
write this module ever performs is the atomic export of
``data/profitability.json`` itself (temp file + os.replace, same pattern
as the coordinator, rewards, dashboard, and admin exports).

Derivation rules (binding, docs/master-mission9-design.md):
  - Formula (§1, Obj 4 §1 / M4 §3, implemented exactly):
      daily coins  = (your hashrate / network hashrate) x blocks/day
                     x block reward x (1 - pool fee)
      gross $/day  = daily coins x price (USD)
      electricity $/day = wall watts x 24 / 1000 x price per kWh (USD)
      net $/day    = gross - electricity
      net XMR/day  = net $/day / XMR price (USD)      [panel unit, D-M9-3]
      gross XMR/day (non-XMR coin) = gross $/day / XMR price (USD)
      breakeven H/W = (electricity $/day per wall watt)
                      / (gross $/day per H/s)
      breakeven c/kWh = gross $/day / kWh/day x 100
      user share XMR/day = 0.75 x gross XMR/day
      user net XMR/day = 0.75 x gross XMR/day
                         - electricity $/day / XMR price
    Money is computed in USD and converted to XMR/day only at the final
    rendering step. USD intermediates live only under ``audit_usd`` in
    the export, never in the panel payload (D-M9-3).
  - Live inputs (D-M9-4): XMR network difficulty/height/block value from
    MoneroOcean ``/network/stats`` (port 18081; ``/api/stats`` 404s —
    NEVER used) + XMR price from CoinGecko ``simple/price``; KAS/RVN/ERG
    network stats from the 2Miners ``api/stats`` endpoints + prices from
    the same CoinGecko call; USD/CAD from CoinGecko ``exchange_rates``.
    10 s timeout per endpoint. On any failure the module uses the last
    recorded inputs for that coin and marks that coin STALE with the
    last-fetch time — never raises, never fabricates an input.
  - Electricity rates are tariff constants (HQ Tier 1 7.065c CAD/kWh,
    Tier 2 11.142c CAD/kWh, US average 17.23c USD/kWh), recorded with
    source + effective date, re-verified only on a schedule, not per
    export. The pending 19.5c CAD/kWh Quebec blockchain tariff appears
    ONLY as a labelled RISK SCENARIO row ("Proposed tariff — not in
    effect"), never inside any base-case figure (D-M9-7).
  - Reference profiles only (D-M9-5): CPU Ryzen 7 5800X (10,000 H/s @
    171 W wall) for XMR; GPU RTX 3060 Ti for KAS (480 MH/s @ 150 W),
    RVN (27 MH/s @ 240 W), ERG (137 MH/s @ 132 W); browser workers from
    M4 (laptop 200 H/s @ 45 W, desktop 850 H/s @ 50 W) for XMR.
    Hashrate and wall watts are labelled ASSUMPTION (published
    benchmarks / estimate ranges, not measurements).
  - Your-hardware estimate is NULL while Gate 1 is unmeasured, with the
    verbatim reason "Cannot estimate — hashrate not measured" (D-M9-5).
  - Confirmed earnings are REUSED from the dashboard export's earnings
    block by import — never recomputed — so the profitability section
    can never show a different confirmed-earnings number than the user
    dashboard (D-M9-2).
  - Pool fees (D-M9-8): XMR net under MoneroOcean 0%, SupportXMR 0.6%,
    P2Pool 0% (fees from config/pool-rewards.json, applied to projected
    gross coins only); KAS/RVN/ERG carry 2Miners 1% (Obj 4, CARRIED).
  - 75/25 split projection (D-M9-9): per coin at Tier 2 (base case),
    under the verbatim note "Projection only — not earnings".
  - STALE (D-M9-10): the section is STALE when any live input (price or
    network stats for any coin) is > 1 h old, measured from that input's
    ``fetched_at``; the STALE tag names the stale input. "Not computed
    yet" when a coin has never been computed.

Usage:
    python3 core/atlas_profitability.py status
    python3 core/atlas_profitability.py export

Stdlib only. Portable by copying ~/workspace/atlas.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.expanduser("~/workspace/atlas")
CFG_ATLAS = os.path.join(BASE, "config", "atlas.json")
CFG_POOL = os.path.join(BASE, "config", "pool-rewards.json")
DB = os.path.join(BASE, "data", "atlas.db")
EXPORT = os.path.join(BASE, "data", "profitability.json")
DATA_DIR = os.path.join(BASE, "data")

FETCH_TIMEOUT_S = 10          # per endpoint (D-M9-4)
STALE_AFTER_S = 3600          # live input older than this is STALE (D-M9-10)
BUSY_TIMEOUT_MS = 5000
USER_AGENT = "ATLAS-profitability/1.0"

MONERO_NETWORK_URL = "https://api.moneroocean.stream/network/stats"
MONERO_PORT = "18081"         # XMR network-stats key (M4 endpoint note)
MONERO_BLOCK_TIME_S = 120
MONERO_BLOCK_REWARD = 0.6     # tail emission (Obj 4 / M4)
MONERO_BLOCKS_PER_DAY = 720
COINGECKO_PRICE_URL = ("https://api.coingecko.com/api/v3/simple/price"
                       "?ids=monero,kaspa,ravencoin,ergo&vs_currencies=usd")
COINGECKO_RATES_URL = "https://api.coingecko.com/api/v3/exchange_rates"
TWOMINERS_URL = "https://{sub}.2miners.com/api/stats"

ESTIMATE_NOTE = ("All figures are estimates from live inputs and stated "
                 "assumptions — not earnings, not a promise of profit.")
YOUR_HARDWARE_REASON = "Cannot estimate — hashrate not measured"
SPLIT_NOTE = "Projection only — not earnings"
TARIFF_LABEL = "Proposed tariff — not in effect"
TWOMINERS_NOTE = "2Miners 1% fee applied"
NOT_COMPUTED = "Not computed yet"
ABOVE = "Above breakeven"
BELOW = "Below breakeven"

# Tariff constants (D-M9-4): HQ Rate D, effective April 1, 2026; US EIA
# Form EIA-861 final 2025 data. Recorded with source + effective date,
# re-verified only on a schedule, not per export.
ELECTRICITY = {
    "tier1": {"cents_per_kwh_cad": 7.065,
              "source": "Hydro-Québec Rate D (residential)",
              "effective_date": "2026-04-01"},
    "tier2": {"cents_per_kwh_cad": 11.142,
              "source": "Hydro-Québec Rate D (residential)",
              "effective_date": "2026-04-01"},
    "us_avg": {"cents_per_kwh_usd": 17.23,
               "source": "U.S. EIA Form EIA-861 final 2025 data",
               "effective_date": "2025"},
    "proposed_tariff": {"cents_per_kwh_cad": 19.5,
                        "label": TARIFF_LABEL,
                        "source": ("Proposed February 2026, pending "
                                   "Régie de l'énergie approval"),
                        "effective_date": None},
}
# Fallback fees (D-M9-8) when the config cannot be read; the live path
# always reads config/pool-rewards.json fresh (see _pool_fees()).
DEFAULT_POOL_FEES_PCT = {"moneroocean": 0.0, "supportxmr": 0.6,
                         "p2pool": 0.0, "twominers": 1.0}

# Reference profiles only (D-M9-5, Obj 4 / M4 CARRIED). hashrate_hps is
# the profile hashrate in H/s; hashrate + hashrate_unit are the display
# values. pool_fee_percent None on XMR profiles means "the XMR pool fee
# under comparison" (MoneroOcean 0% is the base case).
PROFILES = (
    {"id": "xmr_cpu", "coin": "xmr", "hardware": "Ryzen 7 5800X",
     "hashrate": 10000, "hashrate_unit": "H/s", "hashrate_hps": 10000,
     "wall_watts": 171, "pool_fee_percent": None},
    {"id": "kas", "coin": "kas", "hardware": "RTX 3060 Ti",
     "hashrate": 480, "hashrate_unit": "MH/s", "hashrate_hps": 480_000_000,
     "wall_watts": 150, "pool_fee_percent": 1.0},
    {"id": "rvn", "coin": "rvn", "hardware": "RTX 3060 Ti",
     "hashrate": 27, "hashrate_unit": "MH/s", "hashrate_hps": 27_000_000,
     "wall_watts": 240, "pool_fee_percent": 1.0},
    {"id": "erg", "coin": "erg", "hardware": "RTX 3060 Ti",
     "hashrate": 137, "hashrate_unit": "MH/s", "hashrate_hps": 137_000_000,
     "wall_watts": 132, "pool_fee_percent": 1.0},
    {"id": "xmr_browser_laptop", "coin": "xmr", "hardware": "Laptop browser",
     "hashrate": 200, "hashrate_unit": "H/s", "hashrate_hps": 200,
     "wall_watts": 45, "pool_fee_percent": None},
    {"id": "xmr_browser_desktop", "coin": "xmr", "hardware": "Desktop browser",
     "hashrate": 850, "hashrate_unit": "H/s", "hashrate_hps": 850,
     "wall_watts": 50, "pool_fee_percent": None},
)
PROFILE_BY_ID = {p["id"]: p for p in PROFILES}
# Coins in the comparison (the split projection covers these four).
SPLIT_PROFILE_IDS = ("xmr_cpu", "kas", "rvn", "erg")
COINS = ("xmr", "kas", "rvn", "erg")
COIN_LABELS = {"xmr": "XMR", "kas": "KAS", "rvn": "RVN", "erg": "ERG"}
COINGECKO_IDS = {"xmr": "monero", "kas": "kaspa", "rvn": "ravencoin",
                 "erg": "ergo"}
TWOMINERS_SUBS = {"kas": "kas", "rvn": "rvn", "erg": "erg"}
# Carried blocks/day when a 2Miners avgBlockTime is unavailable (Obj 4).
CARRIED_BLOCKS_PER_DAY = {"kas": 864000, "rvn": 1440, "erg": 888.7}
# 2Miners blockReward units (Obj 4 §5: KAS blockReward is in sompis,
# 194,454,365 sompis = 1.94454365 KAS; RVN/ERG arrive in coin units on
# their endpoints, with the smallest-unit form as a fallback band).
# _normalize_block_reward() only accepts a raw value that lands in a
# documented band; anything else fails the coin (STALE / not computed),
# never a guessed reward.
# DEVIATION (verified live 2026-11-18, see _fetch_2miners): the 2Miners
# nodes for RVN and ERG publish NO blockReward field at all (and no
# blockReward exists anywhere in the api/stats payload), so their block
# rewards are the CARRIED protocol constants below, recorded with
# provenance — never guessed. KAS publishes blockReward live.
# 2Miners also returns every numeric field as a STRING — _num() coerces.
CARRIED_BLOCK_REWARDS = {
    "rvn": (1250.0, "CARRIED — Obj 4 §6: 1,250 RVN/block post-halving "
            "(Jan 2026, block 4,200,000); next halving ~2030; "
            "2Miners node omits blockReward"),
    "erg": (3.0, "CARRIED — Obj 4 §7: 3 ERG/block verified on the Ergo "
           "explorer (blocks 1,919,263/4); 2Miners node omits blockReward"),
}
BLOCK_REWARD_BANDS = {
    # (low, high, divisor) bands, tried in order.
    "kas": [(0.1, 100.0, 1.0), (1e7, 1e10, 1e8)],
    "rvn": [(100.0, 10000.0, 1.0), (1e9, 1e13, 1e8)],
    "erg": [(0.5, 10.0, 1.0), (1e8, 1e10, 1e9)],
}
XMR_POOLS = (("moneroocean", "MoneroOcean"),
             ("supportxmr", "SupportXMR"),
             ("p2pool", "P2Pool"))


def _now():
    return int(time.time())


def _fmt_age(seconds):
    """Seconds as a short age string ('45s', '73 min old' handled by caller)."""
    seconds = max(int(seconds), 0)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def _read_json_file(path):
    """Parsed JSON dict from a file, or None when missing/unparseable."""
    try:
        with open(path) as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else None
    except (OSError, ValueError):
        return None


def _load_configs():
    """Read both configs fresh on every call — never cached across passes."""
    with open(CFG_ATLAS) as f:
        atlas_cfg = json.load(f)
    with open(CFG_POOL) as f:
        pool_cfg = json.load(f)
    return atlas_cfg, pool_cfg


def _pool_fees(pool_cfg):
    """XMR pool fees (percent) from config/pool-rewards.json, with the
    Obj 4 CARRIED 2Miners 1% for KAS/RVN/ERG. Falls back to the carried
    constants if the config shape is unexpected — never raises."""
    fees = dict(DEFAULT_POOL_FEES_PCT)
    try:
        primary = pool_cfg.get("primary_pool", {})
        if primary.get("name") == "MoneroOcean":
            fees["moneroocean"] = float(primary.get("pool_fee_percent", 0.0))
        for fb in pool_cfg.get("fallback_pools", []):
            name = (fb.get("name") or "").lower().replace(" ", "")
            if name in fees:
                fees[name] = float(fb.get("pool_fee_percent", fees[name]))
    except (AttributeError, TypeError, ValueError):
        pass
    return fees


# ---------------------------------------------------------------------------
# Live fetching (D-M9-4) — fetch-with-fallback, never raises
# ---------------------------------------------------------------------------

def _http_get_json(url):
    """One GET, 10 s timeout. Returns the parsed JSON dict. Raises on any
    transport / HTTP / parse failure — the caller falls back, never
    fabricates."""
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
        if resp.status != 200:
            raise urllib.error.HTTPError(url, resp.status, "non-200",
                                         None, None)
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"unexpected JSON shape from {url}")
    return data


def _fetch_prices():
    """CoinGecko simple/price for all four coins (one call). Returns
    {coin: price_usd or None} or None when the call itself fails."""
    try:
        data = _http_get_json(COINGECKO_PRICE_URL)
    except Exception:
        return None
    prices = {}
    for coin, cg_id in COINGECKO_IDS.items():
        entry = data.get(cg_id) or {}
        price = entry.get("usd")
        prices[coin] = (float(price) if isinstance(price, (int, float))
                        and not isinstance(price, bool) and price > 0
                        else None)
    return prices


def _fetch_usd_cad():
    """CoinGecko exchange_rates: USD/CAD = CAD value / USD value (both
    BTC-denominated). Returns the float, or raises."""
    data = _http_get_json(COINGECKO_RATES_URL)
    rates = data.get("rates") or {}
    usd = (rates.get("usd") or {}).get("value")
    cad = (rates.get("cad") or {}).get("value")
    if not isinstance(usd, (int, float)) or not isinstance(cad, (int, float)):
        raise ValueError("exchange_rates missing usd/cad values")
    if usd <= 0:
        raise ValueError("exchange_rates usd value not positive")
    return float(cad) / float(usd)


def _num(value):
    """A JSON number — or a numeric string (2Miners returns its numeric
    fields as strings) — as a float, or None. Bools are never numbers."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _int_or_none(value):
    """An integer — or an integer string — as an int, or None. Float
    strings with a fractional part (e.g. RVN difficulty '7110.2819')
    return None: difficulty/height are recorded integers only."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _not_computed_coin(coin):
    """A coin record with no live inputs: nothing fabricated, nothing
    presented as fresh (D-M9-10: 'Not computed yet')."""
    rec = {"network_hashrate_hps": None, "difficulty": None, "height": None,
           "block_reward": None, "block_reward_source": None,
           "blocks_per_day": None,
           "price_usd": None, "source_network": None, "source_price": None,
           "fetched_at": None, "stale": False, "status": "not_computed"}
    if coin == "xmr":
        rec["block_reward"] = MONERO_BLOCK_REWARD
        rec["block_reward_source"] = "tail emission (protocol constant)"
        rec["block_time_s"] = MONERO_BLOCK_TIME_S
        rec["blocks_per_day"] = MONERO_BLOCKS_PER_DAY
        rec["source_network"] = ("MoneroOcean /network/stats (port 18081)")
        rec["source_price"] = "CoinGecko simple/price"
    else:
        rec["blocks_per_day"] = CARRIED_BLOCKS_PER_DAY[coin]
        rec["source_network"] = (f"2Miners api/stats "
                                 f"({TWOMINERS_SUBS[coin]}.2miners.com)")
        rec["source_price"] = "CoinGecko simple/price"
    return rec


def _stale_copy(prev_coin):
    """Last recorded inputs for a coin, marked STALE with the last-fetch
    time preserved — never re-stamped fresh (D-M9-4 / D-M9-10)."""
    rec = dict(prev_coin)
    rec["stale"] = True
    rec["status"] = "stale"
    return rec


def _fetch_xmr(prices, prev):
    """XMR network stats (MoneroOcean /network/stats, port 18081) +
    price. Either half failing falls the whole coin back to its last
    recorded inputs (STALE) or to not-computed. Never raises."""
    prev_coin = (prev or {}).get("xmr") or {}
    try:
        data = _http_get_json(MONERO_NETWORK_URL)
        node = data.get(MONERO_PORT) if isinstance(data, dict) else None
        if not isinstance(node, dict):
            node = data if isinstance(data, dict) and "difficulty" in data else None
        if node is None:
            raise ValueError("no port-18081 entry in /network/stats")
        difficulty = int(node["difficulty"])
        if difficulty <= 0:
            raise ValueError("difficulty not positive")
        height = node.get("height") or node.get("main_height")
        value = node.get("value")
        last_block = (value / 1e12 if isinstance(value, (int, float))
                      and not isinstance(value, bool) else None)
        price = (prices or {}).get("xmr")
        if price is None:
            raise ValueError("no XMR price from CoinGecko")
        return {
            "network_hashrate_hps": difficulty / float(MONERO_BLOCK_TIME_S),
            "difficulty": difficulty,
            "height": (int(height) if isinstance(height, (int, float))
                       and not isinstance(height, bool) else None),
            "block_reward": MONERO_BLOCK_REWARD,
            "block_reward_source": "tail emission (protocol constant)",
            "last_block_value_xmr": last_block,
            "block_time_s": MONERO_BLOCK_TIME_S,
            "blocks_per_day": MONERO_BLOCKS_PER_DAY,
            "price_usd": float(price),
            "source_network": "MoneroOcean /network/stats (port 18081)",
            "source_price": "CoinGecko simple/price",
            "fetched_at": _now(), "stale": False, "status": "fresh",
        }
    except Exception:
        if (prev_coin.get("network_hashrate_hps") is not None
                and prev_coin.get("price_usd") is not None):
            return _stale_copy(prev_coin)
        return _not_computed_coin("xmr")


def _normalize_block_reward(coin, raw):
    """2Miners blockReward into whole coins, via the documented bands
    only. The raw value may be a numeric string (2Miners returns its
    numeric fields as strings). Returns None when the raw value lands
    in no band (the coin then falls back — never a guessed reward)."""
    value = _num(raw)
    if value is None:
        return None
    for low, high, divisor in BLOCK_REWARD_BANDS[coin]:
        if low <= value <= high:
            return value / divisor
    return None


def _fetch_2miners(coin, prices, prev):
    """KAS/RVN/ERG network stats from the 2Miners api/stats endpoint +
    price. Same per-coin fallback rule as XMR. Never raises."""
    prev_coin = (prev or {}).get(coin) or {}
    try:
        data = _http_get_json(
            TWOMINERS_URL.format(sub=TWOMINERS_SUBS[coin]))
        nodes = data.get("nodes") if isinstance(data, dict) else None
        node = None
        if isinstance(nodes, list) and nodes and isinstance(nodes[0], dict):
            node = nodes[0]
        elif isinstance(data, dict) and "networkhashps" in data:
            node = data
        if node is None:
            raise ValueError("no node entry in 2Miners api/stats")
        # 2Miners returns its numeric fields as strings — _num() coerces.
        network_hashrate = _num(node.get("networkhashps"))
        if network_hashrate is None or network_hashrate <= 0:
            raise ValueError("networkhashps missing or not positive")
        block_reward, reward_source = _resolve_block_reward(coin, node)
        if block_reward is None:
            raise ValueError("blockReward in no documented band")
        avg_block = _num(node.get("avgBlockTime"))
        if avg_block is not None and avg_block > 0:
            blocks_per_day = 86400.0 / avg_block
            if not (1.0 <= blocks_per_day <= 900000.0):
                blocks_per_day = CARRIED_BLOCKS_PER_DAY[coin]
        else:
            blocks_per_day = CARRIED_BLOCKS_PER_DAY[coin]
        price = (prices or {}).get(coin)
        if price is None:
            raise ValueError(f"no {coin.upper()} price from CoinGecko")
        difficulty = _int_or_none(node.get("difficulty"))
        height = _int_or_none(node.get("height"))
        return {
            "network_hashrate_hps": network_hashrate,
            "difficulty": difficulty,
            "height": height,
            "block_reward": block_reward,
            "block_reward_source": reward_source,
            "raw_block_reward": node.get("blockReward"),
            "avg_block_time_s": avg_block,
            "blocks_per_day": blocks_per_day,
            "price_usd": float(price),
            "source_network": (f"2Miners api/stats "
                               f"({TWOMINERS_SUBS[coin]}.2miners.com)"),
            "source_price": "CoinGecko simple/price",
            "fetched_at": _now(), "stale": False, "status": "fresh",
        }
    except Exception:
        if (prev_coin.get("network_hashrate_hps") is not None
                and prev_coin.get("price_usd") is not None
                and prev_coin.get("block_reward") is not None):
            return _stale_copy(prev_coin)
        return _not_computed_coin(coin)


def _resolve_block_reward(coin, node):
    """Block reward in whole coins + its provenance. Live from the
    2Miners node when published (KAS); the CARRIED protocol constant
    when the node omits it (RVN/ERG — verified live 2026-11-18 that no
    blockReward exists anywhere in their api/stats payloads). Returns
    (reward_or_None, source_string)."""
    live = _normalize_block_reward(coin, node.get("blockReward"))
    if live is not None:
        return live, "live — 2Miners api/stats node blockReward"
    if coin in CARRIED_BLOCK_REWARDS:
        reward, source = CARRIED_BLOCK_REWARDS[coin]
        return reward, source
    return None, None


def _prev_inputs(export_dir):
    """Last recorded inputs from a previous profitability export in the
    same directory, or None. The fallback source (D-M9-4)."""
    payload = _read_json_file(os.path.join(export_dir, "profitability.json"))
    if payload is None:
        return None
    inputs = payload.get("inputs")
    return inputs if isinstance(inputs, dict) else None


def fetch_live_inputs(export_dir=None):
    """Fetch every live input with per-coin fallback to the last recorded
    inputs (STALE) or not-computed. Never raises, never fabricates."""
    if export_dir is None:
        export_dir = DATA_DIR
    prev = _prev_inputs(export_dir)
    prices = _fetch_prices()
    try:
        usd_cad_value = _fetch_usd_cad()
        usd_cad = {"value": usd_cad_value,
                   "source": "CoinGecko exchange_rates",
                   "fetched_at": _now(), "stale": False, "status": "fresh"}
    except Exception:
        prev_fx = (prev or {}).get("usd_cad") or {}
        if prev_fx.get("value") is not None:
            usd_cad = dict(prev_fx)
            usd_cad["stale"] = True
            usd_cad["status"] = "stale"
        else:
            usd_cad = {"value": None, "source": "CoinGecko exchange_rates",
                       "fetched_at": None, "stale": False,
                       "status": "not_computed"}
    return {
        "xmr": _fetch_xmr(prices, prev),
        "kas": _fetch_2miners("kas", prices, prev),
        "rvn": _fetch_2miners("rvn", prices, prev),
        "erg": _fetch_2miners("erg", prices, prev),
        "usd_cad": usd_cad,
    }


def _normalize_staleness(inputs, now):
    """Re-derive each live input's stale flag from its fetched_at at
    export time (D-M9-10: > 1 h old is STALE). Returns a copy — the
    caller's dicts are never mutated. A failed-fetch fallback already
    marks its record stale; this also catches a record that simply
    aged past the hour since it was fetched."""
    fresh = {}
    for key, rec in (inputs or {}).items():
        if not isinstance(rec, dict):
            fresh[key] = rec
            continue
        rec = dict(rec)
        fetched_at = rec.get("fetched_at")
        if rec.get("status") != "not_computed" and isinstance(fetched_at, int):
            if now - fetched_at > STALE_AFTER_S:
                rec["stale"] = True
                rec["status"] = "stale"
        fresh[key] = rec
    return fresh


# ---------------------------------------------------------------------------
# Pure computation — the §1 formula (Obj 4 §1 / M4 §3)
# ---------------------------------------------------------------------------

def _rates_usd_per_kwh(inputs):
    """Electricity price in USD/kWh per rate, or None where the USD/CAD
    conversion is unavailable (Tier 1 / Tier 2 / proposed tariff are CAD
    rates; the US average is already USD)."""
    usd_cad = (inputs.get("usd_cad") or {}).get("value")
    rates = {"us_avg": ELECTRICITY["us_avg"]["cents_per_kwh_usd"] / 100.0}
    for key in ("tier1", "tier2", "proposed_tariff"):
        if usd_cad:
            rates[key] = (ELECTRICITY[key]["cents_per_kwh_cad"] / 100.0
                          / float(usd_cad))
        else:
            rates[key] = None
    return rates


def _coin_figures(profile, coin_rec, rates, xmr_price, base_fee_pct):
    """Per-profile figures from one coin's recorded inputs. Returns None
    when the coin has never been computed (figures stay null, panel shows
    'Not computed yet'). ``base_fee_pct`` is the pool fee for the base
    case (MoneroOcean 0% for XMR, 2Miners 1% for KAS/RVN/ERG)."""
    if (coin_rec is None
            or coin_rec.get("network_hashrate_hps") is None
            or coin_rec.get("block_reward") is None
            or coin_rec.get("blocks_per_day") is None
            or coin_rec.get("price_usd") is None
            or xmr_price is None):
        return None
    network_hps = float(coin_rec["network_hashrate_hps"])
    block_reward = float(coin_rec["block_reward"])
    blocks_per_day = float(coin_rec["blocks_per_day"])
    price = float(coin_rec["price_usd"])
    fee = base_fee_pct / 100.0
    hashrate_hps = float(profile["hashrate_hps"])
    wall_w = float(profile["wall_watts"])
    kwh_per_day = wall_w * 24.0 / 1000.0
    unit_scale = 1.0 if profile["hashrate_unit"] == "H/s" else 1e6

    daily_coins = (hashrate_hps / network_hps * blocks_per_day
                   * block_reward * (1.0 - fee))
    gross_usd = daily_coins * price
    # Gross $/day per H/s (breakeven denominator) and per wall watt.
    gross_per_hps = (1.0 / network_hps * blocks_per_day * block_reward
                     * (1.0 - fee) * price)
    gross_per_unit = gross_per_hps * unit_scale

    net_usd, net_xmr = {}, {}
    for rate, usd_per_kwh in rates.items():
        if usd_per_kwh is None:
            net_usd[rate] = None
            net_xmr[rate] = None
            continue
        elec_usd = kwh_per_day * usd_per_kwh
        net = gross_usd - elec_usd
        net_usd[rate] = net
        net_xmr[rate] = net / xmr_price
    elec_usd = {rate: (None if usd_per_kwh is None else kwh_per_day * usd_per_kwh)
                for rate, usd_per_kwh in rates.items()}

    breakeven_hw, distance, verdict = {}, {}, {}
    for rate, usd_per_kwh in rates.items():
        if usd_per_kwh is None or gross_per_unit == 0:
            breakeven_hw[rate] = None
            distance[rate] = None
            verdict[rate] = None
            continue
        elec_per_watt = 24.0 / 1000.0 * usd_per_kwh
        gate = elec_per_watt / gross_per_unit
        breakeven_hw[rate] = gate
        current_hw = profile["hashrate"] / wall_w
        distance[rate] = current_hw / gate if gate else None
        verdict[rate] = ABOVE if current_hw >= gate else BELOW
    breakeven_cents = (gross_usd / kwh_per_day * 100.0
                       if kwh_per_day else None)
    return {
        "daily_coins": daily_coins,
        "gross_usd_per_day": gross_usd,
        "gross_xmr_per_day": gross_usd / xmr_price,
        "net_usd_per_day": net_usd,
        "net_xmr_per_day": net_xmr,
        "electricity_usd_per_day": elec_usd,
        "kwh_per_day": kwh_per_day,
        "gross_usd_per_hps": gross_per_hps,
        "breakeven_hw": breakeven_hw,
        "breakeven_cents_per_kwh": breakeven_cents,
        "current_hw": profile["hashrate"] / wall_w,
        "distance_to_breakeven": distance,
        "verdict": verdict,
    }


def compute_profitability(inputs, now=None, pool_fees=None):
    """Pure §1 computation over recorded inputs. ``inputs`` is the
    normalized inputs dict (see fetch_live_inputs / test fixtures);
    ``pool_fees`` is {moneroocean, supportxmr, p2pool, twominers} in
    percent (config-derived on the live path). Returns the computed
    blocks (full precision — the panel rounds at assembly)."""
    if now is None:
        now = _now()
    if pool_fees is None:
        pool_fees = dict(DEFAULT_POOL_FEES_PCT)
    rates = _rates_usd_per_kwh(inputs)
    xmr_rec = (inputs.get("xmr") or {})
    xmr_price = xmr_rec.get("price_usd")
    xmr_price = float(xmr_price) if isinstance(xmr_price, (int, float)) else None

    profiles = {}
    for profile in PROFILES:
        coin_rec = inputs.get(profile["coin"]) or {}
        base_fee = (pool_fees.get("moneroocean", 0.0)
                    if profile["coin"] == "xmr"
                    else pool_fees.get("twominers", 1.0))
        if profile["pool_fee_percent"] is not None:
            base_fee = profile["pool_fee_percent"]
        figs = _coin_figures(profile, coin_rec, rates, xmr_price, base_fee)
        profiles[profile["id"]] = {
            "profile": profile["id"], "coin": profile["coin"],
            "hardware": profile["hardware"],
            "hashrate": profile["hashrate"],
            "hashrate_unit": profile["hashrate_unit"],
            "wall_watts": profile["wall_watts"],
            "status": ("computed" if figs is not None else "not_computed"),
            "figures": figs,
        }

    # Pool-fee comparison (D-M9-8): the XMR CPU profile under each XMR
    # pool fee. The fee applies to projected gross coins only.
    xmr_cpu = PROFILE_BY_ID["xmr_cpu"]
    pool_fee_block = {}
    for key, label in XMR_POOLS:
        fee_pct = pool_fees.get(key, 0.0)
        figs = _coin_figures(xmr_cpu, xmr_rec, rates, xmr_price, fee_pct)
        pool_fee_block[key] = {
            "pool": label, "fee_percent": fee_pct,
            "status": ("computed" if figs is not None else "not_computed"),
            "figures": figs,
        }

    # 75/25 split projection at Tier 2 (D-M9-9): user share = 0.75 x
    # gross, ATLAS share = 0.25 x gross, user net = 0.75 x gross -
    # electricity (Tier 2), all in XMR/day.
    split = {}
    for pid in SPLIT_PROFILE_IDS:
        entry = profiles[pid]
        figs = entry["figures"]
        if figs is None:
            split[pid] = {"coin": entry["coin"], "status": "not_computed",
                          "user_share_xmr_per_day": None,
                          "atlas_share_xmr_per_day": None,
                          "user_net_xmr_per_day": None,
                          "gross_xmr_per_day": None}
            continue
        gross_xmr = figs["gross_xmr_per_day"]
        elec_tier2 = figs["electricity_usd_per_day"].get("tier2")
        user_net = None
        if elec_tier2 is not None and xmr_price is not None:
            user_net = 0.75 * gross_xmr - elec_tier2 / xmr_price
        split[pid] = {"coin": entry["coin"], "status": "computed",
                      "user_share_xmr_per_day": 0.75 * gross_xmr,
                      "atlas_share_xmr_per_day": 0.25 * gross_xmr,
                      "user_net_xmr_per_day": user_net,
                      "gross_xmr_per_day": gross_xmr}

    # STALE bookkeeping (D-M9-10 + D-M9-4): any live input > 1 h old is
    # STALE, and any input that arrived via the failed-fetch fallback
    # (status "stale") is STALE even when its last fetch was recent —
    # D-M9-4 marks a fallback coin STALE with its last-fetch time.
    stale_inputs = []
    not_computed = []
    for coin in COINS:
        rec = inputs.get(coin) or {}
        fetched_at = rec.get("fetched_at")
        status = rec.get("status")
        if status == "not_computed" or fetched_at is None:
            if rec.get("network_hashrate_hps") is None:
                not_computed.append(COIN_LABELS[coin])
            continue
        age = now - int(fetched_at)
        if status == "stale" or age > STALE_AFTER_S:
            stale_inputs.append(
                f"STALE — {COIN_LABELS[coin]} network stats "
                f"{_fmt_age(age)} old")
    fx = inputs.get("usd_cad") or {}
    if fx.get("status") == "not_computed" or fx.get("value") is None:
        not_computed.append("USD/CAD")
    elif isinstance(fx.get("fetched_at"), int):
        age = now - int(fx["fetched_at"])
        if fx.get("status") == "stale" or age > STALE_AFTER_S:
            stale_inputs.append(f"STALE — USD/CAD {_fmt_age(age)} old")

    return {"profiles": profiles, "pool_fees": pool_fee_block,
            "split": split, "rates_usd_per_kwh": rates,
            "xmr_price_usd": xmr_price,
            "stale": bool(stale_inputs), "stale_inputs": stale_inputs,
            "not_computed": not_computed}


# ---------------------------------------------------------------------------
# Export assembly
# ---------------------------------------------------------------------------

def _round(value, places):
    return None if value is None else round(value, places)


def _dashboard_earnings(con, export_dir):
    """Confirmed-earnings block reused verbatim from the dashboard export
    (D-M9-2) — never recomputed here."""
    import atlas_dashboard
    dash = atlas_dashboard.dashboard_status(con, export_dir=export_dir)
    return dash["earnings"]


def profitability_status(con, export_dir=None, inputs=None, now=None):
    """Derive the profitability state object from live inputs + carried
    constants + the dashboard earnings block.

    Read-only: performs SELECTs (via the dashboard/coordinator reuse)
    and file reads only. ``export_dir`` is where the sibling exports
    live (and where a previous profitability.json is read for fallback);
    it defaults to the live data dir. ``inputs`` overrides the live
    fetch (tests feed fixture inputs); ``now`` overrides the clock
    (tests). The only write this module ever performs is the export
    itself, in export_profitability_json()."""
    if export_dir is None:
        export_dir = DATA_DIR
    if now is None:
        now = _now()
    atlas_cfg, pool_cfg = _load_configs()
    user_version = con.execute("PRAGMA user_version").fetchone()[0]
    mode = pool_cfg.get("mode", "simulation-only")
    pool_fees = _pool_fees(pool_cfg)
    if inputs is None:
        inputs = fetch_live_inputs(export_dir=export_dir)
    inputs = _normalize_staleness(inputs, now)
    computed = compute_profitability(inputs, now=now, pool_fees=pool_fees)
    earnings = _dashboard_earnings(con, export_dir)

    # Panel payload (D-M9-3): XMR/day to 6 decimals + c/kWh + ratios
    # only. No USD figure appears anywhere in this block.
    comparison = []
    breakeven_rows = []
    sensitivity_rows = []
    for profile in PROFILES:
        entry = computed["profiles"][profile["id"]]
        figs = entry["figures"]
        if figs is None:
            comparison.append({
                "profile": profile["id"], "coin": profile["coin"],
                "reference_hardware": profile["hardware"],
                "hashrate": profile["hashrate"],
                "hashrate_unit": profile["hashrate_unit"],
                "wall_watts": profile["wall_watts"],
                "daily_coins": None,
                "daily_coins_unit": COIN_LABELS[profile["coin"]],
                "gross_xmr_per_day": None,
                "net_xmr_per_day_tier2": None,
                "verdict": None, "status": "not_computed",
                "empty_state": NOT_COMPUTED})
            breakeven_rows.append({
                "profile": profile["id"], "coin": profile["coin"],
                "breakeven_hw_tier2": None, "breakeven_hw_us_avg": None,
                "current_hw": _round(profile["hashrate"] / profile["wall_watts"], 1),
                "distance_to_breakeven_tier2": None,
                "distance_to_breakeven_us_avg": None,
                "breakeven_cents_per_kwh": None,
                "verdict_tier2": None, "verdict_us_avg": None,
                "status": "not_computed", "empty_state": NOT_COMPUTED})
            sensitivity_rows.append({
                "profile": profile["id"], "coin": profile["coin"],
                "net_xmr_per_day": {"tier1": None, "tier2": None,
                                    "us_avg": None, "proposed_tariff": None},
                "status": "not_computed", "empty_state": NOT_COMPUTED})
            continue
        comparison.append({
            "profile": profile["id"], "coin": profile["coin"],
            "reference_hardware": profile["hardware"],
            "hashrate": profile["hashrate"],
            "hashrate_unit": profile["hashrate_unit"],
            "wall_watts": profile["wall_watts"],
            "daily_coins": _round(figs["daily_coins"], 6),
            "daily_coins_unit": COIN_LABELS[profile["coin"]],
            "gross_xmr_per_day": _round(figs["gross_xmr_per_day"], 6),
            "net_xmr_per_day_tier2": _round(
                figs["net_xmr_per_day"].get("tier2"), 6),
            "verdict": figs["verdict"].get("tier2"),
            "status": "computed", "empty_state": None})
        breakeven_rows.append({
            "profile": profile["id"], "coin": profile["coin"],
            "breakeven_hw_tier2": _round(
                figs["breakeven_hw"].get("tier2"), 1),
            "breakeven_hw_us_avg": _round(
                figs["breakeven_hw"].get("us_avg"), 1),
            "current_hw": _round(figs["current_hw"], 1),
            "distance_to_breakeven_tier2": _round(
                figs["distance_to_breakeven"].get("tier2"), 3),
            "distance_to_breakeven_us_avg": _round(
                figs["distance_to_breakeven"].get("us_avg"), 3),
            "breakeven_cents_per_kwh": _round(
                figs["breakeven_cents_per_kwh"], 2),
            "verdict_tier2": figs["verdict"].get("tier2"),
            "verdict_us_avg": figs["verdict"].get("us_avg"),
            "status": "computed", "empty_state": None})
        sensitivity_rows.append({
            "profile": profile["id"], "coin": profile["coin"],
            "net_xmr_per_day": {
                rate: _round(figs["net_xmr_per_day"].get(rate), 6)
                for rate in ("tier1", "tier2", "us_avg", "proposed_tariff")},
            "status": "computed", "empty_state": None})

    pool_fee_rows = []
    for key, _label in XMR_POOLS:
        entry = computed["pool_fees"][key]
        figs = entry["figures"]
        pool_fee_rows.append({
            "pool": entry["pool"], "fee_percent": entry["fee_percent"],
            "net_xmr_per_day_tier2": (
                None if figs is None else _round(
                    figs["net_xmr_per_day"].get("tier2"), 6)),
            "status": entry["status"],
            "empty_state": NOT_COMPUTED if figs is None else None})

    split_rows = []
    for pid in SPLIT_PROFILE_IDS:
        entry = computed["split"][pid]
        split_rows.append({
            "profile": pid, "coin": entry["coin"],
            "user_share_xmr_per_day": _round(
                entry["user_share_xmr_per_day"], 6),
            "atlas_share_xmr_per_day": _round(
                entry["atlas_share_xmr_per_day"], 6),
            "user_net_xmr_per_day": _round(
                entry["user_net_xmr_per_day"], 6),
            "note": SPLIT_NOTE,
            "status": entry["status"],
            "empty_state": NOT_COMPUTED if entry["status"] != "computed" else None})

    # Panel inputs (7a): network stats + tariff rates + fees — values
    # with source + fetched_at + age. Prices and USD/CAD are RECORDED
    # inputs in the top-level inputs block, not panel figures (D-M9-3:
    # no fiat in the panel).
    panel_inputs = []
    for coin in COINS:
        rec = inputs.get(coin) or {}
        fetched_at = rec.get("fetched_at")
        age_s = (now - int(fetched_at)) if isinstance(fetched_at, int) else None
        panel_inputs.append({
            "coin": coin,
            "network_hashrate_hps": rec.get("network_hashrate_hps"),
            "difficulty": rec.get("difficulty"),
            "height": rec.get("height"),
            "block_reward": rec.get("block_reward"),
            "blocks_per_day": rec.get("blocks_per_day"),
            "pool_fee_percent": (pool_fees.get("moneroocean", 0.0)
                                 if coin == "xmr"
                                 else pool_fees.get("twominers", 1.0)),
            "source_network": rec.get("source_network"),
            "fetched_at": fetched_at, "age_s": age_s,
            "age": _fmt_age(age_s) if age_s is not None else None,
            "stale": bool(rec.get("stale")),
            "status": rec.get("status", "not_computed"),
            "stale_label": None,  # filled by the loop below (D-M9-10)
        })
    # Attach the naming STALE label to its input row (D-M9-10).
    for row in panel_inputs:
        label = None
        for stale in computed["stale_inputs"]:
            if COIN_LABELS[row["coin"]] in stale:
                label = stale
        row["stale_label"] = label
    for key, rec in (("tier1", ELECTRICITY["tier1"]),
                     ("tier2", ELECTRICITY["tier2"]),
                     ("us_avg", ELECTRICITY["us_avg"]),
                     ("proposed_tariff", ELECTRICITY["proposed_tariff"])):
        panel_inputs.append({
            "coin": None, "rate": key,
            "cents_per_kwh": (rec.get("cents_per_kwh_cad")
                              if "cents_per_kwh_cad" in rec
                              else rec.get("cents_per_kwh_usd")),
            "source": rec["source"],
            "effective_date": rec.get("effective_date"),
            "label": rec.get("label"),
            "fetched_at": None, "age_s": None, "age": None,
            "stale": False, "status": "constant", "stale_label": None,
        })

    coord_exported_at = _read_export_ts(export_dir, "coordinator.json")
    panel = {
        "estimate_note": ESTIMATE_NOTE,
        "coin_comparison": comparison,
        "breakeven": breakeven_rows,
        "sensitivity": sensitivity_rows,
        "pool_fees": {"rows": pool_fee_rows,
                      "other_coins_note": TWOMINERS_NOTE},
        "split_projection": split_rows,
        "your_hardware": None,
        "your_hardware_reason": YOUR_HARDWARE_REASON,
        "inputs": panel_inputs,
        "last_sync": {
            "profitability_exported_at": now,
            "age_s": 0,
            "stale": computed["stale"],
            "coordinator_exported_at": coord_exported_at,
        },
    }

    # USD intermediates for audit only (D-M9-3) — never rendered.
    audit_usd = {
        "xmr_price_usd": computed["xmr_price_usd"],
        "usd_cad": (inputs.get("usd_cad") or {}).get("value"),
        "rates_usd_per_kwh": computed["rates_usd_per_kwh"],
        "profiles": {},
        "pool_fees": {},
    }
    for profile in PROFILES:
        entry = computed["profiles"][profile["id"]]
        figs = entry["figures"]
        if figs is None:
            audit_usd["profiles"][profile["id"]] = None
            continue
        audit_usd["profiles"][profile["id"]] = {
            "gross_usd_per_day": figs["gross_usd_per_day"],
            "net_usd_per_day": figs["net_usd_per_day"],
            "electricity_usd_per_day": figs["electricity_usd_per_day"],
            "gross_usd_per_day_per_khs": (
                figs["gross_usd_per_hps"] * 1000.0
                if profile["coin"] == "xmr" else None),
        }
    for key, entry in computed["pool_fees"].items():
        figs = entry["figures"]
        audit_usd["pool_fees"][key] = (
            None if figs is None else {
                "gross_usd_per_day": figs["gross_usd_per_day"],
                "net_usd_per_day": figs["net_usd_per_day"]})

    # Inputs block: every input with value, source, fetched_at (live
    # inputs) or source + effective date (tariff constants, D-M9-4).
    inputs_block = {}
    for coin in COINS:
        rec = dict(inputs.get(coin) or {})
        inputs_block[coin] = rec
    inputs_block["usd_cad"] = dict(inputs.get("usd_cad") or {})
    inputs_block["electricity"] = {
        key: dict(val) for key, val in ELECTRICITY.items()}
    inputs_block["pool_fees"] = {
        "moneroocean": {"fee_percent": pool_fees.get("moneroocean", 0.0),
                        "source": "config/pool-rewards.json"},
        "supportxmr": {"fee_percent": pool_fees.get("supportxmr", 0.6),
                       "source": "config/pool-rewards.json"},
        "p2pool": {"fee_percent": pool_fees.get("p2pool", 0.0),
                   "source": "config/pool-rewards.json"},
        "twominers": {"fee_percent": pool_fees.get("twominers", 1.0),
                      "source": "Obj 4 (CARRIED)"},
    }

    return {
        "exported_at": now,
        "source_db_user_version": user_version,
        "mode": mode,
        "emergency_stop": bool(atlas_cfg.get("emergency_stop")),
        "estimate_note": ESTIMATE_NOTE,
        "simulation": mode == "simulation-only",
        "inputs": inputs_block,
        "panel": panel,
        "audit_usd": audit_usd,
        # Confirmed earnings reused verbatim from the dashboard export
        # (D-M9-2) — never recomputed here.
        "confirmed_earnings": earnings,
        "your_hardware": None,
        "your_hardware_reason": YOUR_HARDWARE_REASON,
        "stale": computed["stale"],
        "stale_inputs": computed["stale_inputs"],
        "not_computed": computed["not_computed"],
        "provenance": {
            "inputs": ("RECORDED (live fetch with source + fetched_at; "
                       "tariff constants with source + effective date)"),
            "figures": "DERIVED (host) + ESTIMATE — §1 formula from recorded inputs",
            "confirmed_earnings": ("DERIVED (host) — dashboard export "
                                   "earnings block reused by import, "
                                   "SIMULATION-tagged"),
            "your_hardware": "UNAVAILABLE — Gate 1 unmeasured",
        },
    }


def _read_export_ts(export_dir, filename):
    """exported_at (or diagnostics-style ts) from a sibling export
    file, or None when missing/unparseable."""
    payload = _read_json_file(os.path.join(export_dir, filename))
    if payload is None:
        return None
    for key in ("exported_at", "ts"):
        ts = payload.get(key)
        if isinstance(ts, int) and not isinstance(ts, bool):
            return ts
    return None


def connect(db_path=DB):
    """Open a connection with manual transaction control (autocommit mode),
    same pattern as atlas_coordinator.connect()."""
    con = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000.0)
    con.isolation_level = None
    con.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def export_profitability_json(con=None, db_path=DB, export_path=EXPORT,
                              inputs=None):
    """Write data/profitability.json by atomic write (.tmp -> os.replace),
    the same pattern as the coordinator, rewards, dashboard, and admin
    exports. The file is a derived export: deleting it loses nothing,
    it regenerates from the DB + live inputs. The sibling source exports
    are read from the export path's own directory, so temp-DB exports in
    /tmp never read live files. Returns (path, payload)."""
    own_con = False
    if con is None:
        con = connect(db_path)
        own_con = True
    try:
        export_dir = os.path.dirname(os.path.abspath(export_path))
        payload = profitability_status(con, export_dir=export_dir,
                                       inputs=inputs)
    finally:
        if own_con:
            con.close()
    tmp_path = export_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(payload, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, export_path)
    return export_path, payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _open():
    return connect(DB)


def cmd_status(_args):
    con = _open()
    try:
        payload = profitability_status(con)
    finally:
        con.close()
    print(json.dumps(payload, indent=2))
    print("Hashrate: not measured (Gate 1 unmeasured — no probe measurement exists)")
    print("Estimated earnings: none (Cannot estimate — hashrate not measured)")
    return 0


def cmd_export(_args):
    path, payload = export_profitability_json()
    xmr = next((r for r in payload["panel"]["coin_comparison"]
                if r["profile"] == "xmr_cpu"), {})
    print(f"Exported {path} (exported_at {payload['exported_at']}, "
          f"stale={payload['stale']}, "
          f"XMR net XMR/day (Tier 2) {xmr.get('net_xmr_per_day_tier2')}, "
          f"your-hardware {payload['your_hardware']})")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="ATLAS host profitability (Master Mission 9) — read-only derivation, simulation only.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="print derived profitability state")
    sub.add_parser("export", help="write data/profitability.json (atomic)")

    args = parser.parse_args(argv)
    handlers = {"status": cmd_status, "export": cmd_export}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
