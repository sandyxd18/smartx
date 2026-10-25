# Phase 2: Simulation workspace (step 2)

Goal: a free-form (sandbox) project workspace with many files, the user's own testbenches, and a run history. Here the user learns to write their own verification, not just use the testbenches provided.

## Tasks

1. [x] **Sandbox projects**: create a new project from a template (`empty`, `cocotb-basic`, or "copy from exercise X"). File tree with create/rename/delete for files and folders.
2. [x] **Project configuration** (`smartx.yaml` at the project root): `top`, `sources` (globs), `tests` (cocotb modules), `simulator` (`icarus` | `verilator`), `parameters`, `defines`. Both a UI form and a raw editor, kept in sync.
3. [x] **`lint` job**: `verilator --lint-only -Wall` over all sources. Output parser → diagnostics `{file, line, col, severity, code, message}` → shown in a Problems panel and as Monaco markers.
4. [x] **`sim` job**: generalize `grade.py` into a project runner (cocotb runner with many sources, parameters, defines, and a choice of simulator). Results per test + waveform.
5. [x] **Run history**: list of runs per project (time, kind, status, duration, test summary). Click to open an old result.
6. [x] **Compare two runs**: which tests changed status. (No waveform diff needed.)
7. [x] **Testbench templates**: cocotb snippets for clock/reset, a valid-ready driver, a simple scoreboard, and coverage with `cocotb-coverage` (optional).
8. [x] **Short lessons** in `content/lessons/02-*.md`: writing a reference model, random tests with a seed, reading waveforms for debugging. Shown in a workspace sidebar.

## Done criteria

- [x] Create a sandbox project with a synchronous FIFO + a cocotb testbench with a scoreboard, run it on Icarus and Verilator, both green.
- [x] Lint warnings appear in the editor on the right line.
- [x] The history keeps at least the last 50 runs per project; old results can be opened together with their waveform.
- [x] The differences between Icarus and Verilator (for example X-propagation) are explained in the lessons.
