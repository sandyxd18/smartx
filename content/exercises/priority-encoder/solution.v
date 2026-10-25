module prio_enc8 (
    input  wire [7:0] req,
    output reg  [2:0] idx,
    output reg        valid
);

    integer i;

    always @(*) begin
        idx   = 3'd0;
        valid = 1'b0;
        // Lower bits first, so a higher set bit overwrites the result.
        for (i = 0; i < 8; i = i + 1) begin
            if (req[i]) begin
                idx   = i[2:0];
                valid = 1'b1;
            end
        end
    end

endmodule
