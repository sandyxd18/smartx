# Wire dan assign

Soal pertama: menyambung sinyal dengan `assign`. Buat modul `wire_assign`:

| Port   | Arah   | Lebar | Keterangan |
|--------|--------|-------|------------|
| `in`   | input  | 4     | data masuk |
| `out`  | output | 4     | sama persis dengan `in` |
| `rev`  | output | 4     | `in` dengan urutan bit dibalik: `rev[3] = in[0]`, ..., `rev[0] = in[3]` |
| `five` | output | 4     | selalu bernilai 5 |
| `msb`  | output | 1     | bit paling kiri dari `in` (`in[3]`) |

Contoh: `in = 4'b1100` menghasilkan `out = 1100`, `rev = 0011`, `five = 0101`, `msb = 1`.
