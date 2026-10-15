# Keamanan dan batas pengujian

Helper berjalan sebagai root melalui Magisk. Perubahan launcher membatasi target ke aktivitas HOME yang ditemukan, memverifikasi hasil, dan mencatat komponen yang diubah. Jangan memasang APK pendamping dari pihak yang tidak dipercaya: helper menganggap preferensi privat APK pendamping sebagai permintaan pengguna.

Samba memerlukan root untuk port 445, lalu menggunakan user `shell`/group `media_rw` untuk akses share. Aksesnya bukan seluruh filesystem root. Tidak ada guest, SMB1, atau akses melalui symlink. Pembatasan jaringan mengikuti interface/subnet Wi-Fi/Ethernet yang terdeteksi, bukan autentikasi identitas jaringan rumah; matikan server saat bergabung jaringan yang tidak dipercaya. Jangan port-forward 445 ke internet.

Kata sandi disimpan privat agar dapat ditampilkan di TV; ini bukan enkripsi data-at-rest. Signing wajib tidak berarti semua transfer SMB dienkripsi. Siapa pun yang dapat membuka menu kredensial pada TV dapat melihat kata sandi. Jangan gunakan ulang kata sandi akun lain.

Tidak ada pembaruan kernel atau patch keamanan Android dalam proyek ini. Basis uji tetap melaporkan 1 Mei 2025. Mode root tetap memiliki konsekuensi keamanan bawaan.

Untuk laporan publik, hapus kredensial, IP publik, MAC, serial, dan data akun. Jangan memublikasikan eksploit aktif beserta data pribadi. Gunakan GitHub private vulnerability reporting jika diaktifkan oleh pemilik repo; jika tidak tersedia, laporkan gejala umum tanpa rahasia.
