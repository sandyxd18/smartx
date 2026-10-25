module shift8 (
    input  wire       clk,
    input  wire       rst,
    input  wire       en,
    input  wire       sin,
    output reg  [7:0] q,
    output wire       sout
);

    always @(posedge clk) begin
        if (rst)
            q <= 8'd0;
        else if (en)
            q <= {q[6:0], sin};
    end

    assign sout = q[7];

endmodule
