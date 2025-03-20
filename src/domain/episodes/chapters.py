"""Chapter markers.

Markers are offsets into the finished episode with a title attached.  They have
to be strictly increasing, they may not sit past the end, and the first one has
to be at zero for the players that assume it -- all three of which the API used
to accept and then fail on export.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_text
from src.domain.timeline.duration import Duration


class Chapter:
    """One marker."""

    __slots__ = ("start_millis", "title", "url", "image_key")

    def __init__(self, start_millis, title, url=None, image_key=None):
        self.start_millis = require_int(start_millis, "start_millis", minimum=0)
        self.title = require_text(title, "title", max_length=128)
        self.url = require_text(url, "url", max_length=500) if url else None
        self.image_key = (
            require_text(image_key, "image_key", max_length=255) if image_key else None
        )

    @property
    def start(self):
        return Duration(self.start_millis)

    def shifted(self, millis):
        return Chapter(
            self.start_millis + require_int(millis, "millis"),
            self.title,
            self.url,
            self.image_key,
        )

    def to_dict(self):
        return {
            "startTime": self.start_millis // 1000,
            "start_millis": self.start_millis,
            "title": self.title,
            "url": self.url,
            "img": self.image_key,
        }

    def __eq__(self, other):
        return isinstance(other, Chapter) and other.to_dict() == self.to_dict()

    def __lt__(self, other):
        return self.start_millis < other.start_millis

    def __hash__(self):
        return hash(("chapter", self.start_millis, self.title))

    def __repr__(self):
        return "Chapter({}, {!r})".format(self.start.format(), self.title)


def validate_chapters(chapters, duration_millis=None):
    """Check a whole marker list and return it in order."""
    ordered = tuple(sorted(chapters))
    if not ordered:
        return ordered
    if ordered[0].start_millis != 0:
        raise ValidationError("the first chapter must start at zero", field="chapters")
    seen = set()
    for chapter in ordered:
        if chapter.start_millis in seen:
            raise ValidationError(
                "two chapters share a start time", field="chapters"
            )
        seen.add(chapter.start_millis)
        if duration_millis is not None and chapter.start_millis >= duration_millis:
            raise ValidationError(
                "a chapter starts past the end of the episode", field="chapters"
            )
    return ordered


def chapter_lengths(chapters, duration_millis):
    """How long each chapter runs for, given the episode length."""
    ordered = validate_chapters(chapters, duration_millis)
    lengths = []
    for index, chapter in enumerate(ordered):
        end = (
            ordered[index + 1].start_millis
            if index + 1 < len(ordered)
            else require_int(duration_millis, "duration_millis", minimum=1)
        )
        lengths.append(Duration(end - chapter.start_millis))
    return tuple(lengths)


def chapter_at(chapters, offset_millis):
    """The chapter covering an offset, or ``None`` before the first one."""
    found = None
    for chapter in sorted(chapters):
        if chapter.start_millis <= offset_millis:
            found = chapter
        else:
            break
    return found


def shift_all(chapters, millis):
    """Move every marker, which is what adding an intro does."""
    return tuple(sorted(chapter.shifted(millis) for chapter in chapters))
