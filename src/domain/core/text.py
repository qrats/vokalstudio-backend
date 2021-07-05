"""Text helpers.

Blog posts, show notes and episode titles all pass through here, so the rules
live in one place: slugs are lowercase ASCII, whitespace is squeezed, and
truncation never splits a word when it can avoid it.
"""

import re
import unicodedata

from src.domain.core.errors import ValidationError

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_WHITESPACE = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]*>")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_WORD = re.compile(r"[^\s]+")

WORDS_PER_MINUTE = 220

_TRANSLITERATIONS = {
    "ß": "ss",
    "æ": "ae",
    "œ": "oe",
    "ø": "o",
    "đ": "d",
    "ł": "l",
}


def _fold(value):
    folded = "".join(_TRANSLITERATIONS.get(char, char) for char in value.lower())
    decomposed = unicodedata.normalize("NFKD", folded)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def slugify(value, max_length=80, field="slug"):
    """Return a lowercase ``a-z0-9-`` slug."""
    if not isinstance(value, str):
        raise ValidationError("{} must be a string".format(field), field=field)
    slug = _SLUG_STRIP.sub("-", _fold(value)).strip("-")
    if max_length is not None and len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    if not slug:
        raise ValidationError(
            "{} could not be derived from {!r}".format(field, value), field=field
        )
    return slug


def is_slug(value):
    """Return whether ``value`` is already a canonical slug."""
    return isinstance(value, str) and bool(value) and slugify_safe(value) == value


def slugify_safe(value, default=""):
    """Like :func:`slugify` but returns ``default`` instead of raising."""
    try:
        return slugify(value)
    except ValidationError:
        return default


def normalize_whitespace(value):
    """Collapse runs of whitespace and trim the ends."""
    if not isinstance(value, str):
        raise ValidationError("value must be a string", field="value")
    return _WHITESPACE.sub(" ", value).strip()


def strip_markup(value):
    """Remove HTML tags and markdown link syntax, keeping the link text."""
    if not isinstance(value, str):
        raise ValidationError("value must be a string", field="value")
    without_links = _MD_LINK.sub(lambda match: match.group(1), value)
    return normalize_whitespace(_TAG.sub(" ", without_links))


def truncate(value, limit, suffix="…"):
    """Shorten ``value`` to ``limit`` characters including ``suffix``."""
    if limit <= 0:
        raise ValidationError("limit must be positive", field="limit")
    text = normalize_whitespace(value)
    if len(text) <= limit:
        return text
    if limit <= len(suffix):
        return suffix[:limit]
    room = limit - len(suffix)
    head = text[:room]
    if " " in head and not text[room: room + 1].isspace():
        head = head[: head.rindex(" ")]
    return head.rstrip() + suffix


def word_count(value):
    """Count words after markup has been stripped."""
    return len(_WORD.findall(strip_markup(value)))


def reading_time_seconds(value, words_per_minute=WORDS_PER_MINUTE):
    """Estimate reading time, rounded up to whole seconds."""
    if words_per_minute <= 0:
        raise ValidationError(
            "words_per_minute must be positive", field="words_per_minute"
        )
    words = word_count(value)
    if words == 0:
        return 0
    return -(-words * 60 // words_per_minute)


def extract_links(value):
    """Return the URLs referenced by markdown links, in order, de-duplicated."""
    seen = []
    for match in _MD_LINK.finditer(value or ""):
        url = match.group(2).strip()
        if url and url not in seen:
            seen.append(url)
    return tuple(seen)


def initials(value, size=2):
    """Return up to ``size`` uppercase initials for a display name."""
    words = _WORD.findall(normalize_whitespace(value or ""))
    letters = [word[0].upper() for word in words if word[:1].isalnum()]
    return "".join(letters[:size])


def mask(value, keep=4, char="*"):
    """Mask all but the last ``keep`` characters of a secret."""
    if not isinstance(value, str):
        raise ValidationError("value must be a string", field="value")
    if keep < 0:
        raise ValidationError("keep must not be negative", field="keep")
    if keep == 0 or len(value) <= keep:
        return char * len(value)
    return char * (len(value) - keep) + value[-keep:]
