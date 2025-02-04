from src.domain.servers import allocator as mod
from src.domain.servers.lifecycle import DRAINING, READY, RELEASED, RestreamServer
from src.domain.servers.pool import ServerPool
from tests.support import DomainTestCase


def server(reference="I-1", region="eu-west-1", **overrides):
    payload = {"subscription_reference": reference, "region": region}
    payload.update(overrides)
    return RestreamServer(**payload)


class AllocationTests(DomainTestCase):
    def test_unknown_outcome(self):
        self.assertField("outcome", mod.Allocation, "maybe")

    def test_needs_provisioning(self):
        self.assertTrue(mod.Allocation(mod.PROVISION).needs_provisioning)

    def test_satisfied_by_reuse(self):
        self.assertTrue(mod.Allocation(mod.REUSED).satisfied)

    def test_satisfied_by_sharing(self):
        self.assertTrue(mod.Allocation(mod.SHARED).satisfied)

    def test_refused_is_not_satisfied(self):
        self.assertFalse(mod.Allocation(mod.REFUSED).satisfied)

    def test_to_dict(self):
        payload = mod.Allocation(mod.PROVISION, None, "t3.medium", "because").to_dict()
        self.assertEqual("t3.medium", payload["instance_type"])
        self.assertIsNone(payload["server"])

    def test_to_dict_with_a_server(self):
        payload = mod.Allocation(mod.REUSED, server(), "t3.medium").to_dict()
        self.assertEqual(server().name, payload["server"]["name"])

    def test_equality(self):
        self.assertEqual(mod.Allocation(mod.REUSED), mod.Allocation(mod.REUSED))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Allocation(mod.REUSED), mod.Allocation(mod.REUSED)}))

    def test_repr(self):
        self.assertIn("reused", repr(mod.Allocation(mod.REUSED)))


class AllocateTests(DomainTestCase):
    def setUp(self):
        self.own = server("I-1", "eu-west-1", state=READY, image_id="ami-1", assigned=1)
        self.other = server("I-2", "eu-central-1", state=READY, image_id="ami-2")

    def test_reuses_its_own_server(self):
        pool = ServerPool([self.own, self.other])
        decision = mod.allocate(pool, "I-1", "eu-west-1", 2)
        self.assertEqual(mod.REUSED, decision.outcome)
        self.assertEqual(self.own.name, decision.server.name)

    def test_ignores_its_own_full_server(self):
        pool = ServerPool([self.own.with_assigned(4), self.other])
        decision = mod.allocate(pool, "I-1", "eu-west-1", 2)
        self.assertEqual(mod.SHARED, decision.outcome)

    def test_shares_a_nearby_server(self):
        pool = ServerPool([self.other])
        decision = mod.allocate(pool, "I-9", "eu-west-1", 2)
        self.assertEqual(mod.SHARED, decision.outcome)
        self.assertEqual(self.other.name, decision.server.name)

    def test_provisions_when_nothing_is_near(self):
        far = server("I-2", "ap-southeast-2", state=READY, image_id="ami-2")
        decision = mod.allocate(ServerPool([far]), "I-9", "us-east-1", 2)
        self.assertEqual(mod.PROVISION, decision.outcome)
        self.assertEqual("t3.small", decision.instance_type)

    def test_provisions_when_the_pool_is_empty(self):
        decision = mod.allocate(ServerPool(), "I-9", "eu-west-1", 3)
        self.assertEqual(mod.PROVISION, decision.outcome)
        self.assertEqual("t3.medium", decision.instance_type)

    def test_bitrate_sizes_the_instance(self):
        decision = mod.allocate(ServerPool(), "I-9", "eu-west-1", 2, 9000)
        self.assertEqual("c5.large", decision.instance_type)

    def test_refuses_an_impossible_fan_out(self):
        decision = mod.allocate(ServerPool(), "I-9", "eu-west-1", 100)
        self.assertEqual(mod.REFUSED, decision.outcome)
        self.assertIsNone(decision.instance_type)

    def test_unusable_servers_are_ignored(self):
        pool = ServerPool([server("I-2", "eu-west-1", state=DRAINING)])
        self.assertEqual(mod.PROVISION, mod.allocate(pool, "I-9", "eu-west-1", 1).outcome)

    def test_zero_targets(self):
        self.assertField("targets", mod.allocate, ServerPool(), "I-1", "eu-west-1", 0)

    def test_unknown_origin(self):
        self.assertField(
            "origin_region", mod.allocate, ServerPool(), "I-1", "mars-1", 1
        )

    def test_reason_is_reported(self):
        decision = mod.allocate(ServerPool(), "I-9", "eu-west-1", 1)
        self.assertIn("no server", decision.reason)


class RequestServerTests(DomainTestCase):
    def test_builds_a_record(self):
        decision = mod.allocate(ServerPool(), "I-9", "eu-west-1", 3)
        built = mod.request_server(decision, "I-9", "eu-west-1")
        self.assertEqual("I-9", built.subscription_reference)
        self.assertEqual("t3.medium", built.instance_type)

    def test_records_the_request_time(self):
        decision = mod.allocate(ServerPool(), "I-9", "eu-west-1", 1)
        built = mod.request_server(decision, "I-9", "eu-west-1", "2021-05-01T10:00:00Z")
        self.assertEqual("2021-05-01T10:00:00Z", built.requested_at.to_iso())

    def test_rejects_a_reuse_decision(self):
        self.assertField(
            "allocation", mod.request_server, mod.Allocation(mod.REUSED), "I-1", "eu-west-1"
        )

    def test_rejects_a_refusal(self):
        self.assertField(
            "allocation", mod.request_server, mod.Allocation(mod.REFUSED), "I-1", "eu-west-1"
        )


class ReleaseTests(DomainTestCase):
    def test_drains_a_ready_server(self):
        one = server("I-1", state=READY, image_id="ami-1")
        pool = mod.release_for(ServerPool([one]), "I-1")
        self.assertEqual(DRAINING, pool.find(one.name).state)

    def test_releases_a_pending_server(self):
        one = server("I-1")
        pool = mod.release_for(ServerPool([one]), "I-1")
        self.assertEqual(RELEASED, pool.find(one.name).state)

    def test_leaves_other_subscriptions_alone(self):
        mine, theirs = server("I-1", state=READY, image_id="a"), server("I-2")
        pool = mod.release_for(ServerPool([mine, theirs]), "I-1")
        self.assertEqual("requested", pool.find(theirs.name).state)

    def test_already_draining_is_untouched(self):
        one = server("I-1", state=DRAINING)
        pool = mod.release_for(ServerPool([one]), "I-1")
        self.assertEqual(DRAINING, pool.find(one.name).state)

    def test_unknown_subscription_changes_nothing(self):
        pool = ServerPool([server("I-1")])
        self.assertEqual(pool, mod.release_for(pool, "I-9"))
