# Phase 6: Tapeout export (step 6)

Goal: from a design that passed Phase 5, generate a repository ready for a Tiny Tapeout shuttle, and prove it with a local hardening run using the official TT tools.

## Before starting

Check which shuttle is open on tinytapeout.com and its repository template (SKY, IHP, or GF). Every shuttle uses its own `tt-support-tools` branch and may change the pin rules, tile sizes, or flow version. Store this as a profile in `content/tapeout/shuttles/<id>.yaml` (repo template, tools branch, PDK flag such as `--ihp`, available tile sizes). Do not hard-code it.

## Tasks

1. **`tt_um_*` wrapper**: a wizard that maps the design's ports to the standard TT interface (`ui_in[7:0]`, `uo_out[7:0]`, `uio_in/out/oe[7:0]`, `clk`, `rst_n`, `ena`). Generate the Verilog wrapper module, and tie unused outputs to 0.
2. **Repository generator**: from the shuttle template, fill in `info.yaml` (title, author, description, tile count, clock frequency, pinout), `src/`, `test/` (cocotb testbench for the wrapper), `docs/info.md`. The result can be downloaded as a `.zip` or `git init`-ed with a first commit.
3. **Checks before hardening**: the top name starts with `tt_um_`, every pin is documented in `info.yaml`, the wrapper's cocotb tests pass, no latches, clean lint.
4. **`tt_harden` job** (heavy): inside the generated repository, clone `tt-support-tools` (branch from the profile) into `tt/`, then run `tt_tool.py --create-user-config` and `tt_tool.py --harden` (with the shuttle's PDK flag), then `--print-warnings`. Note: `tt_tool.py --harden` itself uses a container, so this job needs a special approach (Docker-in-Docker, or running this step through a helper on the host). Decide and record it in `DECISIONS.md`.
5. **Gate-level test**: run the cocotb tests against the hardened netlist, as TT requires.
6. **Render**: `tt_tool.py --create-png` for an image of the tile GDS.
7. **Submission checklist** in the UI: link to the TT submission page, steps to push to GitHub, and checking that the GitHub Actions of the generated repository (gds, docs, test) are green.

## Done criteria

- [ ] `uart-tx` (or another small design) becomes a TT repository, local hardening succeeds, and the warnings are read and explained.
- [ ] The gate-level test passes.
- [ ] The repository pushed to GitHub passes every GitHub Action of the TT template.
- [ ] The "v1 done" definition in `SPEC.md` is met.
