"""Schema of content files. See docs/CONTENT-FORMAT.md."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# A bare file name inside the exercise folder: no separators, no '..', no hidden files.
FileName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")]
ExerciseId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]


class ExerciseFiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starter: FileName
    solution: FileName
    test: FileName
    statement: FileName


class ExerciseMeta(BaseModel):
    """exercise.yaml"""

    model_config = ConfigDict(extra="forbid")

    id: ExerciseId
    title: Annotated[str, StringConstraints(min_length=1)]
    step: int = Field(ge=1, le=6)
    level: int = Field(ge=1, le=3)
    topics: list[str] = Field(min_length=1)
    toplevel: Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_$]*$")]
    language: Literal["verilog", "systemverilog"] = "verilog"
    files: ExerciseFiles
    timeout_s: int = Field(default=30, ge=1, le=600)
    hints: list[str] = []
    order: int | None = None
    requires: list[ExerciseId] = []
