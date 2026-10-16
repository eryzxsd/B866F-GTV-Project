"""Require complete load/liveness/unload evidence and normal syscall flags."""
import unittest
from kernel_original_load_probe import MODULES, check_log


class OriginalLoadChecks(unittest.TestCase):
    def test_complete_runtime_evidence_and_no_force_flags(self):
        log = ''.join('B866F_ORIGINAL_LOAD: ' + n + ' result=0 errno=0 flags=0\n' +
                      'B866F_ORIGINAL_LIVE: ' + n + '\n' for n in MODULES)
        log += ''.join('B866F_ORIGINAL_UNLOAD: ' + n + ' result=0 errno=0\n' for n in reversed(MODULES))
        log += 'B866F_QEMU_ORIGINAL_LOAD_PASSED count=8\n'
        self.assertTrue(check_log(log))
        self.assertFalse(check_log(log.replace('flags=0', 'flags=1', 1)))
        self.assertFalse(check_log(log.replace('result=0 errno=0', 'result=-1 errno=8', 1)))
        self.assertFalse(check_log(log.replace('B866F_ORIGINAL_LIVE: mii\n', '')))
        self.assertFalse(check_log(log + 'B866F_QEMU_FAIL: live'))
        self.assertFalse(check_log(log + 'B866F_ORIGINAL_UNLOAD: mii result=0 errno=0\n'))


if __name__ == '__main__':
    unittest.main()
