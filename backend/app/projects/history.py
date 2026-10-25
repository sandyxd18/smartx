"""A project's run history: one-line summaries and pruning of old runs."""

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
