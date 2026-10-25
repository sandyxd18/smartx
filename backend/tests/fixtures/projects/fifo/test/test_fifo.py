"""FIFO testbench: directed fill/drain plus random traffic against a scoreboard."""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge
from scoreboard import FifoModel

DEPTH = 8  # smartx.yaml overrides the module default of 16


async def start(dut) -> None:
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.din.value = 0
    await FallingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


@cocotb.test()
async def reset_is_empty(dut):
    await start(dut)
    assert int(dut.empty.value) == 1, "Setelah reset FIFO harus kosong"
    assert int(dut.full.value) == 0, "Setelah reset FIFO tidak boleh penuh"


@cocotb.test()
async def fills_to_depth_and_drains_in_order(dut):
    await start(dut)
    written = 0
    dut.wr_en.value = 1
    while int(dut.full.value) == 0:
        dut.din.value = written + 1
        await FallingEdge(dut.clk)
        written += 1
        assert written <= 64, "full tidak pernah 1"
    dut.wr_en.value = 0
    assert written == DEPTH, (
        f"FIFO penuh setelah {written} tulis, seharusnya {DEPTH} (parameter DEPTH)"
    )

    for expected in range(1, DEPTH + 1):
        dut.rd_en.value = 1
        await FallingEdge(dut.clk)
        assert int(dut.dout.value) == expected, f"baca ke-{expected}: dout = {int(dut.dout.value)}"
    dut.rd_en.value = 0
    assert int(dut.empty.value) == 1, "Setelah semua dibaca FIFO harus kosong"


@cocotb.test()
async def random_traffic_matches_scoreboard(dut):
    rng = random.Random(42)
    model = FifoModel(DEPTH)
    await start(dut)
    for cycle in range(500):
        wr = rng.random() < 0.6
        rd = rng.random() < 0.5
        value = rng.randrange(256)
        dut.wr_en.value = int(wr)
        dut.rd_en.value = int(rd)
        dut.din.value = value
        assert int(dut.full.value) == int(model.full), f"siklus {cycle}: full salah"
        assert int(dut.empty.value) == int(model.empty), f"siklus {cycle}: empty salah"
        # The RTL decides on the flags before the clock edge.
        was_full, was_empty = model.full, model.empty
        expected = model.pop() if rd and not was_empty else None
        if wr and not was_full:
            model.push(value)
        await FallingEdge(dut.clk)
        if expected is not None:
            got = int(dut.dout.value)
            assert got == expected, f"siklus {cycle}: dout = {got}, seharusnya {expected}"
