# DigiByte Wallet website

Public website source for [digibytewallet.org](https://www.digibytewallet.org/).

This repository initially tracks only approved static files from the production
webroot: homepage, CSS, JavaScript, images, news, privacy, donate, robots.txt,
XML sitemap, ads.txt, app-ads.txt, and favicon.

The running server, private settings, deployment credentials, CGI code, the faucet/, nested
site copies, archives, and unreviewed application directories are intentionally
excluded. Do not use `git add -f` or commit credentials. Review any additional
production directories before including them.

GitHub is a source snapshot, not the deployment target: importing files does
not alter the live site. The main site sitemap is separate from the planned
Google News sitemap (which should list only recent articles).

## Google News sitemap and newsroom

- `/sitemap.xml`: original general-purpose sitemap (not modified by this addition).
- `/news-sitemap.xml`: Google News-specific sitemap, generated from original
  `NewsArticle` page metadata and restricted to recent published articles.
- `tools/digibyte-news-readiness.py`: audited generator/installer source; run on
  the server with `--refresh` to regenerate the Google News XML.
- `ops/digibyte-news-sitemap.cron`: server schedule for every 15 minutes.
- `/news/about.html`: publisher information and editorial standards.

Production remains outside Git; the server's standalone Git working copy is at
`/root/digibytewallet-org-github`. Existing ads, private configuration, faucet,
explorer, and wallet directories remain outside this Git repository. New articles
must have canonical URLs and original publication dates; the generator reads
published HTML metadata rather than applying a new timestamp to old articles.

Google Search Console: submit `https://www.digibytewallet.org/news-sitemap.xml`
separately from the existing `sitemap.xml`. Inclusion in Google News is not
promised or controlled by this repository.
