"""Instance types.

A restream server is an EC2 instance running an RTMP relay.  What matters to
the domain is how many outbound copies it can push and what it costs per hour.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_int, require_text
from src.domain.money.amount import Money

TYPES = {
    "t3.small": {"targets": 2, "kbps": 8000, "cents_per_hour": 3},
    "t3.medium": {"targets": 4, "kbps": 16000, "cents_per_hour": 5},
    "c5.large": {"targets": 8, "kbps": 40000, "cents_per_hour": 9},
    "c5.xlarge": {"targets": 16, "kbps": 80000, "cents_per_hour": 18},
}

DEFAULT_TYPE = "t3.medium"


def normalize_type(instance_type, field="instance_type"):
    name = require_text(instance_type, field, max_length=20).lower()
    if name not in TYPES:
        raise ValidationError(
            "unknown instance type {}".format(name),
            field=field,
            details={"supported": sorted(TYPES)},
        )
    return name


def capacity(instance_type):
    return TYPES[normalize_type(instance_type)]["targets"]


def throughput_kbps(instance_type):
    return TYPES[normalize_type(instance_type)]["kbps"]


def hourly_cost(instance_type, currency="USD"):
    return Money(TYPES[normalize_type(instance_type)]["cents_per_hour"], currency)


def cost_for_hours(instance_type, hours, currency="USD"):
    return hourly_cost(instance_type, currency).times(
        require_int(hours, "hours", minimum=0)
    )


def smallest_for(targets, kbps=None):
    """The cheapest type that can push ``targets`` copies at ``kbps`` each."""
    wanted = require_int(targets, "targets", minimum=1)
    rate = require_int(kbps, "kbps", minimum=1) if kbps is not None else None
    ordered = sorted(TYPES.items(), key=lambda pair: pair[1]["cents_per_hour"])
    for name, record in ordered:
        if record["targets"] < wanted:
            continue
        if rate is not None and record["kbps"] < wanted * rate:
            continue
        return name
    return None


def supported_types():
    return tuple(sorted(TYPES))
