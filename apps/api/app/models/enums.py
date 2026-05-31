"""String enums — stored as their `.value` in VARCHAR columns (portable)."""
from enum import Enum


class RoleName(str, Enum):
    SUPER_ADMIN = "super_admin"            # Platform Owner — full wildcard (manages operators)
    # Platform-tier operator roles (least-privilege, below the Owner):
    PLATFORM_ADMIN = "platform_admin"          # merchants + coalitions + drill-in, NOT operators
    PLATFORM_ONBOARDER = "platform_onboarder"  # onboard/edit merchants only (no suspend/coalitions/drill-in)
    PLATFORM_SUPPORT = "platform_support"      # read-only (overview + merchants + read-only drill-in)
    MERCHANT_OWNER = "merchant_owner"
    BRAND_MANAGER = "brand_manager"
    OUTLET_MANAGER = "outlet_manager"
    STAFF = "staff"
    CUSTOMER = "customer"


class ScopeType(str, Enum):
    PLATFORM = "platform"
    MERCHANT = "merchant"
    BRAND = "brand"
    OUTLET = "outlet"


class AuthProvider(str, Enum):
    PASSWORD = "password"       # email + password
    MOBILE_OTP = "mobile_otp"   # phone + OTP
    GOOGLE = "google"
    APPLE = "apple"


class OrderChannel(str, Enum):
    QR = "qr"
    CASHIER = "cashier"
    POS = "pos"  # pushed in from a merchant's external POS (integrations API, Phase 3)


class OrderType(str, Enum):
    DINE_IN = "dine_in"
    TAKEAWAY = "takeaway"
    MANUAL = "manual"


class OrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Allowed forward transitions for the order lifecycle.
ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    NETS = "nets"
    PAYWAVE = "paywave"
    PAYNOW = "paynow"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class RewardTxnType(str, Enum):
    EARN = "earn"
    REDEEM = "redeem"
    ADJUST = "adjust"
    EXPIRE = "expire"


class RewardScope(str, Enum):
    MERCHANT = "merchant"
    COALITION = "coalition"


class RewardRuleType(str, Enum):
    EARN_RATE = "earn_rate"               # points per $1 spent
    FIRST_VISIT = "first_visit"           # one-off bonus on first order
    BIRTHDAY = "birthday"                 # bonus in birthday month
    REPEAT_VISIT = "repeat_visit"         # bonus every N visits
    CAMPAIGN_MULTIPLIER = "campaign_multiplier"  # x multiplier in a window


class LoyaltyTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class LifecycleStage(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    AT_RISK = "at_risk"
    DORMANT = "dormant"
    VIP = "vip"


class CampaignType(str, Enum):
    WHATSAPP_PROMO = "whatsapp_promo"
    BIRTHDAY = "birthday"
    WINBACK = "winback"
    WEEKDAY_BOOST = "weekday_boost"
    NEW_CUSTOMER_RETURN = "new_customer_return"
    VIP_REWARD = "vip_reward"


class MessageStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class RewardKind(str, Enum):
    DISCOUNT = "discount"      # $ off (value = amount)
    FREE_ITEM = "free_item"    # a free menu item (value in name)
    VOUCHER = "voucher"        # generic voucher


class WheelPrizeKind(str, Enum):
    POINTS = "points"          # award N points (value)
    VOUCHER = "voucher"        # award a voucher (label)
    NOTHING = "nothing"        # better luck next time


class TaskStatus(str, Enum):
    OPEN = "open"
    DONE = "done"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class OpportunityStage(str, Enum):
    PROSPECTING = "prospecting"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


# Stages that count as still-in-pipeline (open) vs terminal.
OPEN_OPPORTUNITY_STAGES = [
    OpportunityStage.PROSPECTING, OpportunityStage.QUALIFIED,
    OpportunityStage.PROPOSAL, OpportunityStage.NEGOTIATION,
]
PIPELINE_STAGE_ORDER = OPEN_OPPORTUNITY_STAGES + [OpportunityStage.WON, OpportunityStage.LOST]

# --- Pipeline modes: a merchant's pipeline can be a B2B "sales" pipeline or a
# customer "winback" (retention) pipeline. Each has its own ordered stage set. ---
SALES_STAGES = [s.value for s in PIPELINE_STAGE_ORDER]
WINBACK_STAGES = ["at_risk", "contacted", "offer_sent", "recovered", "churned"]
PIPELINE_DEFS: dict[str, dict] = {
    "sales": {
        "stages": SALES_STAGES,
        "open": [s.value for s in OPEN_OPPORTUNITY_STAGES],
        "won": "won", "lost": "lost",
    },
    "winback": {
        "stages": WINBACK_STAGES,
        "open": ["at_risk", "contacted", "offer_sent"],
        "won": "recovered", "lost": "churned",
    },
}
ALL_OPPORTUNITY_STAGES = SALES_STAGES + WINBACK_STAGES


class ActivityType(str, Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    WHATSAPP = "whatsapp"
    NOTE = "note"
