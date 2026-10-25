# Roadmap

Kerjakan berurutan. Setiap fase menghasilkan aplikasi yang bisa dipakai, dan fase berikutnya dibangun di atasnya. Detail task dan kriteria selesai ada di `docs/phases/`.

Status: `[ ]` belum, `[~]` sedang dikerjakan, `[x]` selesai (semua kriteria terpenuhi dan `make check` hijau).

| Fase | Isi | Langkah belajar | Status |
|---|---|---|---|
| 0 | Fondasi: repo, backend, frontend, Docker runner, toolchain image | (semua) | [~] |
| 1 | Exercises: daftar soal, editor, grading, waveform, 20 soal | 1 | [ ] |
| 2 | Workspace simulasi: proyek multi-file, lint, sim, cocotb, riwayat run | 2 | [ ] |
| 3 | FPGA: board profile, sintesis, PnR, laporan, bitstream, helper flash | 3 | [ ] |
| 4 | Proyek terpandu: UART, SPI, I2C, RV32I, mini-SoC | 4 | [ ] |
| 5 | ASIC: LibreLane, PDK, laporan sign-off, render GDS | 5 | [ ] |
| 6 | Tapeout export: generator repo Tiny Tapeout, hardening lokal, checklist | 6 | [ ] |

## Yang sudah ada saat proyek diserahkan

- `tools/grader/grade.py` dan `check_content.py`: grader cocotb yang sudah diuji dengan Icarus Verilog 12 + cocotb 2.1.
- `content/exercises/counter-4bit/`: contoh soal lengkap; solusi lulus, starter gagal dengan pesan yang jelas.
- `docker/toolchain/Dockerfile`, `Makefile`, `.env.example`.
- Dokumen: SPEC, ARCHITECTURE, DECISIONS, CONTENT-FORMAT, rencana per fase.

## Log kemajuan

Tambahkan satu baris per sesi kerja: tanggal, fase, apa yang selesai, apa yang tertunda.

- 2026-10-25: paket awal dibuat (dokumen, grader, contoh soal, Dockerfile toolchain).
- 2026-10-25: Fase 0 task 1 selesai (image toolchain OSS CAD Suite 2026-10-24, check-content hijau di Windows). Diperbaiki: libpython untuk cocotb, UID user container, Makefile lintas PowerShell/Git Bash. Berikutnya: task 2 backend skeleton.
