from src.domain.distribution import credential as mod
from tests.support import DomainTestCase

ISSUED = "2021-05-01T10:00:00Z"


def build(**overrides):
    payload = {
        "user_id": "u-1",
        "destination": "podbean",
        "token": "token-abcdefgh",
        "issued_at": ISSUED,
        "scopes": ["episode_publish"],
    }
    payload.update(overrides)
    return mod.Credential(**payload)


class ConstructionTests(DomainTestCase):
    def test_defaults(self):
        credential = build()
        self.assertEqual(3600, credential.expires_in)
        self.assertFalse(credential.can_refresh())

    def test_destination_must_use_oauth(self):
        self.assertField("destination", build, destination="apple")

    def test_unknown_destination(self):
        self.assertField("destination", build, destination="soundcloud")

    def test_short_token(self):
        self.assertField("token", build, token="abc")

    def test_short_refresh_token(self):
        self.assertField("refresh_token", build, refresh_token="abc")

    def test_zero_lifetime(self):
        self.assertField("expires_in", build, expires_in=0)

    def test_scopes_are_sorted_and_unique(self):
        credential = build(scopes=["b", "a", "b"])
        self.assertEqual(("a", "b"), credential.scopes)

    def test_scopes_are_lowercased(self):
        self.assertEqual(("upload",), build(scopes=["UPLOAD"]).scopes)

    def test_refresh_token_is_kept(self):
        self.assertTrue(build(refresh_token="refresh-abcdefgh").can_refresh())


class ExpiryTests(DomainTestCase):
    def test_expires_at(self):
        self.assertEqual("2021-05-01T11:00:00Z", build().expires_at().to_iso())

    def test_not_expired(self):
        self.assertFalse(build().is_expired("2021-05-01T10:59:59Z"))

    def test_expired_on_the_boundary(self):
        self.assertTrue(build().is_expired("2021-05-01T11:00:00Z"))

    def test_needs_refresh_inside_the_margin(self):
        self.assertTrue(build().needs_refresh("2021-05-01T10:55:00Z"))

    def test_does_not_need_refresh_yet(self):
        self.assertFalse(build().needs_refresh("2021-05-01T10:54:59Z"))

    def test_custom_margin(self):
        self.assertTrue(build().needs_refresh("2021-05-01T10:30:00Z", 1800))

    def test_negative_margin_is_rejected(self):
        self.assertField("margin_seconds", build().needs_refresh, ISSUED, -1)


class ScopeTests(DomainTestCase):
    def test_all_scopes_present(self):
        self.assertEqual((), build().missing_scopes())

    def test_missing_scope(self):
        self.assertEqual(("episode_publish",), build(scopes=[]).missing_scopes())

    def test_destination_without_required_scopes(self):
        credential = build(destination="spotify", scopes=["upload", "read"])
        self.assertEqual((), credential.missing_scopes())

    def test_partially_missing_scopes(self):
        credential = build(destination="spotify", scopes=["upload"])
        self.assertEqual(("read",), credential.missing_scopes())

    def test_is_usable(self):
        self.assertTrue(build().is_usable(ISSUED))

    def test_not_usable_when_expired(self):
        self.assertFalse(build().is_usable("2021-05-01T12:00:00Z"))

    def test_not_usable_without_scopes(self):
        self.assertFalse(build(scopes=[]).is_usable(ISSUED))


class RefreshTests(DomainTestCase):
    def test_refreshed(self):
        credential = build(refresh_token="refresh-abcdefgh")
        renewed = credential.refreshed("token-newtoken", "2021-05-01T11:00:00Z")
        self.assertEqual("2021-05-01T12:00:00Z", renewed.expires_at().to_iso())

    def test_refresh_token_is_carried(self):
        credential = build(refresh_token="refresh-abcdefgh")
        renewed = credential.refreshed("token-newtoken", "2021-05-01T11:00:00Z")
        self.assertTrue(renewed.can_refresh())

    def test_scopes_are_carried(self):
        credential = build(refresh_token="refresh-abcdefgh")
        renewed = credential.refreshed("token-newtoken", "2021-05-01T11:00:00Z")
        self.assertEqual(("episode_publish",), renewed.scopes)

    def test_new_refresh_token_replaces_the_old(self):
        credential = build(refresh_token="refresh-abcdefgh")
        renewed = credential.refreshed(
            "token-newtoken", "2021-05-01T11:00:00Z", refresh_token="refresh-zzzzzzzz"
        )
        self.assertEqual("refresh-zzzzzzzz", renewed.refresh_token)

    def test_without_a_refresh_token(self):
        self.assertField("refresh_token", build().refreshed, "token-newtoken", ISSUED)


class SerialisationTests(DomainTestCase):
    def test_token_is_masked(self):
        self.assertNotIn("token-abcdefgh", build().to_dict()["token"])

    def test_masked_token_keeps_the_tail(self):
        self.assertTrue(build().to_dict()["token"].endswith("efgh"))

    def test_expiry_is_included(self):
        self.assertEqual("2021-05-01T11:00:00Z", build().to_dict()["expires_at"])

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("podbean", repr(build()))


class LookupTests(DomainTestCase):
    def setUp(self):
        self.mine = build()
        self.theirs = build(user_id="u-2")
        self.other = build(destination="spotify", scopes=["upload", "read"])

    def test_for_destination(self):
        found = mod.for_destination([self.mine, self.other], "u-1", "podbean")
        self.assertEqual(self.mine, found)

    def test_wrong_user(self):
        self.assertIsNone(mod.for_destination([self.theirs], "u-1", "podbean"))

    def test_wrong_destination(self):
        self.assertIsNone(mod.for_destination([self.mine], "u-1", "spotify"))

    def test_due_for_refresh(self):
        fresh = build(refresh_token="refresh-abcdefgh")
        found = mod.due_for_refresh([fresh, self.mine], "2021-05-01T10:59:00Z")
        self.assertEqual((fresh,), found)

    def test_nothing_due(self):
        fresh = build(refresh_token="refresh-abcdefgh")
        self.assertEqual((), mod.due_for_refresh([fresh], ISSUED))
