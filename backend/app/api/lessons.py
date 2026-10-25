from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.runs import get_app_settings
from app.config import Settings
from app.content.lessons import load_lessons

router = APIRouter(prefix="/lessons", tags=["lessons"])

SettingsDep = Annotated[Settings, Depends(get_app_settings)]


class LessonRead(BaseModel):
    id: str
    title: str
    step: int
    order: int
    body: str  # Markdown


@router.get("")
def list_lessons(
    settings: SettingsDep, step: Annotated[int | None, Query(ge=1, le=6)] = None
) -> list[LessonRead]:
    """Lessons in reading order, optionally only those of one learning step."""
    return [
        LessonRead(id=x.id, title=x.title, step=x.step, order=x.order, body=x.body)
        for x in load_lessons(settings.content_dir / "lessons")
        if step is None or x.step == step
    ]
