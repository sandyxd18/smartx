---
title: Test acak dengan seed
step: 2
order: 20
---

# Test acak dengan seed

Test terarah (directed) memeriksa kasus yang kamu pikirkan. Test acak menemukan kasus yang **tidak** kamu pikirkan: tulis dan baca di siklus yang sama saat FIFO penuh, backpressure tepat di data terakhir, dan sejenisnya. Gunakan keduanya.

## Seed tetap: kegagalan harus bisa diulang

Test acak yang gagal sekali lalu lulus di run berikutnya hampir tidak berguna, karena kamu tidak bisa memeriksa kegagalannya. Karena itu, pakai generator sendiri dengan seed tetap:

```python
rng = random.Random(1234)
for cycle in range(500):
    wr = rng.random() < 0.6
    value = rng.randrange(256)
```

Jangan pakai `random.random()` (generator global). cocotb mengisi seed generator global dengan angka baru di setiap run; log simulasi mencetaknya sebagai `Seeding Python random module with ...`. Akibatnya urutan angkanya berubah setiap kali.

Kalau ingin mencoba lebih banyak urutan, ganti seed-nya secara sengaja (misalnya ulangi test dengan seed 1, 2, 3), dan tulis seed di pesan gagal.

## Mengatur peluang

Acak yang seragam jarang mengenai kasus tepi. Atur peluangnya:

- `rng.random() < 0.6` untuk tulis dan `< 0.5` untuk baca membuat FIFO perlahan terisi, sehingga kondisi penuh benar-benar terjadi.
- Backpressure (`ready` acak) dengan peluang 0,7 membuat penerima kadang menahan data.
- Untuk nilai data, `rng.randrange(256)` sudah cukup; untuk batas, sisipkan sesekali `0` dan `255`.

## Tahu apa yang sudah teruji: coverage

Test acak bisa lulus karena kasus sulitnya tidak pernah terjadi. Snippet **Coverage sederhana** mencatat kasus yang kamu sebut di awal, lalu gagal kalau ada yang belum pernah terjadi:

```python
coverage = Coverage("stall", "no_stall")
waited = await driver.send(value)
coverage.hit("stall" if waited else "no_stall")
...
coverage.check()   # gagal kalau backpressure tidak pernah terjadi
```

Saat snippet SmartX sendiri ditulis, coverage inilah yang menunjukkan bahwa versi awal contoh test tidak pernah benar-benar mengalami backpressure.
