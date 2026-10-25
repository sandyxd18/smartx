# Deteksi pola 1011 (FSM Moore)

Buat FSM yang membaca satu bit `x` di setiap sisi naik clock dan menyalakan `z` ketika
empat bit terakhir yang dibaca adalah `1`, `0`, `1`, `1` (berurutan, bit terakhir paling akhir).
Buat modul `seq1011`:

| Port  | Arah   | Lebar | Keterangan |
|-------|--------|-------|------------|
| `clk` | input  | 1     | clock, aktif di sisi naik |
| `rst` | input  | 1     | reset sinkron, aktif tinggi: lupakan semua bit sebelumnya |
| `x`   | input  | 1     | bit masuk, dibaca di sisi naik clock |
| `z`   | output | 1     | 1 selama satu siklus setelah pola 1011 lengkap |

Ketentuan:

- **Moore**: `z` hanya bergantung pada state, jadi `z` naik pada siklus *setelah* bit `1`
  terakhir dibaca, dan tidak berubah walaupun `x` berubah di tengah siklus.
- Pola boleh **tumpang tindih**: masukan `1011011` menyalakan `z` dua kali.
