from src.domain.money import allocation as mod
from src.domain.money.amount import Money
from tests.support import DomainTestCase


def _sum(shares):
    running = Money(0, shares[0].currency)
    for share in shares:
        running = running.plus(share)
    return running


class SplitEvenlyTests(DomainTestCase):
    def test_exact_split(self):
        shares = mod.split_evenly(Money(9900), 3)
        self.assertEqual((Money(3300),) * 3, shares)

    def test_remainder_goes_to_the_front(self):
        shares = mod.split_evenly(Money(1000), 3)
        self.assertEqual((Money(334), Money(333), Money(333)), shares)

    def test_shares_add_back_up(self):
        shares = mod.split_evenly(Money(1000), 7)
        self.assertEqual(Money(1000), _sum(shares))

    def test_single_part(self):
        self.assertEqual((Money(1000),), mod.split_evenly(Money(1000), 1))

    def test_negative_amount(self):
        shares = mod.split_evenly(Money(-1000), 3)
        self.assertEqual((Money(-334), Money(-333), Money(-333)), shares)

    def test_currency_is_kept(self):
        self.assertEqual("EUR", mod.split_evenly(Money(10, "EUR"), 2)[0].currency)

    def test_zero_parts_rejected(self):
        self.assertField("parts", mod.split_evenly, Money(1), 0)

    def test_non_money_rejected(self):
        self.assertField("amount", mod.split_evenly, 100, 2)


class AllocateByWeightsTests(DomainTestCase):
    def test_proportional(self):
        shares = mod.allocate_by_weights(Money(1000), [1, 1, 2])
        self.assertEqual((Money(250), Money(250), Money(500)), shares)

    def test_largest_remainder(self):
        shares = mod.allocate_by_weights(Money(100), [1, 1, 1])
        self.assertEqual((Money(34), Money(33), Money(33)), shares)

    def test_earlier_entries_win_ties(self):
        shares = mod.allocate_by_weights(Money(10), [1, 1, 1])
        self.assertEqual(Money(4), shares[0])

    def test_zero_weight_gets_nothing(self):
        shares = mod.allocate_by_weights(Money(100), [1, 0])
        self.assertEqual((Money(100), Money(0)), shares)

    def test_shares_add_back_up(self):
        shares = mod.allocate_by_weights(Money(9999), [3, 5, 7, 11])
        self.assertEqual(Money(9999), _sum(shares))

    def test_negative_amount(self):
        shares = mod.allocate_by_weights(Money(-100), [1, 1, 1])
        self.assertEqual(Money(-100), _sum(shares))

    def test_all_zero_weights_rejected(self):
        self.assertField("weights", mod.allocate_by_weights, Money(1), [0, 0])

    def test_negative_weight_rejected(self):
        self.assertField("weights", mod.allocate_by_weights, Money(1), [-1, 2])

    def test_empty_weights_rejected(self):
        self.assertField("weights", mod.allocate_by_weights, Money(1), [])

    def test_non_money_rejected(self):
        self.assertField("amount", mod.allocate_by_weights, 1, [1])


class AllocateByRatiosTests(DomainTestCase):
    def test_halves(self):
        shares = mod.allocate_by_ratios(Money(1000), [0.5, 0.5])
        self.assertEqual((Money(500), Money(500)), shares)

    def test_uneven_ratios(self):
        shares = mod.allocate_by_ratios(Money(1000), [0.3, 0.7])
        self.assertEqual((Money(300), Money(700)), shares)

    def test_ratios_need_not_sum_to_one(self):
        shares = mod.allocate_by_ratios(Money(900), [1, 2])
        self.assertEqual((Money(300), Money(600)), shares)

    def test_negative_ratio_rejected(self):
        self.assertField("ratios", mod.allocate_by_ratios, Money(1), [-0.5, 1])


class ProrateTests(DomainTestCase):
    def test_half_way(self):
        self.assertEqual(Money(500), mod.prorate(Money(1000), 15, 30))

    def test_nothing_elapsed(self):
        self.assertEqual(Money(0), mod.prorate(Money(1000), 0, 30))

    def test_fully_elapsed(self):
        self.assertEqual(Money(1000), mod.prorate(Money(1000), 30, 30))

    def test_leftover_unit_follows_the_larger_remainder(self):
        self.assertEqual(Money(33), mod.prorate(Money(100), 1, 3))
        self.assertEqual(Money(67), mod.remaining_credit(Money(100), 1, 3))

    def test_credit_is_the_complement(self):
        earned = mod.prorate(Money(1000), 7, 30)
        credit = mod.remaining_credit(Money(1000), 7, 30)
        self.assertEqual(Money(1000), earned.plus(credit))

    def test_elapsed_beyond_total_rejected(self):
        self.assertField("elapsed_days", mod.prorate, Money(1), 31, 30)

    def test_zero_total_rejected(self):
        self.assertField("total_days", mod.prorate, Money(1), 0, 0)

    def test_negative_elapsed_rejected(self):
        self.assertField("elapsed_days", mod.prorate, Money(1), -1, 30)

    def test_non_money_rejected(self):
        self.assertField("amount", mod.prorate, 1, 1, 30)


class ReconcileTests(DomainTestCase):
    def test_balanced(self):
        shares = mod.split_evenly(Money(1000), 3)
        self.assertTrue(mod.reconcile(shares, Money(1000)).is_zero())

    def test_short(self):
        self.assertEqual(Money(-1), mod.reconcile([Money(999)], Money(1000)))

    def test_over(self):
        self.assertEqual(Money(1), mod.reconcile([Money(1001)], Money(1000)))
