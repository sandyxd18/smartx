# FPGA counter ke LED

Enam LED Tang Nano 9K menampilkan counter 6-bit dalam biner, yang naik empat kali per detik. Setelah 63, counter kembali ke 0. Tombol S2 mengembalikan counter ke 0.

| File | Isi |
|---|---|
| `src/counter_led.v` | desain: pembagi clock, counter, dan reset dari tombol |
| `src/sync2.v` | synchronizer 2-flop untuk tombol reset |
| `test/test_counter_led.py` | testbench cocotb: model referensi lengkap, test terarah, dan test acak ber-seed |
| `constraints/tang-nano-9k.cst` | nama port → pin board (`rst_n` di pin 4 = tombol S2) |
| `smartx.yaml` | modul top, file, dan bagian `fpga` |

## Langkah

1. **Simulasi.** Klik *Simulasi*. Dengan `TICK: 3`, counter naik tiap 3 siklus. Di tab Waveform, perhatikan bahwa `rst_n` baru berpengaruh dua siklus setelah berubah: itu jeda synchronizer.
2. **Build.** Klik *Build*. Board memakai `TICK: 6750000` dari `fpga.parameters`.
3. **Ke board.** Jalankan perintah `smartx-flash` dari tab FPGA. Tekan S2 untuk me-reset.

## Kenapa ada synchronizer?

Tombol berubah kapan saja, tidak mengikuti clock. Tanpa `sync2`, flip-flop yang membaca tombol bisa metastabil, dan sebagian bit counter bisa ter-reset sementara bit lain tidak. Materi *Synchronizer 2-flop* menjelaskan lebih lanjut. Reset tidak perlu debounce: pantulan tombol hanya me-reset counter beberapa kali berturut-turut, dan hasilnya tetap 0.

## Coba ubah

- Buat counter turun, bukan naik, lalu perbarui model referensi.
- Tambahkan tombol S1 (`btn`, pin 3) untuk menghentikan counter sementara. Jangan lupa synchronizer-nya.

Catatan: pin di constraint diambil dari pinout Tang Nano 9K dan belum dicoba di board fisik oleh pembuat SmartX.
