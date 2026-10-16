from pathlib import Path
import shutil
import tempfile
import unittest

from kernel_patch_match import compare


@unittest.skipUnless(shutil.which('patch'), 'GNU patch required')
class PatchMatchTests(unittest.TestCase):
    def check(self, content, expected):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            file = source / 'example.c'
            file.write_text(content)
            patch = root / 'fix.patch'
            patch.write_text('--- a/example.c\n+++ b/example.c\n@@ -1 +1 @@\n-old\n+fixed\n')
            before = file.read_bytes()
            result = compare(source, patch)
            self.assertEqual(result['status'], expected)
            self.assertEqual(file.read_bytes(), before)
            self.assertEqual(sorted(p.name for p in source.iterdir()), ['example.c'])
            self.assertFalse(result['coverage_established'])

    def test_forward(self):
        self.check('old\n', 'forward_patch_matches')

    def test_reverse(self):
        self.check('fixed\n', 'reverse_patch_matches')

    def test_different_implementation_remains_unknown(self):
        self.check('another implementation\n', 'manual_review')


if __name__ == '__main__':
    unittest.main()
