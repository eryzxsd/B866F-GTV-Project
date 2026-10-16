# Pemeriksaan konsistensi Settings

Overlay versi 20 mengubah entri **Text to speech** di Aksesibilitas agar membuka
`TextToSpeechActivity` saat dipilih. Entri ini tidak lagi membuat preview
`TextToSpeechFragment` hanya karena mendapat fokus remote.

Dua laporan ANR memperlihatkan thread UI menunggu lock di
`TextToSpeech.shutdown()` ketika fragment preview ditutup. Worker inisialisasi
memegang lock tersebut sambil menunggu jawaban Binder
`getDefaultVoiceNameFor`. Menghindari preview otomatis memutus pemicu saat
pengguna sekadar menggulir menu. Ini mitigasi navigasi; implementasi engine
Google TTS dan metode shutdown framework tidak diubah.

Pada satu B866F dengan APK Settings yang hash-nya dipatok, dua putaran gulir
penuh turun/naik selesai tanpa restart proses. Memilih Text to speech tetap
membuka halaman aslinya, dan Back kembali ke Aksesibilitas. Key, kategori,
layanan pembaca layar, dan pengaturan aksesibilitas lainnya dipertahankan.
Nilai toggle tidak diubah selama pengujian.

Review visual terbatas mencakup Aksesibilitas, Jaringan, Aplikasi, dan Opsi
developer. Pada layar yang diperiksa, teks fokus terbaca, thumb sakelar terlihat,
ikon aplikasi mempertahankan warna aslinya, dan tidak ditemukan tabrakan judul
dengan baris. Warna sakelar OEM unlock yang tidak bisa diubah mengikuti keadaan
disabled. Hasil ini bukan pemeriksaan seluruh submenu atau seluruh kondisi tema.

Catatan terukur ada di [hasil pengujian](settings-accessibility-result.json).
APK dan laporan ANR lengkap tetap privat. Tidak ada modifikasi APK Settings
dasar, reboot STB, atau kelanjutan eksperimen kernel dalam perubahan ini.

Untuk mematikan overlay penampilan jika diperlukan, gunakan shell ADB:

```sh
cmd overlay disable --user 0 com.local.ebs.settingstheme
```

Ini mengembalikan resource tampilan dari overlay tersebut ke basisnya. Untuk
menyalakannya kembali, gunakan `cmd overlay enable --user 0` dengan nama paket
yang sama. Build source mengikuti [panduan build](BUILD.md).
