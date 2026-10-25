module pipe2 (
    input  wire       clk,
    input  wire [7:0] d,
    output reg  [7:0] q1,
    output reg  [7:0] q2
);

    always @(posedge clk) begin
        q1 <= d;
        q2 <= q1;
    end

endmodule
