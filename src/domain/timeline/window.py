"""Recurring broadcast windows.

A show that goes live "every Tuesday at 19:00 for 90 minutes" is described by a
:class:`Window`; expanding one over a date range produces the intervals the
scheduler and the server allocator work with.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_sequence, require_text
from src.domain.timeline.calendar import date_range, parse_date
from src.domain.timeline.duration import Duration, coerce_duration
from src.domain.timeline.instant import Instant
from src.domain.timeline.interval import Interval

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def parse_weekday(value, field="weekday"):
    if isinstance(value, int) and not isinstance(value, bool):
        return require_int(value, field, minimum=0, maximum=6)
    name = require_text(value, field).strip().lower()[:3]
    if name not in WEEKDAYS:
        raise ValidationError(
            "{} must be one of {}".format(field, ", ".join(WEEKDAYS)), field=field
        )
    return WEEKDAYS.index(name)


def parse_time_of_day(value, field="time"):
    """Parse ``HH:MM`` into whole minutes past midnight."""
    raw = require_text(value, field)
    parts = raw.split(":")
    if len(parts) != 2:
        raise ValidationError("{} must look like HH:MM".format(field), field=field)
    try:
        hours, minutes = (int(part, 10) for part in parts)
    except ValueError:
        raise ValidationError("{} must look like HH:MM".format(field), field=field) from None
    if not 0 <= hours <= 23 or not 0 <= minutes <= 59:
        raise ValidationError("{} is out of range".format(field), field=field)
    return hours * 60 + minutes


def format_time_of_day(minutes):
    total = require_int(minutes, "minutes", minimum=0, maximum=24 * 60 - 1)
    return "{:02d}:{:02d}".format(total // 60, total % 60)


class Window:
    """A weekly recurring slot of a fixed length."""

    __slots__ = ("weekdays", "start_minute", "duration", "label")

    def __init__(self, weekdays, start_time, duration, label=None):
        days = require_sequence(weekdays, "weekdays", min_length=1)
        self.weekdays = tuple(sorted({parse_weekday(day) for day in days}))
        self.start_minute = parse_time_of_day(start_time, "start_time")
        self.duration = coerce_duration(duration, "duration")
        if self.duration.is_zero():
            raise ValidationError("duration must be positive", field="duration")
        if self.duration.millis > 24 * 3600 * 1000:
            raise ValidationError("duration must fit in a day", field="duration")
        self.label = require_text(label, "label", max_length=80) if label else None

    def occurs_on(self, day):
        return parse_date(day).weekday() in self.weekdays

    def interval_on(self, day):
        """The interval this window covers on ``day``, or ``None``."""
        target = parse_date(day)
        if target.weekday() not in self.weekdays:
            return None
        midnight = Instant.parse(target.isoformat() + "T00:00:00Z")
        start = midnight.plus_minutes(self.start_minute)
        return Interval.starting(start, self.duration)

    def expand(self, start, end):
        """Every occurrence whose day falls in ``[start, end)``."""
        spans = []
        for day in date_range(start, end):
            span = self.interval_on(day)
            if span is not None:
                spans.append(span)
        return tuple(spans)

    def weekly_load(self):
        """Total broadcast time per week."""
        return Duration(self.duration.millis * len(self.weekdays))

    def to_dict(self):
        payload = {
            "weekdays": [WEEKDAYS[day] for day in self.weekdays],
            "start_time": format_time_of_day(self.start_minute),
            "duration_millis": self.duration.millis,
        }
        if self.label:
            payload["label"] = self.label
        return payload

    def __eq__(self, other):
        return (
            isinstance(other, Window)
            and other.weekdays == self.weekdays
            and other.start_minute == self.start_minute
            and other.duration == self.duration
        )

    def __hash__(self):
        return hash(("window", self.weekdays, self.start_minute, self.duration.millis))

    def __repr__(self):
        return "Window({}, {})".format(
            ",".join(WEEKDAYS[day] for day in self.weekdays),
            format_time_of_day(self.start_minute),
        )


def schedule_conflicts(windows, start, end):
    """Return the pairs of window indexes that collide inside a date range."""
    expanded = [window.expand(start, end) for window in windows]
    clashes = []
    for left in range(len(expanded)):
        for right in range(left + 1, len(expanded)):
            if any(
                one.overlaps(two) for one in expanded[left] for two in expanded[right]
            ):
                clashes.append((left, right))
    return tuple(clashes)


def busiest_day(windows, start, end):
    """The day in the range with the most scheduled milliseconds."""
    totals = {}
    for window in windows:
        for span in window.expand(start, end):
            day = span.start.to_date()
            totals[day] = totals.get(day, 0) + span.duration.millis
    if not totals:
        return None
    ordered = sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))
    return ordered[0][0]
