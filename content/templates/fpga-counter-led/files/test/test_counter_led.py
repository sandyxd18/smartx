"""Testbench cocotb untuk src/counter_led.v.

Di simulasi, TICK diisi 3 lewat `parameters` di smartx.yaml, supaya counter naik
setiap 3 siklus. Build FPGA memakai `fpga.parameters` (6_750_000).

Model referensi meniru seluruh desain, termasuk dua flip-flop synchronizer di depan
rst_n: tombol reset baru terasa dua siklus setelah ditekan.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge

TICK = 3  # harus sama dengan parameters.TICK di smartx.yaml


def read_int(signal, name: str) -> int:
    """Baca sinyal sebagai int; beri pesan jelas jika masih X/Z."""
    value = signal.value
    if not value.is_resolvable:
        raise AssertionError(f"{name} bernilai {value} (X/Z). Apakah nilai awal register sudah diisi?")
    return int(value)


class Model:
    """Satu sisi naik clock per panggilan step(), dengan nilai rst_n saat itu."""

    def __init__(self) -> None:
        self.meta = 0
        self.stable = 0
        self.div = 0
        self.count = 0
        self.wraps = 0

    def step(self, rst_n: int) -> None:
        if not self.stable:
            self.div, self.count = 0, 0
        elif self.div == TICK - 1:
            self.div = 0
            self.count = (self.count + 1) % 64
            self.wraps += self.count == 0
        else:
            self.div += 1
        self.meta, self.stable = rst_n, self.meta

    @property
    def led(self) -> int:
        return ~self.count & 0b111111


async def start(dut) -> Model:
    """Clock, lalu tombol reset ditahan tiga siklus.

    Test-test di file ini berjalan di simulasi yang sama, jadi desain membawa state
    dari test sebelumnya. Setelah tiga siklus dengan rst_n = 0, kedua flip-flop
    synchronizer dan counter pasti 0: sama dengan model yang baru dibuat.
    """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    for _ in range(3):
        await FallingEdge(dut.clk)
    return Model()


async def run(dut, model: Model, presses: list[int], first_cycle: int = 0) -> None:
    """Satu siklus per nilai rst_n; bandingkan led dengan model setelah setiap siklus."""
    for i, rst_n in enumerate(presses):
        dut.rst_n.value = rst_n  # diubah di sisi turun clock
        await FallingEdge(dut.clk)
        model.step(rst_n)
        got = read_int(dut.led, "led")
        assert got == model.led, (
            f"Siklus {first_cycle + i}: rst_n={rst_n}: led = {got:06b} (count {~got & 63}), "
            f"seharusnya {model.led:06b} (count {model.count})"
        )


@cocotb.test()
async def counts_up_and_wraps(dut):
    """Tanpa tombol ditekan, counter naik setiap TICK siklus dan kembali ke 0 setelah 63."""
    model = await start(dut)
    await run(dut, model, [1] * (TICK * 70))
    assert model.wraps == 1, "Test ini seharusnya melewati 63 -> 0 tepat sekali."


@cocotb.test()
async def reset_button_clears_count(dut):
    """Tombol S2 ditekan satu siklus: counter kembali ke 0, dua siklus kemudian."""
    model = await start(dut)
    await run(dut, model, [1] * 20)
    assert model.count > 0, "Sebelum tombol ditekan, counter seharusnya sudah naik."
    await run(dut, model, [0] + [1] * 10, first_cycle=20)


@cocotb.test()
async def random_reset_presses(dut):
    """Tombol reset ditekan acak; seed tetap supaya kegagalan bisa diulang."""
    rng = random.Random(2026)
    model = await start(dut)
    presses = [0 if rng.random() < 0.08 else 1 for _ in range(300)]
    await run(dut, model, presses)
