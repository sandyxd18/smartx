# Fase 1: Exercises (langkah 1)

Tujuan: pengganti HDLBits versi pribadi. Tulis Verilog di browser, klik Run, lihat hasil test dan waveform.

## Task

1. [x] **Content loader**: `backend/app/content/` membaca `content/exercises/*/exercise.yaml`, memvalidasi dengan model Pydantic, dan cache di memori (reload saat file berubah di mode dev).
2. [x] **Job `grade`**: memanggil `tools/grader/grade.py` di dalam image toolchain. Mount soal read-only; kode user ditulis ke folder run. `collect()` membaca `result.json`. Path waveform di JSON dipetakan ke URL artefak.
3. [x] **API exercises** sesuai ARCHITECTURE: daftar + progres, detail, run, hint berikutnya, solusi (403 sampai lulus atau `attempts >= SOLUTION_UNLOCK_ATTEMPTS`, default 5).
4. [x] **Halaman daftar soal**: dikelompokkan per topik, badge level, status (belum/gagal/lulus), filter.
5. [x] **Halaman soal**: split view. Kiri: teks soal (Markdown + tabel). Kanan: Monaco editor (bahasa Verilog via Monarch), tombol Run (`Ctrl+Enter`), reset ke starter. Bawah: panel hasil dengan tab **Tests** (daftar test, hijau/merah, pesan), **Log**, **Waveform**.
6. [x] **Autosave** kode per soal (debounce 1 detik) ke `ExerciseProgress.last_code`.
7. [x] **WaveView**: iframe Surfer yang memuat `.fst` dari URL artefak. Tambahkan tombol unduh sebagai fallback.
8. **Tulis 19 soal lagi** sesuai tabel kurikulum di `CONTENT-FORMAT.md` (total 20). Setiap soal harus lolos `make check-content`. Untuk soal "jebakan umum", starter berisi kode yang salah dan user diminta memperbaikinya.
9. **Verilator lint pada Run** (opsional tapi bagus): sebelum simulasi, jalankan `verilator --lint-only -Wall` dan tampilkan warning (misalnya latch, width mismatch) sebagai anotasi di Monaco.

## Kriteria selesai

- [ ] 20 soal tampil di daftar, semua lolos `make check-content`.
- [x] Mengerjakan `counter-4bit` dari starter sampai lulus sepenuhnya lewat UI, termasuk melihat waveform.
- [x] Error kompilasi menampilkan baris dan pesan dari Icarus, dan baris itu ditandai di editor.
- [x] Waktu dari klik Run sampai hasil < 5 detik untuk soal kecil (ukur dan catat di log kemajuan).
- [x] `solution.v` tidak bisa diambil lewat API sebelum syarat terpenuhi (ada test-nya).
- [x] Refresh halaman tidak menghilangkan kode yang sedang ditulis.
