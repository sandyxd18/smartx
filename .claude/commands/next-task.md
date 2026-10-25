---
description: Take the next task of the active phase and finish it
---

1. Read `docs/ROADMAP.md` and find the active phase (the first one not marked `[x]`). Mark it `[~]` if it is still `[ ]`.
2. Open that phase's file in `docs/phases/`. Take the first unfinished task.
3. Before writing code, summarize in 3–5 lines what will be built, which files are touched, and how it will be tested. If the task depends on the CLI or file format of an EDA tool, check `--help` or the documentation of the pinned version first.
4. Implement it with tests. Run the relevant checks (`make check` once available).
5. If everything is green: tick the task, commit, and report briefly what was done and what the owner should check by hand (for example the UI look, a physical board).
6. If blocked (a tool behaves differently from its documentation, a decision belongs to the owner): stop, explain the problem, and propose options.

$ARGUMENTS
