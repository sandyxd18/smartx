# SmartX: product specification

## Goal

SmartX is a local web app for one person (its owner) who wants to learn digital chip design from scratch all the way to tapeout. The same Verilog design is carried through six steps:

| Step | Question it answers | Module in the app |
|---|---|---|
| 1. Verilog exercises | How do I describe hardware? | Exercises |
| 2. Simulation & verification | Is the logic correct? | Workspace: Sim |
| 3. FPGA | Does it run on real hardware? | Workspace: FPGA |
| 4. Step-by-step projects | Can I build a whole system? | Projects |
| 5. ASIC flow | How does a design become chip geometry? | Workspace: ASIC |
| 6. Tapeout | Does it work in silicon? | Tapeout export |

The app wraps existing open-source tools. No EDA tool is rewritten.

## Users

One user, on a local network. No login, no multi-tenancy. The app runs on a laptop or a Linux VM and is used from a browser.

## Functional requirements

### F1. Exercises (step 1)
- Exercise list grouped by topic and level, with a status: not started, failed, passed.
- Exercise page: statement (Markdown), Verilog editor (Monaco, syntax highlighting), **Run** button.
- Run result: status per test, readable error messages, compile log, and waveform.
- Hints open one at a time. The solution can be opened after passing or after N failures (N is configurable).
- The latest code of each exercise is saved automatically.

### F2. Simulation workspace (step 2)
- Projects with many files (`.v`, `.sv`, `.py`, `.yaml`) and a file tree.
- Actions: Lint (Verilator `--lint-only`), Simulate (Icarus or Verilator), run cocotb tests.
- In-browser waveform viewer for `.fst`/`.vcd` files.
- Run history per project, with a comparison of two runs.

### F3. FPGA (step 3)
- Pick a target board (board profile). Tang Nano 9K (Gowin) and Terasic DE1-SoC (Cyclone V); iCE40 (iCEBreaker/UPduino) later.
- Constraint editor (`.cst` for Gowin, `.qsf` for Cyclone V, `.pcf` for iCE40) with a template per board.
- Actions: Synthesize (Yosys), Place & Route (nextpnr), Pack (bitstream).
- Reports: resource utilization (LUT, FF, BRAM), Fmax per clock, important warnings (latch, multi-driven, unused signals).
- The bitstream can be downloaded. Flashing is done with a helper script on the host (`smartx-flash`), because USB access from a container is unreliable.

### F4. Projects (step 4)
- Guided projects: UART TX/RX, SPI master, I2C master, single-cycle RV32I, pipelined RV32I, mini-SoC.
- Each project has milestones. Each milestone has an explanation, starter files, and cocotb tests that must pass before moving on.
- RISC-V projects: the `riscv64-unknown-elf-gcc` toolchain to compile C/assembly programs, and `riscv-tests` integration.

### F5. ASIC flow (step 5)
- LibreLane configuration per project (`config.yaml`) with a simple form plus a raw editor.
- PDKs: SKY130 and IHP SG13G2 (GF180MCU optional).
- Jobs run in the background, logs are shown live, and jobs can be cancelled.
- Result summary: area, cell count, WNS/TNS per corner, number of DRC/LVS/antenna violations.
- GDS layout rendered as PNG images (KLayout in batch mode), with zoom.

### F6. Tapeout export (step 6)
- Tiny Tapeout project generator from a design that passed step 5: `info.yaml`, `src/`, `test/`, `docs/info.md`.
- Pin check (8 inputs, 8 outputs, 8 bidirectional, clk, rst_n, ena) and a `tt_um_*` top name.
- Local hardening with `tt-support-tools` for the chosen shuttle.
- Submission checklist. Submission and payment stay manual on the Tiny Tapeout site.

### F7. General
- Learning progress per step (simple dashboard).
- All data in one folder (`data/`), easy to back up.
- Project export/import as `.zip` or a Git repository.

## Non-functional requirements

- **Response time**: grading a small exercise takes < 5 seconds from click to result (once the toolchain image exists).
- **Isolation**: every job runs in a fresh container, `--network none`, with CPU/RAM/time limits, as a non-root user.
- **Reproducible**: tool versions are pinned (OSS CAD Suite date, ASIC image tag). Tool versions are recorded with every run result.
- **Survives restarts**: jobs that were running when the backend stopped are marked `failed` with a clear reason.
- **Language**: UI and learning material in Indonesian; code, identifiers, commits, and documentation in English.

## Out of scope

- Multiple users, authentication, quotas.
- Analog design (Xschem/ngspice). Possible expansion after v1.
- Commercial tools (Cadence, Synopsys).
- In-browser simulation via WebAssembly. All tools run in the backend; this may be considered later.
- Automatic submission to Tiny Tapeout.

## Definition of "v1 done"

One design (for example a UART TX) can be carried from an exercise → cocotb testbench → FPGA bitstream → GDS with LibreLane → Tiny Tapeout repository that passes local hardening, entirely from the SmartX UI.
