from __future__ import annotations

import json
import mimetypes
import os
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import Iterable, Iterator, Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote

import httpx

from ._version import __version__
from .exceptions import ApiError, ConnectionError, IncompatibleVersionError
from .models import Position, Project, Task, VersionInfo, Workspace

SUPPORTED_API_VERSIONS = (1,)
_UNSET = object()
FileInput = str | os.PathLike[str] | bytes | bytearray | BinaryIO


class Client:
    """Synchronous client for the MettleDeck local automation API."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        api_version: int = 1,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version
        self._http = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": f"mettledeck-python/{__version__}",
            },
            timeout=timeout,
            transport=transport,
        )
        self._version_info: VersionInfo | None = None

    @classmethod
    def connect(
        cls,
        *,
        timeout: float = 30.0,
        executable: str | os.PathLike[str] | None = None,
    ) -> Client:
        """Discover a live app, or launch it and wait for user approval."""

        deadline = time.monotonic() + timeout
        discovery = _read_live_discovery()
        if discovery is None:
            _launch_application(executable)
            while time.monotonic() < deadline:
                discovery = _read_live_discovery()
                if discovery is not None:
                    break
                time.sleep(0.1)
        if discovery is None:
            raise ConnectionError(
                "MettleDeck did not expose its local API. Approve the request in the app, "
                "or enable Local automation API in Settings."
            )

        raw_version = _read_version(str(discovery["base_url"]))
        shared = sorted(
            set(int(value) for value in raw_version.get("supported_api_versions", ()))
            & set(SUPPORTED_API_VERSIONS)
        )
        if not shared:
            raise IncompatibleVersionError(
                "The installed application and this SDK do not share an API version"
            )
        selected = shared[-1]
        client = cls(
            str(discovery["base_url"]),
            str(discovery["token"]),
            api_version=selected,
        )
        client._version_info = VersionInfo.from_dict(raw_version, selected)
        return client

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def version(self) -> VersionInfo:
        """Return application and negotiated API version information."""

        if self._version_info is None:
            response = self._request("GET", "/api/version", authenticated=False)
            self._version_info = VersionInfo.from_dict(response.json(), self.api_version)
        return self._version_info

    def list_projects(self) -> tuple[Project, ...]:
        """List projects without switching the active project."""

        value = self._request("GET", self._path("projects")).json()
        active_id = str(value.get("active_project_id", ""))
        return tuple(
            Project(
                id=str(item.get("id", "")),
                name=str(item.get("name", "")),
                revision=int(item.get("revision", 0)),
                active=str(item.get("id", "")) == active_id,
            )
            for item in value.get("projects", ())
        )

    def project(self, project: str = "active") -> Project:
        """Read project columns, tags, and revision."""

        value = self._request("GET", self._path("projects", project)).json()
        return Project.from_dict(value)

    def list(
        self,
        *,
        project: str = "active",
        workspace: Workspace | str | None = None,
        column: str | None = None,
        planning_lane: int | None = None,
        tags: Sequence[str] = (),
    ) -> tuple[Task, ...]:
        """List tasks using optional workspace, location, and tag filters."""

        params = _without_none(
            {
                "workspace": _enum_value(workspace),
                "column": column,
                "planning_lane": planning_lane,
                "tags": ",".join(tags) if tags else None,
            }
        )
        value = self._request("GET", self._path("projects", project, "tasks"), params=params).json()
        return tuple(Task.from_dict(item) for item in value.get("tasks", ()))

    def get(self, task_id: str, *, project: str = "active", include_history: bool = False) -> Task:
        """Read a task by ID."""

        value = self._request(
            "GET",
            self._path("projects", project, "tasks", task_id),
            params={"include_history": str(include_history).lower()},
        ).json()
        return Task.from_dict(value)

    def create(
        self,
        *,
        title: str,
        project: str = "active",
        description: str | None = None,
        tags: Sequence[str] = (),
        impact: int | None = None,
        difficulty: int | None = None,
        progress: int | None = None,
        time_estimate: float | None = None,
        planning_description_hidden: bool = False,
        workspace: Workspace | str = Workspace.KANBAN,
        column: str | None = None,
        planning_lane: int | None = None,
        position: Position | str = Position.TOP,
        before_task: str | None = None,
        after_task: str | None = None,
        media: FileInput | None = None,
        attachments: Iterable[FileInput] = (),
    ) -> Task:
        """Create a task. A stable idempotency key is reused for one transport retry."""

        payload = _without_none(
            {
                "title": title,
                "description": description,
                "tags": list(tags),
                "impact": impact,
                "difficulty": difficulty,
                "progress": progress,
                "time_estimate": time_estimate,
                "planning_description_hidden": planning_description_hidden,
                "workspace": _enum_value(workspace),
                "column": column,
                "planning_lane": planning_lane,
                "position": _enum_value(position),
                "before_task": before_task,
                "after_task": after_task,
            }
        )
        key = str(uuid.uuid4())
        response = self._mutation_with_assets(
            "POST",
            self._path("projects", project, "tasks"),
            payload,
            media=media,
            attachments=attachments,
            headers={"Idempotency-Key": key},
            retry_transport_once=True,
        )
        return Task.from_dict(response.json())

    def update(
        self,
        task_id: str,
        *,
        project: str = "active",
        title: str | object = _UNSET,
        description: str | None | object = _UNSET,
        tags: Sequence[str] | None | object = _UNSET,
        add_tags: Sequence[str] = (),
        remove_tags: Sequence[str] = (),
        impact: int | None | object = _UNSET,
        difficulty: int | None | object = _UNSET,
        progress: int | None | object = _UNSET,
        time_estimate: float | None | object = _UNSET,
        planning_description_hidden: bool | None | object = _UNSET,
        media: FileInput | None = None,
        clear_media: bool = False,
        attachments: Iterable[FileInput] = (),
        remove_attachments: Sequence[str] = (),
    ) -> Task:
        """Partially update a task. Omitted values remain unchanged; None clears."""

        payload = _patch_payload(
            title=title,
            description=description,
            tags=None if tags is None else list(tags) if tags is not _UNSET else _UNSET,
            impact=impact,
            difficulty=difficulty,
            progress=progress,
            time_estimate=time_estimate,
            planning_description_hidden=planning_description_hidden,
        )
        payload.update(
            {
                "add_tags": list(add_tags),
                "remove_tags": list(remove_tags),
                "clear_media": clear_media,
                "remove_attachments": list(remove_attachments),
            }
        )
        response = self._mutation_with_assets(
            "PATCH",
            self._path("projects", project, "tasks", task_id),
            payload,
            media=media,
            attachments=attachments,
        )
        return Task.from_dict(response.json())

    def move(
        self,
        task_id: str,
        *,
        workspace: Workspace | str,
        project: str = "active",
        column: str | None = None,
        planning_lane: int | None = None,
        position: Position | str | None = None,
        before_task: str | None = None,
        after_task: str | None = None,
    ) -> Task:
        """Move or reorder a task using a stable destination anchor."""

        payload = _without_none(
            {
                "workspace": _enum_value(workspace),
                "column": column,
                "planning_lane": planning_lane,
                "position": _enum_value(position),
                "before_task": before_task,
                "after_task": after_task,
            }
        )
        response = self._request(
            "PATCH",
            self._path("projects", project, "tasks", task_id, "position"),
            json=payload,
        )
        return Task.from_dict(response.json())

    def watch_tasks(
        self,
        *,
        interval: float = 1.0,
        project: str = "active",
        workspace: Workspace | str | None = None,
        column: str | None = None,
        planning_lane: int | None = None,
        tags: Sequence[str] = (),
    ) -> Iterator[tuple[Task, ...]]:
        """Yield task snapshots only when the project ETag changes."""

        etag: str | None = None
        params = _without_none(
            {
                "workspace": _enum_value(workspace),
                "column": column,
                "planning_lane": planning_lane,
                "tags": ",".join(tags) if tags else None,
            }
        )
        while True:
            headers = {"If-None-Match": etag} if etag else None
            response = self._request(
                "GET",
                self._path("projects", project, "tasks"),
                params=params,
                headers=headers,
                allow_not_modified=True,
            )
            if response.status_code != 304:
                etag = response.headers.get("etag", etag)
                yield tuple(Task.from_dict(item) for item in response.json().get("tasks", ()))
            time.sleep(interval)

    def _path(self, *parts: str) -> str:
        encoded = "/".join(quote(str(part), safe="") for part in parts)
        return f"/api/v{self.api_version}/{encoded}"

    def _mutation_with_assets(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any],
        *,
        media: FileInput | None,
        attachments: Iterable[FileInput],
        headers: Mapping[str, str] | None = None,
        retry_transport_once: bool = False,
    ) -> httpx.Response:
        attachment_values = tuple(attachments)
        if media is None and not attachment_values:
            return self._request(
                method,
                path,
                json=payload,
                headers=headers,
                retry_transport_once=retry_transport_once,
            )
        files: list[tuple[str, tuple[str | None, bytes, str]]] = [
            ("payload", (None, json.dumps(payload).encode("utf-8"), "application/json"))
        ]
        if media is not None:
            files.append(("media", _file_tuple(media, "media")))
        files.extend(
            ("attachment", _file_tuple(value, "attachment")) for value in attachment_values
        )
        return self._request(
            method,
            path,
            files=files,
            headers=headers,
            retry_transport_once=retry_transport_once,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        allow_not_modified: bool = False,
        retry_transport_once: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        attempts = 2 if retry_transport_once else 1
        headers = dict(kwargs.pop("headers", None) or {})
        if not authenticated:
            headers["Authorization"] = ""
        for attempt in range(attempts):
            try:
                response = self._http.request(method, path, headers=headers, **kwargs)
                break
            except httpx.TransportError:
                if attempt + 1 >= attempts:
                    raise
        if allow_not_modified and response.status_code == 304:
            return response
        if response.is_error:
            try:
                value = response.json()
            except ValueError:
                value = {}
            raise ApiError(
                response.status_code,
                str(value.get("code", "http_error")),
                str(value.get("message", response.reason_phrase)),
                value.get("details"),
            )
        return response


def _discovery_paths() -> tuple[Path, ...]:
    override = os.environ.get("METTLEDECK_DISCOVERY_FILE")
    if override:
        return (Path(override),)
    if sys.platform == "win32":
        roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return (
            roaming / "com.quantumoblique.mettledeck/local-api-discovery.json",
            local / "com.quantumoblique.mettledeck/local-api-discovery.json",
            local / "MettleDeck/local-api-discovery.json",
        )
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return (config / "com.quantumoblique.mettledeck/local-api-discovery.json",)


def _read_live_discovery() -> dict[str, Any] | None:
    for path in _discovery_paths():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            _read_version(str(value["base_url"]))
            if value.get("token"):
                return value
        except (OSError, ValueError, KeyError, httpx.HTTPError):
            continue
    return None


def _read_version(base_url: str) -> dict[str, Any]:
    response = httpx.get(f"{base_url.rstrip('/')}/api/version", timeout=0.5)
    response.raise_for_status()
    return dict(response.json())


def _launch_application(executable: str | os.PathLike[str] | None) -> None:
    candidate = Path(executable) if executable else _find_executable()
    if candidate is None:
        raise ConnectionError(
            "MettleDeck is not running and its executable could not be found. Set "
            "METTLEDECK_EXECUTABLE to the installed executable path."
        )
    kwargs: dict[str, Any] = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(
        [str(candidate), "--mettledeck-api-request", "--background"],
        **kwargs,
    )


def _find_executable() -> Path | None:
    configured = os.environ.get("METTLEDECK_EXECUTABLE")
    candidates: list[Path] = [Path(configured)] if configured else []
    found = shutil.which("MettleDeck") or shutil.which("mettledeck")
    if found:
        candidates.append(Path(found))
    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        candidates.extend(
            [
                local / "MettleDeck/MettleDeck.exe",
                local / "Programs/MettleDeck/MettleDeck.exe",
                program_files / "MettleDeck/MettleDeck.exe",
            ]
        )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _file_tuple(value: FileInput, fallback_name: str) -> tuple[str, bytes, str]:
    if isinstance(value, (str, os.PathLike)):
        path = Path(value)
        data = path.read_bytes()
        name = path.name
    elif isinstance(value, (bytes, bytearray)):
        data = bytes(value)
        name = fallback_name
    else:
        name = Path(str(getattr(value, "name", fallback_name))).name
        position = value.tell() if hasattr(value, "tell") else None
        data = value.read()
        if position is not None and hasattr(value, "seek"):
            value.seek(position)
        if not isinstance(data, bytes):
            raise TypeError("File objects must be opened in binary mode")
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return name, data, mime


def _without_none(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _patch_payload(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not _UNSET}


def _enum_value(value: Enum | str | None) -> str | None:
    if value is None:
        return None
    return str(value.value if isinstance(value, Enum) else value)
