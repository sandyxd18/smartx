# Decision log (short ADRs)

Every important decision is recorded here: brief context, the choice, the reason. Decisions marked **[CONFIRM]** were made as defaults and should be checked by the project owner. Add new entries at the bottom; never delete old entries, mark them as superseded instead.

## D01. Local web app, not a desktop app
Browser + backend in Docker. Reason: EDA tools only run well on Linux; with a web UI the app can run in a VM/server and be opened from any laptop. No Electron needed.

## D02. Python backend (FastAPI) + SQLite
cocotb, the report parsers, and LibreLane are all Python, so one language for the backend and the tooling. SQLite is enough for one user; no Postgres/Redis. The job queue uses `asyncio` inside the backend process, without Celery.

## D03. React + Vite + TypeScript frontend, Monaco editor
Monaco supports Verilog/SystemVerilog through Monarch language definitions and is widely used.

## D04. One container per job through the Docker socket
Isolation, resource limits, and consistent tool versions. The alternative (subprocesses in the backend container) is slightly faster but mixes backend dependencies with EDA tools and complicates the large ASIC image.

## D05. Digital toolchain from OSS CAD Suite, pinned by date
Ubuntu apt packages for Yosys/nextpnr lag far behind. OSS CAD Suite gives one consistent bundle; the release date is pinned in `.env`.

## D06. ASIC flow with LibreLane, not OpenLane 1
OpenLane 2 continued under the FOSSi Foundation as LibreLane (released July 2025). Tiny Tapeout uses a LibreLane-based flow. Old OpenLane configurations remain compatible.

## D07. ASIC image: IIC-OSIC-TOOLS (pinned tag) **[CONFIRM in Phase 5]**
An all-in-one image from JKU (~4 GB) with the SKY130/GF180/IHP PDKs and digital/analog tools. When Phase 5 starts, check whether its LibreLane version matches what the `tt-support-tools` of the target shuttle needs. If not, use LibreLane's official image or installation method.

## D08. Default FPGA board: Tang Nano 9K **[CONFIRM]**
Cheap, easy to get, supported by the open-source toolchain (Yosys + nextpnr-himbaechel + Apicula + openFPGALoader). iCE40 (iCEBreaker/UPduino) is the second target, as the most mature board in the open-source ecosystem. Change this if the owner already has another board.

## D09. FPGA flashing on the host, not in a container
USB passthrough to Docker is fragile (especially on WSL/macOS). The backend only produces bitstreams; the `tools/flash/smartx-flash` script on the host calls `openFPGALoader`.

## D10. Waveforms: Surfer web, self-hosted
Surfer runs in the browser (WASM), can be embedded in an iframe, and is controlled with `postMessage`. Its API is not stable yet, so the version is pinned and the integration is wrapped in one component.

## D11. Exercise content is written from scratch
HDLBits exercises are not copied. Every exercise in `content/` is original, with a solution and testbench that are tested automatically (`make check-content`).

## D12. Tapeout through Tiny Tapeout, manual submission
The app builds a repository that follows the TT template and runs local hardening. Submission and payment on app.tinytapeout.com stay manual. The shuttle (SKY/IHP/GF) is chosen through an easily updated profile, because every shuttle has its own `tt-support-tools` branch.

## D13. Development host: native Windows, make through Git for Windows' bash
The owner runs the project directly on Windows (not WSL). GNU Make is installed from winget (`ezwinports.make`). On Windows, the Makefile uses `C:/Progra~1/Git/bin/bash.exe` as `SHELL` (overridable through `GIT_BASH`) so the same bash recipes work from PowerShell and Git Bash, and exports `MSYS_NO_PATHCONV=1` so container paths such as `/work` are not turned into Windows paths. `PY` defaults to `python` on Windows because `python3` there is usually the Microsoft Store stub. `.gitattributes` forces LF because the files are used in Linux containers.

## D14. Toolchain image fixes (Phase 0)
Tested with OSS CAD Suite `2026-10-24` (Yosys 0.70+219, Icarus 14.0 devel, Verilator 5.053 devel, nextpnr 0.11.1, cocotb 2.1.0). The release file names matched the Dockerfile's assumption. Two fixes:
- cocotb needs `libpython3.12.so`, which the `python3` package on Ubuntu 24.04 does not include; `libpython3.12t64` was added. Without it every exercise ended in `compile_error` ("Unable to find libpython").
- `ubuntu:24.04` already has a `ubuntu` user with UID 1000, so `useradd -u 1000` failed silently because of `|| true`. The `ubuntu` user is removed first, then `smartx` is created without `|| true`.

The tested date is written in `.env.example`, so a fresh clone uses the same versions. `make pin-toolchain` remains for deliberate upgrades; after upgrading, run `make check-content`.

## D15. Backend skeleton (Phase 0 task 2)
- Dependencies and the venv are managed by `uv` (`backend/pyproject.toml` + `uv.lock` committed, Python 3.12 through `.python-version`). The app version has one source: `app/__init__.py`.
- The app is built by a `create_app(settings)` factory (`uvicorn --factory app.main:create_app`) so tests can pass their own `Settings` and data folder.
- A relative `SMARTX_DATA_DIR` is resolved against the repository root, not the working directory.
- Tables are created with `SQLModel.metadata.create_all`; there are no migrations yet. Once the schema starts changing while there is data worth keeping, add Alembic.
- `Run.id` is a uuid4 hex (not an integer) so `data/runs/<id>` folders never collide after the database is reset.
- The Docker status in `/api/health` comes from a `get_docker_probe` dependency, replaced by a fake probe in tests. The probe never raises: if Docker is down, health is still 200 with `docker.available=false`.
- Starlette 1.x warns that `httpx` for `TestClient` is superseded by `httpx2`. For now it stays `httpx` (as the phase plan says) and only that warning is silenced in the pytest configuration; other warnings are errors. Move to `httpx2` once the package has been checked.

## D16. Job system (Phase 0 task 3)
- The queue uses two `asyncio.Semaphore`s (light/heavy) inside the backend process, without a broker. A job kind sets its class through the `JOB_CLASS` constant; `DockerRunner` takes the image and resource limits from that class (light → `TOOLCHAIN_IMAGE`, heavy → `ASIC_IMAGE`). So `prepare(run_dir, params)` does not need to know the image name.
- Container hardening beyond what ARCHITECTURE lists: `cap_drop=ALL`, `no-new-privileges`, and `memswap_limit` equal to `mem_limit` (no extra swap). Every container gets a `smartx.run_id` label. At startup every container with that label is removed, because a new backend cannot continue old jobs.
- Windows has no `os.getuid()`, so job containers run as `1000:1000` (the `smartx` user in the image). Configurable through `JOB_USER`.
- The Docker client used for log streams and `wait` has no read timeout. docker-py's default of 60 seconds would cut the log stream of a job that is silent for longer. Job time limits are enforced by the queue (`JOB_*_TIMEOUT_S`).
- On a clean backend shutdown, running containers are killed, but the run status is left `running`. On the next start, recovery marks it `failed` with the same message as after a crash, so both paths end in one behavior.
- `kind=echo` accepts `sleep_s` (int 0–600, strictly validated) to test cancel and timeout from the UI without a test-only job kind.
- User-facing run error messages are written in Indonesian, including the recovery message ("Backend di-restart saat run ini belum selesai.").
- Tests with real Docker live in `backend/tests/integration/` and only run when `SMARTX_DOCKER_TESTS=1`. Unit tests keep using `FakeRunner`.

## D17. Run API and SSE (Phase 0 task 4)
- `POST /api/runs` temporarily only accepts `kind=echo`. Parameters are validated by the job kind's `Params` model before the run is created, so bad input gets a 422 right away instead of becoming a `failed` run. Every job kind must have `Params`.
- SSE `GET /api/runs/{id}/events` sends `log` (`{"line"}`) and `status` (`{"status"}`) events as JSON. The stream starts by replaying `run.log` and the current status, then forwards live events until the final status, then closes. No events are duplicated or lost, because the queue writes the log, updates the status, and publishes events without an `await` in between, and followers take their snapshot the same way (see `app/jobs/stream.py`). A ping every 15 seconds.
- `run.log` is always written with LF, also on Windows.
- Timestamps in API responses are always UTC-zoned, because SQLite drops time zone information and the browser would read them as local time.
- Artifact paths go through `app/paths.py::safe_join`. Rejected (400): `..` segments, absolute paths, Windows drives, UNC paths, NUL, and symlinks pointing outside the run folder. Backslashes count as separators. `run_id` must be 32 hex characters, so it cannot be used for traversal. The symlink test is skipped on Windows without Developer Mode.

## D18. Frontend skeleton (Phase 0 task 5)
- Vite 8, React 19, React Router 8 (the `react-router` package), Tailwind 4 through `@tailwindcss/vite`. Tests use Vitest 5, jsdom, and Testing Library. ESLint 10 flat config with typescript-eslint (type-checked) and `--max-warnings 0`.
- TypeScript is pinned to `~5.9.3`, not 7.x: typescript-eslint 8.72 only supports `<6.1` and openapi-typescript 7 requires `^5`. Upgrade once both support the new version.
- API client: `openapi-typescript` generates `src/api/schema.d.ts` (committed) and `openapi-fetch` uses it. `npm run gen:api` gets the schema with `uv run python -m app.openapi_dump` in `backend/`, so no running server is needed. After changing the backend API, run `npm run gen:api`.
- Ports: the browser only talks to Vite on `SMARTX_PORT` (8080). Vite proxies `/api` to the backend at `SMARTX_API_URL` (default `http://127.0.0.1:8000`). As a result the backend no longer uses `SMARTX_PORT`; `.env` and compose were adjusted in task 6.
- `useRunEvents` clears the log on every `EventSource` (re)connect, because the server replays the whole log on every connection. The stream is closed from the client on the final status, so the browser does not reconnect on its own.
- 502–504 from the dev proxy are shown as "Backend tidak bisa dihubungi", with a "Periksa lagi" button. Found while testing in the browser: the frontend is often ready before the backend.
- `.claude/launch.json` holds the `backend` (port 8000) and `frontend` (port 8080) configurations for previews in Claude Code.

## D19. Compose, make commands, and Surfer (Phase 0 task 6)
- `make dev` runs `docker compose up --build --renew-anon-volumes`. `backend` (uvicorn `--reload`, not published to the host) holds the Docker socket. `frontend` (Vite) is published on `${SMARTX_BIND}:${SMARTX_PORT}`, default `127.0.0.1:8080`, and only starts once the backend healthcheck is green. Base images are pinned: `python:3.12.15-slim-bookworm` + `uv==0.13.0`, and `node:24.22.1-bookworm-slim`.
- The Makefile exports `SMARTX_HOST_DIR=$(CURDIR)`. Compose passes it on as `SMARTX_HOST_DATA_DIR`/`SMARTX_HOST_CONTENT_DIR`, so job containers created by the backend from inside a container get host paths (on Windows: `C:/Users/.../data/runs/<id>`). Tested: echo and cancel through compose.
- The backend in compose runs as root, because it needs the Docker socket. To keep jobs from running as root too: `default_job_user()` falls back to `1000:1000` when the backend has uid 0, `JOB_USER` rejects uid 0, and run folders are `chown`ed to the job user when the backend is root. On Linux the Makefile sets `JOB_USER` to the caller's uid:gid.
- On Windows, bind mounts do not forward file change events. So uvicorn uses `WATCHFILES_FORCE_POLLING` and Vite uses polling (`SMARTX_WATCH_POLLING`). The frontend's `node_modules` lives in a container volume, because the host's holds Windows binaries.
- `make test`/`make lint` run on the host (uv + npm). `make check` = lint + test + `test-docker` + `check-content`. The frontend lint also fails when `schema.d.ts` does not match the backend API (`gen:api --check`). Backend tests remove the `.env` variables from the environment, because the Makefile exports them.
- Surfer: Surfer releases only contain native binaries, and the web build only exists as a CI artifact that expires within an hour. So `make surfer` builds the web version from the pinned tag (`SURFER_VERSION=v0.7.0`, `rust:1.99.1-bookworm`, trunk v0.21.14) with the same steps as Surfer's `pages_build` CI job, then exports it to `frontend/public/surfer/` (gitignored, about 13 MB). The first build takes about 4 minutes. Checked: the viewer loads from `/surfer/index.html` without errors, and `integration.js` (the `postMessage` API) is included.
- Windows note: after `docker compose down`, Docker Desktop may hold port 8080 for a few dozen seconds (`EADDRINUSE` with no visible listener).

## D20. Content loader (Phase 1 task 1)
- `app/content/` validates `exercise.yaml` with Pydantic (`extra="forbid"`, so a misspelled field name shows up immediately). The rules: `id` is kebab-case and equals the folder name, `files.*` must be plain file names that exist in the exercise folder (no `/`, `\`, `..`, or hidden files), and every `requires` must point at an existing exercise.
- Invalid exercises are skipped and recorded in `catalog.errors` and the log. The app keeps running with the other exercises.
- Reloading without a watcher: whenever the catalog is accessed, the mtime and size of every `exercise.yaml` are compared with the previous values. For a few dozen exercises the cost is small, and it still works on Docker Desktop bind mounts on Windows, which do not forward file change events. Statements and starters are always read from disk on request. Can be turned off with `SMARTX_CONTENT_RELOAD=false`.
- Exercise order: `step`, then `order` (exercises without `order` last), then `id`. Grouping by topic is decided on the list page (task 4).
- The test `test_repo_content_is_valid` loads the real `content/` folder, so an exercise with broken metadata makes `make test` fail, not only `check-content`.

## D21. `grade` job (Phase 1 task 2)
- **Exercises are not mounted from `content/`.** The phase plan said "mount the exercise read-only", but `content/` holds `solution.v`, and the user's Verilog code could read it with `$fopen` and print it to the log. So `prepare()` only copies `exercise.yaml` and the testbench into `run/exercise/`, which is then mounted read-only at `/exercise`. The user's code is written to `run/user.v`. The integration test `test_grade_cannot_read_solution` makes sure an `$fopen` of the solution fails. The default of `ContainerSpec.mount_content` is now `False`.
- The grader comes from `tools/`, mounted read-only at `/tools` (not baked into the image), so the app and `make check-content` always use the same grader. Compose passes on `SMARTX_HOST_TOOLS_DIR`.
- Job kind interface: `prepare(run_dir, params, ctx)` with a `JobContext` (settings + catalog), `OK_EXIT_CODES` per kind, and `JobInputError` for input that passes validation but cannot be used (for example a missing exercise). The grader exits with code 1 when a test fails; that is a verdict, not a broken job, so the run is still `succeeded` and the verdict is in `result.status` (`pass`/`fail`/`compile_error`/`error`).
- Grade timeout = the exercise's `timeout_s` + 30 seconds (container start, compilation, cocotb startup), through `ContainerSpec.timeout_s`.
- `collect()` maps `wave_file` from the container path (`/work/...`) to a path relative to the run folder and a `wave_url` (`/api/runs/<id>/files/...`). Paths not under `/work`, containing `..`, or whose file does not exist are ignored.
- Icarus compile errors are parsed into `diagnostics: [{line, severity, message}]`, only for `dut.v` (the copy of the user's code). Messages from cocotb's dump module (`cocotb_iverilog_dump.v`) are dropped. Icarus often reports an error on the line *after* the real mistake (for example a missing semicolon), and may give several messages for one line; line numbers are passed on as they are.
- The `collect()` fixtures (`tests/fixtures/runs/grade-*`) come from real grader output in the toolchain image. `.gitignore` makes exceptions for `sim_build/` and `*.fst` in the fixture folders.

## D22. Exercises API and progress (Phase 1 task 3)
- Endpoints as in ARCHITECTURE. `GET /api/exercises/{id}` returns the statement, the starter, `code` (the last code that was Run, or the starter), only the hints already opened, `solution_available`, and `last_run`, so the UI can show the last result after a page refresh.
- Every Run increments `attempts` and stores `last_code` in the same transaction that creates the run, including runs that fail to compile. The status becomes `attempted`, then `solved` through an `on_finished` hook in `JobQueue`. The hook is called after the final status is stored and before the SSE event is sent, so by the time the UI receives the final status the progress is correct. `solved` never goes back down, and `solved_at` is the time of the first pass.
- The solution endpoint (`GET .../solution`) is the only way `solution.v` leaves the server. It answers 403 until the exercise is passed or `attempts >= SOLUTION_UNLOCK_ATTEMPTS` (default 5). Tests put a marker in `solution.v` and make sure the marker never appears in the responses of other endpoints.
- `POST .../hints/next` opens the next hint. Once every hint is open, it changes nothing (still 200).
- An exercise's latest run is found through `params.exercise_id` (JSON in SQLite), so the table schema did not change and no migration is needed yet.
- Measured through compose (the API, not yet through the UI): grading `counter-4bit` takes 1.0–1.9 seconds from POST to the final status.

## D23. Exercise list page (Phase 1 task 4)
- Exercises are grouped by **first topic** (`combinational`, `sequential`, `fsm`, `pitfalls` → Kombinasional, Sekuensial, FSM, Jebakan umum), with the group order following the curriculum. Within a group the order is the API's (step, order, id). This convention is recorded in CONTENT-FORMAT, section "Topics".
- Status labels follow the phase plan: `not_started` = "Belum", `attempted` = "Gagal", `solved` = "Lulus". The number of attempts is shown next to it. Levels 1–3 = Dasar, Menengah, Lanjut.
- Filters (text, status, level) live in the query string (`?q=&status=&level=`), so they survive a refresh and can be shared as a link.
- `/latihan/:id` showed a placeholder until the exercise page was built in task 5.

## D24. Exercise page and editor (Phase 1 task 5)
- Monaco is self-hosted, not loaded from a CDN (the `@monaco-editor/react` default), so the app works without internet. Only the editor features (`monaco-editor/features/register.all`), Monaco's built-in Verilog/SystemVerilog Monarch grammar (`languages/definitions/systemverilog/register`), and `editor.worker` are loaded. The TS/CSS/HTML/JSON language services from `editor.main` are deliberately left out. The exercise page is a lazy route, so the Monaco chunk (~4 MB, ~1 MB gzipped) only loads when an exercise is opened.
- `monaco-editor` 0.57.0 pins `dompurify` 3.4.15, which is affected by critical XSS advisories (GHSA-p98j-92pf-mc4p and related). `package.json` forces `dompurify` 3.4.17 through `overrides`. Remove the override once Monaco releases a version with the fixed dompurify. `@tailwindcss/typography` is not used, because it pins a vulnerable `postcss-selector-parser`; statements are styled with our own CSS (`.markdown` in `index.css`).
- Statements are rendered with `react-markdown` + `remark-gfm` (for tables), without raw HTML. The H1 at the start of the README is dropped, because the page title comes from `exercise.yaml`.
- Grade results in the API have the type `GradeResult` (Pydantic; also used by `collect()`), with `ExerciseRunRead.grade` and the endpoint `GET /api/exercises/{id}/runs/{run_id}`. So the frontend never writes result types by hand.
- **Bug found while testing in the browser:** Ctrl+Enter pressed right after typing sent the *old* code. Monaco already held the new text, but React had not re-rendered, so the `code` state was still the previous version. Fix: `onRun` receives the current contents of the Monaco model (`editor.getValue()`), and that value is used. There is a regression test.
- Error markers use the grader's `diagnostics` through `setModelMarkers`; line numbers out of range are clamped to the last line. Markers stay until the next Run.
- On narrow screens (< `lg`) the statement is shown above the editor; on wide screens they sit side by side.
- Measured in the browser (backend on the host, separate data): 1.2–1.7 seconds from clicking Run to the result for `counter-4bit`.

## D25. Code autosave (Phase 1 task 6)
- `PUT /api/exercises/{id}/code` (204) only stores `last_code`. It does not count an attempt, change the status, or unlock the solution; only Run counts as an attempt.
- `useAutosave` saves 1 second after the last keystroke. Saves run in sequence (a promise chain), so an old draft can never land after a newer one. Only user edits (typing, reset to starter) trigger a save; loading the page does not.
- Unsaved changes are flushed on `pagehide`, on `visibilitychange` to hidden, and on component unmount (navigating inside the app), using `fetch` with `keepalive: true` so the request is still sent when the page is closed or refreshed. Tested in the browser: typing and reloading right away (before the 1-second pause) still saves the code, with exactly one PUT.
- If a save fails, "Gagal menyimpan" is shown; the next keystroke retries with the latest text. There is no automatic retry without a keystroke yet.

## D26. WaveView (Phase 1 task 7)
- `WaveView` loads the Surfer build from `make surfer` in an iframe (`/surfer/index.html#dev`). `#dev` is Surfer's own option for not registering its service worker. That service worker caches nothing, but it would intercept every request from the iframe and add COEP/COOP headers; Surfer runs normally without it.
- Files are loaded through the API documented in `integration.js` v0.7.0: `postMessage({command: "LoadUrl", url})`. The message listener is installed before the WASM is ready, but `inject_message` only exists afterwards, so messages sent too early are lost. Because the iframe has the same origin, `WaveView` waits until `inject_message` exists (polling every 100 ms, at most 20 seconds) before sending. If it is never ready, the user is pointed to the `.fst` download button.
- Surfer's availability is checked from the contents of `/surfer/SURFER_VERSION`, not the HTTP status, because the Vite dev server answers missing paths with `index.html` (200). If it is not installed, the page suggests `make surfer`.
- A new run loads its waveform into the same viewer (without a reload). The Waveform tab stays mounted once opened, so switching tabs does not reload the WASM. While a run is going, the previous waveform stays visible. The result panel grows (32rem) while the Waveform tab is active. A test caught a double send when the viewer had just become ready; fixed by remembering the last URL sent.
- Tested in the browser: `counter-4bit` from starter to passing through the UI (3/3 tests, 1.9 seconds), then the Waveform tab loads that run's `.fst` in Surfer, and the signals `clk`, `en`, `q[3:0]`, `rst` show.
- Not done: Surfer does not show signals automatically; the user picks a scope and presses "+". Adding signals automatically needs `InjectMessage` with Surfer's `Message` enum, which `integration.js` describes as not stable yet, so it is postponed.

## D27. 22 new exercises (Phase 1 task 8)
- The phase plan said "19 more exercises", but the curriculum table in CONTENT-FORMAT has 23 rows (including `counter-4bit`). Every row was written, so there are **22 new exercises, 23 in total**. That meets "at least 20" without having to pick three to drop.
- The row "D flip-flop (sync/async reset)" is split in two: **asynchronous** reset in `dff-async-reset`, **synchronous** reset in `register-8bit`. Each has a test that fails the wrong kind of reset.
- Besides "the solution passes, the starter fails", every key exercise is tested with **plausible wrong implementations**, which must all fail: synchronous reset in the asynchronous exercise and the other way around, Moore in the Mealy exercise and the other way around, a priority encoder where the lowest bit wins, a 3-cycle debouncer, a 3-cycle green light. The Moore/Mealy tests check `z` before (Mealy) or after (Moore) the rising clock edge. The LFSR period (taps 8,6,5,4) was checked to be maximal (255) by a generator before the exercise was written.
- The three "common pitfall" exercises hold buggy code that compiles (accidental latch, blocking `=` in a pipeline, two `assign`s to one wire), and their failure messages point at the cause.
- The grader (`tools/grader/grade.py`, `clean_message`) drops the assertion introspection cocotb appends (`assert 1 == 0`, `+ where ...`) after the test author's message, because it confuses beginners. Tested in `backend/tests/test_grader_messages.py`.
- `counter-4bit` got `order: 30` and `requires: [register-8bit]` to sit in order within the Sekuensial group.
- `make check-content` now takes about 3 minutes (23 exercises × 2 runs). If that gets in the way, run the exercises in parallel in the grader.
- Frontend: the root route has a `hydrateFallbackElement` ("Memuat halaman…"). Without it, opening an exercise page by URL showed a white screen while the lazy route (Monaco) loaded, several seconds on a freshly started dev server. The exercise page tests load the module in `beforeAll`, because the first two tests used to fail (`findBy` timeouts) on a busy machine.

## D28. Verilator lint on Run (Phase 1 task 9)
- Lint runs **inside the same `grade` job**, before the Icarus compilation, not as a separate job or container. `verilator --lint-only` on one small file takes about 60 ms, while a new container adds about 1 second. A separate `lint` job was still planned for the workspace (Phase 2), and its parser (`app/jobs/verilator_lint.py`) can be reused.
- Command (flags checked with `verilator --help` in the image, Verilator 5.053): `verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-EOFNEWLINE -Wno-fatal --quiet --top-module <toplevel> dut.v`. `DECLFILENAME` is off because the file is always called `dut.v`. `EOFNEWLINE` is off because the editor may save without a final newline. The grader writes the raw output to `lint_log` in `result.json`, and the backend parses it into `GradeResult.lint`: line, column, warning code, and message.
- Lint is only advice; pass/fail is still decided by the simulation. Every finding, including Verilator's `%Error`, is shown as a **warning** (yellow). If Verilator is missing or crashes, `lint_log` is empty and grading proceeds as usual. For a `compile_error` status, lint is not shown because Icarus already marks the broken line.
- Messages start with a short Indonesian explanation for the warnings beginners meet most often (LATCH, CASEINCOMPLETE, BLKSEQ, COMBDLY, WIDTH*, UNDRIVEN, UNUSED*, MULTIDRIVEN*, and others). Verilator's original text is kept so it can be searched on the internet.
- Monaco underlines the word at the column Verilator points at, not the whole line. The Tests tab shows a "Peringatan Verilator" list.
- `check_content` now also requires `solution.v` to be free of lint warnings, because the official solution is an example users copy. All 23 existing solutions are clean. The rule is proven with a solution given an unused signal: that exercise is rejected. Note: by default Verilator ignores signals whose names contain `unused`.
- Tested in the browser with real Docker: the `pitfall-latch` starter shows a LATCH warning on line 10, with the word `always` underlined. 2.7 seconds from clicking Run to the result.

## D29. Container cleanup per installation (Phase 1 review finding)
- During the review, one Docker test (`test_sandbox_restrictions`) failed. The cause: another backend that had just started ran its startup recovery and removed **every** container labeled `smartx.run_id` in Docker, including the test's running container. When the test then removed its own container, Docker answered `409 removal already in progress`, and a run that had actually succeeded was recorded as `failed`.
- Fix 1: every job container gets a `smartx.instance` label, the first 16 characters of the SHA-256 of the data location on the host (`SMARTX_HOST_DATA_DIR` if set, otherwise the absolute `data_dir`). `remove_orphans` only removes containers of the same instance. So `make dev`, compose, and `make check` can share one Docker without disturbing each other.
- Fix 2: `cleanup` and `remove_orphans` treat 404 (already removed) and 409 (being removed by someone else) as success. Other Docker errors are still reported.
- As a result, containers left over from versions before this label are no longer cleaned up automatically. If there are any, remove them once with `docker rm -f $(docker ps -aq --filter label=smartx.run_id)`.

## D30. Sandbox projects and the file tree (Phase 2 task 1)
- Project files stay in the `File` table (see ARCHITECTURE). Folders are stored in a new `Folder` table, one row per folder, including the parents of every file. That way an empty folder is not lost after its last file is deleted. Because the table is new, `create_all` creates it and existing databases need no migration.
- Project paths are validated in `app/projects/paths.py`. A path must be relative with `/` as the separator, without empty, `.` or `..` segments, and without backslashes. Names use letters, digits, `_`, `-`, and `.`, do not start with `.` and do not end with `.`. Windows device names (`con`, `nul`, `com1`, and so on) are rejected. At most 200 characters and 8 levels deep. Uniqueness is checked **regardless of letter case**, because on a run the files are written to a folder on a Windows host. Renames that only change letter case are still allowed.
- Limits per project: 300 entries (files + folders) and 500,000 characters per file. Violations get a 422 with an Indonesian message; a name already in use gets a 409.
- `PUT /files/{path}` saves (and creates the file if it does not exist, for autosave). `POST /files` only creates a new file (409 if it exists). `DELETE` on a folder deletes everything in it. Deleting a project is refused (409) while it has a `queued`/`running` run; otherwise its old runs and their folders are deleted with it.
- Projects from templates or exercises are all `kind = sandbox`, with `source = "template:<id>"` or `"exercise:<id>"`. Templates are written from scratch in `content/templates/` (`empty`, `cocotb-basic`). The `cocotb-basic` testbench was checked in the image: it passes for its design and fails for two mutants.
- Templates and projects copied from exercises already contain a draft `smartx.yaml` (`top`, `sources`, `tests`, `simulator`). Its validation and form came in task 2.
- Frontend: `/workspace` (project list + "Proyek baru" form; exercises grouped by topic) and `/workspace/:id` (file tree + Monaco). Autosave uses one `useAutosave` per page with `{path, content}` values. The hook is now generic and has `settle()`, which saves pending changes and waits until done. `settle()` is called before switching files, creating, renaming, or deleting, so a late autosave cannot write to the wrong file or bring a just-deleted file back. There is a mutation test for this ordering.
- On Windows, Monaco uses CRLF line endings for new or single-line files; this showed up when checking in the browser. `CodeEditor` now forces the model to LF, so project files and exercise code are saved with LF line endings.
- Monaco now also loads the Python, YAML, and Markdown grammars for project files. The language comes from the file extension (`editor/languages.ts`).
- Not in the UI yet: renaming a project (the `PATCH` API exists) and moving a file to another folder (the `move` API supports it, but renaming in the tree only changes the name within the same folder).

## D31. Project configuration smartx.yaml (Phase 2 task 2)
- `smartx.yaml` stays an ordinary project file (stored in the `File` table), so it can be edited, renamed, and exported like any other file. The single source of its rules is `ProjectConfig` in `app/projects/config.py` (Pydantic, `extra="forbid"`). The full format is in CONTENT-FORMAT.
- Checking `--help` and the source in the pinned image (cocotb 2.1.0) showed that the runner writes `defines` as `-DNAME=value` and `parameters` as `-P<top>.NAME=value` (Icarus) or `-GNAME=value` (Verilator), using `str(value)`. So values are limited to integers or text: `None` would become `-DFOO=None`, and `True` would become `True`. Whether Icarus accepts text such as `8'hFF` in `-P` was not tested yet; that was checked in task 4 with the `sim` job.
- Error messages are in Indonesian, and every error is mapped to its YAML line by walking the `yaml.compose` node tree. For mapping entries the key's line is used. Warnings are computed against the project's contents and do not block saving: `sources` patterns that match nothing, a missing top module (regex `module <top>`), missing test files, and an empty `tests`.
- Globs are implemented by hand (`*`, `?`, and `**` as a whole segment), because `PurePath.full_match` only arrived in Python 3.13. Matching is case-sensitive, like the Linux container where the simulation runs.
- API: `GET /config` reads and analyzes the stored file. `POST /config/check {text}` analyzes text that is still being typed without saving it, so problems show right away without waiting for autosave. `PUT /config` (from the form) rewrites `smartx.yaml` from the form's contents; hand-written comments are lost and only the header line is kept.
- UI: opening `smartx.yaml` in a project shows "Form | YAML" tabs. The form is chosen when the file is valid, YAML when it has errors. YAML mode is an ordinary editor (file autosave) with problems as Monaco markers. Form mode saves on its own (600 ms debounce), then the saved text is passed back to the editor. Syncing happens when switching modes: before going to the form, the pending YAML save is awaited and the text is checked again; before going to YAML, the form save is awaited. The form cannot open while the YAML still has errors. The project page also waits for form saves before switching files or changing the tree; there is a mutation test for this.
- When checking in the browser, a newly added parameter row turned out not to get focus, so typing was lost. New parameter, define, and source pattern rows are now focused right away, with a test.

## D32. Project lint job (Phase 2 task 3)
- When Lint is clicked, the API reads `smartx.yaml` and refuses (422) if the config is not valid yet (naming the first error and its line) or if `sources` matches no file. After that, **every** project file is copied to `runs/<id>/project/` (a snapshot at the moment of the click), and only then is the job queued. All files are copied, not only `sources`, so an `` `include `` from the same folder is found. The run params hold the resolved config (`top`, the list of `sources` files after globbing, `defines`, `parameters`), so the run history (task 5) can show what was run without reading files.
- Command, checked in the pinned image (Verilator 5.053):

  ```
  verilator --lint-only -Wall -Wno-EOFNEWLINE -Wno-fatal --quiet --diagnostics-sarif --diagnostics-sarif-output lint.sarif --top-module <top> -I<folder of each source> -D<n>=<v> -G<n>=<v> project/<source>...
  ```

  Unlike the `grade` job, `DECLFILENAME` stays on because in a project the file names are chosen by the user.
- Results are read from **SARIF**, not the text log. SARIF gives `endColumn` (Monaco markers cover the exact range), the rule code, the original level (`error`/`warning`), and is still written when there is a syntax error. Results without a location ("Cannot continue") and locations outside `project/` are dropped. Messages get the same Indonesian explanations as lint in exercises (`describe()` in `verilator_lint.py`). Exit code 1 (Verilator errors) counts as a result, not a failed job. The text log is still in `run.log`.
- The SARIF fixtures for tests come from the real image. Docker tests prove lint across folders with `` `include ``, and that a syntax error still gives a `succeeded` run with exit code 1.
- UI: a Lint button in the project header (pending saves are stored first), a Problems panel grouped per file with a summary "N error, M warning", and markers only for the open file. Clicking a problem opens its file and moves the cursor to its line and column (`CodeEditor.reveal`). `useProjectRun` is reused by the `sim` job in task 4. Markers do not move when the file is edited after linting; run Lint again to update them.
- Measured in the browser: 0.9 seconds from clicking Lint to Problems showing.

## D33. Project sim job (Phase 2 task 4)
- **g++ added to the toolchain image.** On checking, the image had no C++ compiler, so Verilator could not simulate anything (Verilator compiles the model to C++). `g++`, `liblz4-dev`, and `zlib1g-dev` from Ubuntu 24.04 were added; the last two are needed for FST waveforms (`fstcpp_writer.cpp` includes `lz4.h`). The packages are installed in a new layer **after** the OSS CAD Suite download, so a rebuild takes 8 seconds and the cache is not invalidated. Version when added: g++ 13.3.0. `make tool-versions` now prints it too.
- Runner: `tools/grader/sim.py` (next to `grade.py`, using the same `parse_results`) reads a JSON spec written by `prepare()` (`sim.json`: top, sources, tests, simulator, parameters, defines), then writes `result.json`. Checked against the pinned cocotb 2.1.0:
  - `Runner.test()` gives the test process the runner's `PYTHONPATH = sys.path`. So `sim.py` adds the folder of each testbench to `sys.path`, letting a testbench import helper modules next to it (`scoreboard.py`). Proven by the FIFO test.
  - Verilator writes VCD into the test folder unless given `--trace-fst`, which is added through `build_args`. The result is `dump.fst` in the work folder; Icarus writes `<top>.fst` in `sim_build`. `find_waves()` looks in both places.
  - Every source file's folder becomes an include folder. The simulator version (`iverilog -V` or `verilator --version`) is recorded in the run result.
- The question left open by D31 is answered: text parameters such as `8'hA5` are accepted as they are by Icarus (`-P`) and Verilator (`-G`). There is a Docker test.
- Compile errors are read from the build log with two patterns, Icarus `path:line: msg` (no column) and Verilator `%Error[-CODE]: path:line:col: msg`. Only files in `project/` are kept, and duplicate Icarus messages are dropped. The diagnostic model is now shared by lint and sim (`app/jobs/diagnostics.py`, `col` optional). The mapping of artifact paths to URLs moved to `app/jobs/artifacts.py` and is also used by the `grade` job.
- API: `POST /projects/{id}/runs {kind: "sim"}` uses the same snapshot flow as lint. The API refuses (422) when `tests` is empty or its files are missing. `ProjectRunRead` has `lint` and `sim`, parsed according to the run's kind.
- UI: a "Simulasi" button (primary) next to "Lint", and a result panel with Problems, Tests, Log, and Waveform tabs. Problems also shows compile errors from the simulation; the panel switches to Problems when the code does not compile. Tests are grouped per testbench module. The Log streams live during a run. Waveform uses the same `WaveView` as the exercise page: it stays mounted once opened, and the old waveform stays visible while a new run is going.
- The fixture `backend/tests/fixtures/projects/fifo` (synchronous FIFO, `DEPTH` overridden through the config, scoreboard in a separate module) is used by Docker tests to prove the Phase 2 criterion on both simulators. The run result fixtures (`sim-*`) come from the real image. pytest no longer walks `tests/fixtures`, so the cocotb testbenches there are not collected.
- Measured in the browser with the FIFO: Icarus 2.5 seconds and Verilator 12.5 seconds from click to result. Verilator is slower because it compiles C++ in a container with a CPU limit; run by hand outside a job, Verilator takes 4.7 seconds.

## D34. Project run history (Phase 2 task 5)
- `GET /api/projects/{id}/runs` returns the newest runs first (`limit` 1–200, default 50). Each row holds the time, kind, status, duration (from start to finish), simulator (for sim), and a one-line summary computed from the run result: "3/3 test lulus", "1 dari 3 test gagal", "Error kompilasi", "1 error, 2 warning", or "Tidak ada masalah". For runs that did not finish, the summary is their error message (`app/projects/history.py`).
- **Retention:** a new setting `PROJECT_RUN_HISTORY` (default 100, at least 50 per the phase criterion). Whenever a new run is created, finished runs beyond the N newest are deleted, with their run folders. `queued`/`running` runs are never deleted. Without this limit, `data/runs/` would grow forever.
- UI: a "Riwayat" tab in the result panel. The list is read again every time the tab opens. Clicking a row loads the full run (`GET /runs/{id}`) into the matching view: lint into Problems, sim into Tests (or Problems on a compile error), including its Log and Waveform. The run currently shown is marked in the list. Runs still going cannot be clicked.
- Checked in the browser: three runs (sim passing, lint, sim failing after breaking the code) show with their summaries and durations. An old passing run can be opened again, complete with Tests 4/4 and its waveform in Surfer.

## D35. Comparing two runs (Phase 2 task 6)
- `GET /api/projects/{id}/runs/compare?a=&b=` only accepts two **different, finished simulations** of the same project (otherwise 422, or 404 if a run belongs to another project). The older run is always "before", whatever order they were picked in.
- Tests are matched by `(module, name)`, so two testbenches with the same test names are not mixed up. Every test is labeled `fixed` (failed→passed), `broken` (passed→failed), `added`, `removed` (the test only exists in one run, for example after a rename or a compile error), or `same`. Results are sorted with changes first (`broken` at the top), with a count per category (`compare_tests()` in `history.py`).
- A waveform diff is deliberately not built, per the phase plan.
- UI: in the Riwayat tab, finished simulations have a checkbox (at most two; picking a third drops the oldest pick). The "Bandingkan" button shows before and after (time, simulator, summary), the Rusak/Diperbaiki/Baru/Hilang counts, the list of changed tests (`lulus → gagal`), and the number of unchanged tests.

## D36. cocotb testbench snippets (Phase 2 task 7)
- Snippets are stored as content (`content/snippets/cocotb.yaml`), not in frontend code, so they can be added without a rebuild and tested from the backend. All written from scratch: clock and reset, a valid/ready driver (`send()` returns the number of cycles waited), a valid/ready monitor, random backpressure, a scoreboard, simple coverage, and an example random test with a seed that uses all of them. API: `GET /api/snippets`.
- **Coverage without `cocotb-coverage`.** That library is not in the image, and the phase plan calls it optional. Adding it means installing a new package and checking its compatibility with cocotb 2.1. Instead, the `Coverage` snippet counts the bins named up front and fails if one never happened. The library can be added later if needed.
- **Proof that the snippets work:** a Docker test combines every snippet into one testbench for a valid/ready pipeline register (`tests/fixtures/projects/pipe_reg`). It passes on Icarus and Verilator, and fails with a scoreboard message for a register that ignores `in_ready` (data overwritten under backpressure).
- Found during verification: the first version of the example test passed on Verilator but failed on Icarus (`Cannot convert Logic('X') to int`). The driver was created after reset, so `in_valid` was still X on the first rising edge after reset. 4-state Icarus passes the X on, while 2-state Verilator silently uses 0. The example test now drives every input before reset, and the driver's docstring explains why. This is a real example for the "Icarus vs Verilator" lesson in task 8.
- UI: an open `.py` file in a project has a "Sisipkan snippet cocotb…" menu. Missing imports go after the last import (or after the module docstring, or on the first line), the body goes at the end of the file after two blank lines (PEP 8), then the cursor moves to the start of the body. The logic is in the pure function `applySnippet()` (`editor/snippets.ts`) with its own unit tests.

## D37. Short lessons (Phase 2 task 8)
- New format `content/lessons/NN-slug.md`: YAML front matter (`title`, `step` 1–6, `order`) followed by Markdown. The format is validated on read (unknown keys, empty title or body are rejected), and files are always read again from disk. API: `GET /api/lessons?step=N`.
- Four step 2 lessons, written from scratch: reference models, random tests with a seed (including a note that cocotb seeds the global `random` generator differently on every run, as the log says), reading waveforms in Surfer, and Icarus vs Verilator.
- The Icarus vs Verilator content was **measured first** in the pinned image with small designs. Results: unreset registers and inputs that are never driven are `X` on Icarus and `0` on Verilator. `if (sel)` with `sel = X` takes the `else` branch on Icarus (X-optimism, the X is hidden). An X sent by cocotb to Verilator reads as `0`. The FIFO simulation times (2.5 and 12.5 seconds) come from the task 4 measurements. Claims that were not measured are written in general terms.
- UI: a "Materi" button in the project header opens a sidebar next to the editor (lesson list; click to read; a "← Daftar materi" button to go back). Lessons are rendered with the same `Markdown` component as the exercise page.

## D38. FPGA board profiles (Phase 3 task 1)
- The owner has no board yet (confirmed 2026-10-25). The first board stays the Tang Nano 9K, per D08. The flow up to the bitstream is tested in the pinned image; the pins in the constraint template come from the board's pinout and are **not tried on a physical board yet**. The "blinks on the board" criterion can only be ticked once the owner has tried it.
- Following "finish one board completely", iCE40 moved to the last task of this phase. Its format has been checked to fit: an iCEBreaker blinky (`nextpnr-ice40 --up5k --package sg48 --pcf ... --asc`, then `icepack`) builds in the same image.
- Tool arguments are data in the profile, with the placeholders `{constraints}`, `{pnr}`, `{bitstream}`. The job adds `--json`, `--freq`, `--report`, and `-l` itself. Unknown placeholders, or required ones left unused, are rejected when the profile is read. The constraint template must pin the profile's clock port to its clock pin.
- The device name in the old example (`GW1NR-LV9QN88PC6/I6`) is rejected by nextpnr 0.11.1-79 ("Speed grade 'C6/I6' not found"). The right one is `GW1NR-LV9QN88PC6/I5` with `--vopt family=GW1N-9C`. The CST file is passed to nextpnr through `--vopt cst=`, not to `gowin_pack`.
- Measured nextpnr behavior: CST ports that do not exist in the design are ignored without a warning (the template may hold every board pin), design ports without a constraint fail with `Unconstrained IO`, and a wrong pin fails with `Pin 999 not found`.
- The Docker test `test_board_profile_builds_blinky` builds a blinky for every profile from nothing but the profile and its template. Every profile must have `backend/tests/fixtures/boards/<id>/blinky.v`. Tang Nano 9K blinky: synthesis 0.9 seconds, PnR 0.5 seconds, pack 3.2 seconds (measured per stage in task 2), Fmax 159 MHz against a 27 MHz target.
- API: `GET /api/boards` sends the name, device, clock, format, and constraint template text. Tool arguments are not sent, because they are the job's business.

## D39. fpga job (Phase 3 task 2)
- A new `fpga:` section in `smartx.yaml` (`board`, `constraints`, optional `freq_mhz` defaulting to the board clock). The build uses the same `top`, `sources`, `parameters`, and `defines` as the simulation, so one design does not need two configurations. The simulation form carries this section along unchanged, so saving the form never deletes it.
- The backend builds one command per stage from the board profile and writes them to `fpga.json`. `tools/fpga/build.py` in the image only runs them in order in `build/`, records the time and exit code of each stage, and stops at the first stage that fails (later stages are `skipped`). The run log uses the markers `==> Synthesize` / `<== Synthesize: ok (0.86 s)`. Knowledge about boards stays in one place (profile + backend).
- Synthesis through a `synth.ys` script: `read_verilog` (with `-sv` for `.sv`) with `-I` for every source folder and `-D` from the defines, then `chparam -set` for parameters, then `synth_*`, then `stat` (text and JSON). Parameters and defines are written into the script, so their values must be one token (no spaces, quotes, `;`, `#`). Tested in the image: `chparam` accepts sized literals such as `8'hFF`.
- Yosys and nextpnr run with `-q`: the run log only holds warnings and errors, while the full logs are in `build/yosys.log` and `build/nextpnr.log` (blinky: 55 kB and 10 kB). Source paths are written as absolute paths (`/work/project/...`), so a Yosys error `/work/project/src/a.v:7: ERROR: ...` becomes a file-and-line diagnostic through the same parser as Icarus.
- nextpnr runs with `--timing-allow-fail`. Without it, a design that misses timing stops with exit 1 (the report is still written) and gets no bitstream. With it, the bitstream is still produced and the report (task 3) marks it red. Reason: the user can still try it on the board and learn from the report.
- Apicula's Numpy/Msgspec warnings on every `gowin_pack` start are silenced with `PYTHONWARNINGS=ignore` in the job container.
- Result (`FpgaResult`): status, stages (status, seconds, log URL), the first error of the failed stage (from that stage's log, or the run log for pack), Yosys diagnostics, Yosys and nextpnr versions, and URLs for the bitstream, `report.json`, and `stat.txt`. History summary: "Bitstream jadi" or "Gagal di <stage>".
- The job uses the light class with the same time limit (120 seconds). Blinky needs about 5 seconds. The limit will be revisited once the Phase 4 designs (RV32I) exist.

## D40. FPGA report parsers (Phase 3 task 3)
- Module `backend/app/reports/`: `yosys.py` (synthesis warnings from the log and netlist) and `nextpnr.py` (utilization, Fmax per clock, critical paths from `report.json`). The fpga job's `collect()` attaches the results to `FpgaResult`: `warnings`, `utilization`, `clocks`, `timing_met`, and `critical_paths`. Parts whose stage has not run stay empty.
- Every Yosys warning pattern was **measured first** in the pinned image (Yosys 0.70+219) with a small design, and the real (trimmed) logs are kept in `backend/tests/fixtures/reports/`:
  - Latch: `Latch inferred for signal ... from process ...file.v:LINE$proc`. The file and line come from the process name.
  - Multi-driven: `multiple conflicting drivers for top.\x:`, without a line. Yosys also names nets it created itself (for example `a_IBUF_I_O_DFF_D_Q`), so only names that appear in the user's sources are kept, and their line comes from the declaration.
  - Undriven: `Wire top.\x is used but has no driver` (appears twice, merged).
  - Implicit identifier: `file.v:LINE: Warning: Identifier ... is implicitly declared`.
  - A memory that could not be mapped to RAM: `using FF mapping for memory top.mem` (memory_libmap). A RAM that maps successfully reads `mapping memory top.mem via $__GOWIN_SP_`.
  - Other warnings about project files are shown as they are. Warnings about Yosys's own library (`Lexer warning ... abc9_map.v`) and `ABC: Warning: The network is combinational`, which appear on every build, are dropped.
- Yosys **never** reports unused signals. Unused top inputs are detected from `netlist.json`: input bits that no cell reads, looking through Gowin IBUFs. Inputs whose names contain `unused` are skipped, as in the lint rules. Unused internal signals are removed silently by Yosys; the full list still comes from Lint (Verilator `UNUSEDSIGNAL`).
- Warning messages are in Indonesian and say how to fix the problem (latch: a default value, `else`, `default`).
- Numbers come from `report.json`, not the log. The Fmax in the report equals the **last** "Max frequency" line in the log (the first one is an estimate before routing). The "Device utilisation" table in the log is printed before placement and can differ from the final numbers (blinky: 50 vs 43 LUT4). The tests `test_fmax_matches_the_raw_log` and `test_critical_path_matches_the_raw_log` compare the parser output with nextpnr's raw log (Fmax, target, PASS/FAIL, logic/routing ns).
- User-facing clock names come from the nextpnr net (`clk_IBUF_I_O` becomes `clk`, `clk$SB_IO_IN_$glb_clk` becomes `clk`). Critical path steps point at a project file and line when the net comes from the user's code.
- Utilization rows follow `resources` in the board profile; several nextpnr resource types can be summed into one row.
- The fpga run fixtures are made from real containers by `backend/tests/fixtures/make_fpga_fixtures.py` (Yosys log and netlist trimmed, bitstream replaced). Run it again after pinning a new OSS CAD Suite.

## D41. FPGA page in the workspace (Phase 3 task 4)
- The project page gets an **FPGA** button (a settings side panel) and **Build** (runs the job), next to Lint and Simulasi. Results show in the **FPGA** tab of the result panel. Not a separate page, because constraints and code are edited in the same editor and synthesis results point at code lines.
- The settings panel writes the `fpga:` section of `smartx.yaml` through `PUT /config`. The rest of the file is read again first and pending changes are saved first, so no edits are lost. If `smartx.yaml` is open, its editor is reloaded. Like the simulation form, this save rewrites the file, so comments are lost.
- Picking a board immediately creates `constraints/<board>.<cst|pcf>` from the board template (if it does not exist), saves the configuration, and opens the constraint file in the editor. So the "constraint editor" is the ordinary code editor (plaintext). The target clock is saved on Enter or when the field loses focus; empty means the board clock.
- A build without an `fpga` section gets a 422 from the API, and the settings panel opens by itself once.
- The three stages are visible separately from the moment the build runs: the FPGA tab reads the `==>`/`<==` markers in the streamed log (`liveStages`), then uses the stage statuses from the result once finished.
- Report: stages with their times, the first error of the failed stage, synthesis warnings (with links to file and line), a resource table with percentage bars, an Fmax table per clock (red row and "Gagal" when the target is missed), critical paths (open by default when timing fails), links to the per-stage logs and `report.json`, and an **Unduh bitstream** button named `<top>-<board>.fs`. Backticked text in messages is rendered as code.
- Synthesis warnings that have a file and line also go into Problems and become Monaco markers (code `Yosys`), like lint results.
- History summary for a build that missed timing: "Bitstream jadi, timing tidak tercapai".
- Found while checking in the browser: with a 28rem panel, the editor (min 24rem) covered the result panel on a 900 px screen. The FPGA tab now uses 20rem and its content scrolls.
- Checked in the browser with real Docker: a blinky project from the empty template, then Build without a board (the panel opens), then picking the Tang Nano 9K (constraints created and opened), then Build to a bitstream (5.5 seconds). The numbers in the UI (LUT 43/8640, FF 31/6480, IO 8/276, Fmax 159.08 MHz against a 27 MHz target) match `report.json` and the last "Max frequency" line in that run's `nextpnr.log`. A latch design with a 300 MHz target showed the latch warning on line 10 and the unused input `btn` on line 3 (squiggles in the editor), timing in red at 244.86 MHz against 300 MHz, and the critical path with links to the sources.

## D42. Flashing helper smartx-flash (Phase 3 task 5)
- `tools/flash/smartx-flash` is written in Python with the standard library only (3.8+), so it runs on Linux, macOS, and Windows without `pip install`. On Windows it is called as `python tools/flash/smartx-flash`.
- Bitstream sources: `--project ID` (that project's newest FPGA build with a bitstream; running, failed, or other kinds of runs are skipped), `--run ID`, or `--file PATH --board ID`. The openFPGALoader command comes from the board profile through a new `flash_command` field in `GET /api/boards`, so board knowledge stays in one place. As a result `--file` also needs the backend; without it, the README shows the openFPGALoader arguments per board.
- By default the bitstream is loaded into SRAM (openFPGALoader's default, `-m`), which is fast and lost when the board is unplugged. `--flash` adds `-f` to make it permanent. `--dry-run` only shows the command, and arguments after `--` are passed on to openFPGALoader. Builds that missed timing get a warning but are still loaded.
- Flags checked with `openFPGALoader --help` v1.2.0 in the image: `-b/--board`, `-f/--write-flash`, `-m/--write-sram` (default), and the `tangnano9k` board is in `--list-boards`. With no board attached, the command from the Tang Nano 9K profile stops at the USB stage (`unable to open ftdi device: -3 (device not found)`, exit 1), meaning its arguments are accepted.
- The installation steps and udev rules in the README come from openFPGALoader's official guide (Debian/Ubuntu, Arch, Fedora, Homebrew, MSYS2 UCRT64; `99-openfpgaloader.rules` with the `plugdev` group, or `70-...` with `dialout`). That guide does not cover Windows drivers, so the Zadig/WinUSB advice is marked untested.
- The FPGA tab shows the `smartx-flash --run <id>` command for the run being viewed.
- The test `backend/tests/test_flash_tool.py` runs the script against a stub backend over real HTTP: picking the newest build, the downloaded bitstream being byte-identical, `--flash`/extra arguments, `--file`, `--dry-run`, and error messages. Flashing a physical board is **not tested yet** because the owner has no board.

## D43. Step 3 lessons (Phase 3 task 6)
- Five lessons written from scratch: code that does not synthesize, the 2-flop synchronizer, button debounce, reading the timing report, and simulation passes but the FPGA fails.
- Tool claims were **measured first** in the pinned image (Yosys 0.70 `synth_gowin`, nextpnr 0.11.1-79, Icarus 14, Verilator 5.053):
  - Rejected by Yosys: dual-edge always blocks (`Multiple edge sensitive events found for this signal!`) and `while` loops bounded by data (`While loops are only allowed in constant functions!`).
  - Ignored without a warning by both Yosys and Verilator lint `-Wall`: `assign #5` (becomes `y = a`), `initial q = 0; #10 q = 1;` (becomes a **constant 1**), `$display`, and incomplete sensitivity lists. For `always @(a) y = a & b`, Icarus gives `y = 0` after `a = 1, b = 1`, while Yosys builds a LUT2 `a & b`.
  - A 16-bit divider becomes 376 ALUs and 128 LUTs. A 16×16 multiplier becomes one `MULT18X18`. Register initial values (`initial q = 9`) are kept by Yosys (DFFS for the 1 bits).
  - Verilator lint gives `PROCASSINIT` for registers with an initial value that are also written in an always block. The lesson explains this is fine on an FPGA but not on an ASIC.
  - A button design with `sync2` + `debounce` (10 ms = 270,000 cycles at 27 MHz) passes PnR on the Tang Nano 9K with an Fmax of 169 MHz. The timing numbers in the timing lesson are blinky's from tasks 3 and 4 (159.08 MHz, 6.29 ns = 3.70 + 2.59, first estimate 209.42 MHz).
  - Things not measured (button bounce lasting a few milliseconds, register values without an initial value on the chip, LED and button polarity from a template not yet tried on a board) are written in general terms, or their source is named.
- The Docker test `test_lesson_code_builds_for_the_board` takes the ```verilog blocks from the synchronizer and debounce lessons and builds them with the fpga job for the Tang Nano 9K. The result must be ok, with timing met and no synthesis warnings, so the code in the lessons cannot break silently.
- The Materi sidebar on the project page now shows steps 2 and 3, grouped per step with step titles. The panel fetches every lesson and filters the steps on the client.
- Found while measuring: for hierarchical designs, nextpnr names the clock after a hierarchical net (`u_db.clk`, not `clk_IBUF_I_O`), so the clock name in the report does not always match the top port. Noted for the example projects in task 7.

## D44. English documentation, public repository
- The owner decided (2026-10-26) to publish the repository on GitHub as a public repository with the MIT license, and to have all documentation in English.
- Documentation means `README.md`, `CLAUDE.md`, everything in `docs/`, the tool READMEs (`tools/flash/README.md`, `docker/asic/README.md`), and the Claude commands in `.claude/commands/`. The phase files were renamed to English (`phase-0-foundation.md`, `phase-2-simulation.md`, `phase-4-projects.md`). Earlier entries of this log were translated without changing their content.
- What stays in Indonesian, because it is the product for an Indonesian-speaking learner: the UI, the learning material in `content/` (exercise statements, hints, lessons, template READMEs, test messages), user-facing error messages, and the help text of the command-line tools. This supersedes the language rule in the earlier SPEC/CLAUDE.md, which had the documents in Indonesian.
- Commit history is published as it is; it contains the author names and email addresses of the commits.
