"""Reserved API dependencies.

Pre-wired bearer-auth so a future authenticated trigger endpoint binds behind it
without rearchitecting. Unused by the MVP routes (which are unauthenticated and
read-only: /health, /version).
"""

from __future__ import annotations

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from qaia.settings import Settings

_bearer = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    return Settings()


def require_bearer(
    credentials: HTTPAuthorizationCredentials | None = None,
) -> None:
    """Placeholder auth gate for a future trigger endpoint.

    Not attached to any MVP route. Wired here so adding an authenticated endpoint
    is a one-line ``Depends(require_bearer)`` rather than an auth rework.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")


__all__ = ["_bearer", "get_settings", "require_bearer"]
