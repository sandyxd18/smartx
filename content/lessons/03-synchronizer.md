---
title: Synchronizer 2-flop
step: 3
order: 20
---

# Synchronizer 2-flop

Di simulasi, input berubah tepat di tempat yang kita tentukan, biasanya di sisi turun clock. Di board, tombol, sinyal UART, atau sensor berubah **kapan saja**, tidak peduli clock FPGA. Sinyal seperti ini disebut **asinkron**.

## Masalahnya: metastabilitas

Flip-flop butuh inputnya diam sebentar sebelum dan sesudah sisi naik clock (waktu *setup* dan *hold*). Kalau input berubah tepat di jendela itu, flip-flop bisa terjebak di antara 0 dan 1 untuk beberapa saat sebelum memilih salah satunya. Keadaan ini disebut **metastabil**.

Akibatnya bukan sekadar "telat satu siklus". Kalau keluaran flip-flop metastabil masuk ke beberapa bagian logika sekaligus, bagian yang satu bisa membacanya sebagai 0 dan bagian lain sebagai 1 di siklus yang sama. Misalnya FSM masuk ke state yang mustahil, atau counter melompat. Bug seperti ini muncul jarang dan acak, dan tidak pernah terlihat di simulasi.

## Solusinya: dua flip-flop berurutan

```verilog
module sync2 (
    input  wire clk,
    input  wire async_in,   // dari pin, berubah kapan saja
    output wire sync_out    // aman dipakai logika ber-clock clk
);
    reg meta = 1'b0;
    reg stable = 1'b0;
    always @(posedge clk) begin
        meta   <= async_in;
        stable <= meta;
    end
    assign sync_out = stable;
endmodule
```

Flip-flop pertama (`meta`) boleh sesekali metastabil. Ia punya satu siklus penuh untuk tenang sebelum dibaca flip-flop kedua. Peluang ia masih belum tenang setelah satu siklus sangat kecil, sehingga `stable` praktis selalu bersih. Harganya: sinyal terlambat dua siklus (di 27 MHz sekitar 74 ns, tidak terasa untuk tombol).

## Aturan pakai

1. **Setiap input asinkron melewati synchronizer tepat satu kali**, lalu hanya `sync_out` yang dipakai. Jangan membaca `async_in` di tempat lain.
2. **Jangan memberi logika di antara kedua flip-flop.** `meta` hanya boleh masuk ke `stable`.
3. **Satu synchronizer untuk satu bit.** Bus multi-bit (misalnya counter 8-bit dari domain clock lain) tidak boleh disinkronkan bit per bit, karena tiap bit bisa tertangkap di siklus berbeda dan nilainya jadi campuran. Untuk bus, pakai FIFO asinkron atau kode Gray; itu topik lanjutan.

## Hubungannya dengan laporan timing

nextpnr hanya menganalisis jalur dari flip-flop ke flip-flop di dalam satu domain clock. Ia tidak tahu kapan sebuah pin berubah, jadi "Fmax tercapai" **tidak** berarti input asinkron aman. Synchronizer adalah tanggung jawab desainer, bukan tool.

Kode `sync2` di atas sudah dicoba di image toolchain SmartX: Yosys membangunnya menjadi dua flip-flop, dan Lint hanya memberi warning `PROCASSINIT` untuk nilai awal register (lihat materi *Kode yang tidak bisa disintesis*).
