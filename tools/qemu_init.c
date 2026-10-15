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
#ifdef B866F_TRUST_PROBE
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
    /* Discover the root-owned built-in ring, then search within that ring.
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
    long certificate = syscall(SYS_keyctl, KEYCTL_SEARCH, (int)ring, "asymmetric",
                               "id:821976dbe4b8a702b6f3b8804f03a4d517df1f3b", 0);
    require(certificate > 0, "original-certificate-in-builtin-trusted-keyring");
    puts("B866F_QEMU_ORIGINAL_CERT_TRUST_PASSED");
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
    puts("B866F_QEMU_CORE_TESTS_PASSED");
    puts("Virtual hardware only; STB boot, drivers, DRM and patch coverage UNTESTED.");
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
