# Phase 3: FPGA (step 3)

Goal: designs from the workspace are synthesized and placed & routed for a real board, and the user can read the resource and timing reports before flashing.

## Before starting

Confirm which board the owner has (see `DECISIONS.md` D08). Finish one board completely before adding a second one.

Confirmed on 2026-10-25: the owner has no board yet. Start with the Tang Nano 9K up to the bitstream; iCE40 moves to task 8 (D38).

## Tasks

1. [x] **Board profile** in `content/boards/` (format in `CONTENT-FORMAT.md`) and a constraint template. First board: Tang Nano 9K (Gowin, `nextpnr-himbaechel` + `gowin_pack`). The second board (iCE40) is task 8.
2. [x] **`fpga` job** with three stages that are visible separately in the UI:
   - Synthesize: `yosys -p "synth_gowin -top <top> -json out.json"` (or `synth_ice40`). Keep `yosys.log` and `stat`.
   - Place & Route: nextpnr with `--freq` from `smartx.yaml`, writing `--report report.json`.
   - Pack: produce the bitstream.
3. [x] **Report parsers** in `backend/app/reports/`:
   - Resource utilization from nextpnr's `report.json` (LUT, FF, BRAM, IO) against the device capacity.
   - Fmax per clock domain against the target, red when missed.
   - Important Yosys warnings: inferred latch, unused signal, multi-driven, failed memory inference.
   Write parser unit tests with sample report files in `backend/tests/fixtures/`.
4. [x] **FPGA page** in the workspace: board picker, constraint editor, Build button, report tables, bitstream download.
5. [x] **Flashing helper** `tools/flash/smartx-flash`: a host script that downloads the bitstream of the latest run from the backend (or takes a local path) and calls `openFPGALoader` according to the board profile. Document installing `openFPGALoader` and the udev rules in a README.
6. [x] **Lessons** `content/lessons/03-*.md`: code that does not synthesize, the 2-flop synchronizer, debounce, reading the timing report, why simulation passes but the FPGA fails.
7. [x] **Example FPGA projects**: blinky, counter on the LEDs, button with debounce.
8. [ ] **Second board: iCE40** (`nextpnr-ice40` + `icepack`), once the Tang Nano 9K is complete: profile, `.pcf` template, blinky fixture, and example projects.

## Done criteria

- [ ] Blinky built from the UI blinks on the board after `smartx-flash`.
- [x] The report shows resources and Fmax that match the raw nextpnr output.
- [x] A design with an accidental latch shows a clear warning in the UI.
- [x] A design that misses timing is marked red, with the critical path (from the report) shown.
