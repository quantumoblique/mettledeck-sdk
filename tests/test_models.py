from dataclasses import FrozenInstanceError

import pytest

from mettledeck import Task


def test_task_models_are_frozen_and_ignore_unknown_fields(
    task_payload: dict[str, object],
) -> None:
    task = Task.from_dict({**task_payload, "future_field": {"added": "later"}})
    assert task.title == "Test task"
    with pytest.raises(FrozenInstanceError):
        setattr(task, "title", "Changed")
