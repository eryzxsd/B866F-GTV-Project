"""Exercise ordinary socket APIs in offline QEMU using a verified cached Image.

No device access, firmware packaging, driver loading or patch-coverage claim.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

from kernel_baseline import ROOT
from kernel_pkcs7_probe import sha
from kernel_qemu import archive_entry

CHECKS = ('guest-pid1', 'unix-stream-create', 'unix-stream-roundtrip', 'unix-stream-eof',
          'unix-rights-create', 'unix-rights-send', 'unix-rights-receive', 'unix-rights-header',
          'unix-rights-descriptor-usable', 'unix-oob-create', 'unix-oob-peek-consume',
          'unix-oob-following-normal-send', 'unix-oob-following-normal-data', 'epoll-create', 'epoll-register-send',
          'epoll-readable-event', 'epoll-peer-shutdown', 'epoll-unregister', 'vsock-create',
          'vsock-autobind', 'vsock-autobind-concrete-port')


def check_log(log, code, timed_out):
    checks = re.findall(r'^B866F_SOCKET_OK:([\w-]+) errno=0\r?$', log, re.MULTILINE)
    return (checks == list(CHECKS) and log.count('B866F_QEMU_SOCKET_TESTS_PASSED') == 1 and
            'B866F_SOCKET_FAIL:' not in log and 'Kernel panic' not in log and
            'BUG:' not in log and 'WARNING:' not in log and
            'reboot: Power down' in log and code == 0 and not timed_out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing-build', type=Path, required=True)
    args = parser.parse_args()
    if os.name != 'posix' or os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
        raise RuntimeError('Requires existing local Linux diagnostic build')
    existing = args.existing_build.resolve()
    image = existing / 'out/arch/arm64/boot/Image'
    reference = json.loads((ROOT / 'kernel/trust/original-signature-result.json').read_text())
    if sha(image) != reference['kernel_image_sha256'] or sha(existing / 'out/.config') != reference['resolved_config_sha256']:
        raise ValueError('Cached build differs from verified candidate')
    work, report = ROOT / 'build/socket-private', ROOT / 'build/socket-report'
    if work.exists() or report.exists():
        raise RuntimeError('Existing diagnostic retained; no overwrite')
    os.umask(0o077)
    work.mkdir(parents=True)
    report.mkdir(parents=True)
    status = {'status': 'preparing', 'installable': False, 'stb_accessed': False,
              'stb_boot_tested': False, 'android_tested': False, 'security_coverage_established': False,
              'guest_network': 'none', 'kernel_image_sha256': sha(image),
              'resolved_config_sha256': reference['resolved_config_sha256'],
              'source_sha256': {n: sha(ROOT / 'tools' / n) for n in
                                ('kernel_socket_probe.py', 'qemu_socket_init.c')}}
    start = time.monotonic()
    try:
        init = work / 'init'
        with (report / 'init-build.txt').open('w') as log:
            subprocess.run(['aarch64-linux-gnu-gcc', '-static', '-O2', '-Wall', '-Wextra', '-Werror',
                            str(ROOT / 'tools/qemu_socket_init.c'), '-o', str(init)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        ramdisk = archive_entry('dev')
        ramdisk += archive_entry('dev/console', mode=stat.S_IFCHR | 0o600, major=5, minor=1)
        ramdisk += archive_entry('dev/null', mode=stat.S_IFCHR | 0o666, major=1, minor=3)
        ramdisk += archive_entry('init', init.read_bytes(), stat.S_IFREG | 0o500)
        ramdisk += archive_entry('TRAILER!!!', mode=0)
        initrd = work / 'initramfs.cpio.gz'
        initrd.write_bytes(gzip.compress(ramdisk, mtime=0))
        command = ['qemu-system-aarch64', '-machine', 'virt,gic-version=2', '-cpu', 'cortex-a53',
                   '-m', '2048', '-smp', '2', '-accel', 'tcg', '-display', 'none', '-monitor', 'none',
                   '-serial', 'stdio', '-nic', 'none', '-no-reboot', '-kernel', str(image),
                   '-initrd', str(initrd), '-append',
                   'console=ttyAMA0 earlycon=pl011,0x9000000 rdinit=/init panic=-1 nokaslr fiq_check_en=0']
        timed_out = False
        status['status'] = 'running isolated socket API checks'
        (report / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
        with (report / 'qemu-serial.txt').open('w') as log:
            with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT) as process:
                try:
                    code = process.wait(timeout=120)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    process.kill()
                    code = process.wait()
        log = (report / 'qemu-serial.txt').read_text(errors='replace')
        passed = check_log(log, code, timed_out)
        status.update(socket_api_checks_passed=passed, clean_shutdown=passed,
                      qemu_exit_code=code, timed_out=timed_out, check_count=len(CHECKS))
        if not passed:
            raise RuntimeError('Socket checks or clean shutdown incomplete')
        if sha(image) != reference['kernel_image_sha256']:
            raise ValueError('Kernel Image changed during experiment')
        status['status'] = str(len(CHECKS)) + ' ordinary socket API checks passed; clean QEMU shutdown'
        print(status['status'])
    except Exception as error:
        status.update(status='failed or incomplete', error=str(error))
        raise
    finally:
        status['duration_seconds'] = round(time.monotonic() - start, 2)
        (report / 'status.json').write_text(json.dumps(status, indent=2) + '\n')


if __name__ == '__main__':
    main()
