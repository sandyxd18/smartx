module logic_sel (
    input  wire a,
    input  wire b,
    input  wire sel,
    output wire y
);

    // Kode ini sudah bisa dikompilasi, tapi perilakunya salah. Temukan dan perbaiki.
    assign y = a & b;   // dipakai saat sel = 0
    assign y = a | b;   // dipakai saat sel = 1

endmodule
