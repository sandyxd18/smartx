# FPGA blinky

LED pertama di Tang Nano 9K menyala 0,5 detik lalu mati 0,5 detik, terus-menerus. Lima LED lain mati.

| File | Isi |
|---|---|
| `src/blinky.v` | desain: counter pembagi clock dan satu register `on` |
| `test/test_blinky.py` | testbench cocotb dengan model referensi |
| `constraints/tang-nano-9k.cst` | nama port → pin board (`clk` di pin 52, `led[0]` di pin 10, ...) |
| `smartx.yaml` | modul top, file, dan bagian `fpga` (board, constraint, parameter untuk board) |

## Langkah

1. **Simulasi.** Klik *Simulasi*. Testbench memakai `HALF_PERIOD: 4` dari `parameters`, jadi LED berganti tiap 4 siklus. Buka tab Waveform untuk melihat `led[0]` berkedip.
2. **Build.** Klik *Build*. Build FPGA memakai `fpga.parameters`, yaitu `HALF_PERIOD: 13500000`: 0,5 detik pada clock 27 MHz. Di tab FPGA, lihat tabel resource dan Fmax: desain ini jauh lebih cepat dari 27 MHz.
3. **Ke board.** Jalankan perintah `smartx-flash` yang tampil di tab FPGA (lihat `tools/flash/README.md` di repo SmartX).

## Coba ubah

- Ganti kecepatan kedip lewat `fpga.parameters.HALF_PERIOD`, misalnya `2700000` untuk lima kali per detik.
- Buat LED kedua berkedip berlawanan dengan LED pertama, lalu perbarui model referensi di testbench.

Catatan: pin di constraint diambil dari pinout Tang Nano 9K dan belum dicoba di board fisik oleh pembuat SmartX.
