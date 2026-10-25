module wire_assign (
    input  wire [3:0] in,
    output wire [3:0] out,
    output wire [3:0] rev,
    output wire [3:0] five,
    output wire       msb
);

    assign out  = in;
    assign rev  = {in[0], in[1], in[2], in[3]};
    assign five = 4'd5;
    assign msb  = in[3];

endmodule
