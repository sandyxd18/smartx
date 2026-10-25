# Lampu lalu lintas

Buat pengendali lampu lalu lintas sederhana `traffic` yang berputar
hijau → kuning → merah → hijau → ...

| Port     | Arah   | Lebar | Keterangan |
|----------|--------|-------|------------|
| `clk`    | input  | 1     | clock, aktif di sisi naik |
| `rst`    | input  | 1     | reset sinkron, aktif tinggi |
| `green`  | output | 1     | lampu hijau |
| `yellow` | output | 1     | lampu kuning |
| `red`    | output | 1     | lampu merah |

Ketentuan:

- Tepat satu lampu menyala setiap saat.
- Setelah reset, hijau menyala. Siklus clock tempat reset terjadi dihitung sebagai siklus hijau pertama.
- Lama menyala: **hijau 4 siklus, kuning 2 siklus, merah 3 siklus**, lalu kembali ke hijau.

Urutan yang terlihat setelah setiap sisi naik clock, mulai dari reset:
`H H H H K K M M M H H H H K K ...`
