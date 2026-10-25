---
title: Membaca laporan timing
step: 3
order: 40
---

# Membaca laporan timing

Simulasi tidak mengenal waktu tunda: begitu sisi clock datang, semua logika langsung punya hasil. Di FPGA, setiap LUT dan setiap kabel butuh waktu. Hasil dari satu flip-flop harus sampai ke flip-flop berikutnya **sebelum** sisi clock berikutnya. Tahap Place & Route (nextpnr) menghitung waktu ini untuk setiap jalur, dan tab **FPGA** menampilkan ringkasannya.

Angka di bawah berasal dari blinky di Tang Nano 9K yang dibangun di SmartX (nextpnr 0.11.1-79).

## Fmax dan target

| Clock | Fmax | Target | Status |
|---|---|---|---|
| clk | 159,08 MHz | 27 MHz | Tercapai |

- **Target** adalah frekuensi clock yang Anda janjikan: `freq_mhz` di `smartx.yaml`, atau clock board (27 MHz) kalau kosong. Nilainya harus sama dengan clock yang benar-benar masuk ke pin.
- **Fmax** adalah frekuensi tertinggi yang masih aman untuk desain hasil place & route ini. Nilainya dihitung dari jalur paling lambat.

Selama Fmax ≥ target, desain aman. Blinky punya sisa hampir enam kali lipat. Kalau target dinaikkan ke 300 MHz, baris itu menjadi merah dengan status **Gagal**. Bitstream tetap dibuat, tetapi di board hasilnya bisa salah: flip-flop menangkap nilai yang belum selesai dihitung.

Log nextpnr mencetak Fmax dua kali. Angka pertama adalah perkiraan sebelum routing (blinky: 209,42 MHz), dan yang dipakai adalah angka **terakhir** (159,08 MHz). SmartX mengambil angka akhir itu dari `report.json`.

## Jalur kritis

Jalur kritis adalah jalur paling lambat, yang menentukan Fmax: `Fmax = 1 / delay jalur kritis`. Untuk blinky:

```
Jalur kritis posedge clk → posedge clk: 6,29 ns (3,70 ns logika, 2,59 ns routing)
```

1000 / 6,29 ns ≈ 159 MHz, sama dengan Fmax di tabel. Tabel langkahnya dibaca dari atas ke bawah:

| Jenis | Artinya |
|---|---|
| `clk-to-q` | waktu flip-flop awal mengeluarkan nilai setelah sisi clock |
| `routing` | waktu sinyal berjalan di kabel antar-blok; kolom Net menunjukkan nama sinyalnya |
| `logic` | waktu melewati satu LUT, ALU, atau MUX |
| `setup` | waktu yang dibutuhkan flip-flop tujuan sebelum sisi clock berikutnya |

Kolom **Sumber** menunjuk baris di kode Anda kalau net itu berasal dari kode Anda. Klik untuk membuka file di baris itu. Di blinky, jalur kritis berawal dari `count[24]` (baris deklarasi `count`) dan melewati pembanding `count == 13_499_999`: membandingkan 25 bit butuh beberapa lapis LUT. Net dengan nama panjang seperti `state_DFFRE_Q_CE_MUX2_LUT5_O_S0` dibuat Yosys sendiri saat memetakan logika, jadi tidak punya baris di kode Anda.

## Kalau timing gagal

Lihat perbandingan logika dan routing di jalur kritis, lalu coba salah satu cara ini:

1. **Kurangi logika di antara dua flip-flop.** Rantai panjang seperti pembanding lebar, penjumlahan berantai, atau mux bertingkat bisa dipecah dengan menyisipkan register di tengah (*pipelining*). Hasilnya terlambat satu siklus, tetapi tiap tahap jadi pendek.
2. **Hindari operasi mahal dalam satu siklus.** Pembagian umum, misalnya, sebaiknya dikerjakan beberapa siklus.
3. **Turunkan target.** Kalau desain memang tidak perlu cepat, clock lebih lambat (misalnya dari PLL) adalah solusi yang sah, asalkan target di `smartx.yaml` sama dengan clock sebenarnya.

Satu catatan: jalur dari pin input yang asinkron tidak masuk analisis ini. "Tercapai" tidak menjamin tombol atau UART aman; untuk itu pakai synchronizer.

## Tabel resource

Di samping timing ada tabel **Resource**: LUT, FF (flip-flop), BRAM, dan IO yang dipakai dibandingkan kapasitas chip. Blinky hanya memakai 43 dari 8640 LUT. Angka yang tiba-tiba melonjak, misalnya ratusan ALU untuk satu baris kode, biasanya menunjukkan operasi mahal seperti pembagi.
