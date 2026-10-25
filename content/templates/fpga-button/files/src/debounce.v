// Debouncer: keluaran `clean` baru mengikuti `noisy` setelah `noisy` berbeda dari
// `clean` selama CYCLES siklus berturut-turut. Pantulan tombol yang lebih pendek
// dari itu tidak pernah lolos. Lihat materi "Debounce tombol".
module debounce #(
    parameter integer CYCLES = 270_000  // 10 ms pada 27 MHz
) (
    input  wire clk,
    input  wire noisy,     // sudah lewat sync2
    output reg  clean
);

    localparam integer W = $clog2(CYCLES);

    reg [W-1:0] count;

    initial begin
        clean = 1'b0;
        count = 0;
    end

    always @(posedge clk) begin
        if (noisy == clean) begin
            count <= 0;
        end else if (count == CYCLES[W-1:0] - 1'b1) begin
            clean <= noisy;
            count <= 0;
        end else begin
            count <= count + 1'b1;
        end
    end

endmodule
