# Audit patch keamanan Android

> **ARSIP — DIHENTIKAN pada 17 Oktober 2026.** Upaya upgrade kernel dan patch
> keamanan penuh telah berakhir. Isi folder ini dipertahankan sebagai catatan
> eksperimen historis, bukan pengembangan aktif, roadmap, atau paket siap pasang.
> Petunjuk dan status menunggu di bawah merupakan konteks saat eksperimen dibuat.
> Fokus aktif proyek adalah kustomisasi Google TV.

Tujuan eksperimen terdahulu adalah pembaruan nyata, bukan mengganti teks tanggal pada Settings.
Hasil uji kernel dan ABI tidak membuktikan seluruh patch platform terpasang.

## Temuan adbd Mei 2026

[Bulletin AOSP Mei 2026](https://source.android.com/docs/security/bulletin/2026/2026-05-01)
mencantumkan CVE-2026-0073 pada adbd, termasuk Android 14. Patch level juga
mencakup perbaikan bulletin sebelumnya. [Perbaikan source resmi](https://android.googlesource.com/platform/packages/modules/adb/+/842d331f9e5fb10770a09379e19240daea057dba)
membatasi hasil perbandingan public key yang diterima menjadi nilai 1 saja.
Ini perubahan userspace Android, bukan perubahan kernel Linux.

Pemeriksaan read-only pada binary STB yang hash-nya dicatat dalam
`adbd-may2026-audit.json` menemukan callback verifikasi TLS masih menerima hasil
nonzero. Decompilation Ghidra pada fungsi tersebut diperiksa silang dengan
disassembly LLVM dan relocation import EVP_PKEY_cmp. Jadi perbaikan resmi tidak
ada pada callsite yang diidentifikasi. Tidak dilakukan exploit atau perubahan
daemon/APEX, dan tidak diklaim bahwa seluruh jalur runtime telah diuji.

Autoanalysis Ghidra global berhenti pada batas 180 detik; decompilation caller
yang relevan selesai dan bukti instruksi diperiksa terpisah. REA Windows tidak
mendukung ELF ini melalui provider native-nya, sehingga dipakai Ghidra headless
yang sudah terpasang dan LLVM biasa. Hasil ini bukan klaim REA Evidence.

Script `tools/InspectAdbd.java` dapat dipakai pada salinan lokal dengan Ghidra
headless untuk mereproduksi inspeksi caller. Output lengkap dan binary tetap
privat. Contoh argumen Ghidra (ganti placeholder dengan path lokal):

```text
analyzeHeadless PROJECT_DIR AUDIT_NAME -import LOCAL_ADBD -readOnly -deleteProject -analysisTimeoutPerFile 180 -scriptPath tools -postScript InspectAdbd.java PRIVATE_REPORT
```

### Backport source Android 14 dan uji kontrak crypto

Backport khusus source disiapkan untuk `daemon/auth.cpp` AOSP pada commit
`0c88a54d6300ddc98f27bfc3ade96190b53b7c86`. Patch ada di
`patches/adbd-android14-CVE-2026-0073.patch`; perubahan hanya menambahkan syarat
`== 1`, mempertahankan logging Android 14 yang ada. Tool menolak hash input
yang berbeda dan output yang sudah ada. Source asli tidak ditimpa.
`adbd-source-backport-result.json` mencatat hash dan pengujian guard tersebut.

```text
python tools/prepare_adbd_backport.py --source LOCAL_AOSP_AUTH_CPP --output NEW_SOURCE_DIRECTORY
python tools/adbd_compare_host.py --original LOCAL_AOSP_AUTH_CPP --backported NEW_SOURCE_DIRECTORY/daemon/auth.cpp --output NEW_HOST_REPORT
```

Input diambil dari [source AOSP yang dipatok](https://android.googlesource.com/platform/packages/modules/adb/+/0c88a54d6300ddc98f27bfc3ade96190b53b7c86/daemon/auth.cpp).
Uji host memerlukan Linux, g++, dan development library libcrypto. Ekspresi
guard diambil dari dua source yang hash-nya diverifikasi, kemudian dikompilasi
dan dijalankan dengan key RSA/Ed25519 nyata yang hanya berada di memori.
Hasil pada `adbd-host-comparison-result.json`:

| Perbandingan | Hasil API | Kondisi lama menerima | Backport menerima |
|---|---:|---|---|
| Key yang sama | 1 | Ya | Ya |
| Key RSA berbeda | 0 | Tidak | Tidak |
| Jenis key berbeda | -1 | Ya | Tidak |

Ini memakai OpenSSL host, bukan runtime BoringSSL Android. Review terpisah
pada header dan implementasi BoringSSL Android 14 yang dipatok juga menemukan
kontrak hasil negatif sebagai error, termasuk `-1` untuk jenis berbeda dan `-2`
untuk perbandingan yang tidak didukung. Library BoringSSL dari perangkat belum
dicocokkan atau diuji runtime. Percobaan awal dengan object key kosong yang
sama tidak memenuhi asumsi error pada OpenSSL host; hasil tersebut disimpan
privat dan tidak dihitung sebagai pengujian error `-2`.

Uji tambahan pada `adbd-boringssl-host-result.json` memakai **BoringSSL AOSP
yang dipatok dan dibangun untuk Linux host**, bukan OpenSSL sistem. Tiga kelas
key yang sama juga lolos: hasil `1` diterima, `0` dan `-1` ditolak backport.
Hash archive host dicatat. Ini tetap pengujian ekspresi guard, bukan daemon
atau runtime Android ARM. Untuk mengulang dengan checkout build lokal yang
sudah menghasilkan archive host BoringSSL:

```text
python tools/adbd_compare_host.py --original LOCAL_AOSP_AUTH_CPP --backported NEW_SOURCE_DIRECTORY/daemon/auth.cpp --output NEW_HOST_REPORT --android-build LOCAL_ANDROID_TREE
```

### Persyaratan build dan paket

`adbd-build-packaging-review.json` mencatat ABI dari salinan daemon asli yang
sudah ada: **ARM32 ELF**, interpreter `/system/bin/linker`, serta dependency
`libadbd_auth.so`, `libadbd_fs.so`, dan library Android lain. Kernel ARM64 tidak
berarti daemon penggantinya boleh langsung berupa binary Linux ARM64.
Target source yang relevan ialah Soong `adbd` dan APEX `com.android.adbd` di
source tree Android 14 dengan dependency/API yang kompatibel. **Binary daemon
ARM32 dengan backport kini berhasil dibangun dan diperiksa secara offline.**
APEX belum dibangun dan daemon belum dijalankan pada Android atau STB.
Uji host di atas tetap terpisah dari hasil build daemon.

Untuk update APEX normal, [AOSP mensyaratkan verifikasi signature payload dan
container](https://source.android.com/docs/core/ota/apex#signing-options).
Identitas signer yang diterima firmware ini belum diketahui dan material
signing kompatibel belum diverifikasi tersedia. Memperbesar version code atau
memakai key pengembangan sendiri tidak membuktikan paket akan diterima.
Tidak ada perubahan signature enforcement, penggantian daemon, atau instalasi
APEX yang dilakukan dalam pekerjaan ini.

### Checkout eksperimen build modul

Checkout terpisah kini disiapkan untuk build modul Android 14. Manifest
`adbd-build-seed-manifest.xml` mencatat commit proyek yang dipatok serta link
root sesuai manifest AOSP. Subset berisi **52 proyek** dan berhasil menghasilkan
target binary `adbd` dengan source view serta konfigurasi di bawah. Ini bukan
manifest firmware EBS atau source tree Android lengkap.
Backport source diterapkan setelah hash awal `daemon/auth.cpp` cocok.

Source view juga memakai Git sparse-checkout pada proyek `development`, hanya
direktori `sdk` yang menyediakan genrule versi platform-tools. Sample APK dari
proyek itu memerlukan SDK Java lengkap dan tidak diperlukan untuk target ini.
Pada checkout eksperimen baru yang bersih, jalankan:

```text
git -C development sparse-checkout set --cone sdk
```

Commit dan isi source SDK tetap asli; tidak dibuat file API/header pengganti.
Manifest tanpa source view ini tidak mereproduksi eksperimen yang sama.

Pemeriksaan konfigurasi Soong berhasil menghasilkan `TARGET_PRODUCT=module_arm`,
`TARGET_ARCH=arm`, `TARGET_ARCH_VARIANT=armv7-a-neon`,
`TARGET_CPU_ABI=armeabi-v7a`, dan `TARGET_BUILD_VARIANT=user`.
Pemilihan variant tersebut tidak mengaktifkan adb root atau menonaktifkan auth.
Target modul resmi dapat dipilih melalui helper `banchan com.android.adbd arm user`
pada source tree yang dependency-nya lengkap. Konfigurasi target sendiri bukan
bukti ABI/runtime atau signature APEX sudah benar.

Untuk checkout Linux baru, gunakan repo client dan dependency host build AOSP
yang sesuai. Manifest dapat dipilih melalui:

```sh
repo init -u https://github.com/eryzxsd/B866F-GTV-Project -b main -m security/adbd-build-seed-manifest.xml
repo sync -j2
git -C development sparse-checkout set --cone sdk
```

Simpan salinan source asli di luar checkout. Jalankan
`tools/prepare_adbd_backport.py` dari repo proyek dengan input source asli dan
direktori staging baru seperti contoh sebelumnya. Salin hanya hasil
`daemon/auth.cpp` yang hash-nya diverifikasi ke
`packages/modules/adb/daemon/auth.cpp` dalam checkout eksperimen. Jangan
menerapkan perubahan ini pada tree firmware yang sedang dipakai tanpa review.
Perintah build yang berhasil, dari root checkout Android:

```sh
unset ALLOW_MISSING_DEPENDENCIES
export TARGET_PRODUCT=module_arm
export TARGET_BUILD_VARIANT=user
export TARGET_BUILD_TYPE=release
export TARGET_BUILD_APPS=com.android.adbd
export OUT_DIR="$PWD/out"
export BUILD_BROKEN_DISABLE_BAZEL=1
bash build/soong/soong_ui.bash --make-mode -j1 adbd
```

Output binary berada pada
`out/target/product/module_arm/apex/com.android.adbd/bin/adbd`. Ini direktori
staging build, **bukan APEX bertanda tangan atau paket siap instalasi**. Manifest
dan perintah tersebut merekam konfigurasi eksperimen yang sudah digunakan;
checkout kedua dari nol belum diuji terpisah.

Build lokal memakai satu job. Checkout/output berada di disk Linux WSL pada D:,
terpisah dari kernel emulator yang sudah berhasil. Ruang kosong partisi Windows
tetap dipantau: angka kapasitas virtual dari `df` di dalam WSL tidak membuktikan
ruang fisik D: tersedia. Tidak diunduh seluruh 1.224 proyek manifest Android 14.

Percobaan build awal menemukan dependency Go untuk build system yang belum
ada (`go-cmp` dan SPDX tools); kedua proyek kemudian ditambahkan dari AOSP.
Wrapper shell percobaan awal mengaburkan exit code. Wrapper Python berikutnya
mencatat return code proses secara langsung dan memeriksa pesan kegagalan;
percobaan yang gagal tidak dihitung sukses. Tidak ada module/library palsu atau perubahan signature enforcement untuk
melewati dependency yang hilang. Status eksperimen dan tahap terakhir dicatat
pada `adbd-module-bootstrap-result.json`. Build terakhir selesai dengan exit code
0, 2.395 action Ninja, dan 59 stamp paket pengujian build tool. Jumlah action
bukan jumlah tes daemon. Waktu 714 detik adalah percobaan terakhir dengan cache
dari tahap sebelumnya, bukan waktu total setup atau clean build.

Mode unbundled AOSP sendiri mengaktifkan `Allow_missing_dependencies` pada
konfigurasi Soong. Ini mengizinkan graph subset dianalisis; dependency target
tetap diperiksa Ninja. Percobaan awal berhenti pada target `adbd` saat
`libunwind`, `libclang_rt.builtins`, dan `libclang_rt.ubsan_minimal` belum ada.
Prebuilt compiler dan dependency asli kemudian ditambahkan, dan target binary
berhasil link. Flag tersebut sendiri tidak membuktikan dependency lengkap.
Percobaan discovery
dengan override environment juga tidak menghasilkan daemon dan tidak digunakan
sebagai hasil validasi. Fallback Soong resmi `BUILD_BROKEN_DISABLE_BAZEL=1`
dipakai untuk menghindari kebutuhan mixed build Bazel dalam eksperimen ini.

Baseline source masih memakai build ID Android 14 `UP1A.231105.003` dengan
backport spesifik di atas. Ini baseline eksperimen build/ABI, bukan kandidat
rilis keamanan yang telah diaudit terhadap seluruh perubahan sejak 2023.

`adbd-system-api-baseline.json` mencocokkan sembilan import `LIBADBD_AUTH` dan
satu import `LIBADBD_FS` dari consumer asli dengan symbol map source yang
dipatok. `adbd_auth_prompt_user_with_id` berstatus WEAK pada consumer asli;
keberadaan import opsional tidak membuktikan provider perangkat mengekspornya.
Binary kandidat kini dibandingkan dengan consumer asli: sepuluh import tersebut
cocok dalam nama, versi dan binding, termasuk simbol WEAK. Sepuluh nama library
dinamis juga sama. Namun seluruh import dinamis tidak identik: ada empat import
libc/libm tambahan dan sebelas helper ARM lama yang tidak lagi diimpor. Rincian
tercatat pada hasil build. Export provider perangkat belum diperiksa, sehingga
kecocokan sebagian ini belum membuktikan ABI atau runtime kompatibel.

Binary yang dibangun berukuran 1.800.012 byte, ELF32 ARM PIE, interpreter
`/system/bin/linker`, SHA-256
`a59c42a5cfd108bb33a1cc50ef5ca75bec98ac5043516e5655e51dee4b127d16`.
Disassembly LLVM, byte executable, serta relocation PLT/GOT mengonfirmasi
callback hasil build memanggil `EVP_PKEY_cmp` lalu membandingkan hasilnya dengan
`1` sebelum masuk jalur key cocok. Ini inspeksi kode statis; koneksi TLS daemon
Android belum diuji. Binary dan log lengkap tetap lokal dan tidak dibagikan.

Perbaikan adbd saja juga belum cukup untuk menyatakan seluruh perangkat berada
pada patch level Mei 2026. Framework, System, Mainline, kernel, serta komponen
vendor yang berlaku perlu diperiksa dan diperbarui. Driver asli yang lolos load
test tetap merupakan versi lama; keberhasilan load tidak memperbaiki bug di
dalamnya. Belum ada paket platform kompatibel dan jalur restore mandiri yang
terbukti, sehingga tanggal patch tidak diubah dan tidak ada instalasi firmware.

## Inventaris persyaratan dan review kernel kandidat

`bulletin-requirements-summary.json` merangkum 13 bulletin resmi Mei 2025 hingga
Mei 2026. Parser menemukan 410 baris referensi, termasuk 157 baris platform yang
mencantumkan Android 14. Angka ini bukan jumlah patch yang sudah dipasang dan
bukan jumlah CVE unik. Oktober 2025 tidak memuat tabel CVE pada halaman yang
diambil dan tidak secara eksplisit menyatakan tanpa patch: statusnya tetap
memerlukan review, tidak dihitung sebagai bukti bersih.

`kernel-candidate-review.json` meninjau 26 CVE unik pada baris kernel tersebut
terhadap source kandidat CoreELEC yang dipatok dan konfigurasi emulator yang
sudah dibangun. Pemeriksaan mencakup 88 diff commit resmi. Reverse dry-run
memakai fuzz nol; kegagalan pencocokan tidak otomatis berarti patch hilang.
Beberapa fix sudah hadir dengan konteks berbeda. Untuk TLS, F2FS, MTE dan
virtualisasi, status konfigurasi dicatat terpisah dari keberadaan patch source.
Hasil tidak diterapkan pada kernel asli yang masih berjalan di STB.

Contoh penting: fix epoll CVE-2025-38349 menargetkan model reference-count baru.
Source kandidat masih memakai model `epmutex` sebelumnya. Pemeriksaan silang
dengan [catatan Linux CNA](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2025/38xxx/CVE-2025-38349.json)
dan [commit pengenal perubahan](https://github.com/gregkh/linux/commit/f2451def095c1743adcfcb0cb5dadc86034e162a)
menghindari penambahan refactor yang tidak diperlukan hanya agar diff cocok.
Ini kesimpulan source yang terbatas, bukan sertifikasi seluruh implementasi.

Alat yang dapat diulang, dengan input/cache lokal milik pengembang:

```text
python tools/security_bulletin_inventory.py --cache PRIVATE_CACHE --output PRIVATE_INVENTORY
python tools/kernel_patch_match.py --source LOCAL_KERNEL --patch OFFICIAL_FIX --output PRIVATE_REPORT
```

`kernel_patch_match.py` hanya menjalankan dry-run; tidak menerapkan atau
membalik patch source. Simpan halaman lengkap dan diagnostik privat. Inventaris
tidak memindai perangkat atau mengubah tanggal patch.

## Uji API socket pada Image yang sama

`kernel/trust/socket-api-result.json` mencatat 21 pemeriksaan API normal:
stream/EOF Unix socket, pengiriman descriptor SCM_RIGHTS dan penggunaannya,
urgent data dengan peek/consume, event epoll, serta alokasi port vsock.
Semuanya selesai dengan shutdown QEMU bersih. Percobaan pertama gagal compile
karena urutan include header; percobaan kedua memperlihatkan batas urgent-data
yang perlu dikonsumsi sebelum pembacaan normal. Harness diperbaiki tanpa
mengubah kernel, dan hasil sukses tetap memakai hash Image yang sama.

```text
python tools/kernel_socket_probe.py --existing-build LOCAL_VERIFIED_BUILD
```

Tes ini bukan exploit, bukan pengujian CVE lengkap, dan tidak memuat Android,
Netflix atau hardware STB. Tidak ada driver yang dimuat pada eksperimen socket.

## Batas pekerjaan saat ini

Eksplorasi integrasi upstream 5.15.196 ke 5.15.207 disimpan terpisah secara lokal.
Tahap 197 sudah diintegrasikan; tahap 198 masih memiliki 14 file dengan konflik
API Android/vendor. Cabang parsial ini belum dibangun, belum diuji, belum
dipublikasikan sebagai patch kernel, dan tidak dipakai untuk hasil QEMU di atas.
Versi upstream yang lebih tinggi sendiri tidak membuktikan cakupan bulletin.

Pekerjaan instalasi masih membutuhkan dua hal yang belum tersedia: basis
platform/vendor kompatibel atau source yang memungkinkan fix Android diterapkan
dan divalidasi, serta jalur restore mandiri yang benar-benar bekerja ketika
Android gagal boot. Backup dan menu recovery saja belum membuktikan restore.
Hasil emulator tidak dapat menggantikan kedua kebutuhan itu. Tidak ada paket
Mei 2026 siap pasang atau jaminan kompatibilitas Netflix dari hasil ini.
