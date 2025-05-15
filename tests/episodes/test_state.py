from src.domain.episodes import state as mod
from tests.support import DomainTestCase


class TableTests(DomainTestCase):
    def test_every_state_has_a_row(self):
        self.assertEqual(set(mod.STATES), set(mod.TRANSITIONS))

    def test_targets_are_known(self):
        for targets in mod.TRANSITIONS.values():
            for target in targets:
                self.assertIn(target, mod.STATES)

    def test_published_only_archives(self):
        self.assertEqual((mod.ARCHIVED,), mod.TRANSITIONS[mod.PUBLISHED])

    def test_archived_can_be_reopened(self):
        self.assertEqual((mod.DRAFT,), mod.TRANSITIONS[mod.ARCHIVED])


class TransitionTests(DomainTestCase):
    def test_draft_to_ready(self):
        self.assertTrue(mod.can_transition(mod.DRAFT, mod.READY))

    def test_draft_cannot_publish(self):
        self.assertFalse(mod.can_transition(mod.DRAFT, mod.PUBLISHED))

    def test_ready_to_scheduled(self):
        self.assertTrue(mod.can_transition(mod.READY, mod.SCHEDULED))

    def test_scheduled_back_to_ready(self):
        self.assertTrue(mod.can_transition(mod.SCHEDULED, mod.READY))

    def test_published_cannot_go_back(self):
        self.assertFalse(mod.can_transition(mod.PUBLISHED, mod.DRAFT))

    def test_unknown_current(self):
        self.assertField("current", mod.can_transition, "pending", mod.READY)

    def test_unknown_target(self):
        self.assertField("target", mod.can_transition, mod.DRAFT, "pending")

    def test_transition_returns_the_target(self):
        self.assertEqual(mod.READY, mod.transition(mod.DRAFT, mod.READY))

    def test_transition_raises(self):
        error = self.assertRaisesCode(
            "invalid_state", mod.transition, mod.PUBLISHED, mod.DRAFT
        )
        self.assertEqual(mod.PUBLISHED, error.current)


class PredicateTests(DomainTestCase):
    def test_published_is_visible(self):
        self.assertTrue(mod.is_visible(mod.PUBLISHED))

    def test_scheduled_is_not_visible(self):
        self.assertFalse(mod.is_visible(mod.SCHEDULED))

    def test_archived_is_not_visible(self):
        self.assertFalse(mod.is_visible(mod.ARCHIVED))

    def test_draft_is_editable(self):
        self.assertTrue(mod.is_editable(mod.DRAFT))

    def test_scheduled_is_editable(self):
        self.assertTrue(mod.is_editable(mod.SCHEDULED))

    def test_published_is_not_editable(self):
        self.assertFalse(mod.is_editable(mod.PUBLISHED))

    def test_unknown_state_is_rejected(self):
        self.assertField("state", mod.is_visible, "pending")


class ReachabilityTests(DomainTestCase):
    def test_from_draft(self):
        self.assertEqual(
            ("archived", "draft", "published", "ready", "scheduled"),
            mod.reachable_from(mod.DRAFT),
        )

    def test_from_published(self):
        self.assertIn("draft", mod.reachable_from(mod.PUBLISHED))

    def test_result_is_sorted(self):
        found = mod.reachable_from(mod.READY)
        self.assertEqual(tuple(sorted(found)), found)

    def test_unknown_state(self):
        self.assertField("state", mod.reachable_from, "pending")
