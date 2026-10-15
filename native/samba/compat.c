/* Process-local compatibility for the unmodified Termux Samba binaries.
 * Set supported Samba runtime paths and use TDB's fcntl locking fallback:
 * This Android compatibility mode avoids process-shared robust mutexes.
 * This is loaded only by the Samba commands, never globally into Android.
 */
extern const char *set_dyn_MODULESDIR(const char *) __attribute__((weak));
extern const char *set_dyn_CODEPAGEDIR(const char *) __attribute__((weak));
extern const char *set_dyn_BINDIR(const char *) __attribute__((weak));
extern const char *set_dyn_SBINDIR(const char *) __attribute__((weak));
extern const char *set_dyn_SAMBA_LIBEXECDIR(const char *) __attribute__((weak));

__attribute__((constructor)) static void b866f_samba_paths(void) {
    if (set_dyn_MODULESDIR) set_dyn_MODULESDIR("/data/adb/modules/ebs_gtv_system_app/samba/runtime/lib/samba");
    if (set_dyn_CODEPAGEDIR) set_dyn_CODEPAGEDIR("/data/adb/modules/ebs_gtv_system_app/samba/runtime/share/samba");
    if (set_dyn_BINDIR) set_dyn_BINDIR("/data/adb/modules/ebs_gtv_system_app/samba/runtime/bin");
    if (set_dyn_SBINDIR) set_dyn_SBINDIR("/data/adb/modules/ebs_gtv_system_app/samba/runtime/bin");
    if (set_dyn_SAMBA_LIBEXECDIR) set_dyn_SAMBA_LIBEXECDIR("/data/adb/modules/ebs_gtv_system_app/samba/runtime/libexec/samba");
}

int tdb_runtime_check_for_robust_mutexes(void) { return 0; }
