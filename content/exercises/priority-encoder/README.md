# Priority encoder 8 ke 3

Beberapa permintaan bisa aktif bersamaan; priority encoder melaporkan yang prioritasnya
paling tinggi. Di soal ini, **nomor bit tertinggi menang**. Buat modul `prio_enc8`:

| Port    | Arah   | Lebar | Keterangan |
|---------|--------|-------|------------|
| `req`   | input  | 8     | permintaan; bit `i` = 1 berarti permintaan `i` aktif |
| `idx`   | output | 3     | nomor bit tertinggi yang 1 |
| `valid` | output | 1     | 1 jika ada minimal satu permintaan |

Saat `req = 0`, `valid = 0` dan `idx = 0`.

Contoh: `req = 8'b0010_0110` menghasilkan `idx = 5`, `valid = 1`.
