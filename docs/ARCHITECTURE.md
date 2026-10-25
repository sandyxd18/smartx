# Arsitektur SmartX

## Gambaran

```
Browser (React)
  │  HTTP + SSE
  ▼
Backend (FastAPI, Python)  ── SQLite (data/smartx.db)
  │  Docker API (socket)
  ▼
Job container (sekali pakai, per run)
  ├─ image light: smartx/toolchain  (iverilog, verilator, yosys, nextpnr, cocotb)
  └─ image heavy: ASIC_IMAGE         (LibreLane + PDK)
        │
        ▼
  data/runs/<run_id>/   (input, log, artefak: result.json, .fst, .bit, .gds, report)
```

Backend tidak menjalankan tool EDA sendiri. Backend menyiapkan folder run, menyalakan container, mengalirkan log ke browser, lalu membaca `result.json` dan artefak.

## Struktur repo

```
smartx/
├─ CLAUDE.md                 aturan kerja untuk Claude Code
├─ Makefile                  semua perintah (make help)
├─ docker-compose.yml        backend + frontend (dibuat di Fase 0)
├─ docker/
│  ├─ toolchain/Dockerfile   image light
│  └─ asic/                  catatan/pin image heavy (Fase 5)
├─ backend/
│  ├─ pyproject.toml
│  ├─ app/
│  │  ├─ main.py             FastAPI app, mount router
│  │  ├─ config.py           baca .env (pydantic-settings)
│  │  ├─ db.py               SQLite (SQLModel)
│  │  ├─ models.py           tabel: Project, File, Run, ExerciseProgress
│  │  ├─ api/                router per domain: exercises, projects, runs, fpga, asic, tapeout
│  │  ├─ content/            loader soal & proyek dari folder content/
│  │  ├─ jobs/
│  │  │  ├─ queue.py         antrian asyncio, dua kelas: light & heavy
│  │  │  ├─ runner.py        interface JobRunner
│  │  │  ├─ docker_runner.py implementasi pakai docker SDK
│  │  │  └─ kinds/           satu file per jenis job (grade, sim, lint, fpga, asic, tt)
│  │  └─ reports/            parser laporan: yosys.py (warning sintesis), nextpnr.py (utilisasi, Fmax, jalur kritis); librelane menyusul
│  └─ tests/
├─ frontend/
│  ├─ package.json           Vite + React + TypeScript
│  ├─ public/surfer/         build web Surfer (diunduh oleh skrip, di-gitignore)
│  └─ src/
│     ├─ pages/              Dashboard, Exercises, Exercise, Workspace, Projects, Tapeout
│     ├─ components/         Editor, FileTree, RunPanel, WaveView, FpgaPanel, FpgaReport, GdsView
│     └─ api/                client typed (dibuat dari OpenAPI backend)
├─ content/
│  ├─ exercises/<id>/        soal langkah 1 (format: docs/CONTENT-FORMAT.md)
│  ├─ projects/<id>/         proyek terpandu langkah 4
│  └─ boards/<id>.yaml       profil board FPGA
├─ tools/
│  ├─ grader/                grade.py, check_content.py (sudah jalan)
│  └─ flash/smartx-flash    helper flashing di host (Python stdlib + openFPGALoader; README untuk instalasi)
└─ data/                     runtime, di-gitignore
```

## Model data (SQLite)

- **Project**: `id, name, kind (exercise|sandbox|guided|tt), source (exercise_id/project_id), created_at`
- **File**: `project_id, path, content, updated_at`. File proyek disimpan di DB supaya autosave sederhana; saat run, file ditulis ke folder run.
- **Folder**: `project_id, path`. Setiap folder di tree punya baris (termasuk induk setiap file), jadi folder kosong tetap ada. Path divalidasi di `app/projects/paths.py` dan unik tanpa membedakan huruf besar/kecil.
- **Run**: `id, project_id, kind, status, params (JSON), result (JSON), tool_versions (JSON), created_at, started_at, finished_at, exit_code, error`
- **ExerciseProgress**: `exercise_id, status, attempts, last_code, solved_at, hints_opened`

Status run: `queued → running → succeeded | failed | cancelled | timeout`.

## Jenis job

| kind | Image | Kelas | Input | Output utama |
|---|---|---|---|---|
| `grade` | light | light | kode user + folder soal | `result.json` (test, diagnostics Icarus, lint Verilator), `.fst` |
| `lint` | light | light | salinan file proyek (`project/`) + config | `lint.sarif` → diagnostic (file, baris, kolom, severity, kode, pesan) |
| `sim` | light | light | salinan file proyek (`project/`) + `sim.json` (config) | `result.json` (test per modul, error kompilasi, versi simulator), `.fst` |
| `fpga` | light | light | salinan file proyek (`project/`) + `fpga.json` (perintah tiap tahap dari profil board) | `result.json` (status per tahap, error pertama, diagnostics Yosys, versi tool); `collect()` menambah warning sintesis, utilisasi, Fmax, dan jalur kritis (`app/reports/`); `build/`: bitstream, `report.json` nextpnr, `stat`, log per tahap |
| `asic` | ASIC_IMAGE | heavy | file + `config.yaml` + PDK | GDS, metrics, laporan, PNG layout |
| `tt_harden` | ASIC_IMAGE | heavy | repo TT hasil generator | GDS TT, warning |

Setiap jenis job adalah satu modul di `backend/app/jobs/kinds/` dengan `JOB_CLASS`, `OK_EXIT_CODES`, model `Params`, serta dua fungsi: `prepare(run_dir, params, ctx) -> ContainerSpec` dan `collect(run_dir) -> dict`. `ctx` (`JobContext`) memberi akses ke settings dan katalog soal. Ini membuat jenis job baru mudah ditambah dan mudah dites tanpa Docker (test unit untuk `prepare` dan `collect` memakai folder fixture).

## Docker runner

- Pakai Python `docker` SDK lewat `/var/run/docker.sock` yang di-mount ke container backend.
- Setiap job: `docker run --rm --network none --user <uid>:<gid> --memory <limit> --cpus <n> --pids-limit 512`, mount `data/runs/<id>` sebagai `/work` (rw). Mount lain diminta lewat `ContainerSpec`: `tools/` di `/tools` (ro), subfolder run yang di-mount ulang read-only, dan `content/` di `/content` (ro). Job yang menjalankan kode user **tidak boleh** me-mount `content/`, karena di sana ada `solution.v`; file soal yang dibutuhkan disalin ke folder run.
- Path folder run harus berupa path di **host**, karena container job dibuat oleh daemon host. Simpan `SMARTX_DATA_DIR` host di config dan terjemahkan path.
- Log stdout/stderr dibaca streaming dan ditulis ke `run.log` serta diteruskan ke SSE.
- Timeout per kelas (`JOB_LIGHT_TIMEOUT_S`, `JOB_HEAVY_TIMEOUT_S`). Saat timeout atau cancel: `container.kill()`, status `timeout`/`cancelled`.
- Saat backend start: run berstatus `running`/`queued` diubah ke `failed` dengan error "backend restarted".

## API (ringkas)

```
GET  /api/health
GET  /api/exercises                       daftar + progres
GET  /api/exercises/{id}                  teks, starter/kode terakhir, hint terbuka
POST /api/exercises/{id}/runs             {code} -> run
POST /api/exercises/{id}/hints/next
GET  /api/exercises/{id}/solution         403 sampai syarat terpenuhi

GET  /api/project-templates
GET  /api/snippets                        snippet testbench cocotb (content/snippets/*.yaml)
GET  /api/lessons?step=2                  materi singkat (content/lessons/*.md)
GET  /api/projects | POST /api/projects       {name, template | exercise_id}
GET | PATCH | DELETE /api/projects/{id}       detail + tree | ganti nama | hapus
POST /api/projects/{id}/files                {path, content} (409 kalau sudah ada)
GET | PUT | DELETE /api/projects/{id}/files/{path}   PUT = simpan (autosave), DELETE folder = rekursif
POST /api/projects/{id}/folders              {path}
POST /api/projects/{id}/move                 {from_path, to_path}: ganti nama/pindah file atau folder
GET | PUT /api/projects/{id}/config           smartx.yaml: teks + hasil parse + masalah | simpan dari form
POST /api/projects/{id}/config/check          {text}: periksa YAML yang sedang diketik (tidak disimpan)
POST /api/projects/{id}/runs              {kind: lint|sim|fpga}: salin file proyek ke folder run, ambil params dari smartx.yaml
GET  /api/projects/{id}/runs?limit=50     riwayat: waktu, jenis, status, durasi, ringkasan (terbaru dulu)
GET  /api/projects/{id}/runs/compare?a=&b=  test yang berubah status antara dua simulasi
GET  /api/projects/{id}/runs/{run_id}     run + hasil sesuai jenisnya (lint, sim)
GET  /api/runs/{id}
GET  /api/runs/{id}/events                SSE: log, status
POST /api/runs/{id}/cancel
GET  /api/runs/{id}/files/{path}          artefak (cegah path traversal!)

GET  /api/boards                          profil board FPGA + template constraint + perintah flash (content/boards/)
POST /api/projects/{id}/tapeout/generate
```

Frontend memakai client yang di-generate dari OpenAPI backend (`openapi-typescript`), supaya tipe tidak ditulis dua kali.

## Waveform viewer

Pakai **Surfer** versi web (WASM), di-host sendiri di `frontend/public/surfer/` dan ditampilkan lewat `<iframe>`. Surfer mendukung pemuatan file lewat URL dan kontrol lewat `postMessage`; API-nya didokumentasikan di `surfer/assets/integration.js` di repo Surfer dan masih bisa berubah, jadi bungkus semua interaksi di satu komponen `WaveView` dan pin versi Surfer yang dipakai.

Fallback jika integrasi bermasalah: tombol unduh `.fst` untuk dibuka di GTKWave/Surfer desktop.

## Viewer layout GDS

Fase 5 cukup memakai PNG yang dirender KLayout dalam mode batch (`klayout -zz -r render.py`) di container ASIC, dengan beberapa level zoom. Viewer interaktif (misalnya konversi GDS → glTF untuk tampilan 3D) adalah ekstensi opsional.

## Keamanan (single user)

- Backend bind ke `127.0.0.1` secara default. Akses dari jaringan lain harus lewat reverse proxy yang punya autentikasi.
- Akses ke Docker socket setara root di host. Ini diterima karena aplikasi ini pribadi, tapi tetap: job container tidak pernah mendapat socket, selalu `--network none`, dan tidak berjalan `--privileged`.
- Semua path dari user dinormalisasi dan dicek tetap di dalam folder proyek/run.

## Kebutuhan mesin

| Fase | CPU | RAM | Disk |
|---|---|---|---|
| 0–4 | 2 core | 4 GB | ~5 GB (image toolchain ~2 GB) |
| 5–6 | 4+ core | 12–16 GB | +25 GB (image ASIC ~4 GB + PDK + hasil run) |
