"""Durations measured in whole milliseconds.

Episode lengths, intro beds and advertisement breaks are all durations, and
they are added together often enough that a dedicated type is worth it.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_text

MILLIS_PER_SECOND = 1000
MILLIS_PER_MINUTE = 60 * MILLIS_PER_SECOND
MILLIS_PER_HOUR = 60 * MILLIS_PER_MINUTE


class Duration:
    """A non-negative length of time."""

    __slots__ = ("millis",)

    def __init__(self, millis):
        self.millis = require_int(millis, "millis", minimum=0)

    @classmethod
    def zero(cls):
        return cls(0)

    @classmethod
    def of_seconds(cls, seconds):
        return cls(require_int(seconds, "seconds", minimum=0) * MILLIS_PER_SECOND)

    @classmethod
    def of_minutes(cls, minutes):
        return cls(require_int(minutes, "minutes", minimum=0) * MILLIS_PER_MINUTE)

    @classmethod
    def of_hours(cls, hours):
        return cls(require_int(hours, "hours", minimum=0) * MILLIS_PER_HOUR)

    @classmethod
    def parse(cls, text, field="duration"):
        """Parse ``HH:MM:SS``, ``MM:SS`` or either with ``.mmm`` attached."""
        raw = require_text(text, field)
        body, _, fraction = raw.partition(".")
        parts = body.split(":")
        if len(parts) not in (2, 3):
            raise ValidationError(
                "{} must look like HH:MM:SS".format(field), field=field
            )
        try:
            numbers = [int(part, 10) for part in parts]
        except ValueError:
            raise ValidationError(
                "{} must look like HH:MM:SS".format(field), field=field
            ) from None
        if any(number < 0 for number in numbers):
            raise ValidationError("{} must not be negative".format(field), field=field)
        if len(numbers) == 2:
            numbers = [0] + numbers
        hours, minutes, seconds = numbers
        if minutes > 59 or seconds > 59:
            raise ValidationError(
                "{} has an out of range component".format(field), field=field
            )
        millis = hours * MILLIS_PER_HOUR + minutes * MILLIS_PER_MINUTE
        millis += seconds * MILLIS_PER_SECOND
        if fraction:
            if not fraction.isdigit() or len(fraction) > 3:
                raise ValidationError(
                    "{} has an invalid fraction".format(field), field=field
                )
            millis += int(fraction.ljust(3, "0"), 10)
        return cls(millis)

    @property
    def seconds(self):
        return self.millis // MILLIS_PER_SECOND

    @property
    def whole_minutes(self):
        return self.millis // MILLIS_PER_MINUTE

    def plus(self, other):
        return Duration(self.millis + _as_duration(other).millis)

    def minus(self, other):
        difference = self.millis - _as_duration(other).millis
        if difference < 0:
            raise ValidationError("duration would go negative", field="duration")
        return Duration(difference)

    def times(self, factor):
        return Duration(self.millis * require_int(factor, "factor", minimum=0))

    def is_zero(self):
        return self.millis == 0

    def format(self, always_hours=False, millis=False):
        total = self.millis
        hours = total // MILLIS_PER_HOUR
        minutes = (total % MILLIS_PER_HOUR) // MILLIS_PER_MINUTE
        seconds = (total % MILLIS_PER_MINUTE) // MILLIS_PER_SECOND
        if hours or always_hours:
            body = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
        else:
            body = "{:02d}:{:02d}".format(minutes, seconds)
        if millis:
            body += ".{:03d}".format(total % MILLIS_PER_SECOND)
        return body

    def to_dict(self):
        return {"millis": self.millis, "formatted": self.format()}

    def __eq__(self, other):
        return isinstance(other, Duration) and other.millis == self.millis

    def __lt__(self, other):
        return self.millis < _as_duration(other).millis

    def __le__(self, other):
        return self.millis <= _as_duration(other).millis

    def __gt__(self, other):
        return self.millis > _as_duration(other).millis

    def __ge__(self, other):
        return self.millis >= _as_duration(other).millis

    def __hash__(self):
        return hash(("duration", self.millis))

    def __repr__(self):
        return "Duration({})".format(self.format(millis=True))


def _as_duration(value):
    if isinstance(value, Duration):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Duration(value)
    if isinstance(value, str):
        return Duration.parse(value)
    raise ValidationError("value must be a Duration", field="value")


def coerce_duration(value, field="duration"):
    """Accept a :class:`Duration`, whole millis or ``HH:MM:SS`` text."""
    if isinstance(value, Duration):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Duration(require_int(value, field, minimum=0))
    if isinstance(value, str):
        return Duration.parse(value, field)
    raise ValidationError("{} must be a duration".format(field), field=field)


def total(durations):
    """Sum a sequence of durations."""
    millis = 0
    for value in durations:
        millis += coerce_duration(value).millis
    return Duration(millis)
