"""Testbench cocotb untuk soal basic-gates."""

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



def model(a: int, b: int) -> dict[str, int]:
    return {
        "y_and": a & b,
        "y_or": a | b,
        "y_xor": a ^ b,
        "y_nand": 1 - (a & b),
        "y_nor": 1 - (a | b),
        "y_xnor": 1 - (a ^ b),
        "y_not": 1 - a,
    }


async def check(dut, a: int, b: int):
    dut.a.value = a
    dut.b.value = b
    await Timer(1, unit="ns")
    for name, want in model(a, b).items():
        got = read_int(getattr(dut, name), name)
        assert got == want, f"a = {a}, b = {b}: {name} = {got}, seharusnya {want}"


@cocotb.test()
async def truth_table(dut):
    """Seluruh tabel kebenaran."""
    for a in (0, 1):
        for b in (0, 1):
            await check(dut, a, b)


@cocotb.test()
async def random_sequence(dut):
    """Urutan input acak (seed tetap)."""
    rng = random.Random(22)
    for _ in range(40):
        await check(dut, rng.randint(0, 1), rng.randint(0, 1))
