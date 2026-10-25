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

## D21. Job `grade` (Fase 1 task 2)
- **Soal tidak di-mount dari `content/`.** Rencana fase menyebut "mount soal read-only", tetapi `content/` berisi `solution.v`, dan kode Verilog user bisa membacanya dengan `$fopen` lalu mencetaknya ke log. Karena itu `prepare()` hanya menyalin `exercise.yaml` dan testbench ke `run/exercise/`, yang lalu di-mount read-only di `/exercise`. Kode user ditulis ke `run/user.v`. Test integrasi `test_grade_cannot_read_solution` memastikan `$fopen` ke solusi gagal. Default `ContainerSpec.mount_content` sekarang `False`.
- Grader diambil dari `tools/` yang di-mount read-only di `/tools` (bukan dibakar ke image), jadi aplikasi dan `make check-content` selalu memakai grader yang sama. Compose meneruskan `SMARTX_HOST_TOOLS_DIR`.
- Interface job kind: `prepare(run_dir, params, ctx)` dengan `JobContext` (settings + katalog), `OK_EXIT_CODES` per kind, dan `JobInputError` untuk input yang lolos validasi tetapi tidak bisa dipakai (misalnya soal tidak ada). Grader keluar dengan kode 1 saat test gagal; itu hasil penilaian, bukan job rusak, jadi run tetap `succeeded` dan putusannya ada di `result.status` (`pass`/`fail`/`compile_error`/`error`).
- Timeout grade = `timeout_s` soal + 30 detik (start container, kompilasi, startup cocotb), lewat `ContainerSpec.timeout_s`.
- `collect()` memetakan `wave_file` dari path container (`/work/...`) ke path relatif folder run dan `wave_url` (`/api/runs/<id>/files/...`). Path yang tidak berada di bawah `/work`, mengandung `..`, atau filenya tidak ada, diabaikan.
- Error kompilasi Icarus diurai menjadi `diagnostics: [{line, severity, message}]`, hanya untuk `dut.v` (salinan kode user). Pesan dari modul dump milik cocotb (`cocotb_iverilog_dump.v`) dibuang. Icarus sering melaporkan error di baris *setelah* kesalahan sebenarnya (misalnya titik koma yang hilang), dan bisa memberi beberapa pesan untuk satu baris; nomor barisnya diteruskan apa adanya.
- Fixture `collect()` (`tests/fixtures/runs/grade-*`) diambil dari keluaran grader yang asli di image toolchain. `.gitignore` mengecualikan `sim_build/` dan `*.fst` di folder fixture.

## D22. API exercises dan progres (Fase 1 task 3)
- Endpoint sesuai ARCHITECTURE. `GET /api/exercises/{id}` mengembalikan teks soal, starter, `code` (kode terakhir yang di-Run, atau starter), hanya hint yang sudah dibuka, `solution_available`, dan `last_run`, sehingga UI bisa menampilkan hasil terakhir setelah halaman di-refresh.
- Setiap Run menambah `attempts` dan menyimpan `last_code` dalam transaksi yang sama dengan pembuatan run, termasuk run yang gagal kompilasi. Status menjadi `attempted`, lalu `solved` lewat hook `on_finished` di `JobQueue`. Hook ini dipanggil setelah status akhir disimpan dan sebelum event SSE dikirim, jadi saat UI menerima status akhir, progres sudah benar. `solved` tidak pernah turun lagi, dan `solved_at` adalah waktu pertama kali lulus.
- Solusi (`GET .../solution`) adalah satu-satunya jalan `solution.v` keluar. Endpoint ini menjawab 403 sampai soal lulus atau `attempts >= SOLUTION_UNLOCK_ATTEMPTS` (default 5). Test memakai penanda di `solution.v` dan memastikan penanda itu tidak muncul di respons endpoint lain.
- `POST .../hints/next` membuka hint berikutnya. Kalau semua hint sudah terbuka, endpoint ini tidak mengubah apa pun (tetap 200).
- Run terakhir sebuah soal dicari lewat `params.exercise_id` (JSON di SQLite), jadi skema tabel tidak berubah dan belum perlu migrasi.
- Diukur lewat compose (API, belum lewat UI): grade `counter-4bit` butuh 1,0–1,9 detik dari POST sampai status akhir.

## D23. Halaman daftar soal (Fase 1 task 4)
- Soal dikelompokkan menurut **topik pertama** (`combinational`, `sequential`, `fsm`, `pitfalls` → Kombinasional, Sekuensial, FSM, Jebakan umum), dengan urutan grup mengikuti kurikulum. Di dalam grup, urutannya sama dengan API (step, order, id). Konvensi ini dicatat di CONTENT-FORMAT, bagian "Topik".
- Label status mengikuti rencana fase: `not_started` = "Belum", `attempted` = "Gagal", `solved` = "Lulus". Jumlah percobaan ditampilkan di sampingnya. Level 1–3 = Dasar, Menengah, Lanjut.
- Filter (teks, status, level) disimpan di query string (`?q=&status=&level=`), sehingga tetap berlaku setelah refresh dan bisa dibagikan sebagai tautan.
- `/latihan/:id` sementara menampilkan placeholder sampai halaman soal dibuat di task 5.

## D24. Halaman soal dan editor (Fase 1 task 5)
- Monaco di-host sendiri, bukan dari CDN (bawaan `@monaco-editor/react`), supaya aplikasi tetap jalan tanpa internet. Yang dimuat hanya fitur editor (`monaco-editor/features/register.all`), grammar Monarch Verilog/SystemVerilog bawaan Monaco (`languages/definitions/systemverilog/register`), dan `editor.worker`. Layanan bahasa TS/CSS/HTML/JSON dari `editor.main` sengaja tidak dimuat. Halaman soal adalah lazy route, jadi chunk Monaco (~4 MB, gzip ~1 MB) hanya dimuat saat soal dibuka.
- `monaco-editor` 0.57.0 mengunci `dompurify` 3.4.15, yang terkena advisory XSS kritis (GHSA-p98j-92pf-mc4p dan kawan-kawan). `package.json` memaksa `dompurify` 3.4.17 lewat `overrides`. Hapus override ini setelah Monaco merilis versi dengan dompurify yang sudah diperbaiki. `@tailwindcss/typography` tidak dipakai, karena mengunci `postcss-selector-parser` yang rentan; teks soal ditata dengan CSS sendiri (`.markdown` di `index.css`).
- Teks soal di-render dengan `react-markdown` + `remark-gfm` (untuk tabel), tanpa HTML mentah. H1 di awal README dibuang, karena judul halaman sudah diambil dari `exercise.yaml`.
- Hasil grade di API bertipe `GradeResult` (Pydantic; dipakai juga oleh `collect()`), dengan `ExerciseRunRead.grade` dan endpoint `GET /api/exercises/{id}/runs/{run_id}`. Dengan begitu frontend tidak perlu menulis tipe hasil secara manual.
- **Bug yang ditemukan saat uji di browser:** Ctrl+Enter yang ditekan sesaat setelah mengetik mengirim kode *lama*. Monaco sudah berisi teks baru, tetapi React belum me-render ulang, sehingga state `code` masih versi sebelumnya. Perbaikannya: `onRun` menerima isi model Monaco saat itu (`editor.getValue()`), dan nilai itu yang dipakai. Ada test regresinya.
- Penanda error memakai `diagnostics` dari grader sebagai `setModelMarkers`; nomor baris di luar jangkauan dijepit ke baris terakhir. Penanda tetap ada sampai Run berikutnya.
- Di layar sempit (< `lg`), soal ditampilkan di atas editor; di layar lebar, keduanya berdampingan.
- Diukur di browser (backend di host, data terpisah): waktu dari klik Run sampai hasil tampil 1,2–1,7 detik untuk `counter-4bit`.

## D25. Autosave kode (Fase 1 task 6)
- `PUT /api/exercises/{id}/code` (204) menyimpan `last_code` saja. Tidak menghitung percobaan, tidak mengubah status, dan tidak membuka solusi; yang dihitung sebagai percobaan hanya Run.
- `useAutosave` menyimpan 1 detik setelah ketikan terakhir. Penyimpanan dijalankan berurutan (promise chain), jadi draf lama tidak bisa mendarat setelah draf baru. Hanya editan user (mengetik, reset ke starter) yang memicu penyimpanan; memuat halaman tidak.
- Perubahan yang belum tersimpan di-flush saat `pagehide`, saat `visibilitychange` menjadi hidden, dan saat komponen unmount (pindah halaman di dalam aplikasi), memakai `fetch` dengan `keepalive: true` supaya request tetap terkirim walaupun halaman ditutup atau di-refresh. Diuji di browser: mengetik lalu langsung reload (sebelum jeda 1 detik) tetap menyimpan kode, dengan tepat satu PUT.
- Kalau penyimpanan gagal, ditampilkan "Gagal menyimpan"; ketikan berikutnya mencoba lagi dengan teks terbaru. Belum ada retry otomatis tanpa ketikan.

## D26. WaveView (Fase 1 task 7)
- `WaveView` memuat build Surfer dari `make surfer` dalam iframe (`/surfer/index.html#dev`). `#dev` adalah opsi bawaan Surfer untuk tidak mendaftarkan service worker. Service worker itu tidak menyimpan cache, tetapi akan mencegat semua request dari iframe dan menambahkan header COEP/COOP; Surfer berjalan normal tanpanya.
- File dimuat lewat API yang terdokumentasi di `integration.js` v0.7.0: `postMessage({command: "LoadUrl", url})`. Listener pesan sudah terpasang sebelum WASM siap, tetapi `inject_message` baru ada setelahnya, sehingga pesan yang dikirim terlalu cepat hilang. Karena iframe satu origin, `WaveView` menunggu sampai `inject_message` ada (polling 100 ms, maksimal 20 detik) sebelum mengirim. Kalau tidak siap, pengguna diarahkan ke tombol unduh `.fst`.
- Ketersediaan Surfer dicek dari isi `/surfer/SURFER_VERSION`, bukan status HTTP, karena dev server Vite menjawab path yang tidak ada dengan `index.html` (200). Kalau belum terpasang, halaman menyarankan `make surfer`.
- Run baru memuat waveform baru ke viewer yang sama (tanpa reload). Tab Waveform tetap terpasang setelah dibuka, sehingga berpindah tab tidak memuat ulang WASM. Selama run berjalan, waveform sebelumnya tetap tampil. Panel hasil menjadi lebih tinggi (32rem) saat tab Waveform aktif. Test menangkap bug pengiriman ganda saat viewer baru siap; diperbaiki dengan mencatat URL yang terakhir dikirim.
- Diuji di browser: dari starter sampai lulus `counter-4bit` lewat UI (3/3 test, 1,9 detik), lalu tab Waveform memuat `.fst` dari run itu di Surfer, dan sinyal `clk`, `en`, `q[3:0]`, `rst` tampil.
- Belum dilakukan: Surfer tidak otomatis menampilkan sinyal; pengguna memilih scope lalu menekan "+". Menambahkan sinyal secara otomatis membutuhkan `InjectMessage` dengan enum `Message` Surfer, yang menurut `integration.js` belum stabil, jadi ditunda.

## D27. 22 soal baru (Fase 1 task 8)
- Rencana fase menyebut "19 soal lagi", tetapi tabel kurikulum di CONTENT-FORMAT berisi 23 baris (termasuk `counter-4bit`). Semua baris ditulis, jadi ada **22 soal baru, total 23**. Itu memenuhi "minimal 20" tanpa harus memilih tiga soal untuk dibuang.
- Baris "D flip-flop (reset sinkron/asinkron)" dibagi dua: reset **asinkron** di `dff-async-reset`, reset **sinkron** di `register-8bit`. Masing-masing punya test yang menggagalkan jenis reset yang salah.
- Selain "solusi lulus, starter gagal", setiap soal kunci diuji dengan **implementasi keliru yang masuk akal**, dan semuanya harus gagal: reset sinkron di soal asinkron dan sebaliknya, Moore di soal Mealy dan sebaliknya, priority encoder dengan bit terendah menang, debouncer 3 siklus, hijau 3 siklus. Test Moore/Mealy memeriksa `z` sebelum (Mealy) atau setelah (Moore) sisi naik clock. Periode LFSR (taps 8,6,5,4) dicek maksimal (255) oleh generator sebelum soal ditulis.
- Tiga soal "jebakan umum" berisi kode buggy yang bisa dikompilasi (latch tak sengaja, blocking `=` di pipeline, dua `assign` ke satu wire), dan pesan gagalnya menunjuk ke penyebabnya.
- Grader (`tools/grader/grade.py`, `clean_message`) membuang introspeksi assertion yang ditempelkan cocotb (`assert 1 == 0`, `+ where ...`) setelah pesan penulis test, karena membingungkan pemula. Ada test-nya di `backend/tests/test_grader_messages.py`.
- `counter-4bit` diberi `order: 30` dan `requires: [register-8bit]` agar urut di grup Sekuensial.
- `make check-content` sekarang butuh sekitar 3 menit (23 soal × 2 run). Kalau mengganggu, jalankan soal secara paralel di grader.
- Frontend: root route punya `hydrateFallbackElement` ("Memuat halaman…"). Tanpa itu, membuka halaman soal lewat URL langsung menampilkan layar putih selama lazy route (Monaco) dimuat, beberapa detik pada dev server yang baru menyala. Test halaman soal memuat modulnya di `beforeAll`, karena dua test pertama sempat gagal (timeout `findBy`) saat mesin sibuk.

## D28. Verilator lint pada Run (Fase 1 task 9)
- Lint berjalan **di dalam job `grade` yang sama**, sebelum kompilasi Icarus, bukan sebagai job atau container terpisah. `verilator --lint-only` untuk satu file kecil butuh sekitar 60 ms, sedangkan container baru menambah sekitar 1 detik. Job `lint` tersendiri tetap direncanakan untuk workspace (Fase 2), dan parser-nya (`app/jobs/verilator_lint.py`) bisa dipakai ulang.
- Perintah (flag dicek dengan `verilator --help` di image, Verilator 5.053): `verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-EOFNEWLINE -Wno-fatal --quiet --top-module <toplevel> dut.v`. `DECLFILENAME` dimatikan karena file selalu bernama `dut.v`. `EOFNEWLINE` dimatikan karena editor bisa menyimpan tanpa baris baru di akhir file. Grader menulis output mentahnya ke `lint_log` di `result.json`, dan backend mem-parse-nya menjadi `GradeResult.lint`: baris, kolom, kode warning, dan pesan.
- Lint hanya saran; hasil lulus/gagal tetap ditentukan simulasi. Semua temuan, termasuk `%Error` Verilator, ditampilkan sebagai **warning** (kuning). Kalau Verilator tidak ada atau crash, `lint_log` kosong dan penilaian berjalan seperti biasa. Untuk status `compile_error`, lint tidak ditampilkan karena Icarus sudah menandai baris yang rusak.
- Pesan diawali penjelasan singkat dalam Bahasa Indonesia untuk warning yang sering ditemui pemula (LATCH, CASEINCOMPLETE, BLKSEQ, COMBDLY, WIDTH*, UNDRIVEN, UNUSED*, MULTIDRIVEN*, dan lain-lain). Teks asli Verilator tetap disertakan supaya bisa dicari di internet.
- Monaco menggarisbawahi kata di kolom yang ditunjuk Verilator, bukan seluruh baris. Tab Tests menampilkan daftar "Peringatan Verilator".
- `check_content` sekarang juga mewajibkan `solution.v` bebas warning lint, karena solusi resmi adalah contoh yang ditiru pengguna. Ke-23 solusi yang ada sudah bersih. Aturan ini dibuktikan dengan solusi yang diberi sinyal tak terpakai: soal itu ditolak. Catatan: secara bawaan, Verilator mengabaikan sinyal yang namanya mengandung `unused`.
- Diuji di browser dengan Docker asli: starter `pitfall-latch` menampilkan warning LATCH di baris 10, dan kata `always` digarisbawahi. Waktu dari klik Run sampai hasil 2,7 detik.

## D29. Pembersihan container per instalasi (temuan review Fase 1)
- Saat review, satu test Docker (`test_sandbox_restrictions`) gagal. Penyebabnya, backend lain yang baru menyala menjalankan pemulihan startup dan menghapus **semua** container berlabel `smartx.run_id` di Docker, termasuk container test yang sedang berjalan. Ketika test itu lalu menghapus container miliknya sendiri, Docker menjawab `409 removal already in progress`, dan run yang sebenarnya sukses tercatat `failed`.
- Perbaikan 1: setiap container job diberi label `smartx.instance`, yaitu 16 karakter pertama SHA-256 dari lokasi data di host (`SMARTX_HOST_DATA_DIR` kalau ada, kalau tidak `data_dir` absolut). `remove_orphans` hanya menghapus container dengan instance yang sama. Dengan begitu `make dev`, compose, dan `make check` bisa memakai satu Docker tanpa saling mengganggu.
- Perbaikan 2: `cleanup` dan `remove_orphans` menganggap 404 (sudah terhapus) dan 409 (sedang dihapus pihak lain) sebagai berhasil. Error Docker lain tetap dilaporkan.
- Akibatnya, container sisa dari versi sebelum label ini tidak lagi dibersihkan otomatis. Kalau ada, hapus sekali dengan `docker rm -f $(docker ps -aq --filter label=smartx.run_id)`.

## D30. Proyek sandbox dan file tree (Fase 2 task 1)
- File proyek tetap di tabel `File` (lihat ARCHITECTURE). Folder disimpan di tabel baru `Folder`, satu baris per folder, termasuk induk setiap file. Dengan begitu folder kosong tidak hilang setelah file terakhirnya dihapus. Karena tabelnya baru, `create_all` membuatnya sendiri dan DB yang sudah ada tidak perlu migrasi.
- Path proyek divalidasi di `app/projects/paths.py`. Path harus relatif dengan `/` sebagai pemisah, tanpa segmen kosong, `.` atau `..`, dan tanpa backslash. Nama memakai huruf, angka, `_`, `-`, dan `.`, tidak diawali `.` dan tidak diakhiri `.`. Nama perangkat Windows (`con`, `nul`, `com1`, dan sejenisnya) ditolak. Panjang maksimal 200 karakter dan kedalaman maksimal 8 tingkat. Keunikan path dicek **tanpa membedakan huruf besar/kecil**, karena saat run file ditulis ke folder di host Windows. Ganti nama yang hanya mengubah huruf besar/kecil tetap boleh.
- Batas per proyek: 300 entri (file + folder) dan 500.000 karakter per file. Pelanggaran dijawab 422 dengan pesan berbahasa Indonesia, nama yang sudah dipakai dijawab 409.
- `PUT /files/{path}` menyimpan (dan membuat file kalau belum ada, untuk autosave). `POST /files` hanya membuat file baru (409 kalau sudah ada). `DELETE` pada folder menghapus seluruh isinya. Menghapus proyek ditolak (409) selama ada run `queued`/`running`; kalau tidak, run lama beserta foldernya ikut dihapus.
- Proyek dari template atau soal semuanya `kind = sandbox`, dengan `source = "template:<id>"` atau `"exercise:<id>"`. Template ditulis sendiri di `content/templates/` (`empty`, `cocotb-basic`). Testbench `cocotb-basic` sudah dicek di image: lulus untuk desainnya, dan gagal untuk dua mutan.
- Template dan proyek salinan soal sudah memuat `smartx.yaml` versi draf (`top`, `sources`, `tests`, `simulator`). Validasi dan form-nya dikerjakan di task 2.
- Frontend: `/workspace` (daftar proyek + form "Proyek baru"; soal dikelompokkan per topik) dan `/workspace/:id` (file tree + Monaco). Autosave memakai satu `useAutosave` per halaman dengan nilai `{path, content}`. Hook ini sekarang generik dan punya `settle()`, yang menyimpan perubahan tertunda lalu menunggu sampai selesai. `settle()` dipanggil sebelum pindah file, membuat, mengganti nama, atau menghapus, supaya autosave yang terlambat tidak menulis ke file yang salah atau menghidupkan lagi file yang baru dihapus. Ada test mutasi untuk urutan ini.
- Monaco memakai CRLF sebagai baris baru di Windows untuk file baru atau file satu baris; ini terlihat saat dicek di browser. `CodeEditor` sekarang memaksa model ke LF, sehingga file proyek dan kode soal disimpan dengan akhir baris LF.
- Monaco sekarang juga memuat grammar Python, YAML, dan Markdown untuk file proyek. Bahasa ditentukan dari ekstensi file (`editor/languages.ts`).
- Belum ada di UI: ganti nama proyek (API `PATCH` sudah ada) dan memindah file ke folder lain (API `move` sudah mendukungnya, tetapi ganti nama di tree hanya mengubah nama di folder yang sama).
