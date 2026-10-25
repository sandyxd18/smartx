import ast

from fastapi.testclient import TestClient

from app.config import REPO_ROOT
from app.projects.snippets import Snippet, assemble, load_snippets

SNIPPETS = REPO_ROOT / "content" / "snippets"


def test_content_snippets_are_valid_and_unique() -> None:
    snippets = load_snippets(SNIPPETS)

    ids = [s.id for s in snippets]
    assert len(ids) == len(set(ids))
    assert {"clock-reset", "valid-ready-driver", "scoreboard", "random-test"} <= set(ids)
    for snippet in snippets:
        # Each snippet compiles on its own with the imports it declares.
        ast.parse("\n".join(snippet.imports) + "\n" + snippet.body, filename=snippet.id)
        for line in snippet.imports:
            assert line.startswith(("import ", "from ")), (snippet.id, line)


def test_assemble_lists_each_import_once() -> None:
    a = Snippet(id="a", title="A", imports=["import cocotb", "import random"], body="x = 1\n")
    b = Snippet(id="b", title="B", imports=["import cocotb"], body="y = 2\n")

    text = assemble([a, b])

    # Two blank lines between top-level blocks, as PEP 8 asks.
    assert text == "import cocotb\nimport random\n\n\nx = 1\n\n\ny = 2\n"


def test_all_snippets_assemble_into_one_module() -> None:
    ast.parse(assemble(load_snippets(SNIPPETS)))


def test_api_lists_snippets(client: TestClient) -> None:
    body = client.get("/api/snippets").json()

    ids = [s["id"] for s in body]
    assert ids == [s.id for s in load_snippets(SNIPPETS)]
    first = body[0]
    assert set(first) == {"id", "title", "description", "language", "imports", "body"}
    assert first["language"] == "python"
