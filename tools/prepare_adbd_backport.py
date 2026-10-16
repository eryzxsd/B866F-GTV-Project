"""Prepare a source-only CVE-2026-0073 backport for one pinned AOSP Android 14 file.

This does not build/install adbd, sign an APEX, access a device or change SPL.
The original source is left untouched. Full Android/device validation is pending.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

BASE_COMMIT = '0c88a54d6300ddc98f27bfc3ade96190b53b7c86'
BASE_SHA256 = '3110ba57946b6f08a0b5a27ffe3667006b424dd90557a30822c908e993e11ba6'
FIXED_SHA256 = '66366cd66152a1bc81b01717bade175f9f7ce5a4aea927d0559e4bb1cac1b043'
OLD = b'if (EVP_PKEY_cmp(known_evp.get(), evp_pkey.get())) {'
NEW = b'if (EVP_PKEY_cmp(known_evp.get(), evp_pkey.get()) == 1) {'
UPSTREAM_FIX = '842d331f9e5fb10770a09379e19240daea057dba'


def prepare(source, output):
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != BASE_SHA256 or data.count(OLD) != 1:
        raise ValueError('Input is not the pinned AOSP Android 14 daemon/auth.cpp')
    fixed = data.replace(OLD, NEW)
    if hashlib.sha256(fixed).hexdigest() != FIXED_SHA256:
        raise ValueError('Unexpected backport output')
    if output.exists():
        raise FileExistsError('Output already exists; refusing to overwrite')
    output.mkdir(parents=True)
    (output / 'daemon').mkdir()
    (output / 'daemon/auth.cpp').write_bytes(fixed)
    patch = ''.join(difflib.unified_diff(data.decode().splitlines(keepends=True),
                                       fixed.decode().splitlines(keepends=True),
                                       fromfile='a/daemon/auth.cpp', tofile='b/daemon/auth.cpp'))
    (output / 'adbd-android14-CVE-2026-0073.patch').write_text(patch, encoding='utf-8', newline='\n')
    report = {'scope': 'Source-only Android 14 adbd key comparison backport', 'cve': 'CVE-2026-0073',
              'base_repository': 'https://android.googlesource.com/platform/packages/modules/adb',
              'base_commit': BASE_COMMIT, 'base_file': 'daemon/auth.cpp', 'base_sha256': BASE_SHA256,
              'upstream_fix_commit': UPSTREAM_FIX, 'backported_file_sha256': FIXED_SHA256,
              'change': 'Accept EVP_PKEY_cmp only when its result equals 1; preserve existing logging',
              'source_input_modified': False, 'full_adbd_built': False, 'apex_built': False,
              'apex_signing_compatibility_verified': False, 'stb_accessed': False,
              'installed': False, 'full_may_2026_patch_coverage_established': False}
    (output / 'source-backport-result.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Pinned AOSP daemon/auth.cpp, never a binary')
    parser.add_argument('--output', type=Path, required=True, help='New source staging directory')
    args = parser.parse_args()
    prepare(args.source, args.output)
    print('Pinned source backport prepared; no daemon build or installation')


if __name__ == '__main__':
    main()
