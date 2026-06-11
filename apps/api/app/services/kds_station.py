"""KDS station tokens — issue / reveal / rotate / revoke a per-outlet bearer token, and resolve one on
the kitchen tablet's authed requests. One row per outlet (rotating replaces the token in place)."""
from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.kds import KdsStation
from app.models.tenancy import Outlet


def _new_token() -> str:
    return secrets.token_urlsafe(24)   # ~32 url-safe chars, fits String(48)


def get_station(db: Session, *, outlet_id: str) -> KdsStation | None:
    return db.scalar(select(KdsStation).where(KdsStation.outlet_id == outlet_id))


def issue_station(db: Session, *, outlet: Outlet, label: str | None = None) -> KdsStation:
    """Create the outlet's station, or **rotate** its token (a new token invalidates the old one).
    Sets it active. Idempotent shape: always exactly one station row per outlet."""
    station = get_station(db, outlet_id=outlet.id)
    if station is None:
        station = KdsStation(merchant_id=outlet.merchant_id, outlet_id=outlet.id,
                             token=_new_token(), label=label or "Kitchen", is_active=True)
        db.add(station)
    else:
        station.token = _new_token()
        station.is_active = True
        if label:
            station.label = label
    db.flush()
    return station


def revoke_station(db: Session, *, outlet_id: str) -> KdsStation | None:
    """Deactivate the outlet's station (the token stops authenticating). Re-issue to bring it back."""
    station = get_station(db, outlet_id=outlet_id)
    if station is not None:
        station.is_active = False
        db.flush()
    return station


def resolve_active(db: Session, *, token: str) -> KdsStation | None:
    """The ACTIVE station for a bearer token (None if unknown/revoked). Touches `last_seen_at`."""
    if not token:
        return None
    station = db.scalar(select(KdsStation).where(KdsStation.token == token, KdsStation.is_active.is_(True)))
    if station is not None:
        station.last_seen_at = utcnow()
    return station
