"""Upload destinations.

Where a finished episode goes after it is rendered.  Each destination has its
own limits on file size, duration and what it will accept as artwork, and those
limits are the reason a publication fails long after the customer pressed the
button.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text

DESTINATIONS = {
    "podbean": {
        "label": "Podbean",
        "containers": ("mp3", "m4a", "mp4"),
        "max_bytes": 500 * 1024 ** 2,
        "max_duration_millis": 5 * 3600 * 1000,
        "needs_artwork": True,
        "oauth": True,
    },
    "spotify": {
        "label": "Spotify for Podcasters",
        "containers": ("mp3", "m4a"),
        "max_bytes": 200 * 1024 ** 2,
        "max_duration_millis": 12 * 3600 * 1000,
        "needs_artwork": True,
        "oauth": True,
    },
    "apple": {
        "label": "Apple Podcasts",
        "containers": ("mp3", "m4a"),
        "max_bytes": 300 * 1024 ** 2,
        "max_duration_millis": 6 * 3600 * 1000,
        "needs_artwork": True,
        "oauth": False,
    },
    "youtube": {
        "label": "YouTube",
        "containers": ("mp4",),
        "max_bytes": 2 * 1024 ** 3,
        "max_duration_millis": 12 * 3600 * 1000,
        "needs_artwork": False,
        "oauth": True,
    },
    "vokal": {
        "label": "Vokal Studio",
        "containers": ("mp3", "m4a", "mp4"),
        "max_bytes": 2 * 1024 ** 3,
        "max_duration_millis": 12 * 3600 * 1000,
        "needs_artwork": False,
        "oauth": False,
    },
}


def normalize_destination(destination, field="destination"):
    name = require_text(destination, field, max_length=30).lower()
    if name not in DESTINATIONS:
        raise ValidationError(
            "unknown destination {}".format(name),
            field=field,
            details={"supported": sorted(DESTINATIONS)},
        )
    return name


def label_of(destination):
    return DESTINATIONS[normalize_destination(destination)]["label"]


def accepts_container(destination, container):
    from src.domain.media.format import normalize_container

    record = DESTINATIONS[normalize_destination(destination)]
    return normalize_container(container) in record["containers"]


def needs_oauth(destination):
    return DESTINATIONS[normalize_destination(destination)]["oauth"]


def needs_artwork(destination):
    return DESTINATIONS[normalize_destination(destination)]["needs_artwork"]


def rejections(destination, asset, has_artwork=True):
    """Every reason ``asset`` would be refused, sorted."""
    record = DESTINATIONS[normalize_destination(destination)]
    problems = []
    if asset.container not in record["containers"]:
        problems.append("container")
    if asset.size_bytes > record["max_bytes"]:
        problems.append("size")
    if asset.duration is not None and asset.duration.millis > record["max_duration_millis"]:
        problems.append("duration")
    if record["needs_artwork"] and not has_artwork:
        problems.append("artwork")
    return tuple(sorted(problems))


def accepts(destination, asset, has_artwork=True):
    return not rejections(destination, asset, has_artwork)


def supported_destinations():
    return tuple(sorted(DESTINATIONS))
