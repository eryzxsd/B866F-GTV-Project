# Build dari source

Dependensi: Python 3.12+, Git, JDK 17, Android SDK Platform 34 dan Build Tools 34.0.0+, Go 1.24+ (diuji Go 1.27.2), Zig 0.11.0. Python perlu dukungan kompresi yang digunakan paket .deb Termux. Toolchain dari sumber resmi tidak disertakan dalam repo.

Perintah dijalankan dari root repo. Contoh berikut memakai nama perintah di PATH; pada Windows gunakan path lengkap jika diperlukan. Skrip Python tidak memanggil shell untuk menjalankan argumen build.

## Input lokal

Simpan berkas berikut di `local-inputs/` yang diabaikan Git:

- `framework-res.apk` dari STB sendiri (`/system/framework/framework-res.apk`).
- `TvSettings.apk` dari path yang ditampilkan `adb shell pm path com.android.tv.settings`.
- Baseline Google TV Home 1.0.331643392 yang diperoleh secara sah. SHA-256: `9177852e231ae4beeb4aabd5a4359d7e76937b01e23250233cc9c4a6d241245c`.
- Keystore pribadi untuk menandatangani APK. Buat dengan `keytool -genkeypair -keystore local-inputs/release.p12 -storetype PKCS12 -alias b866f -keyalg RSA -keysize 3072 -validity 3650`. Isi kata sandi melalui prompt keytool.

Atur variabel lingkungan `B866F_KEYSTORE_PASSWORD` secara privat di terminal. Jangan menuliskannya ke skrip, issue, atau Git. Pertahankan key yang sama untuk pembaruan APK.

## APK

Jalankan untuk `tools` dan `profile-compat`:

```
python tools/build_android.py --component tools --build-tools PATH_BUILD_TOOLS --android-jar PATH_ANDROID_JAR --keystore local-inputs/release.p12
python tools/build_android.py --component profile-compat --build-tools PATH_BUILD_TOOLS --android-jar PATH_ANDROID_JAR --keystore local-inputs/release.p12
```

`PATH_BUILD_TOOLS` adalah direktori SDK build-tools/34.0.0; `PATH_ANDROID_JAR` adalah platforms/android-34/android.jar. JDK 17 harus ada di PATH. Eclipse ECJ dapat dipilih dengan `--ecj PATH_ECJ_JAR`.

```
python tools/build_android.py --component settings-overlay --build-tools PATH_BUILD_TOOLS --android-jar PATH_ANDROID_JAR --framework-apk local-inputs/framework-res.apk --settings-apk local-inputs/TvSettings.apk --keystore local-inputs/release.p12
```

ID paket overlay sengaja `0x7e`. Jangan menggantinya: referensi atribut firmware dapat salah direlokasi dan membuat Settings crash. Hash target Settings diverifikasi sebelum link overlay.

Modul juga memerlukan overlay routing notifikasi:

```
python tools/build_android.py --component notification-routing --build-tools PATH_BUILD_TOOLS --android-jar PATH_ANDROID_JAR --keystore local-inputs/release.p12
```

APK ini hanya berisi satu pemetaan resource, tanpa kode atau izin aplikasi.
Packager menempatkannya di `system/product/overlay/`; jangan memasangnya sebagai
APK pengguna biasa karena resource framework ini memerlukan kebijakan product.
Lihat [NOTIFIKASI.md](NOTIFIKASI.md) untuk aktivasi dan pemulihan.

## Helper dan Samba

```
python tools/build_native.py
python tools/fetch_runtime.py
```

Untuk toolchain di luar PATH, gunakan `--go PATH_GO` dan `--zig PATH_ZIG`. Go memverifikasi checksum dependency melalui go.sum. Fetcher memakai 41 paket ARM yang dipin di `third_party/termux/upstream-packages.json` dan menolak hash yang berbeda. Jika versi telah dihapus dari mirror, hentikan build; jangan mengganti hash tanpa meninjau paket baru dan menguji ulang.

Metadata Termux awal diverifikasi melalui signed Release dengan key fingerprint `CC72CF8BA7DBFA0182877D045A897D96E57CF20C`. Release, signature, dan public key disertakan untuk audit:

```
gpg --no-default-keyring --keyring ./third_party/termux/termux-keyring.gpg --verify third_party/termux/Release.gpg third_party/termux/Release
```

Peringatan trust lokal GPG berbeda dengan signature yang tidak valid. Sumber paket: https://packages.termux.dev/apt/termux-main/ . Resep Samba: https://github.com/termux/termux-packages/tree/master/packages/samba . Versi yang diuji: Samba 4.25.0.

Shim C hanya dimuat dalam proses Samba: mengarahkan path runtime dan memilih locking fcntl normal sebagai pengganti robust mutex. Tidak mengubah linker Android global atau menonaktifkan locking.

## Paket modul lokal

```
python tools/package_module.py --google-tv-system-apk local-inputs/GoogleTVHome-1.0.331643392.apk
```

Keluaran berada di `dist/`, yang diabaikan Git. Paket ini berisi baseline APK Google milik pengguna: jangan unggah paketnya sebagai release publik tanpa hak distribusi. Tidak ada bootanimation dalam paket publik. APK tools/profil dipasang terpisah sesuai INSTALASI.md.

Sebelum commit: `git add ...` lalu `python tools/check_publication.py`. Build tidak menyentuh STB; instalasi/reboot adalah langkah terpisah.
