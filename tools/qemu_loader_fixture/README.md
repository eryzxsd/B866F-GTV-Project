# Fixture loader QEMU

Modul ini hanya untuk initramfs emulator, bukan untuk STB. Fungsi arc4_crypt
adalah stub tanpa implementasi ARC4. Nama ekspor dipilih dari daftar protected
kernel untuk menguji enforcement; tidak ada driver atau konsumen nyata.

Workflow memeriksa nama itu pada header protected hasil generate dan memastikan
tidak dimiliki vmlinux. Modpost memakai tabel simbol kernel hasil build asli.
Tidak memakai force-load, pengabaian CRC/vermagic, atau pengubahan enforcement.

Empat salinan disiapkan di runner sementara:

- Trusted: signature SHA-256 dengan key build kernel sementara; load/unload normal.
- Unsigned: tanpa signature; ekspor protected harus ditolak dengan EACCES.
- Untrusted: signature dari key sementara terpisah yang tidak ditambahkan ke kernel;
  ekspor protected harus ditolak dengan EACCES.
- Tampered: satu byte signature trusted diubah; harus ditolak dengan EKEYREJECTED
  atau EBADMSG, sesuai kegagalan digest/padding pada rsa-pkcs1pad.c yang dipin.

Init fixture hanya boleh berjalan sekali. Serial log harus memperlihatkan dua
penolakan protected export dan marker lulus seluruh kasus. Private key, modul
hasil build, Image dan initramfs tidak diunggah; artifact hanya laporan teks.
Keberhasilan tidak membuktikan loader menerima driver asli, signature vendor,
ABI hardware, Android atau DRM.
