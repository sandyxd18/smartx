module top (input wire clk, input wire [3:0] unused_in, input wire a, output wire y, output wire z);
  wire nodrv;
  reg [7:0] never_read;
  always @(posedge clk) never_read <= never_read + 1;
  assign y = a & nodrv;
  assign z = implicit_w;
endmodule
