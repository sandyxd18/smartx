# Catatan keputusan (ADR ringkas)

Setiap keputusan penting dicatat di sini: konteks singkat, pilihan, alasan. Keputusan bertanda **[KONFIRMASI]** dibuat sebagai default dan sebaiknya dicek pemilik proyek. Tambahkan entri baru di bawah; jangan hapus entri lama, tandai sebagai digantikan.

## D01. Aplikasi web lokal, bukan desktop app
Browser + backend di Docker. Alasan: tool EDA hanya berjalan baik di Linux; dengan web UI, aplikasi bisa dijalankan di VM/server dan dibuka dari laptop mana pun. Tidak perlu Electron.

## D02. Backend Python (FastAPI) + SQLite
cocotb, parser laporan, dan LibreLane semuanya Python, jadi satu bahasa untuk backend dan tooling. SQLite cukup untuk satu pengguna; tidak perlu Postgres/Redis. Antrian job memakai `asyncio` di dalam proses backend, tanpa Celery.

## D03. Frontend React + Vite + TypeScript, editor Monaco
Monaco punya dukungan Verilog/SystemVerilog lewat konfigurasi bahasa Monarch dan sudah umum dipakai.

## D04. Satu container per job lewat Docker socket
Isolasi, batas resource, dan versi tool yang konsisten. Alternatif (subprocess di container backend) lebih cepat sedikit tapi mencampur dependency backend dengan tool EDA dan menyulitkan image ASIC yang besar.

## D05. Toolchain digital dari OSS CAD Suite, dipin per tanggal
Paket apt Ubuntu untuk Yosys/nextpnr tertinggal jauh. OSS CAD Suite memberi satu bundel konsisten; tanggal rilis dipin di `.env`.

## D06. ASIC flow memakai LibreLane, bukan OpenLane 1
OpenLane 2 dilanjutkan di bawah FOSSi Foundation dengan nama LibreLane (rilis Juli 2025). Tiny Tapeout memakai alur berbasis LibreLane. Konfigurasi OpenLane lama masih kompatibel.

## D07. Image ASIC: IIC-OSIC-TOOLS (pin tag) **[KONFIRMASI di Fase 5]**
Image all-in-one dari JKU (~4 GB) berisi PDK SKY130/GF180/IHP dan tool digital/analog. Saat Fase 5 dimulai, cek apakah versi LibreLane di dalamnya sesuai kebutuhan `tt-support-tools` shuttle yang dituju. Jika tidak, pakai image/metode instalasi resmi LibreLane.

## D08. Board FPGA default: Tang Nano 9K **[KONFIRMASI]**
Murah, mudah didapat, didukung toolchain open-source (Yosys + nextpnr-himbaechel + Apicula + openFPGALoader). iCE40 (iCEBreaker/UPduino) jadi target kedua karena paling matang di ekosistem open-source. Ganti jika pemilik sudah punya board lain.

## D09. Flashing FPGA di host, bukan di container
Passthrough USB ke Docker rapuh (terutama di WSL/macOS). Backend hanya menghasilkan bitstream; skrip `tools/flash/smartx-flash` di host memanggil `openFPGALoader`.

## D10. Waveform: Surfer web, di-host sendiri
Surfer berjalan di browser (WASM), bisa di-embed lewat iframe dan dikontrol dengan `postMessage`. API-nya belum stabil, jadi versi dipin dan integrasi dibungkus satu komponen.

## D11. Konten soal ditulis sendiri
Soal HDLBits tidak disalin. Semua soal di `content/` adalah tulisan sendiri, dengan solusi dan testbench yang diuji otomatis (`make check-content`).

## D12. Tapeout lewat Tiny Tapeout, submit manual
Aplikasi membuat repo yang sesuai template TT dan menjalankan hardening lokal. Submit dan pembayaran di app.tinytapeout.com tetap manual. Shuttle (SKY/IHP/GF) dipilih lewat profil yang mudah diperbarui karena tiap shuttle punya branch `tt-support-tools` sendiri.

## D13. Host pengembangan: Windows native, make lewat bash Git for Windows
Pemilik menjalankan proyek langsung di Windows (bukan WSL). GNU Make dipasang dari winget (`ezwinports.make`). Di Windows, Makefile memakai `C:/Progra~1/Git/bin/bash.exe` sebagai `SHELL` (bisa di-override lewat `GIT_BASH`) supaya resep bash yang sama jalan dari PowerShell maupun Git Bash, dan mengekspor `MSYS_NO_PATHCONV=1` agar path container seperti `/work` tidak diubah jadi path Windows. `PY` default `python` di Windows karena `python3` di sana biasanya stub Microsoft Store. `.gitattributes` memaksa LF karena file dipakai di container Linux.

## D14. Perbaikan image toolchain (Fase 0)
Diuji dengan OSS CAD Suite `2026-10-24` (Yosys 0.70+219, Icarus 14.0 devel, Verilator 5.053 devel, nextpnr 0.11.1, cocotb 2.1.0). Nama file rilis sesuai dugaan Dockerfile. Dua perbaikan:
- cocotb butuh `libpython3.12.so`, yang tidak ikut paket `python3` di Ubuntu 24.04; ditambahkan `libpython3.12t64`. Tanpa ini semua soal berstatus `compile_error` ("Unable to find libpython").
- `ubuntu:24.04` sudah punya user `ubuntu` dengan UID 1000, sehingga `useradd -u 1000` gagal diam-diam karena `|| true`. User `ubuntu` dihapus dulu, lalu `smartx` dibuat tanpa `|| true`.

Tanggal yang sudah teruji ditulis di `.env.example`, jadi clone baru memakai versi yang sama. `make pin-toolchain` tetap ada untuk naik versi dengan sengaja; setelah naik, jalankan `make check-content`.

## D15. Kerangka backend (Fase 0 task 2)
- Dependency dan venv dikelola `uv` (`backend/pyproject.toml` + `uv.lock` di-commit, Python 3.12 lewat `.python-version`). Versi aplikasi satu sumber: `app/__init__.py`.
- Aplikasi dibuat lewat factory `create_app(settings)` (`uvicorn --factory app.main:create_app`) supaya test bisa memberi `Settings` dan folder data sendiri.
- Path relatif di `SMARTX_DATA_DIR` diselesaikan terhadap root repo, bukan cwd.
- Tabel dibuat dengan `SQLModel.metadata.create_all`, belum ada migrasi. Kalau skema mulai berubah setelah ada data yang perlu dijaga, tambahkan Alembic.
- `Run.id` berupa uuid4 hex (bukan integer) agar folder `data/runs/<id>` tidak bentrok setelah database direset.
- Status Docker di `/api/health` diambil lewat dependency `get_docker_probe`, yang diganti probe palsu di test. Probe tidak pernah melempar error: kalau Docker mati, health tetap 200 dengan `docker.available=false`.
- Starlette 1.x memberi peringatan bahwa `httpx` untuk `TestClient` digantikan `httpx2`. Untuk sekarang tetap `httpx` (sesuai rencana fase) dan peringatan itu saja yang diredam di konfigurasi pytest; peringatan lain dijadikan error. Pindah ke `httpx2` setelah paketnya dicek.

## D16. Job system (Fase 0 task 3)
- Antrian memakai dua `asyncio.Semaphore` (light/heavy) di dalam proses backend, tanpa broker. Job kind menentukan kelasnya lewat konstanta `JOB_CLASS`; image dan batas resource diambil `DockerRunner` dari kelas itu (light → `TOOLCHAIN_IMAGE`, heavy → `ASIC_IMAGE`). Karena itu `prepare(run_dir, params)` tidak perlu tahu nama image.
- Hardening container, selain yang tertulis di ARCHITECTURE: `cap_drop=ALL`, `no-new-privileges`, dan `memswap_limit` sama dengan `mem_limit` (tanpa swap tambahan). Tiap container diberi label `smartx.run_id`. Saat startup, semua container berlabel itu dihapus, karena backend yang baru tidak bisa melanjutkan job lama.
- Di Windows tidak ada `os.getuid()`, jadi container job berjalan sebagai `1000:1000` (user `smartx` di image). Bisa diatur lewat `JOB_USER`.
- Client Docker untuk stream log dan `wait` dibuat tanpa read timeout. Default docker-py 60 detik akan memutus stream log job yang diam lebih lama dari itu. Batas waktu job diatur oleh queue (`JOB_*_TIMEOUT_S`).
- Saat backend dimatikan dengan rapi, container yang masih berjalan di-kill, tetapi status run dibiarkan `running`. Saat start berikutnya, pemulihan menandainya `failed` dengan pesan yang sama seperti setelah crash, jadi kedua jalur berakhir di satu perilaku.
- `kind=echo` menerima `sleep_s` (int 0–600, divalidasi ketat) untuk menguji cancel dan timeout dari UI tanpa membuat jenis job khusus test.
- Pesan error run untuk pengguna ditulis dalam bahasa Indonesia, termasuk pesan pemulihan ("Backend di-restart saat run ini belum selesai.").
- Test dengan Docker asli ada di `backend/tests/integration/` dan hanya jalan jika `SMARTX_DOCKER_TESTS=1`. Unit test tetap memakai `FakeRunner`.

## D17. API run dan SSE (Fase 0 task 4)
- `POST /api/runs` sementara hanya menerima `kind=echo`. Parameter divalidasi oleh model `Params` milik job kind sebelum run dibuat, jadi input salah langsung dapat 422 dan tidak menjadi run `failed`. Setiap job kind wajib punya `Params`.
- SSE `GET /api/runs/{id}/events` mengirim event `log` (`{"line"}`) dan `status` (`{"status"}`) dalam JSON. Stream dimulai dengan replay isi `run.log` dan status terkini, lalu meneruskan event live sampai status akhir, kemudian ditutup. Tidak ada event ganda atau hilang karena queue menulis log, memperbarui status, dan mem-publish event tanpa `await` di antaranya, dan follower mengambil snapshot dengan cara yang sama (lihat `app/jobs/stream.py`). Ping tiap 15 detik.
- `run.log` selalu ditulis dengan LF, juga di Windows.
- Timestamp di respons API selalu berzona UTC, karena SQLite membuang info zona waktu dan browser akan membacanya sebagai waktu lokal.
- Path artefak lewat `app/paths.py::safe_join`. Yang ditolak (400): segmen `..`, path absolut, drive Windows, UNC, NUL, dan symlink yang mengarah keluar folder run. Backslash diperlakukan sebagai pemisah. `run_id` harus 32 hex, jadi tidak bisa dipakai untuk traversal. Test symlink di-skip di Windows tanpa Developer Mode.

## D18. Kerangka frontend (Fase 0 task 5)
- Vite 8, React 19, React Router 8 (paket `react-router`), Tailwind 4 lewat `@tailwindcss/vite`. Test memakai Vitest 5, jsdom, dan Testing Library. ESLint 10 flat config dengan typescript-eslint (type-checked) dan `--max-warnings 0`.
- TypeScript dipin `~5.9.3`, bukan 7.x: typescript-eslint 8.72 hanya mendukung `<6.1` dan openapi-typescript 7 mensyaratkan `^5`. Naikkan setelah keduanya mendukung versi baru.
- Client API: `openapi-typescript` membuat `src/api/schema.d.ts` (di-commit) dan `openapi-fetch` memakainya. `npm run gen:api` mengambil skema dengan `uv run python -m app.openapi_dump` di `backend/`, jadi tidak perlu server yang menyala. Setelah mengubah API backend, jalankan `npm run gen:api`.
- Port: browser hanya membuka Vite di `SMARTX_PORT` (8080). Vite mem-proxy `/api` ke backend di `SMARTX_API_URL` (default `http://127.0.0.1:8000`). Akibatnya backend tidak lagi memakai `SMARTX_PORT`; penyesuaian `.env` dan compose dikerjakan di task 6.
- `useRunEvents` mengosongkan log setiap kali `EventSource` (re)connect, karena server memutar ulang seluruh log di setiap koneksi. Stream ditutup dari sisi klien saat status akhir, supaya browser tidak reconnect otomatis.
- Status 502–504 dari proxy dev ditampilkan sebagai "Backend tidak bisa dihubungi", dengan tombol "Periksa lagi". Ditemukan saat uji di browser: frontend sering siap lebih dulu daripada backend.
- `.claude/launch.json` berisi konfigurasi `backend` (port 8000) dan `frontend` (port 8080) untuk preview di Claude Code.

## D19. Compose, perintah make, dan Surfer (Fase 0 task 6)
- `make dev` menjalankan `docker compose up --build --renew-anon-volumes`. `backend` (uvicorn `--reload`, tidak dipublikasikan ke host) memegang Docker socket. `frontend` (Vite) dipublikasikan di `${SMARTX_BIND}:${SMARTX_PORT}`, default `127.0.0.1:8080`, dan baru start setelah healthcheck backend hijau. Image dasar dipin: `python:3.12.15-slim-bookworm` + `uv==0.13.0`, dan `node:24.22.1-bookworm-slim`.
- Makefile mengekspor `SMARTX_HOST_DIR=$(CURDIR)`. Compose meneruskannya sebagai `SMARTX_HOST_DATA_DIR`/`SMARTX_HOST_CONTENT_DIR`, sehingga container job yang dibuat backend dari dalam container mendapat path host (di Windows: `C:/Users/.../data/runs/<id>`). Sudah diuji: echo dan cancel lewat compose.
- Backend di compose berjalan sebagai root, karena perlu socket Docker. Agar job tidak ikut jalan sebagai root: `default_job_user()` jatuh ke `1000:1000` kalau backend ber-uid 0, `JOB_USER` menolak uid 0, dan folder run di-`chown` ke user job kalau backend root. Di Linux, Makefile mengisi `JOB_USER` dengan uid:gid pemanggil.
- Di Windows, bind mount tidak meneruskan event perubahan file. Karena itu uvicorn memakai `WATCHFILES_FORCE_POLLING` dan Vite memakai polling (`SMARTX_WATCH_POLLING`). `node_modules` frontend tinggal di volume container, karena milik host berisi binary Windows.
- `make test`/`make lint` berjalan di host (uv + npm). `make check` = lint + test + `test-docker` + `check-content`. Lint frontend juga gagal kalau `schema.d.ts` tidak sesuai dengan API backend (`gen:api --check`). Test backend menghapus variabel `.env` dari environment, karena Makefile mengekspornya.
- Surfer: rilis Surfer hanya berisi binary native, dan build web hanya ada sebagai artefak CI yang kedaluwarsa dalam satu jam. Jadi `make surfer` membangun build web dari tag yang dipin (`SURFER_VERSION=v0.7.0`, `rust:1.99.1-bookworm`, trunk v0.21.14) dengan langkah yang sama seperti job CI `pages_build` milik Surfer, lalu mengekspornya ke `frontend/public/surfer/` (di-gitignore, ±13 MB). Build pertama sekitar 4 menit. Sudah dicek: viewer termuat dari `/surfer/index.html` tanpa error, dan `integration.js` (API `postMessage`) ikut terbawa.
- Catatan Windows: setelah `docker compose down`, Docker Desktop bisa menahan port 8080 selama beberapa puluh detik (`EADDRINUSE` tanpa listener yang terlihat).

## D20. Content loader (Fase 1 task 1)
- `app/content/` memvalidasi `exercise.yaml` dengan Pydantic (`extra="forbid"`, jadi salah ketik nama field langsung ketahuan). Aturannya: `id` kebab-case dan sama dengan nama folder, `files.*` harus nama file polos yang ada di folder soal (tanpa `/`, `\`, `..`, atau file tersembunyi), dan setiap `requires` harus menunjuk soal yang ada.
- Soal yang tidak valid dilewati dan dicatat di `catalog.errors` serta log. Aplikasi tetap jalan dengan soal-soal lain.
- Reload tanpa watcher: setiap kali katalog diakses, mtime dan ukuran semua `exercise.yaml` dibandingkan dengan sebelumnya. Untuk puluhan soal biayanya kecil, dan cara ini tetap bekerja di bind mount Docker Desktop di Windows yang tidak meneruskan event perubahan file. Teks soal dan starter selalu dibaca dari disk saat diminta. Bisa dimatikan dengan `SMARTX_CONTENT_RELOAD=false`.
- Urutan soal: `step`, lalu `order` (soal tanpa `order` di akhir), lalu `id`. Pengelompokan per topik ditentukan di halaman daftar (task 4).
- Test `test_repo_content_is_valid` memuat folder `content/` asli, jadi soal yang metadatanya rusak membuat `make test` gagal, tidak hanya `check-content`.
