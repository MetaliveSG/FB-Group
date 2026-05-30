"""Phone normalization → canonical E.164, region-aware (Google libphonenumber).

Store ONE canonical format (E.164 *with* the leading '+', e.g. '+6591780055'); each
SMS/WhatsApp gateway adapter reformats on send (some want '65…' not '+65…' → just
`lstrip('+')`). Parsing is region-aware so national trunk prefixes are handled
correctly — e.g. a Malaysian '0161234567' with region MY becomes '+60161234567'
(the leading trunk '0' is dropped); naive '+60' + '016…' would be invalid.
"""
from __future__ import annotations

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

DEFAULT_REGION = "SG"
# Regions the country-code picker offers (kept in sync with the frontend list).
SUPPORTED_REGIONS = ("SG", "MY", "ID", "TH")


def to_e164(raw: str | None, region: str = DEFAULT_REGION) -> str | None:
    """Normalize a user-entered number to canonical E.164 for the given region.

    - None  → None (field omitted — caller decides whether that's allowed)
    - blank → ValueError (present-but-empty is rejected)
    - parsed against `region` (so '0161234567'+MY → '+60161234567'); already-'+'
      international input is honored as-is
    - invalid for that region → ValueError (→ 422 at the schema boundary)
    """
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        raise ValueError("Mobile number is required")
    region = (region or DEFAULT_REGION).upper()
    try:
        parsed = phonenumbers.parse(raw, region)
    except NumberParseException:
        raise ValueError("Enter a valid mobile number")
    # is_possible (length/structure) rather than is_valid (assigned-range): accepts
    # well-formed numbers libphonenumber doesn't yet know are assigned — and the PoC's
    # synthetic demo numbers — while still rejecting wrong-length / non-numeric input.
    if not phonenumbers.is_possible_number(parsed):
        raise ValueError("Enter a valid mobile number")
    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
