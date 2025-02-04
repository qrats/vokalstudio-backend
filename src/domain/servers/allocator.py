"""Deciding which server a subscription gets.

Reuse a server the subscription already owns, then a nearby one with room, then
ask for a new one.  The size asked for depends on the fan-out the customer has
configured, which is why this lives next to the pool rather than in a resource.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int
from src.domain.servers.instance import DEFAULT_TYPE, smallest_for
from src.domain.servers.lifecycle import RestreamServer
from src.domain.servers.region import latency_millis, normalize_region

REUSED = "reused"
SHARED = "shared"
PROVISION = "provision"
REFUSED = "refused"

MAX_ACCEPTABLE_LATENCY = 120


class Allocation:
    """What the allocator decided, and why."""

    __slots__ = ("outcome", "server", "instance_type", "reason")

    def __init__(self, outcome, server=None, instance_type=None, reason=None):
        if outcome not in (REUSED, SHARED, PROVISION, REFUSED):
            raise ValidationError("unknown outcome {}".format(outcome), field="outcome")
        self.outcome = outcome
        self.server = server
        self.instance_type = instance_type
        self.reason = reason

    @property
    def needs_provisioning(self):
        return self.outcome == PROVISION

    @property
    def satisfied(self):
        return self.outcome in (REUSED, SHARED)

    def to_dict(self):
        return {
            "outcome": self.outcome,
            "server": self.server.to_dict() if self.server else None,
            "instance_type": self.instance_type,
            "reason": self.reason,
        }

    def __eq__(self, other):
        return isinstance(other, Allocation) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("allocation", self.outcome, self.instance_type, self.reason))

    def __repr__(self):
        return "Allocation({})".format(self.outcome)


def allocate(pool, subscription_reference, origin_region, targets, kbps=None):
    """Choose a server for one subscription's fan-out."""
    wanted = require_int(targets, "targets", minimum=1)
    origin = normalize_region(origin_region, "origin_region")
    own = [
        server
        for server in pool.for_subscription(subscription_reference)
        if server.has_room(wanted)
    ]
    if own:
        best = sorted(own, key=lambda server: (latency_millis(origin, server.region), server.name))[0]
        return Allocation(REUSED, best, best.instance_type, "already provisioned")
    nearby = pool.nearest_usable(origin, wanted)
    if nearby is not None and latency_millis(origin, nearby.region) <= MAX_ACCEPTABLE_LATENCY:
        return Allocation(SHARED, nearby, nearby.instance_type, "spare capacity nearby")
    size = smallest_for(wanted, kbps)
    if size is None:
        return Allocation(REFUSED, None, None, "no instance type is large enough")
    return Allocation(PROVISION, None, size, "no server with room in range")


def request_server(allocation, subscription_reference, region, requested_at=None):
    """Turn a ``provision`` decision into a server record."""
    if not allocation.needs_provisioning:
        raise ValidationError("allocation does not ask for a server", field="allocation")
    return RestreamServer(
        subscription_reference,
        region,
        allocation.instance_type or DEFAULT_TYPE,
        requested_at=requested_at,
    )


def release_for(pool, subscription_reference):
    """Drain every server a lapsed subscription still holds."""
    updated = pool
    for server in pool.for_subscription(subscription_reference):
        if server.state in ("released", "draining"):
            continue
        target = server.drain() if server.is_usable() else server.release()
        updated = updated.replace(target)
    return updated
