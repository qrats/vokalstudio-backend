"""Show notes.

Stored as markdown, delivered as HTML-ish text and as a plain summary.  The
rendering is deliberately small: the destinations disagree about what they
accept, so anything clever would have to be undone per destination.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_text
from src.domain.core.text import (
    extract_links,
    normalize_whitespace,
    reading_time_seconds,
    strip_markup,
    truncate,
    word_count,
)

MAX_SUMMARY = 4000
DEFAULT_SUMMARY_LENGTH = 200


class ShowNotes:
    """The markdown body attached to an episode."""

    __slots__ = ("body",)

    def __init__(self, body):
        text = require_text(body, "body", min_length=0, max_length=MAX_SUMMARY, strip=False)
        self.body = text.strip()

    @property
    def is_empty(self):
        return not self.body

    def plain_text(self):
        return strip_markup(self.body)

    def summary(self, length=DEFAULT_SUMMARY_LENGTH):
        if self.is_empty:
            return ""
        return truncate(self.plain_text(), require_int(length, "length", minimum=1))

    def links(self):
        return extract_links(self.body)

    def word_count(self):
        return word_count(self.body) if self.body else 0

    def reading_time_seconds(self):
        return reading_time_seconds(self.body) if self.body else 0

    def paragraphs(self):
        return tuple(
            normalize_whitespace(block)
            for block in self.body.split("\n\n")
            if normalize_whitespace(block)
        )

    def with_appended(self, extra):
        addition = require_text(extra, "extra", max_length=MAX_SUMMARY)
        joined = "{}\n\n{}".format(self.body, addition) if self.body else addition
        return ShowNotes(joined)

    def to_dict(self):
        return {
            "body": self.body,
            "summary": self.summary(),
            "links": list(self.links()),
            "word_count": self.word_count(),
        }

    def __eq__(self, other):
        return isinstance(other, ShowNotes) and other.body == self.body

    def __hash__(self):
        return hash(("shownotes", self.body))

    def __repr__(self):
        return "ShowNotes({} words)".format(self.word_count())


def require_notes(value, field="show_notes"):
    """Accept a :class:`ShowNotes`, a string or ``None``."""
    if value is None:
        return ShowNotes("")
    if isinstance(value, ShowNotes):
        return value
    if isinstance(value, str):
        return ShowNotes(value)
    raise ValidationError("{} must be text".format(field), field=field)
