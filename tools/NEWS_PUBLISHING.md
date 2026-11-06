# DigiByte Wallet News publishing

This site is statically published from the reviewed GitHub source clone. The original
hand-crafted articles stay unchanged. Only new articles use `tools/news-publisher.py`.

## Editing an article

Create a UTF-8 Markdown file on your Mac, such as `~/Downloads/digibyte-new-release.md`.
Use the following structure, replacing the example values. **Do not publish a placeholder**:

```markdown
---
title: DigiByte Wallet 0.1.5 release announcement
slug: digibyte-wallet-0-1-5-release
summary: An accurate, at least 45-character summary explaining what has actually shipped and what readers should know.
category: Release
published: auto
image: /news/assets/newsroom-social-v33.jpg
image_alt: DigiByte Wallet news announcement artwork
tags: DigiByte, DigiByte Wallet, Software release
---

An opening paragraph that accurately describes the release. Do not claim the
software is available until the app-store or package release is public.

## What changed

Explain the main changes in complete paragraphs, with links to verifiable sources.

- A verified improvement
- A relevant compatibility note
- A limitation or upgrade consideration

## Where to learn more

Readers can check [the open-source wallet](https://github.com/sumcoinlabs/digibyte_flutter).
```

At least 60 words are required in the article body. Supported Markdown: `##` / `###`
headings, paragraphs, bullet and numbered lists, `**bold**`, inline `code`, and
`[text](https://...)` or root-relative links. Raw HTML is escaped. The original
publication timestamp is assigned at publishing time when `published: auto`.
If the original publication time is already known, use a timezone-aware ISO 8601
value instead. Never alter original publication dates to regain News freshness.

Image paths must refer to already-reviewed, already-live assets under
`/news/assets/`, such as `newsroom-social-v33.jpg`. For article-specific images,
add the appropriate public asset to the approved source and production first.
No private keys, API tokens, unpublished secrets, or internal infrastructure
information belong in this public repository.

## Publish (one command from your Mac)

```bash
ssh root@64.23.176.29 'python3 /root/digibytewallet-org-github/tools/news-publisher.py --publish-stdin' < ~/Downloads/digibyte-new-release.md
```

The command checks the GitHub clone, validates the article, and compares existing
production files to their reviewed Git baseline. It then generates the article
page, adds a newsroom card, updates newsroom ItemList structured data, updates
RSS and JSON feeds, updates the *main* sitemap, and regenerates the distinct
Google News sitemap using the existing tool. It stages only approved files,
commits, pushes to GitHub **first**, then deploys only approved public outputs.
The existing 15-minute production cron continues to maintain the News sitemap.
No additional Search Console sitemap submission is needed for each article.
Check indexing in Search Console for each new article URL.

If it stops, inspect the reported error before retrying. If GitHub push succeeds
but a production deployment fails, the GitHub commit is already available for
manual reconciliation. Do not force-push or reset changes without reviewing them.

## Check readiness without publishing

```bash
ssh root@64.23.176.29 'python3 /root/digibytewallet-org-github/tools/news-publisher.py --check'
```

This tool never scans, stages, copies, or deploys `faucet/`, `wallet/`,
`explorer/`, `recovery/`, `cgi-bin/`, `.well-known/`, or server configuration.
The main sitemap may legitimately contain public URLs under those paths.
