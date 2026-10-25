module top (input wire clk, input wire a, input wire b, output wire y);
  wire x;
  assign x = a;
  assign x = b;
  assign y = x;
endmodule
