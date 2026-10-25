"""Testbench cocotb untuk soal comparator-4bit."""

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



async def check(dut, a: int, b: int):
    dut.a.value = a
    dut.b.value = b
    await Timer(1, unit="ns")
    got = tuple(read_int(getattr(dut, n), n) for n in ("lt", "eq", "gt"))
    want = (int(a < b), int(a == b), int(a > b))
    assert got == want, (
        f"a = {a}, b = {b}: (lt, eq, gt) = {got}, seharusnya {want}"
    )


@cocotb.test()
async def all_pairs(dut):
    """Semua 256 pasangan a dan b."""
    for a in range(16):
        for b in range(16):
            await check(dut, a, b)


@cocotb.test()
async def random_pairs(dut):
    """Urutan acak (seed tetap)."""
    rng = random.Random(88)
    for _ in range(100):
        await check(dut, rng.randrange(16), rng.randrange(16))
