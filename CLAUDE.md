# CLAUDE.md

Working guide for Claude Code in this repository. Read this file first in every session.

## Project

SmartX: a local, single-user web app for learning digital chip design, from Verilog exercises to a Tiny Tapeout tapeout. It wraps open-source tools (Icarus, Verilator, cocotb, Yosys, nextpnr, LibreLane, KLayout) behind one UI.

Reference documents, read as needed:
- `docs/SPEC.md`: what is built and what is not.
- `docs/ARCHITECTURE.md`: repository layout, data model, job system, API.
- `docs/DECISIONS.md`: technical decisions and their reasons.
- `docs/CONTENT-FORMAT.md`: format of exercises, projects, board profiles.
- `docs/ROADMAP.md`: phase status and progress log.
- `docs/phases/phase-N-*.md`: tasks and done criteria per phase.

## How to work

1. At the start of a session: open `docs/ROADMAP.md`, find the first phase not marked `[x]`, then open its phase file.
2. Work on **one phase at a time**, task by task in the order of the phase file. Do not start the next phase before every done criterion of the current phase is ticked.
3. For every task: write or update tests first where possible, implement, run `make check` (or the relevant part), and only then consider it done.
4. When a task is done: tick it in the phase file and commit with an English message (`feat(jobs): add docker runner with resource limits`).
5. At the end of a session: add one line to the "Progress log" in `ROADMAP.md`.
6. For a new technical decision, or a change to an old one: add an entry to `DECISIONS.md`.
7. If the specification is unclear or contradictory, ask the project owner before building something expensive to redo. For small things: take the most reasonable option and record it.

## Commands

```
make help                 list targets
make pin-toolchain        pin the OSS CAD Suite version in .env
make toolchain            build the toolchain image
make check-content        test every exercise inside the image
make check-content-local  test exercises with the tools on the host
make dev                  run the app
make test | lint | check
```

Test one exercise by hand:
```
python tools/grader/grade.py --exercise content/exercises/counter-4bit --use-solution
```

## Conventions

- **Language**: the UI, learning material (`content/`), and user-facing error messages are in Indonesian. Code, identifiers, code comments, commit messages, and documentation (`README.md`, `CLAUDE.md`, `docs/`, tool READMEs) are in English.
- **Backend**: Python 3.12, FastAPI, SQLModel, type hints on every public function, `ruff` for lint + format, `pytest` for tests. Functions that call Docker are tested with `FakeRunner`, not real Docker.
- **Frontend**: React + strict TypeScript, function components, API client generated from OpenAPI (never write API types by hand), `eslint` + `vitest`.
- **New job kind**: one module in `backend/app/jobs/kinds/` with `prepare()` and `collect()`; add a run-folder fixture to test `collect()`.
- **Content**: every new exercise or project must pass `check_content` (the solution passes, the starter fails). Follow the testbench rules in `CONTENT-FORMAT.md`.
- **Tool versions**: never use `latest` for images or the toolchain. Pin them, and record the versions in run results.

## Important limits

- Never send `solution.v` to the frontend except through the solution endpoint that checks the unlock condition.
- Job containers: always `--network none`, a non-root user, and memory/CPU/pids/time limits. Never mount the Docker socket into a job container and never use `--privileged`.
- Every path from a request is normalized and checked to stay inside the project/run folder (there are path traversal tests).
- The backend binds to `127.0.0.1` by default.
- Do not copy HDLBits exercises or other copyrighted material into `content/`. Write your own.
- The chip tool ecosystem changes fast (OpenLane → LibreLane, Tiny Tapeout shuttles change). Before writing code that depends on a tool's CLI or file format, check the documentation of the pinned version or run `--help` inside the image; do not rely on memory.
