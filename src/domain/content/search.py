"""Filtering, sorting and paging a list of posts.

The blog index takes the same query parameters from three places, so the query
is a value object rather than a pile of keyword arguments.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_sequence, require_text
from src.domain.core.text import normalize_whitespace, slugify, strip_markup

NEWEST = "newest"
OLDEST = "oldest"
TITLE = "title"

ORDERS = (NEWEST, OLDEST, TITLE)

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


class Query:
    """What the reader asked for."""

    __slots__ = ("text", "tags", "order", "page", "page_size")

    def __init__(self, text=None, tags=(), order=NEWEST, page=1, page_size=DEFAULT_PAGE_SIZE):
        self.text = (
            normalize_whitespace(require_text(text, "text", max_length=200)).lower()
            if text
            else None
        )
        values = require_sequence(tags, "tags", max_length=12)
        cleaned = []
        for tag in values:
            slug = slugify(tag, max_length=40, field="tags")
            if slug not in cleaned:
                cleaned.append(slug)
        self.tags = tuple(sorted(cleaned))
        if order not in ORDERS:
            raise ValidationError(
                "order must be one of {}".format(", ".join(ORDERS)), field="order"
            )
        self.order = order
        self.page = require_int(page, "page", minimum=1)
        self.page_size = require_int(
            page_size, "page_size", minimum=1, maximum=MAX_PAGE_SIZE
        )

    @property
    def offset(self):
        return (self.page - 1) * self.page_size

    def to_dict(self):
        return {
            "text": self.text,
            "tags": list(self.tags),
            "order": self.order,
            "page": self.page,
            "page_size": self.page_size,
        }

    def __eq__(self, other):
        return isinstance(other, Query) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("query", self.text, self.tags, self.order, self.page, self.page_size))

    def __repr__(self):
        return "Query({!r}, page {})".format(self.text, self.page)


def _matches(post, query):
    if query.tags and not all(tag in post.tags for tag in query.tags):
        return False
    if query.text:
        haystack = "{} {}".format(post.title, strip_markup(post.body)).lower()
        if query.text not in haystack:
            return False
    return True


def _sort_key(order):
    if order == TITLE:
        return lambda post: (post.title.lower(), post.slug)
    return lambda post: (
        post.published_at.millis if post.published_at else 0,
        post.slug,
    )


def run(posts, query, now=None):
    """Apply a query and return the page plus the paging metadata."""
    from src.domain.content.post import visible

    candidates = [post for post in visible(posts, now) if _matches(post, query)]
    candidates.sort(key=_sort_key(query.order), reverse=query.order == NEWEST)
    total = len(candidates)
    page = candidates[query.offset: query.offset + query.page_size]
    return {
        "items": tuple(page),
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "pages": -(-total // query.page_size),
        "has_next": query.offset + query.page_size < total,
        "has_previous": query.page > 1,
    }


def tag_counts(posts, now=None):
    """How many visible posts carry each tag."""
    from src.domain.content.post import visible

    counts = {}
    for post in visible(posts, now):
        for tag in post.tags:
            counts[tag] = counts.get(tag, 0) + 1
    return counts


def popular_tags(posts, limit=5, now=None):
    """The most used tags, ties broken alphabetically."""
    size = require_int(limit, "limit", minimum=1)
    counts = tag_counts(posts, now)
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return tuple(name for name, _ in ordered[:size])


def related(posts, post, limit=3, now=None):
    """Other visible posts sharing the most tags."""
    from src.domain.content.post import visible

    size = require_int(limit, "limit", minimum=1)
    scored = []
    for candidate in visible(posts, now):
        if candidate.slug == post.slug:
            continue
        shared = len(set(candidate.tags) & set(post.tags))
        if shared:
            scored.append((shared, candidate))
    scored.sort(key=lambda pair: (-pair[0], pair[1].slug))
    return tuple(candidate for _, candidate in scored[:size])
