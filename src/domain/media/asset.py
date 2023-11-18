"""Media objects.

An asset is one uploaded file: where it lives, what it is, and enough technical
detail to decide whether it can be used where the customer wants to use it.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_text
from src.domain.core.ids import derive_id
from src.domain.media.format import (
    AUDIO,
    IMAGE,
    VIDEO,
    container_from_filename,
    extension_of,
    kind_of,
    normalize_container,
)
from src.domain.timeline.duration import Duration, coerce_duration

BYTES_PER_GIGABYTE = 1024 ** 3

ROLES = (
    "main",
    "intro",
    "outro",
    "bumper",
    "logo",
    "artwork",
    "transcript",
)


class Asset:
    """One stored media object."""

    __slots__ = (
        "user_id",
        "name",
        "container",
        "size_bytes",
        "duration",
        "role",
        "checksum",
    )

    def __init__(
        self,
        user_id,
        name,
        size_bytes,
        container=None,
        duration=None,
        role="main",
        checksum=None,
    ):
        self.user_id = require_text(user_id, "user_id", max_length=64)
        self.name = require_text(name, "name", max_length=255)
        self.container = (
            normalize_container(container)
            if container
            else container_from_filename(self.name)
        )
        self.size_bytes = require_int(size_bytes, "size_bytes", minimum=1)
        self.role = self._check_role(role)
        self.duration = self._check_duration(duration)
        self.checksum = (
            require_text(checksum, "checksum", min_length=32, max_length=64)
            if checksum
            else None
        )

    def _check_role(self, role):
        name = require_text(role, "role", max_length=20).lower()
        if name not in ROLES:
            raise ValidationError(
                "unknown role {}".format(name),
                field="role",
                details={"allowed": sorted(ROLES)},
            )
        return name

    def _check_duration(self, duration):
        if self.kind == IMAGE:
            if duration is not None:
                raise ValidationError("an image has no duration", field="duration")
            return None
        if duration is None:
            raise ValidationError(
                "{} assets need a duration".format(self.kind), field="duration"
            )
        value = coerce_duration(duration, "duration")
        if value.is_zero():
            raise ValidationError("duration must be positive", field="duration")
        return value

    @property
    def kind(self):
        return kind_of(self.container)

    @property
    def key(self):
        """The object key this asset is stored under."""
        return "{}/{}.{}".format(
            self.user_id,
            derive_id("asset", self.user_id, self.name, self.size_bytes),
            extension_of(self.container),
        )

    def size_gigabytes(self):
        """Storage footprint, rounded up to whole gigabytes."""
        return -(-self.size_bytes // BYTES_PER_GIGABYTE)

    def is_audio(self):
        return self.kind == AUDIO

    def is_video(self):
        return self.kind == VIDEO

    def is_image(self):
        return self.kind == IMAGE

    def bitrate_bps(self):
        """Average bitrate, or ``None`` for an image."""
        if self.duration is None or self.duration.is_zero():
            return None
        return self.size_bytes * 8 * 1000 // self.duration.millis

    def with_role(self, role):
        return Asset(
            self.user_id,
            self.name,
            self.size_bytes,
            self.container,
            self.duration,
            role,
            self.checksum,
        )

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "container": self.container,
            "kind": self.kind,
            "size_bytes": self.size_bytes,
            "duration_millis": self.duration.millis if self.duration else None,
            "role": self.role,
            "checksum": self.checksum,
            "key": self.key,
        }

    @classmethod
    def from_dict(cls, payload):
        return cls(
            payload["user_id"],
            payload["name"],
            payload["size_bytes"],
            payload.get("container"),
            payload.get("duration_millis"),
            payload.get("role", "main"),
            payload.get("checksum"),
        )

    def __eq__(self, other):
        return isinstance(other, Asset) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("asset", self.key))

    def __repr__(self):
        return "Asset({!r}, {})".format(self.name, self.kind)


def total_bytes(assets):
    return sum(asset.size_bytes for asset in assets)


def total_duration(assets):
    millis = 0
    for asset in assets:
        if asset.duration is not None:
            millis += asset.duration.millis
    return Duration(millis)


def by_role(assets, role):
    return tuple(asset for asset in assets if asset.role == role)


def storage_used_gb(assets):
    """Whole gigabytes used, rounded up over the whole library."""
    return -(-total_bytes(assets) // BYTES_PER_GIGABYTE)
