"""Testbench cocotb untuk soal lfsr-8bit."""

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



def step(q: int) -> int:
    fb = ((q >> 7) ^ (q >> 5) ^ (q >> 4) ^ (q >> 3)) & 1
    return ((q << 1) | fb) & 0xFF


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.en.value = 0
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


@cocotb.test()
async def reset_value(dut):
    """Setelah reset q = 0x01."""
    await setup(dut)
    q = read_int(dut.q, "q")
    assert q == 0x01, f"Setelah reset q = {q:#04x}, seharusnya 0x01"


@cocotb.test()
async def full_period(dut):
    """255 langkah melewati semua nilai bukan nol lalu kembali ke 0x01."""
    await setup(dut)
    dut.en.value = 1
    model = 1
    seen = set()
    for cycle in range(255):
        await RisingEdge(dut.clk)
        model = step(model)
        await FallingEdge(dut.clk)
        q = read_int(dut.q, "q")
        assert q == model, (
            f"Langkah {cycle + 1}: q = {q:#04x}, seharusnya {model:#04x}"
        )
        seen.add(q)
    assert model == 1 and len(seen) == 255


@cocotb.test()
async def random_enable(dut):
    """en dan reset acak (seed tetap), dibandingkan dengan model."""
    await setup(dut)
    rng = random.Random(5050)
    model = 1
    for cycle in range(300):
        rst = int(rng.random() < 0.02)
        en = rng.randint(0, 1)
        dut.rst.value = rst
        dut.en.value = en
        await RisingEdge(dut.clk)
        if rst:
            model = 1
        elif en:
            model = step(model)
        await FallingEdge(dut.clk)
        q = read_int(dut.q, "q")
        assert q == model, (
            f"Siklus {cycle} (rst = {rst}, en = {en}): q = {q:#04x}, seharusnya {model:#04x}"
        )
