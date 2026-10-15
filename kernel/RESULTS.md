# Hasil eksperimen kernel — 15 Oktober 2026

**5.15.196 berhasil dibangun dari source, tetapi belum kompatibel sebagai pengganti langsung dengan seluruh modul perangkat yang sekarang terpasang. Tidak diinstal ke STB.**

## Cakupan pemeriksaan

Audit read-only mencakup 160 berkas modul, termasuk seluruh 131 modul yang sedang
dimuat saat pengambilan data. Ada 2.531 simbol impor unik pada semua berkas;
2.400 di antaranya digunakan oleh modul yang sedang dimuat.
Data berasal dari 147 berkas yang dibaca langsung dan 22 modul pada cadangan
vendor_boot yang sudah ada, dengan sembilan berkas tumpang tindih. CRC impor
dan ekspor pada sembilan berkas tersebut sama. SHA-256 cadangan cocok dengan
manifest yang sebelumnya diverifikasi terhadap perangkat.

Binary modul dan cadangan firmware tidak diunggah. Repo hanya berisi konfigurasi,
metadata simbol/CRC, source alat, dan patch source.

## Hasil build dan ABI

| Pemeriksaan | Khadas Android 14 5.15.153 | CoreELEC Amlogic 5.15.196 + patch capture |
|---|---:|---:|
| Build vmlinux | Berhasil | Berhasil |
| CRC module_layout | 0x115475ea — cocok | 0x115475ea — cocok |
| Modul aktif dengan CRC berbeda | 23 dari 131 | 23 dari 131 |
| Simbol aktif berbeda, unik | 25 | 23 |
| Simbol aktif cocok dengan vmlinux, unik | 1.830 | 1.838 |
| Simbol cocok melalui modul aktif lain, unik | 538 | 538 |
| Simbol aktif belum ditemukan penyedianya | 7 | 1 |

Hitungan simbol unik berbeda dari jumlah pemakaian simbol oleh setiap modul.
Satu simbol bisa dipakai banyak modul. Kedua build memakai clang 18; firmware
memakai clang 17. Ini pemeriksaan statis, bukan uji boot, signature/namespace,
atau pemutaran video.

Empat sampel awal (amlogic-socinfo, Mali, LED ZTE, dan cfg80211) tidak menunjukkan
CRC berbeda untuk simbol yang ditemukan di vmlinux. Audit yang diperluas
menemukan masalah yang tidak terlihat pada empat sampel tersebut. Dataset
workflow terbaru sudah diperluas menjadi 160 berkas; dua run di bawah masih
menggunakan empat sampel pada laporan CI bawaannya. Angka 131/160 di halaman
ini dihitung lokal dari tabel simbol hasil run yang sama.

- [Build Khadas Android 14](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38715114665)
  — commit workflow `04d8fa62fc129e30f9a940c23bae49646d665afe`.
- [Build 5.15.196 dengan patch](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38717939063)
  — commit workflow `92e80365e13b2db3dea9aac7ff6d2293a5b91849`.

SHA-256 artifact diagnostik yang diperiksa:

- Khadas: `41e819c231e48ef0393307331cc45775576eda24f766ed3b6462c0ca74195218`.
- CoreELEC: `7db1f43302479b80d606289c7768400a8417aabacfc89b0d224a1756b1efeb69`.

## Penghambat pada 5.15.196

Perbedaan terutama mengenai interface vframe, decoder, buffer manager,
deinterlacer, dan hook UVM. Modul yang terpengaruh meliputi decoder AV1,
H.264, H.265, VP9, amvdec_ports, decoder_common, dan media_sync.
amlogic-wireless juga membutuhkan CRC berbeda untuk `pwm_set_times_tee`
dan `to_meson_pwm_tee`; simbol `sdio_get_device` belum ditemukan pada kernel
kandidat maupun ekspor modul yang sedang dimuat.

Patch capture hanya memperbaiki akses field opsional pada source CoreELEC.
Guard-nya mengikuti deklarasi struct upstream. Konfigurasi capture perangkat
tidak diubah; objek video_hw.o dan build vmlinux penuh berhasil dikompilasi.
Patch ini tidak menyelesaikan perbedaan ABI di atas.

Pekerjaan berikutnya memerlukan source/header vendor yang cocok, atau pasangan
kernel dan modul yang dibangun bersama, lalu pemeriksaan ulang semua dependensi
yang dipertahankan. Mengubah CRC, mengabaikan MODVERSIONS, atau mengganti
vermagic bukan penyelesaian perbedaan struktur/interface.

## Pemulihan dan patch keamanan

Pada unit yang diuji, metadata super menunjukkan logical partition B tanpa
data extents, termasuk system_b dan vendor_b. Keberadaan boot_b tidak membuktikan
ada sistem cadangan yang dapat di-boot. Tidak ada flag slot atau partisi yang diubah.
USB ADB pernah bekerja saat Android aktif melalui override runtime; USB recovery
dan fastboot belum menjadi jalur restore yang terverifikasi. Tidak dilakukan flashing.

Kernel baru tidak otomatis memenuhi patch keamanan Android Mei 2026.
[Bulletin resmi Mei 2026](https://source.android.com/docs/security/bulletin/2026/2026-05-01)
mencantumkan perbaikan adbd dan mensyaratkan perbaikan bulletin sebelumnya.
Unit masih melaporkan patch 2025-05-01 dan menjalankan kernel asli
5.15.153-android14-11-maybe-dirty. Versi modul adbd factory 340090000
dicatat untuk audit, bukan bukti bahwa ada/tidak ada backport tertentu.

Tidak ada boot.img, kernel binary, signing key, atau paket flashing yang dipublikasikan.
