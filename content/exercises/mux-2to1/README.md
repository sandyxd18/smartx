# Multiplexer 2:1 (8-bit)

Multiplexer memilih salah satu dari beberapa input. Buat modul `mux2`:

| Port  | Arah   | Lebar | Keterangan |
|-------|--------|-------|------------|
| `a`   | input  | 8     | dipilih saat `sel = 0` |
| `b`   | input  | 8     | dipilih saat `sel = 1` |
| `sel` | input  | 1     | pemilih |
| `y`   | output | 8     | `a` atau `b` |
