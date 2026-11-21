# ATLAS Master Mission 3 — Monero Address Validation Spec (Lane B, research only)

**Lane:** B (research + specification) — read-only. No artifact edited, no wallet created, no keys generated.
**Checked:** 2026-11-18, ~02:55 EST.
**Companion doc:** `master-mission3-getmonero-findings.md` (Lane A — wallet downloads, onboarding copy). This spec covers ONLY address validation rules and the ownership-verification verdict. It does not repeat Lane A's wallet list.
**Status note:** ATLAS safety state unchanged — emergency stop ACTIVE, mining DISABLED, trading PAPER ONLY, capital $0. This spec changes nothing about that.

---

## 1. Validation rules — exact

### 1a. The three address types (mainnet)

| Type | Network byte | Encoded length | First char (mainnet) | Raw payload | Use |
|---|---|---|---|---|---|
| Standard (primary) | 18 (0x12) | **95** | `4` | 69 bytes: 1 network + 32 spend pubkey + 32 view pubkey + 4 checksum | Default receiving address |
| Integrated | 19 (0x13) | **106** | `4` | 77 bytes: 1 network + 32 spend pubkey + 32 view pubkey + 8 payment ID + 4 checksum | Standard address + embedded 8-byte (64-bit) encrypted payment ID; mostly exchanges |
| Subaddress | 42 (0x2A) | **95** | `8` | 69 bytes: 1 network + 32 derived spend pubkey + 32 derived view pubkey + 4 checksum | One fresh address per payer; not linkable to the primary address on-chain |

Sources: getmonero.org Moneropedia "Address" (fetched live 2026-11-18: raw address is 95 chars starting with `4` or `8`; integrated is 106 chars; address = public spend key + public view key, network byte 18, suffixed with first 4 bytes of the Keccak-256 hash as checksum); monero-oxide address docs (network bytes 18/19/42 mainnet); MoneroHelp address validator (standard `4`/95, subaddress `8`/95, integrated `4`/106).

### 1b. Other networks (reject for ATLAS payouts)

| Network | Standard | Integrated | Subaddress |
|---|---|---|---|
| Mainnet | 18 → `4` | 19 → `4` | 42 → `8` |
| Testnet | 53 → `9` | 54 → `9` | 63 → `B` |
| Stagenet | 24 | 25 | 36 |

ATLAS is a mainnet system. **Accept mainnet only.** Testnet/stagenet addresses must be rejected with "not a mainnet address", not silently accepted. Stagenet first characters were not verified from a source — validate stagenet/testnet by decoded network byte, never by first character alone.

### 1c. Base58 alphabet (exact, 58 chars)

```
123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
```

Excluded characters: `0` (zero), `O` (capital o), `I` (capital i), `l` (lowercase L). Any of those four in the input = invalid, full stop.

### 1d. Monero Base58 is NOT Bitcoin Base58 — block encoding

Monero encodes in fixed **8-byte blocks → exactly 11 Base58 characters** each; a short block is left-padded with `1`s (`1` = zero in Base58). The final partial block is padded only to the maximum length for its byte count.

- 69-byte payload = 8 full blocks (64 bytes) + 1 block of 5 bytes → 8×11 + 7 = **95 chars**.
- 77-byte payload = 9 full blocks (72 bytes) + 1 block of 5 bytes → 9×11 + 7 = **106 chars**.

Consequence: **a plain Base58 decode (e.g. Bitcoin's) will give the wrong bytes.** Any validation code must use Monero block-wise Base58, or a vetted Monero library. Do not hand-roll a generic Base58 decoder and call it validation.

### 1e. Checksum — feasible client-side, with one hard requirement

- The last 4 bytes of the decoded payload are a checksum = **first 4 bytes of Keccak-256** computed over all preceding bytes (network byte + keys [+ payment ID]).
- **Keccak-256 is the original Keccak, NOT NIST SHA3-256.** The two differ (different padding). Using a SHA3-256 function will produce the wrong checksum and reject every valid address. The implementation must use a Keccak-256 (pre-standardisation) primitive — e.g. `keccak_256` from js-sha3, or noble-hashes `keccak_256`. Verify the library exposes Keccak, not only SHA3.
- **Feasibility: YES, fully client-side, no network, no node, no wallet needed.** Decode Monero Base58 → check decoded length (69 or 77) → recompute Keccak-256 over payload-minus-last-4 → compare first 4 bytes. A single wrong character passes length/charset checks but fails the checksum, which is the whole point of it.

### 1f. Validation algorithm (ordered — fail fast, in this order)

1. Trim leading/trailing whitespace. Reject empty input.
2. Length must be exactly **95 or 106**. Anything else → "not a Monero address length".
3. Every character must be in the Monero Base58 alphabet (§1c). Reject `0`, `O`, `I`, `l` explicitly in the error text.
4. First character + length must be consistent: 95 chars → first char `4` (standard) or `8` (subaddress); 106 chars → first char `4` (integrated). Anything else → "not a mainnet Monero address" (covers testnet `9`/`B` starts).
5. Monero block-wise Base58 decode. Decoded length must be 69 bytes (95-char input) or 77 bytes (106-char input).
6. Decoded network byte must be 18, 19, or 42 (mainnet), consistent with the length/type: 18↔95, 42↔95, 19↔106. Any other byte (53/54/63 testnet, 24/25/36 stagenet) → reject as non-mainnet.
7. Recompute Keccak-256 over all decoded bytes except the last 4; the first 4 bytes of the hash must equal the last 4 decoded bytes. Mismatch → "checksum failed — check for a typo, do not send to this address".
8. Only if all 7 pass: accept, and record the detected type (standard / integrated / subaddress).

A regex + length check alone is **not** validation — it is step 2–4 only. The checksum (step 7) is mandatory; without it a typo'd address would be stored as valid.

### 1g. What validation does NOT prove

- It does **not** prove the address belongs to the person who pasted it. Anyone can paste anyone else's valid address. Format + checksum only prove the string is a well-formed mainnet address.
- It does **not** prove the address is spendable, funded, or even generated by a real wallet (a well-formed address can be constructed from arbitrary keys).
- It does **not** detect a correctly-formed address that belongs to a scammer. No address check substitutes for "confirm the address with the owner through a trusted channel".

### 1h. Integrated-address handling for ATLAS

- Accept integrated addresses (they are valid mainnet addresses), but **the embedded 8-byte payment ID is ignored by ATLAS** — Mission 3 has no payment-ID handling, and mining payouts do not need one.
- Recommend in UI copy: standard or subaddress preferred for payouts; subaddress preferred for privacy (one fresh subaddress per use). Do not force a type — a user whose wallet only shows the primary address must not be blocked.

### 1i. Correction to Lane A §6e

Lane A's draft says a receiving address "starts with the number 4" and "is 95 characters long and starts with 4". That is incomplete: **subaddresses start with `8` (95 chars) and integrated addresses are 106 chars (start with `4`)**. The Wallet Center copy must say "95 characters starting with 4 or 8 — or 106 characters for an integrated address" or users with subaddresses will think they copied the wrong thing. Flag for the build lane; Lane A's file itself is not edited here.

---

## 2. Ownership verification — verdict

### 2a. Verdict (one line)

**Monero DOES have a Bitcoin-style message-signing scheme — signing proves control of an address without revealing any private key — but verifying a signature needs a real Monero implementation, so it is an optional Phase-2 feature, not part of address onboarding.**

### 2b. What exists (verified from multiple independent sources)

Monero wallets can sign an arbitrary message with the private key behind an address, and anyone can verify that signature using only the message, the address, and the signature — no seed, no private spend key, no private view key ever leaves the signer's wallet, and signing moves no funds.

- **monero-wallet-cli:** `sign <file>` / `sign <account>,<subaddress>`-style commands and `verify <filename> <address> <signature>` (command list visible in the CLI's own help output). Community reference (keys.agntn.dev, tested against monero-wallet-cli/rpc 0.18.5.3): `sign` writes SigV2 signatures; `verify` checks SigV1 and SigV2.
- **Monero GUI Wallet:** Advanced mode → Sign/verify tab — sign a message or file, verify with message + signer address + signature; a pop-up reports valid/invalid (monero-ecosystem GUI guide, §"Sign - verify Message").
- **Programmatic:** monero-ts / monero-javascript `signMessage(message, signatureType, accountIdx, subaddressIdx)` and `verifyMessage(message, address, signature)`; monero-cpp `sign_message` / `check_*_proof` equivalents.
- **Signature formats:** SigV1 (legacy — hashes the bare message) and SigV2 (current — hashes a tagged `MoneroMessageSignature` structure including both public keys, which key signed, and the message, so a view-key signature cannot pose as a spend-key signature). Both still verify.
- **Spend key vs view key:** signing can be done with the spend key (default, proves control/spend authority) or the view key (`sign --view`). A view-key signature proves view access only, **not** spend control. Any verification flow must require — and check — a **spend-key** signature.

### 2c. What this means for ATLAS (honest assessment)

| Claim | True? |
|---|---|
| Format + checksum validation proves an address is well-formed | Yes — §1, client-side, no keys |
| Message signing proves control of an address without revealing seed/spend key/view key | **Yes — verified, exists** |
| ATLAS can verify a pasted signature with a regex or a few lines of JS | **No** — verification needs Ed25519/Schnorr verification over Monero's SigV1/SigV2 scheme (monero-ts, monero-javascript, or wallet RPC/CLI). It is a library dependency, not a string check |
| A user can prove ownership from inside the Wallet Center alone | **No** — the user must sign in their own wallet (GUI Sign/verify tab or CLI `sign`) and paste the signature back. ATLAS can only issue the challenge and verify the result |
| A small test transaction proves ownership | **No — do not present it as a verification method.** It costs a fee, proves only that someone sent funds (not that the claimant controls the destination), and is irreversible. No source supports it as an ownership check |
| Sharing a private view key proves ownership | It proves view access, but it is a large privacy disclosure (exposes incoming transaction history) and must never be requested. Message signing is the correct tool |
| Signing proves the signer's real-world identity | **No** — it proves control of the key at signing time, nothing about who the person is |
| Signing proves a balance | **No** — separate reserve proofs (`get_reserve_proof`) exist for balance; out of scope for Mission 3 |

### 2d. Recommended implementation (address-only now, signing as optional Phase 2)

**Mission 3 (build now):**
1. Address-only onboarding. Store only the address string (existing `setMiningWallet` action). Never request, accept, or store a seed phrase, private spend key, private view key, password, or signature.
2. Implement §1f validation in full, including the Keccak-256 checksum (step 7). A length/charset-only check is not acceptable.
3. Label every stored address honestly: **"Format valid — ownership not verified."** Never display a checkmark, "verified" badge, or "confirmed" label for an address that only passed format checks.
4. Accept standard, integrated, and subaddress mainnet addresses; reject testnet/stagenet; fix Lane A §6e copy per §1i.

**Optional Phase 2 (only if the user orders it — do NOT build silently):**
1. Challenge–response signing: ATLAS issues a fresh one-time challenge (e.g. `ATLAS ownership proof <address> <nonce> <timestamp>`, single-use, short expiry) so a signature cannot be replayed from another site or an old proof.
2. User signs the challenge in their own wallet (GUI Sign/verify tab or CLI `sign`) and pastes the signature into ATLAS.
3. ATLAS verifies with a Monero library (monero-ts `verifyMessage` or equivalent) and requires a **spend-key SigV2** signature. On success, label the address **"Ownership verified by message signature <date>"**; on failure, keep "not verified".
4. Never accept a signature as a substitute for step 1–7 validation, and never store anything but the address + verification status + timestamp. The signature itself need not be stored after verification.

### 2e. What is NOT feasible (plainly)

- **Proving ownership from the address string alone is impossible.** An address is two public keys + a checksum; public data cannot prove private control. Any UI that implies a pasted address is "verified" by format checks alone is lying.
- **There is no way to verify ownership without the user's active participation** (signing in their wallet). ATLAS cannot do it for them, and cannot do it silently in the background.
- **No key material is ever needed or wanted.** If any flow asks for a seed, spend key, or view key, it is either a scam or a design error — stop and report it.

---

## 3. Gemini cross-check

- **Call:** `gemini.py generate --model gemini-3.5-flash` with the research question, 1500 max tokens, temperature 0. **Result: SUCCEEDED** (exit 0, 2026-11-18 ~02:52 EST). No retry was needed.
- **Gemini's claims vs independent verification:**
  - Message signing exists (CLI `sign_message`/`verify_message`, GUI Sign/verify tab, Ed25519/Schnorr) — **CONFIRMED** by getkeyproof.com, monero-ecosystem GUI guide, monero-ts docs, keys.agntn.dev (0.18.5.3). Note: Gemini's exact CLI command names (`sign_message`) differ from the CLI's actual `sign`/`verify` commands — the scheme is real, the command spelling in Gemini's answer was not exact. Use `sign`/`verify` (CLI) and the GUI Sign/verify tab.
  - Signing proves ownership without exposing seed/spend key/view key, and does not prove balance — **CONFIRMED**.
  - Address-format section of Gemini's answer was truncated in capture (output cut at the tool's display limit); **all format claims in this spec were therefore verified against web sources, not taken from Gemini.** Do not treat Gemini as the source for §1.
- **Standing rule applied:** Gemini output treated as advisory only; every claim in this spec rests on a web source listed in §4.

---

## 4. Sources

1. getmonero.org Moneropedia — "Address" (fetched live 2026-11-18): https://www.getmonero.org/resources/moneropedia/address.html — 95 chars starting with `4` or `8`; integrated 106 chars; network byte 18; checksum = first 4 bytes of Keccak-256 hash.
2. monero-oxide address management docs (DeepWiki, from `monero-oxide/wallet/address/src/lib.rs`): network bytes mainnet 18/19/42, testnet 53/54/63, stagenet 24/25/36; 4-byte Keccak-256 checksum; standard 95 chars, subaddress 95 chars, integrated 106 chars.
3. base58-monero crate docs (docs.rs / lib.rs): Monero Base58 block encoding (8 bytes → 11 chars, `1`-padding), 69 bytes → 95 chars (`8*11+7`), alphabet `123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz`, checksum = first 4 bytes of Keccak-256.
4. MoneroHelp address validator: https://www.monerohelp.com/tools/address-validator — length/charset + checksum checks; standard `4`/95, subaddress `8`/95, integrated `4`/106; "can't tell you whose address it is".
5. KeyProof — "How to sign a message with Monero GUI & CLI": https://getkeyproof.com/wallets/monero/ — GUI Sign/verify tab (Advanced mode), CLI `sign`/`verify`, SigV1/SigV2 formats, "keys never leave your wallet".
6. monero-ecosystem GUI guide — "Sign - verify Message": GUI Sign/verify tab description (sign with private key; verify with message + address + signature).
7. monero-ts docs (woodser.github.io/monero-ts): `signMessage(message, signatureType, accountIdx, subaddressIdx)`, `verifyMessage(message, address, signature)`, `getTxProof`/`getSpendProof`/`getReserveProof*`.
8. keys.agntn.dev — "Monero addresses and keys from a 25-word seed" (tested vs monero-wallet-cli/rpc 0.18.5.3): `sign` writes SigV2; `verify` checks SigV1/SigV2; SigV2 hashes a tagged structure incl. both public keys and which key signed; view-key signatures distinct from spend-key ones.
9. crypto.news — "Monero hides payments. How do you prove you paid someone?": transaction proofs (`get_tx_proof`, txid + address + tx key) and spend/reserve proofs are separate mechanisms from message signing; a bare tx hash proves nothing on its own.
10. Bitget wiki — "How to Combine ID and Base Address in Monero": integrated = network byte 0x13, +8-byte payment ID, new Keccak-256 checksum, 106 chars.

## 5. Open items / gaps (honest)

- Stagenet first characters not verified from any source — validate non-mainnet by decoded network byte only (§1b).
- SigV1 vs SigV2 exact byte layout not reproduced here — the Phase-2 build must take verification from a vetted Monero library (monero-ts/monero-javascript), never from a hand-rolled verifier written from this spec.
- No browser run opened the GUI Sign/verify tab — the exact GUI labels are taken from the community GUI guide, not from a live screenshot. Confirm during build testing if Phase 2 is ordered.
