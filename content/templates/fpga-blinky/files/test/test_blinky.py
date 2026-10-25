"""Testbench cocotb untuk src/blinky.v.

Di simulasi, HALF_PERIOD diisi 4 lewat `parameters` di smartx.yaml, supaya satu
kedipan hanya 8 siklus. Build FPGA memakai `fpga.parameters` (13_500_000).
Desain ini tidak punya input selain clock, jadi tidak ada test acak.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge

HALF_PERIOD = 4  # harus sama dengan parameters.HALF_PERIOD di smartx.yaml


def read_int(signal, name: str) -> int:
    """Baca sinyal sebagai int; beri pesan jelas jika masih X/Z."""
    value = signal.value
    if not value.is_resolvable:
        raise AssertionError(f"{name} bernilai {value} (X/Z). Apakah nilai awal register sudah diisi?")
    return int(value)


def expected_led(edges: int) -> int:
    """Model referensi: LED pertama menyala (0) di setiap setengah periode ganjil."""
    on = (edges // HALF_PERIOD) % 2
    return 0b111110 | (1 - on)


@cocotb.test()
async def first_led_blinks(dut):
    """Bandingkan led dengan model, siklus demi siklus, selama lima kedipan."""
    # Clock mulai tinggi di t = 0: itu sudah sisi naik pertama.
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await FallingEdge(dut.clk)
    assert read_int(dut.led, "led") == 0b111111, "Di awal semua LED harus mati (led = 111111)."
    for edges in range(2, 10 * HALF_PERIOD + 2):
        await FallingEdge(dut.clk)
        got = read_int(dut.led, "led")
        want = expected_led(edges)
        assert got == want, (
            f"Setelah {edges} sisi naik clock: led = {got:06b}, seharusnya {want:06b} "
            f"(LED pertama berganti setiap {HALF_PERIOD} siklus, LED lain tetap mati)"
        )
