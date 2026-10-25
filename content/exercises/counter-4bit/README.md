# Counter 4-bit dengan enable dan reset sinkron

Buat modul `counter4` dengan port berikut:

| Port  | Arah   | Lebar | Keterangan |
|-------|--------|-------|------------|
| `clk` | input  | 1     | clock, aktif di sisi naik |
| `rst` | input  | 1     | reset sinkron, aktif tinggi |
| `en`  | input  | 1     | jika 1, counter bertambah satu tiap clock |
| `q`   | output | 4     | nilai counter |

Perilaku:

- Saat `rst = 1` pada sisi naik clock, `q` menjadi 0. Reset menang atas `en`.
- Saat `rst = 0` dan `en = 1`, `q` bertambah 1. Setelah 15, `q` kembali ke 0.
- Saat `rst = 0` dan `en = 0`, `q` tetap.
