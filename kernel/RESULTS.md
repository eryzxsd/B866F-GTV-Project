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

## Eksperimen pasangan driver berikutnya

[Run driver-probe](https://github.com/eryzxsd/B866F-GTV-Project/actions/runs/38721809377)
diluncurkan dari commit `b2aa3ccab393f99bb9bc53d3b8b87b1ee13535ab` dengan
`source=coreelec-5.15.196` dan `driver_probe=true`. Saat catatan ini dibuat,
pemeriksaan inti 160 modul dan objek video lolos; build penuh masih berjalan.
Belum ada hasil kompilasi driver baru atau klaim kompatibilitas dari run tersebut.
Run ini menambahkan source decoder publik `CoreELEC/media_modules-aml` pada
commit `c15aebb1ac93028d0aceadf8f35dda2204d33424`, pasangan branch CoreELEC yang sama.

Penelusuran dependensi secara konservatif dari 23 modul aktif yang berbeda
menjangkau 34 modul aktif. Sebelas konsumen tambahan mencakup driver Wi-Fi/
Bluetooth, encoder dan stream input. Ini bukan klaim bahwa semua 34 modul
pasti perlu diganti: CRC ekspor hasil build baru yang menentukan perbedaan
interface pada konsumen. Checker karena itu mencakup konsumen yang dipertahankan.
Versi checker sesudah commit run juga membedakan seluruh berkas audit dari
profil nama modul yang sedang dimuat; laporan run lama dapat dianalisis ulang
lokal menggunakan metadata ELF yang disimpan, tanpa mengulang kompilasi.

Pembacaan `/proc/kallsyms` menegaskan `sdio_get_device` dan entri ekspornya ada
pada kernel perangkat sekarang. Pada source CoreELEC yang dipilih fungsi itu
ada di `meson-gx-mmc.c`, tetapi tidak diekspor di sana; source wireless baru
tidak memakai impor tersebut. Rebuild wireless dapat mengubah kebutuhan ini,
tetapi tetap perlu pemeriksaan dependensi, bukan menambahkan CRC palsu.

Ada juga perbedaan konfigurasi input yang belum diselesaikan:
`AMLOGIC_GPIO_KEY=y` pada referensi menjadi `m` pada build publik, karena
Kconfig publik menempatkannya di dalam `if AMLOGIC_INPUT` sementara INPUT=m.
Perubahan penempatan driver dan opsi khusus ZTE yang tidak tersedia perlu
ditangani sebelum uji boot. Pemeriksaan CRC saja tidak mencakup kebutuhan ini.

Parser ELF baru dibandingkan dengan parser independen pada 22 modul normal-boot
cadangan privat: seluruh CRC impor/ekspor sama. Uji sintetis juga menangkap
perubahan ekspor provider yang membuat konsumen lama tidak cocok. Netflix,
DRM, interface userspace decoder dan boot tetap belum diuji pada kernel baru.

Perbaikan Kconfig GPIO-key kini disiapkan untuk build berikutnya. Pengujian
subtree input dengan Kconfiglib 14.1.0 menghasilkan INPUT=m/GPIO_KEY=m sebelum
patch dan INPUT=m/GPIO_KEY=y sesudah patch, sesuai penempatan pada referensi.
Patch hanya memindahkan deklarasi Kconfig; source penanganan tombol tidak
diubah. Ini belum hasil build penuh dengan patch tersebut. Build berikutnya
juga mencakup AV1 T5D dan encoder H.264/multi/JPEG yang dimuat pada audit.
