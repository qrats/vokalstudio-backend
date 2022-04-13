from src.domain.money import amount as mod
from tests.support import DomainTestCase


class ConstructionTests(DomainTestCase):
    def test_units_and_currency(self):
        price = mod.Money(9900, "usd")
        self.assertEqual(9900, price.units)
        self.assertEqual("USD", price.currency)

    def test_default_currency(self):
        self.assertEqual("USD", mod.Money(1).currency)

    def test_zero(self):
        self.assertTrue(mod.Money.zero("EUR").is_zero())

    def test_negative_units_allowed(self):
        self.assertTrue(mod.Money(-1).is_negative())

    def test_float_units_rejected(self):
        self.assertField("units", mod.Money, 1.5)

    def test_unknown_currency_rejected(self):
        self.assertField("currency", mod.Money, 1, "XYZ")


class FromMajorTests(DomainTestCase):
    def test_two_places(self):
        self.assertEqual(9900, mod.Money.from_major("99.00").units)

    def test_one_place_is_padded(self):
        self.assertEqual(9950, mod.Money.from_major("99.5").units)

    def test_no_decimal_point(self):
        self.assertEqual(9900, mod.Money.from_major("99").units)

    def test_negative(self):
        self.assertEqual(-9900, mod.Money.from_major("-99.00").units)

    def test_zero_exponent_currency(self):
        self.assertEqual(1200, mod.Money.from_major("1200", "JPY").units)

    def test_zero_exponent_rejects_decimals(self):
        self.assertField("amount", mod.Money.from_major, "12.5", "JPY")

    def test_too_many_places(self):
        self.assertField("amount", mod.Money.from_major, "1.234")

    def test_garbage(self):
        self.assertField("amount", mod.Money.from_major, "ninety nine")

    def test_accepts_a_number(self):
        self.assertEqual(9900, mod.Money.from_major(99).units)

    def test_leading_dot_is_rejected(self):
        self.assertField("amount", mod.Money.from_major, ".5")


class FormattingTests(DomainTestCase):
    def test_to_major(self):
        self.assertEqual("99.00", mod.Money(9900).to_major())

    def test_to_major_pads(self):
        self.assertEqual("0.05", mod.Money(5).to_major())

    def test_to_major_negative(self):
        self.assertEqual("-0.05", mod.Money(-5).to_major())

    def test_to_major_zero_exponent(self):
        self.assertEqual("1200", mod.Money(1200, "JPY").to_major())

    def test_format_uses_symbol(self):
        self.assertEqual("$99.00", mod.Money(9900).format())

    def test_round_trip(self):
        price = mod.Money(12345, "EUR")
        self.assertEqual(price, mod.Money.from_major(price.to_major(), "EUR"))

    def test_to_dict(self):
        self.assertEqual(
            {"units": 9900, "currency": "USD", "display": "99.00"},
            mod.Money(9900).to_dict(),
        )

    def test_repr(self):
        self.assertEqual("Money(99.00 USD)", repr(mod.Money(9900)))


class ArithmeticTests(DomainTestCase):
    def test_plus(self):
        self.assertEqual(mod.Money(300), mod.Money(100).plus(mod.Money(200)))

    def test_minus(self):
        self.assertEqual(mod.Money(-100), mod.Money(100).minus(mod.Money(200)))

    def test_times(self):
        self.assertEqual(mod.Money(300), mod.Money(100).times(3))

    def test_times_rejects_float(self):
        self.assertField("factor", mod.Money(100).times, 1.5)

    def test_scaled_by(self):
        self.assertEqual(mod.Money(20), mod.Money(100).scaled_by(0.2))

    def test_divided_by(self):
        self.assertEqual(mod.Money(33), mod.Money(100).divided_by(3))

    def test_negated(self):
        self.assertEqual(mod.Money(-100), mod.Money(100).negated())

    def test_absolute(self):
        self.assertEqual(mod.Money(100), mod.Money(-100).absolute())

    def test_mixed_currencies_are_rejected(self):
        self.assertField("currency", mod.Money(1, "USD").plus, mod.Money(1, "EUR"))

    def test_non_money_is_rejected(self):
        self.assertField("value", mod.Money(1).plus, 1)

    def test_arithmetic_does_not_mutate(self):
        price = mod.Money(100)
        price.plus(mod.Money(1))
        self.assertEqual(100, price.units)


class PredicateTests(DomainTestCase):
    def test_is_zero(self):
        self.assertTrue(mod.Money(0).is_zero())

    def test_is_positive(self):
        self.assertTrue(mod.Money(1).is_positive())

    def test_zero_is_not_positive(self):
        self.assertFalse(mod.Money(0).is_positive())

    def test_is_negative(self):
        self.assertTrue(mod.Money(-1).is_negative())


class ComparisonTests(DomainTestCase):
    def test_equality(self):
        self.assertEqual(mod.Money(1, "EUR"), mod.Money(1, "EUR"))

    def test_currency_matters(self):
        self.assertNotEqual(mod.Money(1, "EUR"), mod.Money(1, "USD"))

    def test_ordering(self):
        self.assertLess(mod.Money(1), mod.Money(2))
        self.assertLessEqual(mod.Money(2), mod.Money(2))
        self.assertGreater(mod.Money(3), mod.Money(2))
        self.assertGreaterEqual(mod.Money(2), mod.Money(2))

    def test_ordering_across_currencies_is_rejected(self):
        self.assertField("currency", mod.Money(1, "USD").__lt__, mod.Money(2, "EUR"))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Money(1), mod.Money(1)}))

    def test_not_equal_to_int(self):
        self.assertNotEqual(mod.Money(1), 1)


class AggregateTests(DomainTestCase):
    def test_total(self):
        self.assertEqual(mod.Money(300), mod.total([mod.Money(100), mod.Money(200)]))

    def test_total_of_empty(self):
        self.assertTrue(mod.total([]).is_zero())

    def test_total_respects_currency(self):
        self.assertEqual("EUR", mod.total([], "EUR").currency)

    def test_total_rejects_mixed(self):
        self.assertField("currency", mod.total, [mod.Money(1, "EUR")])

    def test_maximum(self):
        self.assertEqual(mod.Money(200), mod.maximum([mod.Money(100), mod.Money(200)]))

    def test_minimum(self):
        self.assertEqual(mod.Money(100), mod.minimum([mod.Money(100), mod.Money(200)]))

    def test_maximum_of_empty(self):
        self.assertIsNone(mod.maximum([]))

    def test_minimum_default(self):
        self.assertEqual("x", mod.minimum([], "x"))
