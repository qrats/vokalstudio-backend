from src.domain.servers import lifecycle as mod
from tests.support import DomainTestCase


def build(**overrides):
    payload = {"subscription_reference": "I-1", "region": "eu-west-1"}
    payload.update(overrides)
    return mod.RestreamServer(**payload)


class ConstructionTests(DomainTestCase):
    def test_defaults(self):
        server = build()
        self.assertEqual("t3.medium", server.instance_type)
        self.assertEqual(mod.REQUESTED, server.state)
        self.assertEqual(0, server.assigned)

    def test_name_starts_with_the_region(self):
        self.assertTrue(build().name.startswith("vs-eu-west-1-"))

    def test_name_is_stable(self):
        self.assertEqual(build().name, build().name)

    def test_name_depends_on_the_subscription(self):
        self.assertNotEqual(build().name, build(subscription_reference="I-2").name)

    def test_unknown_region(self):
        self.assertField("region", build, region="mars-1")

    def test_unknown_instance_type(self):
        self.assertField("instance_type", build, instance_type="m5.huge")

    def test_unknown_state(self):
        self.assertField("state", build, state="booting")

    def test_assigned_cannot_exceed_capacity(self):
        self.assertField("assigned", build, assigned=5)

    def test_assigned_at_capacity_is_allowed(self):
        self.assertEqual(4, build(assigned=4).assigned)

    def test_negative_assigned(self):
        self.assertField("assigned", build, assigned=-1)

    def test_requested_at_is_optional(self):
        self.assertIsNone(build().requested_at)

    def test_requested_at_is_parsed(self):
        server = build(requested_at="2021-05-01T10:00:00Z")
        self.assertEqual("2021-05-01T10:00:00Z", server.requested_at.to_iso())


class CapacityTests(DomainTestCase):
    def test_capacity(self):
        self.assertEqual(4, build().capacity)

    def test_free_slots(self):
        self.assertEqual(3, build(assigned=1).free_slots)

    def test_no_free_slots(self):
        self.assertEqual(0, build(assigned=4).free_slots)

    def test_has_room_requires_ready(self):
        self.assertFalse(build().has_room())

    def test_ready_server_has_room(self):
        self.assertTrue(build(state=mod.READY).has_room())

    def test_full_server_has_no_room(self):
        self.assertFalse(build(state=mod.READY, assigned=4).has_room())

    def test_has_room_for_several(self):
        self.assertTrue(build(state=mod.READY, assigned=1).has_room(3))
        self.assertFalse(build(state=mod.READY, assigned=2).has_room(3))

    def test_is_usable(self):
        self.assertTrue(build(state=mod.READY).is_usable())

    def test_draining_is_not_usable(self):
        self.assertFalse(build(state=mod.DRAINING).is_usable())


class TransitionTests(DomainTestCase):
    def test_table_covers_every_state(self):
        self.assertEqual(set(mod.STATES), set(mod.TRANSITIONS))

    def test_released_is_terminal(self):
        self.assertEqual((), mod.TRANSITIONS[mod.RELEASED])

    def test_targets_are_known(self):
        for targets in mod.TRANSITIONS.values():
            for target in targets:
                self.assertIn(target, mod.STATES)

    def test_start_provisioning(self):
        self.assertEqual(mod.PROVISIONING, build().start_provisioning().state)

    def test_mark_ready(self):
        server = build().start_provisioning().mark_ready("ami-0123")
        self.assertEqual(mod.READY, server.state)
        self.assertEqual("ami-0123", server.image_id)

    def test_cannot_mark_a_requested_server_ready(self):
        self.assertRaisesCode("invalid_state", build().mark_ready, "ami-0123")

    def test_drain(self):
        ready = build().start_provisioning().mark_ready("ami-1")
        self.assertEqual(mod.DRAINING, ready.drain().state)

    def test_release_clears_assignments(self):
        ready = build(state=mod.READY, assigned=2)
        released = ready.drain().release()
        self.assertEqual(0, released.assigned)

    def test_draining_can_go_back_to_ready(self):
        ready = build(state=mod.DRAINING).moved_to(mod.READY)
        self.assertEqual(mod.READY, ready.state)

    def test_fail_then_retry(self):
        failed = build().start_provisioning().fail()
        self.assertEqual(mod.REQUESTED, failed.retry().state)

    def test_released_cannot_be_retried(self):
        released = build().release()
        self.assertRaisesCode("invalid_state", released.retry)

    def test_transitions_return_copies(self):
        server = build()
        server.start_provisioning()
        self.assertEqual(mod.REQUESTED, server.state)

    def test_with_assigned(self):
        self.assertEqual(2, build(state=mod.READY).with_assigned(2).assigned)

    def test_with_assigned_validates(self):
        self.assertField("assigned", build(state=mod.READY).with_assigned, 9)


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build(state=mod.READY, assigned=1).to_dict()
        self.assertEqual(4, payload["capacity"])
        self.assertEqual(1, payload["assigned"])

    def test_to_dict_carries_the_name(self):
        self.assertEqual(build().name, build().to_dict()["name"])

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_inequality(self):
        self.assertNotEqual(build(), build().start_provisioning())

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("requested", repr(build()))
