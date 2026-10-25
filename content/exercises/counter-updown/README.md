# Counter up/down 4-bit dengan load

Lanjutan dari counter 4-bit: sekarang bisa menghitung mundur dan dimuat nilai awal.
Buat modul `counter_ud`:

| Port   | Arah   | Lebar | Keterangan |
|--------|--------|-------|------------|
| `clk`  | input  | 1     | clock, aktif di sisi naik |
| `rst`  | input  | 1     | reset sinkron, aktif tinggi |
| `load` | input  | 1     | muat `d` ke counter |
| `en`   | input  | 1     | hitung |
| `up`   | input  | 1     | arah: 1 = naik, 0 = turun |
| `d`    | input  | 4     | nilai yang dimuat |
| `q`    | output | 4     | nilai counter |

Di setiap sisi naik clock, dengan prioritas dari atas ke bawah:

1. `rst = 1`: `q` menjadi 0.
2. `load = 1`: `q` menjadi `d`.
3. `en = 1`: `q` naik 1 (jika `up = 1`) atau turun 1 (jika `up = 0`), membungkus di 0 dan 15.
4. Selain itu `q` tetap.
