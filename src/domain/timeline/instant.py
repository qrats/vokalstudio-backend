"""UTC instants.

The domain never reads the clock: every function that needs "now" takes it as
an argument.  :class:`Instant` is the type those arguments use.  It wraps a
whole number of milliseconds since the Unix epoch so that serialisation is
lossless and comparisons are exact.
"""

import datetime

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_text

EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
MILLIS_PER_SECOND = 1000
MILLIS_PER_MINUTE = 60 * MILLIS_PER_SECOND
MILLIS_PER_HOUR = 60 * MILLIS_PER_MINUTE
MILLIS_PER_DAY = 24 * MILLIS_PER_HOUR


class Instant:
    """A point in time, stored as milliseconds since the Unix epoch."""

    __slots__ = ("millis",)

    def __init__(self, millis):
        self.millis = require_int(millis, "millis")

    @classmethod
    def from_seconds(cls, seconds):
        return cls(int(round(float(seconds) * MILLIS_PER_SECOND)))

    @classmethod
    def from_datetime(cls, value):
        if not isinstance(value, datetime.datetime):
            raise ValidationError("value must be a datetime", field="value")
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        delta = value.astimezone(datetime.timezone.utc) - EPOCH
        return cls(int(delta.total_seconds() * MILLIS_PER_SECOND))

    @classmethod
    def parse(cls, text, field="instant"):
        """Parse an ISO-8601 timestamp; a trailing ``Z`` is accepted."""
        raw = require_text(text, field)
        candidate = raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
        try:
            parsed = datetime.datetime.fromisoformat(candidate)
        except ValueError:
            raise ValidationError(
                "{} is not an ISO-8601 timestamp".format(field), field=field
            ) from None
        return cls.from_datetime(parsed)

    def to_datetime(self):
        return EPOCH + datetime.timedelta(milliseconds=self.millis)

    def to_iso(self):
        moment = self.to_datetime()
        if self.millis % MILLIS_PER_SECOND:
            return moment.strftime("%Y-%m-%dT%H:%M:%S.") + "{:03d}Z".format(
                self.millis % MILLIS_PER_SECOND
            )
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_date(self):
        return self.to_datetime().date().isoformat()

    def plus_millis(self, millis):
        return Instant(self.millis + require_int(millis, "millis"))

    def plus_seconds(self, seconds):
        return self.plus_millis(require_int(seconds, "seconds") * MILLIS_PER_SECOND)

    def plus_minutes(self, minutes):
        return self.plus_millis(require_int(minutes, "minutes") * MILLIS_PER_MINUTE)

    def plus_hours(self, hours):
        return self.plus_millis(require_int(hours, "hours") * MILLIS_PER_HOUR)

    def plus_days(self, days):
        return self.plus_millis(require_int(days, "days") * MILLIS_PER_DAY)

    def difference_millis(self, other):
        return self.millis - _as_instant(other).millis

    def is_before(self, other):
        return self.millis < _as_instant(other).millis

    def is_after(self, other):
        return self.millis > _as_instant(other).millis

    def floor_to_day(self):
        return Instant(self.millis - (self.millis % MILLIS_PER_DAY))

    def floor_to_hour(self):
        return Instant(self.millis - (self.millis % MILLIS_PER_HOUR))

    def to_dict(self):
        return {"millis": self.millis, "iso": self.to_iso()}

    def __eq__(self, other):
        return isinstance(other, Instant) and other.millis == self.millis

    def __lt__(self, other):
        return self.millis < _as_instant(other).millis

    def __le__(self, other):
        return self.millis <= _as_instant(other).millis

    def __gt__(self, other):
        return self.millis > _as_instant(other).millis

    def __ge__(self, other):
        return self.millis >= _as_instant(other).millis

    def __hash__(self):
        return hash(("instant", self.millis))

    def __repr__(self):
        return "Instant({})".format(self.to_iso())


def _as_instant(value):
    if isinstance(value, Instant):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Instant(value)
    if isinstance(value, str):
        return Instant.parse(value)
    raise ValidationError("value must be an Instant", field="value")


def coerce_instant(value, field="instant"):
    """Accept an :class:`Instant`, epoch millis, ISO text or ``datetime``."""
    if isinstance(value, Instant):
        return value
    if isinstance(value, datetime.datetime):
        return Instant.from_datetime(value)
    if isinstance(value, str):
        return Instant.parse(value, field)
    if isinstance(value, int) and not isinstance(value, bool):
        return Instant(value)
    raise ValidationError("{} must be a timestamp".format(field), field=field)


def earliest(instants, default=None):
    ordered = sorted(coerce_instant(value) for value in instants)
    return ordered[0] if ordered else default


def latest(instants, default=None):
    ordered = sorted(coerce_instant(value) for value in instants)
    return ordered[-1] if ordered else default
