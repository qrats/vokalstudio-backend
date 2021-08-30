from src.domain.core import result as res
from src.domain.core.errors import DomainError, ValidationError
from tests.support import DomainTestCase


class OkTests(DomainTestCase):
    def test_is_ok(self):
        self.assertTrue(res.Ok(1).ok)

    def test_unwrap(self):
        self.assertEqual(1, res.Ok(1).unwrap())

    def test_unwrap_or_ignores_default(self):
        self.assertEqual(1, res.Ok(1).unwrap_or(9))

    def test_map(self):
        self.assertEqual(res.Ok(2), res.Ok(1).map(lambda n: n + 1))

    def test_default_value_is_none(self):
        self.assertIsNone(res.Ok().unwrap())

    def test_equality(self):
        self.assertEqual(res.Ok(1), res.Ok(1))

    def test_inequality(self):
        self.assertNotEqual(res.Ok(1), res.Ok(2))

    def test_hashable(self):
        self.assertEqual(1, len({res.Ok(1), res.Ok(1)}))

    def test_repr(self):
        self.assertEqual("Ok(1)", repr(res.Ok(1)))


class ErrTests(DomainTestCase):
    def test_is_not_ok(self):
        self.assertFalse(res.Err("bad").ok)

    def test_string_is_wrapped(self):
        self.assertIsInstance(res.Err("bad").error, DomainError)

    def test_unwrap_raises(self):
        with self.assertRaises(ValidationError):
            res.Err(ValidationError("bad")).unwrap()

    def test_unwrap_or_returns_default(self):
        self.assertEqual(9, res.Err("bad").unwrap_or(9))

    def test_map_is_a_no_op(self):
        failure = res.Err("bad")
        self.assertIs(failure, failure.map(lambda n: n + 1))

    def test_message(self):
        self.assertEqual("bad", res.Err("bad").message)

    def test_equality_uses_message(self):
        self.assertEqual(res.Err("bad"), res.Err("bad"))

    def test_repr(self):
        self.assertIn("Err(", repr(res.Err("bad")))

    def test_not_equal_to_ok(self):
        self.assertNotEqual(res.Err("bad"), res.Ok("bad"))


class AttemptTests(DomainTestCase):
    def test_success(self):
        self.assertEqual(res.Ok(3), res.attempt(lambda a, b: a + b, 1, 2))

    def test_domain_error_is_captured(self):
        outcome = res.attempt(lambda: (_ for _ in ()).throw(ValidationError("bad")))
        self.assertFalse(outcome.ok)

    def test_other_errors_propagate(self):
        with self.assertRaises(ZeroDivisionError):
            res.attempt(lambda: 1 / 0)

    def test_keyword_arguments(self):
        self.assertEqual(res.Ok(5), res.attempt(lambda a, b=0: a + b, 1, b=4))


class CollectTests(DomainTestCase):
    def test_all_ok(self):
        self.assertEqual(res.Ok((1, 2)), res.collect([res.Ok(1), res.Ok(2)]))

    def test_first_error_wins(self):
        outcome = res.collect([res.Ok(1), res.Err("a"), res.Err("b")])
        self.assertEqual("a", outcome.message)

    def test_empty(self):
        self.assertEqual(res.Ok(()), res.collect([]))


class PartitionResultsTests(DomainTestCase):
    def test_splits(self):
        values, errors = res.partition_results([res.Ok(1), res.Err("a"), res.Ok(2)])
        self.assertEqual((1, 2), values)
        self.assertEqual(1, len(errors))

    def test_empty(self):
        self.assertEqual(((), ()), res.partition_results([]))

    def test_first_error_helper(self):
        self.assertIsNone(res.first_error([res.Ok(1)]))

    def test_first_error_returns_error(self):
        self.assertEqual("a", res.first_error([res.Err("a")]).message)
