# Fase 2: Workspace simulasi (langkah 2)

Tujuan: lingkungan kerja proyek bebas (sandbox) dengan banyak file, testbench sendiri, dan riwayat run. Di sini pengguna belajar menulis verifikasinya sendiri, bukan hanya memakai testbench yang disediakan.

## Task

1. **Proyek sandbox**: buat proyek baru dari template (`empty`, `cocotb-basic`, atau "salin dari soal X"). File tree dengan buat/ganti nama/hapus file dan folder.
2. **Konfigurasi proyek** (`chiplab.yaml` di root proyek): `top`, `sources` (glob), `tests` (modul cocotb), `simulator` (`icarus` | `verilator`), `parameters`, `defines`. Ada form UI dan editor mentah; keduanya sinkron.
3. **Job `lint`**: `verilator --lint-only -Wall` atas semua sumber. Parser output → diagnostic `{file, line, col, severity, code, message}` → tampil di panel Problems dan sebagai marker Monaco.
4. **Job `sim`**: generalisasi `grade.py` menjadi runner proyek (cocotb runner dengan banyak sumber, parameter, defines, dan pilihan simulator). Hasil per test + waveform.
5. **Riwayat run**: daftar run per proyek (waktu, jenis, status, durasi, ringkasan test). Klik untuk membuka hasil lama.
6. **Bandingkan dua run**: test mana yang berubah status. (Diff waveform tidak perlu.)
7. **Template testbench**: snippet cocotb untuk clock/reset, driver valid-ready, scoreboard sederhana, dan coverage dengan `cocotb-coverage` (opsional).
8. **Materi singkat** di `content/lessons/02-*.md`: cara menulis model referensi, test acak dengan seed, membaca waveform untuk debugging. Tampilkan di sidebar workspace.

## Kriteria selesai

- [ ] Membuat proyek sandbox berisi FIFO sinkron + testbench cocotb dengan scoreboard, menjalankannya di Icarus dan Verilator, keduanya hijau.
- [ ] Warning lint muncul di editor pada baris yang tepat.
- [ ] Riwayat menyimpan minimal 50 run terakhir per proyek; hasil lama bisa dibuka beserta waveform-nya.
- [ ] Perbedaan Icarus vs Verilator (mis. X-propagation) dijelaskan di materi.
