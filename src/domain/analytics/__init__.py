"""What listeners did, aggregated into something a dashboard can draw."""

from src.domain.analytics.event import (
    COMPLETE,
    DOWNLOAD,
    KINDS,
    PROGRESS,
    PlayEvent,
    SOURCES,
    START,
    deduplicate,
    for_episode,
    furthest_position,
    sessions,
)
from src.domain.analytics.report import (
    episode_report,
    show_report,
    source_breakdown,
    top_episodes,
    trim_to_retention,
)
from src.domain.analytics.retention import (
    average_position,
    completion_rate,
    curve,
    drop_off_bucket,
    is_healthy,
)
from src.domain.analytics.rollup import (
    DailyTotals,
    busiest,
    combine,
    daily,
    fill_gaps,
    moving_average,
)

__all__ = [
    "COMPLETE",
    "DOWNLOAD",
    "DailyTotals",
    "KINDS",
    "PROGRESS",
    "PlayEvent",
    "SOURCES",
    "START",
    "average_position",
    "busiest",
    "combine",
    "completion_rate",
    "curve",
    "daily",
    "deduplicate",
    "drop_off_bucket",
    "episode_report",
    "fill_gaps",
    "for_episode",
    "furthest_position",
    "is_healthy",
    "moving_average",
    "sessions",
    "show_report",
    "source_breakdown",
    "top_episodes",
    "trim_to_retention",
]
