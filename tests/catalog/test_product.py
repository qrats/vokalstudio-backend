from src.domain.catalog import product as mod
from src.domain.core.ids import ExternalRef
from tests.support import DomainTestCase


def build(**overrides):
    payload = {"name": "PRO", "description": "Everything the studio offers."}
    payload.update(overrides)
    return mod.Product(**payload)


class ConstructionTests(DomainTestCase):
    def test_code_is_derived_from_the_name(self):
        self.assertEqual("pro", build().code)

    def test_explicit_code(self):
        self.assertEqual("studio-pro", build(code="Studio PRO").code)

    def test_defaults(self):
        product = build()
        self.assertEqual("service", product.type)
        self.assertEqual("software", product.category)
        self.assertFalse(product.sandbox)

    def test_empty_name(self):
        self.assertField("name", build, name="")

    def test_long_name(self):
        self.assertField("name", build, name="x" * 128)

    def test_empty_description(self):
        self.assertField("description", build, description="")

    def test_unknown_type(self):
        self.assertField("type", build, type="subscription")

    def test_unknown_category(self):
        self.assertField("category", build, category="hardware")

    def test_sandbox_accepts_text(self):
        self.assertTrue(build(sandbox="true").sandbox)


class RefTests(DomainTestCase):
    def test_no_ref_by_default(self):
        self.assertIsNone(build().ref)
        self.assertFalse(build().is_linked())

    def test_ref_from_text(self):
        product = build(ref="paypal:PROD-1")
        self.assertEqual("paypal", product.ref.provider)
        self.assertTrue(product.is_linked())

    def test_ref_object(self):
        product = build(ref=ExternalRef("paypal", "PROD-1"))
        self.assertEqual("PROD-1", product.ref.value)

    def test_with_ref_returns_a_copy(self):
        product = build()
        linked = product.with_ref("paypal:PROD-1")
        self.assertIsNone(product.ref)
        self.assertTrue(linked.is_linked())

    def test_with_ref_keeps_everything_else(self):
        product = build(category="broadcast", sandbox=True)
        linked = product.with_ref("paypal:PROD-1")
        self.assertEqual("broadcast", linked.category)
        self.assertTrue(linked.sandbox)

    def test_bad_ref(self):
        self.assertField("ref", build, ref="paypal")


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build().to_dict()
        self.assertEqual("pro", payload["code"])
        self.assertNotIn("ref", payload)

    def test_to_dict_includes_ref(self):
        self.assertEqual("paypal:PROD-1", build(ref="paypal:PROD-1").to_dict()["ref"])

    def test_round_trip(self):
        self.assertRoundTrips(mod.Product.from_dict, build(ref="paypal:PROD-1"))

    def test_from_dict_uses_defaults(self):
        product = mod.Product.from_dict({"name": "PRO", "description": "All of it."})
        self.assertEqual("service", product.type)

    def test_summary_truncates(self):
        product = build(description="word " * 40)
        self.assertLessEqual(len(product.summary(30)), 30)

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_inequality(self):
        self.assertNotEqual(build(), build(category="broadcast"))

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("pro", repr(build()))
