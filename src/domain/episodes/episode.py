"""Episodes.

An episode is a title, a media asset, some notes and a state.  What it is
allowed to do depends on that state, and the checks that were spread across
five resources are gathered here.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_bool, require_choice, require_int, require_text
from src.domain.core.ids import derive_id
from src.domain.core.text import slugify
from src.domain.episodes.chapters import validate_chapters
from src.domain.episodes.series import TYPES
from src.domain.episodes.shownotes import require_notes
from src.domain.episodes.state import (
    DRAFT,
    PUBLISHED,
    SCHEDULED,
    STATES,
    is_editable,
    is_visible,
    transition,
)
from src.domain.media.format import AUDIO, VIDEO
from src.domain.timeline.instant import coerce_instant


class Episode:
    """One publishable item."""

    __slots__ = (
        "owner_id",
        "series_slug",
        "title",
        "slug",
        "state",
        "asset",
        "notes",
        "chapters",
        "number",
        "season",
        "kind",
        "explicit",
        "published_at",
    )

    def __init__(
        self,
        owner_id,
        series_slug,
        title,
        asset=None,
        notes=None,
        chapters=(),
        number=None,
        season=None,
        kind="full",
        explicit=False,
        state=DRAFT,
        published_at=None,
        slug=None,
    ):
        self.owner_id = require_text(owner_id, "owner_id", max_length=64)
        self.series_slug = slugify(series_slug, field="series_slug")
        self.title = require_text(title, "title", max_length=200)
        self.slug = slugify(slug or title, field="slug")
        self.state = require_choice(state, "state", STATES)
        self.asset = self._check_asset(asset)
        self.notes = require_notes(notes)
        self.chapters = validate_chapters(
            chapters, self.asset.duration.millis if self.asset else None
        )
        self.number = require_int(number, "number", minimum=1) if number is not None else None
        self.season = require_int(season, "season", minimum=1) if season is not None else None
        self.kind = require_choice(kind, "kind", TYPES)
        self.explicit = require_bool(explicit, "explicit")
        self.published_at = (
            coerce_instant(published_at, "published_at") if published_at else None
        )
        if self.state in (SCHEDULED, PUBLISHED) and self.published_at is None:
            raise ValidationError(
                "a {} episode needs a date".format(self.state), field="published_at"
            )

    @staticmethod
    def _check_asset(asset):
        if asset is None:
            return None
        if asset.kind not in (AUDIO, VIDEO):
            raise ValidationError("an episode needs audio or video", field="asset")
        return asset

    @property
    def reference(self):
        return derive_id("episode", self.owner_id, self.series_slug, self.slug)

    @property
    def duration_millis(self):
        return self.asset.duration.millis if self.asset else 0

    def _copy(self, **changes):
        payload = {
            "owner_id": self.owner_id,
            "series_slug": self.series_slug,
            "title": self.title,
            "asset": self.asset,
            "notes": self.notes,
            "chapters": self.chapters,
            "number": self.number,
            "season": self.season,
            "kind": self.kind,
            "explicit": self.explicit,
            "state": self.state,
            "published_at": self.published_at,
            "slug": self.slug,
        }
        payload.update(changes)
        return Episode(**payload)

    def missing_for_publication(self):
        """Everything still stopping this episode from going out, sorted."""
        missing = []
        if self.asset is None:
            missing.append("asset")
        if self.notes.is_empty:
            missing.append("show_notes")
        if self.number is None:
            missing.append("number")
        return tuple(sorted(missing))

    def is_publishable(self):
        return not self.missing_for_publication()

    def is_editable(self):
        return is_editable(self.state)

    def is_visible(self):
        return is_visible(self.state)

    def mark_ready(self):
        if not self.is_publishable():
            raise ValidationError(
                "episode is incomplete",
                field="episode",
                details={"missing": list(self.missing_for_publication())},
            )
        return self._copy(state=transition(self.state, "ready"))

    def schedule(self, at):
        moment = coerce_instant(at, "at")
        return self._copy(
            state=transition(self.state, SCHEDULED), published_at=moment
        )

    def publish(self, at=None):
        moment = coerce_instant(at, "at") if at is not None else self.published_at
        if moment is None:
            raise ValidationError("publishing needs a date", field="at")
        return self._copy(state=transition(self.state, PUBLISHED), published_at=moment)

    def archive(self):
        return self._copy(state=transition(self.state, "archived"))

    def back_to_draft(self):
        return self._copy(state=transition(self.state, DRAFT))

    def with_asset(self, asset):
        return self._copy(asset=asset, chapters=())

    def with_notes(self, notes):
        return self._copy(notes=require_notes(notes))

    def with_chapters(self, chapters):
        return self._copy(chapters=tuple(chapters))

    def numbered(self, number, season=None):
        return self._copy(number=number, season=season)

    def is_due(self, now):
        """Whether a scheduled episode should now go out."""
        if self.state != SCHEDULED or self.published_at is None:
            return False
        return coerce_instant(now, "now") >= self.published_at

    def to_dict(self):
        return {
            "reference": self.reference,
            "owner_id": self.owner_id,
            "series_slug": self.series_slug,
            "title": self.title,
            "slug": self.slug,
            "state": self.state,
            "asset_key": self.asset.key if self.asset else None,
            "duration_millis": self.duration_millis,
            "notes": self.notes.body,
            "chapters": [chapter.to_dict() for chapter in self.chapters],
            "number": self.number,
            "season": self.season,
            "kind": self.kind,
            "explicit": self.explicit,
            "published_at": self.published_at.to_iso() if self.published_at else None,
        }

    def __eq__(self, other):
        return isinstance(other, Episode) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("episode", self.reference, self.state))

    def __repr__(self):
        return "Episode({!r}, {})".format(self.slug, self.state)


def due_for_publication(episodes, now):
    return tuple(episode for episode in episodes if episode.is_due(now))


def visible(episodes):
    return tuple(episode for episode in episodes if episode.is_visible())


def published_in_month(episodes, year, month):
    prefix = "{:04d}-{:02d}".format(year, month)
    return tuple(
        episode
        for episode in episodes
        if episode.state == PUBLISHED
        and episode.published_at is not None
        and episode.published_at.to_date().startswith(prefix)
    )


def duplicate_slugs(episodes):
    counts = {}
    for episode in episodes:
        key = (episode.series_slug, episode.slug)
        counts[key] = counts.get(key, 0) + 1
    return tuple(sorted(key[1] for key, count in counts.items() if count > 1))
