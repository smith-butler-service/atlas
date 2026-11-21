# ATLAS Master Mission 3 — getmonero.org findings (Lane A, research only)

**Lane:** A (research) — read-only. No artifact edited, no wallet created, no keys generated.
**Checked:** 2026-11-18, 02:51 EST (pages crawled 2026-11-18 07:51 UTC).
**Pages read with `browser.open`:** `https://www.getmonero.org/` and `https://www.getmonero.org/downloads/`
**Supplementary check:** web search used ONLY to resolve two things the live page text could not show (the download-button URLs, which render as buttons, and the garbled Mobile/Desktop table columns). Anything that comes from a secondary source is labelled as such below and is NOT presented as verified from the official pages.

---

## 1. What the homepage actually says

`https://www.getmonero.org/` — "Monero Means Money: Private, decentralized cryptocurrency that keeps your finances confidential and secure."

- **"Choose a Wallet"** — "To use Monero, the first thing you are going to need is a wallet. Visit our Downloads page and get the right wallet for you. The Monero wallets are available for a variety of platforms and contain everything you need to use Monero immediately." Links to the Downloads page.
- **"Get Some Coins"** — "After you install a wallet, you need to get some Monero. There are multiple ways to acquire some coins to spend, like mining or working in exchange for Monero, but the easiest way is to use an exchange and convert your fiat money into XMR."
- **"It's a Currency; Use It!"** — spend XMR with merchants; links to a Merchants page.
- **"Find Answers to Your Questions"** — FAQ; community help.
- **"Guides and Resources"** — community User Guides, Developer Guides, Library (free 'Mastering Monero' and 'Zero to Monero' books).
- **"Moneropedia"** — glossary of terms.
- **"Join Community"** — contributing, Monero Research Lab (MRL), hangouts.

**The homepage names NO wallet and gives NO download links.** It is a pointer to the Downloads page only. All wallet specifics live on the Downloads page.

---

## 2. What the Downloads page actually lists

`https://www.getmonero.org/downloads/` — intro: "On this page you can find and download the latest version available of the Monero software, as well as hardware, light and mobile wallets."

### 2a. Monero GUI Wallet (official, core-team)
- "An open-source graphical user interface (GUI) wallet developed by the Monero community, completely free to use, suitable for both beginners and advanced users."
- **Simple mode** — "Created for less technical users who only want to use Monero in the easiest and quickest way possible. Open the wallet, automatically connect to a remote node, send/receive XMR, done!"
- **Advanced mode** — "With all the advanced features you could need. Ideal for seasoned Monero users who prefer to have full control of their wallet and node."
- Merchant page (receive XMR for a business).
- Compatible with hardware wallets (Trezor and Ledger).
- In-app fiat conversion.
- Blockchain pruning — "Not enough disk space? Just use pruning to download only 1/3 of the blockchain."
- 30+ languages.
- **Current version: 0.18.5.4 — "Fluorine Fermi"** (release-notes link on the page).

### 2b. Monero CLI Wallet (official, core-team)
- "An open-source command line interface (CLI) wallet developed by the Monero community, completely free to use, best suited for developers, intermediate, and advanced users. The CLI wallet gives you the total control over your Monero node and funds. Highly customizable and includes various analysis tools, as well as an HTTP RPC and 0MQ interface."
- Local or remote node; transactions over Tor/I2P; bootstrap node (use a remote node while the blockchain downloads locally); compatible with Trezor and Ledger; RPC Wallet and Daemon included in the archive; blockchain pruning.
- **Current version: 0.18.5.4 — "Fluorine Fermi"** (same as GUI).
- **The page text names NO operating systems for the CLI.** Do not claim CLI platform support from this page.

### 2c. Mobile & Light Wallets (third-party — NOT official)
- The page's own warning, quoted: "The wallets listed below are non-custodial mobile or light wallets **not managed by the Monero core team** that have been around for some time. It is strongly recommended that you do your own research to find out if the wallets are safe and what are the risks of using them."
- **Local synchronization** (connect to remote nodes, scan the blockchain on your device, no keys shared with nodes; higher privacy, slower first sync): ANONERO, Cake Wallet / Monero.com, Feather, Monerujo, Monfluo, Stack Wallet, Unstoppable Wallet.
- **Remote synchronization / lightweight** (these wallets "share your private view key with a remote server, which continuously scans the blockchain looking for your transactions. They are faster to use, but your privacy can be lessened if you don't control the remote server"): Edge.
- Each wallet links to its own site and source code (e.g. Cake Wallet — cakewallet.com, source on GitHub; Feather — featherwallet.org; Monerujo — monerujo.app; Monfluo — codeberg.org; Stack Wallet — stackwallet.com; Unstoppable — unstoppable.money; Edge — edge.app; ANONERO — anonero.io).
- **VERIFICATION GAP — Mobile vs Desktop columns:** the page has a Mobile/Desktop table, but the text fetch garbled which "X" falls in which column, so **which of these wallets runs on iPhone vs Android vs desktop cannot be established from the fetched official-page text.** Do not assert per-wallet phone platforms from this read. Independent guides (secondary sources, NOT the official pages) consistently describe Cake Wallet as iOS + Android, Monerujo and Monfluo as Android, and Feather as desktop — treat that as an unverified hint, not a verified fact. The Wallet Center must tell users to check the wallet's own site for iPhone/Android availability, or the Mission 3 build lane must open the Downloads page in a real browser and read the table visually.

### 2d. Hardware Wallets
- "Monero is currently supported by **Ledger Nano (S, S Plus, and X)** and **Trezor (Model T, Safe 3, Safe 5)**."
- Ledger works with: Monero GUI, Monero CLI, Cake Wallet / Monero.com, Feather, Monerujo. Minimum firmware: Nano S 2.1.0, Nano S Plus 1.0.3, Nano X 2.0.2.
- Trezor works with: Monero GUI, Monero CLI, Feather. Minimum firmware: 2.5.2.
- Links go to Ledger/Trezor support pages (usage instructions), not to a Monero download.

---

## 3. Download links

**Important limitation:** the live text fetch of the Downloads page did **not** expose the actual download-button URLs (they render as buttons, not text links). The following links come from official getmonero.org release posts and the official monero-site source (repo.getmonero.org) — they are official, but the Mission 3 build should **link users to `https://www.getmonero.org/downloads/` and let them pick their OS there**, rather than hard-coding direct file links that can go stale with the next release.

| Wallet | Downloads page offers (per official release posts / site source) |
|---|---|
| Monero GUI | Windows 64-bit, Windows 64-bit (Installer), macOS Intel, macOS ARM, Linux 64-bit — via `https://downloads.getmonero.org/gui/win64install`, `/gui/win64`, `/gui/mac64`, `/gui/linux64` (site source; the macOS link covers Intel and ARM builds on the live page) |
| Monero CLI | Same version 0.18.5.4; per-OS links exist on the page but were not exposed in the text fetch — link to the Downloads page, do not guess CLI file URLs |
| Mobile / light wallets | No files hosted by Monero — each wallet links out to its own site / app store |
| Hardware wallets | No download — links to Ledger / Trezor support pages |

- **Verify your download:** the official GUI release posts point to a GPG-signed hash list at `https://www.getmonero.org/downloads/hashes.txt` — "should be treated as canonical, with the signature checked against the appropriate GPG key." The Wallet Center should mention checking the hash/signature and downloading ONLY from getmonero.org (fake wallet apps and typosquatted domains are a known problem).
- A complete GUI wallet guide is included in the GUI archives (per the official release posts); the release posts also link an online version, but its URL was not captured in this read — do not link it until verified.

---

## 4. Discrepancies and gaps between the two pages

1. **No contradiction, but a big asymmetry:** the homepage names no wallet at all — everything specific (GUI, CLI, third-party wallets, hardware, version 0.18.5.4) is only on the Downloads page. The homepage's "available for a variety of platforms" is the only platform claim it makes.
2. **No per-OS list in the fetched text:** neither page's fetched text lists "Windows / macOS / Linux" as text. The GUI's desktop OS coverage (Windows 64-bit, macOS Intel + ARM, Linux 64-bit) is established from the official GUI release posts on getmonero.org, not from the Downloads page text itself.
3. **No official mobile wallet:** the Downloads page lists third-party mobile/light wallets only, with an explicit "not managed by the core team — do your own research" warning. There is **no official Monero wallet for iPhone or Android**.
4. **No step-by-step wallet-creation tutorial on either page.** The beginner guidance on the pages is: GUI Simple mode ("open the wallet, automatically connect to a remote node, send/receive XMR, done!"), the CLI is for advanced users, pruning if disk space is short, and "do your own research" for third-party wallets. The drafted instructions in §6 therefore describe the standard create-wallet flow in plain words; the exact on-screen labels must be confirmed against the real GUI during build testing.
5. **CLI platform support is unstated on the official pages as fetched.** (A secondary source lists Windows, macOS, Linux incl. ARM/RISC-V, Android, FreeBSD — unverified here.)

---

## 5. Platform coverage — the honest summary

| Platform | Official (core-team) option on getmonero.org? | What to tell the user |
|---|---|---|
| Windows | **Yes — Monero GUI Wallet** (Simple mode for beginners) or CLI (advanced users). Current version 0.18.5.4. | Use the GUI. |
| Linux | **Yes — Monero GUI Wallet** or CLI. Current version 0.18.5.4. | Use the GUI. |
| macOS | **Yes — Monero GUI Wallet** (Intel and ARM builds) or CLI. Current version 0.18.5.4. | Use the GUI. |
| iPhone | **NO official wallet.** Downloads page lists third-party wallets only (Cake Wallet / Monero.com, Stack Wallet, Edge, Unstoppable, etc.) with a "do your own research" warning. | Say so plainly. Do not present any phone wallet as official. |
| Android | **NO official wallet.** Same third-party list as iPhone (Monerujo, Monfluo, Cake Wallet / Monero.com, Edge, etc.), same warning. | Say so plainly. Do not present any phone wallet as official. |
| Hardware | Ledger Nano S / S Plus / X; Trezor Model T / Safe 3 / Safe 5 — work with the GUI/CLI and some third-party wallets. | Optional, for larger amounts. Not needed to receive mining payouts. |

---

## 6. DRAFTED INSTRUCTION TEXT (for the Wallet Center)

Beginner-friendly, short, plain English. No seed phrases, private keys, or passwords are ever requested or stored — Atlas only ever asks for a receiving address. These drafts are written for the Mission 3 build lane to place in the Wallet Center; on-screen button labels should be confirmed against the real wallet apps during testing.

### 6a. Create a wallet — Windows, Linux, macOS (official Monero GUI Wallet)

> **Step 1 — Download the official wallet.** Go to https://www.getmonero.org/downloads/ and download the **Monero GUI Wallet** for your computer (Windows, Mac, or Linux). Current version: 0.18.5.4 "Fluorine Fermi". Download only from getmonero.org — never from an ad, a forum link, or a look-alike site.
>
> **Step 2 — Install and open it.** Install the wallet the same way you install any other app, then open it. If Windows Defender (or your antivirus) warns about the file, that is a known false alarm — the wallet contains mining code, which antivirus tools often flag. Only proceed if you downloaded it from getmonero.org.
>
> **Step 3 — Create a new wallet.** Choose **Create a new wallet**. Give it a name and a password you will remember. The wallet will show you a **recovery phrase (25 words)**. Write it down on paper — see "Protect your recovery phrase" below — and only then continue.
>
> **Step 4 — Pick Simple mode.** When the wallet asks how to connect, choose **Simple mode**. It connects to a remote node automatically, so you can use it right away without downloading the whole blockchain. (Advanced mode downloads the full blockchain to your computer — slower, more private, not needed to start.)
>
> **Step 5 — Wait for it to sync.** The wallet needs a short time to catch up. When your balance shows 0.00 XMR and the wallet says it is connected, you are ready.

*Linux note (one line):* the Linux download is a compressed archive — extract it, then run the wallet app inside. *macOS note (one line):* download the build for your Mac — Intel for older Macs, ARM for Apple-silicon (M1/M2/M3/M4) Macs.

### 6b. Create a wallet — iPhone (no official wallet)

> **There is no official Monero wallet for iPhone.** The official Monero downloads page lists third-party wallets only, and warns that they are **not managed by the Monero team** — do your own research before trusting one with your money.
>
> **Step 1 — Pick a wallet from the official list.** Go to https://www.getmonero.org/downloads/ and look under **"Mobile & Light Wallets"**. Wallets listed there include Cake Wallet / Monero.com, Stack Wallet, Edge, and Unstoppable Wallet. Check the wallet's own website to confirm it supports iPhone.
>
> **Step 2 — Install it from the App Store.** Install the wallet from the official App Store listing linked from the wallet's own website — never from an ad or a link someone sends you.
>
> **Step 3 — Create a new wallet.** Open the app, choose **Create a new wallet**, and write down the recovery phrase on paper (see "Protect your recovery phrase" below). Let the wallet finish syncing before you use the address.

### 6c. Create a wallet — Android (no official wallet)

> **There is no official Monero wallet for Android.** The official Monero downloads page lists third-party wallets only, and warns that they are **not managed by the Monero team** — do your own research before trusting one with your money.
>
> **Step 1 — Pick a wallet from the official list.** Go to https://www.getmonero.org/downloads/ and look under **"Mobile & Light Wallets"**. Wallets listed there include Monerujo, Monfluo, Cake Wallet / Monero.com, Stack Wallet, and Edge. Check the wallet's own website to confirm it supports Android.
>
> **Step 2 — Install it from Google Play, F-Droid, or the wallet's own site.** Install only from the store or source the wallet's own website points to — never from an ad or a link someone sends you.
>
> **Step 3 — Create a new wallet.** Open the app, choose **Create a new wallet**, and write down the recovery phrase on paper (see "Protect your recovery phrase" below). Let the wallet finish syncing before you use the address.

### 6d. Advanced users — Monero CLI Wallet (optional, desktop only)

> The **Monero CLI Wallet** is the official text-based wallet for developers and advanced users (same version, 0.18.5.4). It gives full control over your node and funds but has no buttons or windows — you type commands. **Beginners should use the GUI Wallet above.** The CLI is listed on https://www.getmonero.org/downloads/ for users who know what they are doing.

### 6e. Find your receiving address

> Your receiving address is a long string of letters and numbers. It starts with the number **4**. It is safe to share — it is how people (and Atlas) send you XMR. It is **not** secret, and it is **not** your recovery phrase.
>
> - **In the Monero GUI Wallet (computer):** open your wallet, go to the **Receive** tab. Your address is shown there. Click **Copy** to copy it.
> - **In a phone wallet:** open the wallet, tap **Receive**. Your address (and usually a QR code) is shown there. Tap **Copy**.
> - **Check it:** a Monero address is 95 characters long and starts with 4. If what you copied is much shorter, or does not start with 4, you copied the wrong thing — try again.
> - Never type your address by hand. Always copy and paste it, so a typo cannot send your XMR to the wrong place.

### 6f. Connect your address to Atlas

> 1. Copy your receiving address from your wallet (see above).
> 2. Open the **ATLAS Command Center**, go to the **Mining** tab.
> 3. Find the **wallet address** field and paste your address into it.
> 4. Save it. Atlas stores **only the address** — nothing else from your wallet.
>
> That is all Atlas needs. You can change the address later by pasting a new one in the same field. Atlas will never ask you for your recovery phrase, your password, or your private keys — if anything claiming to be Atlas asks for those, it is a scam.

### 6g. Receive mining payouts

> Mining payouts go to the address connected to Atlas. When the network earns XMR, your share is sent to that address, and it appears in your wallet balance after the wallet syncs.
>
> **Honest status: real payouts are gated and none exist yet.** Mining is currently DISABLED, the emergency stop is ACTIVE, and trading is paper-only with $0 capital. No XMR has been mined and no payouts have been sent. Connecting your address now means you are ready when payouts begin — it does not mean money is on the way today. Atlas will never promise a payout amount or date it cannot guarantee.

### 6h. Protect your recovery phrase

> Your recovery phrase (25 words, shown once when you create your wallet) is the **only** way to get your XMR back if your phone or computer is lost, broken, or stolen. Whoever has it owns your money.
>
> - **Never share it** — not with Atlas, not with support, not with anyone offering help, not with any website or app. Atlas will never ask for it.
> - **Never type it into Atlas or any website.** Your recovery phrase is entered only inside your own wallet app, only when you are restoring a wallet.
> - **Write it on paper (or stamp it on metal) and store it offline**, somewhere safe at home. Two copies in two safe places is better than one.
> - **Never photograph it, never save it in a note, email, or cloud drive, and never store it on your phone or computer.** Photos and cloud accounts get hacked and synced.
> - **Check it once:** after writing it down, read the words back and make sure every word is spelled right and in the right order. One wrong word can make the phrase useless.
> - If anyone asks for your recovery phrase, stop — that is a scam, every time.

---

## 7. Rules for the Wallet Center build (from these findings)

1. **Link to `https://www.getmonero.org/downloads/`** for all downloads. Do not hard-code direct file links (they change every release; the current version is 0.18.5.4).
2. **Desktop = official GUI; phones = third-party only.** Never label a phone wallet "official Monero wallet." Carry the page's own warning: third-party wallets are not managed by the Monero core team — do your own research.
3. **Atlas stores only the receiving address** (via the existing `setMiningWallet` action in the Mining tab). Never request, accept, or store a seed phrase, private key, or password anywhere in Atlas.
4. **Payout copy must stay honest:** payouts gated, none exist yet, mining disabled, stop active, $0 capital. No payout amounts or dates.
5. **Unresolved verification items for the build lane:** (a) read the Downloads page's Mobile/Desktop table in a real browser to pin down which listed wallet is iPhone vs Android vs desktop; (b) confirm the GUI "Receive" tab label and the create-wallet screens against the real GUI 0.18.5.4; (c) confirm the exact `setMiningWallet` field label in the Mining tab.
