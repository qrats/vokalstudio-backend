from src.domain.billing import proration as mod
from src.domain.catalog.plan import BillingCycle
from src.domain.money.amount import Money
from tests.billing.factories import make_plan
from tests.support import DomainTestCase

BASIC = make_plan("BASIC", "29.00")
PRO = make_plan("PRO", "99.00")


class ClassifyTests(DomainTestCase):
    def test_upgrade(self):
        self.assertEqual(mod.UPGRADE, mod.classify(BASIC, PRO))

    def test_downgrade(self):
        self.assertEqual(mod.DOWNGRADE, mod.classify(PRO, BASIC))

    def test_lateral(self):
        self.assertEqual(mod.LATERAL, mod.classify(PRO, make_plan("PRO2", "99.00")))

    def test_currency_mismatch(self):
        other = make_plan("EU", cycles=[BillingCycle(Money.from_major("99.00", "EUR"))])
        self.assertField("target_plan", mod.classify, PRO, other)


class UnusedCreditTests(DomainTestCase):
    def test_half_way_through(self):
        credit = mod.unused_credit(PRO, "2021-05-01", "2021-05-31", "2021-05-16")
        self.assertEqual(Money.from_major("49.50"), credit)

    def test_nothing_used(self):
        credit = mod.unused_credit(PRO, "2021-05-01", "2021-05-31", "2021-05-01")
        self.assertEqual(Money.from_major("99.00"), credit)

    def test_everything_used(self):
        credit = mod.unused_credit(PRO, "2021-05-01", "2021-05-31", "2021-05-31")
        self.assertTrue(credit.is_zero())

    def test_period_must_have_length(self):
        self.assertField(
            "period_end", mod.unused_credit, PRO, "2021-05-01", "2021-05-01", "2021-05-01"
        )

    def test_before_the_period(self):
        self.assertField(
            "changed_on", mod.unused_credit, PRO, "2021-05-01", "2021-05-31", "2021-04-30"
        )

    def test_after_the_period(self):
        self.assertField(
            "changed_on", mod.unused_credit, PRO, "2021-05-01", "2021-05-31", "2021-06-01"
        )


class ChangeQuoteTests(DomainTestCase):
    def test_upgrade_charges_the_difference(self):
        quote = mod.change_quote(BASIC, PRO, "2021-05-01", "2021-05-31", "2021-05-16")
        self.assertEqual(mod.UPGRADE, quote["kind"])
        self.assertEqual(Money.from_major("14.50"), quote["credit"])
        self.assertEqual(Money.from_major("35.00"), quote["charge_now"])

    def test_upgrade_takes_effect_at_once(self):
        quote = mod.change_quote(BASIC, PRO, "2021-05-01", "2021-05-31", "2021-05-16")
        self.assertEqual("2021-05-16", quote["effective_on"].isoformat())

    def test_upgrade_on_the_last_day_costs_nothing(self):
        quote = mod.change_quote(BASIC, PRO, "2021-05-01", "2021-05-31", "2021-05-31")
        self.assertTrue(quote["charge_now"].is_zero())

    def test_downgrade_charges_nothing_now(self):
        quote = mod.change_quote(PRO, BASIC, "2021-05-01", "2021-05-31", "2021-05-16")
        self.assertEqual(mod.DOWNGRADE, quote["kind"])
        self.assertTrue(quote["charge_now"].is_zero())

    def test_downgrade_waits_for_the_renewal(self):
        quote = mod.change_quote(PRO, BASIC, "2021-05-01", "2021-05-31", "2021-05-16")
        self.assertEqual("2021-05-31", quote["effective_on"].isoformat())

    def test_downgrade_still_reports_the_credit(self):
        quote = mod.change_quote(PRO, BASIC, "2021-05-01", "2021-05-31", "2021-05-16")
        self.assertEqual(Money.from_major("49.50"), quote["credit"])

    def test_lateral_move_is_free(self):
        quote = mod.change_quote(
            PRO, make_plan("PRO2", "99.00"), "2021-05-01", "2021-05-31", "2021-05-16"
        )
        self.assertEqual(mod.LATERAL, quote["kind"])
        self.assertTrue(quote["charge_now"].is_zero())


class CancellationRefundTests(DomainTestCase):
    def test_no_refund_by_default(self):
        refund = mod.refund_on_cancellation(PRO, "2021-05-01", "2021-05-31", "2021-05-16")
        self.assertTrue(refund.is_zero())

    def test_prorated_refund(self):
        refund = mod.refund_on_cancellation(
            PRO, "2021-05-01", "2021-05-31", "2021-05-16", "prorated"
        )
        self.assertEqual(Money.from_major("49.50"), refund)

    def test_full_refund(self):
        refund = mod.refund_on_cancellation(
            PRO, "2021-05-01", "2021-05-31", "2021-05-16", "full"
        )
        self.assertEqual(Money.from_major("99.00"), refund)

    def test_unknown_policy(self):
        self.assertField(
            "policy",
            mod.refund_on_cancellation,
            PRO,
            "2021-05-01",
            "2021-05-31",
            "2021-05-16",
            "sometimes",
        )
