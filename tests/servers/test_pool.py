from src.domain.servers.lifecycle import DRAINING, READY, REQUESTED, RestreamServer
from src.domain.servers import pool as mod
from tests.support import DomainTestCase


def server(reference="I-1", region="eu-west-1", **overrides):
    payload = {"subscription_reference": reference, "region": region}
    payload.update(overrides)
    return RestreamServer(**payload)


class ConstructionTests(DomainTestCase):
    def test_empty(self):
        self.assertEqual(0, len(mod.ServerPool()))

    def test_holds_servers(self):
        self.assertEqual(1, len(mod.ServerPool([server()])))

    def test_rejects_other_objects(self):
        self.assertField("servers", mod.ServerPool, ["not-a-server"])

    def test_rejects_duplicates(self):
        self.assertField("servers", mod.ServerPool, [server(), server()])

    def test_iterable(self):
        self.assertEqual(1, len(list(mod.ServerPool([server()]))))


class MutationTests(DomainTestCase):
    def test_with_server(self):
        pool = mod.ServerPool().with_server(server())
        self.assertEqual(1, len(pool))

    def test_with_server_returns_a_copy(self):
        pool = mod.ServerPool()
        pool.with_server(server())
        self.assertEqual(0, len(pool))

    def test_without(self):
        one = server()
        pool = mod.ServerPool([one]).without(one.name)
        self.assertEqual(0, len(pool))

    def test_without_an_absent_name(self):
        self.assertEqual(1, len(mod.ServerPool([server()]).without("nope")))

    def test_replace(self):
        one = server()
        pool = mod.ServerPool([one]).replace(one.start_provisioning())
        self.assertEqual("provisioning", pool.find(one.name).state)

    def test_replace_keeps_the_order(self):
        first, second = server("I-1"), server("I-2")
        pool = mod.ServerPool([first, second]).replace(first.start_provisioning())
        self.assertEqual(first.name, pool.servers[0].name)

    def test_replace_rejects_a_stranger(self):
        self.assertField("server", mod.ServerPool().replace, server())


class QueryTests(DomainTestCase):
    def setUp(self):
        self.ready = server("I-1", "eu-west-1", state=READY, image_id="ami-1", assigned=1)
        self.pending = server("I-2", "us-east-1")
        self.draining = server("I-3", "eu-west-1", state=DRAINING)
        self.pool = mod.ServerPool([self.ready, self.pending, self.draining])

    def test_find(self):
        self.assertEqual(self.ready, self.pool.find(self.ready.name))

    def test_find_default(self):
        self.assertEqual("x", self.pool.find("nope", "x"))

    def test_for_subscription(self):
        self.assertEqual((self.ready,), self.pool.for_subscription("I-1"))

    def test_for_an_unknown_subscription(self):
        self.assertEqual((), self.pool.for_subscription("I-9"))

    def test_in_state(self):
        self.assertEqual((self.pending,), self.pool.in_state(REQUESTED))

    def test_unknown_state(self):
        self.assertField("state", self.pool.in_state, "booting")

    def test_usable(self):
        self.assertEqual((self.ready,), self.pool.usable())

    def test_in_region(self):
        self.assertEqual(2, len(self.pool.in_region("eu-west-1")))

    def test_in_region_normalises(self):
        self.assertEqual(2, len(self.pool.in_region("EU-WEST-1")))

    def test_with_room(self):
        self.assertEqual((self.ready,), self.pool.with_room())

    def test_with_room_for_several(self):
        self.assertEqual((), self.pool.with_room(4))


class CapacityTests(DomainTestCase):
    def test_total_capacity_counts_usable_only(self):
        pool = mod.ServerPool([server("I-1", state=READY), server("I-2")])
        self.assertEqual(4, pool.total_capacity())

    def test_total_assigned(self):
        pool = mod.ServerPool([server("I-1", state=READY, assigned=3)])
        self.assertEqual(3, pool.total_assigned())

    def test_utilisation(self):
        pool = mod.ServerPool([server("I-1", state=READY, assigned=1)])
        self.assertEqual(25.0, pool.utilisation_percent())

    def test_utilisation_of_an_empty_pool(self):
        self.assertEqual(0.0, mod.ServerPool().utilisation_percent())

    def test_utilisation_without_usable_servers(self):
        self.assertEqual(0.0, mod.ServerPool([server()]).utilisation_percent())


class NearestTests(DomainTestCase):
    def setUp(self):
        self.near = server("I-1", "eu-central-1", state=READY)
        self.far = server("I-2", "ap-southeast-2", state=READY)
        self.pool = mod.ServerPool([self.far, self.near])

    def test_picks_the_closest(self):
        self.assertEqual(self.near, self.pool.nearest_usable("eu-west-1"))

    def test_skips_full_servers(self):
        pool = mod.ServerPool([self.near.with_assigned(4), self.far])
        self.assertEqual(self.far, pool.nearest_usable("eu-west-1"))

    def test_skips_unusable_servers(self):
        self.assertIsNone(mod.ServerPool([server()]).nearest_usable("eu-west-1"))

    def test_empty_pool(self):
        self.assertIsNone(mod.ServerPool().nearest_usable("eu-west-1"))

    def test_room_requirement(self):
        pool = mod.ServerPool([self.near.with_assigned(3), self.far])
        self.assertEqual(self.far, pool.nearest_usable("eu-west-1", 2))


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = mod.ServerPool([server("I-1", state=READY, assigned=1)]).to_dict()
        self.assertEqual(1, len(payload["servers"]))
        self.assertEqual(25.0, payload["utilisation_percent"])

    def test_equality(self):
        self.assertEqual(mod.ServerPool([server()]), mod.ServerPool([server()]))

    def test_hashable(self):
        self.assertEqual(1, len({mod.ServerPool(), mod.ServerPool()}))

    def test_repr(self):
        self.assertIn("0 servers", repr(mod.ServerPool()))
