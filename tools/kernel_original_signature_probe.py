"""Opt-in QEMU-only prehashed original-signature crypto experiment.

Does not exercise PKCS7 parsing, original module loading, or B866F hardware.
"""
import hashlib
import json
from pathlib import Path
import re

from kernel_trust_probe import CERTIFICATE_SHA256, CERTIFICATE_SKID

SOURCE_SHA256 = '9bcb52a003f04a415a7bd69d6fe1adee54d371536f8fcd6b31cc41d23926a3e2'
VECTOR_COUNT = 46


def load_vectors(path):
    data = json.loads(Path(path).read_text())
    if (data.get('schema') != 1 or data.get('certificate_sha256') != CERTIFICATE_SHA256 or
            data.get('certificate_skid') != CERTIFICATE_SKID or
            data.get('algorithm') != 'RSA4096-PKCS1v1.5-SHA256-prehashed' or
            data.get('contains_module_bodies') is not False or
            data.get('original_driver_load_tested') is not False):
        raise ValueError('Unexpected signature-vector metadata')
    vectors = data['vectors']
    if len(vectors) != VECTOR_COUNT or len({r['module'] for r in vectors}) != VECTOR_COUNT:
        raise ValueError('Incomplete or duplicate vector scope')
    for row in vectors:
        if set(row) != {'module', 'module_sha256', 'digest_sha256', 'rsa_signature'}:
            raise ValueError('Unexpected vector fields')
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.ko', row['module']):
            raise ValueError('Unsafe vector name')
        for key, size in [('module_sha256', 64), ('digest_sha256', 64), ('rsa_signature', 1024)]:
            if not re.fullmatch('[0-9a-f]{' + str(size) + '}', row[key]):
                raise ValueError('Invalid vector bytes: ' + key)
    return vectors


def instrument(root, kernel):
    vector_path = root / 'kernel/trust/original-signature-vectors.json'
    vectors = load_vectors(vector_path)
    source = kernel / 'certs/system_keyring.c'
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest() != SOURCE_SHA256:
        raise ValueError('Pinned system_keyring.c changed; refusing instrumentation')
    text = original.decode()
    declaration = 'static __init int load_system_certificate_list(void)'
    old_return = '\treturn load_certificate_list(p, size, builtin_trusted_keys);'
    if text.count(declaration) != 1 or text.count(old_return) != 1:
        raise ValueError('Signature probe insertion points are not unique')
    text = text.replace(declaration, '#include "b866f_original_signature.h"\n\n' + declaration)
    text = text.replace(old_return,
                        '\tint ret = load_certificate_list(p, size, builtin_trusted_keys);\n'
                        '\tif (ret)\n\t\treturn ret;\n'
                        '\treturn b866f_original_signature_probe();')
    # Keep C declarations before statements for kernel build style.
    text = text.replace('\tunsigned long size;\n', '\tunsigned long size;\n\tint ret;\n')
    text = text.replace('\tint ret = load_certificate_list(p, size, builtin_trusted_keys);',
                        '\tret = load_certificate_list(p, size, builtin_trusted_keys);')
    header = ['/* Generated from public hashes/signatures, no module bodies. */',
              'struct b866f_signature_vector { const char *name; u8 digest[32]; u8 signature[512]; };',
              'static const struct b866f_signature_vector b866f_signature_vectors[] __initconst = {']
    for row in vectors:
        def byte_array(key):
            return ','.join('0x' + row[key][i:i+2] for i in range(0, len(row[key]), 2))
        header.append('{"' + row['module'] + '", {' + byte_array('digest_sha256') +
                      '}, {' + byte_array('rsa_signature') + '}},')
    header.append('};\n')
    source.write_text(text)
    (kernel / 'certs/b866f_signature_vectors.h').write_text('\n'.join(header))
    probe = (root / 'tools/qemu_original_signature.h').read_bytes()
    (kernel / 'certs/b866f_original_signature.h').write_bytes(probe)
    return {'type': 'QEMU-only built-in prehashed crypto instrumentation',
            'vector_count': len(vectors), 'source_before_sha256': SOURCE_SHA256,
            'source_after_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'probe_sha256': hashlib.sha256(probe).hexdigest(),
            'vectors_sha256': hashlib.sha256(vector_path.read_bytes()).hexdigest(),
            'pkcs7_parser_tested': False, 'original_driver_load_tested': False,
            'enforcement_changed': False, 'installable': False}


def check_log(log, vectors):
    expected = {row['module'] for row in vectors}
    valid = re.findall(r'B866F_ORIGINAL_SIG: ([A-Za-z0-9_-]+\.ko) valid=(-?\d+)', log)
    invalid = re.findall(r'B866F_ORIGINAL_SIG: ([A-Za-z0-9_-]+\.ko) changed_digest=(-?\d+)', log)
    return (len(valid) == len(invalid) == VECTOR_COUNT and
            {name for name, ret in valid if ret == '0'} == expected and
            {name for name, ret in invalid if ret == '-129'} == expected and
            log.count('B866F_QEMU_ORIGINAL_SIGNATURE_CRYPTO_PASSED count=46') == 1 and
            'B866F_QEMU_FAIL:' not in log and 'Kernel panic' not in log)
