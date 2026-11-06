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
