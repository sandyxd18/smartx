---
description: Check whether the active phase meets all of its done criteria
---

1. Find the active phase in `docs/ROADMAP.md` (or use the phase named in the arguments).
2. For every item under "Done criteria" in that phase's file, collect evidence: run the related command or test and quote the result. Items only a person can check (UI, hardware) are marked "needs a manual check", with the steps to check them.
3. Run `make check`.
4. Report a table: criterion, status (proven / failed / needs a manual check), evidence.
5. Do not mark the phase `[x]` in the ROADMAP unless every criterion is proven or confirmed by the owner.

$ARGUMENTS
