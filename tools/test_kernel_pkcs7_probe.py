"""Fail-closed evidence checks for a local private-data PKCS7 experiment."""
import json
from pathlib import Path
import tempfile
import unittest
from kernel_baseline import ROOT
from kernel_pkcs7_probe import check_pkcs7_log, private_inputs


class Pkcs7Checks(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((ROOT / 'kernel/module-signature-result.json').read_text())['modules']

    def test_every_original_and_negative_result_required(self):
        log = ''
        for row in self.rows:
            name = row['module']
            if name == 'amlogic-input.ko':
                log += 'B866F_PKCS7: ' + name + ' original=-126\n'
            else:
                log += ('B866F_PKCS7: ' + name + ' original=0\n' +
                        'B866F_PKCS7: ' + name + ' changed_body=-129\n' +
                        'B866F_PKCS7: ' + name + ' truncated_cms=-74\n')
        log += 'B866F_QEMU_PKCS7_PASSED trusted=46 unknown=1\nB866F_PKCS7_FIXTURE_EXIT\n'
        self.assertTrue(check_pkcs7_log(log, self.rows))
        self.assertFalse(check_pkcs7_log(log.replace('original=-126', 'original=0'), self.rows))
        self.assertFalse(check_pkcs7_log(log.replace('truncated_cms=-74', 'truncated_cms=0', 1), self.rows))
        self.assertFalse(check_pkcs7_log(log + 'B866F_PKCS7_FIXTURE_EXIT', self.rows))
        self.assertFalse(check_pkcs7_log(log + 'B866F_QEMU_FAIL: helper', self.rows))

    def test_original_hash_mismatch_rejected_before_packaging(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / self.rows[0]['module']).write_bytes(b'unexpected original data')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                private_inputs(directory, self.rows)

    def test_incomplete_input_scope_rejected(self):
        with self.assertRaisesRegex(ValueError, '47-module'):
            private_inputs(Path('.'), self.rows[:-1])


if __name__ == '__main__':
    unittest.main()
