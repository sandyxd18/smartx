# Fase 6: Tapeout export (langkah 6)

Tujuan: dari desain yang lolos Fase 5, hasilkan repo yang siap dikirim ke shuttle Tiny Tapeout, dan buktikan dengan hardening lokal memakai alat resmi TT.

## Sebelum mulai

Cek shuttle yang sedang buka di tinytapeout.com dan template repo-nya (SKY, IHP, atau GF). Tiap shuttle memakai branch `tt-support-tools` sendiri dan bisa mengubah aturan pin, ukuran tile, atau versi flow. Simpan sebagai profil di `content/tapeout/shuttles/<id>.yaml` (template repo, branch tools, flag PDK seperti `--ihp`, ukuran tile yang tersedia). Jangan hardcode di kode.

## Task

1. **Pembungkus `tt_um_*`**: wizard untuk memetakan port desain ke antarmuka standar TT (`ui_in[7:0]`, `uo_out[7:0]`, `uio_in/out/oe[7:0]`, `clk`, `rst_n`, `ena`). Hasilkan modul wrapper Verilog, dan pastikan output yang tidak dipakai di-tie ke 0.
2. **Generator repo**: dari template shuttle, isi `info.yaml` (judul, author, deskripsi, jumlah tile, frekuensi clock, pinout), `src/`, `test/` (testbench cocotb untuk wrapper), `docs/info.md`. Hasil bisa diunduh `.zip` atau di-`git init` dengan commit pertama.
3. **Pemeriksaan sebelum hardening**: nama top diawali `tt_um_`, semua pin terdokumentasi di `info.yaml`, test cocotb wrapper lulus, tidak ada latch, lint bersih.
4. **Job `tt_harden`** (heavy): di dalam repo hasil generate, clone `tt-support-tools` (branch sesuai profil) ke `tt/`, lalu jalankan `tt_tool.py --create-user-config` dan `tt_tool.py --harden` (dengan flag PDK sesuai shuttle), lalu `--print-warnings`. Catatan: `tt_tool.py --harden` sendiri memakai container, jadi job ini butuh pendekatan khusus (Docker-in-Docker, atau menjalankan langkah ini lewat helper di host). Putuskan dan catat di `DECISIONS.md`.
5. **Gate-level test**: jalankan test cocotb terhadap netlist hasil hardening, seperti yang diminta TT.
6. **Render**: `tt_tool.py --create-png` untuk gambar GDS tile.
7. **Checklist submit** di UI: tautan ke halaman submit TT, langkah push ke GitHub, verifikasi GitHub Actions di repo hasil (gds, docs, test) hijau.

## Kriteria selesai

- [ ] `uart-tx` (atau desain kecil lain) menjadi repo TT, hardening lokal sukses, warning dibaca dan dijelaskan.
- [ ] Gate-level test lulus.
- [ ] Repo yang di-push ke GitHub lolos semua GitHub Actions template TT.
- [ ] Definisi "v1 selesai" di `SPEC.md` terpenuhi.
