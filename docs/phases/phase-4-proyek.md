# Fase 4: Proyek terpandu (langkah 4)

Tujuan: membangun sistem yang makin besar, milestone demi milestone, memakai workspace (Fase 2) dan FPGA (Fase 3) yang sudah ada.

## Task

1. **Mesin proyek terpandu**: loader `content/projects/*/project.yaml`, membuat proyek workspace dari milestone pertama, dan membuka milestone berikutnya hanya setelah test milestone saat ini lulus. File milestone sebelumnya tetap milik pengguna (tidak ditimpa).
2. **UI proyek**: daftar milestone dengan status, teks penjelasan di samping editor, tombol "Cek milestone".
3. **Konten proyek** (tulis berurutan, uji dengan solusi resmi seperti soal):
   - `uart-tx`: baud generator → shift register → frame lengkap (start/data/stop) → demo FPGA kirim "Hello" ke PC.
   - `uart-rx`: oversampling 16x → deteksi start bit → loopback di FPGA.
   - `spi-master`: mode 0, lalu CPOL/CPHA lengkap; demo baca ID flash SPI di board.
   - `i2c-master`: START/STOP, kirim byte + ACK, baca register sensor.
   - `rv32i-single`: register file → ALU → decoder → datapath lengkap → lulus `riscv-tests` rv32ui.
   - `rv32i-pipe`: 5 tahap → hazard & forwarding → stall load-use → branch.
   - `mini-soc`: RV32I + RAM + UART memory-mapped; program C mencetak "Hello World" di FPGA.
4. **Toolchain RISC-V** di image light: `gcc-riscv64-unknown-elf` + `picolibc-riscv64-unknown-elf` (paket Ubuntu 24.04) atau toolchain dari OSS CAD Suite jika tersedia. Job `riscv_build` untuk compile C/ASM → `.hex` yang dimuat `$readmemh`.
5. **riscv-tests**: build sekali di image (atau sebagai artefak konten), dan test cocotb yang menjalankan setiap test, membaca alamat `tohost`, dan melaporkan lulus/gagal per instruksi.
6. **Hubungkan ke langkah 5**: tiap proyek boleh punya `asic:` di `project.yaml` agar bisa langsung dibawa ke Fase 5 (contoh: `uart-tx` ukuran kecil, cocok untuk Tiny Tapeout).

## Kriteria selesai

- [ ] `uart-tx` selesai dari milestone 1 sampai demo FPGA, terlihat di terminal serial PC.
- [ ] `rv32i-single` lulus semua `rv32ui-p-*` di simulasi.
- [ ] `mini-soc` menjalankan program C "Hello World" lewat UART di FPGA.
- [ ] Semua solusi resmi proyek lulus pengecekan otomatis (perluas `check_content.py`).
