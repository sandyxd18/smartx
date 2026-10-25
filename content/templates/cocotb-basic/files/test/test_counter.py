"""Testbench cocotb untuk src/counter.v.

Pola dasar yang bisa kamu salin ke desainmu sendiri:
1. Nyalakan clock dan beri reset.
2. Simpan model referensi di Python (di sini: satu integer).
3. Ubah input di sisi turun clock, cek output di sisi turun berikutnya.
4. Pakai random.Random(seed) supaya kegagalan bisa diulang persis.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer


def read_int(signal, name: str) -> int:
    """Baca sinyal sebagai int; beri pesan jelas jika masih X/Z."""
    value = signal.value
    if not value.is_resolvable:
        raise AssertionError(f"{name} bernilai {value} (X/Z). Apakah reset sudah ditangani?")
    return int(value)


async def start(dut) -> None:
    """Clock 10 ns dan reset selama dua siklus."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.en.value = 0
    await FallingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


@cocotb.test()
async def reset_clears_count(dut):
    await start(dut)
    assert read_int(dut.count, "count") == 0, "Setelah reset, count harus 0."


@cocotb.test()
async def counts_and_wraps(dut):
    await start(dut)
    dut.en.value = 1
    for expected in range(1, 300):
        await FallingEdge(dut.clk)
        got = read_int(dut.count, "count")
        assert got == expected % 256, f"Siklus {expected}: count = {got}, seharusnya {expected % 256}"


@cocotb.test()
async def random_enable(dut):
    """Bandingkan dengan model referensi untuk pola enable acak."""
    rng = random.Random(1234)
    await start(dut)
    model = 0
    for cycle in range(200):
        en = rng.randint(0, 1)
        dut.en.value = en
        # wrap adalah logika kombinasional: cek sebelum clock naik.
        await Timer(1, unit="ns")
        expected_wrap = int(en == 1 and model == 255)
        got_wrap = read_int(dut.wrap, "wrap")
        assert got_wrap == expected_wrap, (
            f"Siklus {cycle}: en={en}, count={model}: wrap = {got_wrap}, seharusnya {expected_wrap}"
        )
        await FallingEdge(dut.clk)
        if en:
            model = (model + 1) % 256
        got = read_int(dut.count, "count")
        assert got == model, f"Siklus {cycle}: en={en}: count = {got}, seharusnya {model}"


@cocotb.test()
async def wrap_needs_enable(dut):
    """Test terarah untuk kasus tepi: di 255, wrap hanya 1 kalau en = 1."""
    await start(dut)
    dut.en.value = 1
    for _ in range(255):
        await FallingEdge(dut.clk)
    assert read_int(dut.count, "count") == 255, "count harus sampai 255"

    dut.en.value = 0
    await Timer(1, unit="ns")
    assert read_int(dut.wrap, "wrap") == 0, "count = 255 dan en = 0: wrap harus 0"

    dut.en.value = 1
    await Timer(1, unit="ns")
    assert read_int(dut.wrap, "wrap") == 1, "count = 255 dan en = 1: wrap harus 1"

    await FallingEdge(dut.clk)
    assert read_int(dut.count, "count") == 0, "Setelah 255, count harus kembali ke 0"
    assert read_int(dut.wrap, "wrap") == 0, "count = 0: wrap harus 0"
