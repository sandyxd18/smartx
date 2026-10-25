# Format konten

Semua materi belajar ada di `content/` sebagai file biasa (YAML, Markdown, Verilog, Python), supaya mudah ditulis, di-review, dan dites otomatis. Backend hanya membaca folder ini; UI tidak pernah mengirim `solution.v` ke browser kecuali syarat buka solusi terpenuhi.

## Soal latihan: `content/exercises/<id>/`

```
counter-4bit/
├─ exercise.yaml      metadata
├─ README.md          teks soal (Markdown, boleh tabel port)
├─ starter.v          kode awal di editor
├─ solution.v         solusi resmi (rahasia)
└─ test_<top>.py      testbench cocotb
```

`exercise.yaml`:

```yaml
id: counter-4bit          # = nama folder, kebab-case
title: Counter 4-bit dengan enable dan reset sinkron
step: 1                   # langkah kurikulum 1-6
level: 1                  # 1 dasar, 2 menengah, 3 lanjut
topics: [sequential, register, counter]   # topik pertama = grup di daftar soal
toplevel: counter4        # modul yang diuji
language: verilog         # verilog | systemverilog
files: {starter: starter.v, solution: solution.v, test: test_counter4.py, statement: README.md}
timeout_s: 30
hints: ["...", "..."]     # dibuka berurutan
order: 120                # opsional, urutan tampil dalam topik
requires: [dff-basic]     # opsional, soal prasyarat
```

### Topik

Halaman daftar soal mengelompokkan soal menurut **topik pertama** di `topics`. Pakai salah satu id ini agar soal masuk grup kurikulum yang benar (urutan grup juga mengikuti tabel ini):

| id | Grup |
|---|---|
| `combinational` | Kombinasional |
| `sequential` | Sekuensial |
| `fsm` | FSM |
| `pitfalls` | Jebakan umum |

Topik lain boleh dipakai sebagai topik kedua dan seterusnya (misalnya `mux`, `counter`). Topik pertama di luar tabel tetap tampil, tetapi sebagai grup sendiri di akhir daftar.

### Aturan testbench

1. Bandingkan DUT dengan **model referensi Python** siklus demi siklus. Hindari daftar nilai hardcode yang panjang.
2. Pesan assert dalam Bahasa Indonesia dan menyebut siklus, input, nilai didapat, nilai seharusnya.
3. Baca sinyal lewat helper `read_int()` (lihat contoh `counter-4bit`) agar nilai X/Z dijelaskan dengan bahasa manusia.
4. Ada minimal satu test acak dengan seed tetap, supaya hasil bisa diulang.
5. Ubah input di sisi turun clock dan cek output di sisi turun berikutnya. Ini menghindari race antara testbench dan DUT.
6. Jangan andalkan `timescale` di file user; grader memaksa `1ns/1ps`.
7. Pakai `assert kondisi, "pesan"` dengan pesan lengkap. Yang ditampilkan ke pengguna hanya pesan itu; introspeksi assertion dari cocotb dibuang oleh grader.
8. Untuk soal "jebakan umum", pesan gagal starter sebaiknya mengarahkan ke penyebab bug (contoh: `pitfall-latch`).
9. `solution.v` harus bersih dari warning `verilator --lint-only -Wall` (dicek `make check-content`). Sinyal yang memang sengaja tidak dipakai beri nama dengan kata `unused`, atau bungkus dengan `/* verilator lint_off ... */`.

### Validasi

`make check-content` (atau `check-content-local`) menjalankan setiap soal dua kali: `solution.v` wajib lulus, `starter.v` wajib gagal. Soal yang tidak lolos tidak boleh di-commit.

## Kurikulum langkah 1 (target Fase 1)

Urutan disarankan; tiap baris satu soal. Target minimal 20 soal.

| Topik | Soal |
|---|---|
| Kombinasional | wire & assign, gerbang dasar, mux 2:1, mux 4:1 (case), decoder 3→8, priority encoder, adder 4-bit, comparator, 7-segment decoder |
| Sekuensial | D flip-flop (reset sinkron/asinkron), register dengan enable, counter 4-bit, counter up/down + load, shift register, LFSR |
| FSM | deteksi pola `1011` (Moore), deteksi pola (Mealy), lampu lalu lintas, debouncer, edge detector |
| Jebakan umum | latch tak sengaja (soal "perbaiki kode ini"), blocking vs non-blocking, multi-driven net |

## Template proyek: `content/templates/<id>/` (Fase 2)

```
cocotb-basic/
├─ template.yaml      title, description, order
└─ files/             isi proyek baru, apa adanya (src/, test/, smartx.yaml, README.md)
```

Nama file dan folder di `files/` harus lolos aturan path proyek: huruf, angka, `_`, `-`, `.`; tidak diawali `.`; tidak memakai nama yang dicadangkan Windows (`con`, `nul`, `aux`, dan sejenisnya). Testbench template mengikuti aturan testbench di atas dan harus gagal untuk desain yang salah. Untuk `cocotb-basic` hal ini dicek dengan dua mutan (enable diabaikan, `wrap` tanpa `en`).

"Salin dari soal X" membuat proyek berisi `src/<toplevel>.v` (kode terakhir pengguna, atau starter), `test/<test_*.py>` (testbench soal), `README.md` (teks soal), dan `smartx.yaml`. `solution.v` tidak pernah ikut.

## Proyek workspace: `smartx.yaml`

File di root proyek. Divalidasi oleh `backend/app/projects/config.py`, dan bisa diedit lewat form atau sebagai YAML.

```yaml
top: counter              # wajib: modul top (identifier Verilog)
sources:                  # glob relatif ke root proyek; default [src/**/*.v]
  - src/**/*.v
tests:                    # file testbench cocotb (.py); default []
  - test/test_counter.py
simulator: icarus         # icarus | verilator; default icarus
parameters:               # opsional: parameter modul top
  WIDTH: 8
  INIT: 8'hFF             # selain angka bulat, teks diteruskan apa adanya
defines:                  # opsional: -DNAMA=nilai
  SIM: 1
fpga:                     # opsional: build FPGA (Fase 3)
  board: tang-nano-9k     # id profil di content/boards/
  constraints: constraints/tang-nano-9k.cst   # file constraint di proyek
  freq_mhz: 27            # opsional: target --freq nextpnr; default clock board
```

Aturan:

- Kunci yang tidak dikenal ditolak, supaya salah ketik (`simulater`) langsung terlihat.
- Pola `sources` boleh memakai `*` dan `?` (dalam satu folder) serta `**` sebagai satu segmen utuh (lintas folder, termasuk nol folder). Pola harus relatif, tanpa `..` dan tanpa `\`. File yang cocok dipakai sesuai urutan pola, tanpa duplikat.
- `tests` berisi path file `.py` di proyek. Nama file harus berupa nama modul Python yang valid (`test_fifo.py`). Dua file tidak boleh punya nama modul yang sama, karena cocotb memuat test berdasarkan nama modul.
- Nilai `parameters` dan `defines` berupa angka bulat atau teks. `true`/`false`, daftar, dan nilai kosong ditolak, karena cocotb runner (versi yang dipin) menulisnya apa adanya ke perintah simulator (`-P`/`-G`/`-D`). Untuk define tanpa nilai, isi `1`.
- Peringatan, yang tidak menghalangi penyimpanan: pola yang tidak cocok dengan file mana pun, modul top yang tidak ditemukan di file sumber, file test yang tidak ada, dan `tests` yang kosong.
- Menyimpan dari form menulis ulang file dari isi form, sehingga komentar buatan sendiri hilang. Hanya baris judul yang dipertahankan. Bagian `fpga` tidak diedit di form simulasi, tetapi ikut disimpan apa adanya.
- `fpga.board` yang tidak dikenal dan file `fpga.constraints` yang tidak ada menjadi peringatan; tombol Build menolaknya dengan pesan yang sama. Build FPGA memakai `top`, `sources`, `parameters`, dan `defines` yang sama dengan simulasi.

## Snippet testbench: `content/snippets/*.yaml` (Fase 2)

```yaml
snippets:
  - id: scoreboard            # huruf kecil, angka, '-'
    title: Scoreboard
    description: Bandingkan keluaran DUT dengan urutan data yang diharapkan.
    imports:                  # baris import yang dibutuhkan body
      - from collections import deque
    body: |                   # kode tingkat modul (kelas, fungsi, test)
      class Scoreboard:
          ...
```

Menu "Sisipkan snippet" menaruh import yang belum ada di bagian import file dan body di akhir file. Snippet ikut aturan testbench di atas: input diubah di sisi turun clock, dan sinyal dibaca setelah `ReadOnly()`. Semua snippet harus bisa digabung menjadi satu testbench. Test Docker `test_snippets_make_a_working_testbench` menggabungkan semuanya untuk menguji register valid/ready (`backend/tests/fixtures/projects/pipe_reg`): hasilnya harus lulus di Icarus dan Verilator, dan harus gagal untuk register yang membuang data.

## Materi singkat: `content/lessons/NN-slug.md` (Fase 2)

```markdown
---
title: Icarus vs Verilator
step: 2          # langkah belajar 1–6 (SPEC); 2 = simulasi & verifikasi
order: 40        # urutan dalam satu langkah
---

# Icarus vs Verilator
...
```

`NN` adalah langkah belajar (misalnya `02-`). Isinya Markdown biasa (tabel dan blok kode didukung) dan tampil di sidebar "Materi" halaman proyek. Klaim tentang perilaku tool sebaiknya diukur dulu di image toolchain dan disebut versinya, bukan ditulis dari ingatan.

## Proyek terpandu: `content/projects/<id>/` (Fase 4)

```
uart-tx/
├─ project.yaml
└─ milestones/
   ├─ 01-baud-gen/  {README.md, starter/*.v, solution/*.v, test_*.py}
   ├─ 02-shifter/
   └─ 03-full-tx/
```

`project.yaml` berisi `id, title, description, milestones: [{id, title, toplevel, test}]`, dan opsional `fpga: {board, constraints}` serta `asic: {config}` untuk dilanjutkan ke langkah 3 dan 5. File dari milestone sebelumnya ikut terbawa ke milestone berikutnya, jadi proyek tumbuh di workspace yang sama.

## Profil board: `content/boards/<id>.yaml` (Fase 3)

```yaml
id: tang-nano-9k                 # = nama file
name: Sipeed Tang Nano 9K
family: gowin                    # gowin | ice40
device: GW1NR-LV9QN88PC6/I5
synth: synth_gowin               # perintah sintesis Yosys: synth_gowin | synth_ice40
nextpnr:
  binary: nextpnr-himbaechel
  args: [--device, GW1NR-LV9QN88PC6/I5, --vopt, family=GW1N-9C, --vopt, "cst={constraints}", --write, "{pnr}"]
pnr_file: pnr.json               # yang ditulis nextpnr untuk packer
pack:
  binary: gowin_pack
  args: [-d, GW1N-9C, -o, "{bitstream}", "{pnr}"]
bitstream_file: bitstream.fs
flash: {binary: openFPGALoader, args: [-b, tangnano9k]}
clock: {port: clk, pin: "52", freq_mhz: 27}    # freq_mhz = target --freq bawaan
constraints: {format: cst, template: tang-nano-9k.cst}   # cst | pcf, file di folder yang sama
resources:                       # baris laporan: label -> jenis resource nextpnr yang dijumlahkan
  LUT: [LUT4]
  FF: [DFF]
  BRAM: [BSRAM]
  IO: [IOB]
```

Aturan:

- Argumen tool boleh memakai placeholder `{constraints}` (file constraint proyek), `{pnr}` (`pnr_file`), dan `{bitstream}` (`bitstream_file`). Argumen nextpnr wajib memakai `{constraints}` dan `{pnr}`; argumen packer wajib memakai `{pnr}` dan `{bitstream}`. Job menambahkan `--json`, `--freq`, `--report`, dan `-l` sendiri.
- Template constraint berisi semua pin board yang berguna dengan nama port yang konsisten (`clk`, `rst_n`, `btn`, `led[0]`…). Port yang tidak dipakai desain diabaikan nextpnr, jadi template tidak perlu dipangkas. Template wajib memasang `clock.port` ke `clock.pin`.
- Argumen persis untuk nextpnr dan packer harus dicek terhadap versi OSS CAD Suite yang dipin. Test Docker `test_board_profile_builds_blinky` membangun `backend/tests/fixtures/boards/<id>/blinky.v` dengan profil dan template saja, dan setiap profil wajib punya fixture itu.
