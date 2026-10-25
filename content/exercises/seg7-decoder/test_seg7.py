"""Testbench cocotb untuk soal seg7-decoder."""

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



PATTERNS = {
    0x0: 0b1111110,
    0x1: 0b0110000,
    0x2: 0b1101101,
    0x3: 0b1111001,
    0x4: 0b0110011,
    0x5: 0b1011011,
    0x6: 0b1011111,
    0x7: 0b1110000,
    0x8: 0b1111111,
    0x9: 0b1111011,
    0xA: 0b1110111,
    0xB: 0b0011111,
    0xC: 0b1001110,
    0xD: 0b0111101,
    0xE: 0b1001111,
    0xF: 0b1000111,
}
SEGMENTS = "abcdefg"


def describe(bits: int) -> str:
    on = [SEGMENTS[i] for i in range(7) if bits & (1 << (6 - i))]
    return "".join(on) or "(semua mati)"


async def check(dut, digit: int):
    dut.hex.value = digit
    await Timer(1, unit="ns")
    got = read_int(dut.seg, "seg")
    want = PATTERNS[digit]
    assert got == want, (
        f"Digit {digit:X}: seg = {got:07b} (menyala: {describe(got)}), "
        f"seharusnya {want:07b} (menyala: {describe(want)})"
    )


@cocotb.test()
async def all_digits(dut):
    """Digit 0 sampai F."""
    for digit in range(16):
        await check(dut, digit)


@cocotb.test()
async def random_digits(dut):
    """Urutan acak (seed tetap)."""
    rng = random.Random(99)
    for _ in range(64):
        await check(dut, rng.randrange(16))
