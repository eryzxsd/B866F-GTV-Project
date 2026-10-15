# Pemulihan

## Android masih dapat dibuka

Matikan Samba dari menunya. Pilih launcher lama dari **Ganti launcher** sebelum mematikan helpernya. Ini memberi kesempatan alat mengaktifkan kembali komponen HOME yang sebelumnya dinonaktifkannya.

Nonaktifkan modul dari aplikasi Magisk, lalu reboot. Jika ADB root masih bekerja, marker berikut menghentikan aktivasi modul pada boot berikut:

`adb -s SERIAL shell su -c 'touch /data/adb/modules/ebs_gtv_system_app/disable'`

Menonaktifkan modul tidak otomatis menghapus APK profil atau mengembalikan komponen launcher yang pernah dinonaktifkan. Catatannya ada di direktori modul pada `launcher-managed-components.json` (lihat konstanta path di source jika versi berubah). Jangan hapus data modul sebelum memulihkan launcher.

Jika perlu, daftarkan ulang launcher HOME dengan `cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME`, aktifkan komponen launcher lama yang tercatat menggunakan `pm enable --user 0 PAKET/KOMPONEN`, lalu pilih HOME lama. Jangan menebak komponen atau menonaktifkan Settings.

## Android tidak dapat boot

Gunakan recovery yang sudah diuji untuk membuat marker `disable` pada modul di `/data/adb/modules/ebs_gtv_system_app/`, atau jalur pemulihan resmi perangkat. Wireless ADB bukan recovery saat Android belum hidup. Repo ini tidak memberikan prosedur flash universal atau image boot pengganti.
