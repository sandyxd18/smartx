"""Testbench cocotb untuk soal decoder-3to8."""

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



async def check(dut, a: int, en: int):
    dut.a.value = a
    dut.en.value = en
    await Timer(1, unit="ns")
    got = read_int(dut.y, "y")
    want = (1 << a) if en else 0
    assert got == want, f"a = {a}, en = {en}: y = {got:08b}, seharusnya {want:08b}"


@cocotb.test()
async def all_inputs(dut):
    """Semua kombinasi a dan en."""
    for en in (1, 0):
        for a in range(8):
            await check(dut, a, en)


@cocotb.test()
async def random_sequence(dut):
    """Urutan acak (seed tetap)."""
    rng = random.Random(55)
    for _ in range(60):
        await check(dut, rng.randrange(8), rng.randint(0, 1))
