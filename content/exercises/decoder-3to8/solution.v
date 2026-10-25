module decoder3to8 (
    input  wire [2:0] a,
    input  wire       en,
    output wire [7:0] y
);

    assign y = en ? (8'b1 << a) : 8'b0;

endmodule
