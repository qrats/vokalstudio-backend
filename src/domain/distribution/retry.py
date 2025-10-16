"""Backoff for upload jobs.

Uploads fail for two different reasons and they need different treatment: a
timeout deserves another go, a rejected file never will.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int

BASE_DELAY_SECONDS = 30
MAX_DELAY_SECONDS = 3600
DEFAULT_MAX_ATTEMPTS = 5

TRANSIENT = (
    "timeout",
    "rate_limited",
    "server_error",
    "connection_reset",
)

PERMANENT = (
    "rejected",
    "unauthorised",
    "file_too_large",
    "unsupported_format",
    "duplicate",
)

FAILURES = TRANSIENT + PERMANENT


def validate_failure(reason, field="reason"):
    if reason not in FAILURES:
        raise ValidationError(
            "unknown failure {}".format(reason),
            field=field,
            details={"known": sorted(FAILURES)},
        )
    return reason


def is_transient(reason):
    return validate_failure(reason) in TRANSIENT


def delay_seconds(attempt, base=BASE_DELAY_SECONDS, ceiling=MAX_DELAY_SECONDS):
    """Exponential backoff, capped."""
    count = require_int(attempt, "attempt", minimum=1)
    start = require_int(base, "base", minimum=1)
    cap = require_int(ceiling, "ceiling", minimum=1)
    return min(cap, start * (2 ** (count - 1)))


def should_retry(reason, attempt, max_attempts=DEFAULT_MAX_ATTEMPTS):
    """Whether a failed upload is worth another go."""
    if not is_transient(reason):
        return False
    return require_int(attempt, "attempt", minimum=1) < require_int(
        max_attempts, "max_attempts", minimum=1
    )


def schedule(reason, attempt, max_attempts=DEFAULT_MAX_ATTEMPTS):
    """The delay before the next attempt, or ``None`` when giving up."""
    if not should_retry(reason, attempt, max_attempts):
        return None
    return delay_seconds(attempt)


def total_wait_seconds(max_attempts=DEFAULT_MAX_ATTEMPTS):
    """How long a full retry run takes, worst case."""
    count = require_int(max_attempts, "max_attempts", minimum=1)
    return sum(delay_seconds(attempt) for attempt in range(1, count))
