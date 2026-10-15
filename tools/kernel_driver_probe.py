"""Build-only experiment. Does not install modules, package images or access ADB."""
import json
import struct


def module_metadata(data):
    """Read CRC requirements and absolute exported CRCs from an ARM64 module."""
    if data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
        raise ValueError('Expected ARM64 ELF64 little endian')
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, string_index = struct.unpack_from('<HHH', data, 58)
    if size != 64 or not 0 < string_index < count or offset + size * count > len(data):
        raise ValueError('Invalid ELF section table')
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    def section(h):
        if h[4] + h[5] > len(data):
            raise ValueError('Section outside ELF file')
        return data[h[4]:h[4] + h[5]]
    strings = section(headers[string_index])
    sections = {strings[h[0]:].split(b'\0', 1)[0].decode(): section(h)
                for h in headers if h[1] != 8}  # SHT_NOBITS has no file data.
    versions = sections.get('__versions', b'')
    if not versions or len(versions) % 64:
        raise ValueError('Missing or malformed module versions')
    imports = {versions[i + 8:i + 64].split(b'\0', 1)[0].decode():
               hex(struct.unpack_from('<Q', versions, i)[0])
               for i in range(0, len(versions), 64)}
    exports, weak, unknown = {}, [], []
    for h in headers:
        if h[1] != 2:
            continue
        if h[9] != 24 or h[5] % 24 or h[6] >= count:
            raise ValueError('Invalid ELF symbol table')
        names = section(headers[h[6]])
        for i in range(h[4], h[4] + h[5], h[9]):
            name, info, _, index, value, _ = struct.unpack_from('<IBBHQQ', data, i)
            name = names[name:].split(b'\0', 1)[0].decode()
            if index == 0 and info >> 4 == 2:
                weak.append(name)
            if not name.startswith('__crc_'):
                continue
            if index == 0:
                unknown.append(name[6:])
            elif index == 0xfff1 and value <= 0xffffffff:
                exports[name[6:]] = hex(value)
            else:
                raise ValueError('Unsupported exported CRC encoding')
    return {'symbol_crcs': imports, 'exports': exports,
            'weak_undefined_symbols': sorted(weak), 'unknown_export_crcs': sorted(unknown)}


def check_boundary(kernel_exports, original_imports, original_exports, replacements):
    """Check the proposed provider set, including consumers of replaced modules."""
    imports = {**original_imports, **{k: v['symbol_crcs'] for k, v in replacements.items()}}
    exports = {**original_exports, **{k: v['exports'] for k, v in replacements.items()}}
    providers = {}
    for module, symbols in {'vmlinux': kernel_exports, **exports}.items():
        for name, crc in symbols.items():
            providers.setdefault(name, []).append({'module': module, 'crc': hex(int(crc, 16))})
    failures = {}
    for module, symbols in imports.items():
        weak = set(replacements.get(module, {}).get('weak_undefined_symbols', []))
        problems = []
        for name, required in symbols.items():
            # __versions includes the special loader layout check, not an ordinary import.
            available = providers.get(name, [])
            if not available and name in weak:
                continue
            if not available or any(int(p['crc'], 16) != int(required, 16) for p in available):
                problems.append({'symbol': name, 'required': required, 'providers': available})
        if problems:
            failures[module] = problems
    duplicates = {k: v for k, v in providers.items() if len(v) > 1}
    return {'scope': 'all audited files; alternatives may not be loaded together',
            'replacement_modules': sorted(replacements), 'modules_with_import_problems': failures,
            'duplicate_providers': duplicates,
            'boot_tested': False, 'netflix_tested': False, 'installable': False,
            'limits': 'CRC checks only. No signature, namespace, init-order, userspace ABI or DRM validation.'}


def media_options(kernel, media):
    flags = ['CONFIG_AMLOGIC_MEDIA_VDEC_' + codec + '=m' for codec in (
        'MPEG2_MULTI', 'MPEG4_MULTI', 'VC1', 'H264_MULTI', 'H264_MVC',
        'H265', 'VP9', 'MJPEG_MULTI', 'AVS_MULTI', 'AVS2', 'AV1', 'AV1_T5D')]
    flags += ['CONFIG_AMLOGIC_MEDIA_VENC_' + codec + '=m'
              for codec in ('H264', 'MULTI', 'JPEG', 'COMMON')]
    flags += ['CONFIG_AMLOGIC_MEDIA_V4L_DEC=y']
    includes = [media / 'drivers/include', kernel / 'common_drivers/include',
                kernel / 'common_drivers/include/uapi']
    extra = ' '.join('-I' + str(path) for path in includes) + ' -Wno-error'
    return ['M=' + str(media / 'drivers'), 'EXTRA_CFLAGS=' + extra, *flags]


def preflight(kernel, media, make, run):
    # Official Kbuild directory target. This does not replace full modpost/link checks.
    required = ['frame_provider/decoder/utils/vdec.o',
               'frame_provider/decoder/h264_multi/vmh264.o',
               'frame_provider/decoder/h265/vh265.o',
               'frame_provider/decoder_v4l/h264_multi/vmh264.o',
               'amvdec_ports/aml_vcodec_dec.o', 'amvdec_ports/aml_buf_mgr.o']
    for target in required:
        if not (media / 'drivers' / target).with_suffix('.c').is_file():
            raise RuntimeError('Preflight source missing: ' + target)
    run(make + ['modules_prepare'], 'media-prepare.txt')
    # Keep compiling independent targets so one run reports more than the first error.
    # Kbuild's directory target compiles the configured module objects, without modpost.
    run(make + ['-j2', '-k', *media_options(kernel, media), './'], 'media-object-preflight.txt')
    for target in required:
        if not (media / 'drivers' / target).is_file():
            raise RuntimeError('Expected preflight object missing: ' + target)
    return {'targets': ['./'], 'verified_objects': required,
            'scope': 'configured media objects only; no final modules or full ABI result',
            'installable': False, 'boot_tested': False}


def probe(kernel, output, media, make, run, root, report):
    result = {'status': 'building', 'installable': False, 'boot_tested': False}
    try:
        # Full in-tree modules supply the legitimate modpost symbol table.
        # No KBUILD_MODPOST_WARN, signature bypass or CRC overrides are used.
        run(make + ['-j2', 'modules'], 'native-modules.txt')
        run(make + ['-j2', *media_options(kernel, media), 'modules'], 'media-modules.txt')
        replacements = {}
        paths = sorted(media.rglob('*.ko'))
        wireless = output / 'common_drivers/drivers/wireless/amlogic-wireless.ko'
        if not wireless.is_file():
            raise RuntimeError('Expected rebuilt wireless module missing')
        paths.append(wireless)
        for path in paths:
            if path.name in replacements:
                raise RuntimeError('Duplicate rebuilt module basename: ' + path.name)
            replacements[path.name] = module_metadata(path.read_bytes())
        if not replacements or 'amvdec_mh264.ko' not in replacements:
            raise RuntimeError('Expected H264 decoder missing')
        (report / 'rebuilt-module-metadata.json').write_text(json.dumps(replacements, indent=2))
        kernel_exports = {}
        for line in (output / 'vmlinux.symvers').read_text().splitlines():
            fields = line.split()
            if len(fields) >= 2:
                kernel_exports[fields[1]] = fields[0]
        imports = json.loads((root / 'kernel/vendor-symbol-requirements.json').read_text())
        exports = json.loads((root / 'kernel/module-exports.json').read_text())
        loaded = json.loads((root / 'kernel/module-scope.json').read_text())['loaded']
        boundary = check_boundary(kernel_exports, imports, exports, replacements)
        active = check_boundary(kernel_exports,
            {k: v for k, v in imports.items() if loaded.get(k)},
            {k: v for k, v in exports.items() if loaded.get(k)},
            {k: v for k, v in replacements.items() if loaded.get(k)})
        active['scope'] = ('Captured loaded module names, replacing same-named files only. '
                           'New module names require a separate load/dependency plan.')
        (report / 'replacement-boundary.json').write_text(json.dumps(
            {'all_audited': boundary, 'captured_loaded': active}, indent=2))
        result.update(status='compiled; static boundary checked; runtime unverified',
                      rebuilt_modules=len(replacements),
                      modules_with_import_problems=len(boundary['modules_with_import_problems']),
                      duplicate_provider_symbols=len(boundary['duplicate_providers']),
                      captured_loaded_modules_with_import_problems=len(active['modules_with_import_problems']),
                      captured_loaded_duplicate_providers=len(active['duplicate_providers']))
        return result
    except Exception as exc:
        result.update(status='failed', error=str(exc))
        raise
    finally:
        (report / 'driver-probe.json').write_text(json.dumps(result, indent=2))
        # Text metadata only. Kernel/module/firmware binaries stay on ephemeral runner.
        for label, path in [('native', output / 'Module.symvers'),
                            ('media', media / 'drivers/Module.symvers')]:
            if path.is_file():
                (report / (label + '-modules.symvers')).write_bytes(path.read_bytes())
