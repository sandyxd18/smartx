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


def _edge(text: str, ports: dict[str, str]) -> str:
    """'posedge clk_IBUF_I_O' -> 'posedge clk'."""
    edge, _, net = text.partition(" ")
    if not net:
        edge, net = "", edge
    name = ports.get(net) or clock_name(net)
    return f"{edge} {name}" if edge else name


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


def input_ports(netlist: dict[str, Any], top: str) -> dict[str, str]:
    """Net name -> the top-level input port it carries, from the Yosys netlist.

    In a hierarchical design nextpnr may name the clock after a submodule's net
    (`u_db.clk`). That net is the output of the port's input buffer (Gowin IBUF), so
    it is traced back: net bits -> IBUF output -> IBUF input -> port.
    """
    module = netlist.get("modules", {}).get(top, {})
    port_of = {
        tuple(port.get("bits", [])): name
        for name, port in module.get("ports", {}).items()
        if port.get("direction") == "input"
    }
    for cell in module.get("cells", {}).values():
        if cell.get("type") == "IBUF":
            connections = cell.get("connections", {})
            port = port_of.get(tuple(connections.get("I", [])))
            if port is not None:
                port_of.setdefault(tuple(connections.get("O", [])), port)
    found = {}
    for net, info in module.get("netnames", {}).items():
        port = port_of.get(tuple(info.get("bits", [])))
        if port is not None:
            found[net] = port
    return found


def clocks(report: dict[str, Any], ports: dict[str, str] | None = None) -> list[ClockTiming]:
    """Fmax per clock. `ports` (from input_ports()) names clocks after the top port."""
    return [
        ClockTiming(
            net=net,
            name=(ports or {}).get(net) or clock_name(net),
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


def critical_paths(
    report: dict[str, Any], root: str, ports: dict[str, str] | None = None
) -> list[CriticalPath]:
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
                from_clock=_edge(entry.get("from", ""), ports or {}),
                to_clock=_edge(entry.get("to", ""), ports or {}),
                delay_ns=round(total, 2),
                logic_ns=round(logic, 2),
                routing_ns=round(routing, 2),
                steps=steps,
            )
        )
    return paths
