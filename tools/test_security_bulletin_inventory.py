import tempfile
import unittest
from pathlib import Path

from security_bulletin_inventory import fetch_month


class BulletinInventoryTests(unittest.TestCase):
    def parse(self, html):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            (cache / '2026-05.html').write_text(html, encoding='utf-8')
            return fetch_month('2026-05', cache)

    def page(self, content):
        return '<h1>Android Security Bulletin—May 2026</h1>' + content

    def test_wrong_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.parse('<h1>Android Security Bulletin—April 2026</h1>')

    def test_empty_is_not_assumed_clean(self):
        result = self.parse(self.page('<p>No table provided.</p>'))
        self.assertEqual(result['extraction_status'], 'no_rows_manual_review_required')
        self.assertFalse(result['patch_presence_on_device_checked'])

    def test_explicit_empty(self):
        result = self.parse(self.page('<p>There are no security vulnerabilities in this bulletin.</p>'))
        self.assertEqual(result['extraction_status'], 'explicit_no_patches')

    def vulnerability_table(self, version='14, 15, 16'):
        return ('<h2>2026-05-01 security patch level</h2><h3>System</h3><table>'
                '<tr><th>CVE</th><th>References</th><th>Type</th><th>Severity</th>'
                '<th>Updated AOSP versions</th></tr><tr><td>CVE-2026-0073</td>'
                '<td><a href="/fix">fix</a></td><td>EoP</td><td>High</td>'
                f'<td>{version}</td></tr></table>')

    def test_versions_links_and_mainline_not_duplicated(self):
        result = self.parse(self.page(self.vulnerability_table() +
            '<h3>Mainline</h3><table><tr><th>CVE</th><th>Component</th></tr>'
            '<tr><td>CVE-2026-0073</td><td>adbd</td></tr></table>'))
        self.assertEqual(len(result['records']), 1)
        self.assertTrue(result['records'][0]['android14_listed'])
        self.assertEqual(result['records'][0]['references'], ['https://source.android.com/fix'])

    def test_version_substring_is_not_version14(self):
        result = self.parse(self.page(self.vulnerability_table('114, 15')))
        self.assertFalse(result['records'][0]['android14_listed'])

    def test_changed_columns_rejected(self):
        html = self.vulnerability_table().replace('<td>High</td>', '')
        with self.assertRaisesRegex(ValueError, 'column count'):
            self.parse(self.page(html))


if __name__ == '__main__':
    unittest.main()
