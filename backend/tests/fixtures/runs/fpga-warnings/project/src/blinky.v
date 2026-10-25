module blinky (
    input  wire       clk,
    input  wire       btn,
    input  wire       rst_n,
    output reg  [5:0] led
);
    reg [5:0] count = 0;
    always @(posedge clk) count <= count + 1'b1;
    // No else: led keeps its old value when rst_n is 0, so Yosys builds a latch.
    always @* begin
        if (rst_n) led = count;
    end
endmodule
