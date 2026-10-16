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
HID_MODULES = ('hid_roccat', 'hid_roccat_common', 'hid_apple', 'hid_elecom', 'hid_lg_g15',
               'hid_logitech_dj', 'hid_logitech_hidpp', 'hid_logitech', 'hid_magicmouse',
               'hid_microsoft', 'hid_multitouch', 'hid_nintendo', 'hid_picolcd', 'hid_plantronics',
               'hid_prodikeys', 'hid_roccat_arvo', 'hid_roccat_isku', 'hid_roccat_kone',
               'hid_roccat_koneplus', 'hid_roccat_konepure', 'hid_roccat_kovaplus', 'hid_roccat_lua',
               'hid_roccat_pyra', 'hid_roccat_ryos', 'hid_roccat_savu', 'hid_steam', 'hid_uclogic',
               'hid_wiimote', 'wacom')
DEPENDENCIES = {'usbnet': ('mii',), 'cdc_ether': ('usbnet',),
                'cdc_ncm': ('usbnet', 'cdc_ether'), 'r8152': ('mii',), 'zram': ('zsmalloc',)}
DEPENDENCIES.update({name: ('hid_roccat', 'hid_roccat_common') for name in
                     ('hid_roccat_arvo', 'hid_roccat_isku', 'hid_roccat_koneplus',
                      'hid_roccat_konepure', 'hid_roccat_kovaplus', 'hid_roccat_pyra',
                      'hid_roccat_ryos', 'hid_roccat_savu')})
DEPENDENCIES.update(hid_roccat_kone=('hid_roccat',), hid_roccat_lua=('hid_roccat_common',))


def inputs(directory, modules=MODULES):
    audit = json.loads((ROOT / 'kernel/module-signature-result.json').read_text())['modules']
    records = {r['module']: r for r in audit}
    files, hashes = {}, {}
    seen = set()
    for name in modules:
        if any(dep not in seen for dep in DEPENDENCIES.get(name, ())):
            raise ValueError('Invalid dependency order')
        filename = (name.replace('_', '-') if name.startswith('hid_') else name) + '.ko'
        record = records[filename]
        source = Path(directory) / filename
        if record['status'] != 'signature_verified_with_supplied_certificate' or sha(source) != record['sha256']:
            raise ValueError('Unverified original input: ' + name)
        data = source.read_bytes()
        split_signature(data)
        files['original/' + name + '.ko'] = data
        hashes[name] = record['sha256']
        seen.add(name)
    return files, hashes


def check_log(log, modules=MODULES):
    loads = re.findall(r'B866F_ORIGINAL_LOAD: (\w+) result=(-?\d+) errno=(\d+) flags=(\d+)', log)
    live = re.findall(r'B866F_ORIGINAL_LIVE: (\w+)', log)
    unloads = re.findall(r'B866F_ORIGINAL_UNLOAD: (\w+) result=(-?\d+) errno=(\d+)', log)
    return (loads == [(n, '0', '0', '0') for n in modules] and live == list(modules) and
            unloads == [(n, '0', '0') for n in reversed(modules)] and
            re.findall(r'B866F_QEMU_ORIGINAL_LOAD_PASSED count=(\d+)', log) == [str(len(modules))] and
            'B866F_QEMU_FAIL:' not in log and 'Kernel panic' not in log)


def check_zram_log(log, modules=MODULES):
    stats = re.findall(r'B866F_ZRAM_STATS: original=(\d+) compressed=(\d+) allocated=(\d+)', log)
    if len(stats) != 1:
        return False
    original, compressed, allocated = map(int, stats[0])
    return (original == 65536 and 0 < compressed < original and allocated > 0 and
            re.findall(r'B866F_QEMU_ZRAM_IO_PASSED bytes=(\d+)', log) == ['65536'] and
            'B866F_QEMU_OK:zram-drop-block-cache' in log and
            'B866F_QEMU_OK:zram-readback-matches' in log and
            'B866F_QEMU_OK:zram-reset-freed-memory' in log and check_log(log, modules))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing-build', type=Path, required=True)
    parser.add_argument('--module-dir', type=Path, required=True)
    parser.add_argument('--zram-io', action='store_true', help='Also exercise guest-only compression and block I/O')
    parser.add_argument('--hid', action='store_true', help='Also load/unload 29 HID modules without physical HID devices')
    args = parser.parse_args()
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS') or os.name != 'posix':
        raise RuntimeError('Private input experiment requires local Linux, never CI')
    os.umask(0o077)
    prefix = ('hid-' if args.hid else '') + ('zram-io' if args.zram_io else 'original-load')
    work, report = ROOT / ('build/' + prefix + '-private'), ROOT / ('build/' + prefix + '-report')
    if work.exists() or report.exists():
        raise RuntimeError('Existing experiment retained; no overwrite or duplicate')
    existing = args.existing_build.resolve()
    image = existing / 'out/arch/arm64/boot/Image'
    reference = json.loads((ROOT / 'kernel/trust/original-signature-result.json').read_text())
    if sha(image) != reference['kernel_image_sha256']:
        raise ValueError('Existing Image differs from verified local build')
    if sha(existing / 'out/.config') != reference['resolved_config_sha256']:
        raise ValueError('Kernel configuration changed')
    modules = MODULES + HID_MODULES if args.hid else MODULES
    files, hashes = inputs(args.module_dir, modules)
    work.mkdir(parents=True)
    report.mkdir(parents=True)
    status = {'status': 'preparing isolated original-module load test', 'installable': False,
              'stb_boot_tested': False, 'stb_accessed': False, 'original_driver_load_tested': False,
              'hardware_function_tested': False, 'module_order': list(modules),
              'zram_io_requested': args.zram_io,
              'hid_load_requested': args.hid,
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
                            *(['-DB866F_ZRAM_IO_PROBE=1'] if args.zram_io else []),
                            *(['-DB866F_HID_LOAD_PROBE=1'] if args.hid else []),
                            str(ROOT / 'tools/qemu_init.c'), '-o', str(init)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        ramdisk = b''.join(archive_entry(n) for n in ['dev','proc','tmp','original','sys'])
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
        status['original_modules_load_live_unload_passed'] = check_log(log, modules)
        status['zram_compression_io_reset_passed'] = args.zram_io and check_zram_log(log, modules)
        status['original_pkcs7_parser_tested'] = status['original_modules_load_live_unload_passed']
        if not status['clean_shutdown'] or not status['original_modules_load_live_unload_passed']:
            raise RuntimeError('Original module load evidence or clean shutdown incomplete')
        if args.zram_io and not status['zram_compression_io_reset_passed']:
            raise RuntimeError('Zram compression, I/O, cache drop or reset evidence incomplete')
        if sha(image) != reference['kernel_image_sha256']:
            raise ValueError('Image changed during experiment')
        status['status'] = str(len(modules)) + ' original modules loaded, live and unloaded in QEMU'
        if args.zram_io:
            status['status'] += '; zram compression, I/O and reset passed'
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
