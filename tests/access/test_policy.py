from src.domain.access.grant import Grant
from src.domain.access import policy as mod
from src.domain.catalog.entitlement import Entitlement
from tests.support import DomainTestCase


class ActorTests(DomainTestCase):
    def test_owner_defaults_to_the_user(self):
        actor = mod.Actor("u-1", "owner")
        self.assertEqual("u-1", actor.owner_id)
        self.assertTrue(actor.owns_the_studio)

    def test_explicit_owner(self):
        actor = mod.Actor("u-2", "producer", "u-1")
        self.assertFalse(actor.owns_the_studio)

    def test_is_administrator(self):
        self.assertTrue(mod.Actor("u-1", "admin").is_administrator)

    def test_owner_is_not_an_administrator(self):
        self.assertFalse(mod.Actor("u-1", "owner").is_administrator)

    def test_unknown_role(self):
        self.assertField("role", mod.Actor, "u-1", "root")

    def test_empty_user_id(self):
        self.assertField("user_id", mod.Actor, "", "owner")

    def test_to_dict(self):
        self.assertEqual(
            {"user_id": "u-1", "role": "owner", "owner_id": "u-1"},
            mod.Actor("u-1", "owner").to_dict(),
        )

    def test_equality(self):
        self.assertEqual(mod.Actor("u-1", "owner"), mod.Actor("u-1", "owner"))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Actor("u-1", "owner"), mod.Actor("u-1", "owner")}))

    def test_repr(self):
        self.assertIn("u-1", repr(mod.Actor("u-1", "owner")))

    def test_owner_actor_helper(self):
        self.assertEqual("owner", mod.owner_actor("u-1").role)


class DecisionTests(DomainTestCase):
    def test_truthiness(self):
        self.assertTrue(bool(mod.Decision(True, "episodes:read")))
        self.assertFalse(bool(mod.Decision(False, "episodes:read")))

    def test_raise_if_denied_passes(self):
        self.assertTrue(mod.Decision(True, "episodes:read").raise_if_denied())

    def test_raise_if_denied_raises(self):
        error = self.assertRaisesCode(
            "forbidden", mod.Decision(False, "episodes:read", "nope").raise_if_denied
        )
        self.assertEqual("episodes:read", error.action)

    def test_raise_carries_the_subject(self):
        error = self.assertRaisesCode(
            "forbidden",
            mod.Decision(False, "episodes:read").raise_if_denied,
            "u-1",
        )
        self.assertEqual("u-1", error.subject)

    def test_to_dict(self):
        payload = mod.Decision(False, "episodes:read", "nope").to_dict()
        self.assertFalse(payload["allowed"])
        self.assertEqual("nope", payload["reason"])

    def test_equality(self):
        self.assertEqual(mod.Decision(True, "a"), mod.Decision(True, "a"))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Decision(True, "a"), mod.Decision(True, "a")}))

    def test_repr(self):
        self.assertIn("episodes:read", repr(mod.Decision(True, "episodes:read")))


class OwnStudioTests(DomainTestCase):
    def setUp(self):
        self.owner = mod.Actor("u-1", "owner")

    def test_owner_may_delete_episodes(self):
        self.assertTrue(mod.decide(self.owner, "episodes:delete").allowed)

    def test_owner_may_not_touch_users(self):
        decision = mod.decide(self.owner, "users:delete")
        self.assertFalse(decision.allowed)
        self.assertIn("role", decision.reason)

    def test_administrator_bypasses_everything(self):
        decision = mod.decide(mod.Actor("u-9", "admin"), "users:delete")
        self.assertEqual("administrator", decision.reason)

    def test_allowed_decision_has_no_reason(self):
        self.assertIsNone(mod.decide(self.owner, "episodes:delete").reason)


class OtherStudioTests(DomainTestCase):
    def setUp(self):
        self.actor = mod.Actor("u-2", "producer", "u-1")
        self.grant = Grant("u-1", "u-2", "producer")

    def test_grant_lets_the_action_through(self):
        self.assertTrue(mod.decide(self.actor, "episodes:publish", [self.grant]).allowed)

    def test_no_grant_denies(self):
        decision = mod.decide(self.actor, "episodes:publish", [])
        self.assertFalse(decision.allowed)
        self.assertIn("grant", decision.reason)

    def test_grant_for_another_studio_does_not_count(self):
        other = Grant("u-9", "u-2", "producer")
        self.assertFalse(mod.decide(self.actor, "episodes:publish", [other]).allowed)

    def test_grant_role_bounds_the_action(self):
        self.assertFalse(mod.decide(self.actor, "episodes:delete", [self.grant]).allowed)

    def test_episode_scope_is_respected(self):
        narrow = self.grant.narrowed_to(["e-1"])
        self.assertTrue(
            mod.decide(self.actor, "episodes:publish", [narrow], episode_id="e-1").allowed
        )
        self.assertFalse(
            mod.decide(self.actor, "episodes:publish", [narrow], episode_id="e-2").allowed
        )

    def test_expired_grant_denies(self):
        stale = Grant("u-1", "u-2", "producer", None, "2021-01-01", "2021-02-01")
        decision = mod.decide(self.actor, "episodes:publish", [stale], on="2021-05-01")
        self.assertFalse(decision.allowed)


class EntitlementTests(DomainTestCase):
    def setUp(self):
        self.owner = mod.Actor("u-1", "owner")

    def test_plan_without_the_feature_denies(self):
        rights = Entitlement({"streaming.restream_server": False})
        decision = mod.decide(self.owner, "restream_servers:read", entitlement=rights)
        self.assertFalse(decision.allowed)
        self.assertIn("streaming.restream_server", decision.reason)

    def test_plan_with_the_feature_allows(self):
        rights = Entitlement({"streaming.restream_server": True})
        self.assertTrue(
            mod.decide(self.owner, "restream_servers:read", entitlement=rights).allowed
        )

    def test_limit_features_are_not_checked_here(self):
        rights = Entitlement({"streaming.targets": 0})
        self.assertTrue(
            mod.decide(self.owner, "streaming_platforms:create", entitlement=rights).allowed
        )

    def test_unmapped_permission_ignores_the_plan(self):
        rights = Entitlement()
        self.assertTrue(mod.decide(self.owner, "episodes:read", entitlement=rights).allowed)

    def test_no_entitlement_skips_the_check(self):
        self.assertTrue(mod.decide(self.owner, "restream_servers:read").allowed)

    def test_administrator_skips_the_plan_check(self):
        rights = Entitlement({"streaming.restream_server": False})
        actor = mod.Actor("u-9", "admin")
        self.assertTrue(mod.decide(actor, "restream_servers:read", entitlement=rights).allowed)

    def test_every_mapped_feature_is_known(self):
        from src.domain.catalog.feature import BY_KEY

        for feature in mod.FEATURE_BY_PERMISSION.values():
            self.assertIn(feature, BY_KEY)


class RequireTests(DomainTestCase):
    def test_passes(self):
        self.assertTrue(mod.require(mod.Actor("u-1", "owner"), "episodes:read"))

    def test_raises(self):
        error = self.assertRaisesCode(
            "forbidden", mod.require, mod.Actor("u-1", "owner"), "users:delete"
        )
        self.assertEqual("u-1", error.subject)
