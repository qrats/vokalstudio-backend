"""The currency table.

The studio bills in a handful of currencies through PayPal.  Each entry records
how many decimal places the minor unit has, because that is what every
conversion between a provider payload and :class:`~src.domain.money.amount.Money`
depends on.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text

CURRENCIES = {
    "AUD": {"exponent": 2, "symbol": "A$", "name": "Australian dollar"},
    "CAD": {"exponent": 2, "symbol": "C$", "name": "Canadian dollar"},
    "CHF": {"exponent": 2, "symbol": "CHF", "name": "Swiss franc"},
    "DKK": {"exponent": 2, "symbol": "kr", "name": "Danish krone"},
    "EUR": {"exponent": 2, "symbol": "€", "name": "Euro"},
    "GBP": {"exponent": 2, "symbol": "£", "name": "Pound sterling"},
    "JPY": {"exponent": 0, "symbol": "¥", "name": "Japanese yen"},
    "NOK": {"exponent": 2, "symbol": "kr", "name": "Norwegian krone"},
    "SEK": {"exponent": 2, "symbol": "kr", "name": "Swedish krona"},
    "USD": {"exponent": 2, "symbol": "$", "name": "United States dollar"},
}

DEFAULT_CURRENCY = "USD"


def normalize_currency(code, field="currency"):
    """Return the upper-case code after checking it is supported."""
    text = require_text(code, field, min_length=3, max_length=3).upper()
    if text not in CURRENCIES:
        raise ValidationError(
            "{} {} is not supported".format(field, text),
            field=field,
            details={"supported": sorted(CURRENCIES)},
        )
    return text


def exponent(code):
    """Digits after the decimal point for ``code``."""
    return CURRENCIES[normalize_currency(code)]["exponent"]


def minor_units_per_major(code):
    """How many minor units make one major unit, e.g. 100 for USD."""
    return 10 ** exponent(code)


def symbol(code):
    return CURRENCIES[normalize_currency(code)]["symbol"]


def currency_name(code):
    return CURRENCIES[normalize_currency(code)]["name"]


def is_supported(code):
    return isinstance(code, str) and code.strip().upper() in CURRENCIES


def supported_codes():
    return tuple(sorted(CURRENCIES))
