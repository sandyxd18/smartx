# SmartX

A personal lab for learning digital chip design: from Verilog exercises, through simulation and verification, FPGA, step-by-step projects up to a RISC-V CPU, and the ASIC flow with LibreLane, to a repository that is ready to submit to Tiny Tapeout. All from one local web app.

SmartX wraps existing open-source tools (Icarus Verilog, Verilator, cocotb, Yosys, nextpnr, LibreLane, KLayout) behind one UI. It does not reimplement any EDA tool. The user interface and the learning material are in Indonesian; code and documentation are in English.

## Status

Developed with Claude Code, phase by phase, following [docs/ROADMAP.md](docs/ROADMAP.md).

| Phase | Content | Status |
|---|---|---|
| 0 | Foundation: repo, backend, frontend, Docker runner, toolchain image | done |
| 1 | Exercises: exercise list, editor, grading, waveforms, 23 exercises | done |
| 2 | Simulation workspace: multi-file projects, lint, sim, cocotb, run history | done |
| 3 | FPGA: board profiles, synthesis, place & route, reports, bitstream, flash helper | in progress |
| 4 | Guided projects: UART, SPI, I2C, RV32I, mini-SoC | planned |
| 5 | ASIC: LibreLane, PDK, sign-off reports, GDS render | planned |
| 6 | Tapeout export: Tiny Tapeout repo generator, local hardening, checklist | planned |

## Requirements

- Linux, macOS, or Windows with Docker Desktop; GNU Make, Git, Python 3.10+
- Node.js 22.22+ and [uv](https://docs.astral.sh/uv/) (for `make test` / `make lint` on the host)
- Phases 5–6: 12–16 GB RAM, about 30 GB of free disk space

### Windows

`make` works from PowerShell and from Git Bash. You need:

- [Git for Windows](https://git-scm.com/download/win) in its default location (`C:\Program Files\Git`). The Makefile uses its bash. If Git is installed elsewhere, set `GIT_BASH` to the path of `bash.exe` (without spaces).
- GNU Make: `winget install ezwinports.make`, then open a new terminal.
- Docker Desktop, running.

## Getting started

```bash
make toolchain          # build the toolchain image (once, a few minutes; versions are pinned in .env)
make tool-versions      # check that the tools are installed
make dev                # backend + frontend via docker compose
```

Then open http://127.0.0.1:8080. The dashboard shows the status of the backend and Docker, and the "Jalankan echo job" button tests the job pipeline end to end.

Other commands (`make help` lists them all):

```bash
make check              # every check: lint, tests, Docker tests, check-content
make surfer             # build the Surfer waveform viewer (web) into frontend/public/surfer, once (about 5 minutes)
make pin-toolchain      # move OSS CAD Suite to the latest release (then make toolchain && make check)
```

`make test` and `make lint` run on the host, so they need [uv](https://docs.astral.sh/uv/) and Node.js 22.22+. After changing the backend API, run `npm run gen:api` in `frontend/`; `make lint` fails when the frontend API types are out of date.

Without Docker, the grader can be tried on the host if `iverilog` is installed:

```bash
pip install -r tools/grader/requirements.txt
python tools/grader/grade.py --exercise content/exercises/counter-4bit --use-solution   # passes
python tools/grader/grade.py --exercise content/exercises/counter-4bit --use-starter    # fails
```

To load a bitstream onto an FPGA board, see [tools/flash/README.md](tools/flash/README.md).

## Working with Claude Code

Run `claude` in the repository, then ask: *"Read CLAUDE.md and the ROADMAP, then work on the next task."* Or use the `/next-task` and `/phase-review` commands in `.claude/commands/`.

## Layout

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). In short: `backend/` (FastAPI), `frontend/` (React), `content/` (exercises, lessons, templates, board profiles), `tools/` (grader, FPGA build, flash helper), `docker/` (toolchain image), `docs/` (specification and plans).

## License

[MIT](LICENSE)
