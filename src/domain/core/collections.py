"""Small immutable collection helpers.

Nothing here mutates its argument.  ``freeze`` in particular is used by the
value objects so that a caller cannot reach into a constructed object and edit
the list it was built from.
"""

from src.domain.core.errors import ValidationError


def freeze(value):
    """Return a deeply immutable view of ``value``."""
    if isinstance(value, dict):
        return tuple(sorted(((key, freeze(item)) for key, item in value.items())))
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(freeze(item) for item in value)
    return value


def unique(items, key=None):
    """Return ``items`` with duplicates dropped, preserving first-seen order."""
    seen = set()
    kept = []
    for item in items:
        marker = item if key is None else key(item)
        if marker in seen:
            continue
        seen.add(marker)
        kept.append(item)
    return tuple(kept)


def group_by(items, key):
    """Group ``items`` into a dict of tuples, preserving input order."""
    grouped = {}
    for item in items:
        grouped.setdefault(key(item), []).append(item)
    return {name: tuple(values) for name, values in grouped.items()}


def index_by(items, key, on_duplicate="raise"):
    """Build a ``{key: item}`` index."""
    if on_duplicate not in ("raise", "first", "last"):
        raise ValidationError(
            "on_duplicate must be raise, first or last", field="on_duplicate"
        )
    index = {}
    for item in items:
        marker = key(item)
        if marker in index:
            if on_duplicate == "raise":
                raise ValidationError(
                    "duplicate key {!r}".format(marker), field="key"
                )
            if on_duplicate == "first":
                continue
        index[marker] = item
    return index


def partition(items, predicate):
    """Split ``items`` into ``(matching, other)``."""
    matching = []
    other = []
    for item in items:
        (matching if predicate(item) else other).append(item)
    return tuple(matching), tuple(other)


def chunk(items, size):
    """Split ``items`` into tuples of at most ``size`` entries."""
    if size <= 0:
        raise ValidationError("size must be positive", field="size")
    materialised = tuple(items)
    return tuple(
        materialised[start: start + size]
        for start in range(0, len(materialised), size)
    )


def first(items, predicate=None, default=None):
    """Return the first matching item, or ``default``."""
    for item in items:
        if predicate is None or predicate(item):
            return item
    return default


def sum_by(items, value):
    """Sum ``value(item)`` across ``items``, returning ``0`` when empty."""
    total = 0
    for item in items:
        total += value(item)
    return total


def max_by(items, value, default=None):
    """Return the item with the largest ``value(item)``."""
    best = default
    best_value = None
    for item in items:
        current = value(item)
        if best_value is None or current > best_value:
            best = item
            best_value = current
    return best


def merge_dicts(*mappings):
    """Merge mappings left to right into a new dict."""
    merged = {}
    for mapping in mappings:
        if mapping:
            merged.update(mapping)
    return merged


def pluck(items, attribute):
    """Return ``getattr(item, attribute)`` for every item."""
    return tuple(getattr(item, attribute) for item in items)


def sorted_by(items, *keys):
    """Sort by several attribute names, applied left to right."""
    def sort_key(item):
        return tuple(getattr(item, name) for name in keys)

    return tuple(sorted(items, key=sort_key))
