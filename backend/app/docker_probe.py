"""Check whether the Docker daemon is reachable."""

import docker
from pydantic import BaseModel


class DockerStatus(BaseModel):
    available: bool
    server_version: str | None = None
    error: str | None = None


def probe_docker(timeout_s: int = 3) -> DockerStatus:
    """Ping the daemon. Never raises: health checks must answer even without Docker."""
    try:
        client = docker.from_env(timeout=timeout_s)
        try:
            version = client.version()
        finally:
            client.close()
    except Exception as exc:  # docker raises DockerException, OSError, pywintypes.error, ...
        return DockerStatus(available=False, error=f"Docker tidak bisa dihubungi: {exc}")
    return DockerStatus(available=True, server_version=version.get("Version"))
