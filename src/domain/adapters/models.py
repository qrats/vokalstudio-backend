"""Turning stored rows into domain objects.

Each mapper names the row fields it reads, so a column rename shows up here as
a failing test rather than as an ``AttributeError`` in a Celery worker.
"""

from src.domain.access.grant import Grant
from src.domain.adapters.rows import coalesce, field, rename, require_fields
from src.domain.billing.subscription import Subscription
from src.domain.catalog.plan import BillingCycle, Plan
from src.domain.catalog.product import Product
from src.domain.content.post import Post
from src.domain.episodes.episode import Episode
from src.domain.episodes.series import Series
from src.domain.media.asset import Asset
from src.domain.media.configuration import MediaConfiguration
from src.domain.money.amount import Money
from src.domain.streaming.target import StreamTarget


def to_asset(row):
    """Build an :class:`Asset` from a media object row."""
    require_fields(row, "user_id", "name")
    return Asset(
        field(row, "user_id"),
        field(row, "name"),
        coalesce(row, "size_bytes", "size", default=1),
        coalesce(row, "container", "format"),
        coalesce(row, "duration_millis", "duration"),
        field(row, "role", "main"),
        field(row, "checksum", None),
    )


def to_media_configuration(row, intro=None, outro=None):
    """Build a :class:`MediaConfiguration`; the beds are resolved by the caller."""
    require_fields(row, "user_id")
    return MediaConfiguration(
        field(row, "user_id"),
        intro,
        outro,
        None,
        field(row, "loudness_profile", "podcast"),
        field(row, "normalise", True),
        coalesce(row, "fade_millis", "fade", default=0),
    )


def to_stream_target(row):
    """Build a :class:`StreamTarget` from a streaming platform row."""
    require_fields(row, "user_id", "platform", "stream_key")
    return StreamTarget(
        field(row, "user_id"),
        field(row, "platform"),
        field(row, "stream_key"),
        coalesce(row, "ingest", "rtmp_url"),
        field(row, "enabled", True),
        field(row, "label", None),
    )


def to_product(row):
    require_fields(row, "name", "description")
    return Product(
        field(row, "name"),
        field(row, "description"),
        field(row, "code", None),
        field(row, "type", "service"),
        field(row, "category", "software"),
        _product_ref(row),
        field(row, "sandbox", False),
    )


def _product_ref(row):
    external = coalesce(row, "id", "external_id")
    return "paypal:{}".format(external) if external else None


def to_plan(row, product_code=None):
    """Build a :class:`Plan` from a plans row plus its billing cycles."""
    require_fields(row, "name")
    currency = field(row, "currency", "USD")
    cycles = [
        BillingCycle(
            Money.from_major(field(cycle, "price"), field(cycle, "currency", currency)),
            field(cycle, "interval", "month"),
            field(cycle, "frequency", 1),
            field(cycle, "cycles", 0),
            field(cycle, "trial", False),
        )
        for cycle in field(row, "billing_cycles", [])
    ] or [BillingCycle(Money.from_major(field(row, "price", "0"), currency))]
    return Plan(
        field(row, "name"),
        product_code or field(row, "product_id", "vokal"),
        cycles,
        field(row, "grants", None),
        field(row, "code", None),
        field(row, "status", "active"),
        field(row, "quantity_supported", False),
    )


def to_subscription(row):
    require_fields(row, "id", "user_id", "plan_id", "start_time")
    return Subscription(
        field(row, "id"),
        field(row, "user_id"),
        field(row, "plan_id"),
        _day(field(row, "start_time")),
        field(row, "status", "approval_pending"),
        _day(field(row, "cancelled_at", None)),
        _day(field(row, "period_end", None)),
    )


def _day(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


def to_grant(row):
    """Build a :class:`Grant` from an authorized user row."""
    require_fields(row, "owner_id", "user_id")
    return Grant(
        field(row, "owner_id"),
        field(row, "user_id"),
        field(row, "role", "guest"),
        coalesce(row, "episode_ids", "episodes"),
        _day(field(row, "created_at", None)),
        _day(field(row, "expires_at", None)),
    )


def to_series(row):
    require_fields(row, "user_id", "title")
    return Series(
        field(row, "user_id"),
        field(row, "title"),
        field(row, "ordering", "episodic"),
        field(row, "seasons", False),
        field(row, "explicit", False),
        field(row, "slug", None),
    )


def to_episode(row, asset=None):
    require_fields(row, "user_id", "title")
    values = rename(
        row,
        {
            "owner_id": "user_id",
            "series_slug": "series",
            "title": "title",
        },
        {"series_slug": "vokal"},
    )
    return Episode(
        values["owner_id"],
        values["series_slug"],
        values["title"],
        asset,
        field(row, "description", None),
        (),
        field(row, "number", None),
        field(row, "season", None),
        field(row, "kind", "full"),
        field(row, "explicit", False),
        field(row, "state", "draft"),
        field(row, "published_at", None),
        field(row, "slug", None),
    )


def to_post(row):
    require_fields(row, "title", "body", "user_id")
    return Post(
        field(row, "title"),
        field(row, "body"),
        field(row, "user_id"),
        field(row, "slug", None),
        field(row, "state", "draft"),
        coalesce(row, "tags", "categories", default=()),
        field(row, "hero_key", None),
        field(row, "featured", False),
        field(row, "published_at", None),
    )
