"""Roles.

The API has three built-in roles plus the per-episode grants an owner hands to
a guest; a role is just a named :class:`PermissionSet` so that both go through
the same check.
"""

from src.domain.access.permission import Permission, PermissionSet
from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text

ADMIN = "admin"
OWNER = "owner"
PRODUCER = "producer"
GUEST = "guest"
VIEWER = "viewer"

_OWNER_PERMISSIONS = (
    "episodes:read",
    "episodes:create",
    "episodes:update",
    "episodes:delete",
    "episodes:publish",
    "media:read",
    "media:create",
    "media:update",
    "media:delete",
    "media_configuration:read",
    "media_configuration:update",
    "streaming_platforms:read",
    "streaming_platforms:create",
    "streaming_platforms:update",
    "streaming_platforms:delete",
    "uploading_platforms:read",
    "uploading_platforms:create",
    "uploading_platforms:update",
    "uploading_platforms:delete",
    "restream_servers:read",
    "authorized_users:read",
    "authorized_users:invite",
    "authorized_users:delete",
    "subscriptions:read",
    "payments:read",
    "analytics:read",
)

_PRODUCER_PERMISSIONS = (
    "episodes:read",
    "episodes:create",
    "episodes:update",
    "episodes:publish",
    "media:read",
    "media:create",
    "media:update",
    "media_configuration:read",
    "streaming_platforms:read",
    "uploading_platforms:read",
    "analytics:read",
)

_GUEST_PERMISSIONS = (
    "episodes:read",
    "media:read",
    "streaming_platforms:read",
)

_VIEWER_PERMISSIONS = ("episodes:read", "analytics:read")

ROLES = {
    ADMIN: PermissionSet.everything(),
    OWNER: PermissionSet(_OWNER_PERMISSIONS),
    PRODUCER: PermissionSet(_PRODUCER_PERMISSIONS),
    GUEST: PermissionSet(_GUEST_PERMISSIONS),
    VIEWER: PermissionSet(_VIEWER_PERMISSIONS),
}

RANK = (VIEWER, GUEST, PRODUCER, OWNER, ADMIN)


def normalize_role(role, field="role"):
    name = require_text(role, field, max_length=20).lower()
    if name not in ROLES:
        raise ValidationError(
            "unknown role {}".format(name),
            field=field,
            details={"allowed": sorted(ROLES)},
        )
    return name


def permissions_for(role):
    return ROLES[normalize_role(role)]

def outranks(role, other):
    """Whether ``role`` sits above ``other`` in the built-in hierarchy."""
    return RANK.index(normalize_role(role)) > RANK.index(normalize_role(other, "other"))


def highest(roles, default=VIEWER):
    """The most privileged role in ``roles``."""
    best = None
    for role in roles:
        name = normalize_role(role)
        if best is None or RANK.index(name) > RANK.index(best):
            best = name
    return best if best is not None else default


def can(role, permission):
    """Whether a built-in role carries ``permission``."""
    return permissions_for(role).allows(permission)


def describe(role):
    """The permissions a role carries, as sorted strings."""
    return tuple(permissions_for(role).to_list())


def custom_role(base, added=(), removed=()):
    """A permission set derived from a built-in role."""
    rights = permissions_for(base).union(PermissionSet(added))
    for entry in removed:
        rights = rights.without(
            entry if isinstance(entry, Permission) else Permission.parse(entry)
        )
    return rights
