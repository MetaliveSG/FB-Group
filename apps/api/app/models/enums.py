"""String enums — stored as their `.value` in VARCHAR columns (portable)."""
from enum import Enum


class RoleName(str, Enum):
    SUPER_ADMIN = "super_admin"            # Platform Owner — full wildcard (manages operators)
    # Platform-tier operator roles (least-privilege, below the Owner):
    PLATFORM_ADMIN = "platform_admin"          # merchants + coalitions + drill-in, NOT operators
    PLATFORM_ONBOARDER = "platform_onboarder"  # onboard/edit merchants only (no suspend/coalitions/drill-in)
    PLATFORM_SUPPORT = "platform_support"      # read-only (overview + merchants + read-only drill-in)
    # Enterprise (group/holding-co) tier — assigned at an Enterprise org-node, cascades over
    # every Merchant beneath it. Roles = permission bundles; the node decides reach.
    GROUP_CEO = "group_ceo"            # full authority over the whole enterprise downline
    GROUP_COO = "group_coo"            # operations across the enterprise (no finance/admin)
    GROUP_CFO = "group_cfo"            # finance: reports + audit + crm read across the enterprise
    GROUP_ACCOUNTANT = "group_accountant"  # read-only finance (reports + audit)
    MERCHANT_OWNER = "merchant_owner"
    BRAND_MANAGER = "brand_manager"
    AREA_MANAGER = "area_manager"      # manage the outlets beneath a node (brand/region)
    OUTLET_MANAGER = "outlet_manager"
    STALL_OPERATOR = "stall_operator"  # one storefront (foodcourt stall)
    # Member-tree role PALETTE (Chain/Storefront model) — assign at ANY node; the node sets the
    # scope (cascades over its subtree), the role sets the verbs. A Manager high on a Chain IS the
    # area-manager/director; at a Storefront, the storefront manager. Supersedes the GROUP_*/
    # AREA_MANAGER/STALL_OPERATOR bundles (those stay only for the legacy demo seed).
    MANAGER = "manager"                # run everything in the subtree (structure/menu/staff/orders/reports)
    CASHIER = "cashier"                # till / payments at the storefront(s) in scope
    FINANCE = "finance"                # web read-only: REPORTS ONLY (the financials view)
    VIEWER = "viewer"                  # web read-only: view everything in scope EXCEPT reports
    STAFF = "staff"                    # legacy operational web role (order ops); superseded by VIEWER on the node palette
    # POS-only role (PIN operator at a storefront, NOT a web/dashboard login). The on-floor lead over
    # cashiers: POS operations + store reports, but none of web MANAGER's org/menu/staff powers.
    SUPERVISOR = "supervisor"
    CUSTOMER = "customer"


class ScopeType(str, Enum):
    PLATFORM = "platform"
    NODE = "node"          # assigned at any org-node → authority cascades down its subtree
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
    CANCELLED = "cancelled"            # abandoned before payment
    VOIDED = "voided"                  # a COMPLETED (paid) sale reversed at the POS (supervisor)


# Allowed forward transitions for the order lifecycle.
ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


class FulfilmentStatus(str, Enum):
    """The KITCHEN/ticket state — separate from `OrderStatus` (which tracks payment: COMPLETED = paid).
    The kitchen display (KDS) owns this. READY = ready for pick-up (customer collects from the stall)."""
    QUEUED = "queued"            # paid, waiting for the kitchen to start
    PREPARING = "preparing"      # being made
    READY = "ready"              # ready for pick-up / collection
    COLLECTED = "collected"      # handed to the customer — leaves the KDS queue


# Allowed forward transitions for the kitchen/fulfilment lifecycle.
FULFILMENT_TRANSITIONS: dict[FulfilmentStatus, set[FulfilmentStatus]] = {
    FulfilmentStatus.QUEUED: {FulfilmentStatus.PREPARING, FulfilmentStatus.READY},
    FulfilmentStatus.PREPARING: {FulfilmentStatus.READY},
    FulfilmentStatus.READY: {FulfilmentStatus.COLLECTED},
    FulfilmentStatus.COLLECTED: set(),
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
    VOIDED = "voided"     # payment reversed by a POS void (supervisor)


class RewardTxnType(str, Enum):
    EARN = "earn"
    REDEEM = "redeem"
    ADJUST = "adjust"
    EXPIRE = "expire"


class WalletEntryType(str, Enum):
    """Append-only stored-value wallet postings (signed amount). Credits: topup/reload/bonus/refund;
    debit: spend; adjust = caller-signed."""
    TOPUP = "topup"      # manual top-up (any PSP method)
    RELOAD = "reload"    # auto-reload (off-session saved card)
    BONUS = "bonus"      # top-up bonus ("load $50 get $5")
    SPEND = "spend"      # debit at order-ahead checkout
    REFUND = "refund"    # void/refund credited back
    ADJUST = "adjust"    # manual correction


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
