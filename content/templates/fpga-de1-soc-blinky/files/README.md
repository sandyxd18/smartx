# DE1-SoC blinky dan saklar

Contoh untuk board Terasic DE1-SoC (Intel Cyclone V). LED merah LEDR0 berkedip sekali per detik. LEDR1 sampai LEDR9 menyala mengikuti saklar SW1 sampai SW9. SW0 membalik fasa kedipan LEDR0.

Proyek ini sengaja dibuat sebagai **uji pertama di board**: kalau LEDR0 berkedip, clock dan bitstream bekerja; kalau LED mengikuti saklar, pin input dan output juga benar.

| File | Isi |
|---|---|
| `src/de1_blinky.v` | desain: pembagi clock untuk kedipan, saklar langsung ke LED |
| `test/test_de1_blinky.py` | testbench cocotb dengan model referensi dan saklar acak ber-seed |
| `constraints/de1-soc.qsf` | nama port → pin board, format Quartus (`CLOCK_50` di PIN_AF14, `LEDR[0]` di PIN_V16, ...) |
| `smartx.yaml` | modul top, file, dan bagian `fpga` (board `de1-soc`) |

## Langkah

1. **Simulasi.** Klik *Simulasi*. Testbench memakai `HALF_PERIOD: 4`.
2. **Build.** Klik *Build*. Board memakai `HALF_PERIOD: 25000000` dari `fpga.parameters`: 0,5 detik pada clock 50 MHz. DE1-SoC hanya punya dua tahap, Synthesize dan Place & Route, karena nextpnr-mistral langsung menulis bitstream `.rbf`.
3. **Ke board.** Di komputer lab yang terhubung ke DE1-SoC, jalankan perintah `smartx-flash` dari tab FPGA (lihat `tools/flash/README.md` di repo SmartX, bagian DE1-SoC).

## Bedanya dengan Tang Nano 9K

- LED DE1-SoC **aktif-tinggi**: 1 = menyala. Di Tang Nano 9K kebalikannya.
- Clock board 50 MHz, bukan 27 MHz.
- Constraint memakai format Quartus (`set_location_assignment PIN_... -to ...`).

Catatan: dukungan Cyclone V di toolchain open-source (nextpnr-mistral) masih eksperimental. Bitstream dari SmartX belum dicoba di board fisik oleh pembuatnya. Kalau LED tidak berkedip padahal flashing berhasil, catat hasilnya; itu informasi penting.
