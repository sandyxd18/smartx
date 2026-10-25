"""Testbench cocotb untuk soal mux-4to1-case."""

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



async def check(dut, data: list[int], sel: int):
    for port, value in zip("abcd", data):
        getattr(dut, port).value = value
    dut.sel.value = sel
    await Timer(1, unit="ns")
    got = read_int(dut.y, "y")
    want = data[sel]
    assert got == want, (
        f"a,b,c,d = {data}, sel = {sel}: y = {got}, seharusnya {want} (input {'abcd'[sel]})"
    )


@cocotb.test()
async def each_select(dut):
    """Setiap nilai sel memilih input yang benar."""
    data = [1, 2, 4, 8]
    for sel in range(4):
        await check(dut, data, sel)


@cocotb.test()
async def random_data(dut):
    """Data dan sel acak (seed tetap)."""
    rng = random.Random(44)
    for _ in range(200):
        await check(dut, [rng.randrange(16) for _ in range(4)], rng.randrange(4))
