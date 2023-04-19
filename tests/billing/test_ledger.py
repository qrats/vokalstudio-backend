from src.domain.billing import ledger as mod
from src.domain.money.amount import Money
from tests.support import DomainTestCase

MAY = "2021-05-01T00:00:00Z"
JUNE = "2021-06-01T00:00:00Z"


def charge(major="99.00", at=MAY, **kwargs):
    return mod.Entry(mod.CHARGE, Money.from_major(major), at, **kwargs)


def payment(major="99.00", at=JUNE, **kwargs):
    return mod.Entry(mod.PAYMENT, Money.from_major(major), at, **kwargs)


class EntryTests(DomainTestCase):
    def test_kind_and_amount(self):
        entry = charge()
        self.assertEqual(mod.CHARGE, entry.kind)
        self.assertEqual(Money.from_major("99.00"), entry.amount)

    def test_unknown_kind(self):
        self.assertField("kind", mod.Entry, "chargeback", Money(1), MAY)

    def test_amount_must_be_money(self):
        self.assertField("amount", mod.Entry, mod.CHARGE, "1.00", MAY)

    def test_negative_amount(self):
        self.assertField("amount", mod.Entry, mod.CHARGE, Money(-1), MAY)

    def test_zero_charge_is_rejected(self):
        self.assertField("amount", mod.Entry, mod.CHARGE, Money(0), MAY)

    def test_zero_adjustment_is_allowed(self):
        self.assertTrue(mod.Entry(mod.ADJUSTMENT, Money(0), MAY).amount.is_zero())

    def test_note(self):
        self.assertEqual("goodwill", charge(note="goodwill").note)

    def test_note_is_optional(self):
        self.assertIsNone(charge().note)

    def test_reference(self):
        self.assertEqual("PAY-1", charge(reference="PAY-1").reference)

    def test_charge_is_a_debit(self):
        self.assertEqual(9900, charge().signed_units)

    def test_refund_is_a_debit(self):
        entry = mod.Entry(mod.REFUND, Money.from_major("9.00"), MAY)
        self.assertEqual(900, entry.signed_units)

    def test_payment_is_a_credit(self):
        self.assertEqual(-9900, payment().signed_units)

    def test_credit_is_a_credit(self):
        entry = mod.Entry(mod.CREDIT, Money.from_major("5.00"), MAY)
        self.assertEqual(-500, entry.signed_units)

    def test_to_dict(self):
        payload = charge(reference="PAY-1").to_dict()
        self.assertEqual("charge", payload["kind"])
        self.assertEqual(9900, payload["signed_units"])

    def test_equality(self):
        self.assertEqual(charge(), charge())

    def test_hashable(self):
        self.assertEqual(1, len({charge(), charge()}))

    def test_repr(self):
        self.assertIn("charge", repr(charge()))


class LedgerTests(DomainTestCase):
    def test_empty_balance(self):
        self.assertTrue(mod.Ledger("USD").balance().is_zero())

    def test_charge_raises_the_balance(self):
        self.assertEqual(
            Money.from_major("99.00"), mod.Ledger("USD", [charge()]).balance()
        )

    def test_payment_settles_it(self):
        book = mod.Ledger("USD", [charge(), payment()])
        self.assertTrue(book.balance().is_zero())

    def test_overpayment_leaves_credit(self):
        book = mod.Ledger("USD", [charge(), payment("120.00")])
        self.assertEqual(Money.from_major("-21.00"), book.balance())

    def test_entries_are_sorted_by_time(self):
        book = mod.Ledger("USD", [payment(), charge()])
        self.assertEqual(mod.CHARGE, book.entries[0].kind)

    def test_currency_mismatch(self):
        entry = mod.Entry(mod.CHARGE, Money(1, "EUR"), MAY)
        self.assertField("entries", mod.Ledger, "USD", [entry])

    def test_with_entry_returns_a_copy(self):
        book = mod.Ledger("USD", [charge()])
        book.with_entry(payment())
        self.assertEqual(1, len(book.entries))

    def test_balance_until_a_moment(self):
        book = mod.Ledger("USD", [charge(), payment()])
        self.assertEqual(Money.from_major("99.00"), book.balance("2021-05-15T00:00:00Z"))

    def test_balance_includes_the_boundary(self):
        book = mod.Ledger("USD", [charge()])
        self.assertEqual(Money.from_major("99.00"), book.balance(MAY))

    def test_of_kind(self):
        book = mod.Ledger("USD", [charge(), payment()])
        self.assertEqual(1, len(book.of_kind(mod.PAYMENT)))

    def test_of_unknown_kind(self):
        self.assertField("kind", mod.Ledger("USD").of_kind, "chargeback")

    def test_total_of(self):
        book = mod.Ledger("USD", [charge(), charge(at=JUNE)])
        self.assertEqual(Money.from_major("198.00"), book.total_of(mod.CHARGE))

    def test_total_of_an_absent_kind(self):
        self.assertTrue(mod.Ledger("USD", [charge()]).total_of(mod.REFUND).is_zero())

    def test_is_settled(self):
        self.assertTrue(mod.Ledger("USD", [charge(), payment()]).is_settled())

    def test_is_in_arrears(self):
        self.assertTrue(mod.Ledger("USD", [charge()]).is_in_arrears())

    def test_credit_is_not_arrears(self):
        self.assertFalse(mod.Ledger("USD", [payment()]).is_in_arrears())


class StatementTests(DomainTestCase):
    def test_running_balance(self):
        book = mod.Ledger("USD", [charge(), payment("50.00")])
        rows = book.statement()
        self.assertEqual("99.00", rows[0]["balance"]["display"])
        self.assertEqual("49.00", rows[1]["balance"]["display"])

    def test_empty_statement(self):
        self.assertEqual((), mod.Ledger("USD").statement())

    def test_row_carries_the_entry(self):
        rows = mod.Ledger("USD", [charge(note="first")]).statement()
        self.assertEqual("first", rows[0]["note"])

    def test_to_dict(self):
        payload = mod.Ledger("USD", [charge()]).to_dict()
        self.assertEqual("USD", payload["currency"])
        self.assertEqual(1, len(payload["entries"]))

    def test_equality(self):
        self.assertEqual(mod.Ledger("USD", [charge()]), mod.Ledger("USD", [charge()]))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Ledger("USD"), mod.Ledger("USD")}))

    def test_repr(self):
        self.assertIn("USD", repr(mod.Ledger("USD")))
