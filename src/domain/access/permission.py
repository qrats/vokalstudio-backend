"""Permissions.

A permission is a ``resource:action`` pair.  The wildcard ``*`` is allowed in
either half, which is how the administrator role is expressed without listing
every resource the studio will ever grow.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text

WILDCARD = "*"

RESOURCES = (
    "episodes",
    "media",
    "media_configuration",
    "streaming_platforms",
    "uploading_platforms",
    "restream_servers",
    "authorized_users",
    "subscriptions",
    "payments",
    "plans",
    "products",
    "blogs",
    "users",
    "analytics",
)

ACTIONS = ("read", "create", "update", "delete", "publish", "invite")


class Permission:
    """One ``resource:action`` grant."""

    __slots__ = ("resource", "action")

    def __init__(self, resource, action):
        self.resource = self._check(resource, "resource", RESOURCES)
        self.action = self._check(action, "action", ACTIONS)

    @staticmethod
    def _check(value, field, allowed):
        text = require_text(value, field, max_length=40).lower()
        if text != WILDCARD and text not in allowed:
            raise ValidationError(
                "unknown {} {}".format(field, text),
                field=field,
                details={"allowed": sorted(allowed) + [WILDCARD]},
            )
        return text

    @classmethod
    def parse(cls, text, field="permission"):
        raw = require_text(text, field)
        if raw.count(":") != 1:
            raise ValidationError(
                "{} must look like resource:action".format(field), field=field
            )
        resource, _, action = raw.partition(":")
        return cls(resource, action)

    def covers(self, other):
        """Whether holding this permission implies holding ``other``."""
        if self.resource != WILDCARD and self.resource != other.resource:
            return False
        if self.action != WILDCARD and self.action != other.action:
            return False
        return True

    def is_wildcard(self):
        return WILDCARD in (self.resource, self.action)

    def to_string(self):
        return "{}:{}".format(self.resource, self.action)

    def to_dict(self):
        return {"resource": self.resource, "action": self.action}

    def __eq__(self, other):
        return (
            isinstance(other, Permission)
            and other.resource == self.resource
            and other.action == self.action
        )

    def __lt__(self, other):
        return self.to_string() < other.to_string()

    def __hash__(self):
        return hash(("permission", self.resource, self.action))

    def __repr__(self):
        return "Permission({!r})".format(self.to_string())


class PermissionSet:
    """An immutable, de-duplicated set of permissions."""

    __slots__ = ("permissions",)

    def __init__(self, permissions=()):
        parsed = []
        for entry in permissions:
            parsed.append(entry if isinstance(entry, Permission) else Permission.parse(entry))
        self.permissions = tuple(sorted(set(parsed)))

    @classmethod
    def everything(cls):
        return cls([Permission(WILDCARD, WILDCARD)])

    def allows(self, permission):
        wanted = (
            permission if isinstance(permission, Permission) else Permission.parse(permission)
        )
        return any(held.covers(wanted) for held in self.permissions)

    def union(self, other):
        return PermissionSet(self.permissions + other.permissions)

    def without(self, permission):
        wanted = (
            permission if isinstance(permission, Permission) else Permission.parse(permission)
        )
        return PermissionSet(held for held in self.permissions if held != wanted)

    def resources(self):
        return tuple(sorted({held.resource for held in self.permissions}))

    def to_list(self):
        return [held.to_string() for held in self.permissions]

    def __len__(self):
        return len(self.permissions)

    def __iter__(self):
        return iter(self.permissions)

    def __eq__(self, other):
        return isinstance(other, PermissionSet) and other.permissions == self.permissions

    def __hash__(self):
        return hash(("permission_set", self.permissions))

    def __repr__(self):
        return "PermissionSet({})".format(self.to_list())
