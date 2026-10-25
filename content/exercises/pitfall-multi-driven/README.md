# Perbaiki: satu sinyal, dua driver

Kode di editor **sudah bisa dikompilasi**, tetapi tidak sesuai spesifikasi. Tugasmu:
temukan bug-nya dan perbaiki.

Modul `logic_sel` memilih operasi AND atau OR:

| Port     | Arah   | Lebar | Keterangan |
|----------|--------|-------|------------|
| `a`, `b` | input  | 1     | input |
| `sel`    | input  | 1     | 0 = AND, 1 = OR |
| `y`      | output | 1     | `sel = 0`: `a & b`. `sel = 1`: `a | b` |

Penulis kode ini mengira dua `assign` akan "dipilih" otomatis. Jalankan dulu dan lihat apa
yang terjadi pada `y` saat `a` dan `b` berbeda.
