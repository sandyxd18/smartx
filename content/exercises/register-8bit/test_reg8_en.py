"""Testbench cocotb untuk soal register-8bit."""

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
    dut.d.value = 0
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)


@cocotb.test()
async def reset_and_load(dut):
    """Reset mengosongkan, en memuat d, tanpa en nilai tetap."""
    await setup(dut)
    assert read_int(dut.q, "q") == 0, "Setelah reset q seharusnya 0"
    dut.rst.value = 0
    dut.en.value = 1
    dut.d.value = 0xA5
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    q = read_int(dut.q, "q")
    assert q == 0xA5, f"en = 1, d = 0xA5: q = {q:#04x}, seharusnya 0xa5"
    dut.en.value = 0
    dut.d.value = 0x3C
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    q = read_int(dut.q, "q")
    assert q == 0xA5, f"en = 0: q = {q:#04x}, seharusnya tetap 0xa5"


@cocotb.test()
async def reset_waits_for_clock(dut):
    """Reset sinkron tidak berlaku sebelum sisi naik clock."""
    await setup(dut)
    dut.rst.value = 0
    dut.en.value = 1
    dut.d.value = 0x77
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 1
    await Timer(1, unit="ns")
    q = read_int(dut.q, "q")
    assert q == 0x77, (
        f"rst baru naik, clock belum: q = {q:#04x}, seharusnya masih 0x77 (reset sinkron)"
    )


@cocotb.test()
async def random_stimulus(dut):
    """Input acak (seed tetap), dibandingkan dengan model."""
    await setup(dut)
    rng = random.Random(2020)
    model = 0
    for cycle in range(200):
        rst = 1 if rng.random() < 0.05 else 0
        en = rng.randint(0, 1)
        d = rng.randrange(256)
        dut.rst.value = rst
        dut.en.value = en
        dut.d.value = d
        await RisingEdge(dut.clk)
        if rst:
            model = 0
        elif en:
            model = d
        await FallingEdge(dut.clk)
        q = read_int(dut.q, "q")
        assert q == model, (
            f"Siklus {cycle} (rst = {rst}, en = {en}, d = {d:#04x}): "
            f"q = {q:#04x}, seharusnya {model:#04x}"
        )
