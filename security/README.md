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
