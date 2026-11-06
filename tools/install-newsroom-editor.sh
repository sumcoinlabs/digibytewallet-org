#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=/root/digibytewallet-org-github
LIVE=/var/www/digibytewallet-org
cd "$ROOT"
echo '== Check GitHub origin and clean working copy =='
test "$(git branch --show-current)" = main
git remote get-url origin | grep -Eq 'github.com[:/]sumcoinlabs/digibytewallet-org(\.git)?$'
test -z "$(git status --porcelain --untracked-files=all)" || { echo 'Working copy has changes. Resolve before installing.'; exit 1; }
git pull --ff-only origin main
python3 -m py_compile tools/news-publisher.py tools/newsroom-editor.py
test -f "$LIVE/news/index.html"
test -f "$ROOT/tools/newsroom-editor.py"
echo '== Install isolated Python 3.8 compatible image processor =='
if ! test -x /opt/dgb-news-editor/venv/bin/python3; then
  if ! python3 -m venv /opt/dgb-news-editor/venv; then
    echo 'Python venv unavailable; installing the supported OS package.'
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
    python3 -m venv /opt/dgb-news-editor/venv
  fi
fi
/opt/dgb-news-editor/venv/bin/python3 -m pip install --disable-pip-version-check --no-cache-dir 'Pillow==10.4.0'
/opt/dgb-news-editor/venv/bin/python3 -c 'from PIL import Image; print("Pillow ready", Image.__version__)'
echo '== Set private editor password, NOT stored in GitHub =='
/opt/dgb-news-editor/venv/bin/python3 "$ROOT/tools/newsroom-editor.py" --set-password
echo '== Install loopback-only systemd service =='
cat > /etc/systemd/system/dgb-newsroom-editor.service <<'UNIT'
[Unit]
Description=Private DigiByte Wallet newsroom editor (localhost only)
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root/digibytewallet-org-github
ExecStart=/opt/dgb-news-editor/venv/bin/python3 /root/digibytewallet-org-github/tools/newsroom-editor.py --serve
Restart=on-failure
RestartSec=4
UMask=0027
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/root/digibytewallet-org-github /var/www/digibytewallet-org /root/.local/share/dgb-newsroom-editor
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now dgb-newsroom-editor.service
systemctl restart dgb-newsroom-editor.service
sleep 2
systemctl --quiet is-active dgb-newsroom-editor.service
python3 - <<'PY'
import socket
with socket.create_connection(('127.0.0.1',8769),timeout=3) as c:
    c.sendall(b'GET /login HTTP/1.1\r\nHost: 127.0.0.1:8769\r\nConnection: close\r\n\r\n')
    data=c.recv(4096)
    assert b'200 OK' in data and b'X-Frame-Options: DENY' in data, data[:400]
print('PASS: Password-protected editor responds locally')
PY
if command -v ss >/dev/null; then
  ss -ltnp | grep ':8769' | tee /dev/stderr | grep -q '127.0.0.1:8769' || { echo 'Unsafe listener: editor not strictly loopback'; systemctl stop dgb-newsroom-editor; exit 1; }
fi
printf '\nSUCCESS. Private editor is not exposed via Nginx or a public port.\n'
printf 'ON YOUR MAC, open a separate terminal and run:\n'
printf 'ssh -N -L 8877:127.0.0.1:8769 root@64.23.176.29\n'
printf 'Then open http://127.0.0.1:8877/ and log in with your new editor password.\n'
