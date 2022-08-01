"""Products.

A product is what PayPal calls the thing a plan bills for; the studio has a
small number of them and they change rarely, so the model is deliberately thin.
"""

from src.domain.core.guards import (
    require_bool,
    require_choice,
    require_text,
)
from src.domain.core.ids import ExternalRef
from src.domain.core.text import slugify, truncate

TYPES = ("service", "digital", "physical")
CATEGORIES = (
    "software",
    "audio_video",
    "broadcast",
    "media_production",
    "other",
)


class Product:
    """A sellable product in the catalogue."""

    __slots__ = ("code", "name", "description", "type", "category", "ref", "sandbox")

    def __init__(
        self,
        name,
        description,
        code=None,
        type="service",
        category="software",
        ref=None,
        sandbox=False,
    ):
        self.name = require_text(name, "name", max_length=127)
        self.description = require_text(description, "description", max_length=256)
        self.code = slugify(code or name, field="code")
        self.type = require_choice(type, "type", TYPES)
        self.category = require_choice(category, "category", CATEGORIES)
        self.sandbox = require_bool(sandbox, "sandbox")
        self.ref = self._parse_ref(ref)

    @staticmethod
    def _parse_ref(ref):
        if ref is None:
            return None
        if isinstance(ref, ExternalRef):
            return ref
        return ExternalRef.parse(ref)

    def with_ref(self, ref):
        """Return a copy carrying the provider identifier."""
        return Product(
            self.name,
            self.description,
            self.code,
            self.type,
            self.category,
            ref,
            self.sandbox,
        )

    def summary(self, limit=80):
        return truncate(self.description, limit)

    def is_linked(self):
        return self.ref is not None

    def to_dict(self):
        payload = {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "category": self.category,
            "sandbox": self.sandbox,
        }
        if self.ref is not None:
            payload["ref"] = self.ref.to_string()
        return payload

    @classmethod
    def from_dict(cls, payload):
        return cls(
            payload["name"],
            payload["description"],
            payload.get("code"),
            payload.get("type", "service"),
            payload.get("category", "software"),
            payload.get("ref"),
            payload.get("sandbox", False),
        )

    def __eq__(self, other):
        return isinstance(other, Product) and other.to_dict() == self.to_dict()

    def __hash__(self):
        return hash(("product", self.code, self.sandbox))

    def __repr__(self):
        return "Product({!r})".format(self.code)
