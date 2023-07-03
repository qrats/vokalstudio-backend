from src.domain.access import grant as mod
from tests.support import DomainTestCase


def build(**overrides):
    payload = {"owner_id": "owner-1", "subject_id": "guest-1"}
    payload.update(overrides)
    return mod.Grant(**payload)


class ConstructionTests(DomainTestCase):
    def test_defaults_to_guest(self):
        self.assertEqual("guest", build().role)

    def test_covers_all_episodes_by_default(self):
        self.assertTrue(build().covers_all_episodes)

    def test_explicit_episode_list(self):
        self.assertEqual(("e-1", "e-2"), build(episode_ids=["e-1", "e-2"]).episode_ids)

    def test_episode_list_deduplicates(self):
        self.assertEqual(("e-1",), build(episode_ids=["e-1", "e-1"]).episode_ids)

    def test_wildcard_string(self):
        self.assertTrue(build(episode_ids="*").covers_all_episodes)

    def test_empty_episode_list_is_rejected(self):
        self.assertField("episode_ids", build, episode_ids=[])

    def test_owner_cannot_grant_to_self(self):
        self.assertField("subject_id", build, subject_id="owner-1")

    def test_unknown_role(self):
        self.assertField("role", build, role="root")

    def test_expiry_must_follow_the_grant(self):
        self.assertField(
            "expires_on", build, granted_on="2021-05-10", expires_on="2021-05-01"
        )

    def test_expiry_may_be_absent(self):
        self.assertIsNone(build(granted_on="2021-05-10").expires_on)


class ExpiryTests(DomainTestCase):
    def test_never_expires_without_a_date(self):
        self.assertFalse(build().is_expired("2030-01-01"))

    def test_before_expiry(self):
        grant = build(granted_on="2021-05-01", expires_on="2021-06-01")
        self.assertFalse(grant.is_expired("2021-05-31"))

    def test_on_the_expiry_day(self):
        grant = build(granted_on="2021-05-01", expires_on="2021-06-01")
        self.assertTrue(grant.is_expired("2021-06-01"))

    def test_is_active_is_the_inverse(self):
        grant = build(granted_on="2021-05-01", expires_on="2021-06-01")
        self.assertTrue(grant.is_active("2021-05-31"))
        self.assertFalse(grant.is_active("2021-06-01"))


class CoverageTests(DomainTestCase):
    def test_wildcard_covers_anything(self):
        self.assertTrue(build().covers_episode("e-9"))

    def test_listed_episode(self):
        self.assertTrue(build(episode_ids=["e-1"]).covers_episode("e-1"))

    def test_unlisted_episode(self):
        self.assertFalse(build(episode_ids=["e-1"]).covers_episode("e-2"))


class AllowsTests(DomainTestCase):
    def test_role_permission(self):
        self.assertTrue(build().allows("episodes:read"))

    def test_missing_role_permission(self):
        self.assertFalse(build().allows("episodes:delete"))

    def test_producer_grant(self):
        self.assertTrue(build(role="producer").allows("episodes:publish"))

    def test_episode_scope(self):
        grant = build(episode_ids=["e-1"])
        self.assertTrue(grant.allows("episodes:read", "e-1"))
        self.assertFalse(grant.allows("episodes:read", "e-2"))

    def test_expired_grant_allows_nothing(self):
        grant = build(granted_on="2021-05-01", expires_on="2021-06-01")
        self.assertFalse(grant.allows("episodes:read", on="2021-06-02"))

    def test_active_grant_still_allows(self):
        grant = build(granted_on="2021-05-01", expires_on="2021-06-01")
        self.assertTrue(grant.allows("episodes:read", on="2021-05-02"))

    def test_require_passes(self):
        self.assertTrue(build().require("episodes:read"))

    def test_require_raises(self):
        error = self.assertRaisesCode("forbidden", build().require, "episodes:delete")
        self.assertEqual("guest-1", error.subject)


class NarrowTests(DomainTestCase):
    def test_narrowed_to(self):
        narrowed = build().narrowed_to(["e-1"])
        self.assertEqual(("e-1",), narrowed.episode_ids)

    def test_narrowing_returns_a_copy(self):
        grant = build()
        grant.narrowed_to(["e-1"])
        self.assertTrue(grant.covers_all_episodes)

    def test_narrowing_keeps_the_role(self):
        self.assertEqual("producer", build(role="producer").narrowed_to(["e-1"]).role)


class SerialisationTests(DomainTestCase):
    def test_to_dict_wildcard(self):
        self.assertEqual("*", build().to_dict()["episode_ids"])

    def test_to_dict_list(self):
        self.assertEqual(["e-1"], build(episode_ids=["e-1"]).to_dict()["episode_ids"])

    def test_round_trip(self):
        grant = build(role="producer", episode_ids=["e-1"], granted_on="2021-05-01")
        self.assertRoundTrips(mod.Grant.from_dict, grant)

    def test_round_trip_wildcard(self):
        self.assertRoundTrips(mod.Grant.from_dict, build())

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_inequality(self):
        self.assertNotEqual(build(), build(role="producer"))

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr_masks_the_ids(self):
        self.assertNotIn("owner-1", repr(build()))


class QueryTests(DomainTestCase):
    def setUp(self):
        self.one = build(owner_id="owner-1", subject_id="guest-1")
        self.two = build(owner_id="owner-2", subject_id="guest-1")
        self.other = build(owner_id="owner-1", subject_id="guest-2")
        self.stale = build(
            owner_id="owner-3",
            subject_id="guest-1",
            granted_on="2021-01-01",
            expires_on="2021-02-01",
        )

    def test_grants_for(self):
        found = mod.grants_for([self.one, self.other], "guest-1")
        self.assertEqual((self.one,), found)

    def test_grants_for_filters_expired(self):
        found = mod.grants_for([self.one, self.stale], "guest-1", "2021-03-01")
        self.assertEqual((self.one,), found)

    def test_grants_for_without_a_date_keeps_expired(self):
        found = mod.grants_for([self.one, self.stale], "guest-1")
        self.assertEqual(2, len(found))

    def test_studios_visible(self):
        found = mod.studios_visible_to([self.one, self.two, self.other], "guest-1")
        self.assertEqual(("owner-1", "owner-2"), found)

    def test_studios_visible_to_a_stranger(self):
        self.assertEqual((), mod.studios_visible_to([self.one], "guest-9"))
