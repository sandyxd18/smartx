# Edge detector (sisi naik dan turun)

Edge detector mengubah perubahan level menjadi pulsa satu siklus. Buat modul `edge_detect`:

| Port   | Arah   | Lebar | Keterangan |
|--------|--------|-------|------------|
| `clk`  | input  | 1     | clock, aktif di sisi naik |
| `rst`  | input  | 1     | reset sinkron, aktif tinggi |
| `sig`  | input  | 1     | sinyal yang diamati, dibaca di sisi naik clock |
| `rise` | output | 1     | pulsa 1 siklus saat `sig` berubah 0 → 1 |
| `fall` | output | 1     | pulsa 1 siklus saat `sig` berubah 1 → 0 |

Ketentuan:

- Di setiap sisi naik clock, bandingkan `sig` yang dibaca sekarang dengan yang dibaca di sisi naik
  sebelumnya. Hasilnya (`rise`, `fall`) adalah output register, jadi terlihat setelah sisi naik itu.
- Saat reset: `rise = 0`, `fall = 0`, dan nilai "sebelumnya" dianggap 0. Jadi jika `sig = 1`
  tepat setelah reset, itu dihitung sebagai sisi naik.
