"""A configured stream destination.

One row of the customer's "streaming platforms" table: which service, where it
ingests, the key, and whether it is currently switched on.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_bool, require_text
from src.domain.core.ids import derive_id
from src.domain.streaming.platform import (
    CUSTOM,
    default_ingest,
    is_custom,
    max_kbps,
    minimum_key_length,
    normalize_platform,
    requires_secure,
)
from src.domain.streaming.rtmp import IngestUrl, masked_key, validate_stream_key


class StreamTarget:
    """One place a live session is pushed to."""

    __slots__ = ("user_id", "platform", "ingest", "stream_key", "enabled", "label")

    def __init__(self, user_id, platform, stream_key, ingest=None, enabled=True, label=None):
        self.user_id = require_text(user_id, "user_id", max_length=64)
        self.platform = normalize_platform(platform)
        self.stream_key = validate_stream_key(
            stream_key, minimum=minimum_key_length(self.platform)
        )
        self.ingest = self._resolve_ingest(ingest)
        if requires_secure(self.platform) and not self.ingest.is_secure:
            raise ValidationError(
                "{} requires rtmps".format(self.platform), field="ingest"
            )
        self.enabled = require_bool(enabled, "enabled")
        self.label = require_text(label, "label", max_length=80) if label else None

    def _resolve_ingest(self, ingest):
        if ingest is not None:
            return ingest if isinstance(ingest, IngestUrl) else IngestUrl.parse(ingest, "ingest")
        fallback = default_ingest(self.platform)
        if fallback is None:
            raise ValidationError(
                "a custom target needs an ingest url", field="ingest"
            )
        return IngestUrl.parse(fallback, "ingest")

    @property
    def reference(self):
        return derive_id("target", self.user_id, self.platform, self.ingest.to_string())

    @property
    def max_kbps(self):
        return max_kbps(self.platform)

    def is_custom(self):
        return is_custom(self.platform)

    def publish_url(self):
        """The full URL a worker connects to; contains the secret."""
        return self.ingest.with_key(self.stream_key)

    def enabled_copy(self, enabled):
        return StreamTarget(
            self.user_id,
            self.platform,
            self.stream_key,
            self.ingest,
            enabled,
            self.label,
        )

    def accepts(self, kbps):
        """Whether this target will take a stream at ``kbps``."""
        return kbps <= self.max_kbps

    def to_dict(self, reveal_key=False):
        return {
            "reference": self.reference,
            "user_id": self.user_id,
            "platform": self.platform,
            "ingest": self.ingest.to_string(),
            "stream_key": self.stream_key if reveal_key else masked_key(self.stream_key),
            "enabled": self.enabled,
            "label": self.label,
            "max_kbps": self.max_kbps,
        }

    def __eq__(self, other):
        return (
            isinstance(other, StreamTarget)
            and other.to_dict(True) == self.to_dict(True)
        )

    def __hash__(self):
        return hash(("target", self.reference, self.enabled))

    def __repr__(self):
        return "StreamTarget({}, {})".format(
            self.platform, "on" if self.enabled else "off"
        )


def enabled_targets(targets):
    return tuple(target for target in targets if target.enabled)


def by_platform(targets, platform):
    wanted = normalize_platform(platform)
    return tuple(target for target in targets if target.platform == wanted)


def custom_targets(targets):
    return tuple(target for target in targets if target.platform == CUSTOM)


def duplicate_references(targets):
    """References configured more than once, sorted."""
    seen = {}
    for target in targets:
        seen[target.reference] = seen.get(target.reference, 0) + 1
    return tuple(sorted(key for key, count in seen.items() if count > 1))
