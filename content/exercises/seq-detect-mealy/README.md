# Deteksi pola 101 (FSM Mealy)

Mirip soal sebelumnya, tetapi sekarang FSM **Mealy**: `z` dihitung dari state *dan* input
saat ini, sehingga `z` menyala di siklus yang sama ketika bit terakhir pola sedang ada
di `x`, sebelum sisi naik clock membacanya. Buat modul `seq101`:

| Port  | Arah   | Lebar | Keterangan |
|-------|--------|-------|------------|
| `clk` | input  | 1     | clock, aktif di sisi naik |
| `rst` | input  | 1     | reset sinkron, aktif tinggi |
| `x`   | input  | 1     | bit masuk, dibaca di sisi naik clock |
| `z`   | output | 1     | 1 saat dua bit terakhir yang dibaca adalah `1, 0` **dan** `x` sekarang `1` |

Pola boleh tumpang tindih: masukan `10101` menyalakan `z` saat bit ke-3 dan ke-5.
