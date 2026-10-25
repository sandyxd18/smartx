from pathlib import Path

from app.jobs.verilator_lint import parse_lint

# Real `verilator --lint-only -Wall` output (5.053), shortened to two findings.
LOG = (Path(__file__).parent / "fixtures" / "lint" / "latch-width.log").read_text(encoding="utf-8")


def test_parses_location_code_and_keeps_verilator_text() -> None:
    latch, width = parse_lint(LOG)

    assert (latch["line"], latch["column"], latch["code"]) == (10, 5, "LATCH")
    assert latch["severity"] == "warning"
    # Indonesian explanation first, Verilator's own words kept for searching.
    assert latch["message"].startswith("Latch tak sengaja")
    assert "Latch inferred for signal 'y'" in latch["message"]

    assert (width["line"], width["column"], width["code"]) == (9, 27, "WIDTHTRUNC")
    assert "generates 4 bits" in width["message"]


def test_unknown_code_still_shown() -> None:
    (diag,) = parse_lint("%Warning-SOMENEW: dut.v:3:1: Something new\n")

    assert diag["code"] == "SOMENEW"
    assert diag["message"] == "Verilator SOMENEW: Something new"


def test_errors_are_advisory_warnings_and_unlocated_lines_are_dropped() -> None:
    log = (
        "%Error: dut.v:3:1: syntax error, unexpected endmodule\n"
        "%Error: Cannot continue\n"
        "%Warning-UNUSEDSIGNAL: other.v:1:1: Signal is not used: 'x'\n"
        "%Error: Exiting due to 1 warning(s)\n"
    )

    assert parse_lint(log) == [
        {
            "line": 3,
            "column": 1,
            "severity": "warning",
            "code": None,
            "message": "Verilator: syntax error, unexpected endmodule",
        }
    ]


def test_empty_log() -> None:
    assert parse_lint("") == []
