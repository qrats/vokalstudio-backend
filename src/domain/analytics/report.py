"""Assembling the numbers the dashboard shows."""

from src.domain.analytics.event import DOWNLOAD, START, for_episode, sessions
from src.domain.analytics.retention import completion_rate, curve
from src.domain.analytics.rollup import combine, daily, fill_gaps
from src.domain.core.guards import require_int
from src.domain.timeline.calendar import days_between, parse_date


def episode_report(events, episode, start, end, buckets=10):
    """Everything the episode detail screen needs."""
    scoped = for_episode(events, episode.reference)
    rows = fill_gaps(daily(scoped), start, end)
    totals = combine(rows)
    duration = episode.duration_millis or 1
    return {
        "episode": episode.reference,
        "title": episode.title,
        "days": [row.to_dict() for row in rows],
        "totals": totals.to_dict() if totals else None,
        "listeners": len(sessions(scoped)),
        "retention": list(curve(scoped, duration, buckets)),
        "completion_rate": completion_rate(scoped, duration),
    }


def show_report(events, episodes, start, end):
    """One row per episode, ordered by listeners."""
    rows = []
    for episode in episodes:
        scoped = for_episode(events, episode.reference)
        totals = combine(daily(scoped))
        rows.append(
            {
                "episode": episode.reference,
                "title": episode.title,
                "listeners": len(sessions(scoped)),
                "starts": totals.starts if totals else 0,
                "downloads": totals.downloads if totals else 0,
            }
        )
    rows.sort(key=lambda row: (-row["listeners"], row["title"]))
    return {
        "start": parse_date(start, "start").isoformat(),
        "end": parse_date(end, "end").isoformat(),
        "days": days_between(start, end),
        "episodes": rows,
        "listeners": sum(row["listeners"] for row in rows),
        "starts": sum(row["starts"] for row in rows),
    }


def top_episodes(report, limit=5):
    size = require_int(limit, "limit", minimum=1)
    return tuple(row["episode"] for row in report["episodes"][:size])


def source_breakdown(events):
    """How many distinct listeners came from each source, sorted by source."""
    by_source = {}
    for event in events:
        if event.kind not in (START, DOWNLOAD):
            continue
        by_source.setdefault(event.source, set()).add(event.session_id)
    return {source: len(found) for source, found in sorted(by_source.items())}


def trim_to_retention(rows, retention_days):
    """Drop rows older than the plan's analytics retention allows."""
    days = require_int(retention_days, "retention_days", minimum=0)
    if not rows:
        return ()
    newest = max(row.day for row in rows)
    return tuple(row for row in rows if (newest - row.day).days < days)
