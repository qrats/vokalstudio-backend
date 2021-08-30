"""Identifier helpers.

The application stores UUID strings created by the database, but the domain
layer also needs identifiers it can derive without a clock or a random source
-- for restream server names, upload job keys and idempotency markers.
"""

import hashlib
import re

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"


def is_uuid_like(value):
    """Return whether ``value`` looks like a lowercase canonical UUID."""
    return isinstance(value, str) and bool(_UUID.match(value))


def derive_id(namespace, *parts):
    """Return a stable 32 character hex id for ``namespace`` and ``parts``."""
    namespace = require_text(namespace, "namespace")
    digest = hashlib.sha256()
    digest.update(namespace.encode("utf-8"))
    for part in parts:
        digest.update(b"\x1f")
        digest.update(str(part).encode("utf-8"))
    return digest.hexdigest()[:32]


def short_id(namespace, *parts, length=10):
    """Return a short, human typeable id derived from the same inputs."""
    if length < 4 or length > 26:
        raise ValidationError("length must be between 4 and 26", field="length")
    number = int(derive_id(namespace, *parts), 16)
    out = []
    base = len(_ALPHABET)
    while len(out) < length:
        out.append(_ALPHABET[number % base])
        number //= base
    return "".join(out)


class ExternalRef:
    """A provider-scoped identifier, such as a PayPal plan or a Podbean show."""

    __slots__ = ("provider", "value")

    def __init__(self, provider, value):
        self.provider = require_text(provider, "provider", max_length=40).lower()
        self.value = require_text(value, "value", max_length=200)

    @classmethod
    def parse(cls, text):
        text = require_text(text, "ref")
        if ":" not in text:
            raise ValidationError(
                "ref must look like provider:value", field="ref"
            )
        provider, _, value = text.partition(":")
        return cls(provider, value)

    def to_string(self):
        return "{}:{}".format(self.provider, self.value)

    def to_dict(self):
        return {"provider": self.provider, "value": self.value}

    def __eq__(self, other):
        return (
            isinstance(other, ExternalRef)
            and other.provider == self.provider
            and other.value == self.value
        )

    def __hash__(self):
        return hash((self.provider, self.value))

    def __repr__(self):
        return "ExternalRef({!r}, {!r})".format(self.provider, self.value)


def checksum(data):
    """Return the sha256 of ``data``; strings are encoded as UTF-8."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    if not isinstance(data, (bytes, bytearray)):
        raise ValidationError("data must be bytes or str", field="data")
    return hashlib.sha256(bytes(data)).hexdigest()


def idempotency_key(action, actor, *parts):
    """Build the key used to de-duplicate a repeated write."""
    return short_id("idempotency", action, actor, *parts, length=16)
