"""Local-only PKCS7 verification of private original module data in QEMU.

Reuses the hash-pinned successful local Image and its build key. Never invokes
ADB or flashes a device. Original code is data for verification, not loaded.
The work directory contains proprietary data: never publish or upload it.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time

from kernel_baseline import ROOT
from kernel_module_signature_audit import split_signature, MARKER
from kernel_qemu import archive_entry, classify


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_pkcs7_log(log, rows):
    expected = {row['module']: '0' if row['status'] == 'signature_verified_with_supplied_certificate'
                else '-126' for row in rows}
    original = re.findall(r'B866F_PKCS7: ([A-Za-z0-9_-]+\.ko) original=(-?\d+)', log)
    changed = re.findall(r'B866F_PKCS7: ([A-Za-z0-9_-]+\.ko) changed_body=(-?\d+)', log)
    truncated = re.findall(r'B866F_PKCS7: ([A-Za-z0-9_-]+\.ko) truncated_cms=(-?\d+)', log)
    trusted = {name for name, value in expected.items() if value == '0'}
    return (len(original) == 47 and dict(original) == expected and
            len(changed) == len(truncated) == 46 and
            {name for name, value in changed if value == '-129'} == trusted and
            {name for name, value in truncated if value == '-74'} == trusted and
            log.count('B866F_QEMU_PKCS7_PASSED trusted=46 unknown=1') == 1 and
            log.count('B866F_PKCS7_FIXTURE_EXIT') == 1 and
            'B866F_QEMU_FAIL:' not in log and 'Kernel panic' not in log)


def private_inputs(directory, rows):
    entries, table, hashes = {}, [], {}
    if len(rows) != 47 or len({r['module'] for r in rows}) != 47:
        raise ValueError('Expected the complete 47-module audited scope')
    for row in rows:
        name = row['module']
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.ko', name):
            raise ValueError('Invalid module name')
        status = row['status']
        if status == 'signature_verified_with_supplied_certificate':
            expected = 0
        elif name == 'amlogic-input.ko' and status == 'signer_certificate_not_supplied':
            expected = -126
        else:
            raise ValueError('Unexpected signature audit status')
        source = Path(directory) / name
        if sha(source) != row['sha256']:
            raise ValueError('Original module hash mismatch: ' + name)
        body, cms = split_signature(source.read_bytes())
        entries['audit/' + name + '.body'] = body
        entries['audit/' + name + '.p7s'] = cms
        table.append('{"' + name + '", ' + str(expected) + '},')
        hashes[name] = {'module_sha256': row['sha256'],
                        'body_sha256': hashlib.sha256(body).hexdigest(),
                        'cms_sha256': hashlib.sha256(cms).hexdigest()}
    if sum(' -126}' in row for row in table) != 1:
        raise ValueError('Expected exactly one unresolved signer')
    header = ('struct probe_case { const char *name; int expected; };\n'
              'static const struct probe_case probe_cases[] = {\n' + '\n'.join(table) + '\n};\n')
    return entries, header, hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing-build', type=Path, required=True)
    parser.add_argument('--module-dir', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('GITHUB_ACTIONS') or os.environ.get('CI'):
        raise RuntimeError('Private original input experiment is local-only; CI is prohibited')
    if os.name != 'posix' or not Path('/proc/sys/kernel/osrelease').is_file():
        raise RuntimeError('Run in the configured local Linux environment')
    os.umask(0o077)
    work, report = ROOT / 'build/pkcs7-local-private', ROOT / 'build/pkcs7-report'
    if work.exists() or report.exists():
        raise RuntimeError('Existing experiment preserved; refusing duplicate/overwrite')
    existing = args.existing_build.resolve()
    kernel, output = existing / 'linux', existing / 'out'
    image = output / 'arch/arm64/boot/Image'
    reference = json.loads((ROOT / 'kernel/trust/original-signature-result.json').read_text())
    if sha(image) != reference['kernel_image_sha256']:
        raise ValueError('Existing Image does not match completed signature experiment')
    if sha(output / '.config') != reference['resolved_config_sha256']:
        raise ValueError('Existing kernel configuration changed')
    if sha(kernel / 'certs/system_keyring.c') != reference['original_signature_probe']['source_after_sha256']:
        raise ValueError('Existing keyring source changed')
    rows = json.loads((ROOT / 'kernel/module-signature-result.json').read_text())['modules']
    entries, header, hashes = private_inputs(args.module_dir, rows)
    work.mkdir(parents=True)
    report.mkdir(parents=True)
    status = {'status': 'preparing local PKCS7 helper', 'installable': False,
              'original_driver_load_tested': False, 'stb_boot_tested': False,
              'private_original_data_used': True, 'private_data_uploaded': False,
              'kernel_image_sha256': sha(image), 'input_hashes': hashes,
              'harness_hashes': {name: sha(ROOT / 'tools' / name) for name in
                                ['kernel_pkcs7_probe.py', 'qemu_init.c', 'qemu_pkcs7_fixture/b866f_pkcs7_probe.c']}}
    started = time.monotonic()
    env = os.environ.copy()
    env['PATH'] = '/usr/lib/llvm-18/bin:' + env['PATH']
    env.update(KCONFIG_EXT_PREFIX='', COMMON_DRIVERS_DIR='common_drivers',
               KBUILD_BUILD_USER='diagnostic', KBUILD_BUILD_HOST='github-actions',
               KBUILD_BUILD_TIMESTAMP='Thu Oct 15 00:00:00 UTC 2026')
    def run(command, name):
        with (report / name).open('w') as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            print((report / name).read_text(errors='replace')[-5000:], flush=True)
            raise RuntimeError(name + ' failed')
    try:
        make = ['make', '-C', str(kernel), 'O=' + str(output), 'ARCH=arm64', 'LLVM=1',
                'LLVM_IAS=1', 'CROSS_COMPILE=aarch64-linux-gnu-',
                'CROSS_COMPILE_COMPAT=arm-linux-gnueabi-', 'KCFLAGS=-Wno-error -Wno-unknown-warning-option']
        release = (output / 'include/generated/utsrelease.h').read_bytes()
        run(make + ['modules_prepare'], 'modules-prepare.txt')
        if (output / 'include/generated/utsrelease.h').read_bytes() != release:
            raise RuntimeError('Module preparation changed kernel release; refusing mismatch')
        symvers = output / 'Module.symvers'
        if not symvers.exists():
            shutil.copyfile(output / 'vmlinux.symvers', symvers)
        if sha(symvers) != sha(output / 'vmlinux.symvers'):
            raise ValueError('External modpost table differs from built kernel table')
        fixture = work / 'fixture'
        shutil.copytree(ROOT / 'tools/qemu_pkcs7_fixture', fixture)
        (fixture / 'probe_cases.h').write_text(header)
        run(make + ['-j2', 'M=' + str(fixture), 'modules'], 'fixture-build.txt')
        module = fixture / 'b866f_pkcs7_probe.ko'
        if module.read_bytes().endswith(MARKER):
            raise RuntimeError('Helper unexpectedly already signed')
        sign = output / 'scripts/sign-file'
        if not sign.is_file():
            run(make + ['scripts/sign-file'], 'sign-tool.txt')
        run([str(sign), 'sha256', str(output / 'certs/signing_key.pem'),
             str(output / 'certs/signing_key.x509'), str(module)], 'sign-helper.txt')
        split_signature(module.read_bytes())
        status['helper_sha256'] = sha(module)
        init = work / 'init'
        run(['aarch64-linux-gnu-gcc', '-static', '-O2', '-Wall', '-Wextra', '-Werror',
             '-DB866F_TRUST_PROBE=1', '-DB866F_PKCS7_PROBE=1',
             str(ROOT / 'tools/qemu_init.c'), '-o', str(init)], 'init-build.txt')
        ramdisk = b''.join(archive_entry(name) for name in ['dev','proc','tmp','audit'])
        ramdisk += archive_entry('dev/console', mode=stat.S_IFCHR | 0o600, major=5, minor=1)
        ramdisk += archive_entry('init', init.read_bytes(), stat.S_IFREG | 0o500)
        ramdisk += archive_entry('pkcs7-probe.ko', module.read_bytes(), stat.S_IFREG | 0o400)
        for name, data in entries.items():
            ramdisk += archive_entry(name, data, stat.S_IFREG | 0o400)
        ramdisk += archive_entry('TRAILER!!!', mode=0)
        ramdisk_path = work / 'private-initramfs.cpio.gz'
        ramdisk_path.write_bytes(gzip.compress(ramdisk, mtime=0))
        status['status'] = 'running local QEMU PKCS7 experiment'
        (report / 'status.json').write_text(json.dumps(status, indent=2))
        command = ['qemu-system-aarch64', '-machine', 'virt,gic-version=2', '-cpu','cortex-a53',
                   '-m','2048','-smp','2','-accel','tcg','-display','none','-monitor','none',
                   '-serial','stdio','-nic','none','-no-reboot','-kernel',str(image),
                   '-initrd',str(ramdisk_path),'-append',
                   'console=ttyAMA0 earlycon=pl011,0x9000000 rdinit=/init panic=-1 nokaslr fiq_check_en=0']
        timed_out = False
        with (report / 'qemu-serial.txt').open('w') as log:
            with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT) as process:
                try:
                    code = process.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    process.kill()
                    code = process.wait()
        log = (report / 'qemu-serial.txt').read_text(errors='replace')
        status.update(classify(log, timed_out, code, trust_probe=True, signature_probe=True))
        status['pkcs7_parser_and_verifier_passed'] = check_pkcs7_log(log, rows)
        status['original_pkcs7_parser_tested'] = status['pkcs7_parser_and_verifier_passed']
        status['original_module_signature_header_tested_in_kernel'] = False
        if not status['clean_shutdown'] or not status['pkcs7_parser_and_verifier_passed']:
            raise RuntimeError('PKCS7 evidence or clean shutdown incomplete')
        if sha(image) != reference['kernel_image_sha256']:
            raise RuntimeError('Existing Image changed during experiment')
        status['status'] = 'local PKCS7 parser and verifier checks passed'
        print(status['status'], flush=True)
    except Exception as error:
        status['status'] = 'failed or incomplete'
        status['error'] = str(error)
        raise
    finally:
        status['duration_seconds'] = round(time.monotonic() - started, 2)
        (report / 'status.json').write_text(json.dumps(status, indent=2) + '\n')


if __name__ == '__main__':
    main()
