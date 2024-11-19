from src.domain.money.amount import Money
from src.domain.servers import instance as mod
from tests.support import DomainTestCase


class NormalizeTests(DomainTestCase):
    def test_lowercases(self):
        self.assertEqual("t3.medium", mod.normalize_type("T3.MEDIUM"))

    def test_unknown(self):
        error = self.assertRaisesCode("validation_failed", mod.normalize_type, "m5.huge")
        self.assertIn("t3.small", error.details["supported"])

    def test_empty(self):
        self.assertField("instance_type", mod.normalize_type, "")

    def test_default_type_is_known(self):
        self.assertIn(mod.DEFAULT_TYPE, mod.TYPES)

    def test_supported_types_are_sorted(self):
        types = mod.supported_types()
        self.assertEqual(tuple(sorted(types)), types)


class CapacityTests(DomainTestCase):
    def test_capacity(self):
        self.assertEqual(4, mod.capacity("t3.medium"))

    def test_throughput(self):
        self.assertEqual(16000, mod.throughput_kbps("t3.medium"))

    def test_bigger_types_carry_more(self):
        self.assertGreater(mod.capacity("c5.xlarge"), mod.capacity("c5.large"))

    def test_every_entry_is_complete(self):
        for name, record in mod.TYPES.items():
            self.assertGreater(record["targets"], 0, name)
            self.assertGreater(record["kbps"], 0, name)
            self.assertGreater(record["cents_per_hour"], 0, name)


class CostTests(DomainTestCase):
    def test_hourly_cost(self):
        self.assertEqual(Money(5), mod.hourly_cost("t3.medium"))

    def test_currency(self):
        self.assertEqual("EUR", mod.hourly_cost("t3.medium", "EUR").currency)

    def test_cost_for_hours(self):
        self.assertEqual(Money(120), mod.cost_for_hours("t3.medium", 24))

    def test_zero_hours(self):
        self.assertTrue(mod.cost_for_hours("t3.medium", 0).is_zero())

    def test_negative_hours(self):
        self.assertField("hours", mod.cost_for_hours, "t3.medium", -1)

    def test_bigger_types_cost_more(self):
        self.assertGreater(
            mod.hourly_cost("c5.xlarge").units, mod.hourly_cost("c5.large").units
        )


class SmallestForTests(DomainTestCase):
    def test_one_target(self):
        self.assertEqual("t3.small", mod.smallest_for(1))

    def test_three_targets(self):
        self.assertEqual("t3.medium", mod.smallest_for(3))

    def test_eight_targets(self):
        self.assertEqual("c5.large", mod.smallest_for(8))

    def test_bitrate_forces_a_bigger_type(self):
        self.assertEqual("t3.medium", mod.smallest_for(2, 6000))

    def test_bitrate_forces_the_compute_type(self):
        self.assertEqual("c5.large", mod.smallest_for(2, 9000))

    def test_bitrate_within_the_small_type(self):
        self.assertEqual("t3.small", mod.smallest_for(2, 4000))

    def test_nothing_is_large_enough(self):
        self.assertIsNone(mod.smallest_for(100))

    def test_bitrate_beyond_every_type(self):
        self.assertIsNone(mod.smallest_for(2, 60000))

    def test_zero_targets(self):
        self.assertField("targets", mod.smallest_for, 0)

    def test_zero_bitrate(self):
        self.assertField("kbps", mod.smallest_for, 1, 0)
