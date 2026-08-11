"""Reading values off whatever the persistence layer hands over.

The resources pass SQLAlchemy model instances; the tasks pass dictionaries
decoded from a Celery message; the tests pass plain objects.  Everything in
this package goes through :func:`field` so that none of the mappers below has
to care which of the three it received.
"""

from src.domain.core.errors import ValidationError

_MISSING = object()


def field(row, name, default=_MISSING):
    """Read ``name`` off a mapping or an object."""
    if isinstance(row, dict):
        if name in row:
            return row[name]
    elif hasattr(row, name):
        return getattr(row, name)
    if default is _MISSING:
        raise ValidationError(
            "row is missing {}".format(name),
            field=name,
            details={"available": available(row)},
        )
    return default


def has(row, name):
    if isinstance(row, dict):
        return name in row
    return hasattr(row, name)


def available(row):
    """The field names a row offers, sorted."""
    if isinstance(row, dict):
        return sorted(row)
    return sorted(
        name
        for name in dir(row)
        if not name.startswith("_") and not callable(getattr(row, name, None))
    )


def pick(row, *names, **defaults):
    """Read several fields at once into a dict."""
    picked = {}
    for name in names:
        if name in defaults:
            picked[name] = field(row, name, defaults[name])
        else:
            picked[name] = field(row, name)
    return picked


def require_fields(row, *names):
    """Raise unless every name is present."""
    missing = sorted(name for name in names if not has(row, name))
    if missing:
        raise ValidationError(
            "row is missing {}".format(", ".join(missing)),
            field="row",
            details={"missing": missing},
        )
    return row


def rename(row, mapping, defaults=None):
    """Read a row through a ``{domain_name: row_name}`` mapping."""
    fallbacks = defaults or {}
    picked = {}
    for target, source in mapping.items():
        if target in fallbacks:
            picked[target] = field(row, source, fallbacks[target])
        else:
            picked[target] = field(row, source)
    return picked


def coalesce(row, *names, default=None):
    """The first field present on ``row``, or ``default``."""
    for name in names:
        if has(row, name):
            value = field(row, name)
            if value is not None:
                return value
    return default
