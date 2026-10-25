module top (input wire clk, input wire we, input wire [7:0] addr, input wire [7:0] wa, input wire [7:0] d, output wire [7:0] q, output wire [7:0] q2);
  reg [7:0] mem [0:255];
  always @(posedge clk) if (we) mem[wa] <= d;
  integer i;
  always @(posedge clk) if (!we) for (i = 0; i < 4; i = i + 1) mem[i] <= 0;
  assign q = mem[addr];
  assign q2 = mem[addr+1];
endmodule
