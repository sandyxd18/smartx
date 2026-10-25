"""Messages about a project's files, shared by the lint, sim and fpga jobs."""

import re
from typing import Any, Literal

from pydantic import BaseModel

from app.jobs.verilator_lint import describe


class ProjectDiagnostic(BaseModel):
    file: str  # project path
    line: int
    col: int | None = None  # 1-based; Icarus gives none
    end_col: int | None = None  # exclusive
    severity: Literal["error", "warning"]
    code: str | None = None
    message: str


# Icarus: "/work/project/src/a.v:12: [error: |warning: ]message"
# Yosys:  "/work/project/src/a.v:12: ERROR: message"
_ICARUS = re.compile(
    r"^(?P<path>/\S+?):(?P<line>\d+): (?:(?P<sev>error|warning): |ERROR: )?(?P<msg>.*)$"
)
# Verilator: "%Error[-CODE]: /work/project/src/a.v:12:5: message"
_VERILATOR = re.compile(
    r"^%(?P<sev>Error|Warning)(?:-(?P<code>[A-Z0-9_]+))?: "
    r"(?P<path>/\S+?):(?P<line>\d+):(?P<col>\d+): (?P<msg>.*)$"
)


def parse_compile_log(log: str, root: str) -> list[dict[str, Any]]:
    """Compiler messages (Icarus, Verilator, Yosys) about files under root, sorted by place."""
    prefix = root.rstrip("/") + "/"
    found = []
    for raw in log.splitlines():
        line = raw.strip()
        if match := _VERILATOR.match(line):
            code = match["code"]
            col = int(match["col"])
            entry = {
                "line": int(match["line"]),
                "col": col,
                "end_col": None,
                "severity": "error" if match["sev"] == "Error" else "warning",
                "code": code,
                "message": describe(code, match["msg"].strip()),
            }
        elif match := _ICARUS.match(line):
            entry = {
                "line": int(match["line"]),
                "col": None,
                "end_col": None,
                "severity": match["sev"] or "error",
                "code": None,
                "message": match["msg"].strip(),
            }
        else:
            continue
        path = match["path"]
        if path.startswith(prefix):  # not cocotb's own files
            found.append({"file": path[len(prefix) :], **entry})
    unique = {(d["file"], d["line"], d["col"], d["message"]): d for d in found}
    return sorted(unique.values(), key=lambda d: (d["file"], d["line"], d["col"] or 0))
