from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.runs import get_app_settings
from app.config import Settings
from app.content.boards import load_boards

router = APIRouter(prefix="/boards", tags=["boards"])

SettingsDep = Annotated[Settings, Depends(get_app_settings)]


class BoardRead(BaseModel):
    id: str
    name: str
    family: str
    device: str
    clock_port: str
    clock_pin: str
    clock_mhz: float
    constraints_format: str  # cst | pcf
    constraints_template: str  # starting point for a project's constraint file


@router.get("")
def list_boards(settings: SettingsDep) -> list[BoardRead]:
    """FPGA boards that can be targeted, ordered by id."""
    return [
        BoardRead(
            id=b.id,
            name=b.name,
            family=b.family,
            device=b.device,
            clock_port=b.clock.port,
            clock_pin=b.clock.pin,
            clock_mhz=b.clock.freq_mhz,
            constraints_format=b.constraints.format,
            constraints_template=p.constraints_template,
        )
        for p in load_boards(settings.content_dir / "boards")
        for b in [p.board]
    ]
