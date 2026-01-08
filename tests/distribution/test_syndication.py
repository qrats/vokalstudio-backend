from src.domain.catalog.entitlement import Entitlement
from src.domain.distribution.credential import Credential
from src.domain.distribution import syndication as mod
from src.domain.episodes.episode import Episode
from src.domain.media.asset import Asset
from tests.support import DomainTestCase

NOW = "2021-05-01T10:00:00Z"
ASSET = Asset("u-1", "ep.mp3", 5_000_000, duration="30:00")


def episode(**overrides):
    payload = {
        "owner_id": "u-1",
        "series_slug": "vokal-weekly",
        "title": "Episode 12",
        "asset": ASSET,
        "notes": "Some notes.",
        "number": 12,
    }
    payload.update(overrides)
    return Episode(**payload)


def credential(destination="podbean", scopes=("episode_publish",), issued_at=NOW):
    return Credential("u-1", destination, "token-abcdefgh", issued_at, scopes=scopes)


class EvaluateTests(DomainTestCase):
    def test_eligible_without_oauth(self):
        self.assertEqual(mod.ELIGIBLE, mod.evaluate("apple", episode()))

    def test_missing_credential(self):
        self.assertEqual(mod.NO_CREDENTIAL, mod.evaluate("podbean", episode()))

    def test_eligible_with_a_credential(self):
        found = mod.evaluate("podbean", episode(), [credential()])
        self.assertEqual(mod.ELIGIBLE, found)

    def test_missing_scopes(self):
        found = mod.evaluate("podbean", episode(), [credential(scopes=())])
        self.assertEqual(mod.MISSING_SCOPES, found)

    def test_expired_credential(self):
        found = mod.evaluate("podbean", episode(), [credential()], "2021-05-01T12:00:00Z")
        self.assertEqual(mod.CREDENTIAL_EXPIRED, found)

    def test_rejected_media(self):
        one = episode(asset=Asset("u-1", "ep.mp4", 5_000_000, duration="30:00"))
        self.assertEqual(mod.REJECTED, mod.evaluate("spotify", one))

    def test_missing_media(self):
        self.assertEqual(mod.REJECTED, mod.evaluate("apple", episode(asset=None)))

    def test_missing_artwork(self):
        self.assertEqual(
            mod.REJECTED, mod.evaluate("apple", episode(), has_artwork=False)
        )

    def test_unknown_destination(self):
        self.assertField("destination", mod.evaluate, "soundcloud", episode())


class PlanTests(DomainTestCase):
    def test_each_destination_is_decided(self):
        decisions = mod.plan(["apple", "podbean"], episode())
        self.assertEqual(2, len(decisions))

    def test_names_are_normalised(self):
        decisions = mod.plan(["Apple"], episode())
        self.assertEqual("apple", decisions[0][0])

    def test_eligible_destinations(self):
        decisions = mod.plan(["apple", "podbean"], episode())
        self.assertEqual(("apple",), mod.eligible_destinations(decisions))

    def test_blocked(self):
        decisions = mod.plan(["apple", "podbean"], episode())
        self.assertEqual((("podbean", mod.NO_CREDENTIAL),), mod.blocked(decisions))

    def test_plan_limit(self):
        rights = Entitlement({"distribution.destinations": 1})
        decisions = mod.plan(
            ["apple", "vokal"], episode(), entitlement=rights
        )
        self.assertEqual(("apple",), mod.eligible_destinations(decisions))
        self.assertEqual(mod.NOT_ALLOWED, decisions[1][1])

    def test_unlimited_destinations(self):
        rights = Entitlement({"distribution.destinations": -1})
        decisions = mod.plan(["apple", "vokal"], episode(), entitlement=rights)
        self.assertEqual(2, len(mod.eligible_destinations(decisions)))

    def test_blocked_destinations_do_not_consume_the_limit(self):
        rights = Entitlement({"distribution.destinations": 1})
        decisions = mod.plan(
            ["podbean", "apple"], episode(), entitlement=rights
        )
        self.assertEqual(("apple",), mod.eligible_destinations(decisions))

    def test_no_destinations(self):
        self.assertEqual((), mod.plan([], episode()))

    def test_a_string_is_not_a_destination_list(self):
        self.assertField("destinations", mod.plan, "apple", episode())


class JobTests(DomainTestCase):
    def test_one_job_per_eligible_destination(self):
        decisions = mod.plan(["apple", "vokal", "podbean"], episode())
        jobs = mod.build_jobs(episode(), decisions)
        self.assertEqual(2, len(jobs))

    def test_jobs_carry_the_episode(self):
        decisions = mod.plan(["apple"], episode())
        jobs = mod.build_jobs(episode(), decisions)
        self.assertEqual(episode().reference, jobs[0].episode_reference)

    def test_jobs_start_pending(self):
        decisions = mod.plan(["apple"], episode())
        self.assertEqual("pending", mod.build_jobs(episode(), decisions)[0].state)

    def test_no_eligible_destinations(self):
        decisions = mod.plan(["podbean"], episode())
        self.assertEqual((), mod.build_jobs(episode(), decisions))


class ExplainTests(DomainTestCase):
    def test_no_media(self):
        self.assertEqual(("asset",), mod.explain(episode(asset=None), "apple"))

    def test_container(self):
        one = episode(asset=Asset("u-1", "ep.mp4", 5_000_000, duration="30:00"))
        self.assertEqual(("container",), mod.explain(one, "spotify"))

    def test_artwork(self):
        self.assertEqual(("artwork",), mod.explain(episode(), "apple", False))

    def test_nothing_wrong(self):
        self.assertEqual((), mod.explain(episode(), "apple"))
