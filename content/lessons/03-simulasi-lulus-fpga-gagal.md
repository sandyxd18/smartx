---
title: Simulasi lulus, FPGA gagal
step: 3
order: 50
---

# Simulasi lulus, FPGA gagal

Semua test hijau, Build berhasil, bitstream dimuat, tapi LED tidak berkedip atau counter melompat. Ini pengalaman yang sangat umum. Simulasi menguji **model** desain Anda; FPGA menjalankan **rangkaian** hasil sintesis di dunia nyata. Berikut penyebab yang paling sering, kira-kira dari yang paling mudah dicek.

## 1. Pin dan polaritas

- **Nama port tidak sama dengan nama di file constraint.** Port yang tidak dipakai di template diabaikan, tetapi port desain yang tidak ada di constraint membuat Place & Route gagal dengan `Unconstrained IO`. Jadi kalau Build berhasil, semua port sudah terpasang. Pastikan port itu terpasang ke pin yang **benar**.
- **Aktif-rendah.** Menurut template Tang Nano 9K, LED menyala saat diberi 0 dan tombol bernilai 0 saat ditekan. Desain yang benar di simulasi bisa tampak "mati" di board hanya karena polaritasnya terbalik.
- **Clock.** Clock board Tang Nano 9K 27 MHz di pin 52. Counter untuk "satu detik" harus dihitung dari 27 MHz, bukan dari periode clock di testbench.

## 2. Kode yang diabaikan saat sintesis

Delay (`#10`), `initial` dengan delay, dan `$display` tidak menjadi hardware, dan Yosys tidak memberi peringatan. Diukur di image SmartX: `initial begin q = 0; #10 q = 1; end` menjadi `q` yang **konstan 1** di FPGA. Lihat materi *Kode yang tidak bisa disintesis*.

## 3. Sensitivity list tidak lengkap

`always @(a) y = a & b;` di Icarus memberi `y = 0` setelah `a = 1` lalu `b = 1`, karena blok hanya dijalankan ulang saat `a` berubah. Di FPGA hasilnya gerbang AND biasa: `y = 1`. Simulasi dan hardware berbeda, dan baik Yosys maupun Lint tidak memberi peringatan. Selalu gunakan `always @*`.

## 4. Latch tak sengaja

Blok `always @*` yang tidak memberi nilai di semua cabang membuat latch. Di simulasi hasilnya terlihat wajar, tetapi di FPGA latch peka terhadap glitch dan mengacaukan analisis timing. Tab FPGA menampilkan peringatan **Latch** dengan baris kodenya. nextpnr bahkan bisa memperlakukan enable latch sebagai clock baru. Di contoh SmartX, latch dengan enable `rst_n` muncul sebagai jalur kritis `posedge clk → posedge rst_n`.

## 5. Nilai awal dan reset

Di Icarus, register tanpa reset bernilai `X`; di Verilator `0`. Di FPGA, register bernilai sesuai nilai awal di kodenya (`reg q = 0`). Tanpa nilai awal, nilainya bergantung pada chip, biasanya 0, dan tidak ada simulator yang menunjukkannya dengan tepat. Desain yang diam-diam bergantung pada nilai awal bisa lulus di satu tempat dan gagal di tempat lain. Tentukan nilai awal atau reset secara eksplisit untuk setiap register yang penting.

## 6. Input asinkron

Testbench mengubah input di saat yang rapi. Tombol, UART, dan sensor berubah kapan saja, dan tombol juga memantul. Tanpa synchronizer dan debouncer, desain bisa bekerja 99 kali lalu gagal acak di kali ke-100. Lihat materi *Synchronizer 2-flop* dan *Debounce tombol*.

## 7. Timing tidak tercapai

Kalau Fmax di tab FPGA berwarna merah, bitstream tetap dibuat (dan `smartx-flash` memberi peringatan), tetapi rangkaian terlalu lambat untuk clock-nya. Hasilnya bisa salah sesekali atau terus-menerus. Lihat materi *Membaca laporan timing*.

## Urutan memeriksa

1. Baca peringatan sintesis di tab FPGA. Peringatan latch, banyak driver, sinyal tanpa driver, atau input tidak dipakai hampir selalu menunjukkan bug.
2. Cocokkan nama port dan pin dengan file constraint, termasuk polaritasnya.
3. Pastikan timing **Tercapai**.
4. Jalankan **Lint** dan simulasi di **Icarus dan Verilator**. Kalau keduanya berbeda, cari X atau masalah inisialisasi.
5. Sederhanakan: buat desain kecil yang hanya menyalakan satu LED dari satu tombol. Kalau itu jalan, tambahkan bagian lain satu per satu.
