"""CRM annotations: per-merchant tags, notes, and stored custom segment definitions.

Computed CRM metrics (spend, frequency, churn risk, lifecycle, standard segments)
are derived on the fly in the CRM service from orders/transactions — never stored
stale. This table holds only merchant-authored custom segments.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PKMixin, TimestampMixin


class CustomerTag(PKMixin, TimestampMixin, Base):
    __tablename__ = "customer_tags"
    __table_args__ = (UniqueConstraint("merchant_id", "customer_id", "tag", name="uq_customer_tag"),)

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    tag: Mapped[str] = mapped_column(String(48), nullable=False)


class CustomerNote(PKMixin, TimestampMixin, Base):
    __tablename__ = "customer_notes"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    author_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(String(1000), nullable=False)


class CustomerSegment(PKMixin, TimestampMixin, Base):
    """Merchant-defined custom segment (definition stored as JSON criteria)."""

    __tablename__ = "customer_segments"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    definition: Mapped[dict] = mapped_column(JSON, default=dict)
