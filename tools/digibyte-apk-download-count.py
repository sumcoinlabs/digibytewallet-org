#!/usr/bin/env python3
import gzip
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

LOG = Path('/var/log/nginx/access.log')
STATE = Path('/var/lib/digibytewallet/apk-download-state.json')
OUTPUT = Path('/var/www/digibytewallet-org/downloads')
APK_SIZES = {
    p.name[len('DigiByte-Wallet-build'):-4]: p.stat().st_size
    for p in OUTPUT.glob('DigiByte-Wallet-build*.apk')
}

RX = re.compile(
    rb'\[(?P<day>\d{2}/[A-Za-z]{3}/\d{4}):[^\]]+\] '
    rb'"GET /downloads/DigiByte-Wallet-build'
    rb'(?P<version>\d+(?:\.\d+)+)'
    rb'\.apk(?:\?[^ ]*)? HTTP/[0-9.]+" '
    rb'(?P<status>200|206) (?P<bytes>\d+) '
)

def new_stats():
    return {
        'total_requests': 0,
        'responses': {'200': 0, '206': 0},
        'by_day': {},
        'by_version': {},
        'by_month': {},
        'full_length_200_responses': 0
    }

def tally(stats, line):
    m = RX.search(line)
    if m is None:
        return

    date = datetime.strptime(
        m['day'].decode('ascii'), '%d/%b/%Y'
    ).strftime('%Y-%m-%d')

    version = m['version'].decode('ascii')
    status = m['status'].decode('ascii')
    full = (status == '200' and version in APK_SIZES
            and int(m['bytes']) >= APK_SIZES[version])
    if full:
        stats['full_length_200_responses'] += 1

    stats['total_requests'] += 1
    stats['responses'][status] += 1

    for group, key in (
        (stats['by_day'], date),
        (stats['by_version'], version),
        (stats['by_month'], date[:7])
    ):
        rec = group.setdefault(
            key, {'total': 0, '200': 0, '206': 0, 'full_200': 0}
        )
        rec['total'] += 1
        rec[status] += 1
        if full:
            rec['full_200'] += 1

def scan(stats, path, offset=0):
    opener = gzip.open if path.suffix == '.gz' else open

    with opener(path, 'rb') as f:
        if offset:
            f.seek(offset)
        for line in f:
            tally(stats, line)
        return f.tell()

def write_atomic(path, content, perms):
    tmp = path.with_name('.' + path.name + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        f.write(content)
    os.chmod(tmp, perms)
    os.replace(tmp, path)

if not LOG.is_file():
    raise SystemExit('Nginx access log missing')

STATE.parent.mkdir(
    mode=0o700, parents=True, exist_ok=True
)
OUTPUT.mkdir(parents=True, exist_ok=True)

current = LOG.stat()

if STATE.exists():
    state = json.loads(STATE.read_text())
    stats = state['stats']
    inode = state['inode']
    offset = state['offset']

    if inode != current.st_ino or offset > current.st_size:
        found = False

        for old in LOG.parent.glob(LOG.name + '.*'):
            if (
                old.suffix != '.gz'
                and old.is_file()
                and old.stat().st_ino == inode
            ):
                scan(stats, old, offset)
                found = True
                break

        if not found:
            print(
                'WARNING: Previous log unavailable; '
                'some requests may be missing'
            )

        offset = 0

else:
    stats = new_stats()
    offset = 0
    past = []

    # Import retained historical Nginx logs once.
    for old in LOG.parent.glob(LOG.name + '.*'):
        match = re.fullmatch(
            re.escape(LOG.name) + r'\.(\d+)(?:\.gz)?',
            old.name
        )
        if match and old.is_file():
            past.append((int(match.group(1)), old))

    for _, old in sorted(
        past, key=lambda item: item[0], reverse=True
    ):
        scan(stats, old)

new_offset = scan(stats, LOG, offset)

now = datetime.now(
    timezone.utc
).isoformat(timespec='seconds')

write_atomic(
    STATE,
    json.dumps({
        'inode': current.st_ino,
        'offset': new_offset,
        'stats': stats
    }, sort_keys=True) + '\n',
    0o600
)

report = {
    'description': (
        'Successful GET requests (200 and 206); '
        'not unique users or installations'
    ),
    'total_requests': stats['total_requests'],
    'full_responses_200': stats['responses']['200'],
    'full_length_200_responses': stats['full_length_200_responses'],
    'range_responses_206': stats['responses']['206'],
    'by_day': {
        d: stats['by_day'][d]
        for d in sorted(stats['by_day'])
    },
    'by_version': {
        v: stats['by_version'][v]
        for v in sorted(stats['by_version'])
    },
    'by_month': {
        k: stats['by_month'][k] for k in sorted(stats['by_month'])
    },
    'last_updated_utc': now
}



today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
month = today[:7]
daily = report['by_day'].get(today, {})
monthly = report['by_month'].get(month, {})

versions = ', '.join(sorted(report['by_version']))

report['human_summary'] = {
    'Full-size APK transfers': '{} observed'.format(
        report['full_length_200_responses']),
    'Total activity': '{} successful requests'.format(
        report['total_requests']),
    'Today ({} UTC)'.format(today): '{} requests, {} full-size transfers'.format(
        daily.get('total', 0), daily.get('full_200', 0)),
    'This month ({} UTC)'.format(month): '{} requests, {} full-size transfers'.format(
        monthly.get('total', 0), monthly.get('full_200', 0)),
    'Version': versions,
    'Important': 'Not confirmed installs. Chunked downloads may be undercounted.'
}

write_atomic(
    OUTPUT / 'download-stats.json',
    json.dumps(report, indent=2) + '\n',
    0o644
)

print(
    f"DigiByte APK requests: {stats['total_requests']} "
    f"(200={stats['responses']['200']}, "
    f"206={stats['responses']['206']})"
)
