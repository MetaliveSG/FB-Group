"""Back-office identity (User/Role/Permission, scoped assignments) + diner identity
(Customer/CustomerAuthIdentity)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Column, Date, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin

# Role <-> Permission many-to-many
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(PKMixin, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(200), default="")


class Role(PKMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(200), default="")

    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permissions, lazy="selectin")


class User(PKMixin, TimestampMixin, Base):
    """Back-office user (super admin, merchant staff, etc.)."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # POS quick-login PIN. Legacy bcrypt hash (web set_pin, now dead) kept for back-compat.
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    # POS storefront PIN, owner-revealable → encrypted at rest (Fernet ciphertext, not plaintext;
    # key in env, see app/core/pin_crypto.py). Unique per STOREFRONT; resolves one operator at the
    # bound outlet. Only set for kind="pos" users. String(255) holds the Fernet token.
    pin: Mapped[str | None] = mapped_column(String(255))
    # Account kind — the two login surfaces are SEGREGATED:
    #   "web" → email + password at /merchant (dashboard); cannot PIN-login.
    #   "pos" → PIN-only till operator at /pos; synthetic email + locked password → cannot web-login.
    kind: Mapped[str] = mapped_column(String(8), default="web", server_default="web", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )


class UserRoleAssignment(PKMixin, TimestampMixin, Base):
    """A role granted to a user within a scope (platform/merchant/brand/outlet)."""

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id", name="uq_user_role_scope"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    scope_type: Mapped[str] = mapped_column(String(20), default="platform")  # ScopeType
    scope_id: Mapped[str | None] = mapped_column(String(32), index=True)  # merchant/brand/outlet id

    user: Mapped["User"] = relationship(back_populates="role_assignments")
    role: Mapped["Role"] = relationship(lazy="selectin")


class Customer(PKMixin, TimestampMixin, Base):
    """A diner. Global identity (a person can transact at multiple merchants)."""

    __tablename__ = "customers"

    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    birthday: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(16))  # male|female|other|null (optional)
    # PDPA: marketing is EXPRESS opt-in → default False. The audit trail lives in `customer_consents`;
    # this is the current quick flag campaigns filter on. See app/services/consent.py.
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    identities: Mapped[list["CustomerAuthIdentity"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan", lazy="selectin"
    )


class CustomerAuthIdentity(PKMixin, TimestampMixin, Base):
    """One login method linked to a customer (enables account linking)."""

    __tablename__ = "customer_auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "identifier", name="uq_identity_provider_identifier"),
    )

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # AuthProvider
    identifier: Mapped[str] = mapped_column(String(255), nullable=False)  # email/phone/provider-sub
    secret_hash: Mapped[str | None] = mapped_column(String(255))  # password hash (password provider)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped["Customer"] = relationship(back_populates="identities")


class CustomerConsent(PKMixin, TimestampMixin, Base):
    """Append-only PDPA consent audit — ONE row per consent action (grant/withdraw), captured AT the
    point we collect PII. Keyed to the data-controller `merchant_id` (the loyalty domain resolved from
    the QR context; PDPA = consent is given to an organisation) + the `purpose`. This is the legal
    record; `Customer.marketing_consent` is the denormalised current flag. See app/services/consent.py."""

    __tablename__ = "customer_consents"

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    merchant_id: Mapped[str | None] = mapped_column(String(32), index=True)  # loyalty domain / tenant; None = platform
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)  # "terms" | "marketing"
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[str] = mapped_column(String(24), default="")      # consent/notice version captured
    source: Mapped[str] = mapped_column(String(24), default="")       # qr_signup | register | sso | profile
    ip: Mapped[str | None] = mapped_column(String(64))
