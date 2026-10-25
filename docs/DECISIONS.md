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
