"""Phase 0d — boundary indirection.

Two boundaries that the platform must resolve, kept as *concepts* so callers stop hard-coding
`merchant_id` for these purposes. Today both resolve to the merchant (single-tenant, flat tree),
so this is behaviour-neutral — but routing through here means Phase 1/2 can change *how* a
boundary is resolved (walk the org tree, honour a per-venue settlement mode) without touching
any call site.

  * **loyalty domain** — the free-coin ring a posting belongs to. Today = the merchant. Phase 1:
    the nearest `is_loyalty_domain` ancestor in the org tree (a group spanning many merchants).
  * **settlement account** — who collects the money for a sale. Today = the merchant. Phase 2:
    resolved by the venue's `settlement_mode` (operator central till vs per-stall).

See `docs/architecture-org-tree.md` §5.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.org import PATH_SEP, OrgNode
from app.models.orders import Order
from app.services import merchant_settings

# The per-node module flags (resolved binary + parent-gated).
MODULE_FLAGS = ("rewards_enabled", "qr_ordering_enabled", "pos_enabled", "wallet_enabled")

# Module flag → its org_node column (binary on/off, parent-gated).
_MODULE_COL = {
    "rewards_enabled": "mod_rewards",        # Intelligence
    "qr_ordering_enabled": "mod_qr_ordering",  # Table QR
    "pos_enabled": "mod_pos",                # POS
    "wallet_enabled": "mod_wallet",          # Wallet (additionally gated by qr_ordering — see resolve_modules)
}


def loyalty_domain_id(merchant_id: str) -> str:
    """The loyalty domain (free-coin ring) for a merchant. Today the merchant *is* the domain;
    Phase 1 resolves the nearest `is_loyalty_domain` ancestor in the org tree."""
    return merchant_id


def settlement_account_id(db: Session, *, order: Order) -> str:
    """Who the sale settles to. Today = the order's merchant; Phase 2 resolves the venue's
    `settlement_mode` (operator central account vs the individual stall)."""
    return order.merchant_id


def module_flags(db: Session, *, merchant_id: str) -> dict:
    """The adopted-module flags for a merchant (rewards / qr_ordering / pos) from `Merchant.settings`
    (the legacy / fallback layer). Per-node overrides resolve through `resolve_modules`."""
    settings = merchant_settings.get_settings(db, merchant_id=merchant_id)
    return {flag: bool(settings.get(flag, False)) for flag in MODULE_FLAGS}


def _node_chain(db: Session, node: OrgNode) -> list[OrgNode]:
    """`node` + its ancestors, NEAREST-first (node, parent, …, root). Path-prefix, no recursion."""
    ids = node.path.split(PATH_SEP)                       # root-first lineage of node ids
    found = {n.id: n for n in db.scalars(select(OrgNode).where(OrgNode.id.in_(ids))).all()}
    return [found[i] for i in reversed(ids) if i in found]


def resolve_modules(db: Session, *, node: OrgNode | None, merchant_id: str) -> dict:
    """The 3 module flags resolved for a node — **binary + parent-gated**: a module is ON for a node
    only if the node AND every ancestor have it ON (`effective = AND of own-flags up the path`).
    Turning a node OFF locks its whole subtree OFF; a child can be ON only under an ON parent.

    `node=None` (a collapsed/legacy storefront with no spine node, or a tenant-level summary with no
    specific node) falls back to the tenant's `Merchant.settings` → defaults — unchanged.

    `node` is the storefront (or any node) the action happens at; `merchant_id` is the funding tenant
    used for the node=None fallback. Returns the same shape as `module_flags`."""
    if node is None:
        base = module_flags(db, merchant_id=merchant_id)
    else:
        chain = _node_chain(db, node)                      # node + ancestors (nearest-first)
        base = {flag: all(bool(getattr(n, col)) for n in chain) for flag, col in _MODULE_COL.items()}
    # Wallet is money to spend on orders → additionally gated by Table QR (no ordering ⇒ no wallet).
    base["wallet_enabled"] = base["wallet_enabled"] and base["qr_ordering_enabled"]
    return base


def node_for_outlet(db: Session, outlet_id: str | None) -> OrgNode | None:
    """The storefront OrgNode for an outlet — via the `menu.id == node.id` invariant
    (falls back to a node whose id == outlet_id for the legacy/collapsed seed)."""
    if not outlet_id:
        return None
    from app.services import pos_staff
    return pos_staff.node_for_outlet(db, outlet_id)


def resolve_modules_for_outlet(db: Session, *, outlet_id: str | None, merchant_id: str) -> dict:
    """Convenience: resolve the 3 module flags for the node an outlet maps to (cascade + fallback)."""
    return resolve_modules(db, node=node_for_outlet(db, outlet_id), merchant_id=merchant_id)


# --- Service options (fulfilment) — the storefront's enabled set (cascade) ----------------------
def resolve_service_options(db: Session, *, node: OrgNode | None) -> list[str]:
    """The enabled service-option keys for a node — the **nearest declaring ancestor's** non-empty list
    wins (cascade like the module flags); falls back to the default (restaurant table service). Foodcourt
    sets `["dine_in_pickup","takeaway"]` once high and stalls inherit."""
    from app.models.enums import DEFAULT_SERVICE_OPTIONS, SERVICE_OPTIONS
    if node is not None:
        for n in _node_chain(db, node):
            opts = getattr(n, "service_options", None)
            if opts:
                return [k for k in opts if k in SERVICE_OPTIONS] or list(DEFAULT_SERVICE_OPTIONS)
    return list(DEFAULT_SERVICE_OPTIONS)


def resolve_service_options_for_outlet(db: Session, *, outlet_id: str | None) -> list[str]:
    """The enabled service-option keys for the node an outlet maps to (cascade + fallback)."""
    return resolve_service_options(db, node=node_for_outlet(db, outlet_id))


# --- Brand kit (customer-app theming) — cascade-MERGED (partial per-key override) ---------------
# Colours (primary/accent) drive CSS-var overrides; logo_url/hero_image_url/tagline are media/copy the
# customer app's hero consumes. Adding a key here auto-flows through resolve/get/set + the QR context.
_THEME_KEYS = (
    "primary", "accent", "logo_url",
    "hero_image_url", "hero_images",            # hero_images = a list → home carousel/slideshow
    "mascot_url",                               # brand mascot (decorates the rewards promo, with steam)
    "tagline", "story", "about_image_url",      # brand story block
    # Enterprise profile (set on the parent/enterprise node; tenants inherit via the cascade) —
    # powers the "Get to know {enterprise}" section.
    "enterprise_name", "enterprise_logo_url", "enterprise_image_url", "enterprise_story",
    "enterprise_awards",                        # list of award badge image URLs (horizontal scroll)
    # Enterprise SHOWCASE (the corporate landing at /t/node/{enterprise}) — set on the enterprise node:
    "enterprise_stats",       # [{value, label}] headline numbers
    "enterprise_brands",      # [{name, logo}] the brand portfolio (scrollable)
    "enterprise_csr_headline", "enterprise_csr",   # CSR headline + [{title, date, body, image}]
    "enterprise_history",     # [{year, text, image}] company timeline
)


def resolve_theme(db: Session, *, node: OrgNode | None) -> dict:
    """The effective theme for a node — **merged down the path** (root→node, nearest wins per key), so an
    enterprise's house style is inherited and a brand/outlet overrides only the keys it sets. Empty dict =
    no overrides (the customer app falls back to its default design tokens)."""
    out: dict = {}
    if node is not None:
        for n in reversed(_node_chain(db, node)):   # root → node, so nearer nodes overwrite
            t = getattr(n, "theme", None)
            if isinstance(t, dict):
                out.update({k: v for k, v in t.items() if k in _THEME_KEYS and v})
    return out


def resolve_theme_for_outlet(db: Session, *, outlet_id: str | None) -> dict:
    return resolve_theme(db, node=node_for_outlet(db, outlet_id))


def get_node_theme(db: Session, node: OrgNode) -> dict:
    """The node's OWN theme (null = inherit) + the RESOLVED (merged) theme."""
    return {"own": node.theme, "resolved": resolve_theme(db, node=node)}


def set_node_theme(db: Session, node: OrgNode, theme: dict | None) -> dict:
    """Set the node's own theme (known keys only: primary/accent/logo_url/hero_image_url/tagline).
    Empty/null = inherit (clear)."""
    if not theme:
        node.theme = None
    else:
        # keep list values (hero_images / enterprise_awards) intact; coerce scalars to str
        clean = {k: (v if isinstance(v, list) else str(v))
                 for k, v in theme.items() if k in _THEME_KEYS and v}
        node.theme = clean or None
    db.flush()
    return get_node_theme(db, node)


def get_node_service_options(db: Session, node: OrgNode) -> dict:
    """The node's OWN enabled set (null = inherit) + the RESOLVED set (cascade) + the full catalog."""
    from app.models.enums import SERVICE_OPTIONS
    return {
        "own": node.service_options,
        "resolved": resolve_service_options(db, node=node),
        "catalog": [{"key": k, **v} for k, v in SERVICE_OPTIONS.items()],
    }


def set_node_service_options(db: Session, node: OrgNode, options: list[str] | None) -> dict:
    """Set the node's enabled service options (validated to known keys). `None`/empty = inherit (clear)."""
    from app.models.enums import SERVICE_OPTIONS
    if not options:
        node.service_options = None
    else:
        node.service_options = [k for k in options if k in SERVICE_OPTIONS] or None
    db.flush()
    return get_node_service_options(db, node)


# --- per-node toggle get/set (the NodeDetailDrawer "Modules" section) ---------------------------

def _parent_enabled(db: Session, node: OrgNode) -> dict:
    """Each module's effective value at the node's PARENT (the gate): a child can be ON only if the
    parent is ON. A root node (no parent) is ungated → all True."""
    parent = db.get(OrgNode, node.parent_id) if node.parent_id else None
    if parent is None:
        return {flag: True for flag in _MODULE_COL}
    return resolve_modules(db, node=parent, merchant_id=node.settlement_account_id)


def get_node_modules(db: Session, node: OrgNode) -> dict:
    """The node's OWN binary on/off per module + the RESOLVED effective values (after parent-gating)
    + `parent_enabled` (whether each module is ON at the parent — drives the grey/lock in the grid)."""
    return {
        "rewards": bool(node.mod_rewards),
        "qr_ordering": bool(node.mod_qr_ordering),
        "pos": bool(node.mod_pos),
        "wallet": bool(node.mod_wallet),
        "resolved": resolve_modules(db, node=node, merchant_id=node.settlement_account_id),
        "parent_enabled": _parent_enabled(db, node),
    }


def set_node_modules(db: Session, node: OrgNode, *, rewards: bool | None = None,
                     qr_ordering: bool | None = None, pos: bool | None = None,
                     wallet: bool | None = None) -> dict:
    """Set a node's per-module binary on/off. Omitted fields are left unchanged. Turning a node OFF
    cascades OFF to the whole subtree via parent-gating (no extra writes — `resolve_modules` AND-gates)."""
    if rewards is not None:
        node.mod_rewards = bool(rewards)
    if qr_ordering is not None:
        node.mod_qr_ordering = bool(qr_ordering)
    if pos is not None:
        node.mod_pos = bool(pos)
    if wallet is not None:
        node.mod_wallet = bool(wallet)
    db.flush()
    return get_node_modules(db, node)
