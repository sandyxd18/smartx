"""Testbench cocotb untuk soal pitfall-blocking."""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge

def read_int(signal, name: str) -> int:
    """Baca sinyal sebagai int; beri pesan jelas jika masih X/Z."""
    value = signal.value
    if not value.is_resolvable:
        raise AssertionError(
            f"{name} bernilai {value} (X/Z). Biasanya karena sinyal belum pernah "
            f"di-assign, atau ada dua driver yang saling bertentangan."
        )
    return int(value)



async def run(dut, values: list[int]):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await FallingEdge(dut.clk)
    history: list[int] = []
    for cycle, d in enumerate(values):
        dut.d.value = d
        await RisingEdge(dut.clk)
        history.append(d)
        await FallingEdge(dut.clk)
        q1 = read_int(dut.q1, "q1")
        assert q1 == d, f"Siklus {cycle}: q1 = {q1}, seharusnya {d} (d dari 1 clock lalu)"
        if cycle == 0:
            continue  # q2 has no defined value yet
        q2 = read_int(dut.q2, "q2")
        want = history[-2]
        hint = ""
        if q2 == q1 != want:
            hint = (
                ". q2 sama dengan q1: q2 mengambil q1 yang baru saja diubah di clock yang sama. "
                "Periksa jenis assignment di always @(posedge clk)."
            )
        assert q2 == want, (
            f"Siklus {cycle}: q2 = {q2}, seharusnya {want} (d dari 2 clock lalu){hint}"
        )


@cocotb.test()
async def two_stage_delay(dut):
    """10, 20, 30 masuk; q2 tertinggal satu tahap di belakang q1."""
    await run(dut, [10, 20, 30, 40, 50])


@cocotb.test()
async def random_data(dut):
    """Data acak (seed tetap)."""
    rng = random.Random(1313)
    await run(dut, [rng.randrange(256) for _ in range(200)])
