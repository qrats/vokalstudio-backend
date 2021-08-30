"""Primitives shared by every other package in the domain layer."""

from src.domain.core.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionError_,
    QuotaError,
    StateError,
    ValidationError,
)
from src.domain.core.guards import (
    require_bool,
    require_choice,
    require_int,
    require_mapping,
    require_number,
    require_sequence,
    require_text,
)
from src.domain.core.ids import ExternalRef, derive_id, is_uuid_like, short_id
from src.domain.core.result import Err, Ok, Result, collect, first_error
from src.domain.core.text import (
    normalize_whitespace,
    reading_time_seconds,
    slugify,
    strip_markup,
    truncate,
    word_count,
)
from src.domain.core.collections import (
    chunk,
    first,
    freeze,
    group_by,
    index_by,
    partition,
    unique,
)

__all__ = [
    "ConflictError",
    "DomainError",
    "Err",
    "ExternalRef",
    "NotFoundError",
    "Ok",
    "PermissionError_",
    "QuotaError",
    "Result",
    "StateError",
    "ValidationError",
    "chunk",
    "collect",
    "derive_id",
    "first",
    "first_error",
    "freeze",
    "group_by",
    "index_by",
    "is_uuid_like",
    "normalize_whitespace",
    "partition",
    "reading_time_seconds",
    "require_bool",
    "require_choice",
    "require_int",
    "require_mapping",
    "require_number",
    "require_sequence",
    "require_text",
    "short_id",
    "slugify",
    "strip_markup",
    "truncate",
    "unique",
    "word_count",
]
