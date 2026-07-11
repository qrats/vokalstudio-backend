"""Playback events.

The player posts one event per meaningful moment.  They arrive out of order and
sometimes twice, so an event carries enough to be de-duplicated without a
database lookup.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_choice, require_int, require_text
from src.domain.core.ids import derive_id
from src.domain.timeline.instant import coerce_instant

START = "start"
PROGRESS = "progress"
COMPLETE = "complete"
DOWNLOAD = "download"

KINDS = (START, PROGRESS, COMPLETE, DOWNLOAD)
LISTEN_KINDS = (START, PROGRESS, COMPLETE)

SOURCES = ("web", "ios", "android", "rss", "embed", "unknown")


class PlayEvent:
    """One reported playback moment."""

    __slots__ = ("episode_reference", "session_id", "kind", "at", "position_millis", "source")

    def __init__(
        self,
        episode_reference,
        session_id,
        kind,
        at,
        position_millis=0,
        source="unknown",
    ):
        self.episode_reference = require_text(
            episode_reference, "episode_reference", max_length=64
        )
        self.session_id = require_text(session_id, "session_id", max_length=64)
        self.kind = require_choice(kind, "kind", KINDS)
        self.at = coerce_instant(at, "at")
        self.position_millis = require_int(position_millis, "position_millis", minimum=0)
        self.source = require_choice(source, "source", SOURCES)
        if self.kind == DOWNLOAD and self.position_millis:
            raise ValidationError(
                "a download has no position", field="position_millis"
            )

    @property
    def fingerprint(self):
        """What makes two reports of the same moment identical."""
        return derive_id(
            "play",
            self.episode_reference,
            self.session_id,
            self.kind,
            self.position_millis,
        )

    @property
    def is_listen(self):
        return self.kind in LISTEN_KINDS

    def day(self):
        return self.at.to_date()

    def to_dict(self):
        return {
            "episode_reference": self.episode_reference,
            "session_id": self.session_id,
            "kind": self.kind,
            "at": self.at.to_iso(),
            "position_millis": self.position_millis,
            "source": self.source,
            "fingerprint": self.fingerprint,
        }

    def __eq__(self, other):
        return isinstance(other, PlayEvent) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("event", self.fingerprint, self.at.millis))

    def __repr__(self):
        return "PlayEvent({}, {})".format(self.kind, self.position_millis)


def deduplicate(events):
    """Drop repeated reports, keeping the earliest of each."""
    ordered = sorted(events, key=lambda event: event.at.millis)
    seen = set()
    kept = []
    for event in ordered:
        if event.fingerprint in seen:
            continue
        seen.add(event.fingerprint)
        kept.append(event)
    return tuple(kept)


def for_episode(events, reference):
    return tuple(event for event in events if event.episode_reference == reference)


def sessions(events):
    """The distinct session ids present, sorted."""
    return tuple(sorted({event.session_id for event in events}))


def furthest_position(events, session_id):
    """How far one listener got, in milliseconds."""
    positions = [
        event.position_millis
        for event in events
        if event.session_id == session_id and event.is_listen
    ]
    return max(positions) if positions else 0
