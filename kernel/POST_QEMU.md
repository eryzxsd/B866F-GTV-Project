# Pemeriksaan loader sesudah QEMU

[QEMU 5.15.196 berhasil](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38765162974): seluruh pemeriksaan initramfs Linux inti selesai dan shutdown bersih. Varian emulator mengecualikan watermark serta memakai fiq_check_en=0; ini bukan image kandidat STB.

Build pasangan driver sebelumnya menghasilkan 38 modul. Boundary profil 131 modul yang tercatat aktif memakai 35 pengganti dan tidak menemukan masalah CRC impor/provider duplikat. Itu belum memeriksa loader secara lengkap.

Metadata loader kini diambil dari 147 file modul perangkat dan 22 modul ramdisk platform, dengan sembilan file tumpang tindih yang hash-nya sama: total 160 file. Seluruh CRC impor sama dengan audit sebelumnya. Empat file disandingkan dengan parser Go/stdlib dan Python yang independen; modinfo, namespace ekspor dan marker signature cocok. Ada 47 file dengan marker signature, yang bukan bukti signature valid atau dipercaya kernel.

`module-loader-metadata.json` memuat hanya nama, depends, license, import_ns, vermagic dan deklarasi namespace/signature. Tidak ada binary modul, private key, identitas unik perangkat atau paket flashing.

Build diagnostik berikutnya mengekspor metadata sama untuk modul baru dan memeriksa deklarasi dependensi serta namespace pada profil yang dipertahankan. Report lama belum menyimpan metadata ini untuk 35 pengganti, sehingga checker menandainya belum diketahui. Checker baru membedakan namespace hilang, provider tanpa metadata, metadata modul hilang, serta dependency di luar profil. Kebijakan GPL/protected-symbol dan kepercayaan sertifikat tetap belum diverifikasi.

Kondisi penempatan: /vendor/lib/modules menunjuk /vendor_dlkm/lib/modules, dan vendor_dlkm terpasang read-only. Driver wireless pengganti berada pada daftar startup vendor. Daftar platform/recovery ramdisk berisi 13/22 modul yang tidak termasuk 35 pengganti. Seluruh nama startup termasuk dataset, tetapi urutan dan waktu load belum diuji pada kernel baru.

Recovery berbagi vendor_boot dengan ramdisk platform dan DTB. Slot B bukan fallback yang terbukti. Belum ada restore mandiri tanpa Android, dan tidak ada alasan memasang kernel hanya berdasarkan QEMU/CRC. Tidak ada flashing, module loading/unloading, reboot, atau perubahan keamanan pada pemeriksaan loader.
