# ASIC image (Phase 5)

The heavy image for LibreLane + PDKs is not built in this repository. Default: `hpretl/iic-osic-tools` with the tag pinned in `.env` (`ASIC_IMAGE`).

Before Phase 5 starts:
1. Pick the latest stable tag and pin it in `.env`.
2. Check the LibreLane version and the PDK location inside the image, and record them in `docs/notes/asic-manual-run.md`.
3. If that LibreLane version does not match what the target Tiny Tapeout shuttle needs, use LibreLane's official installation method and update `DECISIONS.md` (D07).
