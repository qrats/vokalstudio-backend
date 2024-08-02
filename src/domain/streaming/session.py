"""Live sessions.

A session is one broadcast: it is scheduled, it starts, it may drop and
reconnect, and it ends.  Minutes are billed from the intervals it was actually
connected for, not from the wall-clock span, which is why the connections are
kept rather than a single start and end.
"""

from src.domain.core.errors import StateError, ValidationError
from src.domain.core.guards import require_choice, require_text
from src.domain.core.ids import derive_id
from src.domain.timeline.duration import Duration
from src.domain.timeline.instant import coerce_instant
from src.domain.timeline.interval import Interval, merge_overlapping, total_covered

SCHEDULED = "scheduled"
LIVE = "live"
INTERRUPTED = "interrupted"
ENDED = "ended"
ABANDONED = "abandoned"

STATES = (SCHEDULED, LIVE, INTERRUPTED, ENDED, ABANDONED)

TRANSITIONS = {
    SCHEDULED: (LIVE, ABANDONED),
    LIVE: (INTERRUPTED, ENDED),
    INTERRUPTED: (LIVE, ENDED, ABANDONED),
    ENDED: (),
    ABANDONED: (),
}


class LiveSession:
    """One broadcast and the intervals it was connected for."""

    __slots__ = ("user_id", "title", "state", "connections", "opened_at")

    def __init__(self, user_id, title, opened_at, state=SCHEDULED, connections=()):
        self.user_id = require_text(user_id, "user_id", max_length=64)
        self.title = require_text(title, "title", max_length=200)
        self.opened_at = coerce_instant(opened_at, "opened_at")
        self.state = require_choice(state, "state", STATES)
        spans = tuple(connections)
        for span in spans:
            if not isinstance(span, Interval):
                raise ValidationError("connections must be intervals", field="connections")
            if span.start < self.opened_at:
                raise ValidationError(
                    "a connection precedes the session", field="connections"
                )
        self.connections = tuple(
            sorted(spans, key=lambda span: span.start.millis)
        )

    @property
    def reference(self):
        return derive_id("session", self.user_id, self.opened_at.millis)

    def _copy(self, **changes):
        payload = {
            "user_id": self.user_id,
            "title": self.title,
            "opened_at": self.opened_at,
            "state": self.state,
            "connections": self.connections,
        }
        payload.update(changes)
        return LiveSession(**payload)

    def _moved_to(self, target):
        if target not in TRANSITIONS[self.state]:
            raise StateError(
                "cannot move a {} session to {}".format(self.state, target),
                current=self.state,
                attempted=target,
            )
        return target

    def go_live(self, at, until):
        """Record a connection and mark the session live."""
        state = self._moved_to(LIVE)
        span = Interval(coerce_instant(at, "at"), coerce_instant(until, "until"))
        if span.is_empty():
            raise ValidationError("a connection must have length", field="until")
        if span.start < self.opened_at:
            raise ValidationError("a connection precedes the session", field="at")
        return self._copy(state=state, connections=self.connections + (span,))

    def interrupt(self):
        return self._copy(state=self._moved_to(INTERRUPTED))

    def end(self):
        return self._copy(state=self._moved_to(ENDED))

    def abandon(self):
        return self._copy(state=self._moved_to(ABANDONED))

    def connected_duration(self):
        """Time actually on air, counting overlapping reconnects once."""
        if not self.connections:
            return Duration.zero()
        return total_covered(self.connections)

    def billable_minutes(self):
        """Connected time rounded up to whole minutes."""
        millis = self.connected_duration().millis
        return -(-millis // 60000)

    def span(self):
        """The wall-clock interval from first connection to last, if any."""
        if not self.connections:
            return None
        merged = merge_overlapping(self.connections)
        return Interval(merged[0].start, merged[-1].end)

    def drop_count(self):
        """How many times the stream reconnected after a break."""
        return max(0, len(merge_overlapping(self.connections)) - 1)

    def is_finished(self):
        return self.state in (ENDED, ABANDONED)

    def to_dict(self):
        return {
            "reference": self.reference,
            "user_id": self.user_id,
            "title": self.title,
            "state": self.state,
            "opened_at": self.opened_at.to_iso(),
            "connections": [span.to_dict() for span in self.connections],
            "connected_millis": self.connected_duration().millis,
            "billable_minutes": self.billable_minutes(),
        }

    def __eq__(self, other):
        return isinstance(other, LiveSession) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("session", self.reference, self.state))

    def __repr__(self):
        return "LiveSession({!r}, {})".format(self.title, self.state)


def monthly_minutes(sessions, year, month):
    """Billable minutes across the sessions that started in one month."""
    prefix = "{:04d}-{:02d}".format(year, month)
    total = 0
    for session in sessions:
        if session.opened_at.to_date().startswith(prefix):
            total += session.billable_minutes()
    return total


def longest(sessions, default=None):
    ordered = sorted(sessions, key=lambda item: item.connected_duration().millis)
    return ordered[-1] if ordered else default
