"""Testbench cocotb untuk soal counter-4bit.

Pola yang dipakai semua soal: bandingkan DUT dengan model referensi Python
siklus demi siklus, lalu beri pesan error yang bisa dibaca pemula.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge


def read_int(signal, name: str) -> int:
    """Baca sinyal sebagai int; beri pesan jelas jika masih X/Z."""
    value = signal.value
    if not value.is_resolvable:
        raise AssertionError(
            f"{name} bernilai {value} (X/Z). Biasanya karena sinyal belum pernah "
            f"di-assign atau reset belum ditangani."
        )
    return int(value)


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.en.value = 0
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)


@cocotb.test()
async def reset_sets_zero(dut):
    """Setelah reset, q harus 0."""
    await setup(dut)
    q = read_int(dut.q, "q")
    assert q == 0, f"Setelah reset q = {q}, seharusnya 0"


@cocotb.test()
async def counts_and_wraps(dut):
    """Dengan en=1, q naik 1 tiap clock dan kembali ke 0 setelah 15."""
    await setup(dut)
    dut.rst.value = 0
    dut.en.value = 1
    expected = 0
    for cycle in range(20):
        await RisingEdge(dut.clk)
        expected = (expected + 1) % 16
        await FallingEdge(dut.clk)
        got = read_int(dut.q, "q")
        assert got == expected, f"Siklus {cycle}: q = {got}, seharusnya {expected}"


@cocotb.test()
async def random_stimulus(dut):
    """Input acak untuk rst dan en, dibandingkan dengan model referensi."""
    await setup(dut)
    rng = random.Random(1234)
    model = 0
    for cycle in range(200):
        rst = 1 if rng.random() < 0.05 else 0
        en = rng.randint(0, 1)
        dut.rst.value = rst
        dut.en.value = en
        await RisingEdge(dut.clk)
        if rst:
            model = 0
        elif en:
            model = (model + 1) % 16
        await FallingEdge(dut.clk)
        got = read_int(dut.q, "q")
        assert got == model, (
            f"Siklus {cycle} (rst={rst}, en={en}): q = {got}, seharusnya {model}"
        )
