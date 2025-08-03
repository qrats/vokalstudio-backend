from src.domain.catalog.entitlement import Entitlement
from src.domain.episodes.episode import Episode
from src.domain.episodes import publishing as mod
from src.domain.media.asset import Asset
from tests.support import DomainTestCase

ASSET = Asset("u-1", "episode-12.mp3", 5_000_000, duration="30:00")
WHEN = "2021-05-01T10:00:00Z"


def episode(**overrides):
    payload = {
        "owner_id": "u-1",
        "series_slug": "vokal-weekly",
        "title": "Episode 12",
        "asset": ASSET,
        "notes": "A good conversation.",
        "number": 12,
    }
    payload.update(overrides)
    return Episode(**payload)


def published(title="Episode 1", at=WHEN):
    return episode(title=title).mark_ready().publish(at)


class StepTests(DomainTestCase):
    def test_kind_and_target(self):
        step = mod.PublicationStep(mod.UPLOAD, "podbean")
        self.assertEqual(mod.UPLOAD, step.kind)
        self.assertEqual("podbean", step.target)

    def test_unknown_kind(self):
        self.assertField("kind", mod.PublicationStep, "tweet")

    def test_detail_defaults_to_empty(self):
        self.assertEqual({}, mod.PublicationStep(mod.FEED).detail)

    def test_detail_is_copied(self):
        given = {"a": 1}
        step = mod.PublicationStep(mod.FEED, None, given)
        given["a"] = 2
        self.assertEqual(1, step.detail["a"])

    def test_to_dict(self):
        payload = mod.PublicationStep(mod.UPLOAD, "podbean", {"a": 1}).to_dict()
        self.assertEqual("upload", payload["kind"])
        self.assertEqual({"a": 1}, payload["detail"])

    def test_equality(self):
        self.assertEqual(mod.PublicationStep(mod.FEED), mod.PublicationStep(mod.FEED))

    def test_hashable(self):
        self.assertEqual(
            1, len({mod.PublicationStep(mod.FEED), mod.PublicationStep(mod.FEED)})
        )

    def test_repr(self):
        self.assertIn("upload", repr(mod.PublicationStep(mod.UPLOAD, "podbean")))


class PlanTests(DomainTestCase):
    def test_feed_and_notify_are_always_there(self):
        steps = mod.plan_publication(episode())
        self.assertEqual((mod.FEED, mod.NOTIFY), tuple(step.kind for step in steps))

    def test_render_comes_first(self):
        steps = mod.plan_publication(episode(), needs_render=True)
        self.assertEqual(mod.RENDER, steps[0].kind)

    def test_one_upload_per_destination(self):
        steps = mod.plan_publication(episode(), ["podbean", "spotify"])
        self.assertEqual(2, len(mod.steps_by_kind(steps, mod.UPLOAD)))

    def test_upload_carries_the_reference(self):
        steps = mod.plan_publication(episode(), ["podbean"])
        upload = mod.steps_by_kind(steps, mod.UPLOAD)[0]
        self.assertEqual(episode().reference, upload.detail["episode"])

    def test_feed_targets_the_series(self):
        steps = mod.plan_publication(episode())
        self.assertEqual("vokal-weekly", mod.steps_by_kind(steps, mod.FEED)[0].target)

    def test_no_media(self):
        self.assertField("episode", mod.plan_publication, episode(asset=None))

    def test_incomplete_episode(self):
        error = self.assertRaisesCode(
            "validation_failed", mod.plan_publication, episode(number=None)
        )
        self.assertEqual(["number"], error.details["missing"])


class AllowanceTests(DomainTestCase):
    def setUp(self):
        self.rights = Entitlement({"episodes.monthly": 2})

    def test_within_the_allowance(self):
        self.assertEqual(1, mod.check_monthly_allowance(self.rights, [published()], 2021, 5))

    def test_at_the_allowance(self):
        history = [published("A"), published("B")]
        self.assertRaisesCode(
            "quota_exceeded", mod.check_monthly_allowance, self.rights, history, 2021, 5
        )

    def test_another_month_does_not_count(self):
        history = [published("A"), published("B")]
        self.assertEqual(0, mod.check_monthly_allowance(self.rights, history, 2021, 6))

    def test_unlimited_plan(self):
        rights = Entitlement({"episodes.monthly": -1})
        history = [published("A"), published("B"), published("C")]
        self.assertEqual(3, mod.check_monthly_allowance(rights, history, 2021, 5))

    def test_remaining(self):
        self.assertEqual(1, mod.remaining_this_month(self.rights, [published()], 2021, 5))

    def test_remaining_when_used_up(self):
        history = [published("A"), published("B")]
        self.assertEqual(0, mod.remaining_this_month(self.rights, history, 2021, 5))

    def test_remaining_is_none_when_unlimited(self):
        rights = Entitlement({"episodes.monthly": -1})
        self.assertIsNone(mod.remaining_this_month(rights, [], 2021, 5))

    def test_would_exceed(self):
        history = [published("A"), published("B")]
        self.assertTrue(mod.would_exceed(self.rights, history, 2021, 5))

    def test_would_not_exceed(self):
        self.assertFalse(mod.would_exceed(self.rights, [published()], 2021, 5))


class PublishTests(DomainTestCase):
    def test_publishes_and_returns_the_steps(self):
        ready = episode().mark_ready()
        result, steps = mod.publish(ready, WHEN)
        self.assertEqual("published", result.state)
        self.assertEqual(2, len(steps))

    def test_records_the_date(self):
        result, _ = mod.publish(episode().mark_ready(), WHEN)
        self.assertEqual(WHEN, result.published_at.to_iso())

    def test_destinations_become_uploads(self):
        _, steps = mod.publish(episode().mark_ready(), WHEN, destinations=["podbean"])
        self.assertEqual(1, len(mod.steps_by_kind(steps, mod.UPLOAD)))

    def test_allowance_is_enforced(self):
        rights = Entitlement({"episodes.monthly": 1})
        self.assertRaisesCode(
            "quota_exceeded",
            mod.publish,
            episode(title="Episode 20").mark_ready(),
            WHEN,
            rights,
            [published()],
        )

    def test_allowance_is_month_scoped(self):
        rights = Entitlement({"episodes.monthly": 1})
        result, _ = mod.publish(
            episode(title="Episode 20").mark_ready(),
            "2021-06-01T00:00:00Z",
            rights,
            [published()],
        )
        self.assertEqual("published", result.state)

    def test_no_entitlement_skips_the_check(self):
        result, _ = mod.publish(episode().mark_ready(), WHEN, episodes=[published()])
        self.assertEqual("published", result.state)

    def test_a_draft_cannot_be_published(self):
        self.assertRaisesCode("invalid_state", mod.publish, episode(), WHEN)


class OrderTests(DomainTestCase):
    def test_sorts_into_run_order(self):
        steps = [
            mod.PublicationStep(mod.NOTIFY),
            mod.PublicationStep(mod.RENDER),
            mod.PublicationStep(mod.UPLOAD, "podbean"),
        ]
        ordered = mod.publication_order(steps)
        self.assertEqual(
            (mod.RENDER, mod.UPLOAD, mod.NOTIFY), tuple(step.kind for step in ordered)
        )

    def test_stable_within_a_kind(self):
        steps = [
            mod.PublicationStep(mod.UPLOAD, "b"),
            mod.PublicationStep(mod.UPLOAD, "a"),
        ]
        self.assertEqual("b", mod.publication_order(steps)[0].target)

    def test_empty(self):
        self.assertEqual((), mod.publication_order([]))

    def test_steps_by_kind_with_no_match(self):
        self.assertEqual((), mod.steps_by_kind([mod.PublicationStep(mod.FEED)], mod.UPLOAD))
