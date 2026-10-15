"""Verify local Linux module signatures with a supplied public certificate.

Read-only analysis: no device access, key installation, signing or module loading.
OpenSSL verifies detached signatures; certificate-chain validation is deliberately
separate from this content check. Success never proves candidate-kernel trust.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

MARKER = b'~Module signature appended~\n'


def split_signature(data):
    if not data.endswith(MARKER):
        raise ValueError('Module has no appended signature marker')
    end = len(data) - len(MARKER)
    if end < 12:
        raise ValueError('Truncated signature header')
    algo, digest, kind, signer, key_id, padding, size = struct.unpack(
        '>BBBBB3sI', data[end - 12:end])
    if kind != 2 or any((algo, digest, signer, key_id)) or padding != b'\0' * 3:
        raise ValueError('Unsupported or malformed PKCS7 signature header')
    if not 0 < size < end - 12:
        raise ValueError('Signature size outside module')
    return data[:end - 12 - size], data[end - 12 - size:end - 12]


def audit_module(path, certificate_pem, openssl='openssl', expected_sha256=None):
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise ValueError('Module hash differs from recorded audit: ' + Path(path).name)
    body, signature = split_signature(data)
    with tempfile.TemporaryDirectory(prefix='module-signature-') as directory:
        directory = Path(directory)
        (directory / 'body').write_bytes(body)
        (directory / 'signature').write_bytes(signature)
        result = subprocess.run([
            openssl, 'cms', '-verify', '-binary', '-inform', 'DER',
            '-in', str(directory / 'signature'), '-content', str(directory / 'body'),
            '-certfile', str(Path(certificate_pem).resolve()), '-noverify',
            '-out', str(directory / 'verified-content'),
        ], capture_output=True, text=True, timeout=30)
    detail = result.stderr.strip()
    if result.returncode == 0:
        status = 'signature_verified_with_supplied_certificate'
    elif 'signer certificate not found' in detail.lower():
        status = 'signer_certificate_not_supplied'
    else:
        status = 'signature_verification_failed'
    return {'module': Path(path).name, 'sha256': digest,
            'signature_bytes': len(signature), 'status': status,
            'exit_code': result.returncode}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--certificate', required=True, help='Public certificate in PEM format')
    parser.add_argument('--openssl', default='openssl')
    parser.add_argument('--expected-metadata', type=Path,
                        help='Optional original audit JSON keyed by module filename, including sha256')
    parser.add_argument('--output', type=Path)
    parser.add_argument('modules', type=Path, nargs='+')
    args = parser.parse_args()
    expected = json.loads(args.expected_metadata.read_text()) if args.expected_metadata else None
    records = []
    for path in args.modules:
        expected_hash = expected[path.name]['sha256'] if expected is not None else None
        records.append(audit_module(path, args.certificate, args.openssl, expected_hash))
    report = {'method': 'OpenSSL CMS detached binary signature verification; certificate chain not checked',
              'candidate_kernel_trust_verified': False, 'runtime_load_verified': False,
              'installable': False, 'modules': records}
    output = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(output, encoding='utf-8')
    else:
        print(output, end='')
    return int(any(r['exit_code'] for r in records))


if __name__ == '__main__':
    raise SystemExit(main())
