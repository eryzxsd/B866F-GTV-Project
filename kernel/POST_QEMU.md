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
