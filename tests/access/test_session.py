from src.domain.access import session as mod
from src.domain.timeline.instant import Instant
from tests.support import DomainTestCase

ISSUED = "2021-05-01T12:00:00Z"


def claims(**overrides):
    payload = {"subject": "u-1", "kind": mod.ACCESS, "issued_at": ISSUED}
    payload.update(overrides)
    return mod.TokenClaims(**payload)


class ConstructionTests(DomainTestCase):
    def test_access_ttl_default(self):
        self.assertEqual(mod.ACCESS_TTL_SECONDS, claims().ttl_seconds)

    def test_refresh_ttl_default(self):
        self.assertEqual(
            mod.REFRESH_TTL_SECONDS, claims(kind=mod.REFRESH).ttl_seconds
        )

    def test_explicit_ttl(self):
        self.assertEqual(60, claims(ttl_seconds=60).ttl_seconds)

    def test_zero_ttl_is_rejected(self):
        self.assertField("ttl_seconds", claims, ttl_seconds=0)

    def test_unknown_kind(self):
        self.assertField("kind", claims, kind="id")

    def test_empty_subject(self):
        self.assertField("subject", claims, subject="")

    def test_scopes_are_sorted_and_unique(self):
        self.assertEqual(("a", "b"), claims(scopes=["b", "a", "b"]).scopes)

    def test_scopes_are_lowercased(self):
        self.assertEqual(("admin",), claims(scopes=["ADMIN"]).scopes)

    def test_no_scopes_by_default(self):
        self.assertEqual((), claims().scopes)


class TokenIdTests(DomainTestCase):
    def test_jti_is_stable(self):
        self.assertEqual(claims().jti, claims().jti)

    def test_jti_depends_on_the_subject(self):
        self.assertNotEqual(claims().jti, claims(subject="u-2").jti)

    def test_jti_depends_on_the_kind(self):
        self.assertNotEqual(claims().jti, claims(kind=mod.REFRESH).jti)

    def test_jti_depends_on_the_issue_time(self):
        self.assertNotEqual(claims().jti, claims(issued_at="2021-05-01T12:00:01Z").jti)


class ExpiryTests(DomainTestCase):
    def test_expires_at(self):
        self.assertEqual(
            "2021-05-01T12:15:00Z", claims().expires_at().to_iso()
        )

    def test_not_yet_expired(self):
        self.assertFalse(claims().is_expired("2021-05-01T12:14:59Z"))

    def test_expired_on_the_boundary(self):
        self.assertTrue(claims().is_expired("2021-05-01T12:15:00Z"))

    def test_seconds_left(self):
        self.assertEqual(900, claims().seconds_left(ISSUED))

    def test_seconds_left_never_negative(self):
        self.assertEqual(0, claims().seconds_left("2021-06-01T00:00:00Z"))

    def test_seconds_left_part_way(self):
        self.assertEqual(600, claims().seconds_left("2021-05-01T12:05:00Z"))


class ScopeTests(DomainTestCase):
    def test_has_scope(self):
        self.assertTrue(claims(scopes=["admin"]).has_scope("admin"))

    def test_scope_lookup_is_case_insensitive(self):
        self.assertTrue(claims(scopes=["admin"]).has_scope("ADMIN"))

    def test_missing_scope(self):
        self.assertFalse(claims().has_scope("admin"))

    def test_empty_scope_is_rejected(self):
        self.assertField("scope", claims().has_scope, "")


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = claims().to_dict()
        self.assertEqual("u-1", payload["sub"])
        self.assertEqual("access", payload["type"])

    def test_expiry_is_in_seconds(self):
        payload = claims().to_dict()
        self.assertEqual(900, payload["exp"] - payload["iat"])

    def test_equality(self):
        self.assertEqual(claims(), claims())

    def test_inequality(self):
        self.assertNotEqual(claims(), claims(subject="u-2"))

    def test_hashable(self):
        self.assertEqual(1, len({claims(), claims()}))

    def test_repr(self):
        self.assertIn("u-1", repr(claims()))


class BlacklistTests(DomainTestCase):
    def test_empty(self):
        self.assertEqual(0, len(mod.Blacklist()))

    def test_with_revoked_claims(self):
        book = mod.Blacklist().with_revoked(claims())
        self.assertTrue(book.is_revoked(claims()))

    def test_with_revoked_jti(self):
        book = mod.Blacklist().with_revoked("abc")
        self.assertTrue(book.is_revoked("abc"))

    def test_unknown_jti(self):
        self.assertFalse(mod.Blacklist().is_revoked("abc"))

    def test_revoking_twice_is_idempotent(self):
        book = mod.Blacklist().with_revoked("abc").with_revoked("abc")
        self.assertEqual(1, len(book))

    def test_with_revoked_returns_a_copy(self):
        book = mod.Blacklist()
        book.with_revoked("abc")
        self.assertEqual(0, len(book))

    def test_empty_jti_is_rejected(self):
        self.assertField("jtis", mod.Blacklist, [""])

    def test_equality(self):
        self.assertEqual(mod.Blacklist(["a"]), mod.Blacklist(["a"]))

    def test_hashable(self):
        self.assertEqual(1, len({mod.Blacklist(), mod.Blacklist()}))

    def test_repr(self):
        self.assertIn("0 entries", repr(mod.Blacklist()))


class UsableTests(DomainTestCase):
    def test_fresh_token(self):
        self.assertTrue(mod.is_usable(claims(), ISSUED))

    def test_expired_token(self):
        self.assertFalse(mod.is_usable(claims(), "2021-05-01T13:00:00Z"))

    def test_revoked_token(self):
        book = mod.Blacklist().with_revoked(claims())
        self.assertFalse(mod.is_usable(claims(), ISSUED, book))

    def test_unrevoked_token(self):
        book = mod.Blacklist().with_revoked("other")
        self.assertTrue(mod.is_usable(claims(), ISSUED, book))


class RefreshTests(DomainTestCase):
    def setUp(self):
        self.refresh_token = claims(kind=mod.REFRESH, scopes=["admin"])

    def test_mints_an_access_token(self):
        minted = mod.refresh(self.refresh_token, "2021-05-02T00:00:00Z")
        self.assertEqual(mod.ACCESS, minted.kind)

    def test_carries_the_subject(self):
        minted = mod.refresh(self.refresh_token, "2021-05-02T00:00:00Z")
        self.assertEqual("u-1", minted.subject)

    def test_carries_the_scopes(self):
        minted = mod.refresh(self.refresh_token, "2021-05-02T00:00:00Z")
        self.assertEqual(("admin",), minted.scopes)

    def test_issued_at_is_now(self):
        minted = mod.refresh(self.refresh_token, "2021-05-02T00:00:00Z")
        self.assertEqual(Instant.parse("2021-05-02T00:00:00Z"), minted.issued_at)

    def test_custom_ttl(self):
        minted = mod.refresh(self.refresh_token, "2021-05-02T00:00:00Z", 60)
        self.assertEqual(60, minted.ttl_seconds)

    def test_access_token_cannot_be_exchanged(self):
        self.assertField("kind", mod.refresh, claims(), ISSUED)

    def test_expired_refresh_token_is_rejected(self):
        self.assertField(
            "issued_at", mod.refresh, self.refresh_token, "2021-07-01T00:00:00Z"
        )
