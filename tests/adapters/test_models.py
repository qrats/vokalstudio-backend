from src.domain.adapters import models as mod
from src.domain.media.asset import Asset
from src.domain.money.amount import Money
from tests.support import DomainTestCase


class AssetTests(DomainTestCase):
    def test_from_a_row(self):
        row = {
            "user_id": "u-1",
            "name": "ep.mp3",
            "size_bytes": 5_000_000,
            "duration_millis": 1_800_000,
        }
        asset = mod.to_asset(row)
        self.assertEqual("audio", asset.kind)
        self.assertEqual(1_800_000, asset.duration.millis)

    def test_size_alias(self):
        row = {"user_id": "u-1", "name": "ep.mp3", "size": 99, "duration": 1000}
        self.assertEqual(99, mod.to_asset(row).size_bytes)

    def test_container_override(self):
        row = {
            "user_id": "u-1",
            "name": "ep.dat",
            "container": "mp3",
            "duration": 1000,
        }
        self.assertEqual("mp3", mod.to_asset(row).container)

    def test_format_alias(self):
        row = {"user_id": "u-1", "name": "ep.dat", "format": "wav", "duration": 1000}
        self.assertEqual("wav", mod.to_asset(row).container)

    def test_role(self):
        row = {"user_id": "u-1", "name": "i.mp3", "duration": 1000, "role": "intro"}
        self.assertEqual("intro", mod.to_asset(row).role)

    def test_missing_user(self):
        error = self.assertRaisesCode(
            "validation_failed", mod.to_asset, {"name": "ep.mp3"}
        )
        self.assertEqual(["user_id"], error.details["missing"])

    def test_missing_name(self):
        self.assertRaisesCode("validation_failed", mod.to_asset, {"user_id": "u-1"})


class MediaConfigurationTests(DomainTestCase):
    def test_defaults(self):
        config = mod.to_media_configuration({"user_id": "u-1"})
        self.assertEqual("podcast", config.loudness_profile)
        self.assertTrue(config.normalise)
        self.assertEqual(0, config.fade_millis)

    def test_beds_come_from_the_caller(self):
        intro = Asset("u-1", "i.mp3", 1, duration=1000, role="intro")
        config = mod.to_media_configuration({"user_id": "u-1"}, intro=intro)
        self.assertTrue(config.has_intro())

    def test_fade_alias(self):
        config = mod.to_media_configuration({"user_id": "u-1", "fade": 500})
        self.assertEqual(500, config.fade_millis)

    def test_profile(self):
        row = {"user_id": "u-1", "loudness_profile": "broadcast"}
        self.assertEqual("broadcast", mod.to_media_configuration(row).loudness_profile)

    def test_missing_user(self):
        self.assertRaisesCode("validation_failed", mod.to_media_configuration, {})


class StreamTargetTests(DomainTestCase):
    def test_from_a_row(self):
        row = {
            "user_id": "u-1",
            "platform": "YOUTUBE",
            "stream_key": "abcdefghijklmnopqrst",
        }
        self.assertEqual("youtube", mod.to_stream_target(row).platform)

    def test_rtmp_url_alias(self):
        row = {
            "user_id": "u-1",
            "platform": "custom",
            "stream_key": "abcdefgh",
            "rtmp_url": "rtmp://my.host.test/live",
        }
        self.assertEqual("my.host.test", mod.to_stream_target(row).ingest.host)

    def test_disabled(self):
        row = {
            "user_id": "u-1",
            "platform": "youtube",
            "stream_key": "abcdefghijklmnopqrst",
            "enabled": False,
        }
        self.assertFalse(mod.to_stream_target(row).enabled)

    def test_label(self):
        row = {
            "user_id": "u-1",
            "platform": "youtube",
            "stream_key": "abcdefghijklmnopqrst",
            "label": "Main",
        }
        self.assertEqual("Main", mod.to_stream_target(row).label)

    def test_missing_key(self):
        row = {"user_id": "u-1", "platform": "youtube"}
        error = self.assertRaisesCode("validation_failed", mod.to_stream_target, row)
        self.assertEqual(["stream_key"], error.details["missing"])


class ProductTests(DomainTestCase):
    def test_from_a_row(self):
        product = mod.to_product({"name": "PRO", "description": "Everything."})
        self.assertEqual("pro", product.code)

    def test_reference(self):
        row = {"name": "PRO", "description": "Everything.", "id": "PROD-1"}
        self.assertEqual("paypal:PROD-1", mod.to_product(row).ref.to_string())

    def test_external_id_alias(self):
        row = {"name": "PRO", "description": "Everything.", "external_id": "PROD-2"}
        self.assertEqual("PROD-2", mod.to_product(row).ref.value)

    def test_without_a_reference(self):
        self.assertIsNone(mod.to_product({"name": "PRO", "description": "x"}).ref)

    def test_sandbox(self):
        row = {"name": "PRO", "description": "x", "sandbox": True}
        self.assertTrue(mod.to_product(row).sandbox)

    def test_missing_description(self):
        self.assertRaisesCode("validation_failed", mod.to_product, {"name": "PRO"})


class PlanTests(DomainTestCase):
    def test_flat_price(self):
        plan = mod.to_plan({"name": "PRO", "price": "99.00"})
        self.assertEqual(Money(9900), plan.price)

    def test_currency(self):
        plan = mod.to_plan({"name": "PRO", "price": "99.00", "currency": "EUR"})
        self.assertEqual("EUR", plan.currency)

    def test_billing_cycles(self):
        row = {
            "name": "PRO",
            "billing_cycles": [
                {"price": "0.00", "cycles": 1, "trial": True},
                {"price": "99.00"},
            ],
        }
        plan = mod.to_plan(row)
        self.assertTrue(plan.has_trial())
        self.assertEqual(Money(9900), plan.price)

    def test_cycle_currency_falls_back_to_the_plan(self):
        row = {"name": "PRO", "currency": "GBP", "billing_cycles": [{"price": "9.00"}]}
        self.assertEqual("GBP", mod.to_plan(row).currency)

    def test_product_code_override(self):
        plan = mod.to_plan({"name": "PRO", "price": "1.00"}, product_code="studio")
        self.assertEqual("studio", plan.product_code)

    def test_default_product(self):
        self.assertEqual("vokal", mod.to_plan({"name": "PRO"}).product_code)

    def test_grants(self):
        row = {"name": "PRO", "grants": {"streaming.targets": 4}}
        self.assertEqual(4, mod.to_plan(row).grant_for("streaming.targets"))

    def test_missing_name(self):
        self.assertRaisesCode("validation_failed", mod.to_plan, {})


class SubscriptionTests(DomainTestCase):
    def setUp(self):
        self.row = {
            "id": "I-1",
            "user_id": "u-1",
            "plan_id": "pro",
            "start_time": "2021-01-31",
        }

    def test_from_a_row(self):
        subscription = mod.to_subscription(self.row)
        self.assertEqual("I-1", subscription.reference)
        self.assertEqual(31, subscription.anchor_day)

    def test_default_state(self):
        self.assertEqual("approval_pending", mod.to_subscription(self.row).state)

    def test_state(self):
        row = dict(self.row, status="active")
        self.assertEqual("active", mod.to_subscription(row).state)

    def test_timestamp_is_trimmed_to_a_day(self):
        row = dict(self.row, start_time="2021-01-31T10:00:00")
        self.assertEqual("2021-01-31", mod.to_subscription(row).started_on.isoformat())

    def test_cancellation(self):
        row = dict(
            self.row,
            status="cancelled",
            cancelled_at="2021-03-05",
            period_end="2021-03-31",
        )
        subscription = mod.to_subscription(row)
        self.assertEqual("2021-03-31", subscription.period_end_on.isoformat())

    def test_missing_plan(self):
        error = self.assertRaisesCode(
            "validation_failed",
            mod.to_subscription,
            {"id": "I-1", "user_id": "u-1", "start_time": "2021-01-31"},
        )
        self.assertEqual(["plan_id"], error.details["missing"])


class GrantTests(DomainTestCase):
    def test_from_a_row(self):
        row = {"owner_id": "u-1", "user_id": "u-2", "role": "producer"}
        grant = mod.to_grant(row)
        self.assertEqual("producer", grant.role)
        self.assertTrue(grant.covers_all_episodes)

    def test_episode_scope(self):
        row = {"owner_id": "u-1", "user_id": "u-2", "episode_ids": ["e-1"]}
        self.assertEqual(("e-1",), mod.to_grant(row).episode_ids)

    def test_episodes_alias(self):
        row = {"owner_id": "u-1", "user_id": "u-2", "episodes": ["e-2"]}
        self.assertEqual(("e-2",), mod.to_grant(row).episode_ids)

    def test_dates(self):
        row = {
            "owner_id": "u-1",
            "user_id": "u-2",
            "created_at": "2021-05-01",
            "expires_at": "2021-06-01",
        }
        self.assertEqual("2021-06-01", mod.to_grant(row).expires_on.isoformat())

    def test_missing_owner(self):
        self.assertRaisesCode("validation_failed", mod.to_grant, {"user_id": "u-2"})


class SeriesTests(DomainTestCase):
    def test_from_a_row(self):
        series = mod.to_series({"user_id": "u-1", "title": "Vokal Weekly"})
        self.assertEqual("vokal-weekly", series.slug)

    def test_seasons(self):
        row = {"user_id": "u-1", "title": "Vokal Weekly", "seasons": True}
        self.assertTrue(mod.to_series(row).seasons)

    def test_ordering(self):
        row = {"user_id": "u-1", "title": "Vokal Weekly", "ordering": "serial"}
        self.assertFalse(mod.to_series(row).newest_first())

    def test_missing_title(self):
        self.assertRaisesCode("validation_failed", mod.to_series, {"user_id": "u-1"})


class EpisodeTests(DomainTestCase):
    def test_from_a_row(self):
        row = {"user_id": "u-1", "title": "Episode 12", "series": "weekly"}
        episode = mod.to_episode(row)
        self.assertEqual("weekly", episode.series_slug)
        self.assertEqual("draft", episode.state)

    def test_default_series(self):
        row = {"user_id": "u-1", "title": "Episode 12"}
        self.assertEqual("vokal", mod.to_episode(row).series_slug)

    def test_with_an_asset(self):
        asset = Asset("u-1", "ep.mp3", 1, duration=1000)
        row = {"user_id": "u-1", "title": "Episode 12"}
        self.assertEqual(1000, mod.to_episode(row, asset).duration_millis)

    def test_notes(self):
        row = {"user_id": "u-1", "title": "Episode 12", "description": "Notes."}
        self.assertEqual("Notes.", mod.to_episode(row).notes.body)

    def test_numbering(self):
        row = {"user_id": "u-1", "title": "Episode 12", "number": 12, "season": 2}
        episode = mod.to_episode(row)
        self.assertEqual(12, episode.number)
        self.assertEqual(2, episode.season)

    def test_published_state(self):
        asset = Asset("u-1", "ep.mp3", 1, duration=1000)
        row = {
            "user_id": "u-1",
            "title": "Episode 12",
            "description": "Notes.",
            "number": 1,
            "state": "published",
            "published_at": "2021-05-01T10:00:00Z",
        }
        self.assertTrue(mod.to_episode(row, asset).is_visible())

    def test_missing_title(self):
        self.assertRaisesCode("validation_failed", mod.to_episode, {"user_id": "u-1"})


class PostTests(DomainTestCase):
    def test_from_a_row(self):
        row = {"title": "Hello", "body": "Text.", "user_id": "u-1"}
        self.assertEqual("hello", mod.to_post(row).slug)

    def test_tags(self):
        row = {"title": "Hello", "body": "Text.", "user_id": "u-1", "tags": ["News"]}
        self.assertEqual(("news",), mod.to_post(row).tags)

    def test_categories_alias(self):
        row = {
            "title": "Hello",
            "body": "Text.",
            "user_id": "u-1",
            "categories": ["Studio"],
        }
        self.assertEqual(("studio",), mod.to_post(row).tags)

    def test_published(self):
        row = {
            "title": "Hello",
            "body": "Text.",
            "user_id": "u-1",
            "state": "published",
            "published_at": "2021-05-01T10:00:00Z",
        }
        self.assertTrue(mod.to_post(row).is_visible())

    def test_missing_body(self):
        error = self.assertRaisesCode(
            "validation_failed", mod.to_post, {"title": "Hello", "user_id": "u-1"}
        )
        self.assertEqual(["body"], error.details["missing"])
