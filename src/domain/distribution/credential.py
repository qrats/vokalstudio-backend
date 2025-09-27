"""OAuth credentials for a destination.

The tokens themselves live in the database; what belongs here is when one has
to be refreshed and whether it still covers the scopes an upload needs.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_sequence, require_text
from src.domain.core.text import mask
from src.domain.distribution.destination import needs_oauth, normalize_destination
from src.domain.timeline.instant import coerce_instant

REFRESH_MARGIN_SECONDS = 300

REQUIRED_SCOPES = {
    "podbean": ("episode_publish",),
    "spotify": ("upload", "read"),
    "youtube": ("youtube.upload",),
}


class Credential:
    """One stored OAuth grant."""

    __slots__ = ("user_id", "destination", "token", "refresh_token", "issued_at", "expires_in", "scopes")

    def __init__(
        self,
        user_id,
        destination,
        token,
        issued_at,
        expires_in=3600,
        refresh_token=None,
        scopes=(),
    ):
        self.user_id = require_text(user_id, "user_id", max_length=64)
        self.destination = normalize_destination(destination)
        if not needs_oauth(self.destination):
            raise ValidationError(
                "{} does not use OAuth".format(self.destination), field="destination"
            )
        self.token = require_text(token, "token", min_length=8, max_length=2048)
        self.issued_at = coerce_instant(issued_at, "issued_at")
        self.expires_in = require_int(expires_in, "expires_in", minimum=1)
        self.refresh_token = (
            require_text(refresh_token, "refresh_token", min_length=8, max_length=2048)
            if refresh_token
            else None
        )
        wanted = require_sequence(scopes, "scopes")
        cleaned = []
        for scope in wanted:
            text = require_text(scope, "scopes", max_length=80).lower()
            if text not in cleaned:
                cleaned.append(text)
        self.scopes = tuple(sorted(cleaned))

    def expires_at(self):
        return self.issued_at.plus_seconds(self.expires_in)

    def is_expired(self, now):
        return coerce_instant(now, "now") >= self.expires_at()

    def needs_refresh(self, now, margin_seconds=REFRESH_MARGIN_SECONDS):
        margin = require_int(margin_seconds, "margin_seconds", minimum=0)
        return coerce_instant(now, "now").plus_seconds(margin) >= self.expires_at()

    def can_refresh(self):
        return self.refresh_token is not None

    def missing_scopes(self):
        """Scopes this destination needs that the grant does not carry."""
        wanted = REQUIRED_SCOPES.get(self.destination, ())
        return tuple(sorted(scope for scope in wanted if scope not in self.scopes))

    def is_usable(self, now):
        return not self.is_expired(now) and not self.missing_scopes()

    def refreshed(self, token, issued_at, expires_in=3600, refresh_token=None):
        if not self.can_refresh():
            raise ValidationError("no refresh token stored", field="refresh_token")
        return Credential(
            self.user_id,
            self.destination,
            token,
            issued_at,
            expires_in,
            refresh_token or self.refresh_token,
            self.scopes,
        )

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "destination": self.destination,
            "token": mask(self.token, keep=4),
            "has_refresh_token": self.can_refresh(),
            "issued_at": self.issued_at.to_iso(),
            "expires_at": self.expires_at().to_iso(),
            "scopes": list(self.scopes),
        }

    def __eq__(self, other):
        return isinstance(other, Credential) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("credential", self.user_id, self.destination, self.issued_at.millis))

    def __repr__(self):
        return "Credential({}, {})".format(self.user_id, self.destination)


def for_destination(credentials, user_id, destination):
    wanted = normalize_destination(destination)
    for credential in credentials:
        if credential.user_id == user_id and credential.destination == wanted:
            return credential
    return None


def due_for_refresh(credentials, now, margin_seconds=REFRESH_MARGIN_SECONDS):
    return tuple(
        credential
        for credential in credentials
        if credential.can_refresh() and credential.needs_refresh(now, margin_seconds)
    )
