"""The feature keys a plan can grant.

Feature keys are the vocabulary the rest of the domain uses to ask "is this
allowed" -- ``streaming.custom_rtmp``, ``media.storage_gb`` and so on.  A key is
either a switch or a numeric limit, and mixing the two up is the mistake this
module exists to prevent.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_choice, require_int, require_text

SWITCH = "switch"
LIMIT = "limit"
KINDS = (SWITCH, LIMIT)

UNLIMITED = -1


class Feature:
    """One entry in the feature catalogue."""

    __slots__ = ("key", "kind", "label", "default")

    def __init__(self, key, kind, label=None, default=None):
        self.key = require_text(key, "key", max_length=60).lower()
        self.kind = require_choice(kind, "kind", KINDS)
        self.label = require_text(label or key, "label", max_length=120)
        self.default = self._check_value(default if default is not None else self._fallback())

    def _fallback(self):
        return False if self.kind == SWITCH else 0

    def _check_value(self, value):
        if self.kind == SWITCH:
            if not isinstance(value, bool):
                raise ValidationError(
                    "{} is a switch and needs a boolean".format(self.key), field=self.key
                )
            return value
        number = require_int(value, self.key, minimum=UNLIMITED)
        return number

    def coerce(self, value):
        """Return ``value`` in the shape this feature stores."""
        return self._check_value(value)

    def is_unlimited(self, value):
        return self.kind == LIMIT and self.coerce(value) == UNLIMITED

    def to_dict(self):
        return {
            "key": self.key,
            "kind": self.kind,
            "label": self.label,
            "default": self.default,
        }

    def __eq__(self, other):
        return isinstance(other, Feature) and other.key == self.key

    def __hash__(self):
        return hash(("feature", self.key))

    def __repr__(self):
        return "Feature({!r}, {})".format(self.key, self.kind)


CATALOGUE = (
    Feature("studio.authorized_users", LIMIT, "Authorized studio users", 1),
    Feature("studio.live_minutes_monthly", LIMIT, "Live minutes per month", 300),
    Feature("streaming.targets", LIMIT, "Simultaneous stream targets", 1),
    Feature("streaming.custom_rtmp", SWITCH, "Custom RTMP destinations", False),
    Feature("streaming.restream_server", SWITCH, "Dedicated restream server", False),
    Feature("media.storage_gb", LIMIT, "Media storage in gigabytes", 5),
    Feature("media.intro_outro", SWITCH, "Intro and outro beds", False),
    Feature("media.watermark", SWITCH, "Logo watermark", False),
    Feature("episodes.monthly", LIMIT, "Episodes published per month", 4),
    Feature("episodes.scheduling", SWITCH, "Scheduled publishing", False),
    Feature("distribution.destinations", LIMIT, "Upload destinations", 1),
    Feature("analytics.retention_days", LIMIT, "Analytics retention in days", 30),
)

BY_KEY = {feature.key: feature for feature in CATALOGUE}


def lookup(key, field="feature"):
    """Return the catalogued feature for ``key``."""
    name = require_text(key, field, max_length=60).lower()
    if name not in BY_KEY:
        raise ValidationError(
            "unknown feature {}".format(name),
            field=field,
            details={"known": sorted(BY_KEY)},
        )
    return BY_KEY[name]


def default_values():
    """The feature map a customer with no plan at all is entitled to."""
    return {feature.key: feature.default for feature in CATALOGUE}


def switch_keys():
    return tuple(feature.key for feature in CATALOGUE if feature.kind == SWITCH)


def limit_keys():
    return tuple(feature.key for feature in CATALOGUE if feature.kind == LIMIT)
