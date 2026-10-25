module pick (
    input  wire       en,
    input  wire       sel,
    input  wire [3:0] a,
    input  wire [3:0] b,
    output reg  [3:0] y
);

    always @(*) begin
        y = 4'd0;  // every path assigns y: no latch
        if (en) begin
            if (sel)
                y = b;
            else
                y = a;
        end
    end

endmodule
