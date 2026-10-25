"""cocotb testbench snippets offered in the project editor (content/snippets/*.yaml)."""

from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SnippetId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]


class Snippet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: SnippetId
    title: str = Field(min_length=1)
    description: str = ""
    language: str = "python"
    # Lines the body needs at the top of the file ("import cocotb", "from x import y").
    imports: list[str] = []
    body: str = Field(min_length=1)


class SnippetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snippets: list[Snippet]


def load_snippets(snippets_dir: Path) -> list[Snippet]:
    """All snippets, file by file in name order, keeping each file's order."""
    found: list[Snippet] = []
    if snippets_dir.is_dir():
        for path in sorted(snippets_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            found += SnippetFile.model_validate(data).snippets
    return found


def assemble(snippets: list[Snippet]) -> str:
    """One Python module from several snippets: their imports once, then the bodies."""
    imports: list[str] = []
    for snippet in snippets:
        imports += [line for line in snippet.imports if line not in imports]
    return "\n".join(imports) + "\n\n\n" + "\n\n".join(s.body for s in snippets)
