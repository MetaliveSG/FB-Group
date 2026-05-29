"""Menu read route (public)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.catalog import MenuOut
from app.services import catalog as catalog_service

router = APIRouter(tags=["catalog"])


@router.get("/outlets/{outlet_id}/menu", response_model=MenuOut)
def get_menu(outlet_id: str, db: Session = Depends(get_db)):
    return MenuOut.model_validate(catalog_service.get_active_menu(db, outlet_id))
