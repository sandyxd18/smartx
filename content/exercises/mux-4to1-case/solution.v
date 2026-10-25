module mux4 (
    input  wire [3:0] a,
    input  wire [3:0] b,
    input  wire [3:0] c,
    input  wire [3:0] d,
    input  wire [1:0] sel,
    output reg  [3:0] y
);

    always @(*) begin
        case (sel)
            2'd0:    y = a;
            2'd1:    y = b;
            2'd2:    y = c;
            default: y = d;
        endcase
    end

endmodule
