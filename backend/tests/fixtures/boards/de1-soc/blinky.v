module blinky (
    input  wire       CLOCK_50,
    output wire [9:0] LEDR
);
    reg [24:0] count;
    reg        on;
    initial begin
        count = 0;
        on = 1'b0;
    end
    always @(posedge CLOCK_50) begin
        if (count == 25'd24_999_999) begin
            count <= 0;
            on <= ~on;
        end else begin
            count <= count + 1'b1;
        end
    end
    assign LEDR = {9'b0, on};
endmodule
