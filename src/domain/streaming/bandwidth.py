"""Estimating what a session costs in bytes.

Used both to warn a customer before they go live and to attribute egress after
the fact.
"""

from src.domain.core.guards import require_int
from src.domain.timeline.duration import coerce_duration

BITS_PER_BYTE = 8
BYTES_PER_GIGABYTE = 1024 ** 3


def bytes_for(kbps, duration):
    """Bytes transferred at ``kbps`` for ``duration``."""
    rate = require_int(kbps, "kbps", minimum=1)
    length = coerce_duration(duration, "duration")
    return rate * 1000 * length.millis // (BITS_PER_BYTE * 1000)


def gigabytes_for(kbps, duration):
    """The same figure in gigabytes, rounded up."""
    return -(-bytes_for(kbps, duration) // BYTES_PER_GIGABYTE)


def session_egress_bytes(plan, duration):
    """Total bytes a restream plan pushes over ``duration``."""
    return bytes_for(plan.total_egress_kbps(), duration) if len(plan) else 0


def fits_upstream(plan, upstream_kbps):
    """Whether the fan-out fits the customer's upstream link."""
    return plan.total_egress_kbps() <= require_int(
        upstream_kbps, "upstream_kbps", minimum=1
    )


def headroom_kbps(plan, upstream_kbps):
    """Spare upstream after the fan-out, never negative."""
    return max(
        0,
        require_int(upstream_kbps, "upstream_kbps", minimum=1)
        - plan.total_egress_kbps(),
    )


def max_targets_for(kbps, upstream_kbps):
    """How many copies of a ``kbps`` stream an upstream link can carry."""
    rate = require_int(kbps, "kbps", minimum=1)
    return require_int(upstream_kbps, "upstream_kbps", minimum=1) // rate
