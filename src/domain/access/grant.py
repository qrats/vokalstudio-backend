"""Authorized users.

An owner can let somebody else into the studio, optionally restricted to
particular episodes and optionally with an expiry.  The restrictions are the
part that the resources kept getting wrong, so they live here.
"""

from src.domain.access.role import GUEST, normalize_role, permissions_for
from src.domain.core.errors import PermissionError_, ValidationError
from src.domain.core.guards import require_sequence, require_text
from src.domain.core.text import mask
from src.domain.timeline.calendar import parse_date

ALL_EPISODES = "*"


class Grant:
    """One person's access to another person's studio."""

    __slots__ = ("owner_id", "subject_id", "role", "episode_ids", "granted_on", "expires_on")

    def __init__(
        self,
        owner_id,
        subject_id,
        role=GUEST,
        episode_ids=None,
        granted_on=None,
        expires_on=None,
    ):
        self.owner_id = require_text(owner_id, "owner_id", max_length=64)
        self.subject_id = require_text(subject_id, "subject_id", max_length=64)
        if self.owner_id == self.subject_id:
            raise ValidationError("a studio owner needs no grant", field="subject_id")
        self.role = normalize_role(role)
        self.episode_ids = self._check_episodes(episode_ids)
        self.granted_on = parse_date(granted_on, "granted_on") if granted_on else None
        self.expires_on = parse_date(expires_on, "expires_on") if expires_on else None
        if self.granted_on and self.expires_on and self.expires_on <= self.granted_on:
            raise ValidationError(
                "expires_on must follow granted_on", field="expires_on"
            )

    @staticmethod
    def _check_episodes(episode_ids):
        if episode_ids is None:
            return ALL_EPISODES
        if episode_ids == ALL_EPISODES:
            return ALL_EPISODES
        values = require_sequence(episode_ids, "episode_ids", min_length=1)
        cleaned = []
        for value in values:
            identifier = require_text(value, "episode_ids", max_length=64)
            if identifier not in cleaned:
                cleaned.append(identifier)
        return tuple(cleaned)

    @property
    def covers_all_episodes(self):
        return self.episode_ids == ALL_EPISODES

    def is_expired(self, on):
        if self.expires_on is None:
            return False
        return parse_date(on, "on") >= self.expires_on

    def is_active(self, on):
        return not self.is_expired(on)

    def covers_episode(self, episode_id):
        if self.covers_all_episodes:
            return True
        return episode_id in self.episode_ids

    def allows(self, permission, episode_id=None, on=None):
        """Whether this grant permits an action, optionally on one episode."""
        if on is not None and self.is_expired(on):
            return False
        if episode_id is not None and not self.covers_episode(episode_id):
            return False
        return permissions_for(self.role).allows(permission)

    def require(self, permission, episode_id=None, on=None):
        if not self.allows(permission, episode_id, on):
            raise PermissionError_(
                "grant does not allow this action",
                action=permission,
                subject=self.subject_id,
            )
        return True

    def narrowed_to(self, episode_ids):
        return Grant(
            self.owner_id,
            self.subject_id,
            self.role,
            episode_ids,
            self.granted_on,
            self.expires_on,
        )

    def to_dict(self):
        return {
            "owner_id": self.owner_id,
            "subject_id": self.subject_id,
            "role": self.role,
            "episode_ids": (
                ALL_EPISODES if self.covers_all_episodes else list(self.episode_ids)
            ),
            "granted_on": self.granted_on.isoformat() if self.granted_on else None,
            "expires_on": self.expires_on.isoformat() if self.expires_on else None,
        }

    @classmethod
    def from_dict(cls, payload):
        return cls(
            payload["owner_id"],
            payload["subject_id"],
            payload.get("role", GUEST),
            payload.get("episode_ids"),
            payload.get("granted_on"),
            payload.get("expires_on"),
        )

    def __eq__(self, other):
        return isinstance(other, Grant) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("grant", self.owner_id, self.subject_id))

    def __repr__(self):
        return "Grant({} -> {}, {})".format(
            mask(self.owner_id, 4), mask(self.subject_id, 4), self.role
        )


def grants_for(grants, subject_id, on=None):
    """Every active grant handed to one person."""
    return tuple(
        grant
        for grant in grants
        if grant.subject_id == subject_id and (on is None or grant.is_active(on))
    )


def studios_visible_to(grants, subject_id, on=None):
    """The owner ids a person can currently see, sorted."""
    return tuple(
        sorted({grant.owner_id for grant in grants_for(grants, subject_id, on)})
    )
