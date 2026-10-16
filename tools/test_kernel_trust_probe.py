"""Fail-closed checks for the emulator trust experiment; no device access."""
from pathlib import Path
import tempfile
import struct
import unittest

from kernel_baseline import config_map, ROOT
from kernel_qemu import classify
from kernel_trust_probe import certificate_der, check_config, check_image
from kernel_loader_probe import tamper_signature
from kernel_module_signature_audit import MARKER, split_signature
from kernel_original_signature_probe import load_vectors, check_log, instrument
from kernel_signature_vectors import raw_signature, elements


class TrustProbeChecks(unittest.TestCase):
    def test_signature_probe_requires_every_positive_and_negative_result(self):
        vectors = load_vectors(ROOT / 'kernel/trust/original-signature-vectors.json')
        log = ''.join('B866F_ORIGINAL_SIG: ' + row['module'] + ' valid=0\n' +
                      'B866F_ORIGINAL_SIG: ' + row['module'] + ' changed_digest=-129\n'
                      for row in vectors)
        log += 'B866F_QEMU_ORIGINAL_SIGNATURE_CRYPTO_PASSED count=46\n'
        self.assertTrue(check_log(log, vectors))
        self.assertFalse(check_log(log.replace('changed_digest=-129', 'changed_digest=0', 1), vectors))
        self.assertFalse(check_log(log + 'B866F_ORIGINAL_SIG: cdc_ether.ko valid=0', vectors))
        self.assertFalse(check_log(log.replace('count=46', 'count=45'), vectors))
        core = 'B866F_QEMU_CORE_TESTS_PASSED B866F_QEMU_ORIGINAL_CERT_TRUST_PASSED\n'
        self.assertFalse(classify(core, False, 0, True, signature_probe=True)['clean_shutdown'])
        self.assertTrue(classify(core + log, False, 0, True, signature_probe=True)['clean_shutdown'])
        self.assertFalse(classify(core + log, True, -9, True, signature_probe=True)['clean_shutdown'])

    def test_instrumentation_rejects_unpinned_source(self):
        with tempfile.TemporaryDirectory() as directory:
            kernel = Path(directory)
            (kernel / 'certs').mkdir()
            source = kernel / 'certs/system_keyring.c'
            source.write_text('unexpected source')
            with self.assertRaises(ValueError):
                instrument(ROOT, kernel)
            self.assertEqual(source.read_text(), 'unexpected source')

    def test_cms_parser_rejects_nonminimal_and_truncated_der(self):
        for bad in (b'\x30\x80', b'\x30\x81\x01\x00', b'\x30\x82\x00\x80', b'\x30\x02\x00'):
            with self.assertRaises(ValueError):
                elements(bad)
        with self.assertRaises(ValueError):
            raw_signature(b'\x30\x00', 1)

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

    def test_loader_requires_negative_policy_evidence_and_single_initialization(self):
        base = 'B866F_QEMU_CORE_TESTS_PASSED B866F_QEMU_ORIGINAL_CERT_TRUST_PASSED'
        loader = (' B866F_QEMU_LOADER_POLICY_PASSED B866F_LOADER_FIXTURE_INIT '
                  'B866F_LOADER_FIXTURE_EXIT exports protected symbol arc4_crypt '
                  'exports protected symbol arc4_crypt')
        self.assertFalse(classify(base, False, 0, True, True)['guest_checks_passed'])
        self.assertTrue(classify(base + loader, False, 0, True, True)
                        ['synthetic_loader_policy_test_passed'])
        self.assertFalse(classify(base + loader + ' B866F_LOADER_FIXTURE_INIT', False, 0, True, True)
                         ['guest_checks_passed'])

    def test_tamper_preserves_module_body_and_signature_header(self):
        body = b'example ELF fixture body'
        signature = b'example detached signature'
        header = struct.pack('>BBBBB3sI', 0, 0, 2, 0, 0, b'\0'*3, len(signature))
        original = body + signature + header + MARKER
        tampered = tamper_signature(original)
        actual_body, actual_signature = split_signature(tampered)
        self.assertEqual(actual_body, body)
        self.assertNotEqual(actual_signature, signature)
        self.assertEqual(sum(a != b for a, b in zip(original, tampered)), 1)
        with self.assertRaises(ValueError):
            tamper_signature(body)


if __name__ == '__main__':
    unittest.main()
