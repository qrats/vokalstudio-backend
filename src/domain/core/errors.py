"""Domain errors.

Every failure raised by the domain layer carries a stable machine readable
``code``.  The Flask resources map the code onto an HTTP status and drop the
``details`` mapping straight into the JSON body, so codes must never be renamed
once they have shipped.
"""

STATUS_BY_CODE = {
    "validation_failed": 422,
    "not_found": 404,
    "conflict": 409,
    "invalid_state": 409,
    "forbidden": 403,
    "quota_exceeded": 429,
    "domain_error": 400,
}


class DomainError(Exception):
    """Base class for everything the domain layer raises on purpose."""

    code = "domain_error"

    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = dict(details or {})

    @property
    def status(self):
        return STATUS_BY_CODE.get(self.code, 400)

    def to_dict(self):
        payload = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = dict(self.details)
        return payload

    def __repr__(self):
        return "{}({!r}, code={!r})".format(
            type(self).__name__, self.message, self.code
        )


class ValidationError(DomainError):
    """A value did not satisfy the shape the domain expects."""

    code = "validation_failed"

    def __init__(self, message, field=None, details=None):
        merged = dict(details or {})
        if field is not None:
            merged.setdefault("field", field)
        super().__init__(message, merged)
        self.field = field


class NotFoundError(DomainError):
    """A lookup by identifier came back empty."""

    code = "not_found"

    def __init__(self, message, kind=None, ref=None):
        details = {}
        if kind is not None:
            details["kind"] = kind
        if ref is not None:
            details["ref"] = ref
        super().__init__(message, details)
        self.kind = kind
        self.ref = ref


class ConflictError(DomainError):
    """The requested change collides with something that already exists."""

    code = "conflict"


class StateError(DomainError):
    """A state machine refused the transition it was asked for."""

    code = "invalid_state"

    def __init__(self, message, current=None, attempted=None):
        details = {}
        if current is not None:
            details["current"] = current
        if attempted is not None:
            details["attempted"] = attempted
        super().__init__(message, details)
        self.current = current
        self.attempted = attempted


class PermissionError_(DomainError):
    """The actor is not allowed to perform the action."""

    code = "forbidden"

    def __init__(self, message, action=None, subject=None):
        details = {}
        if action is not None:
            details["action"] = action
        if subject is not None:
            details["subject"] = subject
        super().__init__(message, details)
        self.action = action
        self.subject = subject


class QuotaError(DomainError):
    """A plan limit would be exceeded by the request."""

    code = "quota_exceeded"

    def __init__(self, message, feature=None, limit=None, used=None):
        details = {}
        if feature is not None:
            details["feature"] = feature
        if limit is not None:
            details["limit"] = limit
        if used is not None:
            details["used"] = used
        super().__init__(message, details)
        self.feature = feature
        self.limit = limit
        self.used = used


def error_status(error):
    """Return the HTTP status an error should be surfaced with."""
    if isinstance(error, DomainError):
        return error.status
    return 500
