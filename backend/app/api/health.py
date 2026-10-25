from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import __version__
from app.docker_probe import DockerStatus, probe_docker

router = APIRouter(tags=["health"])

DockerProbe = Callable[[], DockerStatus]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    docker: DockerStatus


def get_docker_probe() -> DockerProbe:
    return probe_docker


@router.get("/health")
def health(probe: Annotated[DockerProbe, Depends(get_docker_probe)]) -> HealthResponse:
    # Sync endpoint: FastAPI runs it in a thread pool, so the blocking ping is fine.
    return HealthResponse(version=__version__, docker=probe())
