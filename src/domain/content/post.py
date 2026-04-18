"""Blog posts.

The marketing site reads these; the admin API writes them.  Slugs are the
primary key the site uses, so a post cannot exist without one and two posts
cannot share one.
"""

from src.domain.content.markup import excerpt, parse_blocks, table_of_contents
from src.domain.core.errors import StateError, ValidationError
from src.domain.core.guards import require_bool, require_choice, require_sequence, require_text
from src.domain.core.text import reading_time_seconds, slugify, word_count
from src.domain.timeline.instant import coerce_instant

DRAFT = "draft"
PUBLISHED = "published"
ARCHIVED = "archived"

STATES = (DRAFT, PUBLISHED, ARCHIVED)

TRANSITIONS = {
    DRAFT: (PUBLISHED, ARCHIVED),
    PUBLISHED: (DRAFT, ARCHIVED),
    ARCHIVED: (DRAFT,),
}

MAX_BODY = 100_000


class Post:
    """One article."""

    __slots__ = (
        "title",
        "slug",
        "body",
        "author_id",
        "state",
        "tags",
        "hero_key",
        "featured",
        "published_at",
    )

    def __init__(
        self,
        title,
        body,
        author_id,
        slug=None,
        state=DRAFT,
        tags=(),
        hero_key=None,
        featured=False,
        published_at=None,
    ):
        self.title = require_text(title, "title", max_length=200)
        self.body = require_text(body, "body", min_length=1, max_length=MAX_BODY)
        self.author_id = require_text(author_id, "author_id", max_length=64)
        self.slug = slugify(slug or title, field="slug")
        self.state = require_choice(state, "state", STATES)
        self.tags = self._check_tags(tags)
        self.hero_key = (
            require_text(hero_key, "hero_key", max_length=255) if hero_key else None
        )
        self.featured = require_bool(featured, "featured")
        self.published_at = (
            coerce_instant(published_at, "published_at") if published_at else None
        )
        if self.state == PUBLISHED and self.published_at is None:
            raise ValidationError(
                "a published post needs a date", field="published_at"
            )
        if self.featured and self.state != PUBLISHED:
            raise ValidationError(
                "only a published post can be featured", field="featured"
            )

    @staticmethod
    def _check_tags(tags):
        values = require_sequence(tags, "tags", max_length=12)
        cleaned = []
        for tag in values:
            slug = slugify(tag, max_length=40, field="tags")
            if slug not in cleaned:
                cleaned.append(slug)
        return tuple(sorted(cleaned))

    def _copy(self, **changes):
        payload = {
            "title": self.title,
            "body": self.body,
            "author_id": self.author_id,
            "slug": self.slug,
            "state": self.state,
            "tags": self.tags,
            "hero_key": self.hero_key,
            "featured": self.featured,
            "published_at": self.published_at,
        }
        payload.update(changes)
        return Post(**payload)

    def _moved_to(self, target):
        if target not in TRANSITIONS[self.state]:
            raise StateError(
                "cannot move a {} post to {}".format(self.state, target),
                current=self.state,
                attempted=target,
            )
        return target

    def publish(self, at):
        return self._copy(state=self._moved_to(PUBLISHED), published_at=coerce_instant(at, "at"))

    def unpublish(self):
        return self._copy(state=self._moved_to(DRAFT), featured=False)

    def archive(self):
        return self._copy(state=self._moved_to(ARCHIVED), featured=False)

    def feature(self):
        if self.state != PUBLISHED:
            raise ValidationError(
                "only a published post can be featured", field="featured"
            )
        return self._copy(featured=True)

    def unfeature(self):
        return self._copy(featured=False)

    def tagged(self, tag):
        return slugify(tag, max_length=40, field="tag") in self.tags

    def with_tags(self, tags):
        return self._copy(tags=tags)

    def is_visible(self, now=None):
        if self.state != PUBLISHED:
            return False
        if now is None or self.published_at is None:
            return True
        return coerce_instant(now, "now") >= self.published_at

    def blocks(self):
        return parse_blocks(self.body)

    def excerpt(self, limit=200):
        return excerpt(self.body, limit)

    def table_of_contents(self):
        return table_of_contents(self.body)

    def word_count(self):
        return word_count(self.body)

    def reading_time_seconds(self):
        return reading_time_seconds(self.body)

    def to_dict(self):
        return {
            "title": self.title,
            "slug": self.slug,
            "author_id": self.author_id,
            "state": self.state,
            "tags": list(self.tags),
            "hero_key": self.hero_key,
            "featured": self.featured,
            "excerpt": self.excerpt(),
            "word_count": self.word_count(),
            "reading_time_seconds": self.reading_time_seconds(),
            "published_at": self.published_at.to_iso() if self.published_at else None,
        }

    def __eq__(self, other):
        return (
            isinstance(other, Post)
            and other.to_dict() == self.to_dict()
            and other.body == self.body
        )

    def __hash__(self):
        return hash(("post", self.slug, self.state))

    def __repr__(self):
        return "Post({!r}, {})".format(self.slug, self.state)


def visible(posts, now=None):
    return tuple(post for post in posts if post.is_visible(now))


def featured(posts, now=None):
    return tuple(post for post in visible(posts, now) if post.featured)


def duplicate_slugs(posts):
    counts = {}
    for post in posts:
        counts[post.slug] = counts.get(post.slug, 0) + 1
    return tuple(sorted(slug for slug, count in counts.items() if count > 1))


def find(posts, slug, default=None):
    wanted = slugify(slug, field="slug")
    for post in posts:
        if post.slug == wanted:
            return post
    return default
