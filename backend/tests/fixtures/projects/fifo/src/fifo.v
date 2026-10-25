// Synchronous FIFO: registered read, one cycle after rd_en.
module fifo #(
    parameter WIDTH = 8,
    parameter DEPTH = 16  // power of two
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             wr_en,
    input  wire [WIDTH-1:0] din,
    input  wire             rd_en,
    output reg  [WIDTH-1:0] dout,
    output wire             full,
    output wire             empty
);
    localparam AW = $clog2(DEPTH);

    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [AW:0]      wptr;
    reg [AW:0]      rptr;

    assign empty = (wptr == rptr);
    assign full  = (wptr[AW-1:0] == rptr[AW-1:0]) && (wptr[AW] != rptr[AW]);

    always @(posedge clk) begin
        if (rst) begin
            wptr <= {(AW + 1){1'b0}};
            rptr <= {(AW + 1){1'b0}};
            dout <= {WIDTH{1'b0}};
        end else begin
            if (wr_en && !full) begin
                mem[wptr[AW-1:0]] <= din;
                wptr <= wptr + 1'b1;
            end
            if (rd_en && !empty) begin
                dout <= mem[rptr[AW-1:0]];
                rptr <= rptr + 1'b1;
            end
        end
    end
endmodule
