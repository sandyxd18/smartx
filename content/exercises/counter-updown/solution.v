module counter_ud (
    input  wire       clk,
    input  wire       rst,
    input  wire       load,
    input  wire       en,
    input  wire       up,
    input  wire [3:0] d,
    output reg  [3:0] q
);

    always @(posedge clk) begin
        if (rst)
            q <= 4'd0;
        else if (load)
            q <= d;
        else if (en)
            q <= up ? q + 4'd1 : q - 4'd1;
    end

endmodule
