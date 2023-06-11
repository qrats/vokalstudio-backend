from src.domain.access import role as mod
from tests.support import DomainTestCase


class NormalizeTests(DomainTestCase):
    def test_lowercases(self):
        self.assertEqual("owner", mod.normalize_role("OWNER"))

    def test_unknown_role(self):
        error = self.assertRaisesCode("validation_failed", mod.normalize_role, "root")
        self.assertIn("admin", error.details["allowed"])

    def test_empty(self):
        self.assertField("role", mod.normalize_role, "")

    def test_field_name(self):
        self.assertField("actor_role", mod.normalize_role, "root", "actor_role")


class PermissionTests(DomainTestCase):
    def test_admin_can_do_anything(self):
        self.assertTrue(mod.can(mod.ADMIN, "users:delete"))

    def test_owner_can_delete_episodes(self):
        self.assertTrue(mod.can(mod.OWNER, "episodes:delete"))

    def test_owner_cannot_touch_users(self):
        self.assertFalse(mod.can(mod.OWNER, "users:delete"))

    def test_producer_can_publish(self):
        self.assertTrue(mod.can(mod.PRODUCER, "episodes:publish"))

    def test_producer_cannot_delete(self):
        self.assertFalse(mod.can(mod.PRODUCER, "episodes:delete"))

    def test_producer_cannot_invite(self):
        self.assertFalse(mod.can(mod.PRODUCER, "authorized_users:invite"))

    def test_guest_can_only_read(self):
        self.assertTrue(mod.can(mod.GUEST, "episodes:read"))
        self.assertFalse(mod.can(mod.GUEST, "episodes:create"))

    def test_viewer_sees_analytics(self):
        self.assertTrue(mod.can(mod.VIEWER, "analytics:read"))

    def test_viewer_cannot_read_media(self):
        self.assertFalse(mod.can(mod.VIEWER, "media:read"))

    def test_permissions_for_returns_a_set(self):
        self.assertTrue(mod.permissions_for(mod.OWNER).allows("episodes:read"))

    def test_describe_is_sorted(self):
        described = mod.describe(mod.GUEST)
        self.assertEqual(tuple(sorted(described)), described)


class HierarchyTests(DomainTestCase):
    def test_rank_covers_every_role(self):
        self.assertEqual(set(mod.ROLES), set(mod.RANK))

    def test_outranks(self):
        self.assertTrue(mod.outranks(mod.OWNER, mod.PRODUCER))

    def test_does_not_outrank(self):
        self.assertFalse(mod.outranks(mod.PRODUCER, mod.OWNER))

    def test_equal_roles_do_not_outrank(self):
        self.assertFalse(mod.outranks(mod.OWNER, mod.OWNER))

    def test_admin_is_top(self):
        self.assertTrue(mod.outranks(mod.ADMIN, mod.OWNER))

    def test_highest(self):
        self.assertEqual(mod.OWNER, mod.highest([mod.GUEST, mod.OWNER, mod.VIEWER]))

    def test_highest_of_nothing(self):
        self.assertEqual(mod.VIEWER, mod.highest([]))

    def test_highest_default(self):
        self.assertEqual(mod.GUEST, mod.highest([], mod.GUEST))

    def test_highest_rejects_unknown(self):
        self.assertField("role", mod.highest, ["root"])


class CustomRoleTests(DomainTestCase):
    def test_adds_a_permission(self):
        rights = mod.custom_role(mod.GUEST, ["media:create"])
        self.assertTrue(rights.allows("media:create"))

    def test_keeps_the_base(self):
        rights = mod.custom_role(mod.GUEST, ["media:create"])
        self.assertTrue(rights.allows("episodes:read"))

    def test_removes_a_permission(self):
        rights = mod.custom_role(mod.GUEST, removed=["episodes:read"])
        self.assertFalse(rights.allows("episodes:read"))

    def test_add_and_remove(self):
        rights = mod.custom_role(mod.GUEST, ["media:create"], ["episodes:read"])
        self.assertEqual(3, len(rights))

    def test_no_change(self):
        self.assertEqual(mod.permissions_for(mod.GUEST), mod.custom_role(mod.GUEST))

    def test_unknown_base(self):
        self.assertField("role", mod.custom_role, "root")
