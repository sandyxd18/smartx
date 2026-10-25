"""Testbench cocotb untuk soal edge-detector."""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

def read_int(signal, name: str) -> int:
    """Baca sinyal sebagai int; beri pesan jelas jika masih X/Z."""
    value = signal.value
    if not value.is_resolvable:
        raise AssertionError(
            f"{name} bernilai {value} (X/Z). Biasanya karena sinyal belum pernah "
            f"di-assign, atau ada dua driver yang saling bertentangan."
        )
    return int(value)


async def setup(dut, **zeros: int):
    """Start the clock and hold reset for one rising edge; inputs start at 0."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for name in zeros:
        getattr(dut, name).value = 0
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


async def feed(dut, bits: list[int], resets: list[int] | None = None):
    prev = rise = fall = 0
    trace = ""
    for cycle, sig in enumerate(bits):
        rst = resets[cycle] if resets else 0
        dut.sig.value = sig
        dut.rst.value = rst
        await RisingEdge(dut.clk)
        if rst:
            prev = rise = fall = 0
        else:
            rise, fall, prev = int(sig and not prev), int(prev and not sig), sig
        trace += str(sig)
        await FallingEdge(dut.clk)
        got = (read_int(dut.rise, "rise"), read_int(dut.fall, "fall"))
        assert got == (rise, fall), (
            f"Siklus {cycle} (sig terakhir: {trace[-6:]}, rst = {rst}): "
            f"(rise, fall) = {got}, seharusnya {(rise, fall)}"
        )


@cocotb.test()
async def pulses_once_per_edge(dut):
    """Satu pulsa per perubahan, bukan selama level bertahan."""
    await setup(dut, sig=0)
    await feed(dut, [0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0])


@cocotb.test()
async def random_signal(dut):
    """Sinyal dan reset acak (seed tetap), dibandingkan dengan model."""
    await setup(dut, sig=0)
    rng = random.Random(1111)
    bits = [rng.randint(0, 1) for _ in range(400)]
    resets = [int(rng.random() < 0.03) for _ in range(400)]
    await feed(dut, bits, resets)
