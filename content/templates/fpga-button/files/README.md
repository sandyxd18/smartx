# FPGA tombol dengan debounce

Setiap kali tombol S1 ditekan, counter 6-bit di enam LED naik satu. Satu tekanan dihitung satu kali, berapa lama pun tombol ditahan dan walaupun kontaknya memantul.

| File | Isi |
|---|---|
| `src/button_counter.v` | modul top: synchronizer → debouncer → deteksi sisi → counter |
| `src/sync2.v` | synchronizer 2-flop |
| `src/debounce.v` | debouncer: menunggu sinyal stabil selama `CYCLES` siklus |
| `test/test_button_counter.py` | testbench cocotb: model referensi, tekanan dengan pantulan, gangguan singkat, test acak ber-seed |
| `constraints/tang-nano-9k.cst` | nama port → pin board (`btn` di pin 3 = tombol S1) |
| `smartx.yaml` | modul top, file, dan bagian `fpga` |

## Langkah

1. **Simulasi.** Klik *Simulasi*. Dengan `DEBOUNCE_CYCLES: 8`, pantulan di test cukup beberapa siklus. Di tab Waveform, bandingkan `btn` yang memantul dengan `u_db.clean` yang bersih.
2. **Build.** Klik *Build*. Board memakai `DEBOUNCE_CYCLES: 270000` (10 ms) dari `fpga.parameters`.
3. **Ke board.** Jalankan perintah `smartx-flash` dari tab FPGA, lalu tekan S1 beberapa kali.

## Coba rusak, lalu lihat test-nya gagal

- Di `button_counter.v`, sambungkan `pressed` langsung ke `btn_sync` (lewati debouncer). Test pantulan akan gagal karena satu tekanan terhitung beberapa kali. Di board, counter akan melompat.
- Ganti `pressed && !last` menjadi `pressed`. Counter akan berlari selama tombol ditahan.

Materi *Synchronizer 2-flop* dan *Debounce tombol* menjelaskan kedua bagian ini.

Catatan: pin di constraint diambil dari pinout Tang Nano 9K dan belum dicoba di board fisik oleh pembuat SmartX.
