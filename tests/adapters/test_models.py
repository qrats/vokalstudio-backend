import datetime

from src.domain.adapters import models as mod
from tests.support import DomainTestCase


class ObjectRow:
    def __init__(self, **values):
        for name, value in values.items():
            setattr(self, name, value)


class AssetTests(DomainTestCase):
    def test_from_a_mapping(self):
        asset = mod.to_asset(
            {"user_id": "u-1", "name": "ep.mp3", "size_bytes": 500, "duration_millis": 1000}
        )
        self.assertEqual("audio", asset.kind)
        self.assertEqual(500, asset.size_bytes)

    def test_from_an_object(self):
        row = ObjectRow(user_id="u-1", name="ep.mp3", size=500, duration=1000)
        self.assertEqual(500, mod.to_asset(row).size_bytes)

    def test_alternate_field_names(self):
        row = {"user_id": "u-1", "name": "ep.wav", "size": 500, "duration": 1000}
        self.assertEqual("wav", mod.to_asset(row).container)

    def test_explicit_container(self):
        row = {"user_id": "u-1", "name": "ep", "size": 500, "duration": 1000, "container": "mp3"}
        self.assertEqual("mp3", mod.to_asset(row).container)

    def test_role(self):
        row = {"user_id": "u-1", "name": "i.mp3", "size": 5, "duration": 10, "role": "intro"}
        self.assertEqual("intro", mod.to_asset(row).role)

    def test_missing_name(self):
        self.assertRaisesCode("validation_failed", mod.to_asset, {"user_id": "u-1"})

    def test_image_needs_no_duration(self):
        row = {"user_id": "u-1", "name": "c.png", "size": 5, "role": "artwork"}
        self.assertIsNone(mod.to_asset(row).duration)


class MediaConfigurationTests(DomainTestCase):
    def test_defaults(self):
        config = mod.to_media_configuration({"user_id": "u-1"})
        self.assertTrue(config.normalise)
        self.assertEqual(0, config.fade_millis)

    def test_fade_alias(self):
        config = mod.to_media_configuration({"user_id": "u-1", "fade": 500})
        self.assertEqual(500, config.fade_millis)

    def test_beds_are_supplied_by_the_caller(self):
        intro = mod.to_asset(
            {"user_id": "u-1", "name": "i.mp3", "size": 5, "duration": 5000, "role": "intro"}
        )
        config = mod.to_media_configuration({"user_id": "u-1"}, intro=intro)
        self.assertTrue(config.has_intro())

    def test_missing_user(self):
        self.assertRaisesCode("validation_failed", mod.to_media_configuration, {})


class StreamTargetTests(DomainTestCase):
    def test_from_a_row(self):
        row = {
            "user_id": "u-1",
            "platform": "youtube",
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

    def test_enabled_default(self):
        row = {"user_id": "u-1", "platform": "youtube", "stream_key": "a" * 20}
        self.assertTrue(mod.to_stream_target(row).enabled)

    def test_disabled(self):
        row = {
            "user_id": "u-1",
            "platform": "youtube",
            "stream_key": "a" * 20,
            "enabled": False,
        }
        self.assertFalse(mod.to_stream_target(row).enabled)

    def test_missing_key(self):
        self.assertRaisesCode(
            "validation_failed", mod.to_stream_target, {"user_id": "u-1", "platform": "youtube"}
        )


class ProductAndPlanTests(DomainTestCase):
    def test_product(self):
        row = {"name": "PRO", "description": "Everything.", "id": "PROD-1"}
        product = mod.to_product(row)
        self.assertEqual("pro", product.code)
        self.assertEqual("paypal", product.ref.provider)

    def test_product_without_an_id(self):
        product = mod.to_product({"name": "PRO", "description": "Everything."})
        self.assertIsNone(product.ref)

    def test_plan_from_a_flat_price(self):
        plan = mod.to_plan({"name": "PRO", "price": "99.00"}, product_code="pro")
        self.assertEqual(9900, plan.price.units)

    def test_plan_from_billing_cycles(self):
        row = {
            "name": "PRO",
            "billing_cycles": [
                {"price": "0.00", "cycles": 1, "trial": True},
                {"price": "99.00"},
            ],
        }
        plan = mod.to_plan(row, product_code="pro")
        self.assertTrue(plan.has_trial())
        self.assertEqual(9900, plan.price.units)

    def test_plan_currency(self):
        plan = mod.to_plan({"name": "PRO", "price": "99.00", "currency": "EUR"}, "pro")
        self.assertEqual("EUR", plan.currency)

    def test_plan_status(self):
        plan = mod.to_plan({"name": "PRO", "price": "9.00", "status": "inactive"}, "pro")
        self.assertFalse(plan.is_active())

    def test_plan_takes_the_product_from_the_row(self):
        plan = mod.to_plan({"name": "PRO", "price": "9.00", "product_id": "studio"})
        self.assertEqual("studio", plan.product_code)


class SubscriptionTests(DomainTestCase):
    def test_from_a_row(self):
        row = {
            "id": "I-1",
            "user_id": "u-1",
            "plan_id": "pro",
            "start_time": "2021-01-31",
        }
        subscription = mod.to_subscription(row)
        self.assertEqual("I-1", subscription.reference)
        self.assertEqual(31, subscription.anchor_day)

    def test_accepts_a_date_object(self):
        row = {
            "id": "I-1",
            "user_id": "u-1",
            "plan_id": "pro",
            "start_time": datetime.date(2021, 1, 31),
        }
        self.assertEqual(31, mod.to_subscription(row).anchor_day)

    def test_accepts_a_datetime(self):
        row = {
            "id": "I-1",
            "user_id": "u-1",
            "plan_id": "pro",
            "start_time": datetime.datetime(2021, 1, 31, 12, 0),
        }
        self.assertEqual(31, mod.to_subscription(row).anchor_day)

    def test_status(self):
        row = {
            "id": "I-1",
            "user_id": "u-1",
            "plan_id": "pro",
            "start_time": "2021-01-31",
            "status": "active",
        }
        self.assertTrue(mod.to_subscription(row).is_billable())

    def test_missing_plan(self):
        self.assertRaisesCode(
            "validation_failed",
            mod.to_subscription,
            {"id": "I-1", "user_id": "u-1", "start_time": "2021-01-31"},
        )


class GrantAndSeriesTests(DomainTestCase):
    def test_grant(self):
        grant = mod.to_grant({"owner_id": "u-1", "user_id": "u-2", "role": "producer"})
        self.assertEqual("producer", grant.role)
        self.assertTrue(grant.covers_all_episodes)

    def test_grant_with_episode_scope(self):
        row = {"owner_id": "u-1", "user_id": "u-2", "episodes": ["e-1"]}
        self.assertEqual(("e-1",), mod.to_grant(row).episode_ids)

    def test_grant_expiry(self):
        row = {
            "owner_id": "u-1",
            "user_id": "u-2",
            "created_at": "2021-05-01",
            "expires_at": "2021-06-01",
        }
        self.assertTrue(mod.to_grant(row).is_expired("2021-06-02"))

    def test_series(self):
        series = mod.to_series({"user_id": "u-1", "title": "Vokal Weekly"})
        self.assertEqual("vokal-weekly", series.slug)

    def test_series_with_seasons(self):
        row = {"user_id": "u-1", "title": "Vokal Weekly", "seasons": True}
        self.assertTrue(mod.to_series(row).seasons)


class EpisodeAndPostTests(DomainTestCase):
    def test_episode(self):
        row = {"user_id": "u-1", "title": "Episode 12", "series": "vokal-weekly"}
        episode = mod.to_episode(row)
        self.assertEqual("episode-12", episode.slug)
        self.assertEqual("vokal-weekly", episode.series_slug)

    def test_episode_series_default(self):
        episode = mod.to_episode({"user_id": "u-1", "title": "Episode 12"})
        self.assertEqual("vokal", episode.series_slug)

    def test_episode_description_becomes_notes(self):
        row = {"user_id": "u-1", "title": "Episode 12", "description": "Notes here."}
        self.assertEqual("Notes here.", mod.to_episode(row).notes.body)

    def test_episode_with_an_asset(self):
        asset = mod.to_asset(
            {"user_id": "u-1", "name": "ep.mp3", "size": 500, "duration": 1000}
        )
        episode = mod.to_episode({"user_id": "u-1", "title": "Episode 12"}, asset)
        self.assertEqual(1000, episode.duration_millis)

    def test_post(self):
        row = {"title": "Going live", "body": "Words.", "user_id": "u-1"}
        self.assertEqual("going-live", mod.to_post(row).slug)

    def test_post_categories_alias(self):
        row = {
            "title": "Going live",
            "body": "Words.",
            "user_id": "u-1",
            "categories": ["Live"],
        }
        self.assertEqual(("live",), mod.to_post(row).tags)

    def test_post_missing_body(self):
        self.assertRaisesCode(
            "validation_failed", mod.to_post, {"title": "T", "user_id": "u-1"}
        )
