"""Testbench cocotb untuk soal mux-2to1."""

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
    got = read_int(dut.y, "y")
    want = b if sel else a
    assert got == want, (
        f"a = {a:#04x}, b = {b:#04x}, sel = {sel}: y = {got:#04x}, seharusnya {want:#04x}"
    )


@cocotb.test()
async def selects_each_input(dut):
    """sel = 0 memilih a, sel = 1 memilih b."""
    await check(dut, 0x12, 0xAB, 0)
    await check(dut, 0x12, 0xAB, 1)
    await check(dut, 0xFF, 0x00, 0)
    await check(dut, 0xFF, 0x00, 1)


@cocotb.test()
async def random_data(dut):
    """Data dan sel acak (seed tetap)."""
    rng = random.Random(33)
    for _ in range(200):
        await check(dut, rng.randrange(256), rng.randrange(256), rng.randint(0, 1))
