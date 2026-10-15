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

Runner Linux sementara membangun vmlinux untuk menghasilkan tabel simbol.
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
