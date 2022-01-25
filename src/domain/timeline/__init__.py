"""Clock-free time handling for the domain layer."""

from src.domain.timeline.calendar import (
    add_days,
    add_months,
    add_years,
    date_range,
    days_between,
    days_in_month,
    format_date,
    is_leap_year,
    month_end,
    month_start,
    next_anniversary,
    parse_date,
    week_start,
)
from src.domain.timeline.duration import Duration, coerce_duration, total
from src.domain.timeline.instant import Instant, coerce_instant, earliest, latest
from src.domain.timeline.interval import (
    Interval,
    find_conflicts,
    gaps,
    merge_overlapping,
    total_covered,
)
from src.domain.timeline.timecode import Timecode, is_drop_frame, snap_millis
from src.domain.timeline.window import Window, busiest_day, schedule_conflicts

__all__ = [
    "Duration",
    "Instant",
    "Interval",
    "Timecode",
    "Window",
    "add_days",
    "add_months",
    "add_years",
    "busiest_day",
    "coerce_duration",
    "coerce_instant",
    "date_range",
    "days_between",
    "days_in_month",
    "earliest",
    "find_conflicts",
    "format_date",
    "gaps",
    "is_drop_frame",
    "is_leap_year",
    "latest",
    "merge_overlapping",
    "month_end",
    "month_start",
    "next_anniversary",
    "parse_date",
    "schedule_conflicts",
    "snap_millis",
    "total",
    "total_covered",
    "week_start",
]
