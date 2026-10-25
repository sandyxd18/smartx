# Phase 5: ASIC flow (step 5)

Goal: take a design from RTL to GDS with LibreLane, and read the sign-off results (timing, DRC, LVS) in the UI.

## Before starting

1. Pick and pin `ASIC_IMAGE` in `.env` (see `DECISIONS.md` D07). Check inside the image: which LibreLane commands exist, its version, and the PDK location (`PDK_ROOT`, `PDK`).
2. Run one small design (counter) by hand in that image from a terminal before writing backend code. Record the exact commands in `docs/notes/asic-manual-run.md`.
3. Make sure the machine has enough RAM and disk (see ARCHITECTURE).

## Tasks

1. **`asic` job** (heavy class):
   - `prepare`: write the RTL sources + LibreLane `config.yaml` to the run folder, set the PDK and standard cell library.
   - Run the LibreLane Classic flow. Streamed log; the active stage (Synthesis, Floorplan, Placement, CTS, Routing, Signoff) is parsed from the log for a progress bar.
   - `collect`: read the LibreLane metrics (JSON in the result run folder), the GDS path, and the STA/DRC/LVS reports.
2. **Configuration form**: `DESIGN_NAME`, `VERILOG_FILES`, `CLOCK_PORT`, `CLOCK_PERIOD`, die size/`FP_CORE_UTIL`, PDK (sky130A / ihp-sg13g2), plus a raw YAML editor.
3. **Result summary**: die/core area, cell count, utilization, setup & hold WNS/TNS per corner, number of DRC/LVS/antenna violations, power (if available). Green/red sign-off status.
4. **GDS render**: a KLayout batch script → a PNG of the whole layout + a few crops. Shown in `GdsView` with zoom/pan. The GDS can be downloaded.
5. **Cancelling & disk space**: cancel kills the container; a button to delete old runs; show the total size of `data/runs/`.
6. **Lessons** `content/lessons/05-*.md`: each flow stage, what WNS/TNS mean, why DRC/LVS matter, how to fix timing (constraints, pipelining, smaller logic).

## Done criteria

- [ ] `counter-4bit` and `uart-tx` reach GDS on SKY130 with clean DRC/LVS.
- [ ] At least one design also passes on IHP SG13G2.
- [ ] The summary in the UI matches the numbers in the raw metrics file (with a parser test and fixtures).
- [ ] A design with a too-tight `CLOCK_PERIOD` shows a negative WNS and a red status.
- [ ] The layout PNG shows and can be zoomed.
