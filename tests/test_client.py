from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from mettledeck import Client, IncompatibleVersionError, Workspace

RequestHandler = Callable[[httpx.Request], httpx.Response]


def make_client(handler: RequestHandler) -> Client:
    return Client(
        "http://127.0.0.1:12345",
        "secret",
        transport=httpx.MockTransport(handler),
    )


def test_version_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/version"
        return httpx.Response(
            200,
            json={
                "application_version": "0.2.0",
                "supported_api_versions": [1],
                "preferred_api_version": 1,
            },
        )

    with make_client(handler) as client:
        assert client.version().application_version == "0.2.0"


def test_create_has_idempotency_key_and_typed_fields(
    task_payload: dict[str, object],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer secret"
        assert request.headers["idempotency-key"]
        assert request.headers["user-agent"].startswith("mettledeck-python/")
        payload = json.loads(request.content)
        assert payload["workspace"] == "planning"
        assert payload["impact"] == 4
        return httpx.Response(200, json=task_payload)

    with make_client(handler) as client:
        task = client.create(
            title="Test task",
            impact=4,
            workspace=Workspace.PLANNING,
        )
        assert task.id == "task-1"


def test_update_sends_explicit_null_but_omits_missing(
    task_payload: dict[str, object],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["impact"] is None
        assert "difficulty" not in payload
        return httpx.Response(200, json=task_payload)

    with make_client(handler) as client:
        client.update("task-1", impact=None)


def test_multipart_accepts_bytes(task_payload: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        content_type = request.headers["content-type"]
        assert content_type.startswith("multipart/form-data; boundary=")
        assert b'name="payload"' in request.content
        assert b'name="media"' in request.content
        return httpx.Response(200, json=task_payload)

    with make_client(handler) as client:
        client.create(title="Test task", media=b"image bytes")


def test_watch_tasks_uses_etag(
    monkeypatch: pytest.MonkeyPatch,
    task_payload: dict[str, object],
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, headers={"etag": '"3"'}, json={"tasks": [task_payload]})
        if calls == 2:
            assert request.headers["if-none-match"] == '"3"'
            return httpx.Response(304)
        return httpx.Response(200, headers={"etag": '"4"'}, json={"tasks": []})

    monkeypatch.setattr("mettledeck.client.time.sleep", lambda _: None)
    with make_client(handler) as client:
        watched = client.watch_tasks(interval=0)
        assert len(next(watched)) == 1
        assert next(watched) == ()


def test_create_retry_reuses_idempotency_key(task_payload: dict[str, object]) -> None:
    keys: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        keys.append(request.headers["idempotency-key"])
        if len(keys) == 1:
            raise httpx.ReadError("connection closed", request=request)
        return httpx.Response(200, json=task_payload)

    with make_client(handler) as client:
        client.create(title="Test task")
    assert len(keys) == 2
    assert keys[0] == keys[1]


def test_connect_negotiates_highest_shared_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "mettledeck.client._read_live_discovery",
        lambda: {"base_url": "http://127.0.0.1:1", "token": "secret"},
    )
    monkeypatch.setattr(
        "mettledeck.client._read_version",
        lambda _: {
            "application_version": "0.2.0",
            "supported_api_versions": [1, 2],
            "preferred_api_version": 2,
        },
    )
    with Client.connect() as client:
        assert client.version().selected_api_version == 1


def test_connect_rejects_incompatible_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "mettledeck.client._read_live_discovery",
        lambda: {"base_url": "http://127.0.0.1:1", "token": "secret"},
    )
    monkeypatch.setattr(
        "mettledeck.client._read_version",
        lambda _: {
            "application_version": "9.0.0",
            "supported_api_versions": [9],
            "preferred_api_version": 9,
        },
    )
    with pytest.raises(IncompatibleVersionError):
        Client.connect()
