"""Testbench cocotb untuk soal debouncer."""

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


async def setup(dut, **zeros: int):
    """Start the clock and hold reset for one rising edge; inputs start at 0."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for name in zeros:
        getattr(dut, name).value = 0
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


class Model:
    def __init__(self) -> None:
        self.clean, self.cnt = 0, 0

    def step(self, rst: int, btn: int) -> None:
        if rst:
            self.clean, self.cnt = 0, 0
        elif btn == self.clean:
            self.cnt = 0
        elif self.cnt == 3:
            self.clean, self.cnt = btn, 0
        else:
            self.cnt += 1


async def feed(dut, bits: list[int], resets: list[int] | None = None):
    model = Model()
    trace = ""
    for cycle, btn in enumerate(bits):
        rst = resets[cycle] if resets else 0
        dut.btn.value = btn
        dut.rst.value = rst
        await RisingEdge(dut.clk)
        model.step(rst, btn)
        trace += str(btn)
        await FallingEdge(dut.clk)
        clean = read_int(dut.clean, "clean")
        assert clean == model.clean, (
            f"Siklus {cycle} (btn terakhir: {trace[-8:]}, rst = {rst}): "
            f"clean = {clean}, seharusnya {model.clean}"
        )


@cocotb.test()
async def ignores_short_glitches(dut):
    """Pantulan pendek tidak boleh lolos."""
    await setup(dut, btn=0)
    await feed(dut, [1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0])


@cocotb.test()
async def passes_stable_press_and_release(dut):
    """Tekan yang stabil lolos setelah 4 siklus; lepas juga."""
    await setup(dut, btn=0)
    await feed(dut, [1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0])


@cocotb.test()
async def random_bouncing(dut):
    """Tombol memantul acak (seed tetap), dibandingkan dengan model."""
    await setup(dut, btn=0)
    rng = random.Random(9090)
    bits, level = [], 0
    for _ in range(500):
        if rng.random() < 0.05:
            level ^= 1  # a real press or release
        bits.append(level ^ int(rng.random() < 0.2))  # plus bounce noise
    resets = [int(rng.random() < 0.01) for _ in range(500)]
    await feed(dut, bits, resets)
