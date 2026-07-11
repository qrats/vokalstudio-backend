"""Daily aggregation of play events."""

from src.domain.analytics.event import COMPLETE, DOWNLOAD, START, deduplicate
from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int
from src.domain.timeline.calendar import date_range, parse_date


class DailyTotals:
    """What happened to one episode on one day."""

    __slots__ = ("day", "starts", "completes", "downloads", "sessions")

    def __init__(self, day, starts=0, completes=0, downloads=0, sessions=0):
        self.day = parse_date(day, "day")
        self.starts = require_int(starts, "starts", minimum=0)
        self.completes = require_int(completes, "completes", minimum=0)
        self.downloads = require_int(downloads, "downloads", minimum=0)
        self.sessions = require_int(sessions, "sessions", minimum=0)
        if self.completes > self.starts:
            raise ValidationError(
                "completes cannot exceed starts", field="completes"
            )

    @property
    def completion_rate(self):
        if self.starts == 0:
            return 0.0
        return round(self.completes * 100.0 / self.starts, 2)

    def plus(self, other):
        return DailyTotals(
            self.day,
            self.starts + other.starts,
            self.completes + other.completes,
            self.downloads + other.downloads,
            self.sessions + other.sessions,
        )

    def to_dict(self):
        return {
            "day": self.day.isoformat(),
            "starts": self.starts,
            "completes": self.completes,
            "downloads": self.downloads,
            "sessions": self.sessions,
            "completion_rate": self.completion_rate,
        }

    def __eq__(self, other):
        return isinstance(other, DailyTotals) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("totals", self.day, self.starts, self.completes, self.downloads))

    def __repr__(self):
        return "DailyTotals({}, {} starts)".format(self.day.isoformat(), self.starts)


def daily(events, reference=None):
    """Roll a stream of events up per day, oldest first."""
    wanted = [
        event
        for event in deduplicate(events)
        if reference is None or event.episode_reference == reference
    ]
    buckets = {}
    seen_sessions = {}
    for event in wanted:
        day = event.day()
        record = buckets.setdefault(day, {"starts": 0, "completes": 0, "downloads": 0})
        if event.kind == START:
            record["starts"] += 1
        elif event.kind == COMPLETE:
            record["completes"] += 1
        elif event.kind == DOWNLOAD:
            record["downloads"] += 1
        seen_sessions.setdefault(day, set()).add(event.session_id)
    return tuple(
        DailyTotals(
            day,
            record["starts"],
            record["completes"],
            record["downloads"],
            len(seen_sessions[day]),
        )
        for day, record in sorted(buckets.items())
    )


def fill_gaps(totals, start, end):
    """Insert zero rows so a chart has one point per day."""
    by_day = {row.day.isoformat(): row for row in totals}
    return tuple(
        by_day.get(day.isoformat(), DailyTotals(day)) for day in date_range(start, end)
    )


def combine(totals):
    """Sum a run of daily rows into one, dated on the first day."""
    materialised = tuple(totals)
    if not materialised:
        return None
    running = materialised[0]
    for row in materialised[1:]:
        running = running.plus(row)
    return running


def busiest(totals, default=None):
    ordered = sorted(totals, key=lambda row: (row.starts, row.day.isoformat()))
    return ordered[-1] if ordered else default


def moving_average(totals, window=7):
    """Trailing average of starts, one value per row."""
    size = require_int(window, "window", minimum=1)
    values = [row.starts for row in totals]
    averages = []
    for index in range(len(values)):
        chunk = values[max(0, index - size + 1): index + 1]
        averages.append(round(sum(chunk) / len(chunk), 2))
    return tuple(averages)
