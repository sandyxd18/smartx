module top (input wire clk, input wire a, input wire b, output reg y);
  always @(posedge clk) y <= a;
  always @(posedge clk) y <= b;
endmodule
