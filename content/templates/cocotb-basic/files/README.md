# Proyek cocotb dasar

Isi proyek ini:

| File | Isi |
|---|---|
| `src/counter.v` | desain: counter 8-bit dengan reset sinkron, enable, dan sinyal `wrap` |
| `test/test_counter.py` | testbench cocotb: clock, reset, model referensi, test acak ber-seed |
| `smartx.yaml` | konfigurasi: modul top, file sumber, file test, simulator |

Coba ubah desainnya (misalnya jadikan counter turun), lalu sesuaikan model referensi di testbench. Test yang baik gagal ketika desainnya salah, jadi pastikan juga test-mu gagal kalau kamu sengaja merusak desain.
