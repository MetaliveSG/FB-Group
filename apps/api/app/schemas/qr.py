"""QR dining-context response."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.catalog import MenuOut


class _Ref(BaseModel):
    id: str
    name: str


class _TableRef(BaseModel):
    id: str
    label: str


class _OutletRef(BaseModel):
    id: str
    name: str
    address: str | None = None


class StallRef(BaseModel):
    menu_id: str
    stall_name: str
    cuisine: str | None = None
    logo: str | None = None
    is_open: bool = True
    item_count: int = 0
    # The stall's own full-ordering page, when it's a dedicated storefront venue (its outlet hosts
    # one menu + has its own table QR) — the group browse navigates here on tap. Null for a stall
    # in a shared foodcourt outlet (no per-stall token): the browse opens its read-only sheet instead.
    order_path: str | None = None


class NodeBrowseOut(BaseModel):
    """A node-scoped customer browse (the 'brand / group app' view): point at any member-tree node
    and see the orderable leaf stalls in its scope (its own sellable leaves + any stalls leased into
    a venue within it). `is_group` = it's a chain (many stalls) vs a single storefront."""
    node_id: str
    name: str
    is_group: bool = True
    stalls: list[StallRef] = []


class QrContextOut(BaseModel):
    qr_token: str
    merchant: _Ref
    brand: _Ref
    outlet: _OutletRef
    table: _TableRef
    # Foodcourt: an outlet may host many stalls (menus). `stalls` always lists them;
    # `is_foodcourt` = len(stalls) > 1. `menu` is the full single menu (single-stall /
    # restaurant — backward compat); null for a foodcourt (fetch one via /qr/{t}/menu/{id}).
    is_foodcourt: bool = False
    stalls: list[StallRef] = []
    menu: MenuOut | None = None
    # Module flags (Phase 2) — let the customer app render the right mode: ordering_enabled
    # off (but rewards on) → a rewards-only landing instead of menu+cart.
    ordering_enabled: bool = True
    rewards_enabled: bool = True
    # The storefront's enabled service options (fulfilment), each {key, label, hand_off}. The diner picks
    # one at checkout (auto if only one). hand_off=self_pickup → diner collects + "ready" alert.
    service_options: list[dict] = []
    # Resolved brand theme {primary, accent, logo_url} — the customer app injects these as CSS-var overrides.
    theme: dict = {}
    # i18n/currency: `locale` = the resolved UI language for this view (a PERSON fact); `currency` = the
    # outlet's settlement currency ISO 4217 (a SETTLEMENT fact). The app formats money with
    # Intl.NumberFormat(locale, {currency}) — so 0-decimal currencies (IDR/VND) render correctly. Decoupled:
    # the diner's language never changes the currency or the time.
    locale: str = "en"
    currency: str = "SGD"
