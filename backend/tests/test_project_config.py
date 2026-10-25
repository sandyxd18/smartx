import pytest

from app.projects.config import (
    ProjectConfig,
    analyze,
    dump_config,
    glob_match,
    parse_config,
)

VALID = """\
# komentar
top: fifo
sources:
  - src/**/*.v
tests:
  - test/test_fifo.py
simulator: verilator
parameters:
  DEPTH: 16
  INIT: "8'hFF"
defines:
  SIM: 1
  MODE: fast
"""


def errors(text: str) -> list[tuple[int | None, str]]:
    config, problems = parse_config(text)
    assert config is None
    return [(p.line, p.message) for p in problems if p.severity == "error"]


class TestParse:
    def test_full_config(self) -> None:
        config, problems = parse_config(VALID)

        assert problems == []
        assert config == ProjectConfig(
            top="fifo",
            sources=["src/**/*.v"],
            tests=["test/test_fifo.py"],
            simulator="verilator",
            parameters={"DEPTH": 16, "INIT": "8'hFF"},
            defines={"SIM": 1, "MODE": "fast"},
        )

    def test_defaults(self) -> None:
        config, problems = parse_config("top: top\n")

        assert problems == []
        assert config is not None
        assert config.sources == ["src/**/*.v"]
        assert config.tests == []
        assert config.simulator == "icarus"
        assert config.parameters == {} and config.defines == {}

    def test_yaml_syntax_error_has_a_line(self) -> None:
        ((line, message),) = errors("top: fifo\nsources: [src/*.v\n")
        assert line == 2 or line == 3
        assert "YAML" in message

    def test_not_a_mapping(self) -> None:
        ((line, message),) = errors("- top\n- fifo\n")
        assert "pasangan kunci: nilai" in message

    def test_empty_file(self) -> None:
        ((_, message),) = errors("")
        assert "top" in message

    @pytest.mark.parametrize(
        ("text", "line", "fragment"),
        [
            ("top: 9lives\n", 1, "identifier Verilog"),
            ("sources: [a.v]\n", None, "top: wajib diisi"),
            ("top: a\nsimulater: icarus\n", 2, "simulater: tidak dikenal"),
            ("top: a\nsimulator: questa\n", 2, "icarus, verilator"),
            ("top: a\nsources: []\n", 2, "minimal satu"),
            ("top: a\nsources:\n  - ok/*.v\n  - ../x.v\n", 4, "sources[1]"),
            ("top: a\nsources:\n  - /abs/*.v\n", 3, "relatif"),
            ("top: a\ntests:\n  - test/test-fifo.py\n", 3, "nama modul Python"),
            ("top: a\ntests:\n  - test/test_fifo.v\n", 3, ".py"),
            ("top: a\ntests:\n  - a/test_x.py\n  - b/test_x.py\n", None, "test_x"),
            ("top: a\nparameters:\n  W: true\n", 3, "parameters.W"),
            ("top: a\nparameters:\n  2W: 4\n", 3, "identifier Verilog"),
            ("top: a\ndefines:\n  SIM:\n", 3, "beri nilai"),
            ("top: a\ndefines:\n  SIM: [1, 2]\n", 3, "defines.SIM"),
        ],
    )
    def test_validation_errors_point_at_the_line(
        self, text: str, line: int | None, fragment: str
    ) -> None:
        found = errors(text)
        assert any(fragment in message for _, message in found), found
        if line is not None:
            assert line in [ln for ln, message in found if fragment in message], found


class TestDump:
    def test_round_trip(self) -> None:
        config, _ = parse_config(VALID)
        assert config is not None

        text = dump_config(config)

        assert text.startswith("# Konfigurasi proyek SmartX")
        assert parse_config(text) == (config, [])
        # Field order follows the documentation.
        keys = [line.split(":")[0] for line in text.splitlines() if line and line[0].isalpha()]
        assert keys == ["top", "sources", "tests", "simulator", "parameters", "defines"]

    def test_leaves_out_empty_parameters_and_defines(self) -> None:
        text = dump_config(ProjectConfig(top="top"))
        assert "parameters" not in text and "defines" not in text
        assert "tests: []" in text

    def test_quotes_strings_that_look_like_numbers(self) -> None:
        config = ProjectConfig(top="t", parameters={"W": "8"}, defines={"V": "true"})
        assert parse_config(dump_config(config))[0] == config


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("src/**/*.v", "src/a.v", True),
        ("src/**/*.v", "src/x/y/a.v", True),
        ("src/**/*.v", "src/a.sv", False),
        ("src/**/*.v", "lib/a.v", False),
        ("src/*.v", "src/x/a.v", False),
        ("**/*.v", "a.v", True),
        ("**/*.v", "deep/er/a.v", True),
        ("src/alu?.v", "src/alu1.v", True),
        ("src/alu?.v", "src/alu12.v", False),
        ("top.v", "top.v", True),
        ("src/*.v", "src/.v", True),
    ],
)
def test_glob_match(pattern: str, path: str, expected: bool) -> None:
    assert glob_match(pattern, path) is expected


class TestAnalyze:
    FILES = {
        "smartx.yaml": "",
        "src/fifo.v": "// FIFO\nmodule fifo #(parameter DEPTH = 4) (\n  input clk\n);\nendmodule\n",
        "src/util/sync.v": "module sync; endmodule\n",
        "src/notes.md": "module fifo",  # not a source: does not match *.v
        "test/test_fifo.py": "import cocotb\n",
    }

    def test_lists_matched_sources_in_pattern_order(self) -> None:
        text = "top: fifo\nsources:\n  - src/util/*.v\n  - src/**/*.v\ntests: [test/test_fifo.py]\n"
        result = analyze(text, self.FILES)

        assert result.problems == []
        assert result.sources == ["src/util/sync.v", "src/fifo.v"]

    def test_warnings_do_not_block(self) -> None:
        text = (
            "top: fifo_top\nsources:\n  - src/**/*.v\n  - rtl/*.v\n"
            "tests:\n  - test/test_missing.py\n"
        )
        result = analyze(text, self.FILES)

        assert result.config is not None
        warnings = [(p.line, p.message) for p in result.problems if p.severity == "warning"]
        assert any("rtl/*.v" in m and "tidak cocok" in m and ln == 4 for ln, m in warnings)
        assert any("fifo_top" in m for _, m in warnings)
        assert any("test/test_missing.py" in m and ln == 6 for ln, m in warnings)

    def test_no_tests_is_a_hint(self) -> None:
        result = analyze("top: fifo\n", self.FILES)
        assert [p.message for p in result.problems] == [
            "Belum ada test di 'tests'. Simulasi butuh minimal satu testbench cocotb."
        ]

    def test_errors_skip_the_file_checks(self) -> None:
        result = analyze("top: [\n", self.FILES)
        assert result.config is None
        assert result.sources == []
        assert all(p.severity == "error" for p in result.problems)
