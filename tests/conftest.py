import pytest


@pytest.fixture
def task_payload() -> dict[str, object]:
    return {
        "id": "task-1",
        "project_id": "project-1",
        "revision": 3,
        "title": "Test task",
        "description": "Test description",
        "tags": ["tag-1"],
        "location": {"workspace": "kanban", "column_id": "todo", "position": 0},
        "planning_description_hidden": False,
        "media": {"present": False},
        "attachments": [],
        "drawing": {"present": False},
    }
