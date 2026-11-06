# Private DigiByte Wallet Newsroom editor

Access is deliberately **not** via a public domain, WordPress, Nginx route, or network-open admin endpoint.
The service binds exclusively to `127.0.0.1:8769` on the server, requires SSH tunnel access **and** an independent password, and issues short-lived HttpOnly SameSite=Strict sessions. The editor has an origin check, CSRF verification, login throttling and private draft storage under `/root/.local/share/dgb-newsroom-editor/` (never pushed to GitHub).

## Install once (from the Mac)

```sh
ssh -t root@64.23.176.29 'bash /root/digibytewallet-org-github/tools/install-newsroom-editor.sh'
```

The installer pulls the reviewed GitHub changes into the existing server source clone, builds an isolated virtual environment with Pillow 10.4.0 (Python 3.8 compatible), asks you to choose a unique 16+ character editor password, and enables the localhost-only systemd service. It does not publish articles or alter the faucet, other excluded directories, Nginx, DNS, or public server configuration.

## Every time you want to publish

1. On the Mac, run `ssh -N -L 8877:127.0.0.1:8769 root@64.23.176.29` (keep terminal open).
2. Open `http://127.0.0.1:8877/` in your Mac browser; sign in with your editor password.
3. Write the article, upload a relevant image at least **1600 × 1200** and under **8 MB**, adjust crop focus, save the draft, inspect preview and choose **Publish to website**.
4. The server generates original 16:9 (1600 × 900), 4:3 (1200 × 900) and 1:1 (1200 × 1200) image assets, strips image metadata, commits and pushes assets to GitHub first, then invokes the existing safe publisher. The publisher creates the article and metadata, updates feeds and sitemaps, pushes the article commit to GitHub and deploys approved public paths.
5. Close the SSH tunnel terminal when finished. Drafts are private; completed articles are public.

**Security:** The editor has no public URL. Access still depends on protecting the Mac, SSH credentials, and the editor password. Nobody can guarantee exclusivity if SSH keys or the machine itself are compromised. The code is public by design; credentials, sessions and private drafts are not.

**SEO:** A new article gets truthful first-publication date in ISO 8601, `NewsArticle` and `BreadcrumbList` JSON-LD, dedicated 16:9 / 4:3 / 1:1 structured-data images, prominent large OG image, `max-image-preview:large`, canonical URL, Twitter metadata, links in the newsroom, RSS + JSON feeds and two updated sitemaps. Google decides how to present a result. Do not falsify timestamps, titles, authors, updates, releases, or image relevance. The News sitemap includes eligible articles for only the most recent 48 hours.

**Check service**: `ssh root@64.23.176.29 'systemctl status --no-pager dgb-newsroom-editor.service'`

**Change password**: `ssh -t root@64.23.176.29 '/opt/dgb-news-editor/venv/bin/python3 /root/digibytewallet-org-github/tools/newsroom-editor.py --set-password && systemctl restart dgb-newsroom-editor.service'`
