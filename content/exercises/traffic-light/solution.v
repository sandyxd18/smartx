module traffic (
    input  wire clk,
    input  wire rst,
    output wire green,
    output wire yellow,
    output wire red
);

    localparam GREEN  = 2'd0;
    localparam YELLOW = 2'd1;
    localparam RED    = 2'd2;

    reg [1:0] state;
    reg [2:0] t;  // cycles already spent in this state, minus one

    always @(posedge clk) begin
        if (rst) begin
            state <= GREEN;
            t     <= 3'd0;
        end else begin
            case (state)
                GREEN:
                    if (t == 3'd3) begin state <= YELLOW; t <= 3'd0; end
                    else t <= t + 3'd1;
                YELLOW:
                    if (t == 3'd1) begin state <= RED; t <= 3'd0; end
                    else t <= t + 3'd1;
                default:
                    if (t == 3'd2) begin state <= GREEN; t <= 3'd0; end
                    else t <= t + 3'd1;
            endcase
        end
    end

    assign green  = (state == GREEN);
    assign yellow = (state == YELLOW);
    assign red    = (state == RED);

endmodule
