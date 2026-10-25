"""Testbench cocotb untuk soal priority-encoder."""

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



def model(req: int) -> tuple[int, int]:
    if req == 0:
        return 0, 0
    return req.bit_length() - 1, 1


async def check(dut, req: int):
    dut.req.value = req
    await Timer(1, unit="ns")
    idx = read_int(dut.idx, "idx")
    valid = read_int(dut.valid, "valid")
    want_idx, want_valid = model(req)
    assert (idx, valid) == (want_idx, want_valid), (
        f"req = {req:08b}: idx = {idx}, valid = {valid}; "
        f"seharusnya idx = {want_idx}, valid = {want_valid}"
    )


@cocotb.test()
async def all_requests(dut):
    """Semua 256 kombinasi permintaan."""
    for req in range(256):
        await check(dut, req)


@cocotb.test()
async def random_requests(dut):
    """Urutan acak (seed tetap)."""
    rng = random.Random(66)
    for _ in range(100):
        await check(dut, rng.randrange(256))
