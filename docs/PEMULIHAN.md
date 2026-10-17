# Pemulihan

## Android masih dapat dibuka

Langkah di bawah adalah panduan, bukan rollback otomatis. Pilih hanya fitur
yang ingin dipulihkan. Cadangkan konfigurasi dan APK hasil build yang cocok
secara privat; gunakan key yang sama jika memasang kembali APK pendamping.

Untuk blok perintah root di halaman ini, masuk dahulu dengan
`adb -s SERIAL shell`, lalu jalankan `su`. Ganti `SERIAL` dengan perangkat
yang benar. Blok berikut dijalankan di shell Android tersebut, bukan langsung
di PowerShell.

### Launcher

Matikan Samba dari menunya. Pilih launcher lama dari **Ganti launcher** sebelum mematikan helpernya. Ini memberi kesempatan alat mengaktifkan kembali komponen HOME yang sebelumnya dinonaktifkannya.

Periksa tombol Home benar-benar membuka launcher pilihan. Simpan
`launcher-managed-components.json` secara privat sebelum menghapus modul.
Layanan profil Google TV tidak perlu dihapus untuk memilih launcher lain.
Jangan hapus launcher Google atau launcher firmware sebagai langkah awal.

### Tampilan Settings

Untuk kembali ke tampilan firmware, cegah penerapan ulang lalu nonaktifkan
dua overlay tampilan yang dimiliki proyek:

```sh
MODDIR=/data/adb/modules/ebs_gtv_system_app
touch "$MODDIR/disable_twopanel" "$MODDIR/disable_settings_theme"
cmd overlay disable --user 0 com.android.shell:EbsTvSettingsTwoPanel
cmd overlay disable --user 0 com.local.ebs.settingstheme
am force-stop com.android.tv.settings
```

Overlay yang belum terpasang dapat melaporkan tidak ditemukan; jangan
menonaktifkan overlay firmware lain. Buka Settings kembali dan verifikasi.
Jika ingin mengaktifkan lagi, hapus hanya kedua flag di atas, lalu reboot saat
siap. Langkah ini memulihkan tampilan, bukan seluruh modifikasi firmware EBS.

### Panel notifikasi dan kartu popup

Untuk mengembalikan panel firmware:

```sh
MODDIR=/data/adb/modules/ebs_gtv_system_app
touch "$MODDIR/disable_gtv_notifications"
"$MODDIR/bin/gtv-notification-panel" restore --refresh
"$MODDIR/bin/gtv-notification-panel" status
```

Restore menonaktifkan overlay APK dan fabricated overlay lama milik fitur ini.
Pada basis uji, status kembali ke `com.google.android.tvrecommendations`.
Opsi refresh dapat menutup panel sementara karena System UI dimulai ulang.
Untuk mengaktifkan lagi, hapus hanya flag `disable_gtv_notifications` dan
jalankan helper dengan `apply --refresh`. Aktivasi pertama masih dapat
memerlukan refresh; pada boot selanjutnya overlay APK mempertahankan routing.

Kartu popup adalah APK terpisah. Untuk menghentikannya tanpa menghapus data:

```sh
cmd notification disallow_listener com.local.b866f.notificationcards/.CardListener 0
cmd appops set com.local.b866f.notificationcards SYSTEM_ALERT_WINDOW default
am force-stop com.local.b866f.notificationcards
```

Ini tidak mengubah panel notifikasi atau listener aplikasi lain. Lihat
[kartu notifikasi](KARTU-NOTIFIKASI.md) untuk izin pemasangan kembali.
Eksperimen filter notifikasi internal launcher pada perangkat pengembangan
bukan bagian installer publik; jangan menghapus seluruh daftar listener untuk
mencoba membatalkannya.

### Menonaktifkan seluruh modul

Pulihkan launcher dan panel notifikasi dahulu seperti di atas, lalu matikan
overlay Settings bila sudah pernah diaktifkan. Ini penting karena fabricated
overlay dapat tetap tercatat di Android walaupun modul dinonaktifkan.

Nonaktifkan modul dari aplikasi Magisk, lalu reboot. Jika ADB root masih bekerja, marker berikut menghentikan aktivasi modul pada boot berikut:

`adb -s SERIAL shell su -c 'touch /data/adb/modules/ebs_gtv_system_app/disable'`

Menonaktifkan modul tidak otomatis menghapus APK profil atau mengembalikan komponen launcher yang pernah dinonaktifkan. Catatannya ada di direktori modul pada `launcher-managed-components.json` (lihat konstanta path di source jika versi berubah). Jangan hapus data modul sebelum memulihkan launcher.

Jika perlu, daftarkan ulang launcher HOME dengan `cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME`, aktifkan komponen launcher lama yang tercatat menggunakan `pm enable --user 0 PAKET/KOMPONEN`, lalu pilih HOME lama. Jangan menebak komponen atau menonaktifkan Settings.

## Android tidak dapat boot

Gunakan recovery yang sudah diuji untuk membuat marker `disable` pada modul di `/data/adb/modules/ebs_gtv_system_app/`, atau jalur pemulihan resmi perangkat. Wireless ADB bukan recovery saat Android belum hidup. Repo ini tidak memberikan prosedur flash universal atau image boot pengganti.
