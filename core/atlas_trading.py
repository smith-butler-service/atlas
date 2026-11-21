#!/usr/bin/env python3
"""ATLAS PAPER-TRADING ENGINE — Master Mission 22 (host-side, stdlib only).

Simulation-only trading priced and executed against live market data,
with a paper ledger. Implements docs/master-mission22-trading-design.md
(D-M22-1 to D-M22-7):

  - Mode is always "paper". There is NO live mode in code: no exchange
    client, no API keys, no order submission to any venue, no wallet /
    key / seed handling of any kind.
  - Funding rule v2 (user order 2026-11-20 ~17:30 EST): eligible
    capital = realized net mining profits + confirmed USDC deposits on
    Solana only. Paper accounts hold VIRTUAL funds only
    (source='virtual-simulation', default $10,000 virtual) — virtual
    funds are not capital, cannot be withdrawn, converted, or counted
    as eligible capital. There is no code path from a virtual balance
    to eligible capital.
  - Prices: CoinGecko simple/price for XMR/KAS/RVN/ERG (same four
    coins as profitability), 10 s timeout, fetch-with-fallback to the
    last recorded price in trading_prices (marked stale, fetched_at
    preserved). No price at all -> the order is REJECTED
    ('no-live-price'), never fabricated. Prices older than 1 h are
    STALE; a stale price still executes but the order row carries
    price_stale = 1.
  - Money is integer USD cents for cash and integer base units for
    coins (XMR piconero 10^12; KAS/RVN/ERG 10^8 units). Order cost is
    computed with Decimal and rounded HALF_UP to integer cents.
    Positions and cash are DERIVED from filled orders only, never
    stored as balances.
  - Orders are append-only with idempotency (UNIQUE order_ref).
    Rejected orders are recorded too (status 'rejected',
    reject_reason set) so refusals are auditable. A duplicate
    order_ref raises (the original row is the audit trail).
  - Deposit slot (D-M22-4): Solana is the ONLY deposit network and
    USDC (SPL) is the ONLY deposit token — hard constants; the config
    loader rejects any other network/token value. The deposit address
    slot (config/trading.json deposit.address) is null until the user
    provides it; set_deposit_address validates a Solana address
    (base58, decodes to exactly 32 bytes). No key, seed phrase, or
    private key is accepted, stored, or handled anywhere here — the
    address is receive-only. Deposits never fund trading
    automatically: the engine never watches the chain and never
    credits a deposit on its own.
  - Confirmed USDC deposits (D-M22-5) are recorded ONLY through the
    explicit operator command record_deposit, with the Solana
    transaction signature (base58, 64 bytes) as evidence and the
    amount in integer micro-USDC, bound to the configured deposit
    address. scan_deposits is the explicit on-demand Solana check
    behind the site's "Accept deposit" button: it queries the Solana
    public RPC for recent USDC transfers to the configured address
    and records the confirmed ones. Automatic on-chain verification
    beyond that on-demand scan is NOT built — a fully automatic
    treasury watcher belongs to a future treasury design, which does
    not exist yet.

Usage (CLI; --db defaults to the live DB — tests MUST pass a temp DB):
    python3 core/atlas_trading.py status
    python3 core/atlas_trading.py export
    python3 core/atlas_trading.py eligible-capital
    python3 core/atlas_trading.py create-account --name <name>
        [--initial-virtual-cents <cents>]
    python3 core/atlas_trading.py place-order --account <id> --coin xmr
        --side buy|sell --qty <base-units> --ref <order-ref>
    python3 core/atlas_trading.py positions --account <id>
    python3 core/atlas_trading.py record-deposit --tx <signature>
        --amount-micro <micro-usdc>
    python3 core/atlas_trading.py scan-deposits [--limit N]
    python3 core/atlas_trading.py set-deposit-address --address <addr>
    python3 core/atlas_trading.py clear-deposit-address
    python3 core/atlas_trading.py fund-from-capital   # always refuses

Stdlib only. Portable by copying ~/workspace/atlas.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

BASE = os.path.expanduser("~/workspace/atlas")
CFG_ATLAS = os.path.join(BASE, "config", "atlas.json")
CFG_TRADING = os.path.join(BASE, "config", "trading.json")
DB = os.path.join(BASE, "data", "atlas.db")
EXPORT = os.path.join(BASE, "data", "trading.json")

FETCH_TIMEOUT_S = 10
STALE_AFTER_S = 3600
BUSY_TIMEOUT_MS = 5000
USER_AGENT = "ATLAS-trading/1.0"
COINGECKO_PRICE_URL = ("https://api.coingecko.com/api/v3/simple/price"
                       "?ids=monero,kaspa,ravencoin,ergo&vs_currencies=usd")

# D-M25: pump.fun paper-trading price source (read-only, public).
# pump.fun has no API-key trading; the engine prices pump.fun tokens
# from Dexscreener's public token API (no key, read-only) — the
# pump.fun frontend API is unreachable from the sandbox (empty reply).
# Prices are validated the same way as CoinGecko (positive finite
# only). Dexscreener returns the best Solana pair for the mint.
DEXSCREENER_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens/"
PUMP_COINS = {
    # symbol: Solana mint address. All mints verified on-chain via
    # getAccountInfo (exist, 6 decimals, mintAuthority None):
    # fiona/buttcoin 2026-11-20 ~18:40 EST (D-M25);
    # penny/chud/butthole/smoove 2026-11-20 ~22:56 EST (D-M26).
    "fiona": "B34nXKzCgsJb9ChLuSHPRpXLE3WFSWyeT8Cqkzzmpump",     # Fiona the Hippo
    "buttcoin": "Cm6fNnMk7NfzStP9CZpsQA2v3jjzbcYGAxdJySmHpump",  # Buttcoin
    "penny": "8fWsV1u1SYcN358tSA6dyTjfpmaQTziftcHwKBFSpump",     # The Last Penny
    "chud": "EV7J2QaPXPytSkM1LD9GPRkgAbmSEr9R3kYiXBzbpump",      # nothing ever happens
    "butthole": "BWkSWbiyfbw1Td5hFwQn7E4B7vTjgCcF96M25aiCpump",  # BUTTHOLE
    "smoove": "BSe1q3SL6KQPLeZHFG9nNw5VFbDL3ZXvBmtjBVpYpump",    # SMOOVE OFF
}

# D-M22-4: Solana is the ONLY deposit network; USDC (SPL) is the ONLY
# deposit token. These are hard constants — there is no parameter
# anywhere to select another network or token for deposits.
DEPOSIT_NETWORK = "Solana"
DEPOSIT_TOKEN = "USDC"
DEPOSIT_TOKEN_STANDARD = "SPL"
# The USDC SPL mint on Solana (public constant, from the wallet build).
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
# Solana program IDs (public constants). The Associated Token Program
# derives the wallet's USDC token account (ATA) from owner + mint.
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

COINS = ("xmr", "kas", "rvn", "erg", "fiona", "buttcoin",
         "penny", "chud", "butthole", "smoove")
COIN_LABELS = {"xmr": "XMR", "kas": "KAS", "rvn": "RVN", "erg": "ERG",
               "fiona": "FIONA", "buttcoin": "Buttcoin",
               "penny": "PENNY", "chud": "chud",
               "butthole": "BUTTHOLE", "smoove": "SMOOVE"}
COINGECKO_IDS = {"xmr": "monero", "kas": "kaspa", "rvn": "ravencoin",
                 "erg": "ergo"}
# Base-unit decimals per coin: XMR piconero (10^12), KAS/RVN/ERG 10^8,
# pump.fun tokens 10^6 (all six pump mints verified 6 decimals,
# D-M25/D-M26).
COIN_DECIMALS = {"xmr": 12, "kas": 8, "rvn": 8, "erg": 8,
                 "fiona": 6, "buttcoin": 6, "penny": 6, "chud": 6,
                 "butthole": 6, "smoove": 6}
# USDC has 6 decimals; deposits are recorded in whole USDC cents only
# (amount_micro % 10000 == 0) so the USD conversion is exact.
USDC_MICRO_PER_CENT = 10000

VIRTUAL_SOURCE = "virtual-simulation"
DEPOSIT_SOURCE = "solana-usdc"
DEFAULT_VIRTUAL_CENTS = 1000000   # $10,000 virtual
DEFAULT_FEE_BPS = 0

B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
B58_INDEX = {c: i for i, c in enumerate(B58_ALPHABET)}


class TradingError(ValueError):
    """Validation / safety refusal. Never carries a secret in its message."""


# ---------------------------------------------------------------------------
# Connection / config / audit
# ---------------------------------------------------------------------------

def connect(db_path=DB):
    """Open a connection with manual transaction control (autocommit mode),
    same pattern as atlas_coordinator.connect()."""
    con = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000.0)
    con.isolation_level = None
    con.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def load_configs():
    """Read both configs fresh on every call — never cached across passes.
    The trading config's deposit network/token are enforced here: any
    value other than Solana / USDC is refused (D-M22-4)."""
    with open(CFG_ATLAS) as f:
        atlas_cfg = json.load(f)
    with open(CFG_TRADING) as f:
        trading_cfg = json.load(f)
    deposit = trading_cfg.get("deposit") or {}
    if deposit.get("network") != DEPOSIT_NETWORK:
        raise TradingError(
            f"deposit network must be {DEPOSIT_NETWORK!r}, "
            f"got {deposit.get('network')!r}")
    if deposit.get("token") != DEPOSIT_TOKEN:
        raise TradingError(
            f"deposit token must be {DEPOSIT_TOKEN!r}, "
            f"got {deposit.get('token')!r}")
    return atlas_cfg, trading_cfg


def _now():
    return int(time.time())


def _log_decision(con, decision, reason):
    """Insert one audit row (dept='trading'). Does NOT commit; the
    caller owns the transaction. A decision without a reason is a failed
    audit entry — reason is required and must name the evidence."""
    if not reason:
        raise TradingError("log_decision requires a non-empty reason")
    con.execute(
        "INSERT INTO decisions (ts, dept, decision, reason) VALUES (?,?,?,?)",
        (_now(), "trading", decision, reason))


def _require_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TradingError(f"{name} must be an integer, got {value!r}")
    return value


# ---------------------------------------------------------------------------
# Base58 validation (Solana addresses and transaction signatures)
# ---------------------------------------------------------------------------

def _b58decode(text):
    """Base58 decode to bytes, or None when the text is not valid base58.
    Leading '1's decode to leading zero bytes (the standard rule)."""
    if not isinstance(text, str) or not text:
        return None
    num = 0
    for ch in text:
        digit = B58_INDEX.get(ch)
        if digit is None:
            return None
        num = num * 58 + digit
    raw = num.to_bytes((num.bit_length() + 7) // 8, "big") if num else b""
    pad = 0
    for ch in text:
        if ch != "1":
            break
        pad += 1
    return b"\x00" * pad + raw


def _b58encode(raw):
    """Base58 encode bytes (the inverse of _b58decode)."""
    num = int.from_bytes(raw, "big")
    out = ""
    while num:
        num, rem = divmod(num, 58)
        out = B58_ALPHABET[rem] + out
    pad = 0
    for byte in raw:
        if byte != 0:
            break
        pad += 1
    return "1" * pad + out


# ed25519 curve parameters for the program-derived-address check:
# -x^2 + y^2 = 1 + d x^2 y^2 (mod p), p = 2^255 - 19.
_ED25519_P = 2**255 - 19
_ED25519_D = (-121665 * pow(121666, _ED25519_P - 2, _ED25519_P)) % _ED25519_P


def _is_on_curve(addr_bytes):
    """True when the 32-byte encoding is a valid ed25519 curve point.
    A program-derived address (PDA) is, by definition, a 32-byte value
    that is NOT on the curve — the off-curve check is what makes a PDA
    a valid program address."""
    y = int.from_bytes(addr_bytes, "little") & ((1 << 255) - 1)
    y2 = (y * y) % _ED25519_P
    num = (y2 - 1) % _ED25519_P
    den = (_ED25519_D * y2 + 1) % _ED25519_P
    try:
        x2 = num * pow(den, _ED25519_P - 2, _ED25519_P) % _ED25519_P
    except ValueError:
        return False
    # sqrt mod p (p = 5 mod 8): x = x2^((p+3)//8); if that fails,
    # multiply by sqrt(-1) = 2^((p-1)//4) and check again.
    x = pow(x2, (_ED25519_P + 3) // 8, _ED25519_P)
    if (x * x - x2) % _ED25519_P != 0:
        x = x * pow(2, (_ED25519_P - 1) // 4, _ED25519_P) % _ED25519_P
    return (x * x - x2) % _ED25519_P == 0


def _find_program_address(seeds, program_id_bytes):
    """Program-derived address for `seeds` under `program_id_bytes`:
    sha256(seeds + bump + program_id + "ProgramDerivedAddress") for
    the first bump (255 down) whose result is off-curve. Returns
    (address_bytes, bump)."""
    for bump in range(255, -1, -1):
        data = (b"".join(seeds) + bytes([bump]) + program_id_bytes
                + b"ProgramDerivedAddress")
        address = hashlib.sha256(data).digest()
        if not _is_on_curve(address):
            return address, bump
    raise TradingError("no off-curve program-derived address found")


def derive_associated_token_account(owner_address):
    """Derive the USDC associated token account (ATA) for a wallet
    address: PDA of [owner, Token program, USDC mint] under the
    Associated Token Program. Pure computation — no RPC call, no
    secret, no key. Raises TradingError on an invalid owner address.
    Verified against the live on-chain ATA
    HAvmUB6eHZM2Z1NNbXXnpEvVqh4adB9pB49qHgdVwjdK (see tests)."""
    owner = _b58decode(owner_address)
    if owner is None or len(owner) != 32:
        raise TradingError(
            f"cannot derive token account: invalid owner address "
            f"{owner_address!r}")
    mint = _b58decode(USDC_MINT)
    token_program = _b58decode(TOKEN_PROGRAM_ID)
    associated_program = _b58decode(ASSOCIATED_TOKEN_PROGRAM_ID)
    address, _bump = _find_program_address(
        [owner, token_program, mint], associated_program)
    return _b58encode(address)


def validate_solana_address(address):
    """A Solana wallet address: base58, decodes to exactly 32 bytes.
    Returns (True, '') or (False, reason)."""
    if not isinstance(address, str) or not address:
        return False, "address must be a non-empty string"
    if not (32 <= len(address) <= 44):
        return False, (f"address length {len(address)} outside the "
                       "Solana 32–44 character range")
    decoded = _b58decode(address)
    if decoded is None:
        return False, "address is not valid base58"
    if len(decoded) != 32:
        return False, (f"address decodes to {len(decoded)} bytes, "
                       "a Solana address is 32 bytes")
    return True, ""


def validate_tx_signature(signature):
    """A Solana transaction signature: base58, decodes to exactly
    64 bytes. Returns (True, '') or (False, reason)."""
    if not isinstance(signature, str) or not signature:
        return False, "signature must be a non-empty string"
    if not (85 <= len(signature) <= 90):
        return False, (f"signature length {len(signature)} outside the "
                       "Solana 85–90 character range")
    decoded = _b58decode(signature)
    if decoded is None:
        return False, "signature is not valid base58"
    if len(decoded) != 64:
        return False, (f"signature decodes to {len(decoded)} bytes, "
                       "a Solana transaction signature is 64 bytes")
    return True, ""


# ---------------------------------------------------------------------------
# Deposit address slot (D-M22-4) — receive-only, no keys ever
# ---------------------------------------------------------------------------

def _atomic_write_json(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def get_deposit(trading_cfg=None):
    """The deposit block: network, token, address (or None), status."""
    if trading_cfg is None:
        _, trading_cfg = load_configs()
    deposit = trading_cfg.get("deposit") or {}
    return {
        "network": deposit.get("network"),
        "token": deposit.get("token"),
        "token_standard": deposit.get("token_standard"),
        "address": deposit.get("address"),
        "status": deposit.get("status"),
    }


def set_deposit_address(con, address):
    """Store the receive-only Solana deposit address. Validates the
    Solana address shape first; writes config/trading.json atomically;
    logs the decision. The address is public (receive-only) and safe
    to log. No key, seed phrase, or private key is ever accepted."""
    ok, reason = validate_solana_address(address)
    if not ok:
        raise TradingError(f"invalid Solana deposit address: {reason}")
    _, trading_cfg = load_configs()
    trading_cfg["deposit"]["address"] = address
    trading_cfg["deposit"]["status"] = "configured"
    _atomic_write_json(CFG_TRADING, trading_cfg)
    try:
        con.execute("BEGIN IMMEDIATE")
        _log_decision(con, "trading-deposit-address-set",
                      f"Solana {DEPOSIT_TOKEN} deposit address configured "
                      f"({address}); receive-only, no keys stored")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    return address


def clear_deposit_address(con):
    """Clear the deposit address slot back to null. Logs the decision."""
    _, trading_cfg = load_configs()
    trading_cfg["deposit"]["address"] = None
    trading_cfg["deposit"]["status"] = "address-pending"
    _atomic_write_json(CFG_TRADING, trading_cfg)
    try:
        con.execute("BEGIN IMMEDIATE")
        _log_decision(con, "trading-deposit-address-cleared",
                      "Solana deposit address slot cleared (address-pending)")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    return None


# ---------------------------------------------------------------------------
# Live pricing (D-M22-2) — fetch-with-fallback, never fabricated
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
    {coin: Decimal price or None} or None when the call itself fails."""
    try:
        data = _http_get_json(COINGECKO_PRICE_URL)
    except Exception:
        return None
    prices = {}
    for coin, cg_id in COINGECKO_IDS.items():
        entry = data.get(cg_id) or {}
        raw = entry.get("usd")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            prices[coin] = None
            continue
        try:
            price = Decimal(str(raw))
        except InvalidOperation:
            prices[coin] = None
            continue
        prices[coin] = price if price > 0 else None
    return prices


def _fetch_pump_price(coin):
    """Dexscreener public token API for one pump.fun coin (D-M25).
    Returns a Decimal price or None. Picks the first Solana pair whose
    base token is the coin's mint. Never raises, never fabricates."""
    mint = PUMP_COINS.get(coin)
    if not mint:
        return None
    try:
        data = _http_get_json(DEXSCREENER_TOKEN_URL + mint)
    except Exception:
        return None
    pairs = data.get("pairs")
    if not isinstance(pairs, list):
        return None
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        if pair.get("chainId") != "solana":
            continue
        base = pair.get("baseToken") or {}
        if base.get("address") != mint:
            continue
        raw = pair.get("priceUsd")
        if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
            continue
        try:
            price = Decimal(str(raw))
        except InvalidOperation:
            continue
        if price > 0:
            return price
    return None


def _read_price_row(con, coin):
    row = con.execute(
        "SELECT price_usd, source, fetched_at, stale FROM trading_prices "
        "WHERE coin = ?", (coin,)).fetchone()
    if row is None:
        return None
    return {"price_usd": Decimal(row["price_usd"]), "source": row["source"],
            "fetched_at": row["fetched_at"], "stale": bool(row["stale"])}


def _upsert_price(con, coin, price, source, fetched_at, stale):
    con.execute(
        """INSERT INTO trading_prices (coin, price_usd, source, fetched_at, stale)
           VALUES (?,?,?,?,?)
           ON CONFLICT(coin) DO UPDATE SET
             price_usd=excluded.price_usd, source=excluded.source,
             fetched_at=excluded.fetched_at, stale=excluded.stale""",
        (coin, str(price), source, fetched_at, 1 if stale else 0))


def get_price(con, coin, trading_cfg=None):
    """The price to execute at: fresh live price when fetchable, else
    the last recorded price marked stale (fetched_at preserved), else
    None when no price has ever been recorded. Returns a dict with
    price_usd (Decimal), source, fetched_at, stale — or None. Never
    raises, never fabricates. The price-row write happens in its own
    short transaction, never inside an order transaction."""
    if coin not in COINS:
        raise TradingError(f"unknown coin {coin!r}")
    if trading_cfg is None:
        _, trading_cfg = load_configs()
    stale_after = trading_cfg.get("price_stale_after_s", STALE_AFTER_S)
    now = _now()
    # D-M25: pump.fun coins price from Dexscreener (public, read-only);
    # the four original coins price from CoinGecko as before.
    if coin in PUMP_COINS:
        pump_price = _fetch_pump_price(coin)
        prices = {coin: pump_price} if pump_price is not None else None
        source = "Dexscreener token API (pump.fun, public)"
    else:
        prices = _fetch_prices()
        source = "CoinGecko simple/price"
    if prices is not None and prices.get(coin) is not None:
        price = prices[coin]
        try:
            con.execute("BEGIN IMMEDIATE")
            _upsert_price(con, coin, price, source, now, False)
            con.execute("COMMIT")
        except Exception:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
            raise
        return {"price_usd": price, "source": source,
                "fetched_at": now, "stale": False}
    # Fallback: last recorded price, marked stale with its fetched_at.
    row = _read_price_row(con, coin)
    if row is None:
        return None
    if not row["stale"]:
        try:
            con.execute("BEGIN IMMEDIATE")
            _upsert_price(con, coin, row["price_usd"], row["source"],
                          row["fetched_at"], True)
            con.execute("COMMIT")
        except Exception:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
            raise
        row["stale"] = True
    if now - row["fetched_at"] > stale_after:
        row["stale"] = True
    return row


# ---------------------------------------------------------------------------
# Funding rule v2 (D-M22-1, D-M22-5)
# ---------------------------------------------------------------------------

def eligible_capital(con, atlas_cfg=None):
    """Eligible capital in integer USD cents, with its two named
    sources. (1) Realized net mining profits from config/atlas.json
    (2) Confirmed USDC deposits on Solana from trading_deposits.
    Any other source has no representation and cannot contribute."""
    if atlas_cfg is None:
        atlas_cfg, _ = load_configs()
    mining_usd = atlas_cfg.get("trading", {}).get("eligible_capital_usd", 0)
    if isinstance(mining_usd, bool) or not isinstance(mining_usd, (int, float)):
        raise TradingError(
            f"eligible_capital_usd must be a number, got {mining_usd!r}")
    mining_cents = int((Decimal(str(mining_usd)) * 100).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP))
    deposits_cents = con.execute(
        "SELECT COALESCE(SUM(amount_usd_cents), 0) FROM trading_deposits "
        "WHERE status = 'confirmed'").fetchone()[0]
    return {"total_usd_cents": mining_cents + int(deposits_cents),
            "mining_profits_usd_cents": mining_cents,
            "usdc_deposits_usd_cents": int(deposits_cents)}


def fund_from_capital(con, account_id, amount_usd_cents):
    """ALWAYS refuses. Paper accounts are virtual-only by definition,
    and eligible capital can only fund live trading, which does not
    exist. The refusal is logged so the guard is auditable."""
    _require_int("amount_usd_cents", amount_usd_cents)
    try:
        con.execute("BEGIN IMMEDIATE")
        _log_decision(
            con, "trading-capital-funding-refused",
            f"refused to fund paper account {account_id} with "
            f"{amount_usd_cents} USD cents of eligible capital: paper "
            "accounts are virtual-only; eligible capital can only fund "
            "live trading, which does not exist (paper-only)")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    raise TradingError(
        "eligible capital cannot fund a paper account: paper accounts "
        "are virtual-only; live trading does not exist")


def record_deposit(con, tx_signature, amount_usdc_micro, note=None):
    """Record one CONFIRMED USDC deposit on Solana (D-M22-5). The
    recording IS the confirmation: an explicit operator action with
    the Solana transaction signature as evidence. Validates the
    signature shape (base58, 64 bytes), requires a positive amount,
    and binds the deposit to the CONFIGURED deposit address (refuses
    when none is configured). The USD conversion floors to whole
    cents (usd_cents = micro // 10000) and keeps the sub-cent
    remainder in remainder_micro — real transfers can carry sub-cent
    amounts, so they are recorded with their remainder, never
    silently dropped and never refused for it. Refuses duplicates
    and non-positive amounts. Logs the decision. Returns the
    deposit row."""
    ok, reason = validate_tx_signature(tx_signature)
    if not ok:
        raise TradingError(f"invalid transaction signature: {reason}")
    _require_int("amount_usdc_micro", amount_usdc_micro)
    if amount_usdc_micro <= 0:
        raise TradingError(
            f"amount_usdc_micro must be > 0, got {amount_usdc_micro}")
    _, trading_cfg = load_configs()
    deposit_address = (trading_cfg.get("deposit") or {}).get("address")
    if not deposit_address:
        raise TradingError(
            "cannot record a deposit: no Solana deposit address is "
            "configured (address-pending)")
    amount_usd_cents = amount_usdc_micro // USDC_MICRO_PER_CENT
    remainder_micro = amount_usdc_micro % USDC_MICRO_PER_CENT
    existing = con.execute(
        "SELECT id FROM trading_deposits WHERE tx_signature = ?",
        (tx_signature,)).fetchone()
    if existing is not None:
        raise TradingError(
            f"duplicate deposit: tx_signature already recorded "
            f"(deposit id {existing['id']})")
    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            """INSERT INTO trading_deposits
                   (tx_signature, deposit_address, amount_usdc_micro,
                    amount_usd_cents, remainder_micro, confirmed_at,
                    source, status, note)
               VALUES (?,?,?,?,?,?, 'solana-usdc','confirmed',?)""",
            (tx_signature, deposit_address, amount_usdc_micro,
             amount_usd_cents, remainder_micro, _now(), note))
        deposit_id = cur.lastrowid
        _log_decision(
            con, "trading-deposit-recorded",
            f"confirmed USDC deposit on Solana: {amount_usd_cents} USD "
            f"cents ({amount_usdc_micro} micro-USDC, remainder "
            f"{remainder_micro}) to {deposit_address}, tx {tx_signature}")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    return {"id": deposit_id, "tx_signature": tx_signature,
            "deposit_address": deposit_address,
            "amount_usdc_micro": amount_usdc_micro,
            "amount_usd_cents": amount_usd_cents,
            "remainder_micro": remainder_micro,
            "source": DEPOSIT_SOURCE, "status": "confirmed"}


# ---------------------------------------------------------------------------
# Solana deposit scan (D-M22-5) — the engine side of the site's
# "Accept deposit" button: an explicit on-demand check for new USDC
# transfers to the configured deposit address.
# ---------------------------------------------------------------------------

def _solana_rpc(method, params):
    """One JSON-RPC call to the Solana public RPC. Returns the result
    payload. Raises on any transport / HTTP / RPC error — the caller
    turns that into an error summary and records nothing."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1,
                       "method": method, "params": params}).encode("utf-8")
    req = urllib.request.Request(
        SOLANA_RPC_URL, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
        if resp.status != 200:
            raise urllib.error.HTTPError(SOLANA_RPC_URL, resp.status,
                                         "non-200", None, None)
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict) or "error" in data:
        raise ValueError(f"Solana RPC error: {data.get('error')}")
    return data.get("result")


def _usdc_delta_micro(tx, address):
    """Net micro-USDC received by `address` in one parsed transaction:
    sum over post-minus-pre token balances for the USDC mint owned by
    the address. Returns an int (<= 0 when no USDC arrived), or None
    when the transaction cannot be parsed (failed tx, missing meta)."""
    if not isinstance(tx, dict):
        return None
    meta = tx.get("meta")
    if not isinstance(meta, dict) or meta.get("err") is not None:
        return None
    pre = meta.get("preTokenBalances") or []
    post = meta.get("postTokenBalances") or []

    def _balances(rows):
        totals = {}
        for entry in rows:
            if not isinstance(entry, dict):
                continue
            if entry.get("mint") != USDC_MINT:
                continue
            if entry.get("owner") != address:
                continue
            amount = (entry.get("uiTokenAmount") or {}).get("amount")
            try:
                value = int(str(amount))
            except (TypeError, ValueError):
                continue
            key = entry.get("accountIndex")
            totals[key] = totals.get(key, 0) + value
        return totals

    pre_totals = _balances(pre)
    post_totals = _balances(post)
    delta = 0
    for key, post_value in post_totals.items():
        delta += post_value - pre_totals.get(key, 0)
    return delta


def scan_deposits(con, limit=10):
    """Check Solana for new USDC transfers to the configured deposit
    address and record the confirmed ones (D-M22-5). Explicit and
    on-demand: fetches recent signatures for the address, fetches
    each unrecorded transaction parsed, and records a positive USDC
    delta via record_deposit (signature as evidence). Failed
    transactions and transactions with no USDC delta are skipped. An
    RPC failure returns an error summary and records NOTHING — never
    fabricates. Returns a summary dict. Raises only when no deposit
    address is configured (the scan has no address to check).
    MISSION 24 FIX (deposit-scan blind spot, 2026-11-20): the scan
    queries signatures for BOTH the wallet address AND its USDC
    associated token account (ATA). A plain USDC transfer touches
    only the token account, not the wallet, so a wallet-only query
    misses every transfer after the first (the first only showed up
    because it created the ATA) — that is why the second deposit
    (landed 2026-11-20 17:53, 4.78776 USDC) was wrongly reported
    missing for ~30 minutes. The ATA is derived locally from owner +
    USDC mint (derive_associated_token_account); the delta check
    already keys on the token-account owner, so it is unchanged."""
    _require_int("limit", limit)
    if limit <= 0 or limit > 50:
        raise TradingError(f"scan limit must be 1..50, got {limit}")
    _, trading_cfg = load_configs()
    address = (trading_cfg.get("deposit") or {}).get("address")
    if not address:
        raise TradingError(
            "cannot scan for deposits: no Solana deposit address is "
            "configured (address-pending)")
    summary = {"address": address, "checked": 0, "new": [],
               "skipped": 0, "errors": []}
    ata = derive_associated_token_account(address)
    summary["token_account"] = ata
    seen = set()
    entries = []
    for queried in (address, ata):
        try:
            signatures = _solana_rpc(
                "getSignaturesForAddress", [queried, {"limit": limit}])
        except Exception as exc:
            summary["errors"].append(
                f"getSignaturesForAddress {queried[:12]}... failed: {exc}")
            continue
        if not isinstance(signatures, list):
            summary["errors"].append(
                "getSignaturesForAddress returned an unexpected shape")
            continue
        for entry in signatures:
            signature = (entry or {}).get("signature")
            if isinstance(signature, str) and signature not in seen:
                seen.add(signature)
                entries.append(entry)
    for entry in entries:
        signature = (entry or {}).get("signature")
        if not isinstance(signature, str):
            summary["skipped"] += 1
            continue
        summary["checked"] += 1
        known = con.execute(
            "SELECT id FROM trading_deposits WHERE tx_signature = ?",
            (signature,)).fetchone()
        if known is not None:
            summary["skipped"] += 1
            continue
        try:
            tx = _solana_rpc("getTransaction", [
                signature, {"encoding": "jsonParsed",
                            "maxSupportedTransactionVersion": 0}])
        except Exception as exc:
            summary["errors"].append(
                f"getTransaction {signature[:12]}... failed: {exc}")
            continue
        delta = _usdc_delta_micro(tx, address)
        if delta is None or delta <= 0:
            summary["skipped"] += 1
            continue
        try:
            dep = record_deposit(
                con, signature, delta,
                note=f"solana-scan: USDC transfer to {address}")
        except TradingError as exc:
            summary["errors"].append(
                f"record {signature[:12]}... refused: {exc}")
            continue
        summary["new"].append({
            "tx_signature": signature,
            "amount_usdc_micro": dep["amount_usdc_micro"],
            "amount_usd_cents": dep["amount_usd_cents"]})
    return summary


# ---------------------------------------------------------------------------
# Paper accounts and orders (D-M22-1, D-M22-3)
# ---------------------------------------------------------------------------

def create_account(con, name, initial_virtual_usd_cents=None,
                   source= VIRTUAL_SOURCE):
    """Create a paper account. The funding source must be exactly
    'virtual-simulation' — any other source is refused, because only
    virtual funds may back a paper account. Logs the decision."""
    if not isinstance(name, str) or not name.strip():
        raise TradingError("account name must be a non-empty string")
    if source != VIRTUAL_SOURCE:
        raise TradingError(
            f"paper account source must be {VIRTUAL_SOURCE!r}, got "
            f"{source!r}: only virtual funds may back a paper account")
    _, trading_cfg = load_configs()
    if initial_virtual_usd_cents is None:
        initial_virtual_usd_cents = int(
            trading_cfg.get("virtual_starting_balance_usd_cents",
                            DEFAULT_VIRTUAL_CENTS))
    _require_int("initial_virtual_usd_cents", initial_virtual_usd_cents)
    if initial_virtual_usd_cents < 0:
        raise TradingError(
            "initial_virtual_usd_cents must be >= 0, got "
            f"{initial_virtual_usd_cents}")
    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            """INSERT INTO trading_accounts
                   (name, mode, initial_virtual_usd_cents, source, status, created_at)
               VALUES (?, 'paper', ?, 'virtual-simulation', 'active', ?)""",
            (name.strip(), initial_virtual_usd_cents, _now()))
        account_id = cur.lastrowid
        _log_decision(
            con, "trading-account-created",
            f"paper account {account_id} {name.strip()!r} created with "
            f"{initial_virtual_usd_cents} virtual USD cents "
            f"(source {VIRTUAL_SOURCE}; not capital, not withdrawable)")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    return {"id": account_id, "name": name.strip(), "mode": "paper",
            "initial_virtual_usd_cents": initial_virtual_usd_cents,
            "source": VIRTUAL_SOURCE, "status": "active"}


def _get_account(con, account_id):
    row = con.execute(
        "SELECT * FROM trading_accounts WHERE id = ?",
        (account_id,)).fetchone()
    if row is None:
        raise TradingError(f"unknown paper account id {account_id}")
    return row


def cash_balance_cents(con, account_id):
    """Virtual cash, DERIVED from filled orders only: initial virtual
    − Σ buy costs − Σ fees + Σ sell proceeds. Never stored."""
    account = _get_account(con, account_id)
    spent = con.execute(
        "SELECT COALESCE(SUM(cost_usd_cents + fee_usd_cents), 0) "
        "FROM trading_orders WHERE account_id = ? AND side = 'buy' "
        "AND status = 'filled'", (account_id,)).fetchone()[0]
    received = con.execute(
        "SELECT COALESCE(SUM(cost_usd_cents - fee_usd_cents), 0) "
        "FROM trading_orders WHERE account_id = ? AND side = 'sell' "
        "AND status = 'filled'", (account_id,)).fetchone()[0]
    return int(account["initial_virtual_usd_cents"]) - int(spent) + int(received)


def positions(con, account_id):
    """Holdings per coin, DERIVED from filled orders only (buys minus
    sells, base units). Only nonzero positions are returned."""
    _get_account(con, account_id)
    held = {}
    for row in con.execute(
            "SELECT coin, side, qty_base_units FROM trading_orders "
            "WHERE account_id = ? AND status = 'filled'",
            (account_id,)).fetchall():
        qty = int(row["qty_base_units"])
        held[row["coin"]] = held.get(row["coin"], 0) + (
            qty if row["side"] == "buy" else -qty)
    return {coin: qty for coin, qty in held.items() if qty != 0}


def _order_cost_cents(qty_base_units, price_usd, coin):
    """Exact integer-cent cost of qty at price: qty * price * 100 /
    10^decimals, rounded HALF_UP. price_usd is a Decimal."""
    raw = (Decimal(qty_base_units) * price_usd * 100
           / Decimal(10 ** COIN_DECIMALS[coin]))
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _fee_cents(cost_cents, fee_bps):
    """Fee, floored (same integer rule as the rewards engine)."""
    return cost_cents * fee_bps // 10000


def place_order(con, account_id, coin, side, qty_base_units, order_ref,
                mode="paper", note=None):
    """Place one paper order at the live price. Validation refusals
    (insufficient virtual cash / holdings, no price) are RECORDED as
    rejected rows with a reason and a logged decision — they are
    auditable, not silent. A duplicate order_ref raises TradingError
    (the original row is the audit trail). Network I/O (price fetch)
    happens BEFORE the transaction opens, never while holding the DB
    lock. Returns the order row dict."""
    if mode != "paper":
        raise TradingError(
            f"trading mode must be 'paper', got {mode!r}: no live mode exists")
    account = _get_account(con, account_id)
    if account["status"] != "active":
        raise TradingError(
            f"paper account {account_id} is not active "
            f"(status {account['status']!r})")
    if coin not in COINS:
        raise TradingError(f"unknown coin {coin!r}")
    if side not in ("buy", "sell"):
        raise TradingError(f"side must be 'buy' or 'sell', got {side!r}")
    _require_int("qty_base_units", qty_base_units)
    if qty_base_units <= 0:
        raise TradingError(
            f"qty_base_units must be > 0, got {qty_base_units}")
    if not isinstance(order_ref, str) or not order_ref.strip():
        raise TradingError("order_ref must be a non-empty string")
    order_ref = order_ref.strip()
    existing = con.execute(
        "SELECT id FROM trading_orders WHERE order_ref = ?",
        (order_ref,)).fetchone()
    if existing is not None:
        raise TradingError(
            f"duplicate order_ref {order_ref!r} (order id {existing['id']})")

    _, trading_cfg = load_configs()
    fee_bps = int(trading_cfg.get("fee_bps", DEFAULT_FEE_BPS))
    price = get_price(con, coin, trading_cfg)

    def _reject(reason):
        try:
            con.execute("BEGIN IMMEDIATE")
            cur = con.execute(
                """INSERT INTO trading_orders
                       (account_id, order_ref, ts, coin, side, qty_base_units,
                        price_usd, price_source, price_fetched_at, price_stale,
                        cost_usd_cents, fee_usd_cents, status, reject_reason,
                        mode, note)
                   VALUES (?,?,?, ?,?,?, ?,?,?,?, NULL, 0,
                           'rejected', ?, 'paper', ?)""",
                (account_id, order_ref, _now(), coin, side,
                 qty_base_units,
                 str(price["price_usd"]) if price else None,
                 price["source"] if price else None,
                 price["fetched_at"] if price else None,
                 1 if price and price["stale"] else 0,
                 reason, note))
            order_id = cur.lastrowid
            _log_decision(
                con, "trading-order-rejected",
                f"paper order {order_ref!r} rejected ({coin} {side} "
                f"{qty_base_units} base units): {reason}")
            con.execute("COMMIT")
        except Exception:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
            raise
        return {"id": order_id, "account_id": account_id,
                "order_ref": order_ref, "coin": coin, "side": side,
                "qty_base_units": qty_base_units, "status": "rejected",
                "reject_reason": reason, "mode": "paper"}

    if price is None:
        return _reject("no-live-price: no price ever recorded for "
                       f"{COIN_LABELS[coin]} and the live fetch failed")
    cost_cents = _order_cost_cents(qty_base_units, price["price_usd"], coin)
    fee_cents = _fee_cents(cost_cents, fee_bps)
    if side == "buy":
        if cost_cents + fee_cents > cash_balance_cents(con, account_id):
            return _reject(
                "insufficient-virtual-funds: buy costs "
                f"{cost_cents + fee_cents} virtual USD cents, cash is "
                f"{cash_balance_cents(con, account_id)}")
    else:
        held = positions(con, account_id).get(coin, 0)
        if qty_base_units > held:
            return _reject(
                "insufficient-holdings: sell asks for "
                f"{qty_base_units} base units of {COIN_LABELS[coin]}, "
                f"holdings are {held}")
    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            """INSERT INTO trading_orders
                   (account_id, order_ref, ts, coin, side, qty_base_units,
                    price_usd, price_source, price_fetched_at, price_stale,
                    cost_usd_cents, fee_usd_cents, status, reject_reason,
                    mode, note)
               VALUES (?,?,?, ?,?,?, ?,?,?,?, ?,?, 'filled', NULL,
                       'paper', ?)""",
            (account_id, order_ref, _now(), coin, side, qty_base_units,
             str(price["price_usd"]), price["source"],
             price["fetched_at"], 1 if price["stale"] else 0,
             cost_cents, fee_cents, note))
        order_id = cur.lastrowid
        _log_decision(
            con, "trading-order-filled",
            f"paper order {order_ref!r} filled ({coin} {side} "
            f"{qty_base_units} base units at ${price['price_usd']} "
            f"[{price['source']}, fetched_at {price['fetched_at']}"
            f"{', STALE' if price['stale'] else ''}]; cost "
            f"{cost_cents} virtual USD cents, fee {fee_cents})")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    return {"id": order_id, "account_id": account_id,
            "order_ref": order_ref, "coin": coin, "side": side,
            "qty_base_units": qty_base_units,
            "price_usd": str(price["price_usd"]),
            "price_source": price["source"],
            "price_fetched_at": price["fetched_at"],
            "price_stale": price["stale"],
            "cost_usd_cents": cost_cents, "fee_usd_cents": fee_cents,
            "status": "filled", "mode": "paper"}


# ---------------------------------------------------------------------------
# Export / status
# ---------------------------------------------------------------------------

def _atomic_write_json(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def portfolio(con, account_id, trading_cfg=None):
    """Mark-to-market value of one paper account at the last recorded
    prices (fresh or stale, labeled). Returns cash, per-coin holdings
    with values, total value, and the price freshness per coin."""
    if trading_cfg is None:
        _, trading_cfg = load_configs()
    held = positions(con, account_id)
    cash = cash_balance_cents(con, account_id)
    coin_rows = []
    total = cash
    for coin, qty in sorted(held.items()):
        row = _read_price_row(con, coin)
        if row is None:
            value_cents = None
        else:
            value_cents = _order_cost_cents(qty, row["price_usd"], coin)
            total += value_cents
        coin_rows.append({
            "coin": coin, "qty_base_units": qty,
            "value_usd_cents": value_cents,
            "price_usd": str(row["price_usd"]) if row else None,
            "price_fetched_at": row["fetched_at"] if row else None,
            "price_stale": bool(row["stale"]) if row else None,
        })
    return {"account_id": account_id, "cash_usd_cents": cash,
            "positions": coin_rows, "total_usd_cents": total}


def export_trading_json(con=None, db_path=DB, export_path=EXPORT):
    """Build data/trading.json. Refreshes live prices first (fallback
    to last recorded, stale-flagged — the export never fails on a
    fetch). The export writes no ledger/decision rows. Atomic write."""
    atlas_cfg, trading_cfg = load_configs()
    own_con = con is None
    if own_con:
        con = connect(db_path)
    try:
        # Refresh prices (best effort; failures fall back to recorded).
        for coin in COINS:
            try:
                get_price(con, coin, trading_cfg)
            except Exception:
                pass
        capital = eligible_capital(con, atlas_cfg)
        accounts = []
        for row in con.execute(
                "SELECT * FROM trading_accounts ORDER BY id").fetchall():
            accounts.append({
                "id": row["id"], "name": row["name"], "mode": row["mode"],
                "initial_virtual_usd_cents": row["initial_virtual_usd_cents"],
                "source": row["source"], "status": row["status"],
                "created_at": row["created_at"],
                "portfolio": portfolio(con, row["id"], trading_cfg),
            })
        orders = []
        for row in con.execute(
                "SELECT * FROM trading_orders ORDER BY id DESC LIMIT 50"
                ).fetchall():
            orders.append({k: row[k] for k in row.keys()})
        deposits = []
        for row in con.execute(
                "SELECT * FROM trading_deposits ORDER BY id").fetchall():
            deposits.append({k: row[k] for k in row.keys()})
        prices = []
        for coin in COINS:
            row = _read_price_row(con, coin)
            prices.append({
                "coin": coin,
                "price_usd": str(row["price_usd"]) if row else None,
                "source": row["source"] if row else None,
                "fetched_at": row["fetched_at"] if row else None,
                "stale": bool(row["stale"]) if row else None,
            })
        payload = {
            "exported_at": _now(),
            "mode": "paper-only",
            "emergency_stop": bool(atlas_cfg.get("emergency_stop")),
            "eligible_capital_usd_cents": capital["total_usd_cents"],
            "eligible_capital_sources": {
                "mining_profits_usd_cents":
                    capital["mining_profits_usd_cents"],
                "usdc_deposits_solana_usd_cents":
                    capital["usdc_deposits_usd_cents"],
            },
            "funding_rule": ("eligible capital = realized net mining "
                             "profits + confirmed USDC deposits on "
                             "Solana only"),
            "deposit": get_deposit(trading_cfg),
            "accounts": accounts,
            "recent_orders": orders,
            "deposits": deposits,
            "prices": prices,
        }
        _atomic_write_json(export_path, payload)
        return payload
    finally:
        if own_con:
            con.close()


def status(db_path=DB):
    """Print the paper-trading state: mode, eligible capital and its
    two sources, the deposit slot, and every paper account."""
    atlas_cfg, trading_cfg = load_configs()
    con = connect(db_path)
    try:
        capital = eligible_capital(con, atlas_cfg)
        deposit = get_deposit(trading_cfg)
        print("ATLAS PAPER TRADING — mode paper-only (simulation only)")
        print(f"Emergency stop: {'ON' if atlas_cfg.get('emergency_stop') else 'OFF'}")
        print(f"Eligible capital: ${capital['total_usd_cents'] / 100:.2f} "
              f"(mining profits ${capital['mining_profits_usd_cents'] / 100:.2f} "
              f"+ confirmed USDC deposits on Solana "
              f"${capital['usdc_deposits_usd_cents'] / 100:.2f})")
        addr = deposit["address"] or "not configured — address owed from user"
        print(f"Deposit: {deposit['network']} / {deposit['token']} "
              f"({deposit['token_standard']}) — {addr}")
        rows = con.execute(
            "SELECT * FROM trading_accounts ORDER BY id").fetchall()
        if not rows:
            print("No paper accounts yet.")
        for row in rows:
            cash = cash_balance_cents(con, row["id"])
            held = positions(con, row["id"])
            print(f"  account {row['id']} {row['name']!r}: virtual cash "
                  f"${cash / 100:.2f} of "
                  f"${row['initial_virtual_usd_cents'] / 100:.2f} virtual; "
                  f"positions {held or 'none'}")
    finally:
        con.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="ATLAS paper-trading engine")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("export")
    sub.add_parser("eligible-capital")
    p = sub.add_parser("create-account")
    p.add_argument("--name", required=True)
    p.add_argument("--initial-virtual-cents", type=int, default=None)
    p = sub.add_parser("place-order")
    p.add_argument("--account", type=int, required=True)
    p.add_argument("--coin", required=True, choices=list(COINS))
    p.add_argument("--side", required=True, choices=["buy", "sell"])
    p.add_argument("--qty", type=int, required=True)
    p.add_argument("--ref", required=True)
    p = sub.add_parser("positions")
    p.add_argument("--account", type=int, required=True)
    p = sub.add_parser("record-deposit")
    p.add_argument("--tx", required=True)
    p.add_argument("--amount-micro", type=int, required=True)
    p.add_argument("--note", default=None)
    p = sub.add_parser("scan-deposits")
    p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("set-deposit-address")
    p.add_argument("--address", required=True)
    sub.add_parser("clear-deposit-address")
    p = sub.add_parser("fund-from-capital")
    p.add_argument("--account", type=int, required=True)
    p.add_argument("--amount-cents", type=int, required=True)
    args = parser.parse_args(argv)
    con = connect()
    try:
        if args.cmd == "status":
            status()
        elif args.cmd == "export":
            payload = export_trading_json(con=con)
            print(f"trading export written: {EXPORT} "
                  f"(exported_at {payload['exported_at']})")
        elif args.cmd == "eligible-capital":
            capital = eligible_capital(con)
            print(f"eligible capital: ${capital['total_usd_cents'] / 100:.2f} "
                  f"(mining profits "
                  f"${capital['mining_profits_usd_cents'] / 100:.2f} + "
                  f"confirmed USDC deposits on Solana "
                  f"${capital['usdc_deposits_usd_cents'] / 100:.2f})")
        elif args.cmd == "create-account":
            acc = create_account(con, args.name,
                                 args.initial_virtual_cents)
            print(f"paper account {acc['id']} {acc['name']!r} created: "
                  f"${acc['initial_virtual_usd_cents'] / 100:.2f} virtual")
        elif args.cmd == "place-order":
            order = place_order(con, args.account, args.coin, args.side,
                                args.qty, args.ref)
            if order["status"] == "filled":
                print(f"filled: {order['coin']} {order['side']} "
                      f"{order['qty_base_units']} base units at "
                      f"${order['price_usd']} — cost "
                      f"{order['cost_usd_cents']} virtual USD cents")
            else:
                print(f"rejected: {order['reject_reason']}")
        elif args.cmd == "positions":
            held = positions(con, args.account)
            print(f"account {args.account} positions: {held or 'none'}; "
                  f"virtual cash "
                  f"${cash_balance_cents(con, args.account) / 100:.2f}")
        elif args.cmd == "record-deposit":
            dep = record_deposit(con, args.tx, args.amount_micro,
                                 args.note)
            print(f"confirmed USDC deposit on Solana recorded: "
                  f"${dep['amount_usd_cents'] / 100:.2f} "
                  f"(tx {dep['tx_signature'][:12]}...)")
        elif args.cmd == "scan-deposits":
            summary = scan_deposits(con, args.limit)
            print(f"deposit scan for {summary['address']}: "
                  f"checked {summary['checked']}, "
                  f"new {len(summary['new'])}, "
                  f"skipped {summary['skipped']}")
            for dep in summary["new"]:
                print(f"  recorded: ${dep['amount_usd_cents'] / 100:.2f} "
                      f"(tx {dep['tx_signature'][:12]}...)")
            for err in summary["errors"]:
                print(f"  error: {err}")
        elif args.cmd == "set-deposit-address":
            set_deposit_address(con, args.address)
            print("Solana USDC deposit address configured (receive-only).")
        elif args.cmd == "clear-deposit-address":
            clear_deposit_address(con)
            print("Deposit address slot cleared (address-pending).")
        elif args.cmd == "fund-from-capital":
            try:
                fund_from_capital(con, args.account, args.amount_cents)
            except TradingError as exc:
                print(f"refused: {exc}")
                return 3
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
