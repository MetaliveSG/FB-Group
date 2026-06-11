"""Internationalisation foundation — locale resolution + content localisation.

Three INDEPENDENT axes (validated against how Grab architects its 8 SEA markets):
  • language  = a PERSON fact  → Customer.locale (floats per-diner, this module)
  • timezone  = a PLACE fact   → Outlet/tenant (app/analytics/timezones.py; untouched here)
  • currency  = a SETTLEMENT fact → Merchant.currency (display-only; FX deferred)

Content (menu names/descriptions) follows Grab's "author once, present many" model: there is ONE
canonical locale (the `name`/`description` columns) and an OPTIONAL `translations` override/cache layer.
A missing locale or key ALWAYS falls back to the canonical value — a diner never sees a blank or a key.
UI-string catalogs live in the web app (`packages/i18n`); this module handles DB-backed content + the
resolution chain the API needs.
"""
from __future__ import annotations

# Locales we recognise. `en` is the canonical/default. `en-SG` (Singlish) is an overlay on `en`.
# SG official languages (en/zh/ms/ta) + SEA-expansion (id/th/vi) + Singlish. Add by appending here;
# unknown tags resolve to DEFAULT_LOCALE so a bad value never errors.
SUPPORTED_LOCALES: tuple[str, ...] = ("en", "en-SG", "zh", "ms", "ta", "id", "th", "vi")
DEFAULT_LOCALE = "en"

# Bahasa Malaysia vs Bahasa Indonesia are close; Grab disambiguates with booking LOCATION, not text.
# We honour an explicit choice but fall a MY-market `id` request back toward `ms` only as a last hop.
_FALLBACK_BASE = {  # locale → its base when the exact tag has no content/catalog
    "en-SG": "en",
}


def normalize_locale(tag: str | None) -> str:
    """Clamp an arbitrary Accept-Language-ish tag to a SUPPORTED locale (else DEFAULT). Case/region
    tolerant: `EN`, `en-US`, `zh-Hans`, `zh_CN` → `en`/`en`/`zh`. Never raises."""
    if not tag:
        return DEFAULT_LOCALE
    t = tag.strip().replace("_", "-")
    if not t:
        return DEFAULT_LOCALE
    # exact supported (case-insensitive) — preserves en-SG
    for loc in SUPPORTED_LOCALES:
        if t.lower() == loc.lower():
            return loc
    # primary subtag (e.g. en-US → en, zh-Hans-CN → zh)
    primary = t.split("-", 1)[0].lower()
    for loc in SUPPORTED_LOCALES:
        if loc.lower() == primary:
            return loc
    return DEFAULT_LOCALE


def _parse_accept_language(header: str | None) -> str | None:
    """First acceptable tag from an Accept-Language header (ignores q-weights ordering nuance — takes
    them in listed order, which browsers already send most-preferred-first)."""
    if not header:
        return None
    for part in header.split(","):
        tag = part.split(";", 1)[0].strip()
        if tag and tag != "*":
            return tag
    return None


def resolve_locale(
    *,
    customer_locale: str | None = None,
    tenant_default: str | None = None,
    accept_language: str | None = None,
    override: str | None = None,
) -> str:
    """The ONE resolution chain (most-specific wins), clamped to a supported locale:
        explicit override (?lang=)  →  the diner's saved Customer.locale  →  tenant default
        (Merchant.settings["locale"])  →  Accept-Language header  →  DEFAULT_LOCALE.
    Takes the first non-empty signal and normalises it (an unsupported tag → DEFAULT, never an error).
    Language is decoupled from currency/timezone — this never consults the outlet."""
    for candidate in (override, customer_locale, tenant_default, _parse_accept_language(accept_language)):
        if candidate:
            return normalize_locale(candidate)
    return DEFAULT_LOCALE


def _translation_chain(locale: str) -> list[str]:
    """Locale + its fallbacks (e.g. en-SG → [en-SG, en]). Used to look through a translations dict."""
    chain = [locale]
    base = _FALLBACK_BASE.get(locale)
    while base and base not in chain:
        chain.append(base)
        base = _FALLBACK_BASE.get(base)
    return chain


def pick(translations: dict | None, locale: str, field: str, canonical: str) -> str:
    """Resolve one localised field: walk locale→fallback in `translations`, else the canonical value.
    `translations` shape = {locale: {field: value}}. A blank/missing entry yields the canonical — a
    diner never sees an empty string or a raw key (Grab's fallback-to-original rule)."""
    if isinstance(translations, dict):
        for loc in _translation_chain(locale):
            entry = translations.get(loc)
            if isinstance(entry, dict):
                val = entry.get(field)
                if isinstance(val, str) and val.strip():
                    return val
    return canonical


def localize_menu(menu, locale: str) -> dict:
    """Build a MenuOut-shaped dict with categories/items localised to `locale` (fallback to canonical).
    The canonical row is never mutated — we emit a plain dict the schema validates. `locale` is assumed
    already resolved/normalised by the caller."""
    return {
        "id": menu.id,
        "name": menu.name,
        "categories": [
            {
                "id": cat.id,
                "name": pick(cat.translations, locale, "name", cat.name),
                "sort_order": cat.sort_order,
                "items": [
                    {
                        "id": it.id,
                        "name": pick(it.translations, locale, "name", it.name),
                        "description": pick(it.translations, locale, "description", it.description),
                        "price": float(it.price),
                        "image_url": it.image_url,
                        "is_available": it.is_available,
                        "modifiers": [
                            {"id": m.id, "name": m.name, "price_delta": float(m.price_delta)}
                            for m in it.modifiers
                        ],
                    }
                    for it in cat.items
                ],
            }
            for cat in menu.categories
        ],
    }
