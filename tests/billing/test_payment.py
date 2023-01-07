from src.domain.billing import payment as mod
from src.domain.money.amount import Money
from tests.support import DomainTestCase

CAPTURED = "2021-05-01T12:00:00Z"


def build(**overrides):
    payload = {
        "reference": "PAY-1",
        "subscription_reference": "I-1",
        "amount": Money.from_major("99.00"),
        "captured_at": CAPTURED,
    }
    payload.update(overrides)
    return mod.Payment(**payload)


class ConstructionTests(DomainTestCase):
    def test_defaults_to_completed(self):
        self.assertEqual(mod.COMPLETED, build().status)

    def test_refunded_defaults_to_zero(self):
        self.assertTrue(build().refunded.is_zero())

    def test_amount_must_be_money(self):
        self.assertField("amount", build, amount="99.00")

    def test_negative_amount(self):
        self.assertField("amount", build, amount=Money(-1))

    def test_zero_amount_is_allowed(self):
        self.assertTrue(build(amount=Money(0)).amount.is_zero())

    def test_unknown_status(self):
        self.assertField("status", build, status="pending")

    def test_refund_currency_must_match(self):
        self.assertField("refunded", build, refunded=Money(1, "EUR"))

    def test_refund_cannot_exceed_the_payment(self):
        self.assertField(
            "refunded",
            build,
            status=mod.PARTIALLY_REFUNDED,
            refunded=Money.from_major("100.00"),
        )

    def test_negative_refund(self):
        self.assertField("refunded", build, refunded=Money(-1))

    def test_declined_needs_a_reason(self):
        self.assertField("decline_reason", build, status=mod.DECLINED)

    def test_only_declined_carries_a_reason(self):
        self.assertField("decline_reason", build, decline_reason="card_declined")

    def test_unknown_decline_reason(self):
        self.assertField(
            "decline_reason", build, status=mod.DECLINED, decline_reason="bad_vibes"
        )

    def test_declined_helper(self):
        payment = mod.Payment.declined(
            "PAY-2", "I-1", Money(9900), CAPTURED, "insufficient_funds"
        )
        self.assertEqual(mod.DECLINED, payment.status)
        self.assertEqual("insufficient_funds", payment.decline_reason)


class NetTests(DomainTestCase):
    def test_completed(self):
        self.assertEqual(Money.from_major("99.00"), build().net())

    def test_partially_refunded(self):
        payment = build(
            status=mod.PARTIALLY_REFUNDED, refunded=Money.from_major("9.00")
        )
        self.assertEqual(Money.from_major("90.00"), payment.net())

    def test_declined_nets_nothing(self):
        payment = mod.Payment.declined("PAY-2", "I-1", Money(9900), CAPTURED, "unknown")
        self.assertTrue(payment.net().is_zero())

    def test_fully_refunded(self):
        payment = build(status=mod.REFUNDED, refunded=Money.from_major("99.00"))
        self.assertTrue(payment.net().is_zero())


class StatusTests(DomainTestCase):
    def test_completed_is_settled(self):
        self.assertTrue(build().is_settled())

    def test_declined_is_not_settled(self):
        payment = mod.Payment.declined("PAY-2", "I-1", Money(9900), CAPTURED, "unknown")
        self.assertFalse(payment.is_settled())

    def test_partially_refunded_is_settled(self):
        payment = build(status=mod.PARTIALLY_REFUNDED, refunded=Money(1))
        self.assertTrue(payment.is_settled())

    def test_fully_refunded_is_not_settled(self):
        payment = build(status=mod.REFUNDED, refunded=Money.from_major("99.00"))
        self.assertFalse(payment.is_settled())

    def test_refundable(self):
        self.assertTrue(build().is_refundable())

    def test_fully_refunded_is_not_refundable(self):
        payment = build(status=mod.REFUNDED, refunded=Money.from_major("99.00"))
        self.assertFalse(payment.is_refundable())


class RefundTests(DomainTestCase):
    def test_full_refund_by_default(self):
        refunded = build().refund()
        self.assertEqual(mod.REFUNDED, refunded.status)
        self.assertEqual(Money.from_major("99.00"), refunded.refunded)

    def test_partial_refund(self):
        refunded = build().refund(Money.from_major("9.00"))
        self.assertEqual(mod.PARTIALLY_REFUNDED, refunded.status)

    def test_second_refund_completes_it(self):
        once = build().refund(Money.from_major("9.00"))
        twice = once.refund(Money.from_major("90.00"))
        self.assertEqual(mod.REFUNDED, twice.status)

    def test_refund_returns_a_copy(self):
        payment = build()
        payment.refund()
        self.assertTrue(payment.refunded.is_zero())

    def test_over_refund_is_rejected(self):
        self.assertField("amount", build().refund, Money.from_major("100.00"))

    def test_zero_refund_is_rejected(self):
        self.assertField("amount", build().refund, Money(0))

    def test_negative_refund_is_rejected(self):
        self.assertField("amount", build().refund, Money(-1))

    def test_non_money_refund_is_rejected(self):
        self.assertField("amount", build().refund, "9.00")

    def test_declined_cannot_be_refunded(self):
        payment = mod.Payment.declined("PAY-2", "I-1", Money(9900), CAPTURED, "unknown")
        self.assertField("status", payment.refund)


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build().to_dict()
        self.assertEqual("PAY-1", payload["reference"])
        self.assertIsNone(payload["decline_reason"])

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_inequality(self):
        self.assertNotEqual(build(), build().refund())

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("PAY-1", repr(build()))


class AggregateTests(DomainTestCase):
    def setUp(self):
        self.good = build()
        self.partial = build(
            reference="PAY-2", status=mod.PARTIALLY_REFUNDED, refunded=Money.from_major("9.00")
        )
        self.bad = mod.Payment.declined(
            "PAY-3", "I-1", Money(9900), "2021-06-01T00:00:00Z", "card_declined"
        )

    def test_settled_total(self):
        total = mod.settled_total([self.good, self.partial, self.bad], "USD")
        self.assertEqual(Money.from_major("189.00"), total)

    def test_settled_total_of_nothing(self):
        self.assertTrue(mod.settled_total([], "USD").is_zero())

    def test_declines(self):
        self.assertEqual((self.bad,), mod.declines([self.good, self.bad]))

    def test_last_settled(self):
        later = build(reference="PAY-4", captured_at="2021-07-01T00:00:00Z")
        self.assertEqual(later, mod.last_settled([self.good, later, self.bad]))

    def test_last_settled_of_nothing(self):
        self.assertIsNone(mod.last_settled([self.bad]))

    def test_last_settled_default(self):
        self.assertEqual("x", mod.last_settled([], "x"))
