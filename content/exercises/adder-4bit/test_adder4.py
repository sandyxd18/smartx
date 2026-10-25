"""Testbench cocotb untuk soal adder-4bit."""

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



async def check(dut, a: int, b: int, cin: int):
    dut.a.value = a
    dut.b.value = b
    dut.cin.value = cin
    await Timer(1, unit="ns")
    got_sum = read_int(dut.sum, "sum")
    got_cout = read_int(dut.cout, "cout")
    total = a + b + cin
    want_sum, want_cout = total & 0xF, total >> 4
    assert (got_sum, got_cout) == (want_sum, want_cout), (
        f"{a} + {b} + {cin} = {total}: sum = {got_sum}, cout = {got_cout}; "
        f"seharusnya sum = {want_sum}, cout = {want_cout}"
    )


@cocotb.test()
async def all_combinations(dut):
    """Semua 512 kombinasi a, b, cin."""
    for cin in (0, 1):
        for a in range(16):
            for b in range(16):
                await check(dut, a, b, cin)


@cocotb.test()
async def random_inputs(dut):
    """Urutan acak (seed tetap)."""
    rng = random.Random(77)
    for _ in range(100):
        await check(dut, rng.randrange(16), rng.randrange(16), rng.randint(0, 1))
