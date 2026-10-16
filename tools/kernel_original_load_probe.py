"""Local-only load/unload of eight private original modules in isolated QEMU.

Never use on an STB. No device access, no network in the guest, no forced module
flags, no signature/CRC bypass. Private initramfs/binaries must not be uploaded.
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
from kernel_qemu import archive_entry, classify
from kernel_module_signature_audit import split_signature

MODULES = ('libarc4', 'mii', 'usbnet', 'cdc_ether', 'cdc_ncm', 'r8152', 'zsmalloc', 'zram')
DEPENDENCIES = {'usbnet': ('mii',), 'cdc_ether': ('usbnet',),
                'cdc_ncm': ('usbnet', 'cdc_ether'), 'r8152': ('mii',), 'zram': ('zsmalloc',)}


def inputs(directory):
    audit = json.loads((ROOT / 'kernel/module-signature-result.json').read_text())['modules']
    records = {r['module']: r for r in audit}
    files, hashes = {}, {}
    seen = set()
    for name in MODULES:
        if any(dep not in seen for dep in DEPENDENCIES.get(name, ())):
            raise ValueError('Invalid dependency order')
        record = records[name + '.ko']
        source = Path(directory) / (name + '.ko')
        if record['status'] != 'signature_verified_with_supplied_certificate' or sha(source) != record['sha256']:
            raise ValueError('Unverified original input: ' + name)
        data = source.read_bytes()
        split_signature(data)
        files['original/' + name + '.ko'] = data
        hashes[name] = record['sha256']
        seen.add(name)
    return files, hashes


def check_log(log):
    loads = re.findall(r'B866F_ORIGINAL_LOAD: (\w+) result=(-?\d+) errno=(\d+) flags=(\d+)', log)
    live = re.findall(r'B866F_ORIGINAL_LIVE: (\w+)', log)
    unloads = re.findall(r'B866F_ORIGINAL_UNLOAD: (\w+) result=(-?\d+) errno=(\d+)', log)
    return (loads == [(n, '0', '0', '0') for n in MODULES] and live == list(MODULES) and
            unloads == [(n, '0', '0') for n in reversed(MODULES)] and
            log.count('B866F_QEMU_ORIGINAL_LOAD_PASSED count=8') == 1 and
            'B866F_QEMU_FAIL:' not in log and 'Kernel panic' not in log)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing-build', type=Path, required=True)
    parser.add_argument('--module-dir', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS') or os.name != 'posix':
        raise RuntimeError('Private input experiment requires local Linux, never CI')
    os.umask(0o077)
    work, report = ROOT / 'build/original-load-private', ROOT / 'build/original-load-report'
    if work.exists() or report.exists():
        raise RuntimeError('Existing experiment retained; no overwrite or duplicate')
    existing = args.existing_build.resolve()
    image = existing / 'out/arch/arm64/boot/Image'
    reference = json.loads((ROOT / 'kernel/trust/original-signature-result.json').read_text())
    if sha(image) != reference['kernel_image_sha256']:
        raise ValueError('Existing Image differs from verified local build')
    if sha(existing / 'out/.config') != reference['resolved_config_sha256']:
        raise ValueError('Kernel configuration changed')
    files, hashes = inputs(args.module_dir)
    work.mkdir(parents=True)
    report.mkdir(parents=True)
    status = {'status': 'preparing isolated original-module load test', 'installable': False,
              'stb_boot_tested': False, 'stb_accessed': False, 'original_driver_load_tested': False,
              'hardware_function_tested': False, 'module_order': list(MODULES),
              'input_sha256': hashes, 'kernel_image_sha256': sha(image),
              'source_sha256': {n: sha(ROOT / 'tools' / n) for n in
                                ('kernel_original_load_probe.py', 'qemu_init.c')},
              'finit_module_flags': 0, 'forced_unload': False, 'guest_network': 'none',
              'original_binaries_uploaded': False}
    start = time.monotonic()
    try:
        init = work / 'init'
        with (report / 'init-build.txt').open('w') as log:
            subprocess.run(['aarch64-linux-gnu-gcc', '-static', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DB866F_TRUST_PROBE=1', '-DB866F_ORIGINAL_LOAD_PROBE=1',
                            str(ROOT / 'tools/qemu_init.c'), '-o', str(init)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        ramdisk = b''.join(archive_entry(n) for n in ['dev','proc','tmp','original'])
        ramdisk += archive_entry('dev/console', mode=stat.S_IFCHR | 0o600, major=5, minor=1)
        ramdisk += archive_entry('init', init.read_bytes(), stat.S_IFREG | 0o500)
        for name, data in files.items():
            ramdisk += archive_entry(name, data, stat.S_IFREG | 0o400)
        ramdisk += archive_entry('TRAILER!!!', mode=0)
        ramdisk_path = work / 'private-initramfs.cpio.gz'
        ramdisk_path.write_bytes(gzip.compress(ramdisk, mtime=0))
        command = ['qemu-system-aarch64', '-machine','virt,gic-version=2','-cpu','cortex-a53',
                   '-m','2048','-smp','2','-accel','tcg','-display','none','-monitor','none',
                   '-serial','stdio','-nic','none','-no-reboot','-kernel',str(image),
                   '-initrd',str(ramdisk_path),'-append',
                   'console=ttyAMA0 earlycon=pl011,0x9000000 rdinit=/init panic=-1 nokaslr fiq_check_en=0']
        status['status'] = 'running isolated original-module load test'
        (report / 'status.json').write_text(json.dumps(status, indent=2))
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
        status['original_driver_load_tested'] = 'B866F_ORIGINAL_LOAD:' in log
        status['eight_original_modules_load_live_unload_passed'] = check_log(log)
        if not status['clean_shutdown'] or not status['eight_original_modules_load_live_unload_passed']:
            raise RuntimeError('Original module load evidence or clean shutdown incomplete')
        if sha(image) != reference['kernel_image_sha256']:
            raise ValueError('Image changed during experiment')
        status['status'] = 'eight original modules loaded, live and unloaded in QEMU'
        print(status['status'], flush=True)
    except Exception as error:
        status['error'] = str(error)
        status['status'] = 'failed or incomplete'
        raise
    finally:
        status['duration_seconds'] = round(time.monotonic() - start, 2)
        (report / 'status.json').write_text(json.dumps(status, indent=2) + '\n')


if __name__ == '__main__':
    main()
