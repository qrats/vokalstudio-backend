from src.domain.servers import region as mod
from tests.support import DomainTestCase


class NormalizeTests(DomainTestCase):
    def test_lowercases(self):
        self.assertEqual("eu-west-1", mod.normalize_region("EU-WEST-1"))

    def test_unknown(self):
        error = self.assertRaisesCode("validation_failed", mod.normalize_region, "mars-1")
        self.assertIn("eu-west-1", error.details["supported"])

    def test_empty(self):
        self.assertField("region", mod.normalize_region, "")

    def test_field_name(self):
        self.assertField("origin", mod.normalize_region, "mars-1", "origin")

    def test_label(self):
        self.assertEqual("Ireland", mod.label_of("eu-west-1"))

    def test_continent(self):
        self.assertEqual("eu", mod.continent_of("eu-central-1"))

    def test_supported_regions_are_sorted(self):
        regions = mod.supported_regions()
        self.assertEqual(tuple(sorted(regions)), regions)

    def test_every_entry_is_complete(self):
        for name, record in mod.REGIONS.items():
            self.assertTrue(record["label"], name)
            self.assertEqual(2, len(record["continent"]), name)


class LatencyTests(DomainTestCase):
    def test_same_region(self):
        self.assertEqual(mod.SAME_REGION_MILLIS, mod.latency_millis("eu-west-1", "eu-west-1"))

    def test_same_continent(self):
        self.assertEqual(
            mod.SAME_CONTINENT_MILLIS, mod.latency_millis("eu-west-1", "eu-central-1")
        )

    def test_known_neighbour_pair(self):
        self.assertEqual(90, mod.latency_millis("us-east-1", "eu-west-1"))

    def test_neighbour_pair_is_symmetric(self):
        self.assertEqual(
            mod.latency_millis("eu-west-1", "us-east-1"),
            mod.latency_millis("us-east-1", "eu-west-1"),
        )

    def test_far_apart(self):
        self.assertEqual(
            mod.CROSS_CONTINENT_MILLIS, mod.latency_millis("us-east-1", "ap-southeast-2")
        )

    def test_unknown_origin(self):
        self.assertField("origin", mod.latency_millis, "mars-1", "eu-west-1")

    def test_unknown_destination(self):
        self.assertField("destination", mod.latency_millis, "eu-west-1", "mars-1")


class NearestTests(DomainTestCase):
    def test_picks_the_closest(self):
        found = mod.nearest("eu-west-1", ["us-east-1", "eu-central-1"])
        self.assertEqual("eu-central-1", found)

    def test_exact_match_wins(self):
        found = mod.nearest("eu-west-1", ["eu-central-1", "eu-west-1"])
        self.assertEqual("eu-west-1", found)

    def test_ties_break_by_name(self):
        found = mod.nearest("us-east-1", ["ap-southeast-2", "sa-east-1"])
        self.assertEqual("sa-east-1", found)

    def test_empty(self):
        self.assertIsNone(mod.nearest("eu-west-1", []))

    def test_unknown_candidate(self):
        self.assertField("candidates", mod.nearest, "eu-west-1", ["mars-1"])


class WithinTests(DomainTestCase):
    def test_tight_budget(self):
        self.assertEqual(("eu-west-1",), mod.within("eu-west-1", 10))

    def test_continent_budget(self):
        found = mod.within("eu-west-1", 40)
        self.assertEqual(("eu-west-1", "eu-central-1"), found)

    def test_wide_budget_reaches_everything(self):
        self.assertEqual(len(mod.REGIONS), len(mod.within("eu-west-1", 200)))

    def test_nearest_first(self):
        found = mod.within("us-east-1", 100)
        self.assertEqual("us-east-1", found[0])

    def test_explicit_candidates(self):
        found = mod.within("eu-west-1", 40, ["eu-central-1", "us-east-1"])
        self.assertEqual(("eu-central-1",), found)

    def test_nothing_in_range(self):
        self.assertEqual((), mod.within("eu-west-1", 1, ["us-east-1"]))
