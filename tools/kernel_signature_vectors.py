"""Extract public RSA/SHA256 vectors locally; never copy module bodies.

Requires cryptography for independent prehashed verification. Input modules and
their audit stay private. Only hashes and public signatures are written.
"""
import argparse
import hashlib
import json
from pathlib import Path

from kernel_module_signature_audit import split_signature
from kernel_trust_probe import certificate_der, CERTIFICATE_SHA256, CERTIFICATE_SKID


def elements(data):
    """Strict definite-length DER TLVs, retaining tag and content only."""
    result = []
    offset = 0
    while offset < len(data):
        tag = data[offset]
        offset += 1
        if tag & 31 == 31 or offset >= len(data):
            raise ValueError('Unsupported/truncated DER tag')
        size = data[offset]
        offset += 1
        if size & 128:
            count = size & 127
            if not 1 <= count <= 4 or offset + count > len(data) or data[offset] == 0:
                raise ValueError('Invalid DER length')
            size = int.from_bytes(data[offset:offset + count], 'big')
            offset += count
            if size < 128:
                raise ValueError('Nonminimal DER length')
        end = offset + size
        if end > len(data):
            raise ValueError('Truncated DER value')
        result.append((tag, data[offset:end]))
        offset = end
    return result


def contents(data, tags):
    rows = elements(data)
    if [tag for tag, _ in rows] != tags:
        raise ValueError('Unexpected CMS structure (including possible signed attributes)')
    return [value for _, value in rows]


def raw_signature(cms, serial):
    """Only the audited detached, attribute-free RSA/SHA256 CMS form."""
    outer, = contents(cms, [0x30])
    oid, wrapped = contents(outer, [6, 0xa0])
    if oid.hex() != '2a864886f70d010702':
        raise ValueError('Expected SignedData')
    signed, = contents(wrapped, [0x30])
    version, algorithms, encap, signers = contents(signed, [2, 0x31, 0x30, 0x31])
    sha256 = bytes.fromhex('300b0609608648016503040201')
    if version != b'\x01' or algorithms != sha256:
        raise ValueError('Unexpected CMS version/digest')
    data_oid, = contents(encap, [6])  # Embedded content must be absent.
    if data_oid.hex() != '2a864886f70d010701':
        raise ValueError('Expected detached data')
    signer, = contents(signers, [0x30])
    version, issuer_serial, digest_alg, sig_alg, signature = contents(signer, [2, 0x30, 0x30, 0x30, 4])
    issuer, encoded_serial = contents(issuer_serial, [0x30, 2])
    if not issuer or int.from_bytes(encoded_serial, 'big') != serial or version != b'\x01':
        raise ValueError('Unexpected signer')
    if b'\x30' + bytes([len(digest_alg)]) + digest_alg != sha256:
        raise ValueError('Unexpected signer digest')
    if sig_alg.hex() != '06092a864886f70d0101010500' or len(signature) != 512:
        raise ValueError('Expected RSA4096 PKCS1 signature')
    return signature


def generate(module_dir, audit_path, certificate):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, utils
    cert = x509.load_der_x509_certificate(certificate_der(certificate))
    audit = json.loads(Path(audit_path).read_text())
    if audit['certificate_sha256'] != CERTIFICATE_SHA256:
        raise ValueError('Audit certificate mismatch')
    vectors, excluded = [], []
    for row in audit['modules']:
        name = row['module']
        if Path(name).name != name or not name.endswith('.ko'):
            raise ValueError('Invalid module name')
        if row['status'] != 'signature_verified_with_supplied_certificate':
            excluded.append({'module': name, 'reason': row['status']})
            continue
        data = (Path(module_dir) / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Original hash mismatch: ' + name)
        body, cms = split_signature(data)
        signature = raw_signature(cms, cert.serial_number)
        digest = hashlib.sha256(body).digest()
        cert.public_key().verify(signature, digest, padding.PKCS1v15(), utils.Prehashed(hashes.SHA256()))
        vectors.append({'module': name, 'module_sha256': row['sha256'],
                        'digest_sha256': digest.hex(), 'rsa_signature': signature.hex()})
    if len(vectors) != 46 or len({r['module'] for r in vectors}) != 46:
        raise ValueError('Expected the complete 46-module verified scope')
    return {'schema': 1, 'certificate_sha256': CERTIFICATE_SHA256,
            'certificate_skid': CERTIFICATE_SKID, 'algorithm': 'RSA4096-PKCS1v1.5-SHA256-prehashed',
            'contains_module_bodies': False, 'original_driver_load_tested': False,
            'excluded': excluded, 'vectors': vectors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module-dir', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--certificate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(generate(args.module_dir, args.audit, args.certificate), indent=2) + '\n')
