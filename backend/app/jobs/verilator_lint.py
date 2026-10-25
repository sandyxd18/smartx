"""Parse `verilator --lint-only -Wall` output into editor diagnostics.

Lint is advisory: the simulation decides pass/fail. Every finding is therefore a
warning, including Verilator's own %Error lines (it is stricter than Icarus).
"""

import re
from typing import Any

# "%Warning-LATCH: dut.v:10:5: message" or "%Error: dut.v:3:1: message" (Verilator 5.053).
# Continuation lines ("   : ... note", source excerpts) start with spaces and do not match.
_FINDING = re.compile(
    r"^%(?:Warning|Error)(?:-(?P<code>[A-Z0-9_]+))?: "
    r"(?:\S*/)?dut\.v:(?P<line>\d+):(?P<col>\d+): (?P<text>.*)$"
)

# Short Indonesian explanations for the warnings beginners meet most often.
HINTS: dict[str, str] = {
    "LATCH": "Latch tak sengaja: tidak semua cabang di always kombinasional memberi nilai",
    "CASEINCOMPLETE": "case tidak mencakup semua nilai; tambahkan default",
    "BLKSEQ": "Pakai <= (non-blocking) di always @(posedge clk)",
    "COMBDLY": "Pakai = (blocking) di always kombinasional",
    "BLKANDNBLK": "Sinyal diberi nilai dengan = dan <= sekaligus",
    "MULTIDRIVEN": "Sinyal diberi nilai dari lebih dari satu tempat",
    "MULTIDRIVENPROC": "Sinyal diberi nilai dari lebih dari satu blok always",
    "WIDTHEXPAND": "Lebar bit berbeda: nilai yang lebih sempit diperlebar",
    "WIDTHTRUNC": "Lebar bit berbeda: bit atas akan terpotong",
    "WIDTH": "Lebar bit kedua sisi berbeda",
    "UNDRIVEN": "Sinyal tidak pernah diberi nilai",
    "UNUSEDSIGNAL": "Sinyal tidak dipakai",
    "UNUSEDPARAM": "Parameter tidak dipakai",
    "IMPLICIT": "Sinyal dipakai tanpa dideklarasikan (jadi wire 1 bit implisit)",
    "PINMISSING": "Ada port modul yang tidak disambungkan",
}


def parse_lint(log: str) -> list[dict[str, Any]]:
    """Findings about the user's code (dut.v), in Verilator's order."""
    findings = []
    for raw in log.splitlines():
        match = _FINDING.match(raw)
        if not match:
            continue
        code = match["code"]
        text = match["text"].strip()
        label = f"Verilator {code}" if code else "Verilator"
        hint = HINTS.get(code or "")
        findings.append(
            {
                "line": int(match["line"]),
                "column": int(match["col"]),
                "severity": "warning",
                "code": code,
                "message": f"{hint} ({label}: {text})" if hint else f"{label}: {text}",
            }
        )
    return findings
