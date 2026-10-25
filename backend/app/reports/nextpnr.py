"""nextpnr's JSON report (--report): resource use, Fmax per clock, critical paths.

The report is the source of truth. nextpnr's log prints the same Fmax, but its
"Device utilisation" table comes from before placement and can differ from the
final numbers in the report (blinky: 50 vs 43 LUT4), so the log is not used.
"""

import re
from typing import Any

from pydantic import BaseModel


class ResourceUse(BaseModel):
    label: str  # LUT, FF, BRAM, IO (from the board profile)
    types: list[str]  # nextpnr resource types summed into this row
    used: int
    available: int
    percent: float  # 0..100, one decimal


class ClockTiming(BaseModel):
    net: str  # nextpnr's clock net: clk_IBUF_I_O
    name: str  # the design's port as the user wrote it: clk
    achieved_mhz: float
    target_mhz: float
    met: bool


class PathStep(BaseModel):
    type: str  # clk-to-q, routing, logic, setup
    delay_ns: float
    total_ns: float  # cumulative, as nextpnr's log prints it
    name: str  # net for routing, cell.port otherwise
    file: str | None = None  # project file the net was defined in, if any
    line: int | None = None


class CriticalPath(BaseModel):
    from_clock: str  # "posedge clk"
    to_clock: str
    delay_ns: float
    logic_ns: float
    routing_ns: float
    steps: list[PathStep]


_SOURCE = re.compile(r"^(?P<path>/\S+?):(?P<line>\d+)(?:\.\d+(?:-\d+\.\d+)?)?$")
_CLOCK_NET = re.compile(r"^(?P<port>[A-Za-z_][A-Za-z0-9_]*?)(?:_IBUF_I_O|\$SB_IO_IN.*)$")


def clock_name(net: str) -> str:
    """The port a clock net comes from: clk_IBUF_I_O (Gowin), clk$SB_IO_IN_$glb_clk (iCE40)."""
    match = _CLOCK_NET.match(net)
    return match["port"] if match else net


def _edge(text: str) -> str:
    """'posedge clk_IBUF_I_O' -> 'posedge clk'."""
    edge, _, net = text.partition(" ")
    return f"{edge} {clock_name(net)}" if net else clock_name(edge)


def utilization(report: dict[str, Any], rows: dict[str, list[str]]) -> list[ResourceUse]:
    found = report.get("utilization", {})
    result = []
    for label, types in rows.items():
        used = sum(found.get(t, {}).get("used", 0) for t in types)
        available = sum(found.get(t, {}).get("available", 0) for t in types)
        percent = round(100 * used / available, 1) if available else 0.0
        result.append(
            ResourceUse(label=label, types=types, used=used, available=available, percent=percent)
        )
    return result


def clocks(report: dict[str, Any]) -> list[ClockTiming]:
    return [
        ClockTiming(
            net=net,
            name=clock_name(net),
            achieved_mhz=round(f["achieved"], 2),
            target_mhz=round(f["constraint"], 2),
            met=f["achieved"] >= f["constraint"],
        )
        for net, f in sorted(report.get("fmax", {}).items())
    ]


def _place(sources: list[str], root: str) -> tuple[str | None, int | None]:
    prefix = root.rstrip("/") + "/"
    for source in sources:
        match = _SOURCE.match(source)
        if match and match["path"].startswith(prefix):
            return match["path"][len(prefix) :], int(match["line"])
    return None, None


def critical_paths(report: dict[str, Any], root: str) -> list[CriticalPath]:
    paths = []
    for entry in report.get("critical_paths", []):
        steps: list[PathStep] = []
        total = logic = routing = 0.0
        for step in entry.get("path", []):
            delay = float(step.get("delay", 0))
            total += delay
            if step.get("type") == "routing":
                routing += delay
                name = step.get("net", "")
            else:
                logic += delay
                end = step.get("from", {})
                name = f"{end.get('cell', '')}.{end.get('port', '')}"
            file, line = _place(step.get("sources", []), root)
            steps.append(
                PathStep(
                    type=step.get("type", ""),
                    delay_ns=round(delay, 2),
                    total_ns=round(total, 2),
                    name=name,
                    file=file,
                    line=line,
                )
            )
        paths.append(
            CriticalPath(
                from_clock=_edge(entry.get("from", "")),
                to_clock=_edge(entry.get("to", "")),
                delay_ns=round(total, 2),
                logic_ns=round(logic, 2),
                routing_ns=round(routing, 2),
                steps=steps,
            )
        )
    return paths
