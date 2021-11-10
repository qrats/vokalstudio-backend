"""Half-open intervals ``[start, end)`` over :class:`Instant`.

Live sessions, ad breaks and server reservations are all intervals, and the
question asked of them is nearly always "do these two overlap".
"""

from src.domain.core.errors import ValidationError
from src.domain.timeline.duration import Duration
from src.domain.timeline.instant import Instant, coerce_instant


class Interval:
    """A half-open span of time; ``end`` is never part of the interval."""

    __slots__ = ("start", "end")

    def __init__(self, start, end):
        self.start = coerce_instant(start, "start")
        self.end = coerce_instant(end, "end")
        if self.end.millis < self.start.millis:
            raise ValidationError("end must not precede start", field="end")

    @classmethod
    def starting(cls, start, duration):
        begin = coerce_instant(start, "start")
        if not isinstance(duration, Duration):
            duration = Duration(duration)
        return cls(begin, begin.plus_millis(duration.millis))

    @property
    def duration(self):
        return Duration(self.end.millis - self.start.millis)

    def is_empty(self):
        return self.start.millis == self.end.millis

    def contains(self, moment):
        point = coerce_instant(moment, "moment")
        return self.start.millis <= point.millis < self.end.millis

    def overlaps(self, other):
        if self.is_empty() or other.is_empty():
            return False
        return self.start.millis < other.end.millis and other.start.millis < self.end.millis

    def touches(self, other):
        return self.end.millis == other.start.millis or other.end.millis == self.start.millis

    def intersection(self, other):
        start = max(self.start.millis, other.start.millis)
        end = min(self.end.millis, other.end.millis)
        if end < start:
            return None
        return Interval(Instant(start), Instant(end))

    def union(self, other):
        if not self.overlaps(other) and not self.touches(other):
            raise ValidationError("intervals are disjoint", field="other")
        return Interval(
            Instant(min(self.start.millis, other.start.millis)),
            Instant(max(self.end.millis, other.end.millis)),
        )

    def shift(self, millis):
        return Interval(self.start.plus_millis(millis), self.end.plus_millis(millis))

    def to_dict(self):
        return {"start": self.start.to_iso(), "end": self.end.to_iso()}

    def __eq__(self, other):
        return (
            isinstance(other, Interval)
            and other.start == self.start
            and other.end == self.end
        )

    def __hash__(self):
        return hash(("interval", self.start.millis, self.end.millis))

    def __repr__(self):
        return "Interval({}, {})".format(self.start.to_iso(), self.end.to_iso())


def merge_overlapping(intervals):
    """Collapse overlapping or touching intervals into the fewest possible."""
    ordered = sorted(intervals, key=lambda span: (span.start.millis, span.end.millis))
    merged = []
    for span in ordered:
        if merged and (merged[-1].overlaps(span) or merged[-1].touches(span)):
            merged[-1] = merged[-1].union(span)
        else:
            merged.append(span)
    return tuple(merged)


def find_conflicts(intervals):
    """Return every pair of indexes whose intervals overlap."""
    materialised = tuple(intervals)
    conflicts = []
    for left in range(len(materialised)):
        for right in range(left + 1, len(materialised)):
            if materialised[left].overlaps(materialised[right]):
                conflicts.append((left, right))
    return tuple(conflicts)


def total_covered(intervals):
    """Total time covered by ``intervals``, counting overlaps only once."""
    millis = 0
    for span in merge_overlapping(intervals):
        millis += span.duration.millis
    return Duration(millis)


def gaps(intervals, within):
    """Return the parts of ``within`` that no interval covers."""
    covered = [
        span
        for span in merge_overlapping(intervals)
        if span.overlaps(within)
    ]
    cursor = within.start.millis
    holes = []
    for span in covered:
        start = max(span.start.millis, within.start.millis)
        if start > cursor:
            holes.append(Interval(Instant(cursor), Instant(start)))
        cursor = max(cursor, min(span.end.millis, within.end.millis))
    if cursor < within.end.millis:
        holes.append(Interval(Instant(cursor), within.end))
    return tuple(holes)
