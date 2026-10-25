"""Testbench cocotb untuk soal shift-register."""

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



async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.en.value = 0
    dut.sin.value = 0
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


async def apply(dut, cycle: int, model: int, rst: int, en: int, sin: int) -> int:
    dut.rst.value = rst
    dut.en.value = en
    dut.sin.value = sin
    await RisingEdge(dut.clk)
    if rst:
        model = 0
    elif en:
        model = ((model << 1) | sin) & 0xFF
    await FallingEdge(dut.clk)
    q = read_int(dut.q, "q")
    sout = read_int(dut.sout, "sout")
    assert q == model, (
        f"Siklus {cycle} (rst = {rst}, en = {en}, sin = {sin}): "
        f"q = {q:08b}, seharusnya {model:08b}"
    )
    assert sout == model >> 7, f"Siklus {cycle}: sout = {sout}, seharusnya q[7] = {model >> 7}"
    return model


@cocotb.test()
async def shifts_in_a_byte(dut):
    """Delapan bit masuk berurutan membentuk satu byte."""
    await setup(dut)
    model = 0
    for cycle, bit in enumerate([1, 0, 1, 1, 0, 0, 1, 0]):
        model = await apply(dut, cycle, model, 0, 1, bit)
    assert model == 0b10110010


@cocotb.test()
async def random_stimulus(dut):
    """Input acak (seed tetap), dibandingkan dengan model."""
    await setup(dut)
    rng = random.Random(4040)
    model = 0
    for cycle in range(250):
        rst = int(rng.random() < 0.03)
        model = await apply(dut, cycle, model, rst, rng.randint(0, 1), rng.randint(0, 1))
