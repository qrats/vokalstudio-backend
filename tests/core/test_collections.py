from src.domain.core import collections as coll
from tests.support import DomainTestCase


class Item:
    def __init__(self, name, size, kind="audio"):
        self.name = name
        self.size = size
        self.kind = kind


class FreezeTests(DomainTestCase):
    def test_scalar_passes_through(self):
        self.assertEqual(3, coll.freeze(3))

    def test_list_becomes_tuple(self):
        self.assertEqual((1, 2), coll.freeze([1, 2]))

    def test_nested_lists(self):
        self.assertEqual(((1,), (2,)), coll.freeze([[1], [2]]))

    def test_dict_becomes_sorted_pairs(self):
        self.assertEqual((("a", 1), ("b", 2)), coll.freeze({"b": 2, "a": 1}))

    def test_dict_values_are_frozen(self):
        self.assertEqual((("a", (1, 2)),), coll.freeze({"a": [1, 2]}))

    def test_set_becomes_tuple(self):
        self.assertEqual((1,), coll.freeze({1}))

    def test_frozen_values_hash(self):
        self.assertIsInstance(hash(coll.freeze({"a": [1]})), int)


class UniqueTests(DomainTestCase):
    def test_preserves_first_seen_order(self):
        self.assertEqual((3, 1, 2), coll.unique([3, 1, 3, 2, 1]))

    def test_key_function(self):
        items = [Item("a", 1), Item("b", 1), Item("c", 2)]
        self.assertEqual(("a", "c"), coll.pluck(coll.unique(items, lambda i: i.size), "name"))

    def test_empty(self):
        self.assertEqual((), coll.unique([]))


class GroupByTests(DomainTestCase):
    def test_groups_and_keeps_order(self):
        grouped = coll.group_by([1, 2, 3, 4], lambda n: n % 2)
        self.assertEqual({1: (1, 3), 0: (2, 4)}, grouped)

    def test_values_are_tuples(self):
        grouped = coll.group_by(["a"], len)
        self.assertIsInstance(grouped[1], tuple)

    def test_empty(self):
        self.assertEqual({}, coll.group_by([], len))


class IndexByTests(DomainTestCase):
    def test_builds_index(self):
        items = [Item("a", 1), Item("b", 2)]
        index = coll.index_by(items, lambda i: i.name)
        self.assertEqual(2, index["b"].size)

    def test_duplicate_raises_by_default(self):
        items = [Item("a", 1), Item("a", 2)]
        self.assertField("key", coll.index_by, items, lambda i: i.name)

    def test_duplicate_first_wins(self):
        items = [Item("a", 1), Item("a", 2)]
        index = coll.index_by(items, lambda i: i.name, "first")
        self.assertEqual(1, index["a"].size)

    def test_duplicate_last_wins(self):
        items = [Item("a", 1), Item("a", 2)]
        index = coll.index_by(items, lambda i: i.name, "last")
        self.assertEqual(2, index["a"].size)

    def test_unknown_policy_is_rejected(self):
        self.assertField("on_duplicate", coll.index_by, [], len, "sometimes")


class PartitionTests(DomainTestCase):
    def test_splits(self):
        even, odd = coll.partition(range(5), lambda n: n % 2 == 0)
        self.assertEqual((0, 2, 4), even)
        self.assertEqual((1, 3), odd)

    def test_empty(self):
        self.assertEqual(((), ()), coll.partition([], bool))


class ChunkTests(DomainTestCase):
    def test_even_split(self):
        self.assertEqual(((1, 2), (3, 4)), coll.chunk([1, 2, 3, 4], 2))

    def test_ragged_tail(self):
        self.assertEqual(((1, 2), (3,)), coll.chunk([1, 2, 3], 2))

    def test_size_larger_than_input(self):
        self.assertEqual(((1,),), coll.chunk([1], 9))

    def test_empty(self):
        self.assertEqual((), coll.chunk([], 2))

    def test_zero_size_is_rejected(self):
        self.assertField("size", coll.chunk, [1], 0)


class FirstTests(DomainTestCase):
    def test_returns_head(self):
        self.assertEqual(1, coll.first([1, 2]))

    def test_predicate(self):
        self.assertEqual(2, coll.first([1, 2, 3], lambda n: n % 2 == 0))

    def test_default(self):
        self.assertEqual("x", coll.first([], default="x"))

    def test_default_when_nothing_matches(self):
        self.assertIsNone(coll.first([1], lambda n: n > 5))


class SumMaxTests(DomainTestCase):
    def test_sum_by(self):
        items = [Item("a", 2), Item("b", 3)]
        self.assertEqual(5, coll.sum_by(items, lambda i: i.size))

    def test_sum_by_empty(self):
        self.assertEqual(0, coll.sum_by([], lambda i: i))

    def test_max_by(self):
        items = [Item("a", 2), Item("b", 9)]
        self.assertEqual("b", coll.max_by(items, lambda i: i.size).name)

    def test_max_by_default(self):
        self.assertIsNone(coll.max_by([], lambda i: i))

    def test_max_by_keeps_first_on_tie(self):
        items = [Item("a", 2), Item("b", 2)]
        self.assertEqual("a", coll.max_by(items, lambda i: i.size).name)


class MergeAndPluckTests(DomainTestCase):
    def test_merge_right_wins(self):
        self.assertEqual({"a": 2}, coll.merge_dicts({"a": 1}, {"a": 2}))

    def test_merge_skips_none(self):
        self.assertEqual({"a": 1}, coll.merge_dicts({"a": 1}, None))

    def test_merge_returns_new_dict(self):
        left = {"a": 1}
        coll.merge_dicts(left, {"b": 2})["a"] = 9
        self.assertEqual(1, left["a"])

    def test_pluck(self):
        self.assertEqual(("a", "b"), coll.pluck([Item("a", 1), Item("b", 1)], "name"))

    def test_sorted_by_single_key(self):
        items = [Item("b", 1), Item("a", 1)]
        self.assertEqual(("a", "b"), coll.pluck(coll.sorted_by(items, "name"), "name"))

    def test_sorted_by_two_keys(self):
        items = [Item("b", 1), Item("a", 2), Item("c", 1)]
        ordered = coll.sorted_by(items, "size", "name")
        self.assertEqual(("b", "c", "a"), coll.pluck(ordered, "name"))
