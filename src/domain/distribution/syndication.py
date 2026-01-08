"""Choosing where an episode goes.

The customer subscribes destinations to a show; this works out which of them
can actually take this particular episode, and turns the answer into jobs.
"""

from src.domain.core.guards import require_sequence
from src.domain.distribution.credential import for_destination
from src.domain.distribution.destination import (
    accepts,
    needs_oauth,
    normalize_destination,
    rejections,
)
from src.domain.distribution.job import UploadJob

ELIGIBLE = "eligible"
NO_CREDENTIAL = "no_credential"
CREDENTIAL_EXPIRED = "credential_expired"
MISSING_SCOPES = "missing_scopes"
REJECTED = "rejected_by_destination"
NOT_ALLOWED = "plan_destination_limit"


def evaluate(destination, episode, credentials=(), now=None, has_artwork=True):
    """Whether one destination can take this episode, and why not."""
    name = normalize_destination(destination)
    if episode.asset is None or not accepts(name, episode.asset, has_artwork):
        return REJECTED
    if needs_oauth(name):
        credential = for_destination(credentials, episode.owner_id, name)
        if credential is None:
            return NO_CREDENTIAL
        if credential.missing_scopes():
            return MISSING_SCOPES
        if now is not None and credential.is_expired(now):
            return CREDENTIAL_EXPIRED
    return ELIGIBLE


def plan(destinations, episode, credentials=(), now=None, has_artwork=True, entitlement=None):
    """Decide each destination, respecting the plan's destination limit."""
    wanted = require_sequence(destinations, "destinations")
    limit = entitlement.limit("distribution.destinations") if entitlement else None
    decisions = []
    admitted = 0
    for destination in wanted:
        verdict = evaluate(destination, episode, credentials, now, has_artwork)
        if verdict == ELIGIBLE and limit is not None and limit >= 0 and admitted >= limit:
            verdict = NOT_ALLOWED
        if verdict == ELIGIBLE:
            admitted += 1
        decisions.append((normalize_destination(destination), verdict))
    return tuple(decisions)


def eligible_destinations(decisions):
    return tuple(name for name, verdict in decisions if verdict == ELIGIBLE)


def blocked(decisions):
    return tuple(
        (name, verdict) for name, verdict in decisions if verdict != ELIGIBLE
    )


def build_jobs(episode, decisions):
    """One pending job per eligible destination."""
    return tuple(
        UploadJob(episode.reference, name)
        for name in eligible_destinations(decisions)
    )


def explain(episode, destination, has_artwork=True):
    """Why a destination refused the media, in the destination's own terms."""
    if episode.asset is None:
        return ("asset",)
    return rejections(destination, episode.asset, has_artwork)
