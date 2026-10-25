"""Testbench cocotb untuk soal counter-updown."""

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



def step(model: int, rst: int, load: int, en: int, up: int, d: int) -> int:
    if rst:
        return 0
    if load:
        return d
    if en:
        return (model + (1 if up else -1)) % 16
    return model


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for name in ("load", "en", "up", "d"):
        getattr(dut, name).value = 0
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


async def apply(dut, cycle: int, model: int, **inputs: int) -> int:
    values = {"rst": 0, "load": 0, "en": 0, "up": 0, "d": 0} | inputs
    for name, value in values.items():
        getattr(dut, name).value = value
    await RisingEdge(dut.clk)
    model = step(model, **values)
    await FallingEdge(dut.clk)
    q = read_int(dut.q, "q")
    shown = ", ".join(f"{k} = {v}" for k, v in values.items())
    assert q == model, f"Siklus {cycle} ({shown}): q = {q}, seharusnya {model}"
    return model


@cocotb.test()
async def counts_down_and_wraps(dut):
    """Turun dari 0 membungkus ke 15."""
    await setup(dut)
    model = 0
    for cycle in range(5):
        model = await apply(dut, cycle, model, en=1, up=0)


@cocotb.test()
async def load_has_priority_over_count(dut):
    """load menang atas en, rst menang atas load."""
    await setup(dut)
    model = await apply(dut, 0, 0, load=1, en=1, up=1, d=9)
    model = await apply(dut, 1, model, en=1, up=1)
    await apply(dut, 2, model, rst=1, load=1, d=5)


@cocotb.test()
async def random_stimulus(dut):
    """Input acak (seed tetap), dibandingkan dengan model."""
    await setup(dut)
    rng = random.Random(3030)
    model = 0
    for cycle in range(300):
        model = await apply(
            dut,
            cycle,
            model,
            rst=int(rng.random() < 0.03),
            load=int(rng.random() < 0.1),
            en=rng.randint(0, 1),
            up=rng.randint(0, 1),
            d=rng.randrange(16),
        )
