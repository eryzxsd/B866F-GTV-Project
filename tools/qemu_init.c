/* Minimal offline Linux smoke test; no Android files or device access. */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>
#if defined(B866F_TRUST_PROBE) || defined(B866F_ORIGINAL_LOAD_PROBE)
#include <errno.h>
#include <linux/keyctl.h>
#include <sys/syscall.h>
#endif

static void require(int condition, const char *test) {
    if (!condition) {
        printf("B866F_QEMU_FAIL:%s\n", test);
        fflush(stdout);
        reboot(RB_POWER_OFF);
        for (;;) pause();
    }
    printf("B866F_QEMU_OK:%s\n", test);
    fflush(stdout);
}

#ifdef B866F_TRUST_PROBE
static void check_original_certificate(void) {
    /* Discover the root-owned built-in ring, then inspect its member IDs.
     * Merely finding a certificate elsewhere in /proc/keys is insufficient. */
    FILE *keys = fopen("/proc/keys", "r");
    require(keys != NULL, "trust-key-list-readable");
    char line[2048];
    unsigned int ring = 0;
    while (fgets(line, sizeof(line), keys)) {
        if (strstr(line, "keyring") && strstr(line, ".builtin_trusted_keys:")) {
            require(sscanf(line, "%x", &ring) == 1, "builtin-keyring-id");
            break;
        }
    }
    fclose(keys);
    require(ring != 0, "builtin-keyring-found");
    errno = 0;
    long certificate = syscall(SYS_keyctl, KEYCTL_SEARCH, (int)ring, "asymmetric",
                               "id:821976dbe4b8a702b6f3b8804f03a4d517df1f3b", 0);
    printf("Trust search diagnostic: result=%ld errno=%d\n", certificate, errno);
    /* certs/common.c grants root VIEW/READ, but not SEARCH on each built-in
     * certificate. A userspace SEARCH can therefore fail even after the kernel
     * has loaded the key. Do not relax permissions: read the ring's actual
     * member IDs, then describe those keys using existing VIEW permission. */
    int members[1024];
    long bytes = syscall(SYS_keyctl, KEYCTL_READ, (int)ring, members, sizeof(members));
    require(bytes >= 0 && (unsigned long)bytes <= sizeof(members) &&
            (unsigned long)bytes % sizeof(members[0]) == 0, "builtin-keyring-members-readable");
    int found = 0;
    for (long i = 0; i < bytes / (long)sizeof(members[0]); i++) {
        char description[2048];
        long size = syscall(SYS_keyctl, KEYCTL_DESCRIBE, members[i], description, sizeof(description));
        if (size <= 0 || (unsigned long)size > sizeof(description)) continue;
        description[size - 1] = '\0';
        if (strncmp(description, "asymmetric;", 11)) continue;
        const char *identifier = strrchr(description, ':');
        if (identifier && !strcmp(identifier, ": 821976dbe4b8a702b6f3b8804f03a4d517df1f3b")) {
            found = 1;
            break;
        }
    }
    require(found, "original-certificate-member-of-builtin-trusted-keyring");
    puts("B866F_QEMU_ORIGINAL_CERT_TRUST_PASSED");
}
#endif

#ifdef B866F_LOADER_PROBE
static long load_fixture(const char *path, int *error) {
    int file = open(path, O_RDONLY);
    require(file >= 0, "loader-fixture-file-readable");
    errno = 0;
    long result = syscall(SYS_finit_module, file, "", 0);
    *error = errno;
    close(file);
    printf("Loader fixture %s: result=%ld errno=%d\n", path, result, *error);
    return result;
}

static void check_loader_policy(void) {
    int error;
    require(load_fixture("/trusted.ko", &error) == 0, "trusted-synthetic-module-load");
    require(syscall(SYS_delete_module, "b866f_policy_probe", O_NONBLOCK) == 0,
            "trusted-synthetic-module-unload");
    long result = load_fixture("/unsigned.ko", &error);
    require(result == -1 && error == EACCES, "unsigned-protected-export-rejected");
    result = load_fixture("/untrusted.ko", &error);
    require(result == -1 && error == EACCES, "untrusted-signer-protected-export-rejected");
    result = load_fixture("/tampered.ko", &error);
    /* rsa-pkcs1pad.c returns EBADMSG for damaged padding, or EKEYREJECTED
     * for a digest mismatch. Both are fatal signature verification failures. */
    require(result == -1 && (error == EKEYREJECTED || error == EBADMSG),
            "tampered-signature-rejected");
    puts("B866F_QEMU_LOADER_POLICY_PASSED");
}
#endif

#ifdef B866F_PKCS7_PROBE
static void check_pkcs7(void) {
    int file = open("/pkcs7-probe.ko", O_RDONLY);
    require(file >= 0, "pkcs7-helper-readable");
    require(syscall(SYS_finit_module, file, "", 0) == 0, "pkcs7-helper-load-and-checks");
    close(file);
    require(syscall(SYS_delete_module, "b866f_pkcs7_probe", O_NONBLOCK) == 0,
            "pkcs7-helper-unload");
}
#endif

#ifdef B866F_ORIGINAL_LOAD_PROBE
static const char *original_modules[] = {
    "libarc4", "mii", "usbnet", "cdc_ether", "cdc_ncm", "r8152", "zsmalloc", "zram"
};

static int original_live(const char *name) {
    FILE *file = fopen("/proc/modules", "r");
    require(file != NULL, "original-proc-modules-readable");
    char line[1024], found_name[128], state[32], dependencies[512];
    unsigned long size;
    unsigned int references;
    int found = 0;
    while (fgets(line, sizeof(line), file)) {
        if (sscanf(line, "%127s %lu %u %511s %31s", found_name, &size,
                   &references, dependencies, state) == 5 && !strcmp(found_name, name)) {
            found = size > 0 && !strcmp(state, "Live");
            break;
        }
    }
    fclose(file);
    return found;
}

static void check_original_load(void) {
    const size_t count = sizeof(original_modules) / sizeof(original_modules[0]);
    for (size_t i = 0; i < count; i++) {
        char path[160];
        snprintf(path, sizeof(path), "/original/%s.ko", original_modules[i]);
        int file = open(path, O_RDONLY);
        require(file >= 0, "original-module-file-readable");
        errno = 0;
        long result = syscall(SYS_finit_module, file, "", 0);
        int error = errno;
        close(file);
        printf("B866F_ORIGINAL_LOAD: %s result=%ld errno=%d flags=0\n",
               original_modules[i], result, error);
        require(result == 0, "original-module-loaded");
        require(original_live(original_modules[i]), "original-module-live");
        printf("B866F_ORIGINAL_LIVE: %s\n", original_modules[i]);
    }
    for (size_t i = count; i > 0; i--) {
        const char *name = original_modules[i - 1];
        errno = 0;
        long result = syscall(SYS_delete_module, name, O_NONBLOCK);
        int error = errno;
        printf("B866F_ORIGINAL_UNLOAD: %s result=%ld errno=%d\n", name, result, error);
        require(result == 0, "original-module-unloaded");
        require(!original_live(name), "original-module-absent");
    }
    puts("B866F_QEMU_ORIGINAL_LOAD_PASSED count=8");
}
#endif

int main(void) {
    int console = open("/dev/console", O_RDWR);
    if (console < 0) return 1;
    for (int i = 0; i < 3; i++) dup2(console, i);
    setvbuf(stdout, NULL, _IONBF, 0);
    puts("B866F_QEMU_INIT_STARTED");
    struct utsname name;
    require(uname(&name) == 0 && !strncmp(name.release, "5.15.196", 8), "kernel-release");
    printf("Kernel release: %s\n", name.release);
    unsigned char *memory = mmap(NULL, 1024 * 1024, PROT_READ | PROT_WRITE,
                                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    require(memory != MAP_FAILED, "anonymous-memory-map");
    memset(memory, 0xa5, 1024 * 1024);
    require(memory[0] == 0xa5 && memory[1024 * 1024 - 1] == 0xa5, "memory-access");
    munmap(memory, 1024 * 1024);
    int descriptors[2];
    require(pipe(descriptors) == 0, "pipe-create");
    pid_t child = fork();
    require(child >= 0, "fork");
    if (child == 0) {
        close(descriptors[0]);
        _exit(write(descriptors[1], "OK", 2) == 2 ? 0 : 1);
    }
    close(descriptors[1]);
    char response[2];
    int status;
    require(read(descriptors[0], response, 2) == 2 && !memcmp(response, "OK", 2), "child-pipe-read");
    close(descriptors[0]);
    require(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0,
            "child-exit");
    require(mount("tmpfs", "/tmp", "tmpfs", 0, "size=1m") == 0, "tmpfs-mount");
    int file = open("/tmp/probe", O_CREAT | O_RDWR, 0600);
    require(file >= 0, "file-create");
    require(write(file, "OK", 2) == 2 && lseek(file, 0, SEEK_SET) == 0 &&
            read(file, response, 2) == 2 && !memcmp(response, "OK", 2), "file-roundtrip");
    close(file);
    require(mount("proc", "/proc", "proc", 0, NULL) == 0, "proc-mount");
    file = open("/proc/version", O_RDONLY);
    require(file >= 0 && read(file, response, 2) == 2, "proc-read");
    close(file);
#ifdef B866F_TRUST_PROBE
    check_original_certificate();
#endif
#ifdef B866F_LOADER_PROBE
    check_loader_policy();
#endif
#ifdef B866F_PKCS7_PROBE
    check_pkcs7();
#endif
#ifdef B866F_ORIGINAL_LOAD_PROBE
    check_original_load();
#endif
    puts("B866F_QEMU_CORE_TESTS_PASSED");
#ifdef B866F_ORIGINAL_LOAD_PROBE
    puts("Eight original modules load-tested only; STB hardware, Android, DRM and patch coverage UNTESTED.");
#else
    puts("Virtual hardware only; STB boot, drivers, DRM and patch coverage UNTESTED.");
#endif
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
