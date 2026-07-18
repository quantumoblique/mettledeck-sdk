from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class Workspace(str, Enum):
    """Task workspace."""

    KANBAN = "kanban"
    PLANNING = "planning"


class Position(str, Enum):
    """Simple destination anchor."""

    TOP = "top"
    BOTTOM = "bottom"


@dataclass(frozen=True, slots=True)
class VersionInfo:
    application_version: str
    supported_api_versions: tuple[int, ...]
    preferred_api_version: int
    selected_api_version: int | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], selected: int | None = None) -> VersionInfo:
        return cls(
            application_version=str(value.get("application_version", "")),
            supported_api_versions=tuple(
                int(item) for item in value.get("supported_api_versions", ())
            ),
            preferred_api_version=int(value.get("preferred_api_version", 0)),
            selected_api_version=selected,
        )


@dataclass(frozen=True, slots=True)
class Column:
    id: str
    name: str
    position: int

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Column:
        return cls(
            id=str(value.get("id", "")),
            name=str(value.get("name", "")),
            position=int(value.get("position", 0)),
        )


@dataclass(frozen=True, slots=True)
class Tag:
    id: str
    name: str
    description: str = ""
    color: str = ""

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Tag:
        return cls(
            id=str(value.get("id", "")),
            name=str(value.get("name", "")),
            description=str(value.get("description", "")),
            color=str(value.get("color", "")),
        )


@dataclass(frozen=True, slots=True)
class Project:
    id: str
    name: str
    revision: int
    active: bool = False
    columns: tuple[Column, ...] = ()
    tags: tuple[Tag, ...] = ()
    planning_lane_count: int = 5

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Project:
        return cls(
            id=str(value.get("id", "")),
            name=str(value.get("name", "")),
            revision=int(value.get("revision", 0)),
            active=bool(value.get("active", False)),
            columns=tuple(Column.from_dict(item) for item in value.get("columns", ())),
            tags=tuple(Tag.from_dict(item) for item in value.get("tags", ())),
            planning_lane_count=int(value.get("planning_lane_count", 5)),
        )


@dataclass(frozen=True, slots=True)
class Location:
    workspace: Workspace
    position: int
    column_id: str | None = None
    column_name: str | None = None
    planning_lane: int | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Location:
        return cls(
            workspace=Workspace(str(value.get("workspace", Workspace.KANBAN.value))),
            position=int(value.get("position", 0)),
            column_id=_optional_str(value.get("column_id")),
            column_name=_optional_str(value.get("column_name")),
            planning_lane=_optional_int(value.get("planning_lane")),
        )


@dataclass(frozen=True, slots=True)
class Drawing:
    present: bool
    color: str | None = None
    strokes: Any = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Drawing:
        return cls(
            present=bool(value.get("present", False)),
            color=_optional_str(value.get("color")),
            strokes=value.get("strokes"),
        )


@dataclass(frozen=True, slots=True)
class Media:
    present: bool
    media_type: str | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Media:
        return cls(
            present=bool(value.get("present", False)),
            media_type=_optional_str(value.get("media_type")),
        )


@dataclass(frozen=True, slots=True)
class Attachment:
    id: str
    name: str
    mime: str
    size: int

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Attachment:
        return cls(
            id=str(value.get("id", "")),
            name=str(value.get("name", "")),
            mime=str(value.get("mime", "")),
            size=int(value.get("size", 0)),
        )


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    timestamp_utc: str
    kind: str
    message: str
    card_id: str | None = None
    from_column_id: str | None = None
    to_column_id: str | None = None
    source: str | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> HistoryEntry:
        return cls(
            timestamp_utc=str(value.get("timestamp_utc", "")),
            kind=str(value.get("kind", "")),
            message=str(value.get("message", "")),
            card_id=_optional_str(value.get("card_id")),
            from_column_id=_optional_str(value.get("from_column_id")),
            to_column_id=_optional_str(value.get("to_column_id")),
            source=_optional_str(value.get("source")),
        )


@dataclass(frozen=True, slots=True)
class Task:
    id: str
    project_id: str
    revision: int
    title: str
    description: str
    tags: tuple[str, ...]
    location: Location
    impact: int | None = None
    difficulty: int | None = None
    progress: int | None = None
    time_estimate: float | None = None
    actual_completion_days: float | None = None
    planning_description_hidden: bool = False
    media: Media = field(default_factory=lambda: Media(False))
    attachments: tuple[Attachment, ...] = ()
    drawing: Drawing = field(default_factory=lambda: Drawing(False))
    created_at: str | None = None
    active_time_days: float | None = None
    history: tuple[HistoryEntry, ...] | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Task:
        history = value.get("history")
        return cls(
            id=str(value.get("id", "")),
            project_id=str(value.get("project_id", "")),
            revision=int(value.get("revision", 0)),
            title=str(value.get("title", "")),
            description=str(value.get("description", "")),
            tags=tuple(str(item) for item in value.get("tags", ())),
            location=Location.from_dict(value.get("location", {})),
            impact=_optional_int(value.get("impact")),
            difficulty=_optional_int(value.get("difficulty")),
            progress=_optional_int(value.get("progress")),
            time_estimate=_optional_float(value.get("time_estimate")),
            actual_completion_days=_optional_float(value.get("actual_completion_days")),
            planning_description_hidden=bool(value.get("planning_description_hidden", False)),
            media=Media.from_dict(value.get("media", {})),
            attachments=tuple(Attachment.from_dict(item) for item in value.get("attachments", ())),
            drawing=Drawing.from_dict(value.get("drawing", {})),
            created_at=_optional_str(value.get("created_at")),
            active_time_days=_optional_float(value.get("active_time_days")),
            history=(
                None if history is None else tuple(HistoryEntry.from_dict(item) for item in history)
            ),
        )


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
