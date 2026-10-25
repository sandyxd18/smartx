"""Testbench cocotb untuk soal pitfall-latch."""

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



def model(en: int, sel: int, a: int, b: int) -> int:
    return (b if sel else a) if en else 0


async def check(dut, en: int, sel: int, a: int, b: int):
    dut.en.value = en
    dut.sel.value = sel
    dut.a.value = a
    dut.b.value = b
    await Timer(1, unit="ns")
    got = read_int(dut.y, "y")
    want = model(en, sel, a, b)
    hint = ""
    if not en and got != 0:
        hint = (
            ". y masih menyimpan nilai lama padahal tidak ada clock: itu latch. "
            "Ada jalur di always @(*) yang tidak meng-assign y."
        )
    assert got == want, f"en = {en}, sel = {sel}, a = {a}, b = {b}: y = {got}, seharusnya {want}{hint}"


@cocotb.test()
async def disabled_output_is_zero(dut):
    """Setelah en turun, y harus 0, bukan nilai sebelumnya."""
    await check(dut, 1, 0, 5, 9)
    await check(dut, 0, 0, 5, 9)
    await check(dut, 1, 1, 5, 9)
    await check(dut, 0, 1, 5, 9)


@cocotb.test()
async def random_inputs(dut):
    """Input acak (seed tetap)."""
    rng = random.Random(1212)
    for _ in range(300):
        await check(dut, rng.randint(0, 1), rng.randint(0, 1), rng.randrange(16), rng.randrange(16))
