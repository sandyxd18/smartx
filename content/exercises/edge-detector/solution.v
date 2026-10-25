module edge_detect (
    input  wire clk,
    input  wire rst,
    input  wire sig,
    output reg  rise,
    output reg  fall
);

    reg prev;

    always @(posedge clk) begin
        if (rst) begin
            prev <= 1'b0;
            rise <= 1'b0;
            fall <= 1'b0;
        end else begin
            rise <= sig & ~prev;
            fall <= ~sig & prev;
            prev <= sig;
        end
    end

endmodule
