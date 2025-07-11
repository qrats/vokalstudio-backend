"""Turning an episode into the work of publishing it.

Publishing means: check the plan allows another episode this month, decide the
destinations, and produce the ordered list of steps a worker performs.
"""

from src.domain.core.errors import QuotaError, ValidationError
from src.domain.episodes.episode import published_in_month
from src.domain.episodes.state import PUBLISHED

RENDER = "render"
UPLOAD = "upload"
FEED = "feed"
NOTIFY = "notify"

STEP_ORDER = (RENDER, UPLOAD, FEED, NOTIFY)


class PublicationStep:
    """One unit of work in a publication."""

    __slots__ = ("kind", "target", "detail")

    def __init__(self, kind, target=None, detail=None):
        if kind not in STEP_ORDER:
            raise ValidationError("unknown step {}".format(kind), field="kind")
        self.kind = kind
        self.target = target
        self.detail = dict(detail or {})

    def to_dict(self):
        return {"kind": self.kind, "target": self.target, "detail": dict(self.detail)}

    def __eq__(self, other):
        return isinstance(other, PublicationStep) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("step", self.kind, self.target))

    def __repr__(self):
        return "PublicationStep({}, {})".format(self.kind, self.target)


def check_monthly_allowance(entitlement, episodes, year, month):
    """Raise when the plan will not take another episode this month."""
    used = len(published_in_month(episodes, year, month))
    entitlement.check("episodes.monthly", used=used, wanted=1)
    return used


def plan_publication(episode, destinations=(), needs_render=False):
    """The ordered steps that publish one episode."""
    if episode.asset is None:
        raise ValidationError("episode has no media", field="episode")
    if not episode.is_publishable():
        raise ValidationError(
            "episode is incomplete",
            field="episode",
            details={"missing": list(episode.missing_for_publication())},
        )
    steps = []
    if needs_render:
        steps.append(PublicationStep(RENDER, episode.asset.key))
    for destination in destinations:
        steps.append(
            PublicationStep(UPLOAD, destination, {"episode": episode.reference})
        )
    steps.append(PublicationStep(FEED, episode.series_slug))
    steps.append(PublicationStep(NOTIFY, episode.owner_id))
    return tuple(steps)


def publish(episode, at, entitlement=None, episodes=(), destinations=(), needs_render=False):
    """Run the checks, then return the published episode and its work list."""
    if entitlement is not None:
        year, month = _stamp(at)
        check_monthly_allowance(entitlement, episodes, year, month)
    steps = plan_publication(episode, destinations, needs_render)
    return episode.publish(at), steps


def _stamp(at):
    from src.domain.timeline.instant import coerce_instant

    date = coerce_instant(at, "at").to_date()
    return int(date[:4], 10), int(date[5:7], 10)


def remaining_this_month(entitlement, episodes, year, month):
    """How many more episodes the plan allows this month."""
    used = len(published_in_month(episodes, year, month))
    return entitlement.remaining("episodes.monthly", used)


def would_exceed(entitlement, episodes, year, month):
    try:
        check_monthly_allowance(entitlement, episodes, year, month)
    except QuotaError:
        return True
    return False


def steps_by_kind(steps, kind):
    return tuple(step for step in steps if step.kind == kind)


def publication_order(steps):
    """The steps sorted into the order a worker should run them."""
    return tuple(sorted(steps, key=lambda step: STEP_ORDER.index(step.kind)))
