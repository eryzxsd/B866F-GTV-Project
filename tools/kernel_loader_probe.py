"""Build synthetic loader fixtures inside an ephemeral QEMU runner only."""
import hashlib
from pathlib import Path
import shutil

from kernel_module_signature_audit import MARKER, split_signature


def tamper_signature(data):
    split_signature(data)  # Reject absent/malformed signatures first.
    corrupted = bytearray(data)
    # Flip only the final signature byte, leaving ELF and PKCS7 lengths intact.
    corrupted[-len(MARKER) - 12 - 1] ^= 1
    return bytes(corrupted)


def build(root, kernel, output, work, make, run):
    protected = (output / 'include/generated/gki_module_protected_exports.h').read_text()
    if '"arc4_crypt"' not in protected:
        raise RuntimeError('Fixture export is absent from generated protected list')
    symvers = output / 'vmlinux.symvers'
    if any(line.split()[1] == 'arc4_crypt' for line in symvers.read_text().splitlines() if line.strip()):
        raise RuntimeError('Fixture export already belongs to vmlinux')
    # Image alone does not generate the linker script needed by external .ko
    # files in this vendor tree. Use Kbuild's normal preparation target.
    run(make + ['modules_prepare'], 'loader-modules-prepare.txt')
    if not (output / 'scripts/module.lds').is_file():
        raise RuntimeError('modules_prepare did not generate scripts/module.lds')
    # This fixture imports only kernel symbols. Use the exact generated kernel
    # table for external modpost; never invent CRCs or suppress modpost errors.
    if not (output / 'Module.symvers').exists():
        shutil.copyfile(symvers, output / 'Module.symvers')
    directory = work / 'loader-fixture'
    shutil.copytree(root / 'tools/qemu_loader_fixture', directory)
    run(make + ['-j2', 'M=' + str(directory), 'modules'], 'loader-fixture-build.txt')
    module = directory / 'b866f_policy_probe.ko'
    unsigned = module.read_bytes()
    if unsigned.endswith(MARKER):
        raise RuntimeError('Expected an unsigned fixture before manual signing')
    sign = output / 'scripts/sign-file'
    if not sign.is_file():
        run(make + ['scripts/sign-file'], 'loader-sign-tool.txt')
    fixtures = {'unsigned': unsigned}
    trusted = directory / 'trusted.ko'
    trusted.write_bytes(unsigned)
    run([str(sign), 'sha256', str(output / 'certs/signing_key.pem'),
         str(output / 'certs/signing_key.x509'), str(trusted)], 'loader-sign-trusted.txt')
    fixtures['trusted'] = trusted.read_bytes()
    split_signature(fixtures['trusted'])
    fixtures['tampered'] = tamper_signature(fixtures['trusted'])
    # A separate ephemeral key is deliberately NOT added to the kernel keyring.
    run(['openssl', 'req', '-new', '-x509', '-newkey', 'rsa:2048', '-nodes',
         '-subj', '/CN=Untrusted QEMU fixture only', '-days', '1',
         '-keyout', str(directory / 'untrusted-key.pem'),
         '-out', str(directory / 'untrusted-cert.pem')], 'loader-untrusted-key.txt')
    untrusted = directory / 'untrusted.ko'
    untrusted.write_bytes(unsigned)
    run([str(sign), 'sha256', str(directory / 'untrusted-key.pem'),
         str(directory / 'untrusted-cert.pem'), str(untrusted)], 'loader-sign-untrusted.txt')
    fixtures['untrusted'] = untrusted.read_bytes()
    split_signature(fixtures['untrusted'])
    return fixtures, {'fixture_type': 'synthetic, not an original STB driver',
                      'protected_export': 'arc4_crypt',
                      'generated_protected_header_checked': True,
                      'trusted_signer': 'ephemeral runner kernel build key, not original vendor key',
                      'fixture_sha256': {k: hashlib.sha256(v).hexdigest() for k, v in fixtures.items()},
                      'original_driver_load_tested': False, 'installable': False}
