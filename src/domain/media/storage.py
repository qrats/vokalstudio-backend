"""Object keys and upload descriptors.

The S3 resource signs whatever it is handed, so the rules about what a key may
look like belong on this side of the boundary.
"""

import re

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_text
from src.domain.core.ids import derive_id
from src.domain.media.format import extension_of, normalize_container

MAX_UPLOAD_BYTES = 5 * 1024 ** 3
MIN_UPLOAD_BYTES = 1
SIGNED_URL_TTL_SECONDS = 900

_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,1022}$")
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")

PREFIXES = ("uploads", "renders", "artwork", "transcripts")


def sanitise_filename(name, field="filename"):
    """Strip a filename down to something safe to put in an object key."""
    text = require_text(name, field, max_length=255)
    stem, _, extension = text.rpartition(".")
    if not stem:
        stem, extension = text, ""
    cleaned = _UNSAFE.sub("-", stem).strip("-.")
    if not cleaned:
        raise ValidationError("{} has no usable characters".format(field), field=field)
    return "{}.{}".format(cleaned[:120], extension.lower()) if extension else cleaned[:120]


def build_key(prefix, user_id, filename, container=None):
    """Compose the object key an upload lands on."""
    if prefix not in PREFIXES:
        raise ValidationError(
            "unknown prefix {}".format(prefix),
            field="prefix",
            details={"allowed": sorted(PREFIXES)},
        )
    owner = require_text(user_id, "user_id", max_length=64)
    safe = sanitise_filename(filename)
    marker = derive_id("key", owner, safe)[:16]
    if container is not None:
        safe = "{}.{}".format(
            safe.rsplit(".", 1)[0], extension_of(normalize_container(container))
        )
    return "{}/{}/{}-{}".format(prefix, owner, marker, safe)


def is_valid_key(key):
    return isinstance(key, str) and bool(_KEY.match(key)) and ".." not in key


def require_key(key, field="key"):
    if not is_valid_key(key):
        raise ValidationError("{} is not a valid object key".format(field), field=field)
    return key


def owner_of(key):
    """The user id embedded in a key built by :func:`build_key`."""
    parts = require_key(key).split("/")
    if len(parts) < 3 or parts[0] not in PREFIXES:
        raise ValidationError("key does not carry an owner", field="key")
    return parts[1]


def upload_descriptor(prefix, user_id, filename, size_bytes, container=None):
    """Everything the client needs to perform a direct upload."""
    size = require_int(size_bytes, "size_bytes", minimum=MIN_UPLOAD_BYTES)
    if size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            "upload exceeds the {} byte limit".format(MAX_UPLOAD_BYTES),
            field="size_bytes",
        )
    key = build_key(prefix, user_id, filename, container)
    return {
        "key": key,
        "size_bytes": size,
        "expires_in": SIGNED_URL_TTL_SECONDS,
        "content_type": _content_type(key),
    }


_CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "wav": "audio/wav",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
    "mkv": "video/x-matroska",
    "png": "image/png",
    "jpg": "image/jpeg",
}


def _content_type(key):
    extension = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    return _CONTENT_TYPES.get(extension, "application/octet-stream")


def content_type_for(container):
    return _CONTENT_TYPES.get(extension_of(container), "application/octet-stream")
