# Perbaiki: blocking vs non-blocking

Kode di editor **sudah bisa dikompilasi**, tetapi tidak sesuai spesifikasi. Tugasmu:
temukan bug-nya dan perbaiki.

Modul `pipe2` adalah pipeline dua tahap: data masuk ke `q1`, lalu satu siklus kemudian ke `q2`.

| Port  | Arah   | Lebar | Keterangan |
|-------|--------|-------|------------|
| `clk` | input  | 1     | clock, aktif di sisi naik |
| `d`   | input  | 8     | data masuk |
| `q1`  | output | 8     | `d` dari 1 sisi naik clock sebelumnya |
| `q2`  | output | 8     | `d` dari 2 sisi naik clock sebelumnya |

Jika `d` berturut-turut 10, 20, 30, maka setelah sisi naik ketiga `q1 = 30` dan `q2 = 20`.
