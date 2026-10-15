"""Checks for an opt-in, emulator-only original public-certificate experiment."""
import hashlib
from pathlib import Path
import ssl

CERTIFICATE_SHA256 = '01c0d6ffe7c65ce8a9b42eed55a3bd0f4d8e5fa2b63e1f9aea13e02317e667f8'
CERTIFICATE_SKID = '821976dbe4b8a702b6f3b8804f03a4d517df1f3b'
TRUST_OPTIONS = ('CONFIG_KEYS', 'CONFIG_SYSTEM_TRUSTED_KEYRING', 'CONFIG_MODULE_SIG',
                 'CONFIG_MODULE_SIG_PROTECT', 'CONFIG_MODULE_SIG_FORCE')


def certificate_der(path):
    text = Path(path).read_text(encoding='ascii').strip()
    if (not text.startswith('-----BEGIN CERTIFICATE-----') or
            not text.endswith('-----END CERTIFICATE-----') or
            text.count('-----BEGIN ') != 1):
        raise ValueError('Expected exactly one public certificate')
    der = ssl.PEM_cert_to_DER_cert(text)
    if hashlib.sha256(der).hexdigest() != CERTIFICATE_SHA256:
        raise ValueError('Original public-certificate fingerprint mismatch')
    return der


def check_config(reference, resolved, certificate_path):
    changes = {key: {'before': reference.get(key), 'after': resolved.get(key)}
               for key in TRUST_OPTIONS if reference.get(key) != resolved.get(key)}
    if changes:
        raise ValueError('Signature/trust enforcement options changed: ' + repr(changes))
    for key in TRUST_OPTIONS[:-1]:
        if resolved.get(key) != 'y':
            raise ValueError('Required trust option is not built in: ' + key)
    if resolved.get('CONFIG_SYSTEM_TRUSTED_KEYS') != '"' + str(certificate_path) + '"':
        raise ValueError('Original public certificate is not configured')
    return {'enforcement_options_unchanged': True,
            'certificate_sha256': CERTIFICATE_SHA256,
            'original_module_signer_skid': CERTIFICATE_SKID,
            'stb_configuration_changed': False,
            'original_driver_load_tested': False, 'installable': False}


def check_image(image, der):
    occurrences = Path(image).read_bytes().count(der)
    if occurrences < 1:
        raise ValueError('Original certificate DER missing from built Image')
    return {'certificate_der_occurrences_in_image': occurrences}
