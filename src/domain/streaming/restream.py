"""Deciding what actually gets pushed where.

The customer may have configured ten destinations, but the plan caps how many
run at once, some of them cannot take the bitrate the encoder is producing, and
custom RTMP is a paid feature.  The plan below is the single answer to "what
happens when I go live".
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int
from src.domain.streaming.platform import CUSTOM
from src.domain.streaming.target import enabled_targets

INCLUDED = "included"
SKIPPED_DISABLED = "disabled"
SKIPPED_BITRATE = "bitrate_exceeds_platform"
SKIPPED_LIMIT = "plan_target_limit"
SKIPPED_FEATURE = "custom_rtmp_not_included"

REASONS = (INCLUDED, SKIPPED_DISABLED, SKIPPED_BITRATE, SKIPPED_LIMIT, SKIPPED_FEATURE)


class RestreamPlan:
    """Which targets a session fans out to, and why the rest were dropped."""

    __slots__ = ("decisions", "kbps")

    def __init__(self, decisions, kbps):
        self.decisions = tuple(decisions)
        self.kbps = require_int(kbps, "kbps", minimum=1)

    @property
    def included(self):
        return tuple(
            target for target, reason in self.decisions if reason == INCLUDED
        )

    @property
    def skipped(self):
        return tuple(
            (target, reason) for target, reason in self.decisions if reason != INCLUDED
        )

    def reason_for(self, reference):
        for target, reason in self.decisions:
            if target.reference == reference:
                return reason
        return None

    def total_egress_kbps(self):
        return self.kbps * len(self.included)

    def is_empty(self):
        return not self.included

    def to_dict(self):
        return {
            "kbps": self.kbps,
            "included": [target.to_dict() for target in self.included],
            "skipped": [
                {"target": target.to_dict(), "reason": reason}
                for target, reason in self.skipped
            ],
            "total_egress_kbps": self.total_egress_kbps(),
        }

    def __len__(self):
        return len(self.included)

    def __eq__(self, other):
        return isinstance(other, RestreamPlan) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("plan", self.kbps, tuple(t.reference for t in self.included)))

    def __repr__(self):
        return "RestreamPlan({} of {})".format(len(self.included), len(self.decisions))


def build_plan(targets, kbps, entitlement=None):
    """Work out which of ``targets`` a session at ``kbps`` will reach."""
    rate = require_int(kbps, "kbps", minimum=1)
    limit = None
    allow_custom = True
    if entitlement is not None:
        limit = entitlement.limit("streaming.targets")
        allow_custom = entitlement.allows("streaming.custom_rtmp")
    decisions = []
    admitted = 0
    for target in targets:
        if not target.enabled:
            decisions.append((target, SKIPPED_DISABLED))
            continue
        if target.platform == CUSTOM and not allow_custom:
            decisions.append((target, SKIPPED_FEATURE))
            continue
        if not target.accepts(rate):
            decisions.append((target, SKIPPED_BITRATE))
            continue
        if limit is not None and limit >= 0 and admitted >= limit:
            decisions.append((target, SKIPPED_LIMIT))
            continue
        decisions.append((target, INCLUDED))
        admitted += 1
    return RestreamPlan(decisions, rate)


def highest_common_kbps(targets):
    """The fastest rate every enabled target will accept."""
    live = enabled_targets(targets)
    if not live:
        return None
    return min(target.max_kbps for target in live)


def unreachable_at(targets, kbps):
    """Enabled targets that would refuse a stream at ``kbps``."""
    return tuple(
        target for target in enabled_targets(targets) if not target.accepts(kbps)
    )


def describe_reason(reason):
    if reason not in REASONS:
        raise ValidationError("unknown reason {}".format(reason), field="reason")
    return {
        INCLUDED: "streaming",
        SKIPPED_DISABLED: "switched off by the customer",
        SKIPPED_BITRATE: "the platform caps the incoming bitrate",
        SKIPPED_LIMIT: "the plan allows fewer simultaneous targets",
        SKIPPED_FEATURE: "custom RTMP is not part of this plan",
    }[reason]
