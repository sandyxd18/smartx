module blinky (
    input  wire       clk,
    input  wire       rst_n,
    output wire [5:0] led
);
    reg [24:0] count
    reg [5:0] state = 6'b000001;
    always @(posedge clk) begin
        if (!rst_n) begin
            count <= 0;
            state <= 6'b000001;
        end else if (count == 25'd13_499_999) begin
            count <= 0;
            state <= {state[4:0], state[5]};
        end else begin
            count <= count + 1'b1;
        end
    end
    assign led = ~state;
endmodule
