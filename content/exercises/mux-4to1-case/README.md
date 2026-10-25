# Multiplexer 4:1 dengan `case`

Buat modul `mux4` yang memilih satu dari empat input 4-bit. Kerjakan dengan
`always @(*)` dan pernyataan `case`, bukan ternary bertingkat.

| Port  | Arah   | Lebar | Keterangan |
|-------|--------|-------|------------|
| `a`, `b`, `c`, `d` | input | 4 | data |
| `sel` | input  | 2     | `0` pilih `a`, `1` pilih `b`, `2` pilih `c`, `3` pilih `d` |
| `y`   | output | 4     | hasil pilihan (dideklarasikan `reg` karena di-assign di dalam always) |
