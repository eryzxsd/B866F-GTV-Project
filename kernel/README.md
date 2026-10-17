# Eksperimen ABI kernel

> **ARSIP — DIHENTIKAN pada 17 Oktober 2026.** Upaya upgrade kernel dan patch
> keamanan penuh telah berakhir. Isi folder ini dipertahankan sebagai catatan
> eksperimen historis, bukan pengembangan aktif, roadmap, atau paket siap pasang.
> Petunjuk dan status menunggu di bawah merupakan konteks saat eksperimen dibuat.
> Fokus aktif proyek adalah kustomisasi Google TV.

Workflow **Kernel ABI baseline (diagnostic only)** dijalankan manual melalui tab
Actions. Tidak berjalan otomatis saat push/PR dan tidak mengakses STB.

Baseline saat ini menggunakan sumber publik Khadas cabang Android 14,
5.15.153, sama dengan versi dasar kernel firmware. Ini hanya baseline untuk
mempelajari perbedaan ABI Amlogic, bukan kandidat pembaruan. Port ke kernel baru
memerlukan pekerjaan terpisah; sumber ini belum terbukti sama dengan sumber ZTE.

Pilihan workflow `source`:

- `khadas-android14`: baseline 5.15.153 pada sumber Khadas Android 14.
- `coreelec-5.15.196`: eksperimen sumber Amlogic 5.15.196 dari CoreELEC,
  bukan firmware Android B866F. Tetap wajib melewati pemeriksaan ABI yang sama.

Kedua pilihan memakai commit tetap. Tidak ada yang dinyatakan siap diinstal.

Pilihan tambahan `driver_probe=true` hanya tersedia untuk sumber CoreELEC.
Sesudah vmlinux selesai, runner membangun modul in-tree dan decoder dari
[CoreELEC media_modules-aml](https://github.com/CoreELEC/media_modules-aml/tree/c15aebb1ac93028d0aceadf8f35dda2204d33424)
pada commit tetap `c15aebb1ac93028d0aceadf8f35dda2204d33424`.
Pilihan decoder mencakup H.264, H.265, VP9, AV1/T5D dan jalur V4L;
encoder H.264, multi dan JPEG juga dicakup sebagai konsumen interface decoder.
Ini percobaan pasangan source kernel/driver, bukan driver ZTE yang terverifikasi.
`make modules` dan modpost tetap memeriksa dependensi secara normal.

Jika berhasil dikompilasi, checker membaca CRC impor/ekspor dari ELF hasil build,
kemudian memeriksa himpunan provider yang diusulkan: vmlinux baru, modul media
baru, amlogic-wireless baru, dan modul lama lainnya. Konsumen modul lama juga
diperiksa agar perubahan ekspor driver baru tidak terlewat.
`module-exports.json` berisi metadata CRC ekspor dari audit privat sebelumnya;
tidak memuat binary modul. Laporan semua berkas dapat mencantumkan provider
alternatif yang tidak dimuat bersamaan, sehingga duplikasi perlu ditinjau
menurut profil driver perangkat. Ini belum menguji signature, namespace,
urutan inisialisasi, interface userspace, DRM atau Netflix.
Artifact tetap hanya log dan metadata. Tidak menjalankan `modules_install`,
tidak menyalin firmware, tidak membuat boot image, dan tidak menghubungi STB.

`object_preflight=true` (bersama `driver_probe=true` dan sumber CoreELEC)
menjalankan uji cepat objek media yang dipilih konfigurasi sebelum build penuh.
Enam objek decoder/V4L/buffer manager wajib ditemukan sebagai bukti cakupan dasar.
Mode ini memakai [target direktori Kbuild resmi](https://www.kernel.org/doc/html/v5.15/kbuild/modules.html#building-separate-files)
dan konfigurasi/flag yang sama dengan probe penuh. Kernel headers disiapkan,
tetapi vmlinux lengkap dan modpost media tidak dijalankan. Hasil hijau hanya
menunjukkan objek yang dipilih konfigurasi bisa dikompilasi, bukan kompatibilitas ABI atau boot.
Grup antreannya terpisah sehingga uji cepat tidak membatalkan eksperimen penuh.
Source media juga mendapat patch guard AVBC wrapper: keseluruhan cabang
`if/else` opsional dijaga oleh CONFIG_AMLOGIC_MEDIA_WRAPPER, sehingga source
tetap valid saat fitur off. Perilaku cabang saat fitur on dipertahankan;
flag wrapper perangkat tidak diaktifkan untuk menutupi kesalahan kompilasi.

Sumber CoreELEC mendapat patch kecil berlisensi GPL-2.0-only di `patches/`:
makro video layer memakai field capture hanya bila VIDEOCAPTURE aktif, sesuai
guard deklarasi struct upstream. Flag konfigurasi perangkat tidak diubah.
Patch Kconfig terpisah memindahkan GPIO-key ke luar kondisi AMLOGIC_INPUT
agar GPIO-key tetap built-in saat meson-remote berupa modul, sesuai referensi.
Aturan ini diverifikasi dengan parser Kconfig pada subtree input terisolasi;
hasil build penuh diperlukan sebelum menyatakan integrasinya berhasil.
Build dihentikan bila penempatan GPIO-key menyimpang dari referensi.
Patch SI2183 menambahkan dependensi I2C_MUX, mengikuti aturan SI2168 di file
yang sama. Frontend tambahan ini tidak ada di konfigurasi referensi, tetapi
default source publik memilihnya sebagai modul walaupun I2C_MUX=n. Tanpa
dependensi tersebut modpost gagal pada tiga fungsi mux. Uji Kconfig terisolasi
memastikan frontend tidak dipilih saat mux off dan tersedia saat mux=m.
Nilai I2C_MUX referensi dipertahankan dan diperiksa. Opsi yang baru dikenal
source publik dicatat terpisah di `config-added.json` agar default tambahan
tidak hilang dari laporan konfigurasi.
Objek `video_hw.o` dikompilasi lebih awal sebagai pemeriksaan integrasi patch.
SHA-256 patch dicatat pada laporan. Jika build penuh gagal, `partial.symvers`
menyimpan CRC objek yang sempat dikompilasi; tabel parsial ini bukan hasil ABI lengkap.

`b866f-running.config` adalah konfigurasi build dari perangkat B866F Android 14.
`vendor-symbol-requirements.json` berisi nama simbol dan CRC yang dibutuhkan
160 modul perangkat; tidak berisi binary modul, firmware, identitas unik
perangkat, kredensial, atau signing key. `module-scope.json` mencatat 131 modul
yang sedang dimuat saat audit. Pembacaan langsung menemukan 147 berkas;
cadangan vendor_boot menambahkan 13 berkas berbeda. Sembilan modul yang ada
di kedua sumber mempunyai CRC sama. Seluruh modul yang sedang dimuat terwakili,
tetapi ini bukan klaim mencakup setiap driver/konfigurasi yang mungkin digunakan.

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
Pilihan CoreELEC memakai [linux-amlogic](https://github.com/CoreELEC/linux-amlogic)
dan [common_drivers](https://github.com/CoreELEC/common_drivers) dari proyek tersebut.
Masing-masing mempertahankan lisensi upstream (kernel GPL-2.0 dan lisensi per file).
Konfigurasi di sini mengikuti lisensi kernel GPL-2.0-only. Tidak ada kode sumber
kernel atau binary proprietary dari firmware yang didistribusikan ulang.

Belum ada prosedur pemulihan melalui USB yang terverifikasi ketika Android gagal
boot. Jangan gunakan hasil eksperimen ini untuk menulis partisi perangkat.

## Hasil awal, 15 Oktober 2026

Eksperimen pertama menggunakan cabang Linux Khadas 5.15.137. Pemeriksaan inti
selesai: `module_layout` hasil build `0x38e28e16`, sedangkan keempat sampel modul
memerlukan `0x115475ea`. Karena berbeda, build penuh dilewati. Ini membuktikan
baseline lama tersebut tidak dapat menggantikan kernel perangkat secara langsung.
[Laporan eksperimen lama](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38714564258).

Setelah itu ditemukan cabang `khadas-vim4-android14` pada kedua repo upstream.
Baseline dialihkan ke commit tetap cabang tersebut untuk menguji sumber yang
lebih dekat. Hasil lama tidak boleh dianggap sebagai hasil cabang Android 14.

Pemeriksaan inti `module_layout` pada cabang Android 14 5.15.153 dan eksperimen
CoreELEC 5.15.196 telah lolos: CRC sama dengan kebutuhan empat sampel perangkat,
`0x115475ea`. Kedua build penuh telah selesai; [hasil audit yang diperluas](RESULTS.md)
menunjukkan bahwa kecocokan simbol inti belum cukup untuk penggantian langsung.
Ini bukan bukti kompatibilitas seluruh driver, apalagi hasil uji boot.

Build Khadas Android 14 telah selesai. Empat sampel awal tidak memiliki CRC
berbeda untuk simbol yang ditemukan di vmlinux. Audit lebih luas menemukan
25 simbol berbeda yang digunakan oleh 23 modul yang sedang dimuat, terutama
interface video. Karena itu, empat sampel awal tidak cukup untuk menyatakan
baseline sebagai pengganti langsung. Dataset workflow diperluas ke 160 modul
agar pemeriksaan berikutnya tidak bergantung pada empat sampel tersebut.

Temuan berikut berasal dari eksperimen **5.15.137**:

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

Lihat [hasil dan penghambat saat ini](RESULTS.md) serta
[riwayat eksperimen](https://github.com/eryzxsd/B866F-GTV-Project/actions/workflows/kernel-baseline.yml).
Jangan menafsirkan workflow hijau sebagai izin flashing.

Run awal telah mencapai kompilasi driver, tetapi berhenti pada watchpoint
Amlogic: konfigurasi Android 14 memilih nama register yang tidak tersedia pada
sumber kernel publik lama. Pemeriksaan inti dilakukan lebih awal untuk
menghindari build penuh jika ABI dasar sudah berbeda; fitur driver tidak
dinonaktifkan untuk memaksakan kelulusan kompatibilitas.

Patch keamanan Android mencakup komponen selain kernel. Membuat kernel baru
tidak otomatis memenuhi seluruh bulletin Android Mei 2026. Nilai patch level
tidak diubah oleh eksperimen ini.
