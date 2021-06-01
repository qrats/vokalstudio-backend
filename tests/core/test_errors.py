from src.domain.core import errors
from tests.support import DomainTestCase


class DomainErrorTests(DomainTestCase):
    def test_base_code_and_status(self):
        error = errors.DomainError("boom")
        self.assertEqual("domain_error", error.code)
        self.assertEqual(400, error.status)
        self.assertEqual("boom", error.message)

    def test_to_dict_omits_empty_details(self):
        self.assertEqual(
            {"code": "domain_error", "message": "boom"},
            errors.DomainError("boom").to_dict(),
        )

    def test_to_dict_includes_details(self):
        error = errors.DomainError("boom", {"field": "title"})
        self.assertEqual({"field": "title"}, error.to_dict()["details"])

    def test_details_are_copied(self):
        given = {"field": "title"}
        error = errors.DomainError("boom", given)
        given["field"] = "other"
        self.assertEqual("title", error.details["field"])

    def test_repr_names_the_subclass(self):
        self.assertIn("ValidationError", repr(errors.ValidationError("no")))

    def test_str_is_the_message(self):
        self.assertEqual("boom", str(errors.DomainError("boom")))


class ValidationErrorTests(DomainTestCase):
    def test_code_and_status(self):
        error = errors.ValidationError("bad", field="title")
        self.assertEqual("validation_failed", error.code)
        self.assertEqual(422, error.status)

    def test_field_lands_in_details(self):
        self.assertEqual("title", errors.ValidationError("bad", "title").details["field"])

    def test_explicit_details_win(self):
        error = errors.ValidationError("bad", "title", {"field": "slug"})
        self.assertEqual("slug", error.details["field"])

    def test_field_is_optional(self):
        error = errors.ValidationError("bad")
        self.assertIsNone(error.field)
        self.assertEqual({}, error.details)


class NotFoundErrorTests(DomainTestCase):
    def test_status(self):
        self.assertEqual(404, errors.NotFoundError("gone").status)

    def test_kind_and_ref(self):
        error = errors.NotFoundError("gone", kind="episode", ref="e-1")
        self.assertEqual({"kind": "episode", "ref": "e-1"}, error.details)

    def test_details_stay_empty_without_kind(self):
        self.assertEqual({}, errors.NotFoundError("gone").details)


class StateErrorTests(DomainTestCase):
    def test_status_is_conflict(self):
        self.assertEqual(409, errors.StateError("no").status)

    def test_transition_is_recorded(self):
        error = errors.StateError("no", current="cancelled", attempted="suspend")
        self.assertEqual("cancelled", error.current)
        self.assertEqual("suspend", error.attempted)
        self.assertEqual("suspend", error.details["attempted"])


class PermissionErrorTests(DomainTestCase):
    def test_status(self):
        self.assertEqual(403, errors.PermissionError_("nope").status)

    def test_action_and_subject(self):
        error = errors.PermissionError_("nope", action="publish", subject="u-1")
        self.assertEqual("publish", error.details["action"])
        self.assertEqual("u-1", error.details["subject"])


class QuotaErrorTests(DomainTestCase):
    def test_status(self):
        self.assertEqual(429, errors.QuotaError("full").status)

    def test_usage_is_recorded(self):
        error = errors.QuotaError("full", feature="episodes", limit=10, used=10)
        self.assertEqual(10, error.limit)
        self.assertEqual("episodes", error.details["feature"])


class ConflictErrorTests(DomainTestCase):
    def test_status(self):
        self.assertEqual(409, errors.ConflictError("dupe").status)


class ErrorStatusTests(DomainTestCase):
    def test_domain_error_status(self):
        self.assertEqual(404, errors.error_status(errors.NotFoundError("x")))

    def test_unknown_error_is_500(self):
        self.assertEqual(500, errors.error_status(ValueError("x")))

    def test_unknown_code_falls_back(self):
        class Odd(errors.DomainError):
            code = "not_registered"

        self.assertEqual(400, Odd("x").status)
