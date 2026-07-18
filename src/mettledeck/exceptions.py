from __future__ import annotations


class MettleDeckError(Exception):
    """Base SDK error."""


class ConnectionError(MettleDeckError):
    """The desktop application could not be discovered or started."""


class IncompatibleVersionError(MettleDeckError):
    """The SDK and application do not share an API version."""


class ApiError(MettleDeckError):
    """A structured error returned by the local API."""

    def __init__(self, status_code: int, code: str, message: str, details: object = None) -> None:
        super().__init__(f"{code}: {message}")
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
