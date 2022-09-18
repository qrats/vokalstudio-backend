"""Entitlements.

An entitlement is the feature map that actually applies to an account: the
catalogue defaults, overlaid with the plan grants, overlaid with any per-account
override an administrator has set.
"""

from src.domain.catalog.feature import LIMIT, SWITCH, UNLIMITED, BY_KEY, lookup
from src.domain.core.errors import PermissionError_, QuotaError
from src.domain.core.guards import require_int, require_mapping


class Entitlement:
    """The resolved feature map for one account."""

    __slots__ = ("values",)

    def __init__(self, values=None):
        resolved = {feature.key: feature.default for feature in BY_KEY.values()}
        for key, value in require_mapping(values or {}, "values").items():
            feature = lookup(key, "values")
            resolved[feature.key] = feature.coerce(value)
        self.values = resolved

    @classmethod
    def for_plan(cls, plan, overrides=None):
        merged = dict(plan.grants)
        merged.update(require_mapping(overrides or {}, "overrides"))
        return cls(merged)

    @classmethod
    def free(cls):
        return cls()

    def value(self, key):
        return self.values[lookup(key).key]

    def allows(self, key):
        """Whether a switch feature is on."""
        feature = lookup(key)
        if feature.kind != SWITCH:
            raise QuotaError(
                "{} is a limit, not a switch".format(feature.key), feature=feature.key
            )
        return bool(self.values[feature.key])

    def limit(self, key):
        """The numeric limit for a feature; ``-1`` means unlimited."""
        feature = lookup(key)
        if feature.kind != LIMIT:
            raise QuotaError(
                "{} is a switch, not a limit".format(feature.key), feature=feature.key
            )
        return self.values[feature.key]

    def is_unlimited(self, key):
        return self.limit(key) == UNLIMITED

    def remaining(self, key, used):
        """How much of a limit is left; ``None`` when unlimited."""
        allowance = self.limit(key)
        count = require_int(used, "used", minimum=0)
        if allowance == UNLIMITED:
            return None
        return max(0, allowance - count)

    def check(self, key, used=0, wanted=1):
        """Raise unless ``wanted`` more units of ``key`` may be consumed."""
        feature = lookup(key)
        if feature.kind == SWITCH:
            if not self.values[feature.key]:
                raise PermissionError_(
                    "{} is not included in this plan".format(feature.key),
                    action=feature.key,
                )
            return True
        allowance = self.values[feature.key]
        if allowance == UNLIMITED:
            return True
        count = require_int(used, "used", minimum=0)
        extra = require_int(wanted, "wanted", minimum=0)
        if count + extra > allowance:
            raise QuotaError(
                "{} limit reached".format(feature.key),
                feature=feature.key,
                limit=allowance,
                used=count,
            )
        return True

    def merged_with(self, overrides):
        merged = dict(self.values)
        for key, value in require_mapping(overrides, "overrides").items():
            feature = lookup(key, "overrides")
            merged[feature.key] = feature.coerce(value)
        return Entitlement(merged)

    def difference(self, other):
        """The keys where ``other`` grants something different."""
        return {
            key: (self.values[key], other.values[key])
            for key in sorted(self.values)
            if self.values[key] != other.values[key]
        }

    def to_dict(self):
        return dict(self.values)

    def __eq__(self, other):
        return isinstance(other, Entitlement) and other.values == self.values

    def __hash__(self):
        return hash(("entitlement", tuple(sorted(self.values.items()))))

    def __repr__(self):
        return "Entitlement({} keys)".format(len(self.values))
