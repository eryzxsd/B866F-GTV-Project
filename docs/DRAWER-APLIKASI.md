# Aplikasi GTV

Drawer aplikasi mandiri untuk remote TV, dengan antarmuka Bahasa Indonesia dan
nama **Aplikasi GTV**. Paket: `com.local.b866f.appdrawer`.

Ini implementasi baru dari source proyek, bukan APK EBS yang ditandatangani ulang.
Tidak menyertakan kode, wallpaper, atau aset milik drawer EBS. Banner dan ikon
aplikasi dibaca dari paket yang sudah terpasang, bukan didistribusikan oleh repo.

## Fitur

- Grid banner mendatar yang ringkas seperti drawer lama, tujuh kolom secara
  default dan nama di bawah tile yang difokuskan; ikon sebagai cadangan.
- Cari nama aplikasi; urut A–Z, Z–A, atau terakhir dibuka **melalui drawer ini**.
- Tahan OK atau tekan Menu untuk membuka opsi aplikasi: buka, favorit,
  sembunyikan dari drawer, atau info aplikasi Android.
- Favorit diletakkan di depan; tombol Semua/Favorit memfilter daftar.
- Tombol Tersembunyi untuk menampilkan kembali aplikasi yang disembunyikan.
- Pilihan 5/6/7 kolom, banner/ikon, tema Gelap/Biru malam, dan reset pengaturan.
- Favorit dan preferensi disimpan secara lokal. Menyembunyikan aplikasi tidak
  menonaktifkan, menghentikan, atau menghapus aplikasi tersebut.

## Batas dan izin

Drawer mencari activity `LEANBACK_LAUNCHER` dan `LAUNCHER`, satu entri per paket,
dengan activity TV diutamakan. Paket tanpa activity peluncur tidak ditampilkan.
Drawer sendiri dan drawer EBS lama dikecualikan dari grid.

Tidak memiliki filter HOME dan tidak mengganti Google TV Home. Tidak memerlukan
root, internet, aksesibilitas, akses notifikasi, usage access, atau layanan latar
belakang. Riwayat terakhir dibuka hanya mencatat peluncuran melalui drawer ini;
bukan riwayat pemakaian seluruh sistem. Penerima perubahan paket hanya aktif
saat activity terlihat. Cache gambar dibatasi 6 MiB dan pemuatan dilakukan di
worker agar tidak memblokir fokus remote.

## Build dan uji berdampingan

Gunakan `tools/build_android.py --component app-drawer` dengan argumen SDK, Java,
dan signing key lokal yang dijelaskan dalam [panduan build](BUILD.md). Signing key
tidak disertakan. APK dibangun ke `dist/app-drawer.apk`.

```sh
adb -s ALAMAT_ADB install -r dist/app-drawer.apk
adb -s ALAMAT_ADB shell am start -n com.local.b866f.appdrawer/.DrawerActivity
```

Instalasi ini tidak menimpa `com.ebsproject.drawer` dan tidak mengubah shortcut
All Apps lama. Buka **Aplikasi GTV** dari daftar aplikasi Google TV. Jangan
menonaktifkan drawer lama sebelum menguji tampilan dan memilih shortcut baru.

Untuk menghapus pratinjau ini saja:

```sh
adb -s ALAMAT_ADB uninstall com.local.b866f.appdrawer
```

Tidak perlu reboot atau perubahan partisi. Pemeriksaan pada satu B866F bukan
jaminan seluruh aplikasi atau firmware lain kompatibel.

## Hasil pemeriksaan pratinjau

Versi 0.2 mengubah grid kartu besar menjadi banner 16:9 yang ringkas, mengurangi
jarak baris, dan menampilkan nama hanya pada tile yang difokuskan. Fokus remote,
Menu, dan scroll diperiksa ulang. Pencarian dan kontrol lain tetap tersedia.

Pemeriksaan fungsi pada versi 0.1:

Pada B866F Android 14, 29 aplikasi dengan activity peluncur terdeteksi. Pemeriksaan
pencarian, A–Z/Z–A, filter favorit, sembunyikan/pulihkan, Menu, tahan OK, dan
scroll grid berhasil. AIDA64 berhasil dibuka. Pilihan kolom, ikon/banner, dan tema
bertahan setelah drawer dihentikan lalu dibuka kembali; reset juga bekerja.
Tidak ada crash/ANR tercatat pada drawer selama pemeriksaan ini. Penghentian
sengaja untuk uji persistensi dan pembaruan APK dicatat sebagai kejadian normal.
APK EBS asli dan default Google TV Home tidak diubah. Riwayat semua aplikasi,
setiap aplikasi terpasang, dan firmware lain belum diuji menyeluruh.
