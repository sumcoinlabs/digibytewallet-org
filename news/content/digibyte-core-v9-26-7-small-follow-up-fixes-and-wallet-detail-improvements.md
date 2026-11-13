---
title: DigiByte Core v9.26.7: Small Follow‑up Fixes and Wallet Detail Improvements
slug: digibyte-core-v9-26-7-small-follow-up-fixes-and-wallet-detail-improvements
summary: The DigiByte Core v9.26.7 release, published on 6 Oct 2026, addresses slow chain‑information requests, a shutdown fatal‑error, and refines three wallet UI details. It adds five user‑facing changes and ten total fixes without altering block‑validation rules or Thaw Day activation heights.
category: Release
image_alt: Original editorial illustration: DigiByte Core v9.26.7: Small Follow‑up Fixes and Wallet Detail Improvements
tags: DigiByte, DGB, DigiByte Wallet
image: /news/assets/digibyte-core-v9-26-7-small-follow-up-fixes-and-wallet-detail-improvements-16x9.jpg
image_4x3: /news/assets/digibyte-core-v9-26-7-small-follow-up-fixes-and-wallet-detail-improvements-4x3.jpg
image_square: /news/assets/digibyte-core-v9-26-7-small-follow-up-fixes-and-wallet-detail-improvements-1x1.jpg
published: 2026-11-13T00:51:00Z
---

## Overview of the v9.26.7 Release
DigiByte Core v9.26.7 was released on 6 Oct 2026 as a non‑prerelease, non‑draft update to the full‑node software. The changelog describes it as a “small follow‑up” to v9.26.6, focusing on performance tweaks and wallet UI refinements. No new consensus rules, oracle requirements, or Thaw Day activation heights were introduced; the mainnet Thaw Day remains at block 24,490,000 and Testnet26 at block 432,100.

## Key Fixes and User‑Facing Changes
The release bundles ten fixes, split between five user‑facing changes and five test/CI corrections:
1. **Chain‑information speed** – `getblockchaininfo` and `getchainstates` now read difficulty directly from the tip block, avoiding a costly walk through retired Groestl history.
2. **Empty address listing** – Unused DigiDollar receive addresses created in the Qt UI now appear in `listdigidollaraddresses` when `include_empty` is true, preserving their labels.
3. **Send‑amount tooltip** – The tooltip clarifies that change must be zero or at least 1.00 DD, reinforcing the existing $1 minimum output rule.
4. **Shutdown statistics** – Pending DigiDollar supply‑check updates now complete cleanly during node shutdown, preventing a false fatal‑error report.
5. **Version display** – The wallet overview now pulls its version number from build settings rather than a hard‑coded artwork label.

The test and CI corrections improve internal validation (e.g., block‑map memory thresholds, CodeQL exclusions, prune‑budget checks) but do not affect transaction or block acceptance rules.

## Upgrade Recommendations
The release notes advise a standard upgrade path:
1. Back up wallet files and configuration, keeping backups private.
2. Verify the downloaded package’s SHA‑256 checksum against the published checksum file.
3. Stop the running daemon cleanly, replace the binaries, and restart.
4. Confirm the node reports version v9.26.7 and finishes synchronization.

A normal upgrade from v9.26.6 does **not** require a blockchain reindex. Existing DigiDollar block history and wallet files remain usable.

## Testing Status and Known Gaps
Automated testing shows all core unit tests (3,762 cases) passed, along with functional, fuzz, and CI checks. However, the release notes note that launch checks on Windows, ARM‑Linux, and macOS targets are still pending, and the Apple Silicon launch report requires a full package signature verification. These gaps mean the binaries for those platforms have not yet been fully validated in real‑world conditions.

## Limitations of the Source Material
The provided release notes are the sole source for this article; no external verification of the checksum process, performance impact, or user experience has been performed. The “45‑minute startup” issue mentioned elsewhere is explicitly not linked to the fixes in v9.26.7, and the release does not claim to resolve that symptom.

**Caution for users:** Always keep private keys and wallet backups offline and never share them. The release notes stress that checksum verification is not a digital signature; users should still confirm package authenticity through DigiByte’s official distribution channels.

---
*This article reflects the information available in the DigiByte Core v9.26.7 GitHub release page as of the source timestamp (6 Oct 2026). It does not constitute independent verification of the software’s security or performance.*

## Original source

[DigiByte Core releases](https://github.com/DigiByte-Core/digibyte/releases/tag/v9.26.7)
