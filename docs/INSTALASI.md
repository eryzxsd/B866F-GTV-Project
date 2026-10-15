# Instalasi bertahap

Rilis ini untuk pengembang yang dapat memakai ADB, Magisk, dan memulihkan firmware sendiri. Belum ada pengujian instalasi bersih pada STB kedua. Jangan menganggap kesamaan nama B866F cukup untuk menjamin cocok.

## Sebelum instalasi

- Cocokkan model, fingerprint, dan hash Settings melalui `tools/preflight.py`.
- Simpan cadangan boot/vendor dan firmware asli secara privat. Cadangan bukan pengganti recovery yang dapat dipakai saat Android tidak boot.
- Pastikan jalur recovery/USB telah diuji. Wireless ADB saja mungkin hilang jika boot gagal.
- Pertahankan launcher bawaan dan jangan menghapus aplikasi sistem.
- Siapkan APK Google TV asli dan sah secara lokal. Baseline sistem yang diuji adalah 1.0.331643392; versi 1.0.994451607 dipasang sebagai update aplikasi pengguna. Repo tidak menyediakan keduanya.

## Urutan yang digunakan

1. Build APK pendamping, layanan profil, dan overlay. Pasang APK pendamping dan profil dengan `adb -s SERIAL install -r BERKAS.apk`.
2. Buka APK pendamping sekali untuk membuat direktori preferensi sebelum helper root dijalankan:

   `adb -s SERIAL shell am start -n com.local.b866f.launcherpicker/.LauncherPickerActivity`

   `adb -s SERIAL shell am start -n com.local.b866f.launcherpicker/.SambaSettingsActivity`

3. Rakit modul lokal sesuai BUILD.md. Pasang modul dari aplikasi Magisk hanya setelah pemeriksaan basis dan recovery selesai. Modul menggunakan ID `ebs_gtv_system_app`; jika sudah ada modul dengan ID itu, ini adalah penggantian/upgrade, bukan modul kedua.
4. Sesudah reboot, periksa launcher lama masih dapat dibuka. Pasang update Google TV asli dengan ADB. Jika berupa split APK, seluruh split yang sesuai harus dipasang bersama dengan `adb install-multiple`.
5. Buka Google TV sebagai preview: `adb -s SERIAL shell am start -n com.google.android.apps.tv.launcherx/.home.HomeActivity`. Pastikan remote, artwork, dan aplikasi berfungsi sebelum memilihnya sebagai HOME dari **Ganti launcher**.
6. Uji Settings, screensaver, dan Samba secara terpisah. Server Samba tetap mati sampai diaktifkan secara eksplisit.

Jangan mengaktifkan ulang helper artwork lama pada launcher terbaru. Paket publik tidak menyertakannya. Bootlogo dan bootanimation tidak diubah oleh paket publik ini.

Jika signature APK pendamping berbeda dari instalasi lama, `install -r` akan gagal. Jangan menghapus APK lama tanpa mempertimbangkan data dan catatan pemulihannya. Gunakan key build yang sama untuk upgrade.

Perubahan modul publik dari setup pengujian: tidak menyertakan APK Google atau bootanimation; tidak menyertakan helper artwork versi lama. Paket lokal memerlukan baseline APK Google dari pengguna. Karena itu paket publik adalah developer preview, bukan salinan ROM STB pengujian.
