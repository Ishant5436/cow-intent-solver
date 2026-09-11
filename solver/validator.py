"""Settlement Invariant and Constraint Validator.

Verifies that proposed batch auction settlement solutions strictly satisfy:
1. Limit price invariant (no trader receives less than signed minimum).
2. Non-zero uniform clearing prices for all traded assets.
3. Valid execution bounds (executed <= order sell amount).
"""

from decimal import Decimal
from typing import NamedTuple

from solver.models import AuctionInstance, Order, Solution


class ValidationResult(NamedTuple):
    is_valid: bool
    errors: list[str]


class SettlementValidator:
    """Deterministic validator for CoW Protocol settlement invariants."""

    def validate(self, auction: AuctionInstance, solution: Solution) -> ValidationResult:
        """Validate all safety and protocol invariants for the candidate solution."""
        errors: list[str] = []
        order_map: dict[str, Order] = {o.uid: o for o in auction.orders}

        for trade in solution.trades:
            order = order_map.get(trade.order_uid)
            if not order:
                errors.append(f"Trade references unknown order UID: {trade.order_uid}")
                continue

            if trade.executed_amount <= 0:
                errors.append(f"Invalid non-positive executed amount: {trade.executed_amount}")
                continue

            if trade.executed_amount > order.sell_amount:
                errors.append(
                    f"Execution exceeds order sell amount: "
                    f"{trade.executed_amount} > {order.sell_amount}"
                )

            # Check prices
            sell_price = solution.prices.get(order.sell_token)
            buy_price = solution.prices.get(order.buy_token)

            if not sell_price or sell_price <= 0:
                errors.append(f"Missing clearing price for sell token: {order.sell_token}")
                continue

            if not buy_price or buy_price <= 0:
                errors.append(f"Missing clearing price for buy token: {order.buy_token}")
                continue

            # Check limit price
            executed_buy_amount = int(
                Decimal(trade.executed_amount) * Decimal(sell_price) / Decimal(buy_price)
            )

            # Pro-rate limit buy amount for partial fills if applicable
            buy_amt = Decimal(order.buy_amount)
            sell_amt = Decimal(order.sell_amount)
            exec_amt = Decimal(trade.executed_amount)
            required_buy_amount = int(buy_amt * exec_amt / sell_amt)

            if executed_buy_amount < required_buy_amount:
                errors.append(
                    f"Limit price violated for order {order.uid}: "
                    f"received {executed_buy_amount} < minimum {required_buy_amount}"
                )

        return ValidationResult(is_valid=(len(errors) == 0), errors=errors)
