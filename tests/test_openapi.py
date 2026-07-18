import json
from pathlib import Path
from typing import Any

OPENAPI_PATH = Path(__file__).resolve().parents[1] / "openapi/mettledeck-v1.json"


def load_openapi() -> dict[str, Any]:
    return dict(json.loads(OPENAPI_PATH.read_text(encoding="utf-8")))


def test_openapi_lists_public_routes() -> None:
    document = load_openapi()
    assert document["info"]["version"] == "1.0.0"
    assert "/api/version" in document["paths"]
    assert "/api/v1/projects/{project}/tasks/{task_id}/position" in document["paths"]


def test_openapi_has_no_delete_or_settings_routes() -> None:
    paths = load_openapi()["paths"]
    methods = {method for operations in paths.values() for method in operations}

    assert "delete" not in methods
    assert "put" not in methods
    assert all("settings" not in path for path in paths)
