// Counter 6-bit yang ditampilkan di enam LED dan naik satu setiap TICK siklus.
// Tombol S2 (rst_n, 0 saat ditekan) mengembalikan counter ke 0.
// Di Tang Nano 9K (clock 27 MHz), TICK = 6_750_000 berarti naik empat kali per detik.
module counter_led #(
    parameter integer TICK = 6_750_000
) (
    input  wire       clk,
    input  wire       rst_n,   // tombol S2: asinkron, jadi lewat sync2 dulu
    output wire [5:0] led      // 0 = menyala: LED Tang Nano 9K aktif-rendah
);

    localparam integer W = $clog2(TICK);

    wire       run;            // 1 = tombol reset tidak ditekan
    reg  [W-1:0] div;
    reg  [5:0]   count;

    initial begin
        div   = 0;
        count = 0;
    end

    // Sampai sync2 terisi (dua siklus pertama), run = 0: counter ikut ter-reset sesaat.
    sync2 u_rst (.clk(clk), .async_in(rst_n), .sync_out(run));

    always @(posedge clk) begin
        if (!run) begin
            div   <= 0;
            count <= 0;
        end else if (div == TICK[W-1:0] - 1'b1) begin
            div   <= 0;
            count <= count + 1'b1;
        end else begin
            div <= div + 1'b1;
        end
    end

    assign led = ~count;

endmodule
