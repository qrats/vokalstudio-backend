"""A very small markdown reader.

The blog editor stores markdown and the API returns blocks, because the two
front ends render them differently.  Only the subset the editor can produce is
supported: headings, paragraphs, list items, quotes and fenced code.
"""

from src.domain.core.errors import ValidationError
from src.domain.core.guards import require_text
from src.domain.core.text import normalize_whitespace, strip_markup

HEADING = "heading"
PARAGRAPH = "paragraph"
LIST = "list"
QUOTE = "quote"
CODE = "code"

BLOCK_KINDS = (HEADING, PARAGRAPH, LIST, QUOTE, CODE)

FENCE = "```"


def _classify(line):
    stripped = line.strip()
    if stripped.startswith("#"):
        return HEADING
    if stripped.startswith(("- ", "* ")):
        return LIST
    if stripped.startswith("> "):
        return QUOTE
    return PARAGRAPH


def heading_level(line):
    """How many ``#`` a heading line carries, capped at six."""
    stripped = require_text(line, "line").lstrip()
    if not stripped.startswith("#"):
        raise ValidationError("not a heading", field="line")
    return min(6, len(stripped) - len(stripped.lstrip("#")))


def parse_blocks(body):
    """Split markdown into a tuple of block dictionaries."""
    text = require_text(body, "body", min_length=0, strip=False)
    blocks = []
    lines = text.split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip().startswith(FENCE):
            language = line.strip()[len(FENCE):].strip()
            collected = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith(FENCE):
                collected.append(lines[index])
                index += 1
            index += 1
            blocks.append(
                {"kind": CODE, "text": "\n".join(collected), "language": language or None}
            )
            continue
        if not line.strip():
            index += 1
            continue
        kind = _classify(line)
        if kind == LIST:
            items = []
            while index < len(lines) and _classify(lines[index]) == LIST and lines[index].strip():
                items.append(normalize_whitespace(lines[index].strip()[2:]))
                index += 1
            blocks.append({"kind": LIST, "items": items})
            continue
        if kind == HEADING:
            blocks.append(
                {
                    "kind": HEADING,
                    "level": heading_level(line),
                    "text": normalize_whitespace(line.strip().lstrip("#")),
                }
            )
            index += 1
            continue
        collected = []
        while index < len(lines) and lines[index].strip() and _classify(lines[index]) == kind:
            body_line = lines[index].strip()
            collected.append(body_line[2:] if kind == QUOTE else body_line)
            index += 1
        blocks.append({"kind": kind, "text": normalize_whitespace(" ".join(collected))})
    return tuple(blocks)


def headings(body):
    """Every heading, as ``(level, text)`` pairs."""
    return tuple(
        (block["level"], block["text"])
        for block in parse_blocks(body)
        if block["kind"] == HEADING
    )


def table_of_contents(body):
    """Headings turned into anchors, skipping the title level."""
    from src.domain.core.text import slugify_safe

    entries = []
    for level, text in headings(body):
        if level < 2:
            continue
        anchor = slugify_safe(text)
        if anchor:
            entries.append({"level": level, "text": text, "anchor": anchor})
    return tuple(entries)


def excerpt(body, limit=200):
    """The first paragraph, stripped of markup and shortened."""
    from src.domain.core.text import truncate

    for block in parse_blocks(body):
        if block["kind"] == PARAGRAPH:
            return truncate(strip_markup(block["text"]), limit)
    return ""


def code_languages(body):
    """The languages named on fenced code blocks, sorted and de-duplicated."""
    found = {
        block["language"]
        for block in parse_blocks(body)
        if block["kind"] == CODE and block["language"]
    }
    return tuple(sorted(found))
