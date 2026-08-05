"""Pydantic models shared across the app's API surfaces."""

from pydantic import BaseModel


class Feedback(BaseModel):
    """User feedback payload collected by the /feedback endpoint."""

    feedback: str
    rating: int | None = None
    session_id: str | None = None
    user_id: str | None = None
