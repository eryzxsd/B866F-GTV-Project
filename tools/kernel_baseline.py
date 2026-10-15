"""Diagnostic source build only. Never creates boot images or accesses a device."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'build/kernel-baseline'
REPORT = ROOT / 'build/kernel-report'
SOURCES = {
    'kernel': ('khadas/linux', '4e557e233b9da219f48b82bfa313f353386097ec'),
    'drivers': ('khadas/common_drivers', '3a11a86a02e759fc57fc79410215f7c0c3a0d8e0'),
}


def fetch_source(name, destination):
    repo, commit = SOURCES[name]
    archive = WORK / (name + '.tar.gz')
    url = f'https://codeload.github.com/{repo}/tar.gz/{commit}'
    urllib.request.urlretrieve(url, archive)
    digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    with tarfile.open(archive) as tf:
        # Only pinned public source; reject traversal, devices and escaping links.
        tf.extractall(WORK / name, filter='data')
    extracted = WORK / name / f'{repo.split("/")[1]}-{commit}'
    extracted.rename(destination)
    archive.unlink()
    return {'repository': repo, 'commit': commit, 'archive_sha256': digest}


def config_map(path):
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line.split('=', 1)
            values[key] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[2:-11]] = 'n'
    return values


def compare(symvers, expected):
    actual = {}
    for line in symvers.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 2:
            actual[fields[1]] = int(fields[0], 16)
    result = {}
    for module, symbols in expected.items():
        rows = {'match': [], 'mismatch': [], 'not_in_vmlinux': []}
        for symbol, crc in symbols.items():
            if symbol not in actual:
                rows['not_in_vmlinux'].append(symbol)
            elif actual[symbol] != int(crc, 16):
                rows['mismatch'].append({'symbol': symbol, 'required': crc,
                                         'built': hex(actual[symbol])})
            else:
                rows['match'].append(symbol)
        result[module] = rows
    return result


def main():
    if WORK.exists():
        raise SystemExit('Use a fresh build/kernel-baseline directory for each run.')
    WORK.mkdir(parents=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    status = {'purpose': 'ABI baseline only; older 5.15.137 source, NOT a security update',
              'installable': False, 'sources': {}, 'status': 'preparing'}
    try:
        kernel = WORK / 'linux'
        status['sources']['kernel'] = fetch_source('kernel', kernel)
        status['sources']['drivers'] = fetch_source('drivers', kernel / 'common_drivers')
        # This pinned Linux tree already includes common_drivers from drivers/Kconfig.
        # No unavailable ZTE project Kconfig is fabricated or included.
        output = WORK / 'out'
        output.mkdir()
        requested = ROOT / 'kernel/b866f-running.config'
        shutil.copyfile(requested, output / '.config')
        # Public Amlogic DVB UAPI headers fail this optional standalone-header
        # test on Ubuntu. It is a build-time test, not a kernel runtime option.
        subprocess.run([str(kernel / 'scripts/config'), '--file', str(output / '.config'),
                        '--disable', 'UAPI_HEADER_TEST'], check=True)
        status['diagnostic_adjustments'] = {
            'CONFIG_UAPI_HEADER_TEST': 'disabled: vendor DVB timespec standalone-header test failure'}
        env = os.environ.copy()
        # This old vendor Makefile supports LLVM=1, not modern LLVM=-18 suffixes.
        env['PATH'] = '/usr/lib/llvm-18/bin:' + env['PATH']
        env.update(KCONFIG_EXT_PREFIX='', COMMON_DRIVERS_DIR='common_drivers',
                   KBUILD_BUILD_USER='diagnostic', KBUILD_BUILD_HOST='github-actions',
                   KBUILD_BUILD_TIMESTAMP='Thu Oct 15 00:00:00 UTC 2026')
        make = ['make', '-C', str(kernel), 'O=' + str(output), 'ARCH=arm64',
                'LLVM=1', 'LLVM_IAS=1', 'CROSS_COMPILE=aarch64-linux-gnu-',
                'CROSS_COMPILE_COMPAT=arm-linux-gnueabi-',
                'KCFLAGS=-Wno-error -Wno-unknown-warning-option']
        def run(args, name):
            with (REPORT / name).open('w') as log:
                # Keep the full artifact log and show periodic real compiler
                # output so long builds can be monitored without guessing.
                last_progress = time.monotonic()
                with subprocess.Popen(args, env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True,
                                      errors='replace', bufsize=1) as proc:
                    for line in proc.stdout:
                        log.write(line)
                        if time.monotonic() - last_progress >= 30 or 'error:' in line:
                            print(f'{name}: {line.rstrip()}', flush=True)
                            last_progress = time.monotonic()
                    proc.wait()
            print(f'{name}: exit {proc.returncode}', flush=True)
            if proc.returncode:
                lines = (REPORT / name).read_text(errors='replace').splitlines()
                errors = [i for i, line in enumerate(lines)
                          if any(token in line for token in ('error:', 'No rule to make', 'fatal error'))]
                for index in errors[:10]:
                    print('\n'.join(lines[max(0, index - 3):index + 5]))
                print('\n'.join(lines[-25:]))
                raise subprocess.CalledProcessError(proc.returncode, args)
        run(make + ['olddefconfig'], 'configure.txt')
        shutil.copyfile(output / '.config', REPORT / 'resolved.config')
        original, resolved = config_map(requested), config_map(output / '.config')
        differences = {k: {'requested': v, 'resolved': resolved.get(k, 'absent')}
                       for k, v in original.items() if resolved.get(k, 'absent') != v}
        (REPORT / 'config-differences.json').write_text(json.dumps(differences, indent=2))
        status['config_differences'] = len(differences)
        for key in ('CONFIG_ARM64', 'CONFIG_MODVERSIONS', 'CONFIG_AMLOGIC_DRIVER',
                    'CONFIG_AMLOGIC_BREAK_GKI', 'CONFIG_AMLOGIC_IN_KERNEL_MODULES'):
            if resolved.get(key) != 'y':
                raise RuntimeError(f'Critical baseline option lost: {key}')
        status['compiler'] = subprocess.check_output(['clang-18', '--version'], text=True)
        # Fail the compatibility gate early rather than building unrelated
        # vendor drivers when the fundamental module_layout CRC differs.
        run(make + ['-j2', 'kernel/module.o'], 'core-abi.txt')
        versions = output / 'kernel/module.o.symversions'
        if not versions.is_file():
            raise RuntimeError('Core object did not produce LTO symbol versions')
        crc_rows = re.findall(r'__crc_(\w+)\s*=\s*(0x[0-9a-fA-F]+)\s*;', versions.read_text())
        crcs = {symbol: int(value, 16) for symbol, value in crc_rows}
        if 'module_layout' not in crcs:
            raise RuntimeError('module_layout CRC missing from core object')
        expected = json.loads((ROOT / 'kernel/vendor-symbol-requirements.json').read_text())
        gate = {'scope': 'module_layout only; not a full driver ABI comparison',
                'built': hex(crcs['module_layout']),
                'required': {name: symbols['module_layout'] for name, symbols in expected.items()},
                'matches_all_samples': all(int(symbols['module_layout'], 16) == crcs['module_layout']
                                           for symbols in expected.values())}
        (REPORT / 'core-abi-gate.json').write_text(json.dumps(gate, indent=2))
        status['core_abi_gate'] = gate
        if not gate['matches_all_samples']:
            status['status'] = 'diagnostic complete: module_layout mismatch; full build skipped'
            markdown = ('# Baseline: tidak kompatibel sebagai pengganti langsung\n\n'
                        f'CRC module_layout hasil build: `{gate["built"]}`.\n\n'
                        + '\n'.join(f'- {name}: membutuhkan `{crc}`'
                                    for name, crc in gate['required'].items())
                        + '\n\nBuild penuh dilewati karena syarat awal ABI sudah berbeda. '
                        'Ini pemeriksaan satu simbol inti, bukan pemeriksaan seluruh driver. '
                        'Keberhasilan workflow berarti eksperimen selesai, bukan kernel kompatibel. '
                        'Tidak ada image kernel, flashing, atau perubahan patch keamanan.\n')
            (REPORT / 'summary.md').write_text(markdown)
            if os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary_file:
                    summary_file.write(markdown)
            print(markdown, flush=True)
            return
        status['status'] = 'compiling'
        (REPORT / 'status.json').write_text(json.dumps(status, indent=2))
        # vmlinux is local to this ephemeral runner; never upload an image.
        run(make + ['-j2', 'vmlinux'], 'compile.txt')
        symvers = output / 'vmlinux.symvers'
        if not symvers.is_file():
            raise RuntimeError('Build did not produce vmlinux.symvers')
        shutil.copyfile(symvers, REPORT / symvers.name)
        expected = json.loads((ROOT / 'kernel/vendor-symbol-requirements.json').read_text())
        comparison = compare(symvers, expected)
        (REPORT / 'abi-comparison.json').write_text(json.dumps(comparison, indent=2))
        summary = ['# Baseline ABI (bukan pembaruan keamanan)', '',
                   '| Modul | Cocok | Berbeda | Tidak ada di vmlinux |',
                   '|---|---:|---:|---:|']
        for module, rows in comparison.items():
            summary.append(f'| {module} | {len(rows["match"])} | {len(rows["mismatch"])} | {len(rows["not_in_vmlinux"])} |')
        summary += ['', 'Simbol yang tidak ada bisa berasal dari modul lain. Kecocokan CRC parsial tidak membuktikan aman untuk boot.',
                    'Sumber publik berbeda dari kernel ZTE; clang 18 juga berbeda dari compiler firmware (clang 17).',
                    'Tidak ada boot.img, flashing, perubahan patch level, atau klaim kompatibilitas penuh.']
        markdown = '\n'.join(summary) + '\n'
        (REPORT / 'summary.md').write_text(markdown)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary_file:
                summary_file.write(markdown)
        status['status'] = 'comparison complete; device compatibility unproven'
    except Exception as exc:
        status['status'] = 'failed'
        status['error'] = str(exc)
        raise
    finally:
        (REPORT / 'status.json').write_text(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
