"""Testbench cocotb untuk soal seq-detect-moore."""

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


PATTERN = [1, 0, 1, 1]


async def feed(dut, bits: list[int], resets: list[int] | None = None):
    """Feed bits one per clock and compare z with the model after every edge."""
    history: list[int] = []
    for cycle, bit in enumerate(bits):
        rst = resets[cycle] if resets else 0
        dut.x.value = bit
        dut.rst.value = rst
        await RisingEdge(dut.clk)
        history = [] if rst else history + [bit]
        want = int(history[-4:] == PATTERN)
        await FallingEdge(dut.clk)
        z = read_int(dut.z, "z")
        recent = "".join(map(str, history[-6:])) or "(kosong)"
        assert z == want, (
            f"Siklus {cycle} (x = {bit}, rst = {rst}, bit terakhir: {recent}): "
            f"z = {z}, seharusnya {want}"
        )


@cocotb.test()
async def detects_overlapping_patterns(dut):
    """1011011 menyalakan z dua kali (pola tumpang tindih)."""
    await setup(dut, x=0)
    await feed(dut, [1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1])


@cocotb.test()
async def z_ignores_x_mid_cycle(dut):
    """Moore: z tidak ikut berubah saat x berubah di tengah siklus."""
    await setup(dut, x=0)
    await feed(dut, [1, 0, 1, 1])
    z_before = read_int(dut.z, "z")
    dut.x.value = 0
    await Timer(1, unit="ns")
    z_after = read_int(dut.z, "z")
    assert z_before == 1 and z_after == 1, (
        f"z = {z_before} lalu {z_after} setelah x berubah tanpa clock; "
        "pada FSM Moore z hanya boleh berubah di sisi naik clock"
    )


@cocotb.test()
async def random_bits(dut):
    """Bit dan reset acak (seed tetap), dibandingkan dengan model."""
    await setup(dut, x=0)
    rng = random.Random(6060)
    bits = [rng.randint(0, 1) for _ in range(400)]
    resets = [int(rng.random() < 0.02) for _ in range(400)]
    await feed(dut, bits, resets)
