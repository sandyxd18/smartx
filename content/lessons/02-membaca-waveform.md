---
title: Membaca waveform untuk debugging
step: 2
order: 30
---

# Membaca waveform untuk debugging

Pesan gagal memberi tahu **bahwa** ada yang salah. Waveform menunjukkan **mengapa**: nilai setiap sinyal di setiap saat.

## Dari pesan gagal ke waktu

Semua template di SmartX memakai clock 10 ns, dan input diubah di sisi turun. Pesan seperti `siklus 7: dout = 3, seharusnya 2` berarti sekitar 70 ns setelah reset selesai. Di tab **Waveform**, waktu ditampilkan dalam ps atau ns di bagian atas.

## Langkah di Surfer

1. Jalankan **Simulasi**, lalu buka tab **Waveform**. File `.fst` dari run itu dimuat otomatis. Run lama juga bisa dibuka lewat tab **Riwayat**.
2. Di panel **Scopes**, klik modul top-mu. Di simulasi Verilator ada juga scope `$rootio` berisi port top-level.
3. Di panel **Variables**, klik sinyal yang mau dilihat, atau tekan **+** untuk menambahkan semuanya.
4. Perbesar dengan Ctrl+scroll dan geser waktu dengan scroll horizontal. Daftar tombolnya tampil di layar awal Surfer.

Kalau viewer tidak terbuka, pakai tautan **Unduh .fst** dan buka file-nya di GTKWave atau Surfer versi desktop.

## Apa yang dicari

Mulai dari sinyal yang salah, lalu mundur ke penyebabnya:

- **Keluaran salah di siklus N:** lihat input dan register yang menentukannya di sisi naik **sebelum** siklus N.
- **Nilai X (tidak diketahui):** di Icarus, X biasanya berasal dari register tanpa reset, input yang belum pernah diberi nilai, atau dua driver yang berebut. Telusuri X itu ke belakang sampai ke sumbernya.
- **Handshake valid/ready:** data berpindah tepat di sisi naik saat `valid` dan `ready` sama-sama 1. Kalau data hilang, cari sisi naik di mana DUT mengganti data padahal `ready` penerima masih 0.
- **Satu siklus terlambat atau terlalu cepat:** bandingkan kapan input berubah dan kapan keluaran merespons. Register menambah satu siklus; logika kombinasional tidak.

## Gunakan perbandingan run

Setelah memperbaiki bug, buka tab **Riwayat**, centang run sebelum dan sesudah perbaikan, lalu klik **Bandingkan**. Kamu langsung melihat test mana yang diperbaiki, dan apakah ada test lain yang ikut rusak.
