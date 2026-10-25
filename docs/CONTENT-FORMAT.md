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
id: tang-nano-9k
name: Sipeed Tang Nano 9K
family: gowin
device: GW1NR-LV9QN88PC6/I6
nextpnr: {binary: nextpnr-himbaechel, args: ["--device", "GW1NR-LV9QN88PC6/I6", "--vopt", "family=GW1N-9C"]}
pack: {binary: gowin_pack, args: ["-d", "GW1N-9C"]}
flash: {tool: openFPGALoader, args: ["-b", "tangnano9k"]}
clock: {pin: "52", freq_mhz: 27}
constraints_template: tang-nano-9k.cst
```

Argumen persis untuk nextpnr dan gowin_pack harus dicek terhadap versi OSS CAD Suite yang dipin (contoh di atas bisa usang).
