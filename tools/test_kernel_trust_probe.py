"""Fail-closed checks for the emulator trust experiment; no device access."""
from pathlib import Path
import tempfile
import unittest

from kernel_baseline import config_map, ROOT
from kernel_qemu import classify
from kernel_trust_probe import certificate_der, check_config, check_image


class TrustProbeChecks(unittest.TestCase):
    def test_real_public_certificate_and_enforcement_guard(self):
        der = certificate_der(ROOT / 'kernel/trust/original-module-signer.crt')
        reference = config_map(ROOT / 'kernel/b866f-running.config')
        resolved = {**reference, 'CONFIG_SYSTEM_TRUSTED_KEYS': '"certs/original.crt"'}
        self.assertTrue(check_config(reference, resolved, 'certs/original.crt')
                        ['enforcement_options_unchanged'])
        resolved['CONFIG_MODULE_SIG_PROTECT'] = 'n'
        with self.assertRaises(ValueError):
            check_config(reference, resolved, 'certs/original.crt')
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'Image'
            image.write_bytes(b'kernel-without-certificate')
            with self.assertRaises(ValueError):
                check_image(image, der)
            image.write_bytes(b'prefix' + der + b'suffix')
            self.assertEqual(check_image(image, der)['certificate_der_occurrences_in_image'], 1)

    def test_different_certificate_rejected(self):
        text = (ROOT / 'kernel/trust/original-module-signer.crt').read_text()
        with tempfile.TemporaryDirectory() as directory:
            certificate = Path(directory) / 'certificate.crt'
            # Change the DER content, retaining a well-formed PEM envelope.
            lines = text.splitlines()
            lines[2] = ('A' if lines[2][0] != 'A' else 'B') + lines[2][1:]
            certificate.write_text('\n'.join(lines))
            with self.assertRaises(ValueError):
                certificate_der(certificate)

    def test_core_pass_is_insufficient_for_requested_trust_test(self):
        core = 'B866F_QEMU_CORE_TESTS_PASSED'
        trust = 'B866F_QEMU_ORIGINAL_CERT_TRUST_PASSED'
        self.assertTrue(classify(core, False, 0)['guest_checks_passed'])
        self.assertFalse(classify(core, False, 0, trust_probe=True)['guest_checks_passed'])
        self.assertTrue(classify(core + trust, False, 0, trust_probe=True)
                        ['original_certificate_keyring_test_passed'])
        self.assertFalse(classify(core + trust + 'Kernel panic', False, 0, trust_probe=True)
                         ['guest_checks_passed'])
        self.assertFalse(classify(core + trust, True, -9, trust_probe=True)['clean_shutdown'])


if __name__ == '__main__':
    unittest.main()
