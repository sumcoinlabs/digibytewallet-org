---
title: DigiByte Wallet Highlights 256-Bit Recovery as 0.1.5 Security Work Advances
slug: digibyte-wallet-256-bit-recovery-security-updates
summary: DigiByte Wallet's new-wallet setup uses 256-bit BIP39 entropy and a 24-word recovery phrase. Recent development work also strengthens iOS Keychain reliability, certificate validation, and app usability ahead of version 0.1.5.
category: Security & development
published: 2026-11-06T02:03:29Z
image: /news/assets/newsroom-social-v33.jpg
image_alt: DigiByte Wallet newsroom artwork for an update on 256-bit recovery and wallet security
tags: DigiByte, DGB, Self-custody, Wallet security, 256-bit entropy, BIP39, DigiByte Wallet
---

**What makes DigiByte (DGB) useful beyond a market quote?** For people who want to hold and use DGB themselves, the answer starts with reliable self-custody. That means understanding how a wallet creates recovery information, protects locally stored data, and responds when a device or network is temporarily unavailable.

DigiByte Wallet's published code offers a concrete starting point: its new-wallet setup requests **256 bits of BIP39 entropy**, corresponding to a **24-word recovery phrase**. Alongside that existing design, recent development work has focused on iOS Keychain reliability, certificate-validation safeguards, connections, and clearer everyday wallet screens as version 0.1.5 is prepared.

## 256-bit entropy: what the 24-word recovery phrase actually means

In the [wallet creation source code](https://github.com/sumcoinlabs/digibyte_flutter/blob/master/lib/screens/setup/setup_create_wallet.dart), the app calls `createPhrase(null, 256)` when creating a new wallet. Its wallet provider uses BIP39 mnemonic generation with the specified strength. Under the [BIP39 standard](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki), 256 bits of initial entropy produce a 24-word recovery phrase, including a checksum.

That is a meaningful security design choice because the recovery phrase is the foundation for recreating the wallet's keys. It is **not** a claim that 24-word wallets are invulnerable, or that standard 12-word BIP39 wallets are inherently unsafe. The quality of the random-number generator, secure device storage, software implementation, and how carefully a person protects their phrase all matter.

This is also **not a newly introduced November feature**: the 256-bit new-wallet setting was already present in the project's earlier code. Existing wallets are not automatically re-created or upgraded to a different phrase length. Nobody needs to reset a wallet or move coins merely because of this update.

## The recent work: protecting an existing wallet during difficult device conditions

One of the more important improvements in the [current wallet source](https://github.com/sumcoinlabs/digibyte_flutter/blob/master/lib/providers/encrypted_box_provider.dart) concerns encrypted storage. If a device temporarily prevents access to an established wallet's stored encryption key, the code is designed to **refuse to generate a replacement key** for that existing wallet. On iOS, additional Keychain handling aims to improve startup and background access without silently replacing the existing encryption key.

That kind of defensive behavior matters more than a dramatic slogan. A temporary access problem should not be mistaken for permission to initialize a new encrypted wallet over an established one. The related [October 28 changes](https://github.com/sumcoinlabs/digibyte_flutter/commit/2016416c58c879038134704b3383caef972d12cd) address Keychain access, wallet initialization, and startup reliability.

## Security maintenance and usability improvements toward 0.1.5

According to the [wallet's development changelog](https://github.com/sumcoinlabs/digibyte_flutter/blob/master/CHANGELOG.md), the 0.1.5 work includes updated FlutterFire dependencies, a Cloud Firestore certificate-validation patch related to the eMudhra certificate-authority compromise, and Flutter/Dart toolchain updates addressing TLS validation issues. It also includes improvements to iOS startup, screen scaling at larger text sizes, and banner-ad layout so unavailable ads do not occupy unnecessary space.

The preceding 0.1.4 development notes describe Electrum connection improvements, more consistent light and dark layouts, a balance-privacy toggle, a revised Send screen, and clearer price information. For someone using DGB day to day, connection reliability, readable transactions, and the ability to hide an on-screen balance are practical improvements—not just release-note filler.

**Release status matters:** these items describe the open-source development and release-preparation work. They should not be confused with a claim that the complete 0.1.5 update is already available to every App Store or Android user. Check the [official wallet website](https://www.digibytewallet.org/) and your app store for the version currently offered to your device.

## A more dependable foundation for DigiByte development

Related work is also progressing below the mobile app. The separately published [DigiCoinLib 0.0.3 release](https://github.com/sumcoinlabs/digicoinlib/blob/master/CHANGELOG.md) updates DigiByte test-network settings, adds development-network configurations, corrects optional key-derivation handling, and improves compatibility with modern Android build tools. Its maintainers explicitly preserved the standard mainnet address prefixes and default BIP32 derivation behavior. That library release is distinct from the mobile wallet's 0.1.5 rollout.

For DGB, the larger point is utility. People are more likely to explore a digital currency when the tools to hold, receive, and send it are understandable and maintained. A better wallet does not determine the market price of DGB, but verifiable security engineering gives users and developers something concrete to evaluate beyond speculation.

## What DGB holders should do now

Keep recovery words **offline and private**. Do not photograph them, place them in cloud notes, or enter them into a website that claims to be support. Verify the wallet version before updating, obtain software from the [official wallet website](https://www.digibytewallet.org/), and follow the [public development repository](https://github.com/sumcoinlabs/digibyte_flutter) for actual changes. No legitimate announcement about 256-bit entropy requires an existing holder to share a recovery phrase.

Follow further development and release announcements in the [DigiByte Wallet newsroom](/news/) or subscribe to its [RSS feed](/news/feed.xml). The most useful security stories are the ones readers can verify in code and apply to their own wallet habits.
