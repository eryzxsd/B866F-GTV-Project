# Kartu notifikasi di pojok kanan atas

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

Footer menampilkan **Notifikasi dari [nama aplikasi]**. Versi 0.3 menghapus
handler tahan-Home dan panel detail eksperimen. Tidak ada accessibility service
atau intersepsi tombol dalam APK ini. Eksperimen 0.2 memicu regresi navigasi pada
firmware uji; pengguna mengonfirmasi navigasi pulih setelah handler dinonaktifkan.
Kartu popup biasa tetap aktif. Tidak semua aplikasi mengirim notifikasi yang
memenuhi filter, dan kartu ini tidak menyisipkan data ke panel internal Google TV.

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

Uji notifikasi berlabel jelas; pesan contoh berakhir setelah 10 detik:

```sh
adb shell am start -n com.local.b866f.notificationcards/.PreviewActivity
adb shell am start -n com.local.b866f.notificationcards/.PreviewActivity --es mode cleanup
```

Android mengikat listener sesuai pengaturan akses notifikasi; tidak memerlukan
service root atau perubahan service boot Magisk. Siklus reboot belum diuji.

## Menonaktifkan atau menghapus

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
Fokus window sebelum dan selama kartu tetap sama. Belum ada pengukuran daya atau
pengujian jangka panjang.
