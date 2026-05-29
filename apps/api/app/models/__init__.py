"""Import all models so SQLAlchemy metadata + Alembic autogenerate see every table."""
from app.db.base import Base  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.campaigns import (  # noqa: F401
    Campaign,
    CampaignAudience,
    CampaignMessage,
    CampaignRedemption,
)
from app.models.catalog import Menu, MenuCategory, MenuItem, MenuModifier  # noqa: F401
from app.models.crm import CustomerNote, CustomerSegment, CustomerTag  # noqa: F401
from app.models.engagement import (  # noqa: F401
    CrmTask,
    CustomerActivity,
    JackpotPrize,
    Opportunity,
    RewardCatalogItem,
    WheelSegment,
)
from app.models.identity import (  # noqa: F401
    Customer,
    CustomerAuthIdentity,
    Permission,
    Role,
    User,
    UserRoleAssignment,
    role_permissions,
)
from app.models.loyalty import (  # noqa: F401
    Coalition,
    LoyaltyAccount,
    RewardRedemption,
    RewardRule,
    RewardTransaction,
    coalition_members,
)
from app.models.orders import Order, OrderItem  # noqa: F401
from app.models.payments import Payment, Transaction  # noqa: F401
from app.models.tenancy import Brand, DiningTable, Merchant, Outlet, QRCode  # noqa: F401

__all__ = ["Base"]
