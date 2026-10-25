# Shift register 8-bit (serial in, parallel out)

Shift register memasukkan data satu bit per clock. Buat modul `shift8`:

| Port   | Arah   | Lebar | Keterangan |
|--------|--------|-------|------------|
| `clk`  | input  | 1     | clock, aktif di sisi naik |
| `rst`  | input  | 1     | reset sinkron, aktif tinggi (`q` menjadi 0) |
| `en`   | input  | 1     | geser jika 1 |
| `sin`  | input  | 1     | bit serial yang masuk |
| `q`    | output | 8     | isi register |
| `sout` | output | 1     | bit yang paling lama di dalam (`q[7]`) |

Saat `en = 1`, isi bergeser ke kiri satu bit dan `sin` masuk di `q[0]`:
`q` lama `abcdefgh` menjadi `bcdefgh` diikuti `sin`. Saat `en = 0`, `q` tetap.
