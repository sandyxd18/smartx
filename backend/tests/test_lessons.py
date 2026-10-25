from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import REPO_ROOT
from app.content.lessons import LessonError, load_lessons


def write(folder: Path, name: str, text: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text, encoding="utf-8")


def test_reads_front_matter_and_body(tmp_path: Path) -> None:
    write(tmp_path, "02-b.md", "---\ntitle: Kedua\nstep: 2\norder: 20\n---\n\n# Kedua\n\nIsi.\n")
    write(tmp_path, "02-a.md", "---\ntitle: Pertama\nstep: 2\norder: 10\n---\nIsi A.\n")
    write(tmp_path, "03-c.md", "---\ntitle: Langkah 3\nstep: 3\n---\nIsi C.\n")
    write(tmp_path, "catatan.txt", "bukan materi")

    lessons = load_lessons(tmp_path)

    assert [(x.id, x.title, x.step) for x in lessons] == [
        ("02-a", "Pertama", 2),
        ("02-b", "Kedua", 2),
        ("03-c", "Langkah 3", 3),
    ]
    assert lessons[1].body == "# Kedua\n\nIsi.\n"


@pytest.mark.parametrize(
    "text",
    [
        "# Tanpa front matter\n",
        "---\nstep: 2\n---\nIsi\n",  # no title
        "---\ntitle: X\nstep: 2\nwarna: biru\n---\nIsi\n",  # unknown key
        "---\ntitle: X\nstep: 2\n---\n\n",  # empty body
    ],
)
def test_invalid_lessons_are_reported(tmp_path: Path, text: str) -> None:
    write(tmp_path, "02-x.md", text)
    with pytest.raises(LessonError, match="02-x.md"):
        load_lessons(tmp_path)


def test_content_lessons_cover_phase_2() -> None:
    lessons = [x for x in load_lessons(REPO_ROOT / "content" / "lessons") if x.step == 2]

    ids = [x.id for x in lessons]
    assert ids == [
        "02-model-referensi",
        "02-test-acak-seed",
        "02-membaca-waveform",
        "02-icarus-vs-verilator",
    ]
    icarus_vs_verilator = lessons[-1].body
    # Phase 2 criterion: the material explains X-propagation differences.
    assert "X" in icarus_vs_verilator and "2-state" in icarus_vs_verilator


def test_api_filters_by_step(client: TestClient) -> None:
    body = client.get("/api/lessons?step=2").json()

    assert [x["id"] for x in body][0] == "02-model-referensi"
    assert all(x["step"] == 2 for x in body)
    assert body[0]["body"].startswith("# Menulis model referensi")
    assert client.get("/api/lessons?step=6").json() == []  # no lessons for step 6 yet
    assert client.get("/api/lessons?step=9").status_code == 422  # steps are 1..6


def test_content_lessons_cover_phase_3() -> None:
    lessons = {x.id: x for x in load_lessons(REPO_ROOT / "content" / "lessons") if x.step == 3}

    assert list(lessons) == [
        "03-tidak-bisa-disintesis",
        "03-synchronizer",
        "03-debounce",
        "03-laporan-timing",
        "03-simulasi-lulus-fpga-gagal",
    ]
    # The topics the phase plan asks for.
    assert "always @*" in lessons["03-tidak-bisa-disintesis"].body
    assert "metastabil" in lessons["03-synchronizer"].body
    assert "270.000 siklus" in lessons["03-debounce"].body
    assert "Jalur kritis" in lessons["03-laporan-timing"].body
    assert "Unconstrained IO" in lessons["03-simulasi-lulus-fpga-gagal"].body
