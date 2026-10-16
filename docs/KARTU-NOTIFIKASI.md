# Kartu notifikasi di pojok kanan atas

**Masalah versi 0.2 pada firmware uji:** jangan aktifkan accessibility service
**B866F: tahan Home untuk notifikasi** untuk pemakaian normal. Setelah service ini
diaktifkan, perpindahan Beranda/Aplikasi terasa berbeda dan fokus Setelan cepat
dapat terjebak di Bantuan & Masukan. Pengguna mengonfirmasi kedua masalah hilang
setelah hanya service Home tersebut dinonaktifkan. Kartu popup biasa tetap aktif.
Fitur tahan Home dinonaktifkan pada perangkat uji; source eksperimen dipertahankan
untuk investigasi, bukan direkomendasikan sebagai fitur stabil.

Komponen opsional `android/notification-cards` menampilkan kartu gelap dengan
sudut membulat, ikon, judul, isi, dan nama aplikasi pengirim. Ini berbeda dari
[panel notifikasi](NOTIFIKASI.md). Kartu ini meniru tampilannya, bukan komponen
Google yang dipindahkan.

Popup asli Google TV berhasil ditampilkan melalui pengujian komponen launcher.
Namun, jalur notifikasi aplikasi biasa belum berhasil melalui konfigurasi OEM
EBS. Percobaan overlay konfigurasi ditolak firmware. APK OEM, SystemUI, launcher,
dan framework tidak diganti untuk fitur ini.

## Perilaku dan batasan

- Notification listener diikat Android, tanpa root, jaringan, polling, atau log
  isi notifikasi. Deduplikasi hanya di memori, maksimal 64 entri.
- Kartu tidak mengambil fokus atau menerima input. Hilang sekitar 6,5 detik
  setelah tampil, atau saat notifikasi asal dihapus.
- Menampilkan notifikasi TV berprioritas normal ke atas, serta notifikasi non-TV
  berprioritas tinggi. Mengabaikan ongoing, foreground service, media, group
  summary, secret, pengguna lain, dan permintaan TV suppress-show-over-apps.
- Tidak tampil saat layar tidak interaktif/terkunci. Tidak memutar suara atau
  mengubah volume. Pesan baru yang terlalu rapat dibatasi.
- Mengabaikan LauncherX, Android, SystemUI, dan ControlDevice agar notifikasi
  internalnya tidak diduplikasi.

Versi 0.2 menambahkan **tekan dan tahan Home untuk detail** melalui accessibility
service opsional. Saat kartu terlihat, tahan Home sekitar satu detik lalu lepas.
Panel detail lokal menampilkan isi notifikasi, **Buka** jika tersedia aksi asal,
**Hapus notifikasi** jika dapat dihapus, serta **Tutup**. Buka menggunakan
PendingIntent asli; Hapus membatalkan notifikasi yang sama melalui listener.

Pada firmware uji, policy vendor tetap dapat membuka **Aplikasi Anda** sebelum
accessibility menerima rangkaian tombol. Karena itu panel dibuka sekali, 600 ms
setelah tombol dilepas. Tampilan aplikasi dapat terlihat sebentar di belakang
panel; Back dapat kembali ke tampilan tersebut. Tidak ada loop yang memaksa panel
kembali muncul setelah ditutup. Back atau Home baru selama jeda membatalkan
pembukaan yang tertunda.

Handler hanya mengambil rangkaian Home yang dimulai ketika kartu terlihat.
Home singkat diarahkan ke Home; tanpa kartu handler meneruskan tombol ke firmware.
Tidak meminta akses isi window, merekam ketikan, atau mengubah policy framework.
Footer petunjuk hanya tampil jika service terhubung; jika tidak, footer tetap
**Notifikasi dari [nama aplikasi]**. Kartu tidak muncul di atas panel detailnya.
Kartu ini tidak menyisipkan notifikasi ke penyimpanan internal Google TV dan tetap
merupakan implementasi proyek ini. Tidak semua aplikasi mengirim notifikasi yang
memenuhi filter.

## Build dan pemasangan opsional

Gunakan `tools/build_android.py --component notification-cards` dengan parameter
SDK/JDK dan keystore pengguna seperti komponen Android lainnya. Hasil build:
`dist/notification-cards.apk`. Kunci dan APK Google/OEM tidak disediakan.

```sh
adb install -r dist/notification-cards.apk
adb shell pm grant com.local.b866f.notificationcards android.permission.POST_NOTIFICATIONS
adb shell cmd appops set com.local.b866f.notificationcards SYSTEM_ALERT_WINDOW allow
adb shell cmd notification allow_listener com.local.b866f.notificationcards/.CardListener 0
```

Akses notifikasi memungkinkan aplikasi membaca notifikasi. Source ini memakainya
hanya untuk kartu lokal dan tidak meminta izin internet. Akses juga dapat diatur
melalui Settings → Special app access.

Handler tahan Home memakai izin tambahan melalui Settings → Accessibility,
tetapi **biarkan nonaktif pada firmware ini** karena regresi navigasi di atas.
Kartu biasa tetap bekerja tanpa handler Home. Jangan mengganti daftar
`enabled_accessibility_services` secara keseluruhan dari skrip karena dapat
menghapus pilihan service pengguna lain.

Uji notifikasi berlabel jelas; pesan contoh berakhir setelah 10 detik:

```sh
adb shell am start -n com.local.b866f.notificationcards/.PreviewActivity
adb shell am start -n com.local.b866f.notificationcards/.PreviewActivity --es mode hold
adb shell am start -n com.local.b866f.notificationcards/.PreviewActivity --es mode cleanup
```

Mode `hold` mempertahankan kartu contoh selama 25 detik untuk pengujian remote;
kartu aplikasi biasa tetap sekitar 6,5 detik. Android mengikat kedua service sesuai
izin masing-masing; tidak memerlukan service root atau perubahan service boot
Magisk. Siklus reboot belum diuji.

## Menonaktifkan atau menghapus

Nonaktifkan **B866F: tahan Home untuk notifikasi** di Accessibility untuk melepas
handler tombol saja. Jangan menonaktifkan seluruh Accessibility karena fitur lain
mungkin memerlukannya. Untuk menghapus aplikasi lengkap:

```sh
adb shell cmd notification disallow_listener com.local.b866f.notificationcards/.CardListener 0
adb shell cmd appops set com.local.b866f.notificationcards SYSTEM_ALERT_WINDOW default
adb uninstall com.local.b866f.notificationcards
```

Ini tidak mengubah panel Google TV. Izin overlay LauncherX adalah pengaturan
terpisah; pada perangkat uji izin itu diaktifkan untuk popup asli LauncherX.

## Validasi

Lihat [notification-cards-result.json](notification-cards-result.json). Kartu diuji
melalui notifikasi Android sungguhan, bukan pemanggilan fungsi gambar langsung.
Fokus window sebelum dan selama kartu tetap sama. Pengguna mengonfirmasi dengan
remote fisik bahwa panel tahan-Home tetap terbuka setelah perbaikan timing.
Tombol Hapus diuji terhadap notifikasi aktif. Home singkat fisik, tombol Buka,
siklus reboot, dan pemakaian jangka panjang belum diuji dalam sesi ini.
