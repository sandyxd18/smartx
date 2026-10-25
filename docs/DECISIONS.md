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
