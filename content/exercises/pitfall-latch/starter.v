module pick (
    input  wire       en,
    input  wire       sel,
    input  wire [3:0] a,
    input  wire [3:0] b,
    output reg  [3:0] y
);

    // Kode ini sudah bisa dikompilasi, tapi perilakunya salah. Temukan dan perbaiki.
    always @(*) begin
        if (en) begin
            if (sel)
                y = b;
            else
                y = a;
        end
    end

endmodule
