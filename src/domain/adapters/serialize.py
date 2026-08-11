"""Turning domain objects back into JSON-ready dictionaries.

Every value object already has ``to_dict``; what this adds is the envelope the
API responses use and the rule that secrets never leave without being asked
for explicitly.
"""

from src.domain.core.errors import DomainError
from src.domain.core.guards import require_int

SECRET_KEYS = ("stream_key", "token", "refresh_token", "password", "secret")


def scrub(payload):
    """Remove anything that looks like a secret from a nested payload."""
    if isinstance(payload, dict):
        return {
            key: scrub(value)
            for key, value in payload.items()
            if key not in SECRET_KEYS
        }
    if isinstance(payload, (list, tuple)):
        return [scrub(item) for item in payload]
    return payload


def one(value, meta=None):
    """The envelope for a single object."""
    body = {"data": value.to_dict() if hasattr(value, "to_dict") else value}
    if meta:
        body["meta"] = dict(meta)
    return body


def many(values, meta=None):
    """The envelope for a list."""
    body = {
        "data": [
            value.to_dict() if hasattr(value, "to_dict") else value for value in values
        ]
    }
    body["meta"] = dict(meta or {})
    body["meta"].setdefault("count", len(body["data"]))
    return body


def page(result, meta=None):
    """The envelope for a paged search result."""
    body = many(result["items"], meta)
    body["meta"].update(
        {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "pages": result["pages"],
            "has_next": result["has_next"],
            "has_previous": result["has_previous"],
        }
    )
    return body


def error(exception):
    """The envelope for a failure, plus the status it should carry."""
    if isinstance(exception, DomainError):
        return exception.to_dict(), exception.status
    return {"code": "internal_error", "message": "unexpected error"}, 500


def truncated(values, limit):
    """The first ``limit`` entries plus a flag saying whether more exist."""
    size = require_int(limit, "limit", minimum=1)
    materialised = list(values)
    return {
        "items": materialised[:size],
        "truncated": len(materialised) > size,
        "total": len(materialised),
    }
