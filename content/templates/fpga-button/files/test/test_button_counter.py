"""Testbench cocotb untuk src/button_counter.v.

Di simulasi, DEBOUNCE_CYCLES diisi 8 lewat `parameters` di smartx.yaml (di board
270_000 = 10 ms), jadi pantulan tombol di test cukup beberapa siklus.

Model referensi meniru seluruh desain siklus demi siklus: synchronizer 2-flop,
debouncer, dan deteksi sisi awal tekanan. Tombol aktif-rendah: btn = 0 saat ditekan.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge

CYCLES = 8  # harus sama dengan parameters.DEBOUNCE_CYCLES di smartx.yaml
PRESSED, RELEASED = 0, 1


def read_int(signal, name: str) -> int:
    """Baca sinyal sebagai int; beri pesan jelas jika masih X/Z."""
    value = signal.value
    if not value.is_resolvable:
        raise AssertionError(f"{name} bernilai {value} (X/Z). Apakah nilai awal register sudah diisi?")
    return int(value)


class Model:
    """Satu sisi naik clock per panggilan step(), dengan nilai btn saat itu."""

    def __init__(self, count: int) -> None:
        self.meta = self.stable = 0  # sync2, sudah dibalik: 1 = ditekan
        self.clean = 0  # keluaran debounce
        self.db_count = 0
        self.last = 0
        self.count = count

    def step(self, btn: int) -> None:
        clean, db_count = self.clean, self.db_count
        if self.stable == self.clean:
            db_count = 0
        elif self.db_count == CYCLES - 1:
            clean, db_count = self.stable, 0
        else:
            db_count += 1
        if self.clean and not self.last:
            self.count = (self.count + 1) % 64
        self.last = self.clean
        self.clean, self.db_count = clean, db_count
        self.meta, self.stable = 1 - btn, self.meta

    @property
    def led(self) -> int:
        return ~self.count & 0b111111


async def start(dut) -> Model:
    """Clock, lalu tombol dilepas cukup lama.

    Test-test di file ini berjalan di simulasi yang sama dan desain tidak punya
    reset. Setelah tombol dilepas lebih dari CYCLES siklus, synchronizer dan
    debouncer pasti diam; counter dibaca dari LED sebagai titik awal model.
    """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.btn.value = RELEASED
    for _ in range(CYCLES + 5):
        await FallingEdge(dut.clk)
    return Model(count=~read_int(dut.led, "led") & 0b111111)


async def drive(dut, model: Model, levels: list[int], what: str) -> None:
    """Satu siklus per nilai btn; bandingkan led dengan model setelah setiap siklus."""
    for cycle, btn in enumerate(levels):
        dut.btn.value = btn  # diubah di sisi turun clock
        await FallingEdge(dut.clk)
        model.step(btn)
        got = read_int(dut.led, "led")
        assert got == model.led, (
            f"{what}, siklus {cycle}: btn={btn}: led = {got:06b} (count {~got & 63}), "
            f"seharusnya {model.led:06b} (count {model.count})"
        )


def bounce(rng: random.Random, end: int) -> list[int]:
    """Pantulan: potongan acak yang lebih pendek dari CYCLES, berakhir di `end`."""
    levels: list[int] = []
    level = 1 - end
    for _ in range(rng.randint(1, 4)):
        levels += [level] * rng.randint(1, CYCLES - 1)
        level = 1 - level
    return levels


@cocotb.test()
async def one_press_counts_once(dut):
    """Tombol ditekan lama lalu dilepas: counter naik tepat satu."""
    model = await start(dut)
    before = model.count
    await drive(dut, model, [PRESSED] * (3 * CYCLES) + [RELEASED] * (3 * CYCLES), "Tekan sekali")
    assert model.count == (before + 1) % 64


@cocotb.test()
async def bouncing_press_counts_once(dut):
    """Pantulan saat ditekan dan saat dilepas tidak menambah hitungan."""
    model = await start(dut)
    before = model.count
    levels = [0, 1, 1, 0, 1, 0, 0, 0, 1] + [PRESSED] * (2 * CYCLES)
    levels += [1, 0, 0, 1, 0, 1, 1] + [RELEASED] * (2 * CYCLES)
    await drive(dut, model, levels, "Tekan dengan pantulan")
    assert model.count == (before + 1) % 64


@cocotb.test()
async def short_glitch_is_ignored(dut):
    """Tekanan yang lebih pendek dari CYCLES dianggap gangguan."""
    model = await start(dut)
    before = model.count
    levels = [PRESSED] * (CYCLES - 1) + [RELEASED] * (2 * CYCLES)
    await drive(dut, model, levels, "Gangguan singkat")
    assert model.count == before


@cocotb.test()
async def random_presses(dut):
    """Sepuluh tekanan dengan pantulan acak; seed tetap supaya bisa diulang."""
    rng = random.Random(7)
    model = await start(dut)
    before = model.count
    for press in range(10):
        levels = bounce(rng, PRESSED) + [PRESSED] * rng.randint(CYCLES + 3, 3 * CYCLES)
        levels += bounce(rng, RELEASED) + [RELEASED] * rng.randint(CYCLES + 3, 3 * CYCLES)
        await drive(dut, model, levels, f"Tekanan acak ke-{press + 1}")
    assert model.count == (before + 10) % 64
