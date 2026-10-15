# Hasil pengujian rilis awal

Tanggal: 15 Oktober 2026. Basis: satu B866F V1.1 EBS Android 14; bukan pengujian lintas perangkat.

## Source publik

- APK tools, layanan profil, dan overlay dikompilasi ulang dari direktori publik dan lolos verifikasi tanda tangan memakai keystore uji lokal.
- Dua helper Go berhasil di-cross-compile untuk Linux ARMv7; shim C berhasil dibangun dengan Zig 0.11.0.
- Seluruh 41 paket Termux yang dipin lolos SHA256; runtime Samba dapat dirakit ulang.
- Paket modul lokal berhasil dirakit; tidak menyertakan password/config privat, bootanimation, atau helper artwork lama.
- Preflight hanya-baca terhadap perangkat pengujian mengenali model/OS dan hash Settings yang sesuai.
- Pemeriksaan file publikasi dan whitespace Git lulus. Keystore, APK Google, APK firmware, config privat, dan berkas build tidak masuk Git.

Paket lokal hasil build publik belum dipasang pada STB kedua. Guard installer publik diperiksa secara statis, belum diuji dengan instalasi Magisk baru. Berkas ini tidak mengklaim pengujian itu sudah dilakukan.

## Implementasi yang sedang berjalan pada perangkat pengujian

- Google TV Home 1.0.994451607 tampil dan dinavigasi normal; pemilik perangkat mengonfirmasi artwork dan ikon terisi.
- Pemilih launcher memverifikasi HOME dan menghentikan launcher sebelumnya setelah pilihan berhasil. Sebagian layanan Google bisa hidup lagi akibat permintaan komponen lain Android.
- Menu Samba tampil di submenu proyek; koneksi Windows terautentikasi dan enumerasi share berhasil.
- Password salah ditolak. Mode read-only menolak unggah. Mode tulis: transfer biner 2 MiB cocok, nama Unicode, rename dan hapus berhasil. Berkas uji dibersihkan.
- Share USB dapat didaftarkan tetapi belum ada USB fisik untuk menguji transfer dari drive.
- Autostart Samba diuji dengan restart controller, bukan reboot penuh setelah penambahan fitur.
- Keadaan akhir: Samba off, read-only on, autostart off; port 445 tertutup dan tidak ada worker Samba/RPC. SELinux tetap Enforcing.

Instalasi publik diharapkan divalidasi bertahap, dengan hasil gagal maupun berhasil dilaporkan tanpa data pribadi.
