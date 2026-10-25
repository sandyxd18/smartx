"""Testbench cocotb untuk soal wire-assign."""

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



def reverse4(v: int) -> int:
    return int(f"{v:04b}"[::-1], 2)


async def check(dut, value: int):
    getattr(dut, "in").value = value  # "in" is a Python keyword
    await Timer(1, unit="ns")
    expected = {"out": value, "rev": reverse4(value), "five": 5, "msb": value >> 3}
    for name, want in expected.items():
        got = read_int(getattr(dut, name), name)
        assert got == want, (
            f"in = {value:04b}: {name} = {got:b}, seharusnya {want:b}"
        )


@cocotb.test()
async def all_inputs(dut):
    """Semua 16 nilai in."""
    for value in range(16):
        await check(dut, value)


@cocotb.test()
async def random_order(dut):
    """Nilai acak (seed tetap) supaya urutan tidak berpengaruh."""
    rng = random.Random(11)
    for _ in range(50):
        await check(dut, rng.randrange(16))
