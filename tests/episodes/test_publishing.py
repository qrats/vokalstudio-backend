from src.domain.catalog.entitlement import Entitlement
from src.domain.episodes.episode import Episode
from src.domain.episodes import publishing as mod
from src.domain.media.asset import Asset
from tests.support import DomainTestCase

ASSET = Asset("u-1", "ep.mp3", 5_000_000, duration="30:00")


def episode(title="Episode 12", **overrides):
    payload = {
        "owner_id": "u-1",
        "series_slug": "vokal-weekly",
        "title": title,
        "asset": ASSET,
        "notes": "Some notes.",
        "number": 12,
    }
    payload.update(overrides)
    return Episode(**payload)


def published(title="Episode 11", at="2021-05-01T10:00:00Z"):
    return episode(title).mark_ready().publish(at)


class StepTests(DomainTestCase):
    def test_kind_and_target(self):
        step = mod.PublicationStep(mod.UPLOAD, "podbean")
        self.assertEqual(mod.UPLOAD, step.kind)
        self.assertEqual("podbean", step.target)

    def test_unknown_kind(self):
        self.assertField("kind", mod.PublicationStep, "tweet")

    def test_detail_is_copied(self):
        detail = {"a": 1}
        step = mod.PublicationStep(mod.FEED, "x", detail)
        detail["a"] = 2
        self.assertEqual(1, step.detail["a"])

    def test_to_dict(self):
        payload = mod.PublicationStep(mod.FEED, "x").to_dict()
        self.assertEqual("feed", payload["kind"])
        self.assertEqual({}, payload["detail"])

    def test_equality(self):
        self.assertEqual(
            mod.PublicationStep(mod.FEED, "x"), mod.PublicationStep(mod.FEED, "x")
        )

    def test_hashable(self):
        one = mod.PublicationStep(mod.FEED, "x")
        self.assertEqual(1, len({one, mod.PublicationStep(mod.FEED, "x")}))

    def test_repr(self):
        self.assertIn("feed", repr(mod.PublicationStep(mod.FEED, "x")))


class PlanTests(DomainTestCase):
    def test_minimum_plan(self):
        steps = mod.plan_publication(episode())
        self.assertEqual((mod.FEED, mod.NOTIFY), tuple(step.kind for step in steps))

    def test_render_comes_first(self):
        steps = mod.plan_publication(episode(), needs_render=True)
        self.assertEqual(mod.RENDER, steps[0].kind)

    def test_one_upload_per_destination(self):
        steps = mod.plan_publication(episode(), ["podbean", "spotify"])
        self.assertEqual(2, len(mod.steps_by_kind(steps, mod.UPLOAD)))

    def test_upload_carries_the_episode(self):
        steps = mod.plan_publication(episode(), ["podbean"])
        upload = mod.steps_by_kind(steps, mod.UPLOAD)[0]
        self.assertEqual(episode().reference, upload.detail["episode"])

    def test_feed_targets_the_series(self):
        steps = mod.plan_publication(episode())
        self.assertEqual("vokal-weekly", mod.steps_by_kind(steps, mod.FEED)[0].target)

    def test_missing_media_is_rejected(self):
        self.assertField("episode", mod.plan_publication, episode(asset=None))

    def test_incomplete_episode_is_rejected(self):
        error = self.assertRaisesCode(
            "validation_failed", mod.plan_publication, episode(notes=None)
        )
        self.assertEqual(["show_notes"], error.details["missing"])

    def test_publication_order(self):
        steps = mod.plan_publication(episode(), ["podbean"], needs_render=True)
        shuffled = tuple(reversed(steps))
        self.assertEqual(steps, mod.publication_order(shuffled))


class AllowanceTests(DomainTestCase):
    def setUp(self):
        self.rights = Entitlement({"episodes.monthly": 2})

    def test_under_the_limit(self):
        self.assertEqual(1, mod.check_monthly_allowance(self.rights, [published()], 2021, 5))

    def test_at_the_limit(self):
        history = [published("A"), published("B")]
        self.assertRaisesCode(
            "quota_exceeded", mod.check_monthly_allowance, self.rights, history, 2021, 5
        )

    def test_another_month_does_not_count(self):
        history = [published("A"), published("B")]
        self.assertEqual(0, mod.check_monthly_allowance(self.rights, history, 2021, 6))

    def test_remaining(self):
        self.assertEqual(1, mod.remaining_this_month(self.rights, [published()], 2021, 5))

    def test_remaining_when_unlimited(self):
        rights = Entitlement({"episodes.monthly": -1})
        self.assertIsNone(mod.remaining_this_month(rights, [published()], 2021, 5))

    def test_would_exceed(self):
        history = [published("A"), published("B")]
        self.assertTrue(mod.would_exceed(self.rights, history, 2021, 5))

    def test_would_not_exceed(self):
        self.assertFalse(mod.would_exceed(self.rights, [published()], 2021, 5))


class PublishTests(DomainTestCase):
    def test_returns_the_published_episode(self):
        ready = episode().mark_ready()
        result, steps = mod.publish(ready, "2021-05-03T10:00:00Z")
        self.assertEqual("published", result.state)
        self.assertEqual(2, len(steps))

    def test_destinations_reach_the_steps(self):
        ready = episode().mark_ready()
        _, steps = mod.publish(ready, "2021-05-03T10:00:00Z", destinations=["podbean"])
        self.assertEqual(1, len(mod.steps_by_kind(steps, mod.UPLOAD)))

    def test_allowance_is_checked(self):
        rights = Entitlement({"episodes.monthly": 1})
        ready = episode().mark_ready()
        self.assertRaisesCode(
            "quota_exceeded",
            mod.publish,
            ready,
            "2021-05-03T10:00:00Z",
            rights,
            [published()],
        )

    def test_allowance_in_a_different_month_passes(self):
        rights = Entitlement({"episodes.monthly": 1})
        ready = episode().mark_ready()
        result, _ = mod.publish(ready, "2021-06-03T10:00:00Z", rights, [published()])
        self.assertEqual("published", result.state)

    def test_render_is_requested(self):
        ready = episode().mark_ready()
        _, steps = mod.publish(ready, "2021-05-03T10:00:00Z", needs_render=True)
        self.assertEqual(mod.RENDER, steps[0].kind)

    def test_a_draft_cannot_be_published(self):
        self.assertRaisesCode(
            "invalid_state", mod.publish, episode(), "2021-05-03T10:00:00Z"
        )
