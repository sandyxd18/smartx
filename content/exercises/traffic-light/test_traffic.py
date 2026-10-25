"""Testbench cocotb untuk soal traffic-light."""

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


DURATION = {"H": 4, "K": 2, "M": 3}
NEXT = {"H": "K", "K": "M", "M": "H"}


class Model:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.light, self.t = "H", 0

    def step(self) -> None:
        if self.t + 1 < DURATION[self.light]:
            self.t += 1
        else:
            self.light, self.t = NEXT[self.light], 0


def observed(dut) -> str:
    lights = {
        "H": read_int(dut.green, "green"),
        "K": read_int(dut.yellow, "yellow"),
        "M": read_int(dut.red, "red"),
    }
    on = [name for name, value in lights.items() if value]
    assert len(on) == 1, (
        f"Tepat satu lampu harus menyala, yang menyala: {on or 'tidak ada'} "
        "(H = hijau, K = kuning, M = merah)"
    )
    return on[0]


async def run(dut, cycles: int, resets: list[int]):
    model = Model()
    trace = "H"
    assert observed(dut) == "H", "Setelah reset seharusnya hijau"
    for cycle in range(cycles):
        rst = resets[cycle]
        dut.rst.value = rst
        await RisingEdge(dut.clk)
        if rst:
            model.reset()
        else:
            model.step()
        await FallingEdge(dut.clk)
        got = observed(dut)
        trace += got
        assert got == model.light, (
            f"Siklus {cycle + 1} (rst = {rst}): lampu {got}, seharusnya {model.light}. "
            f"Urutan sejauh ini: {trace[-12:]}"
        )


@cocotb.test()
async def full_cycles(dut):
    """Tiga putaran penuh tanpa reset."""
    await setup(dut)
    await run(dut, 27, [0] * 27)


@cocotb.test()
async def random_resets(dut):
    """Reset di saat acak (seed tetap) selalu kembali ke awal hijau."""
    await setup(dut)
    rng = random.Random(8080)
    await run(dut, 200, [int(rng.random() < 0.05) for _ in range(200)])
