from src.domain.money import currency as mod
from tests.support import DomainTestCase


class NormalizeTests(DomainTestCase):
    def test_uppercases(self):
        self.assertEqual("USD", mod.normalize_currency("usd"))

    def test_trims(self):
        self.assertEqual("EUR", mod.normalize_currency("  eur "))

    def test_unknown_code(self):
        error = self.assertRaisesCode("validation_failed", mod.normalize_currency, "XYZ")
        self.assertIn("USD", error.details["supported"])

    def test_wrong_length(self):
        self.assertField("currency", mod.normalize_currency, "US")

    def test_none(self):
        self.assertField("currency", mod.normalize_currency, None)

    def test_field_name(self):
        self.assertField("plan_currency", mod.normalize_currency, "XYZ", "plan_currency")


class TableTests(DomainTestCase):
    def test_default_is_supported(self):
        self.assertIn(mod.DEFAULT_CURRENCY, mod.CURRENCIES)

    def test_two_place_currency(self):
        self.assertEqual(2, mod.exponent("USD"))

    def test_zero_place_currency(self):
        self.assertEqual(0, mod.exponent("JPY"))

    def test_minor_units_per_major(self):
        self.assertEqual(100, mod.minor_units_per_major("EUR"))

    def test_minor_units_for_yen(self):
        self.assertEqual(1, mod.minor_units_per_major("JPY"))

    def test_symbol(self):
        self.assertEqual("£", mod.symbol("gbp"))

    def test_name(self):
        self.assertEqual("Euro", mod.currency_name("EUR"))

    def test_is_supported(self):
        self.assertTrue(mod.is_supported("usd"))

    def test_is_not_supported(self):
        self.assertFalse(mod.is_supported("XYZ"))

    def test_is_supported_rejects_non_string(self):
        self.assertFalse(mod.is_supported(None))

    def test_supported_codes_are_sorted(self):
        codes = mod.supported_codes()
        self.assertEqual(tuple(sorted(codes)), codes)

    def test_every_entry_is_complete(self):
        for code, entry in mod.CURRENCIES.items():
            self.assertEqual(3, len(code))
            self.assertIn(entry["exponent"], (0, 2))
            self.assertTrue(entry["symbol"])
            self.assertTrue(entry["name"])
