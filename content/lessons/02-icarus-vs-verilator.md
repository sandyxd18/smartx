---
title: Icarus vs Verilator
step: 2
order: 40
---

# Icarus vs Verilator

Workspace bisa memakai dua simulator; pilih di `smartx.yaml` (`simulator: icarus` atau `verilator`). Keduanya menjalankan testbench cocotb yang sama, tetapi cara kerjanya berbeda, dan perbedaan itu bisa membuat test lulus di satu simulator dan gagal di simulator lain.

## Perbedaan utama: 4 nilai vs 2 nilai

Icarus adalah simulator **4-state**: setiap bit bisa bernilai `0`, `1`, `X` (tidak diketahui), atau `Z` (tidak di-drive). Verilator adalah simulator **2-state**: hanya `0` dan `1`.

Contoh berikut diukur di image toolchain SmartX (Icarus 14.0 devel, Verilator 5.053) dengan desain kecil berisi register tanpa reset dan input yang tidak pernah diberi nilai oleh testbench:

| Kasus | Icarus | Verilator |
|---|---|---|
| Register tanpa reset, dibaca setelah 3 siklus | `X` | `0` |
| `a & 1'b1` dengan `a` tidak pernah diberi nilai | `X` | `0` |
| `if (sel) y = 1; else y = 0;` dengan `sel = X` | `y = 0` | `sel` terbaca `0`, `y = 0` |

Ada dua pelajaran dari tabel ini.

1. **Verilator menyembunyikan bug reset.** Register yang lupa di-reset bernilai 0 di Verilator, sehingga test bisa lulus. Di hardware, nilai awalnya tidak bisa ditebak. Icarus menunjukkan X, dan helper `read_int()` di testbench SmartX menolak X dengan pesan yang jelas.
2. **Icarus pun bisa menyembunyikan X.** `if` dengan kondisi X mengambil cabang `else`, sehingga keluarannya terlihat sah (`0`). Perilaku ini disebut *X-optimism*. Karena itu, reset semua register yang penting dan beri nilai ke semua input sejak awal, jangan mengandalkan X untuk muncul dengan sendirinya.

Kasus nyata dari SmartX: contoh test di snippet cocotb awalnya membuat driver valid/ready **setelah** reset. Akibatnya `in_valid` masih X di sisi naik pertama. Test itu lulus di Verilator (X dianggap 0) dan gagal di Icarus (`Cannot convert Logic('X') to int`). Perbaikannya: beri nilai ke semua input sebelum reset dilepas.

## Perbedaan lain

| | Icarus | Verilator |
|---|---|---|
| Cara kerja | menafsirkan desain (event-driven) | mengompilasi desain menjadi program C++ |
| Mulai simulasi | cepat; FIFO contoh sekitar 2,5 detik dari klik Simulasi | lebih lambat karena kompilasi C++; FIFO contoh sekitar 12,5 detik |
| Simulasi panjang | lebih lambat per siklus | jauh lebih cepat per siklus setelah dikompilasi |
| Ketelitian lint | longgar | ketat (lebar bit, sinyal tak terpakai, dan lain-lain); lihat tombol **Lint** |
| Waveform | `<top>.fst` di `sim_build` | `dump.fst`; di Surfer ada scope `$rootio` dan modul top |

Waktu di tabel diukur di mesin pengembangan SmartX dan hanya menggambarkan perbandingan kasar.

## Saran praktis

- Saat menulis desain dan testbench, pakai **Icarus**: mulainya cepat, dan X terlihat.
- Sebelum menganggap desain selesai, jalankan juga di **Verilator**, lalu pakai **Lint**. Kalau hasil kedua simulator berbeda, hampir selalu ada X atau masalah inisialisasi yang perlu dicari.
- Untuk simulasi yang sangat panjang (jutaan siklus, misalnya prosesor yang menjalankan program), Verilator jauh lebih cepat.
