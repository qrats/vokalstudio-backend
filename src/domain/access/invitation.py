"""Invitations.

An invitation is a signed intent to create a :class:`~src.domain.access.grant.Grant`.
The token is derived from the invitation's own fields, so a tampered link fails
verification without a database round trip.
"""

from src.domain.access.role import GUEST, normalize_role
from src.domain.core.errors import StateError, ValidationError
from src.domain.core.guards import require_choice, require_int, require_text
from src.domain.core.ids import derive_id
from src.domain.timeline.calendar import add_days, parse_date

PENDING = "pending"
ACCEPTED = "accepted"
DECLINED = "declined"
REVOKED = "revoked"
LAPSED = "lapsed"

STATES = (PENDING, ACCEPTED, DECLINED, REVOKED, LAPSED)
TERMINAL = (ACCEPTED, DECLINED, REVOKED, LAPSED)

DEFAULT_VALID_DAYS = 7


class Invitation:
    """An outstanding offer of studio access."""

    __slots__ = ("owner_id", "email", "role", "issued_on", "valid_days", "state")

    def __init__(
        self,
        owner_id,
        email,
        role=GUEST,
        issued_on=None,
        valid_days=DEFAULT_VALID_DAYS,
        state=PENDING,
    ):
        self.owner_id = require_text(owner_id, "owner_id", max_length=64)
        self.email = self._check_email(email)
        self.role = normalize_role(role)
        self.issued_on = parse_date(issued_on, "issued_on") if issued_on else None
        self.valid_days = require_int(valid_days, "valid_days", minimum=1, maximum=90)
        self.state = require_choice(state, "state", STATES)

    @staticmethod
    def _check_email(email):
        text = require_text(email, "email", max_length=254).lower()
        local, separator, domain = text.partition("@")
        if not separator or not local or "." not in domain or domain.startswith("."):
            raise ValidationError("email is not valid", field="email")
        return text

    @property
    def token(self):
        """A stable token derived from the invitation itself."""
        return derive_id(
            "invitation",
            self.owner_id,
            self.email,
            self.role,
            self.issued_on.isoformat() if self.issued_on else "",
        )

    def verify(self, token):
        return token == self.token

    def expires_on(self):
        if self.issued_on is None:
            return None
        return add_days(self.issued_on, self.valid_days)

    def is_expired(self, on):
        expiry = self.expires_on()
        if expiry is None:
            return False
        return parse_date(on, "on") >= expiry

    def is_open(self, on=None):
        if self.state != PENDING:
            return False
        return not (on is not None and self.is_expired(on))

    def _moved_to(self, state):
        if self.state in TERMINAL:
            raise StateError(
                "invitation is already {}".format(self.state),
                current=self.state,
                attempted=state,
            )
        return Invitation(
            self.owner_id, self.email, self.role, self.issued_on, self.valid_days, state
        )

    def accept(self, on=None):
        if on is not None and self.is_expired(on):
            raise StateError("invitation has lapsed", current=LAPSED, attempted=ACCEPTED)
        return self._moved_to(ACCEPTED)

    def decline(self):
        return self._moved_to(DECLINED)

    def revoke(self):
        return self._moved_to(REVOKED)

    def lapse(self):
        return self._moved_to(LAPSED)

    def to_grant(self, subject_id, on=None):
        """Build the grant this invitation stands for."""
        if not self.is_open(on):
            raise StateError(
                "invitation cannot be redeemed", current=self.state, attempted="grant"
            )
        from src.domain.access.grant import Grant

        return Grant(self.owner_id, subject_id, self.role, granted_on=on)

    def to_dict(self):
        return {
            "owner_id": self.owner_id,
            "email": self.email,
            "role": self.role,
            "issued_on": self.issued_on.isoformat() if self.issued_on else None,
            "valid_days": self.valid_days,
            "state": self.state,
            "token": self.token,
        }

    def __eq__(self, other):
        return isinstance(other, Invitation) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("invitation", self.token, self.state))

    def __repr__(self):
        return "Invitation({!r}, {})".format(self.email, self.state)


def open_invitations(invitations, on=None):
    return tuple(invite for invite in invitations if invite.is_open(on))


def lapse_stale(invitations, on):
    """Move every expired pending invitation to ``lapsed``."""
    updated = []
    for invite in invitations:
        if invite.state == PENDING and invite.is_expired(on):
            updated.append(invite.lapse())
        else:
            updated.append(invite)
    return tuple(updated)
