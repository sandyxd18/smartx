"""Turn `verilator --lint-only -Wall` output into editor diagnostics.

parse_lint() reads the text output about one file (the grade job's dut.v); there lint
is advisory, so every finding is a warning. parse_sarif() reads the SARIF file the
project lint job asks for (--diagnostics-sarif-output) and keeps Verilator's levels.
"""

import re
from typing import Any
from urllib.parse import unquote, urlparse

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
        findings.append(
            {
                "line": int(match["line"]),
                "column": int(match["col"]),
                "severity": "warning",
                "code": code,
                "message": describe(code, match["text"].strip()),
            }
        )
    return findings


def describe(code: str | None, text: str) -> str:
    """Indonesian hint first (when known), Verilator's own words kept for searching."""
    label = f"Verilator {code}" if code else "Verilator"
    hint = HINTS.get(code or "")
    return f"{hint} ({label}: {text})" if hint else f"{label}: {text}"


def parse_sarif(data: dict[str, Any], root: str) -> list[dict[str, Any]]:
    """Located findings in files under `root` (an absolute folder in the container).

    Paths come back relative to root; results without a location ("Cannot continue")
    and in other files (Verilator's own includes) are dropped.
    """
    prefix = root.rstrip("/") + "/"
    findings = []
    for run in data.get("runs", []):
        for result in run.get("results", []):
            locations = result.get("locations") or []
            physical = locations[0].get("physicalLocation", {}) if locations else {}
            uri = physical.get("artifactLocation", {}).get("uri")
            region = physical.get("region") or {}
            if not uri or "startLine" not in region:
                continue
            path = unquote(urlparse(uri).path)
            if not path.startswith(prefix):
                continue
            code = result.get("ruleId")
            # The first line is the message; the rest are notes and links.
            text = str(result.get("message", {}).get("text", "")).split("\n", 1)[0].strip()
            col = int(region.get("startColumn", 1))
            findings.append(
                {
                    "file": path[len(prefix) :],
                    "line": int(region["startLine"]),
                    "col": col,
                    "end_col": int(region.get("endColumn", col + 1)),
                    "severity": "error" if result.get("level") == "error" else "warning",
                    "code": code,
                    "message": describe(code, text),
                }
            )
    return sorted(findings, key=lambda f: (f["file"], f["line"], f["col"]))
