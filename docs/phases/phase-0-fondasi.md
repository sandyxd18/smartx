# Fase 0: Fondasi

Tujuan: kerangka aplikasi berjalan end-to-end untuk satu jenis job sederhana, sebelum fitur apa pun dibangun.

## Task

1. [x] **Image toolchain**
   - `make pin-toolchain && make toolchain` berhasil.
   - `make tool-versions` mencetak versi yosys, iverilog, verilator, nextpnr-himbaechel, cocotb.
   - `make check-content` hijau di dalam image (soal `counter-4bit` valid).
   - Jika nama binary/argumen di OSS CAD Suite berbeda dari dugaan di Dockerfile, perbaiki Dockerfile dan catat di `DECISIONS.md`.

2. [x] **Backend skeleton** (`backend/`)
   - `pyproject.toml` (Python 3.12, fastapi, uvicorn, sqlmodel, pydantic-settings, docker, pyyaml, sse-starlette; dev: pytest, pytest-asyncio, httpx, ruff).
   - `app/config.py` membaca `.env`.
   - `app/db.py` + `app/models.py` sesuai ARCHITECTURE (Project, File, Run, ExerciseProgress).
   - `GET /api/health` mengembalikan versi app dan status Docker (bisa ping daemon atau tidak).

3. [x] **Job system**
   - `jobs/runner.py`: interface `JobRunner` (`start`, `stream_logs`, `wait`, `kill`).
   - `jobs/docker_runner.py`: implementasi Docker dengan semua batasan di ARCHITECTURE (network none, user, memory, cpus, pids, timeout).
   - `jobs/fake_runner.py`: runner palsu untuk unit test (menulis `result.json` dari fixture).
   - `jobs/queue.py`: dua antrian (light/heavy) dengan concurrency dari `.env`.
   - Pemulihan saat startup: run `running`/`queued` → `failed`.
   - Job pertama: `kind=echo` yang menjalankan `yosys -V` di image toolchain. Hanya untuk membuktikan pipa jalan.

4. **API run**
   - `POST /api/runs` (sementara, untuk `echo`), `GET /api/runs/{id}`, `GET /api/runs/{id}/events` (SSE), `POST /api/runs/{id}/cancel`, `GET /api/runs/{id}/files/{path}` dengan pencegahan path traversal + test-nya.

5. **Frontend skeleton** (`frontend/`)
   - Vite + React + TypeScript, React Router, satu library UI yang ringan (mis. Tailwind; shadcn/ui opsional).
   - Client API typed dari OpenAPI (`openapi-typescript`), dengan skrip `npm run gen:api`.
   - Halaman Dashboard yang menampilkan `/api/health` dan tombol "Run echo job" yang menampilkan log live dari SSE.
   - Layout dasar: sidebar navigasi (Dashboard, Latihan, Workspace, Proyek, Tapeout), bahasa Indonesia.

6. **Compose & perintah**
   - `docker-compose.yml`: service `backend` (mount docker.sock, `content/` ro, `data/`), service `frontend` (dev server Vite dengan proxy `/api`).
   - Isi target `make dev`, `make test`, `make lint`, `make check` (hapus `TODO` di Makefile).
   - `scripts/` atau target make untuk mengunduh build web Surfer ke `frontend/public/surfer/` (dipakai Fase 1).

## Kriteria selesai

- [ ] `make dev` lalu buka `http://127.0.0.1:8080`: Dashboard tampil, health OK, Docker terdeteksi.
- [ ] Klik "Run echo job": log versi Yosys muncul live, status berakhir `succeeded`.
- [ ] Cancel job panjang (mis. `sleep 60` di test) mengubah status jadi `cancelled` dan container hilang.
- [ ] Restart backend saat job berjalan: run ditandai `failed` dengan alasan.
- [ ] `make check` hijau (ruff, pytest, eslint, vitest, check-content).
- [ ] Unit test untuk: path traversal, queue concurrency, pemulihan startup (pakai `FakeRunner`).
