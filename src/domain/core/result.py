"""A tiny result type.

Used where a caller wants to collect every failure rather than stop at the
first one -- bulk media uploads and multi-destination publishing both do.
"""

from src.domain.core.errors import DomainError


class Result:
    """Base class; construct :class:`Ok` or :class:`Err` instead."""

    __slots__ = ()

    ok = False

    def unwrap(self):
        raise NotImplementedError

    def unwrap_or(self, default):
        raise NotImplementedError

    def map(self, function):
        raise NotImplementedError


class Ok(Result):
    __slots__ = ("value",)

    ok = True

    def __init__(self, value=None):
        self.value = value

    def unwrap(self):
        return self.value

    def unwrap_or(self, default):
        return self.value

    def map(self, function):
        return Ok(function(self.value))

    def __eq__(self, other):
        return isinstance(other, Ok) and other.value == self.value

    def __hash__(self):
        return hash(("ok", self.value))

    def __repr__(self):
        return "Ok({!r})".format(self.value)


class Err(Result):
    __slots__ = ("error",)

    ok = False

    def __init__(self, error):
        if isinstance(error, str):
            error = DomainError(error)
        self.error = error

    def unwrap(self):
        raise self.error

    def unwrap_or(self, default):
        return default

    def map(self, function):
        return self

    @property
    def message(self):
        return getattr(self.error, "message", str(self.error))

    def __eq__(self, other):
        return isinstance(other, Err) and str(other.error) == str(self.error)

    def __hash__(self):
        return hash(("err", str(self.error)))

    def __repr__(self):
        return "Err({!r})".format(self.error)


def attempt(function, *args, **kwargs):
    """Run ``function`` and wrap a :class:`DomainError` into :class:`Err`."""
    try:
        return Ok(function(*args, **kwargs))
    except DomainError as error:
        return Err(error)


def collect(results):
    """Turn a sequence of results into ``Ok(tuple)`` or the first ``Err``."""
    values = []
    for result in results:
        if not result.ok:
            return result
        values.append(result.value)
    return Ok(tuple(values))


def partition_results(results):
    """Split results into ``(values, errors)``."""
    values = []
    errors = []
    for result in results:
        if result.ok:
            values.append(result.value)
        else:
            errors.append(result.error)
    return tuple(values), tuple(errors)


def first_error(results):
    """Return the first error in ``results``, or ``None``."""
    for result in results:
        if not result.ok:
            return result.error
    return None
