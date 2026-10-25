# CLAUDE.md

Panduan kerja untuk Claude Code di repo ini. Baca file ini dulu di setiap sesi.

## Proyek

ChipLab: aplikasi web lokal, satu pengguna, untuk belajar desain chip digital dari latihan Verilog sampai tapeout Tiny Tapeout. Membungkus tool open-source (Icarus, Verilator, cocotb, Yosys, nextpnr, LibreLane, KLayout) di balik satu UI.

Dokumen acuan, dibaca sesuai kebutuhan:
- `docs/SPEC.md`: apa yang dibangun dan apa yang tidak.
- `docs/ARCHITECTURE.md`: struktur repo, model data, job system, API.
- `docs/DECISIONS.md`: keputusan teknis dan alasannya.
- `docs/CONTENT-FORMAT.md`: format soal, proyek, profil board.
- `docs/ROADMAP.md`: status fase dan log kemajuan.
- `docs/phases/phase-N-*.md`: task dan kriteria selesai per fase.

## Cara bekerja

1. Di awal sesi: buka `docs/ROADMAP.md`, cari fase pertama yang belum `[x]`, lalu buka file fasenya.
2. Kerjakan **satu fase dalam satu waktu**, task demi task sesuai urutan di file fase. Jangan mulai fase berikutnya sebelum semua kriteria selesai fase saat ini tercentang.
3. Untuk setiap task: tulis/ubah test dulu jika memungkinkan, implementasikan, jalankan `make check` (atau bagian yang relevan), baru anggap selesai.
4. Setelah task selesai: centang di file fase, commit dengan pesan bahasa Inggris (`feat(jobs): add docker runner with resource limits`).
5. Di akhir sesi: tambahkan satu baris di "Log kemajuan" `ROADMAP.md`.
6. Jika ada keputusan teknis baru atau mengubah keputusan lama: tambahkan entri di `DECISIONS.md`.
7. Jika spesifikasi tidak jelas atau bertentangan, tanyakan ke pemilik proyek sebelum membangun hal yang mahal diulang. Hal kecil: ambil pilihan paling masuk akal dan catat.

## Perintah

```
make help                 daftar target
make pin-toolchain        pin versi OSS CAD Suite ke .env
make toolchain            build image toolchain
make check-content        uji semua soal di dalam image
make check-content-local  uji soal dengan tool di host
make dev                  jalankan aplikasi (setelah Fase 0)
make test | lint | check  (setelah Fase 0)
```

Uji satu soal secara manual:
```
python tools/grader/grade.py --exercise content/exercises/counter-4bit --use-solution
```

## Konvensi

- **Bahasa**: UI, materi, pesan error untuk pengguna, dan dokumen dalam Bahasa Indonesia. Kode, identifier, komentar kode, nama commit dalam bahasa Inggris.
- **Backend**: Python 3.12, FastAPI, SQLModel, type hints di semua fungsi publik, `ruff` untuk lint + format, `pytest` untuk test. Fungsi yang memanggil Docker diuji dengan `FakeRunner`, bukan Docker sungguhan.
- **Frontend**: React + TypeScript strict, komponen fungsi, client API di-generate dari OpenAPI (jangan tulis tipe API manual), `eslint` + `vitest`.
- **Job baru**: satu modul di `backend/app/jobs/kinds/` dengan `prepare()` dan `collect()`; tambahkan fixture folder run untuk test `collect()`.
- **Konten**: setiap soal/proyek baru wajib lolos `check_content` (solusi lulus, starter gagal). Ikuti aturan testbench di `CONTENT-FORMAT.md`.
- **Versi tool**: jangan pakai `latest` untuk image atau toolchain. Pin, dan catat versi di hasil run.

## Batasan penting

- Jangan pernah mengirim `solution.v` ke frontend kecuali lewat endpoint solusi yang sudah memeriksa syarat buka.
- Job container: selalu `--network none`, user non-root, batas memori/CPU/pids/waktu. Jangan mount Docker socket ke job container dan jangan `--privileged`.
- Semua path dari request dinormalisasi dan dicek tetap di dalam folder proyek/run (ada test path traversal).
- Backend bind ke `127.0.0.1` secara default.
- Jangan salin soal HDLBits atau materi berhak cipta lain ke `content/`. Tulis sendiri.
- Ekosistem tool chip berubah cepat (OpenLane → LibreLane, shuttle TT berganti). Sebelum menulis kode yang bergantung pada CLI/format file sebuah tool, cek dokumentasi versi yang dipin atau jalankan `--help` di dalam image; jangan andalkan ingatan.
