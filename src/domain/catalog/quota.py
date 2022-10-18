"""Usage counters measured against an entitlement."""

from src.domain.catalog.feature import LIMIT, UNLIMITED, lookup
from src.domain.core.errors import QuotaError
from src.domain.core.guards import require_int, require_mapping


class Usage:
    """How much of each limited feature an account has consumed."""

    __slots__ = ("counts",)

    def __init__(self, counts=None):
        checked = {}
        for key, value in require_mapping(counts or {}, "counts").items():
            feature = lookup(key, "counts")
            if feature.kind != LIMIT:
                raise QuotaError(
                    "{} is not a counted feature".format(feature.key),
                    feature=feature.key,
                )
            checked[feature.key] = require_int(value, feature.key, minimum=0)
        self.counts = checked

    def of(self, key):
        return self.counts.get(lookup(key).key, 0)

    def plus(self, key, amount=1):
        feature = lookup(key)
        counts = dict(self.counts)
        counts[feature.key] = self.of(feature.key) + require_int(
            amount, "amount", minimum=0
        )
        return Usage(counts)

    def reset(self, key):
        counts = dict(self.counts)
        counts.pop(lookup(key).key, None)
        return Usage(counts)

    def to_dict(self):
        return dict(self.counts)

    def __eq__(self, other):
        return isinstance(other, Usage) and other.counts == self.counts

    def __hash__(self):
        return hash(("usage", tuple(sorted(self.counts.items()))))

    def __repr__(self):
        return "Usage({})".format(self.counts)


def headroom(entitlement, usage):
    """Remaining allowance per limited feature; ``None`` where unlimited."""
    report = {}
    for key in sorted(entitlement.values):
        feature = lookup(key)
        if feature.kind != LIMIT:
            continue
        report[key] = entitlement.remaining(key, usage.of(key))
    return report


def exhausted(entitlement, usage):
    """Limited features with nothing left."""
    return tuple(
        key for key, left in sorted(headroom(entitlement, usage).items()) if left == 0
    )


def utilisation(entitlement, usage):
    """Percentage used per limited feature; unlimited features are omitted."""
    report = {}
    for key in sorted(entitlement.values):
        feature = lookup(key)
        if feature.kind != LIMIT:
            continue
        allowance = entitlement.limit(key)
        if allowance == UNLIMITED or allowance == 0:
            continue
        report[key] = round(usage.of(key) * 100.0 / allowance, 2)
    return report
