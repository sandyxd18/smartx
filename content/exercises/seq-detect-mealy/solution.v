module seq101 (
    input  wire clk,
    input  wire rst,
    input  wire x,
    output wire z
);

    localparam S_IDLE = 2'd0;  // nothing useful seen
    localparam S_1    = 2'd1;  // "1"
    localparam S_10   = 2'd2;  // "10"

    reg [1:0] state;

    always @(posedge clk) begin
        if (rst)
            state <= S_IDLE;
        else begin
            case (state)
                S_IDLE:  state <= x ? S_1 : S_IDLE;
                S_1:     state <= x ? S_1 : S_10;
                S_10:    state <= x ? S_1 : S_IDLE;
                default: state <= S_IDLE;
            endcase
        end
    end

    assign z = (state == S_10) && x;

endmodule
