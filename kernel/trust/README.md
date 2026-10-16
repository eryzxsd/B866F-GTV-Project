# Sertifikat publik driver asli

`original-module-signer.crt` hanya berisi sertifikat X.509 publik yang ditemukan
pada backup kernel asli. Tidak ada private key dan file ini tidak dapat digunakan
untuk membuat signature driver yang baru.

Fingerprint SHA-256 DER:
`01c0d6ffe7c65ce8a9b42eed55a3bd0f4d8e5fa2b63e1f9aea13e02317e667f8`.
Subject key identifier:
`821976dbe4b8a702b6f3b8804f03a4d517df1f3b`.

Opsi workflow QEMU `trust_probe` menambahkan sertifikat ini ke
CONFIG_SYSTEM_TRUSTED_KEYS pada varian emulator saja. Pemeriksaan menolak
perubahan opsi enforcement signature, memeriksa DER pada hasil Image, dan
mencocokkan identifier anggota .builtin_trusted_keys saat guest berjalan.
KEYCTL_READ mengambil ID anggota ring, kemudian KEYCTL_DESCRIBE memeriksa
identifier key asymmetric tersebut. KEYCTL_SEARCH hanya diagnostik: source
certs/common.c memberi root VIEW/READ tetapi tidak SEARCH pada sertifikat
built-in, sehingga kegagalan SEARCH bukan bukti sertifikat tidak dipercaya.
Tidak ada perubahan permission atau penambahan key saat runtime. Hasil tidak
cukup untuk membuktikan driver asli dapat dimuat.

Workflow tetap hanya mengunggah laporan teks. Tidak ada image boot, private key,
binary driver asli atau perubahan konfigurasi STB. Kernel kandidat STB belum
mendapat sertifikat ini dan seluruh hasil masih eksperimen, bukan update Android.

Hasil awal uji sertifikat QEMU berhasil: [run 38787178937](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38787178937).
Lihat qemu-result.json untuk fingerprint, hash artifact dan batas cakupan. Keanggotaan
sertifikat pada trusted keyring dan core checks terverifikasi, disertai shutdown
bersih. Run tersebut belum memuat driver asli. Eksperimen lokal berikutnya
memverifikasi PKCS7 lengkap, memuat/melepas 37 modul asli, dan menguji I/O zram;
lihat `pkcs7-result.json`, `hid-zram-result.json` dan dokumentasi kernel utama.
`socket-api-result.json` menambahkan 21 pemeriksaan API socket normal pada Image
emulator yang sama. Hardware STB, Android dan Netflix tetap belum diuji dengan
kernel kandidat. Review persyaratan patch ada pada [audit keamanan](../../security/README.md).
