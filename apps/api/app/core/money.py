"""Money helpers — Decimal with 2dp banker-safe rounding (no float money)."""
from decimal import Decimal, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def to_float(value: Decimal | float | int) -> float:
    """For JSON/graph responses where a number (not string) is expected."""
    return float(money(value))
