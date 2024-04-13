"""The streaming platforms the studio knows how to push to.

Each entry records the ingest host, whether the platform insists on RTMPS, and
the ceiling it enforces on incoming bitrate.  ``custom`` is the escape hatch a
customer uses for anything not listed, and it is the only entry whose host is
supplied per target.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text

CUSTOM = "custom"

PLATFORMS = {
    "youtube": {
        "label": "YouTube Live",
        "host": "a.rtmp.youtube.com",
        "path": "live2",
        "secure": False,
        "max_kbps": 51000,
        "key_length": 20,
    },
    "facebook": {
        "label": "Facebook Live",
        "host": "live-api-s.facebook.com",
        "path": "rtmp",
        "secure": True,
        "max_kbps": 4000,
        "key_length": 20,
    },
    "twitch": {
        "label": "Twitch",
        "host": "live.twitch.tv",
        "path": "app",
        "secure": False,
        "max_kbps": 6000,
        "key_length": 24,
    },
    "linkedin": {
        "label": "LinkedIn Live",
        "host": "rtmp-live.linkedin.com",
        "path": "live",
        "secure": True,
        "max_kbps": 5000,
        "key_length": 16,
    },
    "vokal": {
        "label": "Vokal Studio",
        "host": "ingest.vokalstudio.com",
        "path": "live",
        "secure": True,
        "max_kbps": 12000,
        "key_length": 24,
    },
    CUSTOM: {
        "label": "Custom RTMP",
        "host": None,
        "path": None,
        "secure": False,
        "max_kbps": 20000,
        "key_length": 8,
    },
}


def normalize_platform(platform, field="platform"):
    name = require_text(platform, field, max_length=30).lower()
    if name not in PLATFORMS:
        raise ValidationError(
            "unknown platform {}".format(name),
            field=field,
            details={"supported": sorted(PLATFORMS)},
        )
    return name


def entry(platform):
    return dict(PLATFORMS[normalize_platform(platform)])


def label_of(platform):
    return PLATFORMS[normalize_platform(platform)]["label"]


def is_custom(platform):
    return normalize_platform(platform) == CUSTOM


def requires_secure(platform):
    return PLATFORMS[normalize_platform(platform)]["secure"]


def max_kbps(platform):
    return PLATFORMS[normalize_platform(platform)]["max_kbps"]


def minimum_key_length(platform):
    return PLATFORMS[normalize_platform(platform)]["key_length"]


def default_ingest(platform):
    """The ingest URL for a platform, or ``None`` for a custom target."""
    record = PLATFORMS[normalize_platform(platform)]
    if record["host"] is None:
        return None
    scheme = "rtmps" if record["secure"] else "rtmp"
    return "{}://{}/{}".format(scheme, record["host"], record["path"])


def supported_platforms():
    return tuple(sorted(PLATFORMS))
