"""The provisioning state machine for a restream server.

A subscription creates a server; the server has to boot before anything can be
pushed to it, and it has to be released when the subscription lapses.  Every
one of those steps has failed in production at least once, so the states are
explicit rather than implied by a nullable column.
"""

from src.domain.core.errors import StateError
from src.domain.core.guards import require_choice, require_int, require_text
from src.domain.core.ids import derive_id
from src.domain.servers.instance import DEFAULT_TYPE, capacity, normalize_type
from src.domain.servers.region import normalize_region
from src.domain.timeline.instant import coerce_instant

REQUESTED = "requested"
PROVISIONING = "provisioning"
READY = "ready"
DRAINING = "draining"
RELEASED = "released"
FAILED = "failed"

STATES = (REQUESTED, PROVISIONING, READY, DRAINING, RELEASED, FAILED)

TRANSITIONS = {
    REQUESTED: (PROVISIONING, FAILED, RELEASED),
    PROVISIONING: (READY, FAILED),
    READY: (DRAINING, FAILED),
    DRAINING: (RELEASED, READY),
    RELEASED: (),
    FAILED: (REQUESTED, RELEASED),
}

USABLE_STATES = (READY,)


class RestreamServer:
    """One relay instance and what it is currently doing."""

    __slots__ = (
        "subscription_reference",
        "region",
        "instance_type",
        "state",
        "requested_at",
        "image_id",
        "assigned",
    )

    def __init__(
        self,
        subscription_reference,
        region,
        instance_type=DEFAULT_TYPE,
        state=REQUESTED,
        requested_at=None,
        image_id=None,
        assigned=0,
    ):
        self.subscription_reference = require_text(
            subscription_reference, "subscription_reference", max_length=64
        )
        self.region = normalize_region(region)
        self.instance_type = normalize_type(instance_type)
        self.state = require_choice(state, "state", STATES)
        self.requested_at = (
            coerce_instant(requested_at, "requested_at") if requested_at else None
        )
        self.image_id = (
            require_text(image_id, "image_id", max_length=40) if image_id else None
        )
        self.assigned = require_int(
            assigned, "assigned", minimum=0, maximum=capacity(self.instance_type)
        )

    @property
    def name(self):
        return "vs-{}-{}".format(
            self.region, derive_id("server", self.subscription_reference)[:10]
        )

    @property
    def capacity(self):
        return capacity(self.instance_type)

    @property
    def free_slots(self):
        return self.capacity - self.assigned

    def _copy(self, **changes):
        payload = {
            "subscription_reference": self.subscription_reference,
            "region": self.region,
            "instance_type": self.instance_type,
            "state": self.state,
            "requested_at": self.requested_at,
            "image_id": self.image_id,
            "assigned": self.assigned,
        }
        payload.update(changes)
        return RestreamServer(**payload)

    def moved_to(self, target, image_id=None):
        if target not in TRANSITIONS[self.state]:
            raise StateError(
                "cannot move a {} server to {}".format(self.state, target),
                current=self.state,
                attempted=target,
            )
        changes = {"state": target}
        if image_id is not None:
            changes["image_id"] = image_id
        if target == RELEASED:
            changes["assigned"] = 0
        return self._copy(**changes)

    def start_provisioning(self):
        return self.moved_to(PROVISIONING)

    def mark_ready(self, image_id):
        return self.moved_to(READY, image_id)

    def drain(self):
        return self.moved_to(DRAINING)

    def release(self):
        return self.moved_to(RELEASED)

    def fail(self):
        return self.moved_to(FAILED)

    def retry(self):
        return self.moved_to(REQUESTED)

    def is_usable(self):
        return self.state in USABLE_STATES

    def has_room(self, wanted=1):
        return self.is_usable() and self.free_slots >= wanted

    def with_assigned(self, count):
        return self._copy(assigned=count)

    def to_dict(self):
        return {
            "name": self.name,
            "subscription_reference": self.subscription_reference,
            "region": self.region,
            "instance_type": self.instance_type,
            "state": self.state,
            "requested_at": self.requested_at.to_iso() if self.requested_at else None,
            "image_id": self.image_id,
            "assigned": self.assigned,
            "capacity": self.capacity,
        }

    def __eq__(self, other):
        return isinstance(other, RestreamServer) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("server", self.name, self.state))

    def __repr__(self):
        return "RestreamServer({}, {})".format(self.name, self.state)
