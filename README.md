# SmartX

Lab pribadi untuk belajar desain chip digital: dari latihan Verilog, simulasi dan verifikasi, FPGA, proyek bertahap sampai CPU RISC-V, ASIC flow dengan LibreLane, hingga repo yang siap dikirim ke Tiny Tapeout. Semua dari satu aplikasi web lokal.

Status: rancangan + fondasi awal. Pengembangan dilakukan bersama Claude Code mengikuti `docs/ROADMAP.md`.

## Kebutuhan

- Linux, macOS, atau Windows dengan Docker Desktop; GNU Make, Git, Python 3.10+
- Node.js 20+ (untuk frontend, mulai Fase 0)
- Fase 5–6: RAM 12–16 GB, ruang disk kosong ±30 GB

### Windows

Perintah `make` bisa dijalankan dari PowerShell maupun Git Bash. Yang dibutuhkan:

- [Git for Windows](https://git-scm.com/download/win) di lokasi default (`C:\Program Files\Git`). Makefile memakai bash-nya. Kalau Git dipasang di tempat lain, set `GIT_BASH` ke path `bash.exe` tanpa spasi.
- GNU Make: `winget install ezwinports.make`, lalu buka terminal baru.
- Docker Desktop dalam keadaan menyala.

## Mulai

```bash
cp .env.example .env
make pin-toolchain      # pilih versi OSS CAD Suite terbaru, simpan ke .env
make toolchain          # build image toolchain (sekali, beberapa menit)
make tool-versions      # pastikan tool terpasang
make check-content      # uji soal contoh di dalam image
```

Tanpa Docker, grader bisa dicoba langsung di host jika `iverilog` sudah terpasang:

```bash
pip install -r tools/grader/requirements.txt
python tools/grader/grade.py --exercise content/exercises/counter-4bit --use-solution   # lulus
python tools/grader/grade.py --exercise content/exercises/counter-4bit --use-starter    # gagal
```

## Melanjutkan dengan Claude Code

Folder ini sudah berupa repo Git dengan satu commit awal. Masuk ke foldernya lalu jalankan:

```bash
claude
```

Lalu minta: *"Baca CLAUDE.md dan ROADMAP, lalu kerjakan Fase 0."* Atau pakai perintah `/next-task` dan `/phase-review` yang ada di `.claude/commands/`.

## Struktur

Lihat `docs/ARCHITECTURE.md`. Ringkasnya: `backend/` (FastAPI), `frontend/` (React), `content/` (soal, proyek, profil board), `tools/` (grader, helper flashing), `docker/` (image toolchain), `docs/` (spesifikasi dan rencana).
