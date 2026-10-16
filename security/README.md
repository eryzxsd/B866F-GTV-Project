# Audit patch keamanan Android

Tujuan adalah pembaruan nyata, bukan mengganti teks tanggal pada Settings.
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
