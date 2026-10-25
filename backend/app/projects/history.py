"""A project's run history: summaries, comparing two runs, pruning old runs."""

from typing import Any

from sqlmodel import Session, col, select

from app.models import Run, RunStatus

ACTIVE = (RunStatus.queued, RunStatus.running)


def summarize(run: Run) -> str | None:
    """What a finished run found, in a few words; the error of a run that did not finish."""
    if run.status in ACTIVE:
        return None
    if run.status != RunStatus.succeeded:
        return run.error
    result = run.result or {}
    if run.kind == "lint":
        errors, warnings = result.get("errors", 0), result.get("warnings", 0)
        return f"{errors} error, {warnings} warning" if errors or warnings else "Tidak ada masalah"
    if run.kind == "sim":
        tests = result.get("tests") or []
        failed = sum(not t.get("passed") for t in tests)
        match result.get("status"):
            case "pass":
                return f"{len(tests)}/{len(tests)} test lulus"
            case "fail":
                return f"{failed} dari {len(tests)} test gagal"
            case "compile_error":
                return "Error kompilasi"
            case _:
                return "Tidak ada hasil test"
    if run.kind == "fpga":
        if result.get("status") == "ok":
            if result.get("timing_met") is False:
                return "Bitstream jadi, timing tidak tercapai"
            return "Bitstream jadi"
        failed = next((s for s in result.get("stages") or [] if s.get("status") == "failed"), None)
        return f"Gagal di {failed['title']}" if failed else "Gagal"
    return None


def prune_runs(session: Session, project_id: int, keep: int) -> list[str]:
    """Delete the project's finished runs beyond the `keep` newest; return their ids.

    Queued and running runs are never deleted. The caller commits and removes the
    run folders.
    """
    runs = session.exec(
        select(Run)
        .where(Run.project_id == project_id)
        .order_by(col(Run.created_at).desc(), col(Run.id).desc())
    ).all()
    doomed = [r for r in runs[keep:] if r.status not in ACTIVE]
    for run in doomed:
        session.delete(run)
    return [r.id for r in doomed]


CHANGE_ORDER = ("broken", "fixed", "added", "removed", "same")


def _test_states(result: dict[str, Any] | None) -> dict[tuple[str, str], str]:
    return {
        (t.get("module", ""), t["name"]): "passed" if t.get("passed") else "failed"
        for t in (result or {}).get("tests") or []
    }


def compare_tests(
    before: dict[str, Any] | None, after: dict[str, Any] | None
) -> list[dict[str, str]]:
    """Every test of either run, with its state in each and how it changed.

    Tests are matched by (module, name); a test missing from one run (renamed, or a
    compile error there) is "added" or "removed". Changes come first.
    """
    old, new = _test_states(before), _test_states(after)
    rows = []
    for key in sorted(old.keys() | new.keys()):
        was, now = old.get(key, "missing"), new.get(key, "missing")
        if was == "missing":
            change = "added"
        elif now == "missing":
            change = "removed"
        elif was == now:
            change = "same"
        else:
            change = "fixed" if now == "passed" else "broken"
        rows.append(
            {"module": key[0], "name": key[1], "before": was, "after": now, "change": change}
        )
    return sorted(rows, key=lambda r: CHANGE_ORDER.index(r["change"]))
