"""Testbench cocotb untuk soal seq-detect-mealy."""

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
    """Set x, check z *before* the clock edge (Mealy), then let the edge read x."""
    history: list[int] = []
    for cycle, bit in enumerate(bits):
        rst = resets[cycle] if resets else 0
        dut.x.value = bit
        dut.rst.value = rst
        await Timer(1, unit="ns")
        want = int(history[-2:] == [1, 0] and bit == 1)
        z = read_int(dut.z, "z")
        recent = "".join(map(str, history[-4:])) or "(kosong)"
        assert z == want, (
            f"Siklus {cycle} (bit terakhir dibaca: {recent}, x sekarang = {bit}): "
            f"z = {z}, seharusnya {want}"
            + (" (Mealy: z harus menyala sebelum clock naik)" if want else "")
        )
        await RisingEdge(dut.clk)
        history = [] if rst else history + [bit]
        await FallingEdge(dut.clk)


@cocotb.test()
async def detects_overlapping_patterns(dut):
    """10101 menyalakan z dua kali, di siklus yang sama dengan bit terakhir."""
    await setup(dut, x=0)
    await feed(dut, [1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1])


@cocotb.test()
async def random_bits(dut):
    """Bit dan reset acak (seed tetap), dibandingkan dengan model."""
    await setup(dut, x=0)
    rng = random.Random(7070)
    bits = [rng.randint(0, 1) for _ in range(400)]
    resets = [int(rng.random() < 0.02) for _ in range(400)]
    await feed(dut, bits, resets)
