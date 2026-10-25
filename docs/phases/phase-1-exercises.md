# Phase 1: Exercises (step 1)

Goal: a personal replacement for HDLBits. Write Verilog in the browser, click Run, see the test results and the waveform.

## Tasks

1. [x] **Content loader**: `backend/app/content/` reads `content/exercises/*/exercise.yaml`, validates it with a Pydantic model, and caches it in memory (reloading when files change in dev mode).
2. [x] **`grade` job**: calls `tools/grader/grade.py` inside the toolchain image. The exercise is mounted read-only; the user's code is written to the run folder. `collect()` reads `result.json`. The waveform path in the JSON is mapped to an artifact URL.
3. [x] **Exercises API** as in ARCHITECTURE: list + progress, detail, run, next hint, solution (403 until passed or `attempts >= SOLUTION_UNLOCK_ATTEMPTS`, default 5).
4. [x] **Exercise list page**: grouped by topic, level badge, status (not started/failed/passed), filters.
5. [x] **Exercise page**: split view. Left: the statement (Markdown + tables). Right: Monaco editor (Verilog via Monarch), Run button (`Ctrl+Enter`), reset to starter. Bottom: a result panel with **Tests** (test list, green/red, messages), **Log**, and **Waveform** tabs.
6. [x] **Autosave** of the code per exercise (1-second debounce) to `ExerciseProgress.last_code`.
7. [x] **WaveView**: a Surfer iframe that loads the `.fst` from its artifact URL. Add a download button as a fallback.
8. [x] **Write 19 more exercises** following the curriculum table in `CONTENT-FORMAT.md` (20 in total). Every exercise must pass `make check-content`. For "common pitfall" exercises, the starter holds wrong code and the user is asked to fix it.
9. [x] **Verilator lint on Run** (optional but nice): before simulating, run `verilator --lint-only -Wall` and show warnings (for example latch, width mismatch) as annotations in Monaco.

## Done criteria

- [x] 20 exercises in the list, all passing `make check-content`.
- [x] Solving `counter-4bit` from the starter to passing entirely through the UI, including viewing the waveform.
- [x] Compile errors show the line and the message from Icarus, and that line is marked in the editor.
- [x] Time from clicking Run to the result < 5 seconds for a small exercise (measure it and record it in the progress log).
- [x] `solution.v` cannot be fetched through the API before the condition is met (with a test).
- [x] Refreshing the page does not lose the code being written.
