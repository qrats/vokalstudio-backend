"""Upload jobs.

One row per episode per destination.  The job records every attempt so that a
support question about "why is this not on Spotify" has an answer.
"""

from src.domain.core.errors import StateError, ValidationError
from src.domain.core.guards import require_choice, require_int, require_text
from src.domain.core.ids import derive_id
from src.domain.distribution.destination import normalize_destination
from src.domain.distribution.retry import schedule, validate_failure
from src.domain.timeline.instant import coerce_instant

PENDING = "pending"
RUNNING = "running"
SUCCEEDED = "succeeded"
FAILED = "failed"
ABANDONED = "abandoned"

STATES = (PENDING, RUNNING, SUCCEEDED, FAILED, ABANDONED)

TRANSITIONS = {
    PENDING: (RUNNING, ABANDONED),
    RUNNING: (SUCCEEDED, FAILED),
    FAILED: (PENDING, ABANDONED),
    SUCCEEDED: (),
    ABANDONED: (),
}


class UploadJob:
    """One attempt series to place an episode on a destination."""

    __slots__ = (
        "episode_reference",
        "destination",
        "state",
        "attempts",
        "last_failure",
        "external_id",
        "updated_at",
    )

    def __init__(
        self,
        episode_reference,
        destination,
        state=PENDING,
        attempts=0,
        last_failure=None,
        external_id=None,
        updated_at=None,
    ):
        self.episode_reference = require_text(
            episode_reference, "episode_reference", max_length=64
        )
        self.destination = normalize_destination(destination)
        self.state = require_choice(state, "state", STATES)
        self.attempts = require_int(attempts, "attempts", minimum=0)
        self.last_failure = (
            validate_failure(last_failure, "last_failure") if last_failure else None
        )
        self.external_id = (
            require_text(external_id, "external_id", max_length=200)
            if external_id
            else None
        )
        self.updated_at = (
            coerce_instant(updated_at, "updated_at") if updated_at else None
        )
        if self.state == FAILED and self.last_failure is None:
            raise ValidationError(
                "a failed job needs a reason", field="last_failure"
            )
        if self.state == SUCCEEDED and self.external_id is None:
            raise ValidationError(
                "a successful job records the remote id", field="external_id"
            )

    @property
    def reference(self):
        return derive_id("upload", self.episode_reference, self.destination)

    def _copy(self, **changes):
        payload = {
            "episode_reference": self.episode_reference,
            "destination": self.destination,
            "state": self.state,
            "attempts": self.attempts,
            "last_failure": self.last_failure,
            "external_id": self.external_id,
            "updated_at": self.updated_at,
        }
        payload.update(changes)
        return UploadJob(**payload)

    def _moved_to(self, target):
        if target not in TRANSITIONS[self.state]:
            raise StateError(
                "cannot move a {} job to {}".format(self.state, target),
                current=self.state,
                attempted=target,
            )
        return target

    def start(self, at=None):
        return self._copy(
            state=self._moved_to(RUNNING),
            attempts=self.attempts + 1,
            updated_at=at or self.updated_at,
        )

    def succeed(self, external_id, at=None):
        return self._copy(
            state=self._moved_to(SUCCEEDED),
            external_id=external_id,
            last_failure=None,
            updated_at=at or self.updated_at,
        )

    def fail(self, reason, at=None):
        return self._copy(
            state=self._moved_to(FAILED),
            last_failure=validate_failure(reason),
            updated_at=at or self.updated_at,
        )

    def requeue(self, at=None):
        return self._copy(state=self._moved_to(PENDING), updated_at=at or self.updated_at)

    def abandon(self, at=None):
        return self._copy(
            state=self._moved_to(ABANDONED), updated_at=at or self.updated_at
        )

    def next_delay_seconds(self, max_attempts=None):
        """Seconds to wait before retrying, or ``None`` if it should stop."""
        if self.state != FAILED or self.last_failure is None:
            return None
        if max_attempts is None:
            return schedule(self.last_failure, self.attempts)
        return schedule(self.last_failure, self.attempts, max_attempts)

    def is_retryable(self, max_attempts=None):
        return self.next_delay_seconds(max_attempts) is not None

    def is_finished(self):
        return self.state in (SUCCEEDED, ABANDONED)

    def to_dict(self):
        return {
            "reference": self.reference,
            "episode_reference": self.episode_reference,
            "destination": self.destination,
            "state": self.state,
            "attempts": self.attempts,
            "last_failure": self.last_failure,
            "external_id": self.external_id,
            "updated_at": self.updated_at.to_iso() if self.updated_at else None,
        }

    def __eq__(self, other):
        return isinstance(other, UploadJob) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("job", self.reference, self.state, self.attempts))

    def __repr__(self):
        return "UploadJob({}, {})".format(self.destination, self.state)


def outstanding(jobs):
    return tuple(job for job in jobs if not job.is_finished())


def retryable(jobs, max_attempts=None):
    return tuple(job for job in jobs if job.is_retryable(max_attempts))


def by_destination(jobs, destination):
    wanted = normalize_destination(destination)
    return tuple(job for job in jobs if job.destination == wanted)


def summarise(jobs):
    """A count per state, for the episode detail screen."""
    counts = {state: 0 for state in STATES}
    for job in jobs:
        counts[job.state] += 1
    return counts
