# MettleDeck Python SDK

Python client for MettleDeck's local automation API. It connects to the desktop
application over the loopback interface; it does not expose MettleDeck to the
local network.

## Installation

```shell
pip install mettledeck
```

MettleDeck must be installed on the same computer. Enable **Local automation
API** under **Settings > General > Application**. The first connection may ask
for approval in the desktop application.

## Quick start

```python
from mettledeck import Client, Workspace

with Client.connect() as client:
    task = client.create(title="New task", workspace=Workspace.KANBAN)
    client.move(task.id, workspace=Workspace.PLANNING, planning_lane=2)
```

`Client.connect()` discovers a running application or starts the installed
application. The SDK and application negotiate the newest API version they both
support.

## Task operations

| Method | Action |
| --- | --- |
| `list_projects()` | List available projects |
| `project()` | Read columns, tags, and the current revision |
| `list()` | List tasks, optionally filtered by workspace, column, lane, or tag |
| `get()` | Read one task, with optional history |
| `create()` | Create a task, with optional media and attachments |
| `update()` | Change supplied task fields and leave omitted fields alone |
| `move()` | Move or reorder a task |
| `watch_tasks()` | Poll for task snapshots when the project revision changes |

Projects, columns, and tags are read-only in API v1. There is no task or project
deletion endpoint. `update()` can clear nullable task fields and can remove media
or attachments when those options are supplied explicitly.

All returned models are frozen dataclasses. Unknown response fields are ignored
so an older SDK can continue to work with compatible additions to API v1.

## Examples

The `examples` directory contains six small scripts:

- `create_task.py`
- `update_task.py`
- `move_task.py`
- `list_tasks.py`
- `add_media_and_attachments.py`
- `watch_tasks.py`

```shell
python -m pip install -e .
python examples/create_task.py
```

## Development

```shell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
python scripts/check_openapi.py
python -m build
python -m twine check dist/*
```

The API description is in `openapi/mettledeck-v1.json`.

## License

MIT

Copyright 2026 Quantum Oblique.
