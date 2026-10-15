"""Build/test a QEMU variant. No STB access, firmware packaging or image upload."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import time

import kernel_baseline as baseline

ROOT = baseline.ROOT
REPORT = ROOT / 'build/qemu-report'


def archive_entry(name, data=b'', mode=stat.S_IFDIR | 0o755, major=0, minor=0):
    encoded = name.encode() + b'\0'
    fields = [0, mode, 0, 0, 1, 0, len(data), 0, 0, major, minor, len(encoded), 0]
    result = b'070701' + ''.join(f'{x:08x}' for x in fields).encode() + encoded
    result += b'\0' * (-len(result) % 4)
    result += data
    return result + b'\0' * (-len(result) % 4)


def classify(log, timed_out, returncode):
    reached = 'B866F_QEMU_CORE_TESTS_PASSED' in log
    failed = 'B866F_QEMU_FAIL:' in log or 'Kernel panic' in log
    return {'guest_checks_passed': reached and not failed,
            'clean_shutdown': reached and not failed and not timed_out and returncode == 0,
            'timed_out': timed_out, 'qemu_exit_code': returncode,
            'stb_boot_tested': False, 'installable': False}


def main():
    if baseline.SOURCE_KEY != 'coreelec-5.15.196':
        raise RuntimeError('This test requires the pinned CoreELEC source')
    if baseline.WORK.exists():
        raise RuntimeError('Requires a fresh runner build directory')
    baseline.WORK.mkdir(parents=True)
    REPORT.mkdir(parents=True)
    status = {'status': 'preparing', 'installable': False, 'stb_boot_tested': False,
              'configuration': 'separate QEMU variant, not the paired-driver configuration',
              'coverage': 'core Linux boot/syscalls only; Amlogic hardware and Android untested'}
    env = os.environ.copy()
    env['PATH'] = '/usr/lib/llvm-18/bin:' + env['PATH']
    env.update(KCONFIG_EXT_PREFIX='', COMMON_DRIVERS_DIR='common_drivers',
               KBUILD_BUILD_USER='diagnostic', KBUILD_BUILD_HOST='github-actions',
               KBUILD_BUILD_TIMESTAMP='Thu Oct 15 00:00:00 UTC 2026')

    def run(command, log_name, cwd=None):
        last = time.monotonic()
        with (REPORT / log_name).open('w') as log:
            with subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors='replace') as process:
                for line in process.stdout:
                    log.write(line)
                    if time.monotonic() - last > 30 or 'error:' in line:
                        print(log_name + ': ' + line.rstrip(), flush=True)
                        last = time.monotonic()
                code = process.wait()
        if code:
            print((REPORT / log_name).read_text(errors='replace')[-6000:])
            raise RuntimeError(log_name + ' failed')

    try:
        kernel = baseline.WORK / 'linux'
        status['sources'] = {'kernel': baseline.fetch_source('kernel', kernel),
                             'drivers': baseline.fetch_source('drivers', kernel / 'common_drivers')}
        status['patches'] = {}
        for name in ('coreelec-video-capture-guards.patch', 'coreelec-gpio-key-builtin.patch',
                     'coreelec-si2183-mux-dependency.patch'):
            patch = ROOT / 'kernel/patches' / name
            run(['patch', '--batch', '--forward', '--dry-run', '-p1', '-i', str(patch)],
                name + '.check.txt', cwd=kernel)
            run(['patch', '--batch', '--forward', '-p1', '-i', str(patch)],
                name + '.apply.txt', cwd=kernel)
            status['patches'][name] = hashlib.sha256(patch.read_bytes()).hexdigest()
        output = baseline.WORK / 'out'
        output.mkdir()
        requested = ROOT / 'kernel/b866f-running.config'
        shutil.copyfile(requested, output / '.config')
        run([str(kernel / 'scripts/config'), '--file', str(output / '.config'),
             '--disable', 'UAPI_HEADER_TEST', '--disable', 'AMLOGIC_WATERMARK',
             '--enable', 'SERIAL_AMBA_PL011',
             '--enable', 'SERIAL_AMBA_PL011_CONSOLE'], 'qemu-config-fragment.txt')
        make = ['make', '-C', str(kernel), 'O=' + str(output), 'ARCH=arm64', 'LLVM=1',
                'LLVM_IAS=1', 'CROSS_COMPILE=aarch64-linux-gnu-',
                'CROSS_COMPILE_COMPAT=arm-linux-gnueabi-', 'KCFLAGS=-Wno-error -Wno-unknown-warning-option']
        run(make + ['olddefconfig'], 'configure.txt')
        before, after = baseline.config_map(requested), baseline.config_map(output / '.config')
        status['config_changes'] = {key: {'before': before.get(key), 'after': after.get(key)}
                                    for key in sorted(before.keys() | after.keys())
                                    if before.get(key) != after.get(key)}
        # Preserve debug exports needed by the vendor GPIO driver. Use the
        # vendor's existing boot option to skip its unsupported FIQ SMC in QEMU.
        if after.get('CONFIG_AMLOGIC_DEBUG') != 'y':
            raise RuntimeError('Vendor debug exports must remain built in')
        if after.get('CONFIG_AMLOGIC_WATERMARK') != 'n':
            raise RuntimeError('QEMU-only watermark exclusion did not resolve')
        lockup = (kernel / 'common_drivers/drivers/debug/lockup.c').read_text()
        if '__setup("fiq_check_en=", fiq_check_en_setup)' not in lockup or 'if (!fiq_check_en)' not in lockup:
            raise RuntimeError('Pinned vendor FIQ opt-out is unavailable')
        status['qemu_exclusions'] = {
            'CONFIG_AMLOGIC_WATERMARK': 'No vendor watermark secure-monitor '
                                        'service on QEMU virt; driver untested',
            'fiq_check_en=0': 'Skip vendor FIQ debug SMC 0x820000f1 in QEMU; '
                              'keep AMLOGIC_DEBUG and GPIO exports enabled',
        }
        for key in ('CONFIG_SERIAL_AMBA_PL011', 'CONFIG_SERIAL_AMBA_PL011_CONSOLE',
                    'CONFIG_BLK_DEV_INITRD', 'CONFIG_RD_GZIP', 'CONFIG_ARM_GIC', 'CONFIG_ARM_PSCI_FW'):
            if after.get(key) != 'y':
                raise RuntimeError('Required QEMU option not built in: ' + key)
        shutil.copyfile(output / '.config', REPORT / 'qemu-resolved.config')
        status['status'] = 'building QEMU kernel variant'
        (REPORT / 'status.json').write_text(json.dumps(status, indent=2))
        run(make + ['-j2', 'Image'], 'compile.txt')
        image = output / 'arch/arm64/boot/Image'
        status['kernel_image_sha256'] = hashlib.sha256(image.read_bytes()).hexdigest()
        init = baseline.WORK / 'init'
        run(['aarch64-linux-gnu-gcc', '-static', '-O2', '-Wall', '-Wextra', '-Werror',
             str(ROOT / 'tools/qemu_init.c'), '-o', str(init)], 'init-build.txt')
        ramdisk = b''.join(archive_entry(name) for name in ('dev', 'proc', 'tmp'))
        ramdisk += archive_entry('dev/console', mode=stat.S_IFCHR | 0o600, major=5, minor=1)
        ramdisk += archive_entry('init', init.read_bytes(), stat.S_IFREG | 0o755)
        ramdisk += archive_entry('TRAILER!!!', mode=0)
        ramdisk_path = baseline.WORK / 'initramfs.cpio.gz'
        ramdisk_path.write_bytes(gzip.compress(ramdisk, mtime=0))
        command = ['qemu-system-aarch64', '-machine', 'virt,gic-version=2', '-cpu', 'cortex-a53',
                   '-m', '2048', '-smp', '2', '-accel', 'tcg', '-display', 'none',
                   '-monitor', 'none', '-serial', 'stdio', '-nic', 'none', '-no-reboot',
                   '-kernel', str(image), '-initrd', str(ramdisk_path),
                   '-append', 'console=ttyAMA0 earlycon=pl011,0x9000000 rdinit=/init panic=-1 nokaslr fiq_check_en=0']
        status['qemu_command'] = command
        timed_out = False
        with (REPORT / 'qemu-serial.txt').open('w') as log:
            with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT) as process:
                try:
                    code = process.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    process.kill()
                    code = process.wait()
        result = classify((REPORT / 'qemu-serial.txt').read_text(errors='replace'), timed_out, code)
        status.update(result)
        status['status'] = 'QEMU core checks passed' if result['guest_checks_passed'] else 'QEMU boot test failed'
        print(json.dumps(result, indent=2))
        if not result['guest_checks_passed']:
            raise RuntimeError('Guest failed to complete core tests; inspect serial log')
    except Exception as error:
        status['error'] = str(error)
        status['status'] = 'failed or incomplete; not STB validation'
        raise
    finally:
        (REPORT / 'status.json').write_text(json.dumps(status, indent=2))
        summary = ('# Uji QEMU, bukan validasi STB\n\nStatus: ' + status['status'] +
                   '\n\nKonfigurasi emulator terpisah. Tidak menguji driver B866F, HDMI, DRM, Netflix, '
                   'AVB atau kelengkapan patch Mei 2026. Tidak mengunggah image atau melakukan flashing.\n')
        (REPORT / 'summary.md').write_text(summary)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
                output.write(summary)


if __name__ == '__main__':
    main()
