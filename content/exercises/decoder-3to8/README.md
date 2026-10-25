# Decoder 3 ke 8 dengan enable

Decoder mengubah angka biner menjadi satu bit aktif ("one-hot"). Buat modul `decoder3to8`:

| Port | Arah   | Lebar | Keterangan |
|------|--------|-------|------------|
| `a`  | input  | 3     | nomor output yang diaktifkan (0 sampai 7) |
| `en` | input  | 1     | enable |
| `y`  | output | 8     | saat `en = 1`: hanya `y[a]` yang 1. Saat `en = 0`: semua 0 |

Contoh: `en = 1, a = 5` menghasilkan `y = 8'b0010_0000`.
