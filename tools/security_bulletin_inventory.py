"""Inventory official bulletin references; does not infer patch installation.

Raw pages and full output should stay in a private research directory. This is
a requirements index, not a vulnerability scanner or a patch-level certificate.
"""
import argparse
import calendar
from concurrent.futures import ThreadPoolExecutor
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin
from urllib.request import urlopen


class BulletinParser(HTMLParser):
    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.heading = None
        self.heading_text = []
        self.level = None
        self.component = None
        self.table = None
        self.row = None
        self.cell = None
        self.tables = []
        self.text = []
        self.title = None

    def handle_starttag(self, tag, attrs):
        if tag in {'h1', 'h2', 'h3'}:
            self.heading, self.heading_text = tag, []
        if tag == 'table':
            self.table = {'level': self.level, 'component': self.component, 'rows': []}
        if self.table is not None:
            if tag == 'tr':
                self.row = []
            if tag in {'td', 'th'}:
                self.cell = {'text': [], 'links': []}
            if tag == 'a' and self.cell is not None:
                href = dict(attrs).get('href')
                if href:
                    self.cell['links'].append(urljoin(self.url, href))

    def handle_data(self, data):
        self.text.append(data)
        if self.heading:
            self.heading_text.append(data)
        if self.cell is not None:
            self.cell['text'].append(data)

    def handle_endtag(self, tag):
        if tag == self.heading:
            text = ' '.join(''.join(self.heading_text).split())
            if tag == 'h1':
                self.title = text
            elif tag == 'h2':
                found = re.match(r'(\d{4}-\d{2}-\d{2}) security patch level', text)
                if found:
                    self.level = found[1]
                    self.component = None
            else:
                self.component = text
            self.heading = None
        if self.table is not None:
            if tag in {'td', 'th'} and self.cell is not None:
                self.cell['text'] = ' '.join(''.join(self.cell['text']).split())
                if self.row is not None:
                    self.row.append(self.cell)
                self.cell = None
            if tag == 'tr' and self.row:
                self.table['rows'].append(self.row)
                self.row = None
            if tag == 'table':
                self.tables.append(self.table)
                self.table = None

    def records(self):
        result = []
        for table in self.tables:
            rows = table['rows']
            if not rows or not table['level']:
                continue
            headers = [c['text'] for c in rows[0]]
            if not headers or headers[0] != 'CVE' or len(headers) < 4:
                continue  # Mainline cross-reference tables are not extra CVEs.
            version_index = headers.index('Updated AOSP versions') if 'Updated AOSP versions' in headers else None
            for row in rows[1:]:
                if len(row) != len(headers):
                    raise ValueError('Unexpected vulnerability table column count')
                ids = re.findall(r'CVE-\d{4}-\d{4,}', row[0]['text'])
                for cve in ids:
                    versions = row[version_index]['text'] if version_index is not None else None
                    result.append({'cve': cve, 'patch_level': table['level'],
                                   'component': table['component'], 'versions': versions,
                                   'android14_listed': bool(re.search(r'(?<!\d)14(?!\d)', versions)) if versions else None,
                                   'references': row[1]['links'], 'bulletin': self.url})
        return result


def fetch_month(month, cache):
    year = month[:4]
    prefix = year + '/' if int(year) >= 2026 else ''
    url = f'https://source.android.com/docs/security/bulletin/{prefix}{month}-01'
    path = cache / (month + '.html')
    if not path.exists():
        with urlopen(url, timeout=60) as response:
            data = response.read()
        path.write_bytes(data)
    data = path.read_bytes()
    parser = BulletinParser(url)
    parser.feed(data.decode('utf-8'))
    records = parser.records()
    if (not parser.title or not parser.title.startswith('Android Security Bulletin') or
            calendar.month_name[int(month[5:])] + ' ' + year not in parser.title):
        raise ValueError('Unexpected bulletin identity: ' + month)
    no_patches_text = ('There are no Android security patches in the ' +
                       calendar.month_name[int(month[5:])] + ' ' + year + ' Android Security Bulletin')
    text = ' '.join(' '.join(parser.text).split())
    explicit_none = no_patches_text in text or 'There are no security vulnerabilities in this bulletin.' in text
    extraction_status = 'rows_parsed' if records else 'explicit_no_patches' if explicit_none else 'no_rows_manual_review_required'
    lts = []
    for table in parser.tables:
        if table['component'] == 'Kernel LTS' and len(table['rows']) > 1:
            headers = [c['text'] for c in table['rows'][0]]
            for row in table['rows'][1:]:
                if len(row) != len(headers):
                    raise ValueError('Unexpected kernel LTS table')
                lts.append(dict(zip(headers, [c['text'] for c in row])))
    return {'month': month, 'url': url, 'html_sha256': hashlib.sha256(data).hexdigest(),
            'records': records, 'explicit_no_android_patches': explicit_none,
            'extraction_status': extraction_status,
            'kernel_lts_requirements': lts, 'patch_presence_on_device_checked': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    months = [f'2025-{m:02d}' for m in range(5, 13)] + [f'2026-{m:02d}' for m in range(1, 6)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda month: fetch_month(month, args.cache), months))
    output = {'scope': 'May 2025 through May 2026 published bulletin requirements',
              'coverage_established': False, 'months': results}
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    for result in results:
        records = result['records']
        print(result['month'], result['extraction_status'], 'rows', len(records), 'Android14 platform rows',
              sum(r['android14_listed'] is True for r in records),
              'kernel rows', sum(r['component'] in {'Kernel', 'Kernel components'} for r in records))


if __name__ == '__main__':
    main()
