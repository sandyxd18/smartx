# Content format

All learning material lives in `content/` as plain files (YAML, Markdown, Verilog, Python), so it is easy to write, review, and test automatically. The backend only reads this folder; the UI never sends `solution.v` to the browser unless the unlock condition is met.

The content itself (exercise statements, hints, lessons, test messages) is written in Indonesian, like the UI.

## Exercises: `content/exercises/<id>/`

```
counter-4bit/
├─ exercise.yaml      metadata
├─ README.md          statement (Markdown, port tables allowed)
├─ starter.v          initial code in the editor
├─ solution.v         official solution (secret)
└─ test_<top>.py      cocotb testbench
```

`exercise.yaml`:

```yaml
id: counter-4bit          # = folder name, kebab-case
title: Counter 4-bit dengan enable dan reset sinkron
step: 1                   # curriculum step 1-6
level: 1                  # 1 basic, 2 intermediate, 3 advanced
topics: [sequential, register, counter]   # first topic = group in the exercise list
toplevel: counter4        # module under test
language: verilog         # verilog | systemverilog
files: {starter: starter.v, solution: solution.v, test: test_counter4.py, statement: README.md}
timeout_s: 30
hints: ["...", "..."]     # opened in order
order: 120                # optional, display order within the topic
requires: [dff-basic]     # optional, prerequisite exercises
```

### Topics

The exercise list groups exercises by the **first topic** in `topics`. Use one of these ids so the exercise lands in the right curriculum group (the group order follows this table):

| id | Group (shown in the UI) |
|---|---|
| `combinational` | Kombinasional |
| `sequential` | Sekuensial |
| `fsm` | FSM |
| `pitfalls` | Jebakan umum |

Other topics may be used as the second topic onwards (for example `mux`, `counter`). A first topic outside the table still shows up, but as its own group at the end of the list.

### Testbench rules

1. Compare the DUT with a **Python reference model**, cycle by cycle. Avoid long hard-coded value lists.
2. Assert messages are in Indonesian and name the cycle, the inputs, the value read, and the expected value.
3. Read signals through the `read_int()` helper (see the `counter-4bit` example) so X/Z values are explained in plain language.
4. At least one random test with a fixed seed, so results are repeatable.
5. Change inputs on the falling clock edge and check outputs on the next falling edge. This avoids races between the testbench and the DUT.
6. Do not rely on a `timescale` in the user's file; the grader forces `1ns/1ps`.
7. Use `assert condition, "message"` with a complete message. Only that message is shown to the user; cocotb's assertion introspection is dropped by the grader.
8. For "common pitfall" exercises, the starter's failure message should point at the cause of the bug (example: `pitfall-latch`).
9. `solution.v` must be free of `verilator --lint-only -Wall` warnings (checked by `make check-content`). Signals that are intentionally unused get the word `unused` in their name, or are wrapped in `/* verilator lint_off ... */`.

### Validation

`make check-content` (or `check-content-local`) runs every exercise twice: `solution.v` must pass and `starter.v` must fail. An exercise that does not pass this check must not be committed.

## Step 1 curriculum (Phase 1 target)

Suggested order; one exercise per item. Target: at least 20 exercises.

| Topic | Exercises |
|---|---|
| Combinational | wire & assign, basic gates, 2:1 mux, 4:1 mux (case), 3→8 decoder, priority encoder, 4-bit adder, comparator, 7-segment decoder |
| Sequential | D flip-flop (sync/async reset), register with enable, 4-bit counter, up/down counter + load, shift register, LFSR |
| FSM | `1011` pattern detector (Moore), pattern detector (Mealy), traffic light, debouncer, edge detector |
| Common pitfalls | accidental latch ("fix this code" exercise), blocking vs non-blocking, multi-driven net |

## Project templates: `content/templates/<id>/` (Phase 2)

```
cocotb-basic/
├─ template.yaml      title, description, order
└─ files/             contents of the new project, as is (src/, test/, smartx.yaml, README.md)
```

File and folder names in `files/` must follow the project path rules: letters, digits, `_`, `-`, `.`; not starting with `.`; not a name reserved by Windows (`con`, `nul`, `aux`, and so on). Template testbenches follow the testbench rules above and must fail for a wrong design. For `cocotb-basic` this is checked with two mutants (enable ignored, `wrap` without `en`).

The FPGA examples (`fpga-blinky`, `fpga-counter-led`, `fpga-button`) are templates too. Each holds a copy of its board's constraint template (a test keeps it identical), a cocotb testbench that follows the rules above with simulation-sized parameters, and the board values in `fpga.parameters`. The Docker tests check, per example: the testbench passes on Icarus and Verilator, it fails for one plausible mistake, and the build meets timing without synthesis warnings. Designs use `initial` blocks for register initial values, which Verilator lint accepts (an initial value in the declaration gives `PROCASSINIT`).

"Copy from exercise X" creates a project with `src/<toplevel>.v` (the user's latest code, or the starter), `test/<test_*.py>` (the exercise testbench), `README.md` (the statement), and `smartx.yaml`. `solution.v` is never included.

## Workspace project: `smartx.yaml`

A file at the project root. Validated by `backend/app/projects/config.py`, and editable through a form or as YAML.

```yaml
top: counter              # required: top module (Verilog identifier)
sources:                  # globs relative to the project root; default [src/**/*.v]
  - src/**/*.v
tests:                    # cocotb testbench files (.py); default []
  - test/test_counter.py
simulator: icarus         # icarus | verilator; default icarus
parameters:               # optional: parameters of the top module
  WIDTH: 8
  INIT: 8'hFF             # anything other than an integer is passed on as text
defines:                  # optional: -DNAME=value
  SIM: 1
fpga:                     # optional: FPGA build (Phase 3)
  board: tang-nano-9k     # profile id in content/boards/
  constraints: constraints/tang-nano-9k.cst   # constraint file in the project
  freq_mhz: 27            # optional: nextpnr --freq target; default is the board clock
  parameters:             # optional: build-only values, merged over the ones above
    WIDTH: 16
  defines:                # optional: build-only defines, merged the same way
    BOARD: 1
```

Rules:

- Unknown keys are rejected, so a typo (`simulater`) shows up immediately.
- `sources` patterns may use `*` and `?` (within one folder) and `**` as a whole segment (across folders, including zero folders). Patterns must be relative, without `..` and without `\`. Matched files are used in pattern order, without duplicates.
- `tests` holds paths of `.py` files in the project. The file name must be a valid Python module name (`test_fifo.py`). Two files may not share a module name, because cocotb loads tests by module name.
- `parameters` and `defines` values are integers or text. `true`/`false`, lists, and empty values are rejected, because the cocotb runner (pinned version) writes them as they are onto the simulator command line (`-P`/`-G`/`-D`). For a define without a value, use `1`.
- Warnings, which do not block saving: a pattern that matches no file, a top module not found in the source files, a missing test file, and an empty `tests`.
- Saving from the form rewrites the file from the form's contents, so hand-written comments are lost. Only the header line is kept. The `fpga` section is not edited in the simulation form, but it is saved along unchanged.
- An unknown `fpga.board` and a missing `fpga.constraints` file are warnings; the Build button refuses them with the same message. The FPGA build uses the same `top` and `sources` as the simulation, and the top-level `parameters` and `defines` with `fpga.parameters` and `fpga.defines` merged over them (the build-only value wins). Typical use: a short blink period for the testbench at the top level, the real one in `fpga.parameters`.

## Testbench snippets: `content/snippets/*.yaml` (Phase 2)

```yaml
snippets:
  - id: scoreboard            # lowercase letters, digits, '-'
    title: Scoreboard
    description: Bandingkan keluaran DUT dengan urutan data yang diharapkan.
    imports:                  # import lines the body needs
      - from collections import deque
    body: |                   # module-level code (classes, functions, tests)
      class Scoreboard:
          ...
```

The "Sisipkan snippet" menu puts imports that are not there yet into the file's import section and the body at the end of the file. Snippets follow the testbench rules above: inputs change on the falling clock edge, and signals are read after `ReadOnly()`. All snippets must combine into one testbench. The Docker test `test_snippets_make_a_working_testbench` combines them all to test a valid/ready register (`backend/tests/fixtures/projects/pipe_reg`): the result must pass on Icarus and Verilator, and must fail for a register that drops data.

## Short lessons: `content/lessons/NN-slug.md` (Phase 2)

```markdown
---
title: Icarus vs Verilator
step: 2          # learning step 1–6 (SPEC); 2 = simulation & verification
order: 40        # order within one step
---

# Icarus vs Verilator
...
```

`NN` is the learning step (for example `02-`). The body is plain Markdown (tables and code blocks are supported) and is shown in the "Materi" sidebar of the project page, which shows steps 2 and 3, grouped per step. The ```verilog blocks in the step 3 lessons that a Docker test builds must keep building without warnings. Claims about tool behavior should be measured in the toolchain image first and name the version, not be written from memory.

## Guided projects: `content/projects/<id>/` (Phase 4)

```
uart-tx/
├─ project.yaml
└─ milestones/
   ├─ 01-baud-gen/  {README.md, starter/*.v, solution/*.v, test_*.py}
   ├─ 02-shifter/
   └─ 03-full-tx/
```

`project.yaml` holds `id, title, description, milestones: [{id, title, toplevel, test}]`, and optionally `fpga: {board, constraints}` and `asic: {config}` to continue into steps 3 and 5. Files from earlier milestones carry over to the next milestone, so the project grows in the same workspace.

## Board profiles: `content/boards/<id>.yaml` (Phase 3)

```yaml
id: tang-nano-9k                 # = file name
name: Sipeed Tang Nano 9K
family: gowin                    # gowin | ice40
device: GW1NR-LV9QN88PC6/I5
synth: synth_gowin               # Yosys synthesis command: synth_gowin | synth_ice40
nextpnr:
  binary: nextpnr-himbaechel
  args: [--device, GW1NR-LV9QN88PC6/I5, --vopt, family=GW1N-9C, --vopt, "cst={constraints}", --write, "{pnr}"]
pnr_file: pnr.json               # what nextpnr writes for the packer
pack:
  binary: gowin_pack
  args: [-d, GW1N-9C, -o, "{bitstream}", "{pnr}"]
bitstream_file: bitstream.fs
flash: {binary: openFPGALoader, args: [-b, tangnano9k]}
clock: {port: clk, pin: "52", freq_mhz: 27}    # freq_mhz = default --freq target
constraints: {format: cst, template: tang-nano-9k.cst}   # cst | pcf, a file in the same folder
resources:                       # report rows: label -> nextpnr resource types summed into it
  LUT: [LUT4]
  FF: [DFF]
  BRAM: [BSRAM]
  IO: [IOB]
```

Rules:

- Tool arguments may use the placeholders `{constraints}` (the project's constraint file), `{pnr}` (`pnr_file`), and `{bitstream}` (`bitstream_file`). nextpnr arguments must use `{constraints}` and `{pnr}`; packer arguments must use `{pnr}` and `{bitstream}`. The job adds `--json`, `--freq`, `--report`, and `-l` itself.
- The constraint template holds every useful board pin with consistent port names (`clk`, `rst_n`, `btn`, `led[0]`…). Ports the design does not use are ignored by nextpnr, so the template need not be trimmed. The template must pin `clock.port` to `clock.pin`.
- The exact nextpnr and packer arguments must be checked against the pinned OSS CAD Suite version. The Docker test `test_board_profile_builds_blinky` builds `backend/tests/fixtures/boards/<id>/blinky.v` with nothing but the profile and its template, and every profile must have that fixture.
