"""Access and refresh tokens.

The Flask app stores revoked JTIs in the database; the rules about what a token
claims and when it stops being usable are here so they can be tested without
one.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_choice, require_int, require_text
from src.domain.core.ids import derive_id
from src.domain.timeline.instant import coerce_instant

ACCESS = "access"
REFRESH = "refresh"
KINDS = (ACCESS, REFRESH)

ACCESS_TTL_SECONDS = 15 * 60
REFRESH_TTL_SECONDS = 30 * 24 * 3600


class TokenClaims:
    """What a token asserts, independent of how it is signed."""

    __slots__ = ("subject", "kind", "issued_at", "ttl_seconds", "scopes")

    def __init__(self, subject, kind, issued_at, ttl_seconds=None, scopes=()):
        self.subject = require_text(subject, "subject", max_length=64)
        self.kind = require_choice(kind, "kind", KINDS)
        self.issued_at = coerce_instant(issued_at, "issued_at")
        default = ACCESS_TTL_SECONDS if self.kind == ACCESS else REFRESH_TTL_SECONDS
        self.ttl_seconds = require_int(
            default if ttl_seconds is None else ttl_seconds,
            "ttl_seconds",
            minimum=1,
        )
        cleaned = []
        for scope in scopes:
            text = require_text(scope, "scopes", max_length=60).lower()
            if text not in cleaned:
                cleaned.append(text)
        self.scopes = tuple(sorted(cleaned))

    @property
    def jti(self):
        return derive_id("jti", self.subject, self.kind, self.issued_at.millis)

    def expires_at(self):
        return self.issued_at.plus_seconds(self.ttl_seconds)

    def is_expired(self, now):
        return coerce_instant(now, "now") >= self.expires_at()

    def seconds_left(self, now):
        remaining = self.expires_at().difference_millis(coerce_instant(now, "now"))
        return max(0, remaining // 1000)

    def has_scope(self, scope):
        return require_text(scope, "scope").lower() in self.scopes

    def to_dict(self):
        return {
            "sub": self.subject,
            "type": self.kind,
            "jti": self.jti,
            "iat": self.issued_at.millis // 1000,
            "exp": self.expires_at().millis // 1000,
            "scopes": list(self.scopes),
        }

    def __eq__(self, other):
        return isinstance(other, TokenClaims) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("claims", self.jti))

    def __repr__(self):
        return "TokenClaims({}, {})".format(self.subject, self.kind)


class Blacklist:
    """The set of revoked token identifiers."""

    __slots__ = ("jtis",)

    def __init__(self, jtis=()):
        cleaned = set()
        for jti in jtis:
            cleaned.add(require_text(jti, "jtis", max_length=64))
        self.jtis = frozenset(cleaned)

    def with_revoked(self, claims_or_jti):
        jti = (
            claims_or_jti.jti
            if isinstance(claims_or_jti, TokenClaims)
            else require_text(claims_or_jti, "jti", max_length=64)
        )
        return Blacklist(set(self.jtis) | {jti})

    def is_revoked(self, claims_or_jti):
        jti = (
            claims_or_jti.jti
            if isinstance(claims_or_jti, TokenClaims)
            else claims_or_jti
        )
        return jti in self.jtis

    def __len__(self):
        return len(self.jtis)

    def __eq__(self, other):
        return isinstance(other, Blacklist) and other.jtis == self.jtis

    def __hash__(self):
        return hash(("blacklist", self.jtis))

    def __repr__(self):
        return "Blacklist({} entries)".format(len(self.jtis))


def is_usable(claims, now, blacklist=None):
    """Whether a token may still be exchanged for access."""
    if blacklist is not None and blacklist.is_revoked(claims):
        return False
    return not claims.is_expired(now)


def refresh(claims, now, ttl_seconds=None):
    """Mint a new access token from a refresh token."""
    if claims.kind != REFRESH:
        raise ValidationError("only a refresh token can be exchanged", field="kind")
    if claims.is_expired(now):
        raise ValidationError("refresh token has expired", field="issued_at")
    return TokenClaims(claims.subject, ACCESS, now, ttl_seconds, claims.scopes)
