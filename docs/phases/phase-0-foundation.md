# Phase 0: Foundation

Goal: an app skeleton that runs end to end for one simple job kind, before any feature is built.

## Tasks

1. [x] **Toolchain image**
   - `make pin-toolchain && make toolchain` succeed.
   - `make tool-versions` prints the versions of yosys, iverilog, verilator, nextpnr-himbaechel, cocotb.
   - `make check-content` is green inside the image (the `counter-4bit` exercise is valid).
   - If binary names or arguments in OSS CAD Suite differ from what the Dockerfile assumes, fix the Dockerfile and record it in `DECISIONS.md`.

2. [x] **Backend skeleton** (`backend/`)
   - `pyproject.toml` (Python 3.12, fastapi, uvicorn, sqlmodel, pydantic-settings, docker, pyyaml, sse-starlette; dev: pytest, pytest-asyncio, httpx, ruff).
   - `app/config.py` reads `.env`.
   - `app/db.py` + `app/models.py` as in ARCHITECTURE (Project, File, Run, ExerciseProgress).
   - `GET /api/health` returns the app version and the Docker status (whether the daemon can be pinged).

3. [x] **Job system**
   - `jobs/runner.py`: the `JobRunner` interface (`start`, `stream_logs`, `wait`, `kill`).
   - `jobs/docker_runner.py`: the Docker implementation with every limit in ARCHITECTURE (network none, user, memory, cpus, pids, timeout).
   - `jobs/fake_runner.py`: a fake runner for unit tests (writes `result.json` from a fixture).
   - `jobs/queue.py`: two queues (light/heavy) with concurrency from `.env`.
   - Recovery at startup: `running`/`queued` runs → `failed`.
   - First job: `kind=echo`, which runs `yosys -V` in the toolchain image. Only to prove the pipeline works.

4. [x] **Run API**
   - `POST /api/runs` (temporary, for `echo`), `GET /api/runs/{id}`, `GET /api/runs/{id}/events` (SSE), `POST /api/runs/{id}/cancel`, `GET /api/runs/{id}/files/{path}` with path traversal protection and its tests.

5. [x] **Frontend skeleton** (`frontend/`)
   - Vite + React + TypeScript, React Router, one light UI library (for example Tailwind; shadcn/ui optional).
   - Typed API client from OpenAPI (`openapi-typescript`), with an `npm run gen:api` script.
   - A Dashboard page showing `/api/health` and a "Run echo job" button that shows the live log from SSE.
   - Basic layout: navigation sidebar (Dashboard, Latihan, Workspace, Proyek, Tapeout), in Indonesian.

6. [x] **Compose & commands**
   - `docker-compose.yml`: a `backend` service (mounts docker.sock, `content/` ro, `data/`), a `frontend` service (Vite dev server proxying `/api`).
   - Fill in the `make dev`, `make test`, `make lint`, `make check` targets (remove the `TODO`s in the Makefile).
   - `scripts/` or a make target to download the Surfer web build into `frontend/public/surfer/` (used in Phase 1).

## Done criteria

- [x] `make dev`, then open `http://127.0.0.1:8080`: the Dashboard shows, health is OK, Docker is detected.
- [x] Click "Run echo job": the Yosys version log appears live, and the status ends as `succeeded`.
- [x] Cancelling a long job (for example `sleep 60` in a test) sets the status to `cancelled` and removes the container.
- [x] Restarting the backend while a job runs: the run is marked `failed` with a reason.
- [x] `make check` is green (ruff, pytest, eslint, vitest, check-content).
- [x] Unit tests for: path traversal, queue concurrency, startup recovery (with `FakeRunner`).
