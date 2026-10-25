// Counter 8-bit: reset sinkron, enable, dan sinyal wrap satu siklus saat 255 -> 0.
module counter (
    input  wire       clk,
    input  wire       rst,
    input  wire       en,
    output reg  [7:0] count,
    output wire       wrap
);

    assign wrap = en && (count == 8'hFF);

    always @(posedge clk) begin
        if (rst)
            count <= 8'd0;
        else if (en)
            count <= count + 8'd1;
    end

endmodule
