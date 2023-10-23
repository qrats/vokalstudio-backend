"""Containers, codecs and which combinations actually work.

The studio accepts a wide range of uploads and produces a narrow range of
outputs.  Keeping the compatibility matrix in one table means the ingest
resource and the render planner cannot disagree about it.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text

AUDIO = "audio"
VIDEO = "video"
IMAGE = "image"
KINDS = (AUDIO, VIDEO, IMAGE)

CONTAINERS = {
    "mp3": {"kind": AUDIO, "codecs": ("mp3",), "extension": "mp3"},
    "m4a": {"kind": AUDIO, "codecs": ("aac", "alac"), "extension": "m4a"},
    "wav": {"kind": AUDIO, "codecs": ("pcm_s16le", "pcm_s24le"), "extension": "wav"},
    "flac": {"kind": AUDIO, "codecs": ("flac",), "extension": "flac"},
    "ogg": {"kind": AUDIO, "codecs": ("vorbis", "opus"), "extension": "ogg"},
    "mp4": {"kind": VIDEO, "codecs": ("h264", "hevc"), "extension": "mp4"},
    "mov": {"kind": VIDEO, "codecs": ("h264", "hevc", "prores"), "extension": "mov"},
    "webm": {"kind": VIDEO, "codecs": ("vp8", "vp9"), "extension": "webm"},
    "mkv": {"kind": VIDEO, "codecs": ("h264", "hevc", "vp9"), "extension": "mkv"},
    "png": {"kind": IMAGE, "codecs": ("png",), "extension": "png"},
    "jpeg": {"kind": IMAGE, "codecs": ("jpeg",), "extension": "jpg"},
}

DELIVERY_CONTAINERS = ("mp3", "m4a", "mp4")
STREAMING_CONTAINER = "mp4"
STREAMING_CODEC = "h264"

_ALIASES = {"jpg": "jpeg", "m4v": "mp4", "mpeg4": "mp4", "wave": "wav"}


def normalize_container(container, field="container"):
    name = require_text(container, field, max_length=10).lower().lstrip(".")
    name = _ALIASES.get(name, name)
    if name not in CONTAINERS:
        raise ValidationError(
            "unsupported container {}".format(name),
            field=field,
            details={"supported": sorted(CONTAINERS)},
        )
    return name


def kind_of(container):
    return CONTAINERS[normalize_container(container)]["kind"]


def extension_of(container):
    return CONTAINERS[normalize_container(container)]["extension"]


def codecs_for(container):
    return CONTAINERS[normalize_container(container)]["codecs"]


def supports(container, codec):
    """Whether ``container`` can carry ``codec``."""
    name = require_text(codec, "codec", max_length=20).lower()
    return name in codecs_for(container)


def require_supported(container, codec):
    if not supports(container, codec):
        raise ValidationError(
            "{} cannot carry {}".format(normalize_container(container), codec),
            field="codec",
            details={"allowed": list(codecs_for(container))},
        )
    return normalize_container(container), codec.lower()


def container_from_filename(name, field="filename"):
    text = require_text(name, field, max_length=255)
    if "." not in text:
        raise ValidationError("{} has no extension".format(field), field=field)
    return normalize_container(text.rsplit(".", 1)[1], field)


def is_deliverable(container):
    """Whether the studio will publish this container to a destination."""
    return normalize_container(container) in DELIVERY_CONTAINERS


def default_codec(container):
    return codecs_for(container)[0]
