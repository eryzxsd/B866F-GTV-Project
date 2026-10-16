# Local PKCS7 verifier fixture

This GPL test helper runs only in QEMU. It reads original signed module bodies
and their detached PKCS7 signatures from a private initramfs as data. It calls
the pinned kernel's `verify_pkcs7_signature` with the same trust selector and
usage as `kernel/module_signing.c`. It does not call init_module/finit_module
on any original module or execute original driver code.

The helper itself is compiled normally against the existing kernel, with real
modpost CRC/namespace checks, then signed using that local build's temporary
key. Only the helper is loaded/unloaded by the test init. No signature
enforcement, namespace, vermagic, or version checks are bypassed.

Use `tools/kernel_pkcs7_probe.py --existing-build PATH --module-dir PRIVATE_PATH`
on the configured local Linux host. It requires the exact completed Image,
configuration, keyring source, and full original input hashes. It refuses CI
execution and existing experiment directories. It does not rebuild the Image.
Failed attempts must be retained separately before a corrected run.

**Never upload `build/pkcs7-local-private` or its initramfs.** It contains private
original module data. Build keys also remain local in the existing build tree.
Only source, public hashes, and reviewed text results may be published. The
ordinary QEMU workflow runs source/guard checks but does not run this private
input experiment or acquire original binaries.
