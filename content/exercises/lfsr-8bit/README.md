# LFSR 8-bit (pseudo-random)

Linear Feedback Shift Register (LFSR) adalah shift register yang bit masuknya dihitung
dari XOR beberapa bitnya sendiri. Dengan pilihan bit yang tepat, LFSR 8-bit melewati
semua 255 nilai bukan nol sebelum berulang, sehingga sering dipakai sebagai generator
bilangan acak semu yang murah. Buat modul `lfsr8`:

| Port  | Arah   | Lebar | Keterangan |
|-------|--------|-------|------------|
| `clk` | input  | 1     | clock, aktif di sisi naik |
| `rst` | input  | 1     | reset sinkron, aktif tinggi: `q` menjadi `8'h01` |
| `en`  | input  | 1     | maju satu langkah jika 1 |
| `q`   | output | 8     | isi LFSR |

Satu langkah (saat `en = 1`):

1. `fb = q[7] XOR q[5] XOR q[4] XOR q[3]`
2. `q` bergeser ke kiri satu bit dan `fb` masuk di `q[0]`.

Contoh dari `q = 8'h01`: langkah berikutnya `8'h02`, lalu `8'h04`, `8'h08`, `8'h11`, ...
