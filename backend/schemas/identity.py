"""Local user identity exposed to capability routes."""

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    username: str
    full_name: str
    role: str
    clearance_level: str
