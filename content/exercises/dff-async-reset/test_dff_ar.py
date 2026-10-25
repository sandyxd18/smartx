"""Testbench cocotb untuk soal dff-async-reset."""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

def read_int(signal, name: str) -> int:
    """Baca sinyal sebagai int; beri pesan jelas jika masih X/Z."""
    value = signal.value
    if not value.is_resolvable:
        raise AssertionError(
            f"{name} bernilai {value} (X/Z). Biasanya karena sinyal belum pernah "
            f"di-assign, atau ada dua driver yang saling bertentangan."
        )
    return int(value)



async def start(dut):
    dut.rst_n.value = 1
    dut.d.value = 0
    await Timer(1, unit="ns")
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


@cocotb.test()
async def reset_without_clock(dut):
    """Reset harus bekerja walaupun clock belum berjalan."""
    dut.rst_n.value = 1
    dut.d.value = 0
    await Timer(1, unit="ns")
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    value = dut.q.value
    assert value.is_resolvable and int(value) == 0, (
        f"rst_n = 0 tanpa clock: q = {value}, seharusnya 0. Reset belum bekerja tanpa clock; "
        "soal ini minta reset asinkron (masukkan negedge rst_n ke daftar sensitivitas always)."
    )


@cocotb.test()
async def captures_d(dut):
    """q mengikuti d di setiap sisi naik clock."""
    await start(dut)
    for cycle, d in enumerate([1, 0, 1, 1, 0]):
        dut.d.value = d
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        q = read_int(dut.q, "q")
        assert q == d, f"Siklus {cycle}: d = {d}, q = {q}, seharusnya {d}"


@cocotb.test()
async def reset_is_immediate(dut):
    """Reset di tengah siklus langsung mengosongkan q, sebelum clock naik berikutnya."""
    await start(dut)
    dut.d.value = 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    assert read_int(dut.q, "q") == 1, "q seharusnya 1 setelah d = 1 masuk"
    await Timer(2, unit="ns")  # still before the next rising edge
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    q = read_int(dut.q, "q")
    assert q == 0, (
        f"rst_n turun di tengah siklus: q = {q}, seharusnya langsung 0. "
        "Reset sinkron baru bekerja di sisi naik clock; soal ini minta reset asinkron."
    )


@cocotb.test()
async def random_stimulus(dut):
    """d dan reset acak (seed tetap), dibandingkan dengan model."""
    await start(dut)
    rng = random.Random(1010)
    model = 0
    for cycle in range(150):
        d = rng.randint(0, 1)
        rst = rng.random() < 0.1
        dut.d.value = d
        dut.rst_n.value = 0 if rst else 1
        await RisingEdge(dut.clk)
        model = 0 if rst else d
        await FallingEdge(dut.clk)
        q = read_int(dut.q, "q")
        assert q == model, (
            f"Siklus {cycle} (d = {d}, rst_n = {0 if rst else 1}): q = {q}, seharusnya {model}"
        )
