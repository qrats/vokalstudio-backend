"""Exact money handling: integer minor units, never floats."""

from src.domain.money.allocation import (
    allocate_by_ratios,
    allocate_by_weights,
    prorate,
    reconcile,
    remaining_credit,
    split_evenly,
)
from src.domain.money.amount import Money, maximum, minimum, total
from src.domain.money.currency import (
    CURRENCIES,
    DEFAULT_CURRENCY,
    currency_name,
    exponent,
    is_supported,
    minor_units_per_major,
    normalize_currency,
    supported_codes,
    symbol,
)
from src.domain.money.rounding import (
    CEILING,
    DOWN,
    FLOOR,
    HALF_EVEN,
    HALF_UP,
    UP,
    apply_rate,
    round_division,
)
from src.domain.money.taxes import TaxRate, ZERO_RATE, combined

__all__ = [
    "CEILING",
    "CURRENCIES",
    "DEFAULT_CURRENCY",
    "DOWN",
    "FLOOR",
    "HALF_EVEN",
    "HALF_UP",
    "Money",
    "TaxRate",
    "UP",
    "ZERO_RATE",
    "allocate_by_ratios",
    "allocate_by_weights",
    "apply_rate",
    "combined",
    "currency_name",
    "exponent",
    "is_supported",
    "maximum",
    "minimum",
    "minor_units_per_major",
    "normalize_currency",
    "prorate",
    "reconcile",
    "remaining_credit",
    "round_division",
    "split_evenly",
    "supported_codes",
    "symbol",
    "total",
]
