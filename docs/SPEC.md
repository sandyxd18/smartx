# SmartX: spesifikasi produk

## Tujuan

SmartX adalah aplikasi web lokal untuk satu orang (pemiliknya) yang ingin belajar desain chip digital dari nol sampai tapeout. Satu desain Verilog yang sama dibawa melewati enam langkah:

| Langkah | Pertanyaan yang dijawab | Modul di aplikasi |
|---|---|---|
| 1. Latihan Verilog | Bagaimana mendeskripsikan hardware? | Exercises |
| 2. Simulasi & verifikasi | Apakah logikanya benar? | Workspace: Sim |
| 3. FPGA | Apakah bisa berjalan di hardware nyata? | Workspace: FPGA |
| 4. Proyek bertahap | Bisakah saya membangun sistem utuh? | Projects |
| 5. ASIC flow | Bagaimana desain menjadi geometri chip? | Workspace: ASIC |
| 6. Tapeout | Apakah bekerja di silikon? | Tapeout export |

Aplikasi ini membungkus tool open-source yang sudah ada. Tidak ada tool EDA yang ditulis ulang.

## Pengguna

Satu pengguna, di jaringan lokal. Tidak ada login, tidak ada multi-tenant. Aplikasi bisa dijalankan di laptop atau di VM Linux, diakses lewat browser.

## Kebutuhan fungsional

### F1. Exercises (langkah 1)
- Daftar soal dikelompokkan per topik dan level, dengan status: belum, gagal, lulus.
- Halaman soal: teks soal (Markdown), editor Verilog (Monaco, syntax highlight), tombol **Run**.
- Hasil run: status per test, pesan error yang mudah dibaca, log kompilasi, dan waveform.
- Hint dibuka satu per satu. Solusi bisa dibuka setelah lulus atau setelah N kali gagal (N bisa diatur).
- Kode terakhir per soal tersimpan otomatis.

### F2. Workspace simulasi (langkah 2)
- Proyek berisi banyak file (`.v`, `.sv`, `.py`, `.yaml`), dengan file tree.
- Aksi: Lint (Verilator `--lint-only`), Simulate (Icarus atau Verilator), Run cocotb tests.
- Waveform viewer di browser untuk file `.fst`/`.vcd`.
- Riwayat run per proyek, bisa membandingkan hasil dua run.

### F3. FPGA (langkah 3)
- Pilih board target (profil board). Default: Tang Nano 9K; tambahan: iCE40 (iCEBreaker/UPduino).
- Editor constraint (`.cst` untuk Gowin, `.pcf` untuk iCE40) dengan template per board.
- Aksi: Synthesize (Yosys), Place & Route (nextpnr), Pack (bitstream).
- Laporan: utilisasi resource (LUT, FF, BRAM), Fmax per clock, warning penting (latch, multi-driven, sinyal tidak terpakai).
- Bitstream bisa diunduh. Flashing dilakukan dengan skrip helper di host (`smartx-flash`), karena USB ke container tidak andal.

### F4. Projects (langkah 4)
- Proyek terpandu: UART TX/RX, SPI master, I2C master, RV32I single-cycle, RV32I pipeline, mini-SoC.
- Tiap proyek punya milestone. Tiap milestone punya teks penjelasan, file starter, dan test cocotb yang harus lulus sebelum lanjut.
- Proyek RISC-V: toolchain `riscv64-unknown-elf-gcc` untuk compile program C/ASM, dan integrasi `riscv-tests`.

### F5. ASIC flow (langkah 5)
- Konfigurasi LibreLane per proyek (`config.yaml`) dengan form sederhana + editor mentah.
- PDK: SKY130 dan IHP SG13G2 (GF180MCU opsional).
- Job berjalan di background, log tampil live, bisa dibatalkan.
- Ringkasan hasil: area, jumlah cell, WNS/TNS per corner, jumlah pelanggaran DRC/LVS/antenna.
- Render layout GDS sebagai gambar PNG (KLayout batch), bisa di-zoom.

### F6. Tapeout export (langkah 6)
- Generator proyek Tiny Tapeout dari desain yang sudah lolos langkah 5: `info.yaml`, `src/`, `test/`, `docs/info.md`.
- Pengecekan pin (8 input, 8 output, 8 bidir, clk, rst_n, ena) dan nama top `tt_um_*`.
- Menjalankan hardening lokal dengan `tt-support-tools` sesuai shuttle yang dipilih.
- Checklist submit. Submit dan pembayaran tetap dilakukan manual di situs Tiny Tapeout.

### F7. Umum
- Progres belajar per langkah (dashboard sederhana).
- Semua data ada di satu folder (`data/`), mudah di-backup.
- Export/import proyek sebagai `.zip` atau repo Git.

## Kebutuhan non-fungsional

- **Waktu respons**: grading soal kecil < 5 detik dari klik sampai hasil (setelah image toolchain ada).
- **Isolasi**: setiap job di container baru, `--network none`, batas CPU/RAM/waktu, user non-root.
- **Reproducible**: versi tool dipin (tanggal OSS CAD Suite, tag image ASIC). Versi tool dicatat di setiap hasil run.
- **Pulih dari restart**: job yang sedang berjalan saat backend mati ditandai `failed` dengan alasan jelas.
- **Bahasa**: UI dan materi dalam Bahasa Indonesia; kode, identifier, dan commit dalam bahasa Inggris.

## Di luar cakupan

- Multi-user, autentikasi, kuota.
- Desain analog (Xschem/ngspice). Bisa jadi ekspansi setelah v1.
- Tool komersial (Cadence, Synopsys).
- Simulasi di browser lewat WebAssembly. Semua tool berjalan di backend; ini bisa dipertimbangkan nanti.
- Submit otomatis ke Tiny Tapeout.

## Definisi "v1 selesai"

Satu desain (misalnya UART TX) bisa dibawa dari soal latihan → testbench cocotb → bitstream FPGA → GDS lewat LibreLane → repo Tiny Tapeout yang lolos hardening lokal, seluruhnya dari UI SmartX.
