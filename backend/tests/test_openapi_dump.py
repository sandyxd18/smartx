import json

import pytest

from app import openapi_dump


def test_dump_prints_openapi_schema(capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    openapi_dump.main()
    schema = json.loads(capsysbinary.readouterr().out.decode("utf-8"))
    assert schema["info"]["title"] == "SmartX"
    assert {"/api/health", "/api/runs", "/api/runs/{run_id}/events"} <= set(schema["paths"])
    assert "RunRead" in schema["components"]["schemas"]
