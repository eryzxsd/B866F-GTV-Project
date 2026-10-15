# Eksperimen ABI kernel

Workflow **Kernel ABI baseline (diagnostic only)** dijalankan manual melalui tab
Actions. Tidak berjalan otomatis saat push/PR dan tidak mengakses STB.

Tahap pertama menggunakan sumber publik Khadas 5.15.137, **lebih lama** dari
kernel firmware 5.15.153. Ini hanya baseline untuk mempelajari perbedaan ABI
Amlogic, bukan kandidat pembaruan. Port ke kernel baru memerlukan pekerjaan
terpisah; sumber publik ini belum terbukti sama dengan sumber ZTE.

`b866f-running.config` adalah konfigurasi build dari perangkat B866F Android 14.
`vendor-symbol-requirements.json` berisi nama simbol dan CRC yang dibutuhkan
empat contoh modul perangkat; tidak berisi binary modul, firmware, identitas
perangkat, kredensial, atau signing key. Sampel ini tidak mencakup semua driver.

Runner Linux sementara terlebih dahulu membangun objek inti `kernel/module.o`
dan memeriksa CRC `module_layout`. Jika CRC berbeda dari kebutuhan driver,
build penuh dilewati dan hasil dilaporkan sebagai tidak kompatibel untuk
penggantian langsung. Jika lolos, runner melanjutkan build vmlinux untuk tabel simbol.
Artifact hanya berisi konfigurasi, log, metadata sumber, dan perbandingan CRC.
Binary kernel tidak diunggah. Hasil build berhasil pun tidak membuktikan kernel
bisa boot atau telah memenuhi patch keamanan Mei 2026. Compiler runner clang 18
berbeda dari firmware clang 17; perbedaan ini dicatat dalam laporan.

Sumber diambil pada commit tetap dari [Khadas Linux](https://github.com/khadas/linux)
dan [Khadas common_drivers](https://github.com/khadas/common_drivers).
Masing-masing mempertahankan lisensi upstream (kernel GPL-2.0 dan lisensi per file).
Konfigurasi di sini mengikuti lisensi kernel GPL-2.0-only. Tidak ada kode sumber
kernel atau binary proprietary dari firmware yang didistribusikan ulang.

Belum ada prosedur pemulihan melalui USB yang terverifikasi ketika Android gagal
boot. Jangan gunakan hasil eksperimen ini untuk menulis partisi perangkat.

## Hasil awal, 15 Oktober 2026

Konfigurasi berhasil diproses oleh runner. Opsi inti ARM64, MODVERSIONS,
AMLOGIC_DRIVER, AMLOGIC_BREAK_GKI, dan AMLOGIC_IN_KERNEL_MODULES tetap aktif.
Namun, konfigurasi sumber publik berbeda dari firmware: antara lain opsi
STB_ZTE_DRIVER tidak tersedia, INIT_ENV_ARG_LIMIT berubah dari 32 ke 128, dan
sejumlah opsi Android/Amlogic yang lebih baru tidak dikenal. Perbedaan lengkap
disimpan dalam artifact `config-differences.json` setiap run.

Penyesuaian build diagnostik:

- Menggunakan LLVM=1 dan PATH LLVM 18 sesuai antarmuka Makefile vendor lama.
- Mengabaikan nama warning GCC yang tidak dikenal oleh Clang.
- Menonaktifkan UAPI_HEADER_TEST karena header DVB publik gagal tes standalone
  (`struct timespec` tidak lengkap). Ini tes saat build, bukan fitur runtime.
  Konfigurasi referensi perangkat tetap disimpan utuh; penyesuaian tercatat di laporan.

Belum ada hasil kecocokan ABI dari baseline pada saat catatan ini ditulis.
Lihat [riwayat eksperimen](https://github.com/eryzxsd/B866F-GTV-Project/actions/workflows/kernel-baseline.yml)
untuk status terbaru. Jangan menafsirkan workflow hijau sebagai izin flashing.

Run awal telah mencapai kompilasi driver, tetapi berhenti pada watchpoint
Amlogic: konfigurasi Android 14 memilih nama register yang tidak tersedia pada
sumber kernel publik lama. Pemeriksaan inti dilakukan lebih awal untuk
menghindari build penuh jika ABI dasar sudah berbeda; fitur driver tidak
dinonaktifkan untuk memaksakan kelulusan kompatibilitas.

Patch keamanan Android mencakup komponen selain kernel. Membuat kernel baru
tidak otomatis memenuhi seluruh bulletin Android Mei 2026. Nilai patch level
tidak diubah oleh eksperimen ini.
