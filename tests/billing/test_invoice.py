from src.domain.billing import invoice as mod
from src.domain.money.amount import Money
from src.domain.money.taxes import TaxRate
from tests.support import DomainTestCase

VAT = TaxRate("vat", 20)


class LineItemTests(DomainTestCase):
    def test_untaxed_line(self):
        line = mod.LineItem("PRO plan", Money.from_major("99.00"))
        self.assertEqual(Money.from_major("99.00"), line.net)
        self.assertTrue(line.tax.is_zero())
        self.assertEqual(Money.from_major("99.00"), line.gross)

    def test_quantity_multiplies(self):
        line = mod.LineItem("Seat", Money.from_major("10.00"), 3)
        self.assertEqual(Money.from_major("30.00"), line.gross)

    def test_exclusive_tax(self):
        line = mod.LineItem("PRO plan", Money.from_major("100.00"), 1, VAT)
        self.assertEqual(Money.from_major("20.00"), line.tax)
        self.assertEqual(Money.from_major("120.00"), line.gross)

    def test_inclusive_tax(self):
        line = mod.LineItem(
            "PRO plan", Money.from_major("120.00"), 1, TaxRate("vat", 20, True)
        )
        self.assertEqual(Money.from_major("100.00"), line.net)
        self.assertEqual(Money.from_major("120.00"), line.gross)

    def test_tax_scales_with_quantity(self):
        line = mod.LineItem("Seat", Money.from_major("100.00"), 2, VAT)
        self.assertEqual(Money.from_major("40.00"), line.tax)

    def test_price_must_be_money(self):
        self.assertField("unit_price", mod.LineItem, "Seat", "10.00")

    def test_quantity_floor(self):
        self.assertField("quantity", mod.LineItem, "Seat", Money(1), 0)

    def test_empty_description(self):
        self.assertField("description", mod.LineItem, "", Money(1))

    def test_to_dict(self):
        payload = mod.LineItem("Seat", Money.from_major("10.00"), 2).to_dict()
        self.assertEqual(2, payload["quantity"])
        self.assertEqual("20.00", payload["gross"]["display"])

    def test_equality(self):
        one = mod.LineItem("Seat", Money(1))
        self.assertEqual(one, mod.LineItem("Seat", Money(1)))

    def test_hashable(self):
        self.assertEqual(1, len({mod.LineItem("Seat", Money(1)), mod.LineItem("Seat", Money(1))}))

    def test_repr(self):
        self.assertIn("Seat", repr(mod.LineItem("Seat", Money(1))))


_DEFAULT_LINES = object()


def invoice(lines=_DEFAULT_LINES, **overrides):
    if lines is _DEFAULT_LINES:
        lines = [mod.LineItem("PRO plan", Money.from_major("99.00"))]
    payload = {
        "number": "INV-2021-0001",
        "user_id": "u-1",
        "issued_on": "2021-05-01",
        "lines": lines,
    }
    payload.update(overrides)
    return mod.Invoice(**payload)


class InvoiceTests(DomainTestCase):
    def test_currency_comes_from_the_lines(self):
        self.assertEqual("USD", invoice().currency)

    def test_no_lines(self):
        self.assertField("lines", invoice, lines=[])

    def test_mixed_currencies(self):
        lines = [
            mod.LineItem("A", Money(100, "USD")),
            mod.LineItem("B", Money(100, "EUR")),
        ]
        self.assertField("lines", invoice, lines=lines)

    def test_empty_number(self):
        self.assertField("number", invoice, number="")

    def test_bad_date(self):
        self.assertField("issued_on", invoice, issued_on="01/05/2021")

    def test_totals_without_tax(self):
        one = invoice()
        self.assertEqual(Money.from_major("99.00"), one.net)
        self.assertTrue(one.tax.is_zero())
        self.assertEqual(Money.from_major("99.00"), one.total)

    def test_totals_with_tax(self):
        one = invoice(lines=[mod.LineItem("PRO", Money.from_major("100.00"), 1, VAT)])
        self.assertEqual(Money.from_major("20.00"), one.tax)
        self.assertEqual(Money.from_major("120.00"), one.total)

    def test_several_lines(self):
        one = invoice(
            lines=[
                mod.LineItem("PRO", Money.from_major("99.00")),
                mod.LineItem("Seat", Money.from_major("10.00"), 2),
            ]
        )
        self.assertEqual(Money.from_major("119.00"), one.total)

    def test_with_line_returns_a_copy(self):
        one = invoice()
        two = one.with_line(mod.LineItem("Seat", Money.from_major("10.00")))
        self.assertEqual(1, len(one.lines))
        self.assertEqual(2, len(two.lines))

    def test_total_equals_net_plus_tax(self):
        one = invoice(lines=[mod.LineItem("PRO", Money.from_major("100.00"), 1, VAT)])
        self.assertEqual(one.total, one.net.plus(one.tax))


class TaxSummaryTests(DomainTestCase):
    def test_untaxed_invoice(self):
        self.assertEqual({}, invoice().tax_summary())

    def test_one_rate(self):
        one = invoice(lines=[mod.LineItem("PRO", Money.from_major("100.00"), 1, VAT)])
        self.assertEqual({"vat": Money.from_major("20.00")}, one.tax_summary())

    def test_two_rates(self):
        one = invoice(
            lines=[
                mod.LineItem("PRO", Money.from_major("100.00"), 1, VAT),
                mod.LineItem("Seat", Money.from_major("100.00"), 1, TaxRate("city", 2)),
            ]
        )
        self.assertEqual(
            {"vat": Money.from_major("20.00"), "city": Money.from_major("2.00")},
            one.tax_summary(),
        )

    def test_same_rate_twice_is_summed(self):
        one = invoice(
            lines=[
                mod.LineItem("PRO", Money.from_major("100.00"), 1, VAT),
                mod.LineItem("Seat", Money.from_major("50.00"), 1, VAT),
            ]
        )
        self.assertEqual({"vat": Money.from_major("30.00")}, one.tax_summary())


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = invoice().to_dict()
        self.assertEqual("INV-2021-0001", payload["number"])
        self.assertEqual(1, len(payload["lines"]))
        self.assertEqual("99.00", payload["total"]["display"])

    def test_equality(self):
        self.assertEqual(invoice(), invoice())

    def test_inequality(self):
        self.assertNotEqual(invoice(), invoice(number="INV-2"))

    def test_hashable(self):
        self.assertEqual(1, len({invoice(), invoice()}))

    def test_repr(self):
        self.assertIn("INV-2021-0001", repr(invoice()))
