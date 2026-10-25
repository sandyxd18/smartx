# Perbaiki: latch yang tidak disengaja

Kode di editor **sudah bisa dikompilasi**, tetapi tidak sesuai spesifikasi. Tugasmu:
temukan bug-nya dan perbaiki.

Modul `pick` seharusnya rangkaian kombinasional murni:

| Port     | Arah   | Lebar | Keterangan |
|----------|--------|-------|------------|
| `en`     | input  | 1     | enable |
| `sel`    | input  | 1     | pemilih |
| `a`, `b` | input  | 4     | data |
| `y`      | output | 4     | `en = 1`: `sel ? b : a`. `en = 0`: **0** |

Rangkaian kombinasional tidak punya ingatan: output hanya ditentukan oleh input saat ini.
Jalankan kode apa adanya dulu dan baca pesan test-nya.
