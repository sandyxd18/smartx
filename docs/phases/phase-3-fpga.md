# Fase 3: FPGA (langkah 3)

Tujuan: desain dari workspace disintesis, di-place & route untuk board nyata, dan pengguna bisa membaca laporan resource serta timing sebelum flashing.

## Sebelum mulai

Konfirmasi board yang dimiliki (lihat `DECISIONS.md` D08). Kerjakan satu board sampai tuntas sebelum menambah board kedua.

Dikonfirmasi 2026-10-25: pemilik belum punya board. Mulai dengan Tang Nano 9K sampai bitstream; iCE40 dipindah ke task 8 (D38).

## Task

1. [x] **Profil board** di `content/boards/` (format di `CONTENT-FORMAT.md`) dan template constraint. Board pertama: Tang Nano 9K (Gowin, `nextpnr-himbaechel` + `gowin_pack`). Board kedua (iCE40) ada di task 8.
2. [x] **Job `fpga`** dengan tiga tahap yang terlihat terpisah di UI:
   - Synthesize: `yosys -p "synth_gowin -top <top> -json out.json"` (atau `synth_ice40`). Simpan `yosys.log` dan `stat`.
   - Place & Route: nextpnr dengan `--freq` dari `smartx.yaml`, keluarkan `--report report.json`.
   - Pack: hasilkan bitstream.
3. [x] **Parser laporan** di `backend/app/reports/`:
   - Utilisasi resource dari `report.json` nextpnr (LUT, FF, BRAM, IO) vs kapasitas device.
   - Fmax per domain clock vs target, beri warna merah jika gagal.
   - Warning Yosys yang penting: latch terbentuk, sinyal tidak terpakai, multi-driven, inferred memory gagal.
   Tulis unit test parser dengan file laporan contoh di `backend/tests/fixtures/`.
4. [x] **Halaman FPGA** di workspace: pilih board, editor constraint, tombol Build, tabel laporan, unduh bitstream.
5. [x] **Helper flashing** `tools/flash/smartx-flash`: skrip di host yang mengunduh bitstream run terakhir dari backend (atau path lokal) lalu memanggil `openFPGALoader` sesuai profil board. Dokumentasikan instalasi `openFPGALoader` dan aturan udev di README.
6. [x] **Materi** `content/lessons/03-*.md`: kode yang tidak bisa disintesis, synchronizer 2-flop, debounce, cara membaca laporan timing, kenapa simulasi lulus tapi FPGA gagal.
7. [ ] **Contoh proyek FPGA**: blinky, counter ke LED, tombol dengan debounce.
8. [ ] **Board kedua: iCE40** (`nextpnr-ice40` + `icepack`), setelah Tang Nano 9K tuntas: profil, template `.pcf`, fixture blinky, dan contoh proyek.

## Kriteria selesai

- [ ] Blinky dibangun dari UI dan berkedip di board setelah `smartx-flash`.
- [x] Laporan menampilkan resource dan Fmax yang cocok dengan output nextpnr mentah.
- [x] Desain dengan latch tak sengaja memunculkan peringatan yang jelas di UI.
- [x] Desain yang gagal timing ditandai merah, dengan jalur kritis (dari report) ditampilkan.
