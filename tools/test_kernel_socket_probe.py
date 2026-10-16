import unittest

from kernel_socket_probe import CHECKS, check_log


class SocketEvidenceTests(unittest.TestCase):
    def complete(self):
        return ('\n'.join('B866F_SOCKET_OK:' + name + ' errno=0' for name in CHECKS) +
                '\nB866F_QEMU_SOCKET_TESTS_PASSED\n[3.1] reboot: Power down\n')

    def test_complete(self):
        self.assertTrue(check_log(self.complete(), 0, False))

    def test_missing_duplicate_and_reordered_checks(self):
        log = self.complete()
        lines = log.splitlines()
        self.assertFalse(check_log('\n'.join(lines[1:]), 0, False))
        self.assertFalse(check_log(lines[0] + '\n' + log, 0, False))
        lines[0], lines[1] = lines[1], lines[0]
        self.assertFalse(check_log('\n'.join(lines), 0, False))

    def test_failure_warning_panic_or_incomplete_shutdown_rejected(self):
        for text in ('B866F_SOCKET_FAIL:test', 'Kernel panic', 'BUG:', 'WARNING:'):
            with self.subTest(text=text):
                self.assertFalse(check_log(self.complete() + text, 0, False))
        self.assertFalse(check_log(self.complete(), 1, False))
        self.assertFalse(check_log(self.complete(), 0, True))
        self.assertFalse(check_log(self.complete().replace('reboot: Power down', ''), 0, False))


if __name__ == '__main__':
    unittest.main()
