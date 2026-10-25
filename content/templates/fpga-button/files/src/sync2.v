// Synchronizer 2-flop: untuk input asinkron (tombol) sebelum dipakai logika ber-clock.
// Lihat materi "Synchronizer 2-flop".
module sync2 (
    input  wire clk,
    input  wire async_in,
    output wire sync_out
);

    reg meta;
    reg stable;

    initial begin
        meta   = 1'b0;
        stable = 1'b0;
    end

    always @(posedge clk) begin
        meta   <= async_in;
        stable <= meta;
    end

    assign sync_out = stable;

endmodule
