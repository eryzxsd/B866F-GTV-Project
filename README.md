# B866F GTV Project

Kustomisasi Google TV untuk **ZTE B866F V1.1 dengan basis EBS Project Android 14**. Dokumentasi utama dalam Bahasa Indonesia.

**Rilis awal: pratinjau untuk pengembang.** Diuji pada satu STB. Ini kumpulan kode dan alat untuk merakit perubahan, bukan firmware universal atau ROM siap flash. Firmware, kernel, aplikasi Google, dan alat berbayar milik pihak lain tidak disertakan.

![Menu Samba dalam pengaturan dua panel](docs/images/samba-settings.png)

## Fitur

- Tampilan Settings dua panel, perbaikan jarak baris, fokus, ikon, dan sakelar.
- [Aplikasi GTV](docs/DRAWER-APLIKASI.md): drawer mandiri dengan pencarian, favorit, aplikasi tersembunyi, dan pilihan grid; diuji berdampingan dengan drawer lama.
- Menu **B866F GTV Project → Ganti launcher**: mendeteksi launcher HOME yang terpasang, memilih default, dan menghentikan launcher sebelumnya setelah pilihan baru terverifikasi. Komponen HOME yang dinonaktifkan oleh alat dicatat untuk pemulihan.
- Menu **Samba server**: berbagi folder internal `Shared` dan USB secara terpisah, kata sandi, akses tulis opsional, dan mulai saat boot opsional.
- Layanan kompatibilitas profil lokal untuk Google TV Home **1.0.994451607**. Hanya launcher dengan paket dan sertifikat Google yang sesuai dapat memanggil layanan. Profil anak/multi-profil belum didukung.
- [Panel notifikasi](docs/NOTIFIKASI.md) dengan overlay routing yang bertahan setelah reboot, sehingga System UI tidak perlu dimulai ulang saat Home memuat pada boot berikutnya. [Kartu popup](docs/KARTU-NOTIFIKASI.md) adalah komponen opsional terpisah.

Samba memakai SMB2/3, login wajib, signing wajib, dan pembatasan jaringan lokal. Kondisi awal: **server mati, akses tulis mati, mulai saat boot mati**. Tidak ada port router yang dibuka.

## Progres kernel dan patch keamanan

**Pembaruan status: 17 Oktober 2026 · Upaya upgrade kernel dan patch keamanan penuh dihentikan · Tidak ada paket upgrade siap dipasang.**

Fokus aktif beralih ke stabilitas kustomisasi Google TV. Upaya upgrade kernel
dan target patch keamanan penuh Mei 2026 sudah dihentikan, bukan dijeda.
Source, workflow manual, dan bukti riset tetap tersedia sebagai arsip hasil
eksperimen; kotak yang belum tercentang di bawah mencatat batas hasil, bukan
rencana pekerjaan lanjutan. Tidak ada build atau investigasi lanjutan yang
direncanakan. Pekerjaan keamanan individual pun tidak dilanjutkan otomatis;
pekerjaan baru memerlukan permintaan baru dari pemilik proyek.

Tracker ini diperbarui manual berdasarkan hasil yang sudah dicatat. Kotak tercentang
menunjukkan pemeriksaan dengan cakupan tertentu yang sudah selesai, bukan persentase
kesiapan firmware atau perkiraan waktu selesai. Keberhasilan QEMU tidak membuktikan
kompatibilitas hardware B866F atau cakupan patch Android.

### Kernel 5.15.196

- [x] Audit awal modul/ABI perangkat dan build kernel dari source.
- [x] Boot Linux inti di QEMU, pemeriksaan inti, dan shutdown bersih.
- [x] Uji trust/signature serta load/unload **37 modul asli** di QEMU; I/O zram terbatas berhasil.
- [ ] Verifikasi seluruh driver vendor yang diperlukan, termasuk media/decoder dan Wi-Fi, beserta fungsi hardware nyata.
- [ ] Buktikan jalur restore mandiri, lalu uji boot B866F, Android, audio/video, remote, dan Netflix/DRM.
- [ ] Siapkan serta validasi paket pembaruan yang dapat dipulihkan sebelum rilis.

[Bukti dan batas uji kernel/emulator](kernel/POST_QEMU.md). Uji 37 modul tidak
mencakup seluruh driver vendor atau membuktikan operasi perangkat USB/HID nyata.
Eksplorasi upstream yang lebih baru masih parsial dan tidak termasuk hasil di atas.

### Patch keamanan Android — target Mei 2026

- [x] Susun inventaris awal 13 bulletin Mei 2025–Mei 2026; sebagian cakupan masih memerlukan review.
- [x] Siapkan backport adbd CVE-2026-0073 dan uji guard crypto pada host.
- [x] Build binary kandidat adbd ARM32 dan inspeksi offline perubahan serta sebagian interface-nya.
- [ ] Selesaikan audit/perbaikan seluruh komponen yang berlaku: platform Android, Mainline, kernel, dan vendor.
- [ ] Selesaikan kompatibilitas runtime Android, signing/paket pembaruan, dan pemulihan.
- [ ] Validasi pada STB dan buktikan cakupan patch sebelum menyatakan level keamanan baru.

[Bukti dan batas audit keamanan](security/README.md). Backport adbd saja tidak
memenuhi seluruh level patch Mei 2026. **Belum ada kernel baru atau pembaruan
keamanan dari eksperimen ini yang dipasang ke STB.** Basis terakhir yang diverifikasi
tetap kernel `5.15.153-android14-11-maybe-dirty` dan patch **1 Mei 2025**; tanggal
patch tidak diubah untuk sekadar menampilkan versi lebih baru.

## Kompatibilitas yang benar-benar diuji

| Komponen | Basis pengujian |
|---|---|
| STB | B866F V1.1, Amlogic S4 / oppen |
| OS | EBS Android 14, `EBS.UKG3.250115.001.eng.ztestb.20250704.161752` |
| Vendor build | `V89511304.1018` |
| Kernel | `5.15.153-android14-11-maybe-dirty` |
| Patch keamanan | 1 Mei 2025 |
| Google TV Home | 1.0.994451607 / 831927, aplikasi Google asli |
| Settings target SHA-256 | `b798e976ac4fea52d39c30f98845682bf20bbbe06224e4c592b4f43165197d1f` |

**Proyek ini tidak meningkatkan patch keamanan ke Mei 2026 dan tidak mengganti kernel.** Nama proyek adalah nama kustomisasi pribadi. Firmware dasarnya tetap karya EBS dan komponen pihak lain tetap milik pembuatnya.

Eksperimen source build di GitHub Actions didokumentasikan dalam
[pemeriksaan ABI kernel](kernel/README.md). Workflow hanya menghasilkan laporan
diagnostik; tidak menghasilkan paket instalasi atau menulis partisi STB.
Temuan patch Android dan batas cakupan kandidat dicatat dalam
[audit keamanan](security/README.md), terpisah dari keberhasilan boot emulator.

## Mulai dari sini

1. Baca [panduan instalasi](docs/INSTALASI.md). Siapkan recovery yang sudah diuji sebelum perubahan yang membutuhkan reboot.
2. Pasang dependensi pengembangan dan siapkan berkas lokal sesuai [panduan build](docs/BUILD.md).
3. Jalankan `python tools/preflight.py --serial ALAMAT_ADB`. Pemeriksaan ini hanya membaca informasi perangkat.
4. Rakit APK/helper dan paket modul lokal. Tidak ada unduhan ROM Google atau firmware EBS otomatis.
5. Ikuti instalasi manual bertahap. Simpan launcher lama sampai launcher baru dapat dibuka dan dinavigasi.

Tidak ada installer satu klik untuk semua B866F. Pemeriksaan APK Settings sengaja ketat karena ID resource berbeda antar-ROM.

## Samba

Buka **Settings → B866F GTV Project → Samba server**. Aktifkan server lalu buka **Cara menghubungkan** untuk melihat IP, akun `shell`, dan kata sandi. Di File Explorer Windows masukkan alamat yang ditampilkan, misalnya `\\IP-STB\Shared` atau `\\IP-STB\USB`.

- `Shared` adalah `/storage/emulated/0/Shared`, bukan seluruh penyimpanan internal.
- `USB` berisi direktori volume dari `/mnt/media_rw`.
- **Izinkan menulis** mengizinkan unggah, ubah, dan hapus. Biarkan mati jika hanya ingin membaca.
- Kata sandi tidak dicantumkan dalam repo. Pengaturan disimpan privat pada perangkat.

Pengujian: login Windows dan daftar share berhasil; kata sandi salah ditolak; mode baca menolak unggah; unggah/unduh 2 MiB cocok, nama Unicode, rename, dan hapus berhasil. USB fisik belum diuji karena tidak ada drive terpasang. Autostart diuji dengan restart controller, belum reboot penuh setelah penambahan Samba.

## Pemulihan, laporan masalah, dan kontribusi

Lihat [pemulihan dan rollback launcher/Settings/notifikasi](docs/PEMULIHAN.md), [catatan keamanan](SECURITY.md), dan [kontribusi](CONTRIBUTING.md). Jangan unggah dump perangkat, kata sandi, private key, serial perangkat, token ADB, atau log akun Google ke issue.

Kode proyek dan adaptasi yang dicakup dilisensikan Apache-2.0, kecuali berkas yang menyebut lisensi lain (konfigurasi kernel memakai GPL-2.0-only); lihat [LICENSE](LICENSE) dan [NOTICE](NOTICE). Samba dan dependensinya diambil dari Termux saat build lokal, memakai lisensi masing-masing. Google TV, Android TV, ZTE, dan EBS tidak mensponsori proyek ini.

English: experimental developer preview for one tested B866F firmware base. Indonesian documentation is authoritative. No proprietary firmware/Google APKs, kernel update, or security-patch upgrade is distributed.
