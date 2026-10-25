# Phase 4: Guided projects (step 4)

Goal: build ever larger systems, milestone by milestone, using the existing workspace (Phase 2) and FPGA support (Phase 3).

## Tasks

1. **Guided project engine**: a loader for `content/projects/*/project.yaml` that creates a workspace project from the first milestone and opens the next milestone only after the tests of the current one pass. Files from earlier milestones stay the user's own (they are never overwritten).
2. **Project UI**: milestone list with status, the explanation next to the editor, a "Cek milestone" button.
3. **Project content** (write them in order, test them with the official solutions like the exercises):
   - `uart-tx`: baud generator → shift register → complete frame (start/data/stop) → FPGA demo sending "Hello" to the PC.
   - `uart-rx`: 16x oversampling → start bit detection → loopback on the FPGA.
   - `spi-master`: mode 0, then full CPOL/CPHA; demo reading the ID of the board's SPI flash.
   - `i2c-master`: START/STOP, send a byte + ACK, read a sensor register.
   - `rv32i-single`: register file → ALU → decoder → complete datapath → passes `riscv-tests` rv32ui.
   - `rv32i-pipe`: 5 stages → hazards & forwarding → load-use stall → branches.
   - `mini-soc`: RV32I + RAM + memory-mapped UART; a C program prints "Hello World" on the FPGA.
4. **RISC-V toolchain** in the light image: `gcc-riscv64-unknown-elf` + `picolibc-riscv64-unknown-elf` (Ubuntu 24.04 packages), or the toolchain from OSS CAD Suite if available. A `riscv_build` job compiles C/assembly → a `.hex` loaded with `$readmemh`.
5. **riscv-tests**: build them once in the image (or as content artifacts), with a cocotb test that runs each test, reads the `tohost` address, and reports pass/fail per instruction.
6. **Connect to step 5**: each project may have `asic:` in `project.yaml` so it can go straight to Phase 5 (example: `uart-tx` is small, a good fit for Tiny Tapeout).

## Done criteria

- [ ] `uart-tx` finished from milestone 1 to the FPGA demo, visible in a serial terminal on the PC.
- [ ] `rv32i-single` passes all `rv32ui-p-*` in simulation.
- [ ] `mini-soc` runs a C "Hello World" program over UART on the FPGA.
- [ ] Every official project solution passes the automatic check (extend `check_content.py`).
