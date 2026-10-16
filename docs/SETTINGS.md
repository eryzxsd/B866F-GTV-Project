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

## Perbaikan layout daftar pilihan, versi 21

Pemeriksaan lanjutan pada **Status lokasi** menemukan kasus yang terlewat pada
review empat halaman sebelumnya: kotak judul berelevasi menyentuh baris radio
pertama. Kedua layout fragment preference kini memakai judul transparan tanpa
elevasi. Grid daftar pilihan mendapat padding atas/bawah 12dp dan tinggi sesuai
sisa ruang di bawah judul.

Pada menu yang dilaporkan pengguna, jarak terukur antara batas judul dan baris
fokus berubah dari 0 menjadi 21 piksel. Menu pilihan Bluetooth dengan judul dua
baris juga diperiksa. Navigasi fokus dan Back bekerja; nilai lokasi tetap 3 dan
pilihan radio tidak diubah. Halaman Aksesibilitas tetap dapat dibuka dan
perubahan Text-to-speech versi 20 dipertahankan.

Rincian ada di [hasil layout daftar pilihan](settings-list-layout-result.json).
Ini perbaikan layout bersama, bukan klaim bahwa seluruh submenu telah diperiksa.

## Judul tetap terbaca saat menggulir, versi 22

Header transparan versi 21 memperlihatkan baris yang sudah digulir keluar area
daftar di belakang tulisan **Setelan**. Koreksi ini memakai background header
opaque yang sama dengan halaman. Elevasi 1dp menempatkannya di atas baris, dengan
`outlineProvider="none"` agar tidak menampilkan bayangan kotak.

Kedua layout header bersama diperbarui. Reproduksi pada menu utama yang digulir
ke Preferensi Perangkat menunjukkan judul terbaca dan baris Akun & Profil tidak
lagi terlihat di belakangnya. Dua siklus gulir selesai tanpa restart proses.
Gap 21 piksel pada daftar Status lokasi tetap terjaga; nilai lokasi tidak berubah.
Hasil ada di [catatan header saat scroll](settings-header-scroll-result.json).
