# Register 8-bit dengan enable dan reset sinkron

Register adalah sekumpulan flip-flop yang dimuat bersamaan. Buat modul `reg8_en`:

| Port  | Arah   | Lebar | Keterangan |
|-------|--------|-------|------------|
| `clk` | input  | 1     | clock, aktif di sisi naik |
| `rst` | input  | 1     | reset **sinkron**, aktif tinggi |
| `en`  | input  | 1     | load enable |
| `d`   | input  | 8     | data |
| `q`   | output | 8     | isi register |

Di setiap sisi naik clock:

- `rst = 1`: `q` menjadi 0 (menang atas `en`).
- `rst = 0, en = 1`: `q` menjadi `d`.
- `rst = 0, en = 0`: `q` tetap.

Reset sinkron tidak berpengaruh sampai sisi naik clock berikutnya.
