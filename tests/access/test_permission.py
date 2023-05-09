from src.domain.access import permission as mod
from tests.support import DomainTestCase


class PermissionTests(DomainTestCase):
    def test_resource_and_action(self):
        one = mod.Permission("episodes", "read")
        self.assertEqual("episodes", one.resource)
        self.assertEqual("read", one.action)

    def test_case_is_normalised(self):
        self.assertEqual("episodes", mod.Permission("EPISODES", "READ").resource)

    def test_unknown_resource(self):
        error = self.assertRaisesCode(
            "validation_failed", mod.Permission, "widgets", "read"
        )
        self.assertIn("episodes", error.details["allowed"])

    def test_unknown_action(self):
        self.assertField("action", mod.Permission, "episodes", "archive")

    def test_wildcard_resource(self):
        self.assertEqual("*", mod.Permission("*", "read").resource)

    def test_wildcard_action(self):
        self.assertEqual("*", mod.Permission("episodes", "*").action)

    def test_parse(self):
        self.assertEqual(mod.Permission("episodes", "read"), mod.Permission.parse("episodes:read"))

    def test_parse_without_a_colon(self):
        self.assertField("permission", mod.Permission.parse, "episodes")

    def test_parse_with_two_colons(self):
        self.assertField("permission", mod.Permission.parse, "a:b:c")

    def test_to_string(self):
        self.assertEqual("episodes:read", mod.Permission("episodes", "read").to_string())

    def test_to_dict(self):
        self.assertEqual(
            {"resource": "episodes", "action": "read"},
            mod.Permission("episodes", "read").to_dict(),
        )

    def test_is_wildcard(self):
        self.assertTrue(mod.Permission("*", "read").is_wildcard())

    def test_is_not_wildcard(self):
        self.assertFalse(mod.Permission("episodes", "read").is_wildcard())

    def test_equality(self):
        self.assertEqual(mod.Permission("episodes", "read"), mod.Permission("episodes", "read"))

    def test_ordering(self):
        self.assertLess(mod.Permission("episodes", "read"), mod.Permission("media", "read"))

    def test_hashable(self):
        self.assertEqual(
            1, len({mod.Permission("episodes", "read"), mod.Permission("episodes", "read")})
        )

    def test_repr(self):
        self.assertIn("episodes:read", repr(mod.Permission("episodes", "read")))


class CoverageTests(DomainTestCase):
    def test_exact_match(self):
        one = mod.Permission("episodes", "read")
        self.assertTrue(one.covers(one))

    def test_different_resource(self):
        self.assertFalse(
            mod.Permission("episodes", "read").covers(mod.Permission("media", "read"))
        )

    def test_different_action(self):
        self.assertFalse(
            mod.Permission("episodes", "read").covers(mod.Permission("episodes", "delete"))
        )

    def test_resource_wildcard(self):
        self.assertTrue(
            mod.Permission("*", "read").covers(mod.Permission("media", "read"))
        )

    def test_action_wildcard(self):
        self.assertTrue(
            mod.Permission("episodes", "*").covers(mod.Permission("episodes", "delete"))
        )

    def test_full_wildcard(self):
        self.assertTrue(
            mod.Permission("*", "*").covers(mod.Permission("users", "delete"))
        )

    def test_wildcard_is_not_covered_by_a_specific(self):
        self.assertFalse(
            mod.Permission("episodes", "read").covers(mod.Permission("*", "read"))
        )


class PermissionSetTests(DomainTestCase):
    def test_empty(self):
        self.assertEqual(0, len(mod.PermissionSet()))

    def test_from_strings(self):
        rights = mod.PermissionSet(["episodes:read", "media:read"])
        self.assertEqual(2, len(rights))

    def test_deduplicates(self):
        self.assertEqual(1, len(mod.PermissionSet(["episodes:read", "episodes:read"])))

    def test_sorted(self):
        rights = mod.PermissionSet(["media:read", "episodes:read"])
        self.assertEqual(["episodes:read", "media:read"], rights.to_list())

    def test_accepts_permission_objects(self):
        rights = mod.PermissionSet([mod.Permission("episodes", "read")])
        self.assertTrue(rights.allows("episodes:read"))

    def test_allows(self):
        self.assertTrue(mod.PermissionSet(["episodes:read"]).allows("episodes:read"))

    def test_does_not_allow(self):
        self.assertFalse(mod.PermissionSet(["episodes:read"]).allows("episodes:delete"))

    def test_wildcard_allows_everything(self):
        self.assertTrue(mod.PermissionSet.everything().allows("users:delete"))

    def test_union(self):
        merged = mod.PermissionSet(["episodes:read"]).union(
            mod.PermissionSet(["media:read"])
        )
        self.assertEqual(2, len(merged))

    def test_union_deduplicates(self):
        merged = mod.PermissionSet(["episodes:read"]).union(
            mod.PermissionSet(["episodes:read"])
        )
        self.assertEqual(1, len(merged))

    def test_without(self):
        rights = mod.PermissionSet(["episodes:read", "media:read"]).without("media:read")
        self.assertEqual(["episodes:read"], rights.to_list())

    def test_without_an_absent_permission(self):
        rights = mod.PermissionSet(["episodes:read"]).without("media:read")
        self.assertEqual(1, len(rights))

    def test_resources(self):
        rights = mod.PermissionSet(["episodes:read", "episodes:delete", "media:read"])
        self.assertEqual(("episodes", "media"), rights.resources())

    def test_iterable(self):
        self.assertEqual(1, len(list(mod.PermissionSet(["episodes:read"]))))

    def test_equality(self):
        self.assertEqual(
            mod.PermissionSet(["episodes:read"]), mod.PermissionSet(["episodes:read"])
        )

    def test_hashable(self):
        self.assertEqual(1, len({mod.PermissionSet(), mod.PermissionSet()}))

    def test_repr(self):
        self.assertIn("episodes:read", repr(mod.PermissionSet(["episodes:read"])))
