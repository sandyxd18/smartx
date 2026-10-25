---
title: Debounce tombol
step: 3
order: 30
---

# Debounce tombol

Tombol mekanis tidak berpindah dari "lepas" ke "tekan" dengan bersih. Kontak logamnya memantul, sehingga selama beberapa milidetik sinyalnya berganti-ganti 0 dan 1 sebelum tenang. Bagi FPGA dengan clock 27 MHz, satu milidetik sama dengan 27.000 siklus. Satu tekanan bisa terbaca sebagai puluhan tekanan.

Gejala yang khas: counter yang seharusnya naik satu tiap tombol ditekan malah melompat 3, 7, atau 12.

## Idenya: tunggu sampai stabil

Debouncer hanya menerima nilai baru kalau nilai itu bertahan cukup lama tanpa berubah. Angka 10 ms umum dipakai dan cukup aman untuk tombol di board.

Di Tang Nano 9K (clock 27 MHz), 10 ms = 27.000.000 × 0,010 = **270.000 siklus**. Counter-nya butuh `$clog2(270000)` = 19 bit.

```verilog
module debounce #(
    parameter integer CYCLES = 270_000  // 10 ms pada 27 MHz
) (
    input  wire clk,
    input  wire noisy,           // sudah lewat sync2
    output reg  clean = 1'b0
);
    localparam integer W = $clog2(CYCLES);
    reg [W-1:0] count = 0;
    always @(posedge clk) begin
        if (noisy == clean) begin
            count <= 0;                      // tidak ada perubahan: mulai lagi
        end else if (count == CYCLES[W-1:0] - 1'b1) begin
            clean <= noisy;                  // berbeda selama 10 ms: terima
            count <= 0;
        end else begin
            count <= count + 1'b1;
        end
    end
endmodule
```

Setiap kali `noisy` sama dengan `clean`, counter mulai dari nol. Pantulan selalu mengembalikan sinyal ke nilai lama sebelum 10 ms habis, jadi pantulan tidak pernah lolos.

## Urutannya: synchronizer dulu

Tombol adalah input asinkron, jadi ia harus lewat `sync2` (materi sebelumnya) sebelum masuk debouncer:

```verilog
module top (
    input  wire       clk,
    input  wire       btn,     // S1: 0 saat ditekan
    output wire [5:0] led      // 0 = menyala
);
    wire btn_sync;
    wire pressed;
    reg  [5:0] count = 0;
    reg  last = 1'b0;
    sync2    u_sync (.clk(clk), .async_in(~btn), .sync_out(btn_sync));
    debounce u_db   (.clk(clk), .noisy(btn_sync), .clean(pressed));
    always @(posedge clk) begin
        last <= pressed;
        if (pressed && !last) count <= count + 1'b1;   // sisi naik: satu tekanan
    end
    assign led = ~count;
endmodule
```

Tiga hal yang perlu diperhatikan:

- **Polaritas.** Menurut template constraint Tang Nano 9K di SmartX, tombol bernilai 0 saat ditekan dan LED menyala saat diberi 0. Karena itu ada `~btn` dan `~count`. Kalau LED menyala terbalik dari dugaan, periksa polaritasnya dulu.
- **Deteksi sisi.** `pressed` bernilai 1 selama tombol ditahan. `pressed && !last` hanya 1 selama satu siklus di awal tekanan, jadi counter naik satu per tekanan, bukan terus berlari selama tombol ditahan.
- **Simulasi.** 270.000 siklus per tekanan membuat simulasi lama. Di testbench, override parameternya, misalnya `parameters: {CYCLES: 8}` di `smartx.yaml` kalau `debounce` adalah modul top, atau jadikan `CYCLES` parameter modul top lalu teruskan ke `debounce`.

Desain `top` di atas sudah dibangun di image toolchain untuk Tang Nano 9K: 25 ALU, 29 flip-flop, dan sekitar 26 LUT, dengan Fmax 169 MHz dari target 27 MHz.
