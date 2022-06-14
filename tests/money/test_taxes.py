from src.domain.money.amount import Money
from src.domain.money import taxes as mod
from tests.support import DomainTestCase

NET = Money.from_major("100.00")


class TaxRateTests(DomainTestCase):
    def test_name_and_percent(self):
        rate = mod.TaxRate("vat", 20)
        self.assertEqual("vat", rate.name)
        self.assertEqual(20.0, rate.percent)

    def test_fractional_percent(self):
        self.assertEqual(7.5, mod.TaxRate("gst", 7.5).percent)

    def test_basis_points(self):
        self.assertEqual(2000, mod.TaxRate("vat", 20).basis_points)

    def test_exclusive_by_default(self):
        self.assertFalse(mod.TaxRate("vat", 20).inclusive)

    def test_negative_percent_rejected(self):
        self.assertField("percent", mod.TaxRate, "vat", -1)

    def test_over_hundred_rejected(self):
        self.assertField("percent", mod.TaxRate, "vat", 101)

    def test_empty_name_rejected(self):
        self.assertField("name", mod.TaxRate, "", 20)


class ExclusiveTests(DomainTestCase):
    def setUp(self):
        self.rate = mod.TaxRate("vat", 20)

    def test_tax_on(self):
        self.assertEqual(Money.from_major("20.00"), self.rate.tax_on(NET))

    def test_net_is_unchanged(self):
        self.assertEqual(NET, self.rate.net_of(NET))

    def test_gross_adds_tax(self):
        self.assertEqual(Money.from_major("120.00"), self.rate.gross_of(NET))

    def test_breakdown_is_consistent(self):
        parts = self.rate.breakdown(NET)
        self.assertEqual(parts["gross"], parts["net"].plus(parts["tax"]))

    def test_rounding(self):
        self.assertEqual(Money(2), mod.TaxRate("vat", 20).tax_on(Money(9)))

    def test_non_money_rejected(self):
        self.assertField("amount", self.rate.tax_on, 100)


class InclusiveTests(DomainTestCase):
    def setUp(self):
        self.rate = mod.TaxRate("vat", 20, inclusive=True)
        self.gross = Money.from_major("120.00")

    def test_tax_is_extracted(self):
        self.assertEqual(Money.from_major("20.00"), self.rate.tax_on(self.gross))

    def test_net_removes_tax(self):
        self.assertEqual(Money.from_major("100.00"), self.rate.net_of(self.gross))

    def test_gross_is_unchanged(self):
        self.assertEqual(self.gross, self.rate.gross_of(self.gross))

    def test_breakdown_is_consistent(self):
        parts = self.rate.breakdown(self.gross)
        self.assertEqual(parts["gross"], parts["net"].plus(parts["tax"]))


class ZeroRateTests(DomainTestCase):
    def test_no_tax(self):
        self.assertTrue(mod.ZERO_RATE.tax_on(NET).is_zero())

    def test_gross_equals_net(self):
        self.assertEqual(NET, mod.ZERO_RATE.gross_of(NET))


class ValueSemanticsTests(DomainTestCase):
    def test_equality(self):
        self.assertEqual(mod.TaxRate("vat", 20), mod.TaxRate("vat", 20))

    def test_inclusive_flag_matters(self):
        self.assertNotEqual(mod.TaxRate("vat", 20), mod.TaxRate("vat", 20, True))

    def test_hashable(self):
        self.assertEqual(1, len({mod.TaxRate("vat", 20), mod.TaxRate("vat", 20)}))

    def test_to_dict(self):
        self.assertEqual(
            {"name": "vat", "percent": 20.0, "inclusive": False},
            mod.TaxRate("vat", 20).to_dict(),
        )

    def test_repr(self):
        self.assertIn("vat", repr(mod.TaxRate("vat", 20)))


class CombinedTests(DomainTestCase):
    def test_two_rates(self):
        parts = mod.combined([mod.TaxRate("state", 6), mod.TaxRate("city", 2)], NET)
        self.assertEqual(Money.from_major("8.00"), parts["tax"])

    def test_gross_is_consistent(self):
        parts = mod.combined([mod.TaxRate("state", 6)], NET)
        self.assertEqual(parts["net"].plus(parts["tax"]), parts["gross"])

    def test_no_rates(self):
        self.assertTrue(mod.combined([], NET)["tax"].is_zero())

    def test_inclusive_rate_rejected(self):
        self.assertField(
            "rates", mod.combined, [mod.TaxRate("vat", 20, True)], NET
        )
