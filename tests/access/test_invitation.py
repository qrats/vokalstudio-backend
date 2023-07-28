from src.domain.access import invitation as mod
from tests.support import DomainTestCase


def build(**overrides):
    payload = {
        "owner_id": "owner-1",
        "email": "guest@example.com",
        "issued_on": "2021-05-01",
    }
    payload.update(overrides)
    return mod.Invitation(**payload)


class ConstructionTests(DomainTestCase):
    def test_defaults(self):
        invite = build()
        self.assertEqual("guest", invite.role)
        self.assertEqual(mod.PENDING, invite.state)
        self.assertEqual(7, invite.valid_days)

    def test_email_is_lowercased(self):
        self.assertEqual("guest@example.com", build(email="Guest@Example.COM").email)

    def test_email_without_an_at_sign(self):
        self.assertField("email", build, email="guest.example.com")

    def test_email_without_a_dot_in_the_domain(self):
        self.assertField("email", build, email="guest@example")

    def test_email_without_a_local_part(self):
        self.assertField("email", build, email="@example.com")

    def test_email_with_a_leading_dot_domain(self):
        self.assertField("email", build, email="guest@.example.com")

    def test_valid_days_floor(self):
        self.assertField("valid_days", build, valid_days=0)

    def test_valid_days_ceiling(self):
        self.assertField("valid_days", build, valid_days=91)

    def test_unknown_role(self):
        self.assertField("role", build, role="root")

    def test_unknown_state(self):
        self.assertField("state", build, state="sent")

    def test_issued_on_is_optional(self):
        self.assertIsNone(mod.Invitation("owner-1", "guest@example.com").issued_on)


class TokenTests(DomainTestCase):
    def test_token_is_stable(self):
        self.assertEqual(build().token, build().token)

    def test_token_depends_on_the_email(self):
        self.assertNotEqual(build().token, build(email="other@example.com").token)

    def test_token_depends_on_the_role(self):
        self.assertNotEqual(build().token, build(role="producer").token)

    def test_token_depends_on_the_owner(self):
        self.assertNotEqual(build().token, build(owner_id="owner-2").token)

    def test_token_depends_on_the_issue_date(self):
        self.assertNotEqual(build().token, build(issued_on="2021-05-02").token)

    def test_verify_accepts_its_own_token(self):
        invite = build()
        self.assertTrue(invite.verify(invite.token))

    def test_verify_rejects_another_token(self):
        self.assertFalse(build().verify(build(email="other@example.com").token))

    def test_token_survives_a_state_change(self):
        invite = build()
        self.assertEqual(invite.token, invite.decline().token)


class ExpiryTests(DomainTestCase):
    def test_expires_after_the_validity_window(self):
        self.assertEqual("2021-05-08", build().expires_on().isoformat())

    def test_custom_window(self):
        self.assertEqual("2021-05-31", build(valid_days=30).expires_on().isoformat())

    def test_no_expiry_without_an_issue_date(self):
        invite = mod.Invitation("owner-1", "guest@example.com")
        self.assertIsNone(invite.expires_on())
        self.assertFalse(invite.is_expired("2030-01-01"))

    def test_before_expiry(self):
        self.assertFalse(build().is_expired("2021-05-07"))

    def test_on_the_expiry_day(self):
        self.assertTrue(build().is_expired("2021-05-08"))

    def test_is_open_while_pending(self):
        self.assertTrue(build().is_open("2021-05-05"))

    def test_is_not_open_once_expired(self):
        self.assertFalse(build().is_open("2021-05-09"))

    def test_is_not_open_once_accepted(self):
        self.assertFalse(build().accept().is_open("2021-05-02"))

    def test_is_open_without_a_date(self):
        self.assertTrue(build().is_open())


class TransitionTests(DomainTestCase):
    def test_accept(self):
        self.assertEqual(mod.ACCEPTED, build().accept().state)

    def test_decline(self):
        self.assertEqual(mod.DECLINED, build().decline().state)

    def test_revoke(self):
        self.assertEqual(mod.REVOKED, build().revoke().state)

    def test_lapse(self):
        self.assertEqual(mod.LAPSED, build().lapse().state)

    def test_transitions_return_copies(self):
        invite = build()
        invite.accept()
        self.assertEqual(mod.PENDING, invite.state)

    def test_cannot_accept_twice(self):
        self.assertRaisesCode("invalid_state", build().accept().accept)

    def test_cannot_revoke_after_declining(self):
        self.assertRaisesCode("invalid_state", build().decline().revoke)

    def test_cannot_accept_after_expiry(self):
        error = self.assertRaisesCode("invalid_state", build().accept, "2021-05-09")
        self.assertEqual(mod.LAPSED, error.current)

    def test_can_accept_before_expiry(self):
        self.assertEqual(mod.ACCEPTED, build().accept("2021-05-05").state)


class GrantTests(DomainTestCase):
    def test_builds_a_grant(self):
        grant = build().to_grant("guest-1", "2021-05-05")
        self.assertEqual("owner-1", grant.owner_id)
        self.assertEqual("guest-1", grant.subject_id)

    def test_grant_carries_the_role(self):
        grant = build(role="producer").to_grant("guest-1", "2021-05-05")
        self.assertEqual("producer", grant.role)

    def test_grant_records_the_day(self):
        grant = build().to_grant("guest-1", "2021-05-05")
        self.assertEqual("2021-05-05", grant.granted_on.isoformat())

    def test_expired_invitation_cannot_be_redeemed(self):
        self.assertRaisesCode("invalid_state", build().to_grant, "guest-1", "2021-05-09")

    def test_accepted_invitation_cannot_be_redeemed_again(self):
        self.assertRaisesCode("invalid_state", build().accept().to_grant, "guest-1")


class SerialisationTests(DomainTestCase):
    def test_to_dict(self):
        payload = build().to_dict()
        self.assertEqual("guest@example.com", payload["email"])
        self.assertEqual(build().token, payload["token"])

    def test_equality(self):
        self.assertEqual(build(), build())

    def test_inequality(self):
        self.assertNotEqual(build(), build().accept())

    def test_hashable(self):
        self.assertEqual(1, len({build(), build()}))

    def test_repr(self):
        self.assertIn("pending", repr(build()))


class CollectionTests(DomainTestCase):
    def setUp(self):
        self.open_one = build()
        self.taken = build(email="taken@example.com").accept()
        self.stale = build(email="stale@example.com", issued_on="2021-01-01")

    def test_open_invitations(self):
        found = mod.open_invitations([self.open_one, self.taken], "2021-05-02")
        self.assertEqual((self.open_one,), found)

    def test_open_invitations_drops_expired(self):
        found = mod.open_invitations([self.open_one, self.stale], "2021-05-02")
        self.assertEqual((self.open_one,), found)

    def test_lapse_stale_moves_expired(self):
        updated = mod.lapse_stale([self.open_one, self.stale], "2021-05-02")
        self.assertEqual(mod.PENDING, updated[0].state)
        self.assertEqual(mod.LAPSED, updated[1].state)

    def test_lapse_stale_leaves_settled_invitations(self):
        updated = mod.lapse_stale([self.taken], "2030-01-01")
        self.assertEqual(mod.ACCEPTED, updated[0].state)

    def test_lapse_stale_keeps_the_order(self):
        updated = mod.lapse_stale([self.stale, self.open_one], "2021-05-02")
        self.assertEqual("stale@example.com", updated[0].email)
