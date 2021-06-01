"""Argument checks used by every constructor in the domain layer.

The guards all raise :class:`~src.domain.core.errors.ValidationError` and return
the normalised value, so a constructor reads as a list of assignments rather
than a wall of ``if`` statements.
"""

from src.domain.core.errors import ValidationError

_TRUTHY = ("true", "yes", "on", "1")
_FALSEY = ("false", "no", "off", "0")


def require_text(value, field, min_length=1, max_length=None, strip=True):
    """Return ``value`` as a non-empty string."""
    if value is None:
        raise ValidationError("{} is required".format(field), field=field)
    if not isinstance(value, str):
        raise ValidationError(
            "{} must be a string, got {}".format(field, type(value).__name__),
            field=field,
        )
    text = value.strip() if strip else value
    if len(text) < min_length:
        raise ValidationError(
            "{} must be at least {} characters".format(field, min_length),
            field=field,
        )
    if max_length is not None and len(text) > max_length:
        raise ValidationError(
            "{} must be at most {} characters".format(field, max_length),
            field=field,
        )
    return text


def require_int(value, field, minimum=None, maximum=None):
    """Return ``value`` as an ``int``, rejecting bools and floats."""
    if isinstance(value, bool):
        raise ValidationError("{} must be an integer".format(field), field=field)
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and value.strip():
        try:
            number = int(value.strip(), 10)
        except ValueError:
            raise ValidationError(
                "{} must be an integer".format(field), field=field
            ) from None
    else:
        raise ValidationError("{} must be an integer".format(field), field=field)
    if minimum is not None and number < minimum:
        raise ValidationError(
            "{} must be >= {}".format(field, minimum), field=field
        )
    if maximum is not None and number > maximum:
        raise ValidationError(
            "{} must be <= {}".format(field, maximum), field=field
        )
    return number


def require_number(value, field, minimum=None, maximum=None):
    """Return ``value`` as a ``float``."""
    if isinstance(value, bool):
        raise ValidationError("{} must be a number".format(field), field=field)
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str) and value.strip():
        try:
            number = float(value.strip())
        except ValueError:
            raise ValidationError(
                "{} must be a number".format(field), field=field
            ) from None
    else:
        raise ValidationError("{} must be a number".format(field), field=field)
    if number != number:
        raise ValidationError("{} must be a number".format(field), field=field)
    if minimum is not None and number < minimum:
        raise ValidationError(
            "{} must be >= {}".format(field, minimum), field=field
        )
    if maximum is not None and number > maximum:
        raise ValidationError(
            "{} must be <= {}".format(field, maximum), field=field
        )
    return number


def require_bool(value, field):
    """Return ``value`` as a ``bool``, accepting the usual string spellings."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _TRUTHY:
            return True
        if lowered in _FALSEY:
            return False
    raise ValidationError("{} must be a boolean".format(field), field=field)


def require_choice(value, field, allowed, normalize=True):
    """Return ``value`` after checking it is one of ``allowed``."""
    candidate = value
    if normalize and isinstance(candidate, str):
        candidate = candidate.strip().lower()
    if candidate not in allowed:
        raise ValidationError(
            "{} must be one of {}".format(field, ", ".join(sorted(allowed))),
            field=field,
            details={"allowed": sorted(allowed), "given": value},
        )
    return candidate


def require_mapping(value, field, keys=None):
    """Return ``value`` as a plain ``dict``."""
    if not isinstance(value, dict):
        raise ValidationError("{} must be an object".format(field), field=field)
    if keys is not None:
        missing = [key for key in keys if key not in value]
        if missing:
            raise ValidationError(
                "{} is missing {}".format(field, ", ".join(sorted(missing))),
                field=field,
                details={"missing": sorted(missing)},
            )
    return dict(value)


def require_sequence(value, field, min_length=0, max_length=None):
    """Return ``value`` as a ``tuple``; strings are rejected on purpose."""
    if isinstance(value, (str, bytes)) or not hasattr(value, "__iter__"):
        raise ValidationError("{} must be a list".format(field), field=field)
    items = tuple(value)
    if len(items) < min_length:
        raise ValidationError(
            "{} needs at least {} entries".format(field, min_length), field=field
        )
    if max_length is not None and len(items) > max_length:
        raise ValidationError(
            "{} allows at most {} entries".format(field, max_length), field=field
        )
    return items


def forbid_unknown(payload, field, allowed):
    """Raise when ``payload`` carries keys the caller did not declare."""
    extra = sorted(set(payload) - set(allowed))
    if extra:
        raise ValidationError(
            "{} has unknown keys: {}".format(field, ", ".join(extra)),
            field=field,
            details={"unknown": extra},
        )
    return dict(payload)
