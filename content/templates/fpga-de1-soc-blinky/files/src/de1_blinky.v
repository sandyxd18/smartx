// DE1-SoC: LEDR0 berkedip (SW0 membalik fasanya), LEDR1-LEDR9 mengikuti saklar SW1-SW9.
// Cocok sebagai uji pertama di board: clock, LED, dan saklar sekaligus.
// HALF_PERIOD = jumlah siklus clock untuk setengah periode kedip (minimal 2).
// Di DE1-SoC (clock 50 MHz), 25_000_000 berarti menyala 0,5 detik lalu mati 0,5 detik.
module de1_blinky #(
    parameter integer HALF_PERIOD = 25_000_000
) (
    input  wire       CLOCK_50,
    input  wire [9:0] SW,      // 1 = saklar ke atas
    output wire [9:0] LEDR     // 1 = menyala: LED DE1-SoC aktif-tinggi
);

    localparam integer W = $clog2(HALF_PERIOD);

    reg [W-1:0] count;
    reg         on;

    // Nilai awal: di FPGA tersimpan di bitstream, jadi tidak perlu reset.
    initial begin
        count = 0;
        on    = 1'b0;
    end

    always @(posedge CLOCK_50) begin
        if (count == HALF_PERIOD[W-1:0] - 1'b1) begin
            count <= 0;
            on    <= ~on;
        end else begin
            count <= count + 1'b1;
        end
    end

    // Saklar ke LED tanpa flip-flop: tidak ada clock yang terlibat, jadi tidak perlu
    // synchronizer.
    assign LEDR = {SW[9:1], on ^ SW[0]};

endmodule
