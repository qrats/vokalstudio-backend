import datetime

from src.domain.timeline import instant as mod
from tests.support import DomainTestCase

MOMENT = mod.Instant.parse("2021-05-12T17:44:35Z")


class ConstructionTests(DomainTestCase):
    def test_millis_are_kept(self):
        self.assertEqual(1500, mod.Instant(1500).millis)

    def test_negative_millis_are_allowed(self):
        self.assertEqual(-1000, mod.Instant(-1000).millis)

    def test_float_is_rejected(self):
        self.assertField("millis", mod.Instant, 1.5)

    def test_from_seconds(self):
        self.assertEqual(1500, mod.Instant.from_seconds(1.5).millis)

    def test_from_seconds_rounds(self):
        self.assertEqual(1501, mod.Instant.from_seconds(1.5006).millis)

    def test_from_datetime_naive_is_utc(self):
        naive = datetime.datetime(1970, 1, 1, 0, 0, 1)
        self.assertEqual(1000, mod.Instant.from_datetime(naive).millis)

    def test_from_datetime_with_offset(self):
        aware = datetime.datetime(
            1970, 1, 1, 1, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=1))
        )
        self.assertEqual(0, mod.Instant.from_datetime(aware).millis)

    def test_from_datetime_rejects_other_types(self):
        self.assertField("value", mod.Instant.from_datetime, "2021-01-01")


class ParseTests(DomainTestCase):
    def test_trailing_z(self):
        self.assertEqual(0, mod.Instant.parse("1970-01-01T00:00:00Z").millis)

    def test_lowercase_z(self):
        self.assertEqual(0, mod.Instant.parse("1970-01-01T00:00:00z").millis)

    def test_explicit_offset(self):
        self.assertEqual(0, mod.Instant.parse("1970-01-01T01:00:00+01:00").millis)

    def test_milliseconds(self):
        self.assertEqual(250, mod.Instant.parse("1970-01-01T00:00:00.250Z").millis)

    def test_garbage_is_rejected(self):
        self.assertField("instant", mod.Instant.parse, "yesterday")

    def test_field_name_is_used(self):
        self.assertField("published_at", mod.Instant.parse, "x", "published_at")

    def test_empty_is_rejected(self):
        self.assertField("instant", mod.Instant.parse, "")


class FormattingTests(DomainTestCase):
    def test_iso_without_millis(self):
        self.assertEqual("2021-05-12T17:44:35Z", MOMENT.to_iso())

    def test_iso_with_millis(self):
        self.assertEqual(
            "2021-05-12T17:44:35.500Z", MOMENT.plus_millis(500).to_iso()
        )

    def test_round_trip(self):
        self.assertEqual(MOMENT, mod.Instant.parse(MOMENT.to_iso()))

    def test_to_date(self):
        self.assertEqual("2021-05-12", MOMENT.to_date())

    def test_to_dict(self):
        payload = MOMENT.to_dict()
        self.assertEqual(MOMENT.millis, payload["millis"])
        self.assertEqual(MOMENT.to_iso(), payload["iso"])

    def test_repr(self):
        self.assertIn("2021-05-12", repr(MOMENT))


class ArithmeticTests(DomainTestCase):
    def test_plus_millis(self):
        self.assertEqual(1, mod.Instant(0).plus_millis(1).millis)

    def test_plus_seconds(self):
        self.assertEqual(2000, mod.Instant(0).plus_seconds(2).millis)

    def test_plus_minutes(self):
        self.assertEqual(60000, mod.Instant(0).plus_minutes(1).millis)

    def test_plus_hours(self):
        self.assertEqual(3600000, mod.Instant(0).plus_hours(1).millis)

    def test_plus_days(self):
        self.assertEqual(86400000, mod.Instant(0).plus_days(1).millis)

    def test_negative_offsets(self):
        self.assertEqual(-3600000, mod.Instant(0).plus_hours(-1).millis)

    def test_difference(self):
        self.assertEqual(1000, mod.Instant(2000).difference_millis(mod.Instant(1000)))

    def test_difference_accepts_millis(self):
        self.assertEqual(1000, mod.Instant(2000).difference_millis(1000))

    def test_instants_are_immutable_under_arithmetic(self):
        base = mod.Instant(10)
        base.plus_millis(5)
        self.assertEqual(10, base.millis)


class ComparisonTests(DomainTestCase):
    def test_is_before(self):
        self.assertTrue(mod.Instant(1).is_before(mod.Instant(2)))

    def test_is_after(self):
        self.assertTrue(mod.Instant(2).is_after(mod.Instant(1)))

    def test_ordering_operators(self):
        self.assertLess(mod.Instant(1), mod.Instant(2))
        self.assertLessEqual(mod.Instant(2), mod.Instant(2))
        self.assertGreater(mod.Instant(3), mod.Instant(2))
        self.assertGreaterEqual(mod.Instant(2), mod.Instant(2))

    def test_equality(self):
        self.assertEqual(mod.Instant(5), mod.Instant(5))

    def test_not_equal_to_int(self):
        self.assertNotEqual(mod.Instant(5), 5)

    def test_hashable(self):
        self.assertEqual(1, len({mod.Instant(5), mod.Instant(5)}))

    def test_sorting(self):
        ordered = sorted([mod.Instant(3), mod.Instant(1)])
        self.assertEqual(mod.Instant(1), ordered[0])


class FloorTests(DomainTestCase):
    def test_floor_to_day(self):
        self.assertEqual("2021-05-12T00:00:00Z", MOMENT.floor_to_day().to_iso())

    def test_floor_to_hour(self):
        self.assertEqual("2021-05-12T17:00:00Z", MOMENT.floor_to_hour().to_iso())

    def test_floor_is_idempotent(self):
        once = MOMENT.floor_to_day()
        self.assertEqual(once, once.floor_to_day())


class CoerceTests(DomainTestCase):
    def test_instant_passes_through(self):
        self.assertIs(MOMENT, mod.coerce_instant(MOMENT))

    def test_string(self):
        self.assertEqual(MOMENT, mod.coerce_instant("2021-05-12T17:44:35Z"))

    def test_int(self):
        self.assertEqual(mod.Instant(5), mod.coerce_instant(5))

    def test_datetime(self):
        self.assertEqual(mod.Instant(0), mod.coerce_instant(mod.EPOCH))

    def test_bool_is_rejected(self):
        self.assertField("instant", mod.coerce_instant, True)

    def test_none_is_rejected(self):
        self.assertField("created_at", mod.coerce_instant, None, "created_at")


class EarliestLatestTests(DomainTestCase):
    def test_earliest(self):
        self.assertEqual(mod.Instant(1), mod.earliest([mod.Instant(3), 1]))

    def test_latest(self):
        self.assertEqual(mod.Instant(3), mod.latest([mod.Instant(3), 1]))

    def test_empty_returns_default(self):
        self.assertIsNone(mod.earliest([]))
        self.assertEqual("x", mod.latest([], "x"))
