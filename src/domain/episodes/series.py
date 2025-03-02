"""Shows and how their episodes are numbered.

A show either runs in seasons or does not; getting that wrong is what produced
"Season 0, Episode 0" in three feeds, so the numbering rules are explicit.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_bool, require_choice, require_int, require_text
from src.domain.core.text import slugify

EPISODIC = "episodic"
SERIAL = "serial"
ORDERINGS = (EPISODIC, SERIAL)

TYPES = ("full", "trailer", "bonus")


class Series:
    """One show."""

    __slots__ = ("owner_id", "title", "slug", "ordering", "seasons", "explicit")

    def __init__(self, owner_id, title, ordering=EPISODIC, seasons=False, explicit=False, slug=None):
        self.owner_id = require_text(owner_id, "owner_id", max_length=64)
        self.title = require_text(title, "title", max_length=200)
        self.slug = slugify(slug or title, field="slug")
        self.ordering = require_choice(ordering, "ordering", ORDERINGS)
        self.seasons = require_bool(seasons, "seasons")
        self.explicit = require_bool(explicit, "explicit")

    def newest_first(self):
        """Whether the feed lists the newest episode at the top."""
        return self.ordering == EPISODIC

    def number_for(self, existing_numbers, season=None):
        """The next episode number, given what has already been published."""
        if self.seasons:
            if season is None:
                raise ValidationError("this show uses seasons", field="season")
            wanted = require_int(season, "season", minimum=1)
            used = [
                number
                for taken_season, number in existing_numbers
                if taken_season == wanted
            ]
        else:
            if season is not None:
                raise ValidationError("this show has no seasons", field="season")
            used = [number for _, number in existing_numbers]
        return max(used) + 1 if used else 1

    def label_for(self, number, season=None):
        """The human label for an episode, e.g. ``S2E14`` or ``#14``."""
        index = require_int(number, "number", minimum=1)
        if not self.seasons:
            if season is not None:
                raise ValidationError("this show has no seasons", field="season")
            return "#{}".format(index)
        return "S{}E{}".format(require_int(season, "season", minimum=1), index)

    def to_dict(self):
        return {
            "owner_id": self.owner_id,
            "title": self.title,
            "slug": self.slug,
            "ordering": self.ordering,
            "seasons": self.seasons,
            "explicit": self.explicit,
        }

    @classmethod
    def from_dict(cls, payload):
        return cls(
            payload["owner_id"],
            payload["title"],
            payload.get("ordering", EPISODIC),
            payload.get("seasons", False),
            payload.get("explicit", False),
            payload.get("slug"),
        )

    def __eq__(self, other):
        return isinstance(other, Series) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("series", self.owner_id, self.slug))

    def __repr__(self):
        return "Series({!r})".format(self.slug)
