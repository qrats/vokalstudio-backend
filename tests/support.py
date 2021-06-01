"""Shared fixtures and assertions for the domain test suite."""

import unittest

from src.domain.core.errors import DomainError


class DomainTestCase(unittest.TestCase):
    """Adds assertions for the error contract the domain layer promises."""

    def assertRaisesCode(self, code, callable_, *args, **kwargs):
        with self.assertRaises(DomainError) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)
        return caught.exception

    def assertField(self, field, callable_, *args, **kwargs):
        with self.assertRaises(DomainError) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(field, caught.exception.details.get("field"))
        return caught.exception

    def assertRoundTrips(self, factory, value):
        """A value object must rebuild itself from its own ``to_dict``."""
        rebuilt = factory(value.to_dict())
        self.assertEqual(value.to_dict(), rebuilt.to_dict())
        return rebuilt


def sample_stream_key(index=1):
    return "live_{}_{}".format(100000 + index, "k" * 12)
