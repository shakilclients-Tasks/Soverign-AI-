"""Trusted single-user context for the loopback-only application."""

from backend.schemas.identity import UserResponse


LOCAL_USER = UserResponse(
    id="local-user",
    username="local",
    full_name="Local User",
    role="local operator",
    clearance_level="LOCAL",
)


async def current_user() -> UserResponse:
    return LOCAL_USER
