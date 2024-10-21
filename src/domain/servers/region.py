"""Regions and the latency between them.

A restream server should sit near the broadcaster, not near the platform, so
picking one is a question about round-trip time from the customer.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text

REGIONS = {
    "us-east-1": {"label": "N. Virginia", "continent": "na"},
    "us-west-2": {"label": "Oregon", "continent": "na"},
    "eu-west-1": {"label": "Ireland", "continent": "eu"},
    "eu-central-1": {"label": "Frankfurt", "continent": "eu"},
    "ap-south-1": {"label": "Mumbai", "continent": "as"},
    "ap-southeast-2": {"label": "Sydney", "continent": "oc"},
    "sa-east-1": {"label": "Sao Paulo", "continent": "sa"},
}

SAME_REGION_MILLIS = 5
SAME_CONTINENT_MILLIS = 40
CROSS_CONTINENT_MILLIS = 160

_NEIGHBOURS = {
    ("na", "sa"): 120,
    ("na", "eu"): 90,
    ("eu", "as"): 120,
    ("as", "oc"): 110,
}


def normalize_region(region, field="region"):
    name = require_text(region, field, max_length=20).lower()
    if name not in REGIONS:
        raise ValidationError(
            "unknown region {}".format(name),
            field=field,
            details={"supported": sorted(REGIONS)},
        )
    return name


def label_of(region):
    return REGIONS[normalize_region(region)]["label"]


def continent_of(region):
    return REGIONS[normalize_region(region)]["continent"]


def latency_millis(origin, destination):
    """A coarse round-trip estimate between two regions."""
    left = normalize_region(origin, "origin")
    right = normalize_region(destination, "destination")
    if left == right:
        return SAME_REGION_MILLIS
    one, two = continent_of(left), continent_of(right)
    if one == two:
        return SAME_CONTINENT_MILLIS
    return _NEIGHBOURS.get((one, two)) or _NEIGHBOURS.get((two, one)) or CROSS_CONTINENT_MILLIS


def nearest(origin, candidates):
    """The candidate region with the lowest latency, ties broken by name."""
    options = [normalize_region(region, "candidates") for region in candidates]
    if not options:
        return None
    return sorted(options, key=lambda region: (latency_millis(origin, region), region))[0]


def within(origin, budget_millis, candidates=None):
    """Regions reachable inside a latency budget, nearest first."""
    options = candidates if candidates is not None else sorted(REGIONS)
    reachable = [
        region
        for region in (normalize_region(item, "candidates") for item in options)
        if latency_millis(origin, region) <= budget_millis
    ]
    return tuple(sorted(reachable, key=lambda region: (latency_millis(origin, region), region)))


def supported_regions():
    return tuple(sorted(REGIONS))
