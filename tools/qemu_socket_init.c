/* Ordinary socket API checks inside offline QEMU only. Not a CVE exploit. */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/socket.h>
#include <linux/vm_sockets.h>
#include <unistd.h>

static void require(int ok, const char *name)
{
    printf("B866F_SOCKET_%s:%s errno=%d\n", ok ? "OK" : "FAIL", name, ok ? 0 : errno);
    fflush(stdout);
    if (!ok) {
        reboot(RB_POWER_OFF);
        for (;;) pause();
    }
}

static void check_unix_stream(void)
{
    int pair[2];
    char data[8] = {0};
    require(socketpair(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0, pair) == 0, "unix-stream-create");
    require(send(pair[0], "hello", 5, 0) == 5 && recv(pair[1], data, 5, MSG_WAITALL) == 5 &&
            memcmp(data, "hello", 5) == 0, "unix-stream-roundtrip");
    require(shutdown(pair[0], SHUT_WR) == 0 && recv(pair[1], data, 1, 0) == 0, "unix-stream-eof");
    close(pair[0]);
    close(pair[1]);
}

static void check_descriptor_transfer(void)
{
    int pair[2];
    int original = open("/dev/null", O_RDONLY | O_CLOEXEC);
    require(original >= 0 && socketpair(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0, pair) == 0,
            "unix-rights-create");
    union { struct cmsghdr align; char bytes[CMSG_SPACE(sizeof(int))]; } control;
    memset(&control, 0, sizeof(control));
    char byte = 'r';
    struct iovec iov = {.iov_base = &byte, .iov_len = 1};
    struct msghdr msg = {.msg_iov = &iov, .msg_iovlen = 1,
                        .msg_control = control.bytes, .msg_controllen = sizeof(control.bytes)};
    struct cmsghdr *header = CMSG_FIRSTHDR(&msg);
    header->cmsg_level = SOL_SOCKET;
    header->cmsg_type = SCM_RIGHTS;
    header->cmsg_len = CMSG_LEN(sizeof(int));
    memcpy(CMSG_DATA(header), &original, sizeof(original));
    require(sendmsg(pair[0], &msg, 0) == 1, "unix-rights-send");
    close(original);
    memset(&control, 0, sizeof(control));
    byte = 0;
    require(recvmsg(pair[1], &msg, MSG_CMSG_CLOEXEC) == 1 && byte == 'r' &&
            !(msg.msg_flags & (MSG_CTRUNC | MSG_TRUNC)), "unix-rights-receive");
    header = CMSG_FIRSTHDR(&msg);
    require(header && header->cmsg_level == SOL_SOCKET && header->cmsg_type == SCM_RIGHTS &&
            header->cmsg_len == CMSG_LEN(sizeof(int)), "unix-rights-header");
    int received = -1;
    memcpy(&received, CMSG_DATA(header), sizeof(received));
    require(received >= 0 && (fcntl(received, F_GETFD) & FD_CLOEXEC) && read(received, &byte, 1) == 0,
            "unix-rights-descriptor-usable");
    close(received);
    close(pair[0]);
    close(pair[1]);
}

static void check_urgent_data(void)
{
    int pair[2];
    char byte = 0;
    require(socketpair(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK, 0, pair) == 0, "unix-oob-create");
    require(send(pair[0], "u", 1, MSG_OOB) == 1 &&
            recv(pair[1], &byte, 1, MSG_OOB | MSG_PEEK) == 1 && byte == 'u' &&
            recv(pair[1], &byte, 1, MSG_OOB) == 1 && byte == 'u', "unix-oob-peek-consume");
    require(send(pair[0], "n", 1, 0) == 1, "unix-oob-following-normal-send");
    /* A consumed urgent byte leaves an OOB boundary marker on this API.
     * The first normal nonblocking receive may only consume that marker. */
    ssize_t count = recv(pair[1], &byte, 1, 0);
    if (count < 0 && (errno == EAGAIN || errno == EWOULDBLOCK))
        count = recv(pair[1], &byte, 1, 0);
    require(count == 1 && byte == 'n',
            "unix-oob-following-normal-data");
    close(pair[0]);
    close(pair[1]);
}

static void check_epoll(void)
{
    int pair[2];
    int ep = epoll_create1(EPOLL_CLOEXEC);
    require(ep >= 0 && socketpair(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK, 0, pair) == 0,
            "epoll-create");
    struct epoll_event event = {.events = EPOLLIN | EPOLLRDHUP, .data.u64 = 0x866f};
    require(epoll_ctl(ep, EPOLL_CTL_ADD, pair[1], &event) == 0 && send(pair[0], "e", 1, 0) == 1,
            "epoll-register-send");
    require(epoll_wait(ep, &event, 1, 1000) == 1 && (event.events & EPOLLIN) && event.data.u64 == 0x866f,
            "epoll-readable-event");
    char byte;
    require(recv(pair[1], &byte, 1, 0) == 1 && byte == 'e' && shutdown(pair[0], SHUT_WR) == 0 &&
            epoll_wait(ep, &event, 1, 1000) == 1 && (event.events & EPOLLRDHUP), "epoll-peer-shutdown");
    require(epoll_ctl(ep, EPOLL_CTL_DEL, pair[1], NULL) == 0, "epoll-unregister");
    close(pair[0]);
    close(pair[1]);
    close(ep);
}

static void check_vsock(void)
{
    int fd = socket(AF_VSOCK, SOCK_STREAM | SOCK_CLOEXEC, 0);
    require(fd >= 0, "vsock-create");
    struct sockaddr_vm address = {.svm_family = AF_VSOCK, .svm_cid = VMADDR_CID_ANY,
                                 .svm_port = VMADDR_PORT_ANY};
    require(bind(fd, (struct sockaddr *)&address, sizeof(address)) == 0, "vsock-autobind");
    socklen_t size = sizeof(address);
    require(getsockname(fd, (struct sockaddr *)&address, &size) == 0 && size == sizeof(address) &&
            address.svm_port != VMADDR_PORT_ANY && address.svm_port > 1023,
            "vsock-autobind-concrete-port");
    close(fd);
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    require(getpid() == 1, "guest-pid1");
    check_unix_stream();
    check_descriptor_transfer();
    check_urgent_data();
    check_epoll();
    check_vsock();
    puts("B866F_QEMU_SOCKET_TESTS_PASSED");
    puts("Socket API checks only; CVE coverage, B866F hardware and Android remain unverified.");
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
