"""Run extracted old/fixed source guards against real host crypto keys.

Host contract test only. Does not execute the Android daemon or an Android system.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from prepare_adbd_backport import BASE_SHA256, FIXED_SHA256, OLD, NEW


def expression(data, guard):
    if data.count(guard) != 1:
        raise ValueError('Unexpected comparison guard')
    return guard.decode()[4:-3]


BORINGSSL_COMMIT = 'd513cbc24acec3bfefe3fccb0d963bfcea876a03'


def boringssl_profile(android_build):
    root = android_build.resolve()
    source = root / 'external/boringssl'
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if head != BORINGSSL_COMMIT:
        raise ValueError('BoringSSL source is not the pinned Android 14 reference')
    subprocess.run(['git', '-C', str(source), 'diff', '--quiet', 'HEAD', '--', 'src'], check=True)
    archive = root / ('out/soong/.intermediates/external/boringssl/libcrypto_static/'
                      'linux_glibc_x86_64_static/libcrypto_static.a')
    compiler = root / 'prebuilts/clang/host/linux-x86/clang-r487747c/bin/clang++'
    if not archive.is_file() or not compiler.is_file():
        raise ValueError('Build the pinned host BoringSSL archive and compiler first')
    return compiler, source / 'src/include', archive


def run(original, backported, output, android_build=None):
    if os.name != 'posix':
        raise RuntimeError('Requires local Linux C++ compiler and libcrypto development files')
    old, fixed = original.read_bytes(), backported.read_bytes()
    if hashlib.sha256(old).hexdigest() != BASE_SHA256 or hashlib.sha256(fixed).hexdigest() != FIXED_SHA256:
        raise ValueError('Unrecognized source; refusing to compile extracted expressions')
    if output.exists():
        raise FileExistsError('Retaining prior results; choose a new output directory')
    profile = boringssl_profile(android_build) if android_build else None
    template_path = Path(__file__).with_name('adbd_compare_host_test.cpp.in')
    template = template_path.read_text()
    source = template.replace('@OLD_EXPRESSION@', expression(old, OLD)).replace(
        '@FIXED_EXPRESSION@', expression(fixed, NEW))
    output.mkdir(parents=True)
    cpp = output / 'host-test.cpp'
    cpp.write_text(source)
    binary = output / 'host-test'
    compile_command = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                       '-Wno-deprecated-declarations', str(cpp), '-lcrypto', '-o', str(binary)]
    if profile:
        compiler, includes, archive = profile
        compile_command = [str(compiler), '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                           '-Wno-deprecated-declarations', '-fuse-ld=lld', '-I' + str(includes),
                           str(cpp), str(archive), '-pthread', '-ldl', '-o', str(binary)]
    build = subprocess.run(compile_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    (output / 'compile.txt').write_text(build.stdout)
    build.check_returncode()
    execution = subprocess.run([str(binary.resolve())], text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=30)
    (output / 'host-output.txt').write_text(execution.stdout)
    cases = re.findall(r'^ADBD_HOST_CASE:([\w-]+) cmp=(-?\d+) old_accepts=([01]) fixed_accepts=([01])$',
                       execution.stdout, re.MULTILINE)
    if ([r[0] for r in cases] != ['same-key', 'different-key', 'different-key-type'] or
            execution.returncode != 0 or execution.stdout.count('ADBD_HOST_COMPARE_TEST_PASSED') != 1 or
            'ADBD_HOST_FAIL:' in execution.stdout):
        raise RuntimeError('Missing or failed host comparison evidence')
    crypto = re.findall(r'^ADBD_HOST_CRYPTO:(.+)$', execution.stdout, re.MULTILINE)
    if len(crypto) != 1 or (profile and crypto[0] != 'BoringSSL'):
        raise RuntimeError('Unexpected host crypto backend')
    result = {'scope': 'Extracted pinned AOSP guard expressions against a host crypto API',
              'passed': True, 'crypto': crypto[0],
              'aosp_boringssl_host_library_tested': bool(profile),
              'cases': [{'name': n, 'compare_result': int(c), 'old_accepts': a == '1', 'fixed_accepts': b == '1'}
                        for n, c, a, b in cases], 'base_source_sha256': BASE_SHA256,
              'backported_source_sha256': FIXED_SHA256, 'template_sha256': hashlib.sha256(template_path.read_bytes()).hexdigest(),
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'android_boringssl_tested': False, 'full_adbd_built': False, 'android_runtime_tested': False,
              'stb_accessed': False, 'key_material_serialized': False, 'runtime_exploitability_tested': False}
    if profile:
        result.update(boringssl_source_commit=BORINGSSL_COMMIT,
                      host_crypto_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (output / 'host-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(execution.stdout, end='')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', required=True, type=Path)
    parser.add_argument('--backported', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--android-build', type=Path,
                        help='Use the pinned AOSP host BoringSSL archive from this local checkout')
    args = parser.parse_args()
    run(args.original, args.backported, args.output, args.android_build)


if __name__ == '__main__':
    main()
