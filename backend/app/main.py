"""FastAPI application factory. Run with: uvicorn --factory app.main:create_app"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import exercises, health, projects, runs
from app.config import Settings, get_settings
from app.content import ExerciseCatalog
from app.db import init_db, make_engine
from app.jobs.context import JobContext
from app.jobs.docker_runner import DockerRunner
from app.jobs.events import EventHub
from app.jobs.queue import JobQueue
from app.jobs.recovery import recover_interrupted_runs
from app.jobs.runner import JobRunner
from app.progress import record_run_result

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, runner: JobRunner | None = None) -> FastAPI:
    settings = settings or get_settings()
    runner = runner or DockerRunner(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        engine = make_engine(f"sqlite:///{settings.db_path.as_posix()}")
        init_db(engine)

        recovered = recover_interrupted_runs(engine)
        if recovered:
            log.warning("marked %d interrupted run(s) as failed", recovered)
        try:
            removed = await runner.remove_orphans()
            if removed:
                log.warning("removed %d leftover job container(s)", removed)
        except Exception as exc:  # Docker may be down; the app still has to start.
            log.warning("could not clean up job containers: %s", exc)

        catalog = ExerciseCatalog(
            settings.content_dir / "exercises", auto_reload=settings.content_auto_reload
        )
        log.info("loaded %d exercise(s)", len(catalog.all()))

        events = EventHub()
        queue = JobQueue(
            runner=runner,
            settings=settings,
            engine=engine,
            events=events,
            context=JobContext(settings=settings, catalog=catalog),
            on_finished=lambda run_id: record_run_result(engine, run_id),
        )
        app.state.catalog = catalog
        app.state.engine = engine
        app.state.events = events
        app.state.queue = queue
        try:
            yield
        finally:
            await queue.shutdown()
            engine.dispose()

    app = FastAPI(title="SmartX", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.include_router(health.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")
    app.include_router(exercises.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")
    return app
