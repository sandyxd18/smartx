"""Synthesis warnings worth a beginner's attention, from a Yosys log and netlist.

Yosys prints a lot; only a few messages point at real design mistakes. Each kind
below was produced with the pinned Yosys (0.70+219) on a small design before the
pattern was written (see DECISIONS.md D40). Yosys never reports unused inputs, so
those come from the synthesized netlist instead.
"""

import re
from typing import Any, Literal

from pydantic import BaseModel

WarningKind = Literal[
    "latch", "multi_driven", "undriven", "implicit", "unused_input", "memory_ff", "other"
]


class SynthWarning(BaseModel):
    kind: WarningKind
    signal: str | None = None  # as written in the source: "q", "led[0]"
    module: str | None = None
    file: str | None = None  # project path, when the place is known
    line: int | None = None
    message: str  # Indonesian, says what to do


# Warning: Latch inferred for signal `\top.\q'
#   from process `\top.$/work/project/src/a.v:2$proc$1': ...   (one line in the log)
_LATCH = re.compile(
    r"Latch inferred for signal `\\(?P<module>[^.]+)\.\\(?P<signal>[^']+)' "
    r"from process `[^$]*\$(?P<path>/[^:$]+):(?P<line>\d+)\$"
)
# Warning: multiple conflicting drivers for top.\x:
_MULTI = re.compile(r"multiple conflicting drivers for (?P<module>[^.\s]+)\.\\(?P<signal>\S+?):?$")
# Warning: Wire top.\nodrv is used but has no driver.
_UNDRIVEN = re.compile(r"Wire (?P<module>[^.\s]+)\.\\(?P<signal>\S+) is used but has no driver")
# /work/project/src/a.v:6: Warning: Identifier `\implicit_w' is implicitly declared.
_IMPLICIT = re.compile(
    r"^(?P<path>/\S+?):(?P<line>\d+): Warning: Identifier `\\(?P<signal>[^']+)' "
    r"is implicitly declared"
)
# using FF mapping for memory top.mem   (memory_libmap found no RAM primitive)
_MEMORY_FF = re.compile(r"^using FF mapping for memory (?P<module>[^.\s]+)\.(?P<signal>\S+)$")
_WARNING = re.compile(r"^(?:(?P<path>/\S+?):(?P<line>\d+): )?Warning: (?P<msg>.+)$")

MESSAGES: dict[str, str] = {
    "latch": (
        "Latch terbentuk untuk `{signal}`: ada jalur di blok `always @*` yang tidak memberi "
        "nilai. Beri nilai default di awal blok, atau lengkapi `if` dengan `else` dan `case` "
        "dengan `default`."
    ),
    "multi_driven": (
        "`{signal}` diberi nilai dari lebih dari satu tempat (dua `assign` atau dua blok "
        "`always`). Di hardware itu dua sumber yang saling bertabrakan; tulis sinyal ini di "
        "satu tempat saja."
    ),
    "undriven": (
        "`{signal}` dipakai tetapi tidak pernah diberi nilai, jadi nilainya di FPGA tidak "
        "bisa diandalkan."
    ),
    "implicit": (
        "`{signal}` tidak dideklarasikan, jadi Verilog membuatnya sendiri sebagai wire 1-bit. "
        "Biasanya ini salah ketik nama sinyal. Tulis `` `default_nettype none `` di awal file "
        "supaya kesalahan seperti ini jadi error."
    ),
    "unused_input": (
        "Input `{signal}` tidak dipakai desain, jadi pin-nya tidak berpengaruh. Kalau memang "
        "sengaja, beri nama yang mengandung `unused`."
    ),
    "memory_ff": (
        "Memori `{signal}` tidak bisa dipetakan ke RAM di FPGA, jadi dibangun dari flip-flop "
        "dan banyak LUT. Biasanya karena pola akses yang tidak didukung RAM: reset atau loop "
        "yang menulis banyak alamat sekaligus, atau baca tanpa clock pada memori besar."
    ),
}


def _signal(raw: str) -> str:
    """Yosys names: `\\led [0]` -> led[0]."""
    return raw.replace("\\", "").replace(" [", "[").strip()


def _project_file(path: str, root: str) -> str | None:
    prefix = root.rstrip("/") + "/"
    return path[len(prefix) :] if path.startswith(prefix) else None


def _declaration(name: str, sources: dict[str, str]) -> tuple[str | None, int | None]:
    """The first line that declares `name` (port or net), for warnings Yosys gives no place."""
    base = re.escape(name.split("[")[0])
    decl = re.compile(rf"\b(?:wire|reg|logic|input|output|inout|integer)\b[^;]*\b{base}\b")
    for path, text in sources.items():
        for number, line in enumerate(text.splitlines(), start=1):
            if decl.search(line.split("//")[0]):
                return path, number
    return None, None


def _mentioned(name: str, sources: dict[str, str]) -> bool:
    pattern = re.compile(rf"\b{re.escape(name.split('[')[0])}\b")
    return any(pattern.search(text) for text in sources.values())


def parse_yosys_log(log: str, sources: dict[str, str], root: str) -> list[SynthWarning]:
    """Warnings from a Yosys log. `sources` maps project paths to their text (to find
    declarations); `root` is where the project sat in the container (/work/project)."""
    found: list[SynthWarning] = []

    def add(kind: WarningKind, signal: str, module: str | None, place: tuple[Any, Any]) -> None:
        file, line = place
        found.append(
            SynthWarning(
                kind=kind,
                signal=signal,
                module=module,
                file=file,
                line=line,
                message=MESSAGES[kind].format(signal=signal),
            )
        )

    for raw in log.splitlines():
        text = raw.strip()
        if m := _LATCH.search(text):
            place = (_project_file(m["path"], root), int(m["line"]))
            add("latch", _signal(m["signal"]), m["module"], place)
        elif m := _MULTI.search(text):
            # Yosys also names nets it created while mapping; keep the user's own names.
            if _mentioned(_signal(m["signal"]), sources):
                name = _signal(m["signal"])
                add("multi_driven", name, m["module"], _declaration(name, sources))
        elif m := _UNDRIVEN.search(text):
            name = _signal(m["signal"])
            add("undriven", name, m["module"], _declaration(name, sources))
        elif m := _IMPLICIT.match(text):
            place = (_project_file(m["path"], root), int(m["line"]))
            add("implicit", _signal(m["signal"]), None, place)
        elif m := _MEMORY_FF.match(text):
            name = _signal(m["signal"])
            add("memory_ff", name, m["module"], _declaration(name, sources))
        elif (m := _WARNING.match(text)) and not text.startswith("Warnings:"):
            path = m["path"]
            if path and not path.startswith(root.rstrip("/") + "/"):
                continue  # about Yosys' own library files
            found.append(
                SynthWarning(
                    kind="other",
                    file=_project_file(path, root) if path else None,
                    line=int(m["line"]) if m["line"] else None,
                    message=m["msg"],
                )
            )

    unique = {(w.kind, w.signal, w.file, w.line, w.message): w for w in found}
    return list(unique.values())


def unused_inputs(netlist: dict[str, Any], top: str) -> list[str]:
    """Top-level inputs (or bits of them) that drive nothing after synthesis.

    Input buffers (Gowin IBUF) are looked through: an input that only feeds its own
    buffer, whose output feeds nothing, is unused. Names containing "unused" are
    intentional and skipped, as in lint.
    """
    module = netlist.get("modules", {}).get(top)
    if module is None:
        return []
    read: set[Any] = set()
    buffers: dict[Any, list[Any]] = {}  # buffer input bit -> its output bits
    for cell in module.get("cells", {}).values():
        directions = cell.get("port_directions", {})
        connections = cell.get("connections", {})
        if cell.get("type") == "IBUF":
            for bit in connections.get("I", []):
                buffers[bit] = connections.get("O", [])
            continue
        for port, bits in connections.items():
            if directions.get(port) == "input":
                read.update(bits)
    for port in module.get("ports", {}).values():
        if port.get("direction") == "output":
            read.update(port.get("bits", []))

    def used(bit: Any) -> bool:
        return bit in read or any(b in read for b in buffers.get(bit, []))

    unused: list[str] = []
    for name, port in module.get("ports", {}).items():
        if port.get("direction") != "input" or "unused" in name.lower():
            continue
        bits = port.get("bits", [])
        idle = [i for i, bit in enumerate(bits) if not used(bit)]
        if len(idle) == len(bits):
            unused.append(name)
        else:
            offset = port.get("offset", 0)
            unused += [f"{name}[{i + offset}]" for i in idle]
    return unused


def unused_input_warnings(
    netlist: dict[str, Any], top: str, sources: dict[str, str]
) -> list[SynthWarning]:
    return [
        SynthWarning(
            kind="unused_input",
            signal=name,
            module=top,
            file=(place := _declaration(name, sources))[0],
            line=place[1],
            message=MESSAGES["unused_input"].format(signal=name),
        )
        for name in unused_inputs(netlist, top)
    ]
