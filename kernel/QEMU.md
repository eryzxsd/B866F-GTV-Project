# Uji boot kernel pada QEMU

Workflow manual `Kernel QEMU boot test (not STB validation)` membangun varian
emulator dari source CoreELEC 5.15.196 dan common_drivers yang dipin pada
eksperimen ABI. Tiga patch source kernel yang sama diterapkan. Tidak ada
akses ke STB atau pemasangan software Linux pada laptop.

Konfigurasi dimulai dari konfigurasi referensi B866F, lalu mengaktifkan
`SERIAL_AMBA_PL011` dan `SERIAL_AMBA_PL011_CONSOLE` untuk konsol virtual.
Perbedaan hasil `olddefconfig` dicatat seluruhnya dalam `status.json`.
Tes header UAPI opsional dinonaktifkan seperti pada build diagnostik sebelumnya.
Pada percobaan pertama, `debug_lockup_init` memanggil SMC vendor
`0x820000f1` dan QEMU berhenti dengan undefined-instruction panic.
Percobaan kedua menonaktifkan `AMLOGIC_DEBUG`, tetapi gagal link karena
GPIO vendor membutuhkan ekspor `irq_latch_clr` dari komponen tersebut.

Tes berikutnya mempertahankan `AMLOGIC_DEBUG=y` dan menggunakan opsi boot
vendor yang sudah tersedia: `fiq_check_en=0`, khusus command line QEMU.
Opsi ini melewati inisialisasi FIQ yang memanggil secure monitor Amlogic.
Tidak ada patch source tambahan. Implementasi opt-out pada source yang dipin
akan diperiksa sebelum build. Jalur FIQ vendor tidak tercakup dalam tes ini.
Konfigurasi referensi B866F dan build pasangan driver tidak diubah.
Percobaan ketiga berhasil melewati inisialisasi debug tersebut, lalu panic di
`aml_watermark_driver_init`, pada SMC `0xb200e003`. Varian emulator berikutnya
menonaktifkan `AMLOGIC_WATERMARK`; fungsi watermark dan secure monitor vendor
tidak diuji. Opsi ini tetap dipertahankan pada konfigurasi referensi perangkat.
Ini **bukan konfigurasi yang identik dengan kandidat pasangan driver**.

Kernel menjalankan initramfs kecil pada mesin QEMU `virt`, CPU `cortex-a53`,
dua CPU dan RAM 2 GiB. Jaringan dinonaktifkan; tidak ada disk/firmware
perangkat yang dihubungkan. Program init memeriksa versi kernel, alokasi
memori, fork/pipe/wait, operasi berkas pada tmpfs dan pembacaan procfs.
Serial log harus memuat marker penyelesaian dan tidak memuat marker kegagalan
atau kernel panic. Keberhasilan shutdown dicatat terpisah dari pemeriksaan guest.

Hasil hanya membuktikan bagian Linux inti yang benar-benar dijalankan.
QEMU `virt` bukan model B866F/S4. Decoder Amlogic, Mali, HDMI, audio, USB
fisik, Wi-Fi, AVB, secure world vendor, Widevine/Netflix, serta init Android
belum diuji. Driver media hasil eksperimen pasangan driver tidak dimuat.
Tes ini juga tidak membuktikan kelengkapan patch keamanan Mei 2026.

Artifact hanya berisi konfigurasi dan log diagnostik, tanpa kernel image,
boot.img, vendor_boot.img atau paket flashing. Keberhasilan workflow bukan
izin instalasi; jalur pemulihan perangkat tetap harus diverifikasi.

Referensi mesin virtual:
https://www.qemu.org/docs/master/system/arm/virt.html
