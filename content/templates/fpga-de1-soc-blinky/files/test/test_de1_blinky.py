"""Testbench cocotb untuk src/de1_blinky.v.

Di simulasi, HALF_PERIOD diisi 4 lewat `parameters` di smartx.yaml, supaya satu
kedipan hanya 8 siklus. Build FPGA memakai `fpga.parameters` (25_000_000).
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

HALF_PERIOD = 4  # harus sama dengan parameters.HALF_PERIOD di smartx.yaml


def read_int(signal, name: str) -> int:
    """Baca sinyal sebagai int; beri pesan jelas jika masih X/Z."""
    value = signal.value
    if not value.is_resolvable:
        raise AssertionError(f"{name} bernilai {value} (X/Z). Apakah nilai awal register sudah diisi?")
    return int(value)


def expected_ledr(edges: int, sw: int) -> int:
    """Model referensi: LEDR0 = kedipan XOR SW0, LEDR1-9 = SW1-9."""
    on = (edges // HALF_PERIOD) % 2
    return (sw & 0b1111111110) | (on ^ (sw & 1))


@cocotb.test()
async def blinks_and_follows_switches(dut):
    """Saklar acak (seed tetap) sambil LEDR0 berkedip; bandingkan tiap siklus."""
    rng = random.Random(50)
    dut.SW.value = 0
    # Clock mulai tinggi di t = 0: itu sudah sisi naik pertama.
    cocotb.start_soon(Clock(dut.CLOCK_50, 20, unit="ns").start())
    await FallingEdge(dut.CLOCK_50)
    edges = 1
    for _ in range(12 * HALF_PERIOD):
        sw = rng.randrange(1024)
        dut.SW.value = sw  # diubah di sisi turun clock
        await Timer(1, unit="ns")  # LEDR1-9 tidak menunggu clock
        got = read_int(dut.LEDR, "LEDR")
        want = expected_ledr(edges, sw)
        assert got == want, (
            f"Setelah {edges} sisi naik clock, SW={sw:010b}: LEDR = {got:010b}, "
            f"seharusnya {want:010b}"
        )
        await FallingEdge(dut.CLOCK_50)
        edges += 1
