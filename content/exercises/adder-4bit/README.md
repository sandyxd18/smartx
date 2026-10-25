# Adder 4-bit dengan carry

Buat modul `adder4` yang menjumlahkan dua bilangan 4-bit tak bertanda dan carry masuk:

| Port   | Arah   | Lebar | Keterangan |
|--------|--------|-------|------------|
| `a`, `b` | input | 4    | bilangan yang dijumlahkan |
| `cin`  | input  | 1     | carry masuk |
| `sum`  | output | 4     | 4 bit bawah dari `a + b + cin` |
| `cout` | output | 1     | carry keluar (bit ke-5) |

Contoh: `a = 9, b = 8, cin = 1` menghasilkan 18 = `1_0010`, jadi `sum = 2`, `cout = 1`.
