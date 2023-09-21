"""Putting roles, grants and entitlements together.

A request is allowed when the actor's role carries the permission *and* the
plan the studio owner pays for includes the feature it needs.  Both halves have
to be checked, and forgetting the second is how a cancelled account kept
streaming.
"""

from src.domain.access.grant import grants_for
from src.domain.access.role import ADMIN, OWNER, can, normalize_role
from src.domain.core.errors import PermissionError_
from src.domain.core.guards import require_text

FEATURE_BY_PERMISSION = {
    "streaming_platforms:create": "streaming.targets",
    "restream_servers:read": "streaming.restream_server",
    "media_configuration:update": "media.intro_outro",
    "authorized_users:invite": "studio.authorized_users",
    "episodes:publish": "episodes.monthly",
}


class Actor:
    """Who is making the request and on whose studio."""

    __slots__ = ("user_id", "role", "owner_id")

    def __init__(self, user_id, role, owner_id=None):
        self.user_id = require_text(user_id, "user_id", max_length=64)
        self.role = normalize_role(role)
        self.owner_id = (
            require_text(owner_id, "owner_id", max_length=64) if owner_id else self.user_id
        )

    @property
    def is_administrator(self):
        return self.role == ADMIN

    @property
    def owns_the_studio(self):
        return self.owner_id == self.user_id

    def to_dict(self):
        return {"user_id": self.user_id, "role": self.role, "owner_id": self.owner_id}

    def __eq__(self, other):
        return isinstance(other, Actor) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("actor", self.user_id, self.role, self.owner_id))

    def __repr__(self):
        return "Actor({}, {})".format(self.user_id, self.role)


class Decision:
    """The outcome of one authorisation check."""

    __slots__ = ("allowed", "reason", "permission")

    def __init__(self, allowed, permission, reason=None):
        self.allowed = bool(allowed)
        self.permission = permission
        self.reason = reason

    def raise_if_denied(self, subject=None):
        if not self.allowed:
            raise PermissionError_(
                self.reason or "not allowed", action=self.permission, subject=subject
            )
        return True

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "permission": self.permission,
            "reason": self.reason,
        }

    def __bool__(self):
        return self.allowed

    def __eq__(self, other):
        return isinstance(other, Decision) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("decision", self.allowed, self.permission, self.reason))

    def __repr__(self):
        return "Decision({}, {})".format(self.allowed, self.permission)


def decide(actor, permission, grants=(), entitlement=None, episode_id=None, on=None):
    """Decide whether ``actor`` may perform ``permission``."""
    if actor.is_administrator:
        return Decision(True, permission, "administrator")
    if actor.owns_the_studio:
        if not can(actor.role, permission):
            return Decision(False, permission, "role does not carry this permission")
    else:
        held = grants_for(grants, actor.user_id, on)
        matching = [
            grant
            for grant in held
            if grant.owner_id == actor.owner_id
            and grant.allows(permission, episode_id, on)
        ]
        if not matching:
            return Decision(False, permission, "no grant covers this studio")
    feature = FEATURE_BY_PERMISSION.get(permission)
    if feature and entitlement is not None:
        from src.domain.catalog.feature import SWITCH, lookup

        if lookup(feature).kind == SWITCH and not entitlement.allows(feature):
            return Decision(False, permission, "plan does not include {}".format(feature))
    return Decision(True, permission, None)


def require(actor, permission, **kwargs):
    return decide(actor, permission, **kwargs).raise_if_denied(actor.user_id)


def owner_actor(user_id):
    return Actor(user_id, OWNER)
