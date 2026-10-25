"""Testbench cocotb untuk soal pitfall-multi-driven."""

import random

import cocotb
from cocotb.triggers import Timer

def read_int(signal, name: str) -> int:
    """Baca sinyal sebagai int; beri pesan jelas jika masih X/Z."""
    value = signal.value
    if not value.is_resolvable:
        raise AssertionError(
            f"{name} bernilai {value} (X/Z). Biasanya karena sinyal belum pernah "
            f"di-assign, atau ada dua driver yang saling bertentangan."
        )
    return int(value)



async def check(dut, a: int, b: int, sel: int):
    dut.a.value = a
    dut.b.value = b
    dut.sel.value = sel
    await Timer(1, unit="ns")
    got = read_int(dut.y, f"y (a = {a}, b = {b}, sel = {sel})")
    want = (a | b) if sel else (a & b)
    assert got == want, f"a = {a}, b = {b}, sel = {sel}: y = {got}, seharusnya {want}"


@cocotb.test()
async def truth_table(dut):
    """Semua kombinasi a, b, sel."""
    for sel in (0, 1):
        for a in (0, 1):
            for b in (0, 1):
                await check(dut, a, b, sel)


@cocotb.test()
async def random_inputs(dut):
    """Input acak (seed tetap)."""
    rng = random.Random(1414)
    for _ in range(50):
        await check(dut, rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1))
