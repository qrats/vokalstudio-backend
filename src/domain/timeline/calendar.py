"""Civil dates and billing anniversaries.

Subscriptions renew on a calendar day, not on a fixed number of milliseconds,
so plan arithmetic goes through here rather than through :mod:`instant`.
"""

import datetime

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_text

DAYS_IN_WEEK = 7
MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


def parse_date(value, field="date"):
    """Parse a ``YYYY-MM-DD`` calendar day."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    raw = require_text(value, field)
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        raise ValidationError(
            "{} must look like YYYY-MM-DD".format(field), field=field
        ) from None


def format_date(value):
    return parse_date(value).isoformat()


def days_in_month(year, month):
    require_int(year, "year", minimum=1)
    require_int(month, "month", minimum=1, maximum=12)
    if month == 12:
        return 31
    first = datetime.date(year, month, 1)
    following = datetime.date(year, month + 1, 1)
    return (following - first).days


def add_days(value, days):
    return parse_date(value) + datetime.timedelta(days=require_int(days, "days"))


def add_months(value, months):
    """Add whole months, clamping onto the last day of a shorter month."""
    start = parse_date(value)
    count = require_int(months, "months")
    index = start.year * 12 + (start.month - 1) + count
    year, month = divmod(index, 12)
    month += 1
    day = min(start.day, days_in_month(year, month))
    return datetime.date(year, month, day)


def add_years(value, years):
    return add_months(value, require_int(years, "years") * 12)


def days_between(start, end):
    return (parse_date(end) - parse_date(start)).days


def is_leap_year(year):
    require_int(year, "year", minimum=1)
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def week_start(value, first_weekday=0):
    """Return the first day of the week containing ``value``."""
    require_int(first_weekday, "first_weekday", minimum=0, maximum=6)
    day = parse_date(value)
    offset = (day.weekday() - first_weekday) % DAYS_IN_WEEK
    return day - datetime.timedelta(days=offset)


def month_start(value):
    day = parse_date(value)
    return datetime.date(day.year, day.month, 1)


def month_end(value):
    day = parse_date(value)
    return datetime.date(day.year, day.month, days_in_month(day.year, day.month))


def anniversary_day(value):
    """The day-of-month a subscription anchored on ``value`` renews on."""
    return parse_date(value).day


def next_anniversary(anchor, after, months=1):
    """Return the first anniversary of ``anchor`` strictly after ``after``."""
    start = parse_date(anchor, "anchor")
    cursor_after = parse_date(after, "after")
    step = require_int(months, "months", minimum=1)
    if cursor_after < start:
        return start
    elapsed = (cursor_after.year - start.year) * 12 + (cursor_after.month - start.month)
    periods = max(0, elapsed // step)
    candidate = add_months(start, periods * step)
    while candidate <= cursor_after:
        periods += 1
        candidate = add_months(start, periods * step)
    return candidate


def date_range(start, end):
    """Every day in ``[start, end)``."""
    first = parse_date(start, "start")
    last = parse_date(end, "end")
    if last < first:
        raise ValidationError("end must not precede start", field="end")
    days = []
    cursor = first
    while cursor < last:
        days.append(cursor)
        cursor += datetime.timedelta(days=1)
    return tuple(days)


def month_name(month):
    return MONTHS[require_int(month, "month", minimum=1, maximum=12) - 1]
