// Blinky: LED pertama berkedip, LED lain mati.
// HALF_PERIOD = jumlah siklus clock untuk setengah periode kedip (minimal 2).
// Di Tang Nano 9K (clock 27 MHz), 13_500_000 berarti menyala 0,5 detik lalu mati 0,5 detik.
module blinky #(
    parameter integer HALF_PERIOD = 13_500_000
) (
    input  wire       clk,
    output wire [5:0] led    // 0 = menyala: LED Tang Nano 9K aktif-rendah
);

    localparam integer W = $clog2(HALF_PERIOD);

    reg [W-1:0] count;
    reg         on;

    // Nilai awal: di FPGA tersimpan di bitstream, jadi tidak perlu reset.
    initial begin
        count = 0;
        on    = 1'b0;
    end

    always @(posedge clk) begin
        if (count == HALF_PERIOD[W-1:0] - 1'b1) begin
            count <= 0;
            on    <= ~on;
        end else begin
            count <= count + 1'b1;
        end
    end

    assign led = {5'b11111, ~on};

endmodule
