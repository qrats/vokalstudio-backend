"""Plan changes in the middle of a period.

An upgrade is charged immediately for the unused part of the period; a
downgrade is credited and takes effect at the next renewal.  Both answers come
out of the same three numbers, so they are computed together.
"""

from src.domain.core.errors import ValidationError
from src.domain.money.allocation import remaining_credit
from src.domain.money.amount import Money
from src.domain.timeline.calendar import days_between, parse_date

UPGRADE = "upgrade"
DOWNGRADE = "downgrade"
LATERAL = "lateral"


def classify(current_plan, target_plan):
    """Whether moving between two plans is an upgrade, downgrade or neither."""
    current = current_plan.monthly_equivalent()
    target = target_plan.monthly_equivalent()
    if target.currency != current.currency:
        raise ValidationError("plans must share a currency", field="target_plan")
    if target > current:
        return UPGRADE
    if target < current:
        return DOWNGRADE
    return LATERAL


def unused_credit(plan, period_start, period_end, changed_on):
    """The part of the current period the customer has not consumed."""
    start = parse_date(period_start, "period_start")
    end = parse_date(period_end, "period_end")
    moment = parse_date(changed_on, "changed_on")
    if end <= start:
        raise ValidationError("period_end must follow period_start", field="period_end")
    if moment < start or moment > end:
        raise ValidationError("changed_on is outside the period", field="changed_on")
    span = days_between(start, end)
    used = days_between(start, moment)
    return remaining_credit(plan.price, used, span)


def change_quote(current_plan, target_plan, period_start, period_end, changed_on):
    """What a plan change costs today and what it changes going forward."""
    kind = classify(current_plan, target_plan)
    credit = unused_credit(current_plan, period_start, period_end, changed_on)
    if kind == DOWNGRADE:
        return {
            "kind": kind,
            "credit": credit,
            "charge_now": Money.zero(credit.currency),
            "effective_on": parse_date(period_end, "period_end"),
        }
    start = parse_date(period_start, "period_start")
    end = parse_date(period_end, "period_end")
    moment = parse_date(changed_on, "changed_on")
    span = days_between(start, end)
    remaining = days_between(moment, end)
    target_share = remaining_credit(target_plan.price, span - remaining, span)
    due = target_share.minus(credit)
    if due.is_negative():
        due = Money.zero(due.currency)
    return {
        "kind": kind,
        "credit": credit,
        "charge_now": due,
        "effective_on": moment,
    }


def refund_on_cancellation(plan, period_start, period_end, cancelled_on, policy="none"):
    """How much of the current period is handed back when a plan is cancelled."""
    if policy not in ("none", "prorated", "full"):
        raise ValidationError(
            "policy must be none, prorated or full", field="policy"
        )
    if policy == "none":
        return Money.zero(plan.currency)
    if policy == "full":
        return Money(plan.price.units, plan.currency)
    return unused_credit(plan, period_start, period_end, cancelled_on)
