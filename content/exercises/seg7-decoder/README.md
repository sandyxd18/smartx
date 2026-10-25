# Decoder 7-segment heksadesimal

Display 7-segment punya segmen `a` sampai `g`:

```
 aaa
f   b
f   b
 ggg
e   c
e   c
 ddd
```

Buat modul `seg7` yang menyalakan segmen untuk satu digit heksadesimal (0 sampai F).
Segmen aktif tinggi (1 = menyala).

| Port  | Arah   | Lebar | Keterangan |
|-------|--------|-------|------------|
| `hex` | input  | 4     | digit 0 sampai F |
| `seg` | output | 7     | `{a, b, c, d, e, f, g}`: `seg[6]` = a, ..., `seg[0]` = g |

Pola yang diminta (`seg` dari bit 6 ke bit 0):

| Digit | `seg` |
|-------|-------|
| 0 | `1111110` |
| 1 | `0110000` |
| 2 | `1101101` |
| 3 | `1111001` |
| 4 | `0110011` |
| 5 | `1011011` |
| 6 | `1011111` |
| 7 | `1110000` |
| 8 | `1111111` |
| 9 | `1111011` |
| A | `1110111` |
| B | `0011111` |
| C | `1001110` |
| D | `0111101` |
| E | `1001111` |
| F | `1000111` |

A, C, E, F ditampilkan huruf besar; b dan d huruf kecil supaya tidak tertukar dengan 8 dan 0.
