---
title: Menulis model referensi
step: 2
order: 10
---

# Menulis model referensi

Testbench yang baik tidak menyimpan daftar panjang "nilai yang benar". Testbench menjalankan **model referensi**: versi desain yang ditulis di Python, sederhana, dan jelas benar. Setiap siklus, keluaran DUT dibandingkan dengan keluaran model.

## Model harus lebih sederhana dari desainnya

Model tidak perlu tahu soal register, pointer, atau bit. Ia cukup menggambarkan **perilaku** yang diminta.

| Desain (Verilog) | Model (Python) |
|---|---|
| FIFO dengan RAM, pointer baca/tulis, bit `full`/`empty` | `collections.deque` dengan panjang maksimal |
| Counter 4-bit dengan wrap | `count = (count + 1) % 16` |
| Detektor pola `1011` | simpan 4 bit terakhir, bandingkan dengan `[1, 0, 1, 1]` |

Kalau model mulai terlihat seperti terjemahan baris per baris dari RTL, kesalahan yang sama bisa ada di keduanya, dan test tetap lulus. Tulis model dari spesifikasi, bukan dari kodemu.

## Urutan dalam satu siklus

Pola yang dipakai di semua soal dan template SmartX:

1. Di sisi turun clock, beri nilai ke input DUT.
2. Catat keadaan model **sebelum** sisi naik (misalnya `full` dan `empty` FIFO), karena DUT juga memutuskan berdasarkan keadaan itu.
3. Tunggu sisi turun berikutnya; sisi naik ada di antaranya.
4. Bandingkan keluaran DUT dengan model, lalu perbarui model.

Contoh dari FIFO:

```python
was_full, was_empty = model.full, model.empty   # keputusan DUT memakai keadaan lama
expected = model.pop() if rd and not was_empty else None
if wr and not was_full:
    model.push(value)
await FallingEdge(dut.clk)
if expected is not None:
    got = int(dut.dout.value)
    assert got == expected, f"siklus {cycle}: dout = {got}, seharusnya {expected}"
```

Kesalahan yang sering terjadi: memperbarui model dulu (misalnya `pop()`), lalu memakai keadaan barunya untuk memutuskan apakah tulis diterima. Desainnya benar, tetapi test-nya gagal.

## Pesan yang membantu

Pesan assert harus menjawab tiga hal: **kapan** (siklus ke berapa), **apa** (sinyal apa, nilai berapa), dan **seharusnya** berapa. Pesan seperti `siklus 7: dout = 3, seharusnya 2` langsung memberi tahu waktu yang perlu dilihat di waveform. Pesan seperti `assert 3 == 2` tidak.

Snippet **Scoreboard** di menu "Sisipkan snippet" adalah bentuk umum dari pola ini untuk data yang mengalir: `expect()` saat data dikirim, `got()` saat data keluar, `check()` di akhir test.
