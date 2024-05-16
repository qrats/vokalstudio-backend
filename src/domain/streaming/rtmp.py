"""Parsing and building RTMP ingest URLs.

The customer pastes a URL and a stream key from somewhere else; both need
checking before a worker is asked to connect, and the key must never appear in
a log line or an API response in full.
"""

import re

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text
from src.domain.core.text import mask

SCHEMES = ("rtmp", "rtmps")
DEFAULT_PORTS = {"rtmp": 1935, "rtmps": 443}

_HOST = re.compile(r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$")
_KEY = re.compile(r"^[A-Za-z0-9_-]{4,128}$")


class IngestUrl:
    """A parsed ``rtmp(s)://host[:port]/path`` endpoint."""

    __slots__ = ("scheme", "host", "port", "path")

    def __init__(self, scheme, host, path, port=None):
        self.scheme = require_text(scheme, "scheme", max_length=5).lower()
        if self.scheme not in SCHEMES:
            raise ValidationError(
                "scheme must be rtmp or rtmps", field="scheme"
            )
        self.host = require_text(host, "host", max_length=253).lower()
        if not _HOST.match(self.host) or "." not in self.host:
            raise ValidationError("host is not a domain name", field="host")
        self.path = require_text(path, "path", max_length=200).strip("/")
        if not self.path:
            raise ValidationError("path is required", field="path")
        self.port = port if port is not None else DEFAULT_PORTS[self.scheme]
        if not isinstance(self.port, int) or isinstance(self.port, bool):
            raise ValidationError("port must be an integer", field="port")
        if not 1 <= self.port <= 65535:
            raise ValidationError("port is out of range", field="port")

    @classmethod
    def parse(cls, url, field="url"):
        raw = require_text(url, field, max_length=500)
        if "://" not in raw:
            raise ValidationError("{} needs a scheme".format(field), field=field)
        scheme, _, rest = raw.partition("://")
        if "/" not in rest:
            raise ValidationError("{} needs a path".format(field), field=field)
        authority, _, path = rest.partition("/")
        port = None
        if ":" in authority:
            authority, _, port_text = authority.partition(":")
            if not port_text.isdigit():
                raise ValidationError("{} has a bad port".format(field), field=field)
            port = int(port_text, 10)
        return cls(scheme, authority, path, port)

    @property
    def is_secure(self):
        return self.scheme == "rtmps"

    @property
    def uses_default_port(self):
        return self.port == DEFAULT_PORTS[self.scheme]

    def to_string(self):
        authority = self.host
        if not self.uses_default_port:
            authority = "{}:{}".format(self.host, self.port)
        return "{}://{}/{}".format(self.scheme, authority, self.path)

    def with_key(self, key):
        return "{}/{}".format(self.to_string(), validate_stream_key(key))

    def to_dict(self):
        return {
            "scheme": self.scheme,
            "host": self.host,
            "port": self.port,
            "path": self.path,
            "url": self.to_string(),
        }

    def __eq__(self, other):
        return isinstance(other, IngestUrl) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("ingest", self.scheme, self.host, self.port, self.path))

    def __repr__(self):
        return "IngestUrl({})".format(self.to_string())


def validate_stream_key(key, field="stream_key", minimum=4):
    """Check a stream key without ever returning it changed."""
    text = require_text(key, field, min_length=minimum, max_length=128)
    if not _KEY.match(text):
        raise ValidationError(
            "{} may only contain letters, digits, dashes and underscores".format(field),
            field=field,
        )
    return text


def masked_key(key):
    """The form of a stream key that is safe to return from the API."""
    return mask(key, keep=4)


def split_url_and_key(url, field="url"):
    """Split a pasted ``.../path/streamkey`` into its ingest URL and key."""
    raw = require_text(url, field, max_length=600)
    head, separator, tail = raw.rpartition("/")
    if not separator or not tail:
        raise ValidationError("{} does not carry a key".format(field), field=field)
    return IngestUrl.parse(head, field), validate_stream_key(tail, field)
