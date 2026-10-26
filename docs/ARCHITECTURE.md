# SmartX architecture

## Overview

```
Browser (React)
  │  HTTP + SSE
  ▼
Backend (FastAPI, Python)  ── SQLite (data/smartx.db)
  │  Docker API (socket)
  ▼
Job container (single use, one per run)
  ├─ light image: smartx/toolchain  (iverilog, verilator, yosys, nextpnr, nextpnr-mistral, cocotb)
  └─ heavy image: ASIC_IMAGE         (LibreLane + PDK)
        │
        ▼
  data/runs/<run_id>/   (inputs, logs, artifacts: result.json, .fst, .bit, .gds, reports)
```

The backend never runs EDA tools itself. It prepares a run folder, starts a container, streams the log to the browser, then reads `result.json` and the artifacts.

## Repository layout

```
smartx/
├─ CLAUDE.md                 working rules for Claude Code
├─ Makefile                  every command (make help)
├─ docker-compose.yml        backend + frontend (built in Phase 0)
├─ docker/
│  ├─ toolchain/Dockerfile   light image
│  └─ asic/                  notes/pin for the heavy image (Phase 5)
├─ backend/
│  ├─ pyproject.toml
│  ├─ app/
│  │  ├─ main.py             FastAPI app, mounts the routers
│  │  ├─ config.py           reads .env (pydantic-settings)
│  │  ├─ db.py               SQLite (SQLModel)
│  │  ├─ models.py           tables: Project, File, Folder, Run, ExerciseProgress
│  │  ├─ api/                one router per domain: exercises, projects, runs, boards, lessons, ...
│  │  ├─ content/            loaders for exercises, lessons, and board profiles from content/
│  │  ├─ jobs/
│  │  │  ├─ queue.py         asyncio queue, two classes: light & heavy
│  │  │  ├─ runner.py        JobRunner interface
│  │  │  ├─ docker_runner.py implementation with the docker SDK
│  │  │  └─ kinds/           one file per job kind (grade, lint, sim, fpga, asic, tt)
│  │  └─ reports/            report parsers: yosys.py (synthesis warnings), nextpnr.py (utilization, Fmax, critical paths); librelane later
│  └─ tests/
├─ frontend/
│  ├─ package.json           Vite + React + TypeScript
│  ├─ public/surfer/         Surfer web build (built by a script, gitignored)
│  └─ src/
│     ├─ pages/              Dashboard, Exercises, Exercise, Workspace, Projects, Tapeout
│     ├─ components/         Editor, FileTree, RunPanel, WaveView, FpgaPanel, FpgaReport, GdsView
│     └─ api/                typed client (generated from the backend's OpenAPI)
├─ content/
│  ├─ exercises/<id>/        step 1 exercises (format: docs/CONTENT-FORMAT.md)
│  ├─ projects/<id>/         step 4 guided projects
│  └─ boards/<id>.yaml       FPGA board profiles
├─ tools/
│  ├─ grader/                grade.py, sim.py, check_content.py
│  ├─ fpga/build.py          runs the FPGA build stages inside the image
│  └─ flash/smartx-flash     flashing helper on the host (Python stdlib + openFPGALoader; README for installation)
└─ data/                     runtime data, gitignored
```

## Data model (SQLite)

- **Project**: `id, name, kind (exercise|sandbox|guided|tt), source (exercise_id/project_id), created_at`
- **File**: `project_id, path, content, updated_at`. Project files live in the DB to keep autosave simple; on a run they are written to the run folder.
- **Folder**: `project_id, path`. Every folder in the tree has a row (including the parents of every file), so empty folders persist. Paths are validated in `app/projects/paths.py` and are unique regardless of letter case.
- **Run**: `id, project_id, kind, status, params (JSON), result (JSON), tool_versions (JSON), created_at, started_at, finished_at, exit_code, error`
- **ExerciseProgress**: `exercise_id, status, attempts, last_code, solved_at, hints_opened`

Run status: `queued → running → succeeded | failed | cancelled | timeout`.

## Job kinds

| kind | Image | Class | Input | Main output |
|---|---|---|---|---|
| `grade` | light | light | user code + exercise folder | `result.json` (tests, Icarus diagnostics, Verilator lint), `.fst` |
| `lint` | light | light | copy of the project files (`project/`) + config | `lint.sarif` → diagnostics (file, line, column, severity, code, message) |
| `sim` | light | light | copy of the project files (`project/`) + `sim.json` (config) | `result.json` (tests per module, compile errors, simulator version), `.fst` |
| `fpga` | light | light | copy of the project files (`project/`) + `fpga.json` (one command per stage, from the board profile) | `result.json` (status per stage, first error, Yosys diagnostics, tool versions); `collect()` adds synthesis warnings, utilization, Fmax, and critical paths (`app/reports/`); `build/`: bitstream, nextpnr `report.json`, `stat`, a log per stage |
| `asic` | ASIC_IMAGE | heavy | files + `config.yaml` + PDK | GDS, metrics, reports, layout PNG |
| `tt_harden` | ASIC_IMAGE | heavy | TT repository from the generator | TT GDS, warnings |

Each job kind is one module in `backend/app/jobs/kinds/` with `JOB_CLASS`, `OK_EXIT_CODES`, a `Params` model, and two functions: `prepare(run_dir, params, ctx) -> ContainerSpec` and `collect(run_dir) -> dict`. `ctx` (`JobContext`) gives access to the settings and the exercise catalog. This keeps new job kinds easy to add and easy to test without Docker (unit tests for `prepare` and `collect` use fixture folders).

## Docker runner

- Uses the Python `docker` SDK through `/var/run/docker.sock`, mounted into the backend container.
- Every job: `docker run --rm --network none --user <uid>:<gid> --memory <limit> --cpus <n> --pids-limit 512`, with `data/runs/<id>` mounted at `/work` (rw). Other mounts are requested through `ContainerSpec`: `tools/` at `/tools` (ro), run subfolders mounted again read-only, and `content/` at `/content` (ro). Jobs that run user code **must not** mount `content/`, because it holds `solution.v`; the exercise files they need are copied into the run folder.
- Run folder paths must be **host** paths, because job containers are created by the host's daemon. The host `SMARTX_DATA_DIR` is kept in the config and paths are translated.
- stdout/stderr are read as a stream, written to `run.log`, and forwarded over SSE.
- Timeout per class (`JOB_LIGHT_TIMEOUT_S`, `JOB_HEAVY_TIMEOUT_S`). On timeout or cancel: `container.kill()`, status `timeout`/`cancelled`.
- On backend start: runs that are `running`/`queued` become `failed` with the error "backend restarted".

## API (summary)

```
GET  /api/health
GET  /api/exercises                       list + progress
GET  /api/exercises/{id}                  statement, starter/latest code, opened hints
POST /api/exercises/{id}/runs             {code} -> run
POST /api/exercises/{id}/hints/next
GET  /api/exercises/{id}/solution         403 until the unlock condition is met

GET  /api/project-templates
GET  /api/snippets                        cocotb testbench snippets (content/snippets/*.yaml)
GET  /api/lessons?step=2                  short lessons (content/lessons/*.md)
GET  /api/projects | POST /api/projects       {name, template | exercise_id}
GET | PATCH | DELETE /api/projects/{id}       detail + tree | rename | delete
POST /api/projects/{id}/files                {path, content} (409 if it exists)
GET | PUT | DELETE /api/projects/{id}/files/{path}   PUT = save (autosave), DELETE on a folder = recursive
POST /api/projects/{id}/folders              {path}
POST /api/projects/{id}/move                 {from_path, to_path}: rename/move a file or folder
GET | PUT /api/projects/{id}/config           smartx.yaml: text + parse result + problems | save from the form
POST /api/projects/{id}/config/check          {text}: check YAML that is still being typed (not saved)
POST /api/projects/{id}/runs              {kind: lint|sim|fpga}: copy the project files into the run folder, take params from smartx.yaml
GET  /api/projects/{id}/runs?limit=50     history: time, kind, status, duration, summary (newest first)
GET  /api/projects/{id}/runs/compare?a=&b=  tests whose status changed between two simulations
GET  /api/projects/{id}/runs/{run_id}     run + the result for its kind (lint, sim, fpga)
GET  /api/runs/{id}
GET  /api/runs/{id}/events                SSE: log, status
POST /api/runs/{id}/cancel
GET  /api/runs/{id}/files/{path}          artifacts (path traversal is blocked)

GET  /api/boards                          FPGA board profiles + constraint template + flash command (content/boards/)
POST /api/projects/{id}/tapeout/generate
```

The frontend uses a client generated from the backend's OpenAPI (`openapi-typescript`), so types are not written twice.

## Waveform viewer

Uses the web (WASM) build of **Surfer**, self-hosted in `frontend/public/surfer/` and shown in an `<iframe>`. Surfer can load files from a URL and be controlled with `postMessage`; that API is documented in `surfer/assets/integration.js` in the Surfer repository and may still change, so every interaction is wrapped in one `WaveView` component and the Surfer version is pinned.

Fallback if the integration breaks: a button to download the `.fst` and open it in desktop GTKWave/Surfer.

## GDS layout viewer

For Phase 5, PNGs rendered by KLayout in batch mode (`klayout -zz -r render.py`) in the ASIC container, at several zoom levels, are enough. An interactive viewer (for example a GDS → glTF conversion for a 3D view) is an optional extension.

## Security (single user)

- The backend binds to `127.0.0.1` by default. Access from other networks must go through a reverse proxy with authentication.
- Access to the Docker socket is equivalent to root on the host. This is accepted because the app is personal, but still: job containers never get the socket, always run with `--network none`, and never run `--privileged`.
- Every path from the user is normalized and checked to stay inside the project/run folder.

## Machine requirements

| Phase | CPU | RAM | Disk |
|---|---|---|---|
| 0–4 | 2 cores | 4 GB | ~5 GB (toolchain image ~2 GB) |
| 5–6 | 4+ cores | 12–16 GB | +25 GB (ASIC image ~4 GB + PDK + run results) |
