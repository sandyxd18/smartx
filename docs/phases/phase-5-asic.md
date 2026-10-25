# Fase 5: ASIC flow (langkah 5)

Tujuan: membawa desain dari RTL ke GDS dengan LibreLane, dan membaca hasil sign-off (timing, DRC, LVS) dari UI.

## Sebelum mulai

1. Pilih dan pin `ASIC_IMAGE` di `.env` (lihat `DECISIONS.md` D07). Cek di dalam image: perintah LibreLane yang tersedia, versinya, dan lokasi PDK (`PDK_ROOT`, `PDK`).
2. Uji manual satu desain kecil (counter) di image itu dari terminal sebelum menulis kode backend. Catat perintah persisnya di `docs/notes/asic-manual-run.md`.
3. Pastikan mesin punya RAM dan disk cukup (lihat ARCHITECTURE).

## Task

1. **Job `asic`** (kelas heavy):
   - `prepare`: tulis sumber RTL + `config.yaml` LibreLane ke folder run, set PDK dan standard cell library.
   - Jalankan LibreLane flow Classic. Log streaming; tahap aktif (Synthesis, Floorplan, Placement, CTS, Routing, Signoff) diparse dari log untuk progress bar.
   - `collect`: baca metrics LibreLane (format JSON di folder run hasil), path GDS, dan laporan STA/DRC/LVS.
2. **Form konfigurasi**: `DESIGN_NAME`, `VERILOG_FILES`, `CLOCK_PORT`, `CLOCK_PERIOD`, ukuran die/`FP_CORE_UTIL`, PDK (sky130A / ihp-sg13g2), plus editor YAML mentah.
3. **Ringkasan hasil**: area die/core, jumlah cell, utilisasi, WNS/TNS setup & hold per corner, jumlah pelanggaran DRC/LVS/antenna, daya (jika tersedia). Status sign-off hijau/merah.
4. **Render GDS**: skrip KLayout batch → PNG keseluruhan + beberapa crop. Tampilkan di `GdsView` dengan zoom/pan. GDS bisa diunduh.
5. **Pembatalan & sisa disk**: cancel membunuh container; tombol hapus run lama; tampilkan total ukuran `data/runs/`.
6. **Materi** `content/lessons/05-*.md`: tiap tahap flow, arti WNS/TNS, kenapa DRC/LVS penting, cara memperbaiki timing (constraint, pipeline, mengecilkan logika).

## Kriteria selesai

- [ ] `counter-4bit` dan `uart-tx` sampai GDS di SKY130 dengan DRC/LVS bersih.
- [ ] Setidaknya satu desain juga lolos di IHP SG13G2.
- [ ] Ringkasan di UI cocok dengan angka di file metrics mentah (ada test parser dengan fixture).
- [ ] Desain dengan `CLOCK_PERIOD` terlalu ketat menunjukkan WNS negatif dan status merah.
- [ ] PNG layout tampil dan bisa diperbesar.
