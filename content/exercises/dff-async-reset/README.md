# D flip-flop dengan reset asinkron

Flip-flop D menyimpan nilai `d` setiap sisi naik clock. Reset **asinkron** bekerja
seketika, tanpa menunggu clock. Buat modul `dff_ar`:

| Port    | Arah   | Lebar | Keterangan |
|---------|--------|-------|------------|
| `clk`   | input  | 1     | clock, aktif di sisi naik |
| `rst_n` | input  | 1     | reset asinkron, **aktif rendah** (0 = reset) |
| `d`     | input  | 1     | data |
| `q`     | output | 1     | nilai tersimpan |

Perilaku:

- Begitu `rst_n` turun ke 0, `q` langsung menjadi 0, walaupun tidak ada sisi naik clock.
- Selama `rst_n = 0`, `q` tetap 0.
- Saat `rst_n = 1`, setiap sisi naik clock menyalin `d` ke `q`.

Bandingkan dengan reset sinkron di soal register 8-bit: di sana reset baru berlaku saat clock naik.
