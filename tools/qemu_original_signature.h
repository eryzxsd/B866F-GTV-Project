/* SPDX-License-Identifier: GPL-2.0-only */
/* Emulator-only instrumentation, included after built-in keyring declaration.
 * Digests/public RSA signatures only; no original module code is present.
 */
#include <crypto/public_key.h>
#include "b866f_signature_vectors.h"

static int __init b866f_original_signature_probe(void)
{
	key_ref_t ref;
	unsigned int i;
	int ret = 0;

	ref = keyring_search(make_key_ref(builtin_trusted_keys, 1),
			     &key_type_asymmetric,
			     "ex:821976dbe4b8a702b6f3b8804f03a4d517df1f3b", true);
	if (IS_ERR(ref)) {
		pr_err("B866F_QEMU_FAIL: original signature key lookup %ld\n", PTR_ERR(ref));
		return PTR_ERR(ref);
	}
	for (i = 0; i < ARRAY_SIZE(b866f_signature_vectors); i++) {
		const struct b866f_signature_vector *v = &b866f_signature_vectors[i];
		u8 digest[32];
		struct public_key_signature sig = {
			.s = (u8 *)v->signature,
			.s_size = sizeof(v->signature),
			.digest = digest,
			.digest_size = sizeof(digest),
			.pkey_algo = "rsa", .hash_algo = "sha256", .encoding = "pkcs1",
		};

		memcpy(digest, v->digest, sizeof(digest));
		ret = verify_signature(key_ref_to_ptr(ref), &sig);
		pr_notice("B866F_ORIGINAL_SIG: %s valid=%d\n", v->name, ret);
		if (ret)
			goto fail;
		digest[0] ^= 1;
		ret = verify_signature(key_ref_to_ptr(ref), &sig);
		pr_notice("B866F_ORIGINAL_SIG: %s changed_digest=%d\n", v->name, ret);
		if (ret != -EKEYREJECTED) {
			ret = -EINVAL;
			goto fail;
		}
	}
	key_ref_put(ref);
	pr_notice("B866F_QEMU_ORIGINAL_SIGNATURE_CRYPTO_PASSED count=%zu\n",
		  ARRAY_SIZE(b866f_signature_vectors));
	return 0;
fail:
	key_ref_put(ref);
	pr_err("B866F_QEMU_FAIL: original signature vector %u ret=%d\n", i, ret);
	return ret;
}
