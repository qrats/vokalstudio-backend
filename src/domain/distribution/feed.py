"""Building the RSS payload for a show.

This returns nested dictionaries rather than XML: the serialiser lives in the
Flask layer, and keeping the structure separate is what lets the whole thing be
tested without parsing anything.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text
from src.domain.core.text import truncate
from src.domain.episodes.episode import visible
from src.domain.media.storage import content_type_for

MAX_TITLE = 200
MAX_SUMMARY = 4000


def _episode_entry(episode, base_url):
    if episode.asset is None:
        raise ValidationError("a feed item needs media", field="episode")
    entry = {
        "guid": episode.reference,
        "title": episode.title,
        "link": "{}/{}/{}".format(base_url, episode.series_slug, episode.slug),
        "description": episode.notes.summary(MAX_SUMMARY),
        "duration_millis": episode.duration_millis,
        "explicit": episode.explicit,
        "type": episode.kind,
        "enclosure": {
            "url": "{}/media/{}".format(base_url, episode.asset.key),
            "length": episode.asset.size_bytes,
            "type": content_type_for(episode.asset.container),
        },
        "published_at": episode.published_at.to_iso() if episode.published_at else None,
    }
    if episode.number is not None:
        entry["episode"] = episode.number
    if episode.season is not None:
        entry["season"] = episode.season
    if episode.chapters:
        entry["chapters"] = [chapter.to_dict() for chapter in episode.chapters]
    return entry


def build_feed(series, episodes, base_url, artwork_url=None, description=""):
    """The whole feed document for one show."""
    root = require_text(base_url, "base_url", max_length=500).rstrip("/")
    published = [
        episode
        for episode in visible(episodes)
        if episode.series_slug == series.slug
    ]
    published.sort(
        key=lambda episode: (
            episode.published_at.millis if episode.published_at else 0,
            episode.slug,
        ),
        reverse=series.newest_first(),
    )
    items = [_episode_entry(episode, root) for episode in published]
    return {
        "title": truncate(series.title, MAX_TITLE),
        "link": "{}/{}".format(root, series.slug),
        "description": truncate(description, MAX_SUMMARY) if description else "",
        "explicit": series.explicit,
        "image": artwork_url,
        "ordering": series.ordering,
        "items": items,
        "count": len(items),
    }


def latest_item(feed):
    return feed["items"][0] if feed["items"] else None


def total_duration_millis(feed):
    return sum(item["duration_millis"] for item in feed["items"])


def guids(feed):
    return tuple(item["guid"] for item in feed["items"])


def validate_feed(feed):
    """Every reason a feed would be rejected by a directory, sorted."""
    problems = []
    if not feed["title"]:
        problems.append("title")
    if not feed["description"]:
        problems.append("description")
    if not feed["image"]:
        problems.append("image")
    if not feed["items"]:
        problems.append("items")
    if len(set(guids(feed))) != len(feed["items"]):
        problems.append("duplicate_guid")
    return tuple(sorted(problems))
