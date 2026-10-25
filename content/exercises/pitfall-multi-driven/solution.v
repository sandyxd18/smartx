module logic_sel (
    input  wire a,
    input  wire b,
    input  wire sel,
    output wire y
);

    assign y = sel ? (a | b) : (a & b);

endmodule
