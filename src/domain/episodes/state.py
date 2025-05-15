"""The episode publishing state machine."""

from src.domain.core.errors import StateError
from src.domain.core.guards import require_choice

DRAFT = "draft"
READY = "ready"
SCHEDULED = "scheduled"
PUBLISHED = "published"
ARCHIVED = "archived"

STATES = (DRAFT, READY, SCHEDULED, PUBLISHED, ARCHIVED)

TRANSITIONS = {
    DRAFT: (READY, ARCHIVED),
    READY: (DRAFT, SCHEDULED, PUBLISHED, ARCHIVED),
    SCHEDULED: (READY, PUBLISHED, ARCHIVED),
    PUBLISHED: (ARCHIVED,),
    ARCHIVED: (DRAFT,),
}

VISIBLE_STATES = (PUBLISHED,)
EDITABLE_STATES = (DRAFT, READY, SCHEDULED)


def can_transition(current, target):
    return require_choice(target, "target", STATES) in TRANSITIONS[
        require_choice(current, "current", STATES)
    ]


def transition(current, target):
    if not can_transition(current, target):
        raise StateError(
            "cannot move a {} episode to {}".format(current, target),
            current=current,
            attempted=target,
        )
    return target


def is_visible(state):
    return require_choice(state, "state", STATES) in VISIBLE_STATES


def is_editable(state):
    return require_choice(state, "state", STATES) in EDITABLE_STATES


def reachable_from(state):
    """Every state reachable from ``state``, sorted."""
    seen = set()
    frontier = [require_choice(state, "state", STATES)]
    while frontier:
        current = frontier.pop()
        for target in TRANSITIONS[current]:
            if target not in seen:
                seen.add(target)
                frontier.append(target)
    return tuple(sorted(seen))
