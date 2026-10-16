// SPDX-License-Identifier: GPL-2.0-only
/* Local QEMU verifier only. Original modules are read as data, never loaded. */
#include <linux/module.h>
#include <linux/fs.h>
#include <linux/slab.h>
#include <linux/mm.h>
#include <linux/verification.h>
#include "probe_cases.h"

static void *read_case(const char *name, const char *suffix, size_t *size)
{
	char path[160];
	struct file *file;
	loff_t pos = 0, length;
	void *data;
	ssize_t count;

	if (snprintf(path, sizeof(path), "/audit/%s.%s", name, suffix) >= sizeof(path))
		return ERR_PTR(-ENAMETOOLONG);
	file = filp_open(path, O_RDONLY, 0);
	if (IS_ERR(file))
		return file;
	length = i_size_read(file_inode(file));
	if (length <= 0 || length > 8 * 1024 * 1024) {
		filp_close(file, NULL);
		return ERR_PTR(-EINVAL);
	}
	data = kvmalloc(length, GFP_KERNEL);
	if (!data) {
		filp_close(file, NULL);
		return ERR_PTR(-ENOMEM);
	}
	while (pos < length) {
		loff_t old_pos = pos;
		count = kernel_read(file, (u8 *)data + pos, length - pos, &pos);
		if (count <= 0 || pos != old_pos + count) {
			kvfree(data);
			filp_close(file, NULL);
			return ERR_PTR(-EIO);
		}
	}
	filp_close(file, NULL);
	*size = length;
	return data;
}

static int verify_case(void *body, size_t body_size, void *cms, size_t cms_size)
{
	/* Same trust selector and usage as pinned kernel/module_signing.c. */
	return verify_pkcs7_signature(body, body_size, cms, cms_size,
		VERIFY_USE_SECONDARY_KEYRING, VERIFYING_MODULE_SIGNATURE, NULL, NULL);
}

static int __init probe_start(void)
{
	unsigned int i;
	int ret = 0;

	for (i = 0; i < ARRAY_SIZE(probe_cases); i++) {
		const struct probe_case *c = &probe_cases[i];
		size_t body_size = 0, cms_size = 0;
		void *body = read_case(c->name, "body", &body_size);
		void *cms = read_case(c->name, "p7s", &cms_size);

		if (IS_ERR(body) || IS_ERR(cms)) {
			ret = IS_ERR(body) ? PTR_ERR(body) : PTR_ERR(cms);
			if (!IS_ERR(body)) kvfree(body);
			if (!IS_ERR(cms)) kvfree(cms);
			goto fail;
		}
		ret = verify_case(body, body_size, cms, cms_size);
		pr_notice("B866F_PKCS7: %s original=%d\n", c->name, ret);
		if (ret != c->expected)
			goto case_fail;
		if (c->expected == 0) {
			((u8 *)body)[0] ^= 1;
			ret = verify_case(body, body_size, cms, cms_size);
			((u8 *)body)[0] ^= 1;
			pr_notice("B866F_PKCS7: %s changed_body=%d\n", c->name, ret);
			if (ret != -EKEYREJECTED)
				goto case_fail;
			ret = verify_case(body, body_size, cms, cms_size - 1);
			pr_notice("B866F_PKCS7: %s truncated_cms=%d\n", c->name, ret);
			if (ret != -EBADMSG)
				goto case_fail;
		}
		kvfree(body);
		kvfree(cms);
		continue;
case_fail:
		kvfree(body);
		kvfree(cms);
		goto fail;
	}
	pr_notice("B866F_QEMU_PKCS7_PASSED trusted=46 unknown=1\n");
	return 0;
fail:
	pr_err("B866F_QEMU_FAIL: pkcs7 case=%u ret=%d\n", i, ret);
	return -EINVAL;
}

static void __exit probe_stop(void)
{
	pr_notice("B866F_PKCS7_FIXTURE_EXIT\n");
}
module_init(probe_start);
module_exit(probe_stop);
MODULE_LICENSE("GPL");
MODULE_IMPORT_NS(VFS_internal_I_am_really_a_filesystem_and_am_NOT_a_driver);
MODULE_DESCRIPTION("Local QEMU PKCS7 verifier; no original module execution");
