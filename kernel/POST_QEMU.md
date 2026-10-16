# Pemeriksaan loader sesudah QEMU

[QEMU 5.15.196 berhasil](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38765162974): seluruh pemeriksaan initramfs Linux inti selesai dan shutdown bersih. Varian emulator mengecualikan watermark serta memakai fiq_check_en=0; ini bukan image kandidat STB.

Build pasangan driver sebelumnya menghasilkan 38 modul. Boundary profil 131 modul yang tercatat aktif memakai 35 pengganti dan tidak menemukan masalah CRC impor/provider duplikat. Itu belum memeriksa loader secara lengkap.

Metadata loader kini diambil dari 147 file modul perangkat dan 22 modul ramdisk platform, dengan sembilan file tumpang tindih yang hash-nya sama: total 160 file. Seluruh CRC impor sama dengan audit sebelumnya. Empat file disandingkan dengan parser Go/stdlib dan Python yang independen; modinfo, namespace ekspor dan marker signature cocok. Ada 47 file dengan marker signature, yang bukan bukti signature valid atau dipercaya kernel.

`module-loader-metadata.json` memuat hanya nama, depends, license, import_ns, vermagic dan deklarasi namespace/signature. Tidak ada binary modul, private key, identitas unik perangkat atau paket flashing.

Build diagnostik berikutnya mengekspor metadata sama untuk modul baru dan memeriksa deklarasi dependensi serta namespace pada profil yang dipertahankan. Report lama belum menyimpan metadata ini untuk 35 pengganti, sehingga checker menandainya belum diketahui. Checker baru membedakan namespace hilang, provider tanpa metadata, metadata modul hilang, serta dependency di luar profil. Kebijakan GPL/protected-symbol dan kepercayaan sertifikat tetap belum diverifikasi.

Kondisi penempatan: /vendor/lib/modules menunjuk /vendor_dlkm/lib/modules, dan vendor_dlkm terpasang read-only. Driver wireless pengganti berada pada daftar startup vendor. Daftar platform/recovery ramdisk berisi 13/22 modul yang tidak termasuk 35 pengganti. Seluruh nama startup termasuk dataset, tetapi urutan dan waktu load belum diuji pada kernel baru.

Recovery berbagi vendor_boot dengan ramdisk platform dan DTB. Slot B bukan fallback yang terbukti. Belum ada restore mandiri tanpa Android, dan tidak ada alasan memasang kernel hanya berdasarkan QEMU/CRC. Tidak ada flashing, module loading/unloading, reboot, atau perubahan keamanan pada pemeriksaan loader.

## Hasil build dan koreksi parser namespace

[Build diagnostik selesai](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38771672793). Tidak ada metadata modul hilang, dependency di luar profil, atau import namespace hilang yang terdeteksi. Report awal masih menandai 17 simbol (24 pemakaian impor) pada dua konsumen sebagai namespace belum diketahui.

Kedua konsumen, sprdbt_tty_sdio.ko dan sprdwl_ng.ko, memakai provider uwe5621_bsp_sdio.ko. Pemeriksaan binary yang hash-nya sama dengan audit menunjukkan LTO menghilangkan label __kstrtabns_*, sementara relocation AArch64 PREL32 tetap merujuk string namespace kosong. Parser diperbaiki untuk membaca field nama/namespace dari tabel __ksymtab dan __ksymtab_gpl, termasuk relocation ke section symbol dengan addend.

Parser terpisah berbasis pyelftools mengonfirmasi seluruh 66 ekspor provider memiliki namespace kosong. Relocation di luar tabel sengaja diuji dan ditolak. Pemeriksaan ulang lokal menggunakan artifact build yang sama dan metadata provider yang sudah dikoreksi menyelesaikan seluruh unknown namespace pada profil 131 modul/35 pengganti. Tidak perlu mengulang kompilasi untuk koreksi metadata provider ini. Report CI asli tetap menyimpan hasil sebelum koreksi; hasil ulang diberi label terpisah.

Kecocokan CRC, dependency dan deklarasi namespace sekarang lolos pada profil yang ditangkap. Kepercayaan signature, GPL/protected-export policy, waktu/urutan load, boot nyata, ABI userspace dan DRM tetap belum diuji. Tidak ada perubahan firmware atau klaim siap dipasang.

## Signature dan protected-symbol: pemeriksaan lanjutan

Pemeriksaan source kernel yang dipin pada f231c7811a91c548f86a43e17cf43611f8747c86 menunjukkan MODULE_SIG_PROTECT membutuhkan signature yang dipercaya untuk modul yang mengekspor simbol protected. Marker signature saja tidak cukup. Enam provider yang dipertahankan terkena aturan ini: cdc_ether, cdc_ncm, libarc4, mii, r8152 dan usbnet.

Satu sertifikat publik ditemukan pada kernel backup asli. SHA-256 DER: 01c0d6ffe7c65ce8a9b42eed55a3bd0f4d8e5fa2b63e1f9aea13e02317e667f8. Dari 47 file dengan marker signature, 46 berhasil diverifikasi menggunakan sertifikat tersebut, termasuk keenam provider protected. amlogic-input.ko memiliki signer identifier berbeda; sertifikat penandatangannya belum ditemukan. Ini berarti signature-nya belum terverifikasi, bukan bukti file rusak. Semua hash file sesuai audit asli; tiga file awal diambil dari backup ramdisk yang sudah ada.

`tools/kernel_module_signature_audit.py` memeriksa signature PKCS7 detached menggunakan OpenSSL dan sertifikat publik milik operator. Flag -noverify melewati validasi rantai sertifikat, tetapi tetap memverifikasi signature terhadap isi modul. Tool tidak menghubungi perangkat, memasang key, menandatangani file atau memuat modul. Uji negatif mengubah satu byte isi modul dan verifikasi menolaknya; header rusak juga ditolak. Tidak ada binary modul, sertifikat atau private key yang diterbitkan.

`module-signature-result.json` menyimpan hasil verifikasi lokal. `conditional-policy-result.json` memodelkan profil 131 modul/35 pengganti dengan asumsi sertifikat asli diterima kernel kandidat. Dengan asumsi itu, tidak ditemukan protected export dari modul yang dianggap tidak dipercaya, maupun impor di luar KMI dari provider yang dianggap dipercaya. Pemeriksaan license terhadap EXPORT_SYMBOL_GPL pada symvers kernel/modul hasil build juga tidak menemukan konflik. Jenis GPL ekspor seluruh modul lama dan header GKI hasil generate belum diaudit lengkap.

Jalur eksperimen berikutnya adalah mempertahankan sertifikat publik asli pada trust store kandidat, misalnya melalui CONFIG_SYSTEM_TRUSTED_KEYS, lalu memeriksa hasil build dan penerimaan key. Itu belum diimplementasikan atau dibuktikan oleh hasil lokal ini; sertifikat tidak memberi kemampuan menandatangani driver baru dan tidak menggantikan private key. Kebijakan enforcement tetap utuh.

Belum ada candidate trust test, load driver, boot STB, pengujian Netflix/DRM atau paket restore mandiri yang terbukti. Pemeriksaan ini tidak menerapkan patch keamanan Android Mei 2026. Kernel dan driver pada STB tidak berubah.

## Eksperimen keyring QEMU disiapkan

Opsi trust_probe pada workflow QEMU kini tersedia untuk menguji sertifikat publik asli pada varian emulator. Sertifikat publik saja diterbitkan di kernel/trust, bersama fingerprint yang dipin; tidak ada private key atau binary driver. Eksperimen memeriksa opsi enforcement tidak berubah, keberadaan DER pada Image hasil build, dan KEYCTL_SEARCH pada .builtin_trusted_keys dari guest. Workflow wajib melihat marker trust, seluruh core checks dan shutdown bersih. Core checks saja tidak cukup ketika trust_probe diminta.

Uji lokal menolak sertifikat berbeda, hilangnya DER dari Image, pelemahan opsi enforcement, dan hasil guest tanpa marker trust. Hasil build/runtime eksperimen belum diketahui pada saat perubahan ini dibuat. Dukungan sertifikat hanya ditambahkan ke eksperimen QEMU; konfigurasi kandidat STB tetap belum berubah. Signature driver amlogic-input masih memiliki signer lain yang belum terverifikasi, dan jalur restore mandiri tetap belum terbukti.

### Koreksi observasi keyring

[Run trust pertama](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38782104163) berhasil membangun Image dengan satu salinan DER sertifikat asli dan boot ke init. Serial log mencatat Loaded X.509 cert dengan SKID asli, dan seluruh pemeriksaan inti sampai proc-read lolos. Run tetap gagal karena syscall KEYCTL_SEARCH dari userspace tidak menemukan key; marker trust dan marker selesai tidak terbit. Exit QEMU 0 setelah jalur gagal tidak dihitung sukses.

Source certs/common.c pada commit kernel yang dipin memberi sertifikat built-in permission root VIEW/READ, tetapi tidak SEARCH. Hal ini konsisten dengan kegagalan SEARCH meskipun kernel telah mencatat key berhasil dimuat; errno belum direkam pada run pertama. Pengamatan diperbaiki agar membaca ID anggota ring sebenarnya dengan KEYCTL_READ lalu mencocokkan identifier sertifikat asymmetric melalui KEYCTL_DESCRIBE. SEARCH tetap direkam dengan errno sebagai diagnostik, bukan syarat sukses. Tidak ada permission atau enforcement yang diubah. Hasil verifikasi keanggotaan runtime masih menunggu run ulang.

### Hasil akhir eksperimen trust QEMU: berhasil

[Run pengganti berhasil](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38787178937) dengan commit ff1226bd77e2c4fe61374f53668f70ca794e84b0. Artifact ZIP diverifikasi terhadap SHA-256 d89dcf70ed47a6275de8529050c9cb03f2f8a4ff96ee2a3bf08141318b07d918. Hasil terstruktur disimpan di kernel/trust/qemu-result.json.

Image berisi satu salinan DER sertifikat asli yang fingerprint-nya dipin. Kernel guest 5.15.196-gff1226bd77e2 mencatat sertifikat berhasil dimuat; pemeriksaan READ/DESCRIBE memastikan key asymmetric dengan SKID asli benar-benar anggota .builtin_trusted_keys. SEARCH mengembalikan errno 13 (EACCES), sesuai keterbatasan permission userspace, dan tidak dipakai sebagai bukti trust gagal. Tidak ada permission atau opsi enforcement yang diubah.

Marker B866F_QEMU_ORIGINAL_CERT_TRUST_PASSED dan B866F_QEMU_CORE_TESTS_PASSED muncul; guest power down bersih, exit QEMU 0, tanpa timeout atau kernel panic. Warning hardware vendor tetap ada pada emulator dan bukan validasi driver Amlogic. Bukti ini menunjukkan sertifikat publik asli dapat dimuat pada keyring built-in varian eksperimen. Ini belum menguji acceptance signature modul asli oleh loader, protected-symbol saat load, driver B866F, Android, HDMI, Netflix/DRM, AVB, atau kelengkapan patch Mei 2026.

Investigasi terjadwal berhenti setelah pencatatan hasil ini. Tidak ada akses STB, module load/unload, reboot, flashing atau instalasi kernel. Tahap hardware tetap menunggu validasi terpisah dan jalur restore mandiri yang terbukti.

## Eksperimen loader sintetis berikutnya

Opsi loader_probe pada workflow QEMU menambahkan fixture GPL minimal yang mengekspor nama protected arc4_crypt sebagai stub tanpa konsumen. Ini bukan driver ARC4 asli dan tidak untuk perangkat fisik. Varian trusted memakai key build runner sementara, bukan private key vendor. Percobaan mengharapkan load/unload trusted berhasil, unsigned dan signer asing ditolak karena protected export, serta signature yang diubah ditolak sebelum init. Header protected hasil generate dan tabel simbol kernel diperiksa terlebih dahulu; CRC, vermagic dan opsi enforcement tidak diabaikan.

Artifact tetap hanya teks; seluruh key sementara dan binary fixture tinggal pada runner. Hasil runtime masih menunggu. Sertifikat asli tetap diperiksa di keyring emulator, tetapi percobaan ini belum menguji signature/driver asli maupun membuktikan kernel siap dipasang.

[Run loader pertama](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38817456141) berhasil membangun kernel dan menjalankan compile/LTO/modpost fixture, tetapi link modul berhenti karena scripts/module.lds belum dibuat. QEMU belum dijalankan pada run ini, sehingga tidak ada hasil runtime baru. Target Kbuild modules_prepare kini dipanggil sebelum build eksternal, dan keberadaan linker script diperiksa. Tidak ada CRC, signature atau enforcement bypass yang ditambahkan; hasil menunggu run ulang.

### Hasil loader sintetis: berhasil

[Run yang diperbaiki berhasil](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38830704133), commit 62f03cd2e9e0f5d96b9a95123853ceb259fd3944. SHA-256 artifact ec3214e959f769abc3804334593ed4ade544e81d0c390dd1c36a165ae318994c diverifikasi sebelum membaca bukti. Hasil dicatat di kernel/trust/loader-result.json.

Fixture trusted berhasil init dan unload tepat sekali. Fixture unsigned dan signer asing masing-masing ditolak dengan errno 13 disertai pesan exports protected symbol arc4_crypt. Signature yang diubah ditolak dengan errno 129. Marker loader policy, original certificate keyring dan core checks lengkap, diikuti power down bersih, exit 0 dan tanpa timeout atau kernel panic. Opsi enforcement tetap sama dengan referensi. Tidak ada binary atau private key yang diterbitkan.

Ini membuktikan mekanisme loader pada varian emulator untuk fixture sintetis dengan key build runner sementara. Signature vendor/driver asli, kernel pada B866F, Android, Netflix/DRM dan cakupan patch Mei 2026 tetap belum diuji. Tidak ada akses atau perubahan STB.

## Uji crypto signature asli dengan digest saja

Opsi `signature_probe` menyiapkan eksperimen terpisah: verifikasi RSA4096/PKCS1v1.5/SHA256 atas 46 digest modul asli menggunakan sertifikat asli di built-in keyring. Vector publik berisi nama modul, hash file, digest isi yang ditandatangani, dan signature RSA publik. Tidak ada isi binary driver atau private key. `amlogic-input.ko` dikecualikan karena sertifikat signer berbeda belum tersedia.

Generator lokal `tools/kernel_signature_vectors.py` memeriksa hash file terhadap audit privat, membaca format DER CMS detached yang ketat (tanpa signed attributes atau konten tertanam), dan memverifikasi setiap signature secara independen melalui cryptography dengan Prehashed SHA256. Generator membutuhkan paket Python cryptography; build QEMU memakai vector JSON yang sudah diterbitkan dan tidak memerlukan paket tersebut atau akses file modul asli.

Instrumentasi `certs/system_keyring.c` hanya berlaku saat opsi eksperimen diminta dan menolak source dengan hash berbeda. Setelah sertifikat dimuat, instrumentasi memanggil API kernel `verify_signature` untuk setiap vector. Setiap signature wajib diterima dengan digest asli dan ditolak dengan EKEYREJECTED setelah satu byte digest diubah. Classifier mewajibkan seluruh 46 hasil positif, 46 hasil negatif, marker akhir, core/keyring checks, tanpa panic/failure, dan shutdown bersih. Permission keyring dan enforcement signature tidak diubah. Hasil runtime belum ditetapkan pada saat eksperimen disiapkan.

Ini menguji API crypto prehashed, **bukan parser PKCS7 di kernel, load driver asli, urutan boot atau kompatibilitas hardware/Android/Netflix**. Instrumentasi diagnostik bukan perubahan kernel yang siap dipasang. Patch keamanan Android Mei 2026 tetap membutuhkan audit dan pembaruan komponen terpisah; angka versi kernel atau keberhasilan QEMU saja tidak cukup.

Untuk menjalankan secara lokal pada Linux dengan dependency build yang sama seperti workflow:

```sh
KERNEL_SOURCE=coreelec-5.15.196 SIGNATURE_PROBE=1 KERNEL_BUILD_JOBS=4 python3 tools/kernel_qemu.py
```

Build membutuhkan direktori `build/kernel-baseline` yang belum ada; source, object, Image dan key build sementara tetap lokal. `KERNEL_BUILD_JOBS` dibatasi 1–8 (default 2). Simpan report sebelum eksperimen berikutnya dan jangan menghapus tree build aktif. Tidak ada akses STB atau operasi flash pada tool ini.

### Hasil lokal crypto signature asli: berhasil

Build lokal WSL2 Ubuntu 24.04 dengan empat job, source proyek commit
7af4d5b39fb245b4729ca3ccdf62b087c150b96c, selesai pada 16 Oktober 2026 pukul
10:50:44 +08:00. Durasi total dari persiapan sampai selesai adalah 31 menit
7 detik. Ini run lokal, bukan hasil baru pada halaman GitHub Actions lama.
Tidak ada perbandingan durasi terkontrol dengan runner GitHub.

Serial log yang diperiksa ulang mencatat 46 signature asli diterima oleh API
crypto kernel terhadap digest asli dan 46 digest yang diubah ditolak dengan
EKEYREJECTED. Seluruh nama vector, jumlah hasil, marker akhir, keyring/core
checks, dan shutdown bersih diverifikasi; exit QEMU 0, tanpa timeout atau
kernel panic. DER sertifikat asli ditemukan tepat sekali pada Image. Opsi
enforcement tetap sama. Hasil terstruktur dan hash bukti tersimpan di
`kernel/trust/original-signature-result.json`; log dan binary tetap lokal.

Hasil ini memperluas bukti dari keberadaan sertifikat ke verifikasi signature
RSA prehashed dengan key asli di kernel emulator. Parser PKCS7 kernel dan load
driver asli tetap belum diuji. amlogic-input memakai signer lain yang belum
tersedia. Warning hardware vendor masih ada di emulator. Kompatibilitas B866F,
Android, Netflix/DRM, jalur restore mandiri, dan cakupan patch Mei 2026 belum
dibuktikan. Tidak ada pemasangan kernel atau perubahan STB pada run ini.

## Verifikasi PKCS7 lengkap secara lokal: berhasil

Eksperimen berikutnya memakai ulang Image lokal yang sama, tanpa rebuild kernel.
Helper GPL kecil dibangun dengan Kbuild normal, CRC/namespace asli dan signature
key build lokal, lalu dimuat hanya di QEMU. Input 47 file modul asli diperiksa
hash-nya dan dimasukkan ke initramfs privat sebagai pasangan body/signature.
Helper membaca byte sebagai data; tidak memuat atau menjalankan driver asli.

API `verify_pkcs7_signature` dipanggil dengan VERIFY_USE_SECONDARY_KEYRING dan
VERIFYING_MODULE_SIGNATURE, sama dengan jalur pada kernel/module_signing.c yang
dipin. Hasilnya: 46 signature terhadap isi lengkap diterima; 46 perubahan satu
byte isi ditolak dengan EKEYREJECTED (-129); 46 CMS yang dipotong satu byte
ditolak dengan EBADMSG (-74). amlogic-input.ko ditolak dengan ENOKEY (-126),
sesuai signer lain yang sertifikatnya belum tersedia. Itu bukan bukti signature
file tersebut rusak.

Keyring/core checks dan eksperimen prehashed sebelumnya kembali lolos. Helper
berhasil load/unload, QEMU power down bersih, exit 0, tanpa timeout/kernel panic.
Image tetap memiliki hash yang sama sebelum dan sesudah run. Uji ulang sukses
memerlukan sekitar 19 detik untuk build helper dan boot/verifikasi emulator;
angka ini tidak mencakup penyiapan source atau percobaan compile pertama yang
gagal karena include linux/mm.h belum ditambahkan. Log percobaan pertama tetap
disimpan secara lokal. Hasil terstruktur: `kernel/trust/pkcs7-result.json`.

`tools/kernel_pkcs7_probe.py` menolak CI dan hash input/build yang berbeda.
Tidak ada input asli, initramfs privat, helper binary, Image, atau private key
yang diterbitkan. Sebelas guard tests lolos pada Windows dan Ubuntu, termasuk
penolakan input berbeda serta bukti runtime yang tidak lengkap/negatif gagal.

Ini membuktikan parsing CMS dan verifikasi isi/trust untuk 46 file asli pada
emulator. Header luar signature modul masih diperiksa oleh tool host, bukan
mod_check_sig di kernel pada percobaan ini. Relocation, init/dependency driver
asli, hardware B866F, Android/Netflix dan patch Mei 2026 tetap belum terbukti.
Warning hardware vendor masih ada. Tidak ada akses atau perubahan STB.

## Delapan modul asli berhasil dimuat di QEMU

`tools/kernel_original_load_probe.py` memakai ulang Image lokal yang sama dan
memasukkan delapan file asli yang hash-nya cocok dengan audit ke initramfs
privat. Urutan load: libarc4, mii, usbnet, cdc_ether, cdc_ncm, r8152, zsmalloc,
zram. Kali ini kode init modul asli benar-benar dijalankan oleh kernel emulator,
bukan hanya pembacaan byte atau fixture sintetis.

Seluruh `finit_module` berhasil dengan flags 0. Setiap modul ditemukan pada
/proc/modules dengan state Live dan ukuran positif. Semua modul kemudian
di-unload dalam urutan terbalik dengan O_NONBLOCK, tanpa force, dan dipastikan
tidak lagi berstatus Live. Tidak ada pengubahan signature, vermagic, CRC,
namespace, atau binary asli. Enam provider protected-export yang diaudit
(libarc4, mii, usbnet, cdc_ether, cdc_ncm, r8152) termasuk di dalam delapan modul.

Perbedaan nomor versi awal vermagic tidak dipaksa lewat: source same_magic pada
kernel yang dipin memang membandingkan bagian sesudah nomor versi bila modul
memiliki CRC. Pemeriksaan CRC termasuk module_layout tetap aktif. Keberhasilan
ini memakai perilaku normal kernel MODVERSIONS, bukan IGNORE_VERMAGIC atau
IGNORE_MODVERSIONS. Tidak ada pesan Unknown symbol, CRC disagreement, invalid
module atau verification failed pada serial log percobaan ini.

Keyring/core checks dan prehashed crypto checks kembali lolos; shutdown bersih,
exit 0, tanpa timeout atau kernel panic, dan hash Image tetap sama. Run akhir
memerlukan sekitar 6 detik dengan build kernel yang sudah tersedia. Hasil dan
hash log: `kernel/trust/original-load-result.json`. Dua belas guard tests lolos
di Windows dan Ubuntu. Binary asli, initramfs dan Image tetap lokal; runner
menolak CI. Workflow hanya memeriksa source dan guard tests fitur ini.

Ini memvalidasi jalur header/signature, link simbol, dependency dan init/unload
untuk delapan modul tersebut pada QEMU. Perangkat USB tidak dipasang ke guest,
network guest dinonaktifkan, dan operasi perangkat keras USB/network maupun
I/O zram belum diuji. Driver Amlogic/Wi-Fi lain, boot B866F, Android, Netflix/DRM,
jalur restore mandiri, dan cakupan patch Mei 2026 belum terbukti. Warning vendor
untuk hardware yang tidak ada di QEMU tetap muncul. Tidak ada akses STB.

## Cakupan diperluas: 37 modul dan I/O zram

Profil `--hid --zram-io` pada runner lokal memperluas delapan modul awal dengan
29 driver/helper HID. Semua 37 file asli lolos hash check, finit_module flags 0,
state Live, dan unload normal dalam urutan dependency terbalik. Nama path di
initramfs dinormalisasi ke underscore agar cocok dengan nama internal modul;
isi file, modinfo, CRC dan signature tidak diubah. Tidak ada perangkat HID/USB
fisik atau network guest yang dipasang.

Setelah load, guest membuat zram 1 MiB, menulis 64 KiB pola nonuniform, fsync,
dan membuang cache block device dengan BLKFLSBUF sebelum readback. Data kembali
identik. Statistik driver menunjukkan 65.536 byte data asli, 4.832 byte
terkompresi, dan 16.384 byte alokasi. Reset mengembalikan seluruh statistik
memori ke nol, lalu device node guest dihapus dan seluruh modul di-unload.
Ini menguji kompresi/dekompresi, alokasi dan pembebasan pada zram/zsmalloc asli,
melampaui init/unload saja. Bukan uji swap/memory-pressure Android.

Core/keyring/prehashed checks, shutdown bersih dan hash Image yang sama kembali
terverifikasi. Run gabungan sekitar 13,41 detik dengan Image yang sudah tersedia.
Tiga belas guard tests lolos di Windows dan Ubuntu. Hasil terstruktur:
`kernel/trust/hid-zram-result.json`. Source, hash dan hasil saja diterbitkan;
seluruh input original dan initramfs tetap privat. Fungsi perangkat HID/USB
nyata, driver vendor tersisa, boot Android/Netflix dan patch coverage belum
terbukti. Audit userspace terpisah ada di `security/README.md`.
