"""Shared schema bits."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer


def _to_utc_z(dt: datetime) -> str:
    """Serialize a datetime as unambiguous UTC ISO-8601 with a 'Z' suffix.

    Stored timestamps are naive UTC (``app.db.base.utcnow``); we tag them as UTC and
    emit e.g. ``2026-05-30T05:11:30Z`` so clients across regions parse them correctly
    (a bare ``…T05:11:30`` is read as *local* time by ``new Date()`` → off by the offset).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# Use for every datetime field exposed over the API (multi-region correctness).
UtcDatetime = Annotated[datetime, PlainSerializer(_to_utc_z, return_type=str, when_used="json")]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str
