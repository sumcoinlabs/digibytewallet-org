---
title: DigiByte Wallet 0.1.5 is now available on the App Store
slug: digibyte-wallet-0-1-5-now-available
summary: DigiByte Wallet 0.1.5 is now listed on Apple's App Store, bringing security dependency updates, improved iPhone startup reliability, Send All fixes, and clearer controls.
category: Release
image: /news/assets/newsroom-social-v33.jpg
image_alt: DigiByte Wallet newsroom illustration highlighting wallet software updates
tags: DigiByte, DGB, DigiByte Wallet, iOS, Release
published: 2026-11-12T21:22:08Z
---
DigiByte Wallet version 0.1.5 is now listed on Apple's App Store. The update moves a collection of security-maintenance and everyday-usability changes from development into the released iPhone and iPad app. Users can check their device's current version directly in the App Store.

## What changed in version 0.1.5?

The release brings newer dependencies and toolchain components, improved iOS wallet startup handling, and changes intended to make commonly used screens easier to navigate.

- **Security maintenance.** The app updates its compatible FlutterFire/Firebase components, includes a Cloud Firestore certificate-validation fix associated with the eMudhra certificate-authority issue, and incorporates Flutter/Dart toolchain security updates. The discontinued Firebase Dynamic Links dependency has been removed.
- **More dependable startup.** Adjustments to iOS Keychain handling aim to make opening a wallet more reliable, especially around protected storage access. The app is still a self-custody wallet: never share your recovery phrase.
- **More reliable sending.** The release includes a fix for a crash associated with the Send All feature. Always review the destination address and final amount before authorizing a transfer.
- **Clearer everyday controls.** The light-mode keypad has been corrected, and access to hidden wallets has been improved. Layout scaling was also refined for users with larger text settings.
- **Less wasted advertising space.** Banner-ad space is reserved only when an ad is actually available, reducing unnecessary gaps in the interface.

The update also raises the minimum supported iOS version to iOS 15, configures iPad presentation for portrait orientation, and adds notification-open analytics handling on iOS. These changes are documented in the project's public source and published release notes.

## Availability and what to check

The [DigiByte Wallet App Store listing](https://apps.apple.com/us/app/digibyte-wallet/id6481703766) now identifies version 0.1.5. Device eligibility and storefront rollout may vary by region, so check the version displayed for your device rather than relying on a screenshot or third-party download.

The open-source [DigiByte Wallet changelog](https://github.com/sumcoinlabs/digibyte_flutter/blob/master/CHANGELOG.md) contains the technical release notes. This mobile-wallet release is separate from DigiCoinLib 0.0.3, the underlying developer-library update previously covered in this newsroom.

## An update to our earlier preview

On November 5, this newsroom published a preview while 0.1.5 was still being prepared. That article remains available as a historical record, but its pre-release status should no longer be read as current information. The public App Store listing is the source of truth for whether 0.1.5 is available.

This announcement reports the release and its documented changes. It does not claim an independent security audit, guarantee that every device has received the update, or change the responsibility of wallet users to protect their recovery words offline.
