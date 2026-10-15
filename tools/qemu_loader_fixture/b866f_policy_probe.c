// SPDX-License-Identifier: GPL-2.0-only
/* Emulator-only loader fixture. Never install on a real device.
 * The protected export is deliberately a stub: no ARC4 implementation or
 * real driver functionality is exercised, and there are no consumers. */
#include <linux/module.h>
#include <linux/init.h>

int arc4_crypt(void);
int arc4_crypt(void) { return 0; }
EXPORT_SYMBOL(arc4_crypt);

static int __init probe_start(void)
{
    pr_info("B866F_LOADER_FIXTURE_INIT\n");
    return 0;
}

static void __exit probe_stop(void)
{
    pr_info("B866F_LOADER_FIXTURE_EXIT\n");
}

module_init(probe_start);
module_exit(probe_stop);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("QEMU-only signature and protected-export policy fixture");
