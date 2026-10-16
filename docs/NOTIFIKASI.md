# Panel notifikasi Google TV

Untuk popup aplikasi di pojok kanan atas, lihat [KARTU-NOTIFIKASI.md](KARTU-NOTIFIKASI.md).
Pengalihan panel pada halaman ini tidak mengaktifkan semua popup aplikasi.

Launcher Google TV 1.0.994451607 yang diuji sudah memiliki dashboard dan kartu
notifikasi asli. Pada basis B866F Android 14 ini, resource framework
`android:string/config_notificationHandlerPackage` diarahkan overlay bawaan
ke `com.google.android.tvrecommendations`. Itu membuka panel Android TV lama.

Helper `module/bin/gtv-notification-panel` memakai fabricated resource overlay
untuk mengarahkan resource tersebut ke `com.google.android.apps.tv.launcherx`.
Helper memeriksa bahwa intent OPEN_NOTIFICATION_HANDLER_PANEL benar-benar
di-resolve ke DashboardHandler sebelum mengubah routing, lalu membaca ulang
resource setelah enable. System UI dan APK Google tidak diganti. Tidak ada
service tambahan yang terus berjalan atau akses notifikasi baru yang diberikan.

System UI menyimpan resource ini saat startup. Opsi `--refresh` mengirim TERM
hanya ke proses `com.android.systemui` ketika nilai routing berubah; Android
memulai ulang UI tersebut. Ini dapat menutup panel sementara, bukan reboot STB.
Hook service berjalan setelah Android selesai boot. Jika DashboardHandler tidak
tersedia lagi, helper menonaktifkan overlay miliknya dan memulihkan routing
firmware. Pada basis tanpa overlay fitur ini, resource tidak berubah.

Contoh dari root shell, pada instalasi modul yang sesuai:

```sh
MODDIR=/data/adb/modules/ebs_gtv_system_app
"$MODDIR/bin/gtv-notification-panel" status
"$MODDIR/bin/gtv-notification-panel" apply --refresh
```

Untuk mengembalikan panel firmware sekaligus menonaktifkan penerapan saat boot:

```sh
MODDIR=/data/adb/modules/ebs_gtv_system_app
touch "$MODDIR/disable_gtv_notifications"
"$MODDIR/bin/gtv-notification-panel" restore --refresh
```

Untuk mengaktifkan kembali, hapus hanya flag `disable_gtv_notifications`, lalu
jalankan `apply --refresh`. Restore menonaktifkan overlay milik fitur ini saja;
nilai dasar dan overlay bawaan firmware tetap tersedia. Tidak perlu wipe atau
flash. Pengaturan notification-listener yang sudah ada tidak disentuh.

Perubahan ini mengalihkan panel notifikasi sistem dan menggunakan tampilan yang
disediakan launcher. Bentuk kartu, detail, dan tombol tetap mengikuti versi
Google TV yang terpasang. Popup/toast singkat dan UI khusus di dalam aplikasi
tidak diubah. Tidak mengubah kernel, patch keamanan, audio, atau DRM.

## Verifikasi pada perangkat

Pada B866F Android 14 dengan launcher versi di atas, command sistem
`cmd statusbar expand-notifications` membuka DashboardHandler Google TV setelah
refresh System UI. Kartu USB dan debugging nirkabel tampil, navigasi D-pad
menyorot kartu, dan menu Semua notifikasi membuka daftar tiga notifikasi dalam
bahasa Indonesia. Restore diuji: command yang sama kembali membuka
NotificationsSidePanelHandler milik tvrecommendations. Apply berikutnya kembali
ke Google TV. Pemanggilan apply tanpa perubahan tidak perlu refresh lagi.

Hook startup sudah dipasang dan diperiksa sintaksnya, tetapi persistensi setelah
reboot belum diuji; tidak dilakukan reboot untuk perubahan ini. Sebelum
menonaktifkan seluruh modul, jalankan restore di atas agar fabricated overlay
tidak tertinggal aktif secara terpisah dari modul.
