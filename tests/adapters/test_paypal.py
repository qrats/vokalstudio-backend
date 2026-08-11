from src.domain.adapters import paypal as mod
from src.domain.money.amount import Money
from tests.support import DomainTestCase


class DigTests(DomainTestCase):
    def test_finds_a_nested_value(self):
        self.assertEqual(1, mod.dig({"a": {"b": 1}}, "a", "b"))

    def test_missing_key(self):
        self.assertIsNone(mod.dig({"a": {}}, "a", "b"))

    def test_default(self):
        self.assertEqual("x", mod.dig({}, "a", default="x"))

    def test_stops_at_a_non_mapping(self):
        self.assertIsNone(mod.dig({"a": 1}, "a", "b"))

    def test_no_path_returns_the_payload(self):
        self.assertEqual({"a": 1}, mod.dig({"a": 1}))


class MoneyTests(DomainTestCase):
    def test_value_and_currency(self):
        found = mod.to_money({"value": "99.00", "currency_code": "USD"})
        self.assertEqual(Money(9900), found)

    def test_currency_alias(self):
        found = mod.to_money({"value": "99.00", "currency": "EUR"})
        self.assertEqual("EUR", found.currency)

    def test_default_currency(self):
        self.assertEqual("USD", mod.to_money({"value": "1.00"}).currency)

    def test_missing_value(self):
        self.assertField("amount", mod.to_money, {"currency_code": "USD"})

    def test_not_a_mapping(self):
        self.assertField("amount", mod.to_money, "99.00")

    def test_field_name(self):
        self.assertField("gross", mod.to_money, {}, "gross")


class StatusTests(DomainTestCase):
    def test_maps_to_the_domain(self):
        self.assertEqual("active", mod.subscription_status("ACTIVE"))

    def test_is_case_insensitive(self):
        self.assertEqual("cancelled", mod.subscription_status("cancelled"))

    def test_unknown(self):
        error = self.assertRaisesCode(
            "validation_failed", mod.subscription_status, "PAUSED"
        )
        self.assertIn("ACTIVE", error.details["known"])

    def test_every_mapped_status_is_a_domain_state(self):
        from src.domain.billing.subscription import STATES

        for value in mod.STATUS_MAP.values():
            self.assertIn(value, STATES)


class EventTests(DomainTestCase):
    def test_activation(self):
        self.assertEqual("active", mod.event_state("BILLING.SUBSCRIPTION.ACTIVATED"))

    def test_event_without_a_state(self):
        self.assertIsNone(mod.event_state("PAYMENT.SALE.COMPLETED"))

    def test_unknown_event(self):
        self.assertField("event_type", mod.event_state, "BILLING.PLAN.CREATED")

    def test_is_known_event(self):
        self.assertTrue(mod.is_known_event("billing.subscription.activated"))

    def test_is_not_a_known_event(self):
        self.assertFalse(mod.is_known_event("BILLING.PLAN.CREATED"))

    def test_is_known_event_of_none(self):
        self.assertFalse(mod.is_known_event(None))

    def test_every_mapped_state_is_a_domain_state(self):
        from src.domain.billing.subscription import STATES

        for value in mod.EVENT_MAP.values():
            if value is not None:
                self.assertIn(value, STATES)


class PayloadTests(DomainTestCase):
    def test_subscription_reference_from_the_resource(self):
        self.assertEqual("I-1", mod.subscription_reference({"resource": {"id": "I-1"}}))

    def test_subscription_reference_from_the_root(self):
        self.assertEqual("I-2", mod.subscription_reference({"id": "I-2"}))

    def test_missing_subscription_reference(self):
        self.assertField("resource", mod.subscription_reference, {})

    def test_payment_amount(self):
        payload = {"resource": {"amount": {"value": "99.00", "currency_code": "USD"}}}
        self.assertEqual(Money(9900), mod.payment_amount(payload))

    def test_payment_amount_from_gross(self):
        payload = {"resource": {"gross_amount": {"value": "9.00"}}}
        self.assertEqual(Money(900), mod.payment_amount(payload))

    def test_missing_payment_amount(self):
        self.assertField("resource", mod.payment_amount, {"resource": {}})

    def test_next_billing_date(self):
        payload = {"resource": {"billing_info": {"next_billing_time": "2021-06-01"}}}
        self.assertEqual("2021-06-01", mod.next_billing_date(payload))

    def test_no_next_billing_date(self):
        self.assertIsNone(mod.next_billing_date({"resource": {}}))

    def test_failed_payments_count(self):
        payload = {"resource": {"billing_info": {"failed_payments_count": "2"}}}
        self.assertEqual(2, mod.failed_payments_count(payload))

    def test_failed_payments_default(self):
        self.assertEqual(0, mod.failed_payments_count({}))

    def test_failed_payments_of_garbage(self):
        payload = {"resource": {"billing_info": {"failed_payments_count": "many"}}}
        self.assertEqual(0, mod.failed_payments_count(payload))
