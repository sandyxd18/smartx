module top (input wire clk, input wire sel, input wire [3:0] d, output reg [3:0] q);
  always @* begin
    if (sel) q = d;
  end
endmodule
