module seq1011 (
    input  wire clk,
    input  wire rst,
    input  wire x,
    output wire z
);

    localparam S_IDLE = 3'd0;  // nothing useful seen
    localparam S_1    = 3'd1;  // "1"
    localparam S_10   = 3'd2;  // "10"
    localparam S_101  = 3'd3;  // "101"
    localparam S_FOUND = 3'd4; // "1011"

    reg [2:0] state;

    always @(posedge clk) begin
        if (rst)
            state <= S_IDLE;
        else begin
            case (state)
                S_IDLE:  state <= x ? S_1     : S_IDLE;
                S_1:     state <= x ? S_1     : S_10;
                S_10:    state <= x ? S_101   : S_IDLE;
                S_101:   state <= x ? S_FOUND : S_10;
                S_FOUND: state <= x ? S_1     : S_10;
                default: state <= S_IDLE;
            endcase
        end
    end

    assign z = (state == S_FOUND);

endmodule
