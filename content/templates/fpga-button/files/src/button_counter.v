// Setiap tekanan tombol S1 menaikkan counter 6-bit yang tampil di enam LED.
// Tombol lewat synchronizer lalu debouncer, dan counter naik di sisi awal tekanan,
// sehingga satu tekanan = satu langkah, berapa lama pun tombol ditahan.
module button_counter #(
    parameter integer DEBOUNCE_CYCLES = 270_000  // 10 ms pada 27 MHz
) (
    input  wire       clk,
    input  wire       btn,     // tombol S1: 0 saat ditekan
    output wire [5:0] led      // 0 = menyala: LED Tang Nano 9K aktif-rendah
);

    wire       btn_sync;
    wire       pressed;
    reg  [5:0] count;
    reg        last;

    initial begin
        count = 0;
        last  = 1'b0;
    end

    sync2 u_sync (.clk(clk), .async_in(~btn), .sync_out(btn_sync));

    debounce #(.CYCLES(DEBOUNCE_CYCLES)) u_db (.clk(clk), .noisy(btn_sync), .clean(pressed));

    always @(posedge clk) begin
        last <= pressed;
        if (pressed && !last) count <= count + 1'b1;
    end

    assign led = ~count;

endmodule
