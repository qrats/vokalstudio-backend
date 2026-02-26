from src.domain.catalog.entitlement import Entitlement
from src.domain.distribution.credential import Credential
from src.domain.distribution import syndication as mod
from src.domain.episodes.episode import Episode
from src.domain.media.asset import Asset
from tests.support import DomainTestCase

WHEN = "2021-05-01T10:00:00Z"
AUDIO = Asset("u-1", "episode-12.mp3", 5_000_000, duration="30:00")
VIDEO = Asset("u-1", "episode-12.mp4", 50_000_000, duration="30:00")


def episode(asset=AUDIO):
    return Episode("u-1", "vokal-weekly", "Episode 12", asset, "Notes here.", number=12)


def credential(destination="podbean", scopes=("episode_publish",), **overrides):
    payload = {
        "user_id": "u-1",
        "destination": destination,
        "token": "token-abcdefgh",
        "issued_at": WHEN,
        "scopes": scopes,
    }
    payload.update(overrides)
    return Credential(**payload)


class EvaluateTests(DomainTestCase):
    def test_destination_without_oauth(self):
        self.assertEqual(mod.ELIGIBLE, mod.evaluate("apple", episode()))

    def test_missing_credential(self):
        self.assertEqual(mod.NO_CREDENTIAL, mod.evaluate("podbean", episode()))

    def test_with_a_credential(self):
        self.assertEqual(
            mod.ELIGIBLE, mod.evaluate("podbean", episode(), [credential()])
        )

    def test_missing_scopes(self):
        creds = [credential(scopes=())]
        self.assertEqual(
            mod.MISSING_SCOPES, mod.evaluate("podbean", episode(), creds)
        )

    def test_expired_credential(self):
        creds = [credential()]
        self.assertEqual(
            mod.CREDENTIAL_EXPIRED,
            mod.evaluate("podbean", episode(), creds, "2021-06-01T00:00:00Z"),
        )

    def test_credential_still_valid(self):
        creds = [credential()]
        self.assertEqual(
            mod.ELIGIBLE,
            mod.evaluate("podbean", episode(), creds, "2021-05-01T10:10:00Z"),
        )

    def test_container_is_refused(self):
        self.assertEqual(mod.REJECTED, mod.evaluate("apple", episode(VIDEO)))

    def test_video_reaches_youtube(self):
        creds = [credential("youtube", ("youtube.upload",))]
        self.assertEqual(mod.ELIGIBLE, mod.evaluate("youtube", episode(VIDEO), creds))

    def test_missing_artwork(self):
        self.assertEqual(
            mod.REJECTED, mod.evaluate("apple", episode(), has_artwork=False)
        )

    def test_artwork_is_not_needed_everywhere(self):
        self.assertEqual(
            mod.ELIGIBLE, mod.evaluate("vokal", episode(), has_artwork=False)
        )

    def test_no_media(self):
        bare = Episode("u-1", "vokal-weekly", "Episode 12", None, "Notes.", number=1)
        self.assertEqual(mod.REJECTED, mod.evaluate("apple", bare))

    def test_unknown_destination(self):
        self.assertField("destination", mod.evaluate, "anchor", episode())


class PlanTests(DomainTestCase):
    def test_one_decision_per_destination(self):
        decisions = mod.plan(["apple", "vokal"], episode())
        self.assertEqual(2, len(decisions))

    def test_eligible_destinations(self):
        decisions = mod.plan(["apple", "podbean"], episode())
        self.assertEqual(("apple",), mod.eligible_destinations(decisions))

    def test_blocked_carries_the_reason(self):
        decisions = mod.plan(["podbean"], episode())
        self.assertEqual((("podbean", mod.NO_CREDENTIAL),), mod.blocked(decisions))

    def test_plan_limit(self):
        rights = Entitlement({"distribution.destinations": 1})
        decisions = mod.plan(["apple", "vokal"], episode(), entitlement=rights)
        self.assertEqual(("apple",), mod.eligible_destinations(decisions))
        self.assertEqual(mod.NOT_ALLOWED, decisions[1][1])

    def test_unlimited_plan(self):
        rights = Entitlement({"distribution.destinations": -1})
        decisions = mod.plan(["apple", "vokal"], episode(), entitlement=rights)
        self.assertEqual(2, len(mod.eligible_destinations(decisions)))

    def test_rejected_destinations_do_not_use_the_limit(self):
        rights = Entitlement({"distribution.destinations": 1})
        decisions = mod.plan(["podbean", "vokal"], episode(), entitlement=rights)
        self.assertEqual(("vokal",), mod.eligible_destinations(decisions))

    def test_names_are_normalised(self):
        decisions = mod.plan(["Apple"], episode())
        self.assertEqual("apple", decisions[0][0])

    def test_empty_list(self):
        self.assertEqual((), mod.plan([], episode()))

    def test_a_string_is_not_a_list(self):
        self.assertField("destinations", mod.plan, "apple", episode())


class JobTests(DomainTestCase):
    def test_one_job_per_eligible_destination(self):
        decisions = mod.plan(["apple", "podbean", "vokal"], episode())
        jobs = mod.build_jobs(episode(), decisions)
        self.assertEqual(2, len(jobs))

    def test_jobs_carry_the_episode(self):
        decisions = mod.plan(["apple"], episode())
        self.assertEqual(episode().reference, mod.build_jobs(episode(), decisions)[0].episode_reference)

    def test_jobs_start_pending(self):
        decisions = mod.plan(["apple"], episode())
        self.assertEqual("pending", mod.build_jobs(episode(), decisions)[0].state)

    def test_no_eligible_destinations(self):
        decisions = mod.plan(["podbean"], episode())
        self.assertEqual((), mod.build_jobs(episode(), decisions))


class ExplainTests(DomainTestCase):
    def test_container_problem(self):
        self.assertEqual(("container",), mod.explain(episode(VIDEO), "apple"))

    def test_artwork_problem(self):
        self.assertEqual(("artwork",), mod.explain(episode(), "apple", has_artwork=False))

    def test_nothing_wrong(self):
        self.assertEqual((), mod.explain(episode(), "apple"))

    def test_no_media(self):
        bare = Episode("u-1", "vokal-weekly", "Episode 12", None, "Notes.", number=1)
        self.assertEqual(("asset",), mod.explain(bare, "apple"))
