from __future__ import annotations

import json
from pathlib import Path

EXPECTED_PATHS = {
    "/api/version",
    "/api/v1/projects",
    "/api/v1/projects/{project}",
    "/api/v1/projects/{project}/tasks",
    "/api/v1/projects/{project}/tasks/{task_id}",
    "/api/v1/projects/{project}/tasks/{task_id}/position",
}


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "openapi/mettledeck-v1.json"
    document = json.loads(path.read_text(encoding="utf-8"))

    if not str(document.get("openapi", "")).startswith("3."):
        raise SystemExit("Expected an OpenAPI 3 file")
    if not str(document.get("info", {}).get("version", "")).startswith("1."):
        raise SystemExit("Expected API version 1")

    missing = EXPECTED_PATHS.difference(document.get("paths", {}))
    if missing:
        raise SystemExit(f"Missing paths: {', '.join(sorted(missing))}")

    print("OpenAPI file looks OK.")


if __name__ == "__main__":
    main()
