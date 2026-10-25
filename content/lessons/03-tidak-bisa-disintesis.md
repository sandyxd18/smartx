---
title: Kode yang tidak bisa disintesis
step: 3
order: 10
---

# Kode yang tidak bisa disintesis

Simulator menjalankan Verilog seperti program. Synthesizer (Yosys) melakukan hal lain: ia mencari **rangkaian** yang perilakunya sama, lalu membangunnya dari LUT, flip-flop, dan kabel. Sebagian Verilog tidak punya padanan rangkaian. Ada yang ditolak dengan error, tetapi ada juga yang **diam-diam diabaikan**, dan bagian ini yang paling berbahaya.

Semua contoh di bawah diukur dengan Yosys 0.70 (`synth_gowin`) di image toolchain SmartX.

## Ditolak dengan error

Bagian ini mudah, karena Build berhenti di tahap Synthesize dan barisnya ditandai di editor.

| Kode | Pesan Yosys |
|---|---|
| `always @(posedge clk or negedge clk)` | `Multiple edge sensitive events found for this signal!` |
| `while (v != 0) ...` di blok `always` | `While loops are only allowed in constant functions!` |

Flip-flop di FPGA hanya mengenal satu sisi clock, jadi always dengan dua sisi clock tidak punya padanan. Loop yang jumlah putarannya bergantung pada data juga tidak bisa jadi hardware, karena rangkaian harus punya ukuran tetap. Loop `for` dengan batas konstan boleh dipakai; Yosys membukanya menjadi salinan logika.

## Diabaikan tanpa peringatan

Yosys tidak menulis warning apa pun untuk kode di bawah ini. Lint Verilator (`-Wall`) juga diam.

| Kode | Di simulasi | Di FPGA |
|---|---|---|
| `assign #5 y = a;` | `y` mengikuti `a` 5 ns kemudian | `y = a` tanpa jeda |
| `initial begin q = 0; #10 q = 1; end` | `q` bernilai 0, lalu 1 setelah 10 ns | `q` **konstan 1** (Yosys mengambil nilai terakhir) |
| `$display("q=%b", q);` | mencetak ke log | dihapus |
| `always @(a) y = a & b;` | `y` tidak berubah saat hanya `b` berubah | `y = a & b` selalu |

Baris terakhir paling sering menjebak. Dengan `a = 1` lalu `b` diubah menjadi 1, Icarus memberi `y = 0`, karena blok itu hanya dijalankan ulang saat `a` berubah. Yosys membangun gerbang AND biasa, sehingga di FPGA `y = 1`. Solusinya: untuk logika kombinasional selalu tulis `always @*`, jangan daftar sinyal manual.

Delay (`#`) dan `$display` tetap berguna di **testbench**, karena testbench tidak pernah disintesis. Di file desain, jangan gunakan keduanya.

## Bisa disintesis, tapi mahal

| Kode | Hasil untuk Tang Nano 9K |
|---|---|
| `assign q = a / b;` (16 bit, `b` bukan konstanta) | 376 ALU dan sekitar 130 LUT untuk satu pembagian |
| `assign q = a * b;` (16 bit × 16 bit) | satu blok pengali `MULT18X18`, tanpa LUT |

Pembagi dengan konstanta pangkat dua (`a / 8`) hanya menjadi geser bit dan tidak memakan apa-apa. Pembagi umum menjadi rangkaian besar yang juga lambat, sehingga sering menjadi jalur kritis. Di hardware, pembagian biasanya dikerjakan beberapa siklus (pembagi berurutan), bukan sekaligus.

## Nilai awal register

```verilog
reg [3:0] q = 4'd9;   // atau: initial q = 4'd9;
```

Di FPGA ini **didukung**: Yosys menyimpan nilai awal di bitstream (untuk `9` = `1001`, dua flip-flop memakai jenis yang menyala bernilai 1), sehingga register sudah bernilai 9 begitu board selesai dikonfigurasi. Lint Verilator memberi warning `PROCASSINIT` untuk pola ini, karena di **ASIC** (langkah 5) nilai awal seperti ini tidak ada; chip butuh reset. Untuk latihan FPGA, warning ini boleh diterima. Kalau desain akan dibawa ke ASIC, ganti dengan reset.

## Ringkasnya

- Desain hanya boleh berisi hal yang punya bentuk rangkaian: `assign`, `always @*`, `always @(posedge clk)`, dan instansiasi modul.
- Semua yang berhubungan dengan waktu (`#`, `wait`, `initial` dengan delay) dan cetak (`$display`) hanya untuk testbench.
- Setelah Build, baca tab FPGA: peringatan sintesis dan angka resource sering menunjukkan kode yang tidak menjadi rangkaian seperti yang Anda kira.
