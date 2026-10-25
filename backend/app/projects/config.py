"""smartx.yaml: a project's simulation settings. See docs/CONTENT-FORMAT.md.

parse_config() gives errors with YAML line numbers so the editor can mark them;
analyze() adds warnings that need the project's files (patterns that match nothing,
a top module that is not defined, missing test files). Warnings do not block saving.
"""

import re
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from app.projects.paths import InvalidProjectPath, normalize_project_path

CONFIG_PATH = "smartx.yaml"
HEADER = "# Konfigurasi proyek SmartX (lihat docs/CONTENT-FORMAT.md, bagian Proyek workspace).\n"
FIELDS = ("top", "sources", "tests", "simulator", "parameters", "defines")

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_PY_MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_GLOB_SEGMENT = re.compile(r"^[A-Za-z0-9_.*?-]+$")


def _identifier(value: str) -> str:
    if not _IDENTIFIER.match(value):
        raise ValueError(
            f"'{value}' bukan identifier Verilog yang valid "
            "(huruf, angka, '_', diawali huruf atau '_')"
        )
    return value


def _scalar(value: object) -> object:
    # cocotb's runner passes str(value) on the command line (-D, -P, -G): only plain
    # numbers and text make sense there.
    if value is None:
        raise ValueError("beri nilai, misalnya 1")
    if isinstance(value, bool) or not isinstance(value, int | str):
        raise ValueError("nilai harus angka bulat atau teks")
    return value


Name = Annotated[str, BeforeValidator(lambda v: _identifier(v) if isinstance(v, str) else v)]
Scalar = Annotated[int | str, BeforeValidator(_scalar)]


def check_glob(pattern: str) -> str:
    """A relative pattern with '*', '?' and whole-segment '**', using project path rules."""
    if "\\" in pattern:
        raise ValueError("gunakan '/' sebagai pemisah folder, bukan '\\'")
    if pattern.startswith("/") or re.match(r"^[A-Za-z]:", pattern):
        raise ValueError("pola harus relatif terhadap folder proyek")
    for segment in pattern.split("/"):
        if segment in ("", ".", ".."):
            raise ValueError("pola tidak boleh berisi '//', '.', atau '..'")
        if "**" in segment and segment != "**":
            raise ValueError("'**' harus berdiri sendiri di antara '/'")
        if not _GLOB_SEGMENT.match(segment):
            raise ValueError(f"'{segment}' berisi karakter yang tidak diizinkan")
    return pattern


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top: Name
    sources: Annotated[list[str], Field(min_length=1)] = ["src/**/*.v"]
    tests: list[str] = []
    simulator: Literal["icarus", "verilator"] = "icarus"
    parameters: dict[Name, Scalar] = {}
    defines: dict[Name, Scalar] = {}

    @field_validator("sources")
    @classmethod
    def _check_sources(cls, value: list[str]) -> list[str]:
        problems = []
        for i, pattern in enumerate(value):
            try:
                check_glob(pattern)
            except ValueError as exc:
                problems.append(f"sources[{i}]: {exc}")
        if problems:
            raise ValueError("; ".join(problems))
        return value

    @field_validator("tests")
    @classmethod
    def _check_tests(cls, value: list[str]) -> list[str]:
        checked = []
        for i, path in enumerate(value):
            try:
                path = normalize_project_path(path)
            except InvalidProjectPath as exc:
                raise ValueError(f"tests[{i}]: {exc}") from exc
            name = path.rsplit("/", 1)[-1]
            if not name.endswith(".py"):
                raise ValueError(f"tests[{i}]: file testbench cocotb harus berakhiran .py")
            if not _PY_MODULE.match(name[:-3]):
                raise ValueError(
                    f"tests[{i}]: '{name}' bukan nama modul Python yang valid "
                    "(pakai huruf, angka, '_'; misalnya test_fifo.py)"
                )
            checked.append(path)
        return checked

    @model_validator(mode="after")
    def _unique_test_modules(self) -> "ProjectConfig":
        seen: dict[str, str] = {}
        for path in self.tests:
            module = path.rsplit("/", 1)[-1][:-3]
            if module in seen:
                raise ValueError(
                    f"tests: '{seen[module]}' dan '{path}' sama-sama modul '{module}'; "
                    "cocotb memuat test berdasarkan nama modul, jadi namanya harus beda"
                )
            seen[module] = path
        return self


class ConfigProblem(BaseModel):
    severity: Literal["error", "warning"]
    message: str
    line: int | None = None  # 1-based line in smartx.yaml


@dataclass
class ConfigAnalysis:
    config: ProjectConfig | None
    problems: list[ConfigProblem] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)  # matched files, in pattern order


def _loc_text(loc: tuple[int | str, ...]) -> str:
    text = ""
    for part in loc:
        if part == "[key]":
            continue
        if isinstance(part, int):
            text += f"[{part}]"
        else:
            text += f".{part}" if text else str(part)
    return text


def _line_for(node: yaml.Node | None, loc: tuple[int | str, ...]) -> int | None:
    """Line of the YAML node an error location points at; mapping entries use the key."""
    line = None
    for part in loc:
        if part == "[key]":
            continue
        if isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                if key.value == str(part):
                    line = key.start_mark.line + 1
                    node = value
                    break
            else:
                return line
        elif isinstance(node, yaml.SequenceNode) and isinstance(part, int):
            if part >= len(node.value):
                return line
            node = node.value[part]
            line = node.start_mark.line + 1
        else:
            return line
    return line


def _message(error: Any) -> str:
    loc = tuple(error["loc"])
    where = _loc_text(loc)
    kind = error["type"]
    if kind == "missing":
        return f"{where}: wajib diisi"
    if kind == "extra_forbidden":
        return f"{where}: tidak dikenal (yang tersedia: {', '.join(FIELDS)})"
    if kind == "literal_error":
        return f"{where}: harus salah satu dari: icarus, verilator"
    if kind == "too_short":
        return f"{where}: isi minimal satu pola"
    if kind in ("string_type", "str_type"):
        return f"{where}: harus berupa teks"
    if kind == "list_type":
        return f"{where}: harus berupa daftar (baris yang diawali '- ')"
    if kind == "dict_type":
        return f"{where}: harus berupa pasangan kunci: nilai"
    message = str(error["msg"]).removeprefix("Value error, ")
    # Validators that check a whole list already name the item ("sources[1]: ...").
    if not where or message.startswith(f"{where}[") or message.startswith(f"{where}:"):
        return message
    return f"{where}: {message}"


def _error_loc(error: Any) -> tuple[int | str, ...]:
    """Point list-level validator errors at the item they name ("sources[1]: ...")."""
    loc = tuple(error["loc"])
    match = re.match(r"^Value error, (\w+)\[(\d+)\]", str(error["msg"]))
    if match and loc == (match.group(1),):
        return (match.group(1), int(match.group(2)))
    return loc


def _parse(text: str) -> tuple[ProjectConfig | None, list[ConfigProblem], yaml.Node | None]:
    try:
        data = yaml.safe_load(text)
        root = yaml.compose(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        problem = getattr(exc, "problem", None) or str(exc)
        line = mark.line + 1 if mark is not None else None
        return (
            None,
            [ConfigProblem(severity="error", message=f"YAML tidak valid: {problem}", line=line)],
            None,
        )
    if data is None:
        data = {}
    if not isinstance(data, dict):
        message = "smartx.yaml harus berisi pasangan kunci: nilai (misalnya 'top: counter')"
        return None, [ConfigProblem(severity="error", message=message, line=1)], root
    try:
        return ProjectConfig.model_validate(data), [], root
    except ValidationError as exc:
        problems = [
            ConfigProblem(
                severity="error", message=_message(err), line=_line_for(root, _error_loc(err))
            )
            for err in exc.errors()
        ]
        return None, problems, root


def parse_config(text: str) -> tuple[ProjectConfig | None, list[ConfigProblem]]:
    config, problems, _ = _parse(text)
    return config, problems


def dump_config(config: ProjectConfig) -> str:
    """YAML for a config edited in the form. Comments in the old file are not kept."""
    data: dict[str, Any] = {
        "top": config.top,
        "sources": config.sources,
        "tests": config.tests,
        "simulator": config.simulator,
    }
    if config.parameters:
        data["parameters"] = config.parameters
    if config.defines:
        data["defines"] = config.defines
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return HEADER + body


def _glob_regex(pattern: str) -> re.Pattern[str]:
    parts = pattern.split("/")
    regex = ""
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if part == "**":
            regex += ".*" if last else "(?:[^/]+/)*"
            continue
        for ch in part:
            regex += "[^/]*" if ch == "*" else "[^/]" if ch == "?" else re.escape(ch)
        if not last:
            regex += "/"
    return re.compile(regex + r"\Z")


def glob_match(pattern: str, path: str) -> bool:
    """'*' and '?' stay within a folder; '**' spans any number of folders (also none)."""
    return _glob_regex(pattern).match(path) is not None


def analyze(text: str, files: dict[str, str]) -> ConfigAnalysis:
    """Parse text and check it against the project's files (path -> content)."""
    config, problems, root = _parse(text)
    if config is None:
        return ConfigAnalysis(config=None, problems=problems)

    def warn(message: str, loc: tuple[int | str, ...]) -> None:
        problems.append(
            ConfigProblem(severity="warning", message=message, line=_line_for(root, loc))
        )

    sources: list[str] = []
    for i, pattern in enumerate(config.sources):
        matched = sorted(p for p in files if glob_match(pattern, p))
        if not matched:
            warn(f"Pola '{pattern}' tidak cocok dengan file apa pun.", ("sources", i))
        sources += [p for p in matched if p not in sources]

    top = re.compile(rf"^\s*module\s+{re.escape(config.top)}\b", re.MULTILINE)
    if not any(top.search(files[p]) for p in sources):
        warn(f"Modul top '{config.top}' tidak ditemukan di file sumber.", ("top",))

    if not config.tests:
        warn("Belum ada test di 'tests'. Simulasi butuh minimal satu testbench cocotb.", ())
    for i, path in enumerate(config.tests):
        if path not in files:
            warn(f"File test '{path}' tidak ada di proyek.", ("tests", i))

    return ConfigAnalysis(config=config, problems=problems, sources=sources)
