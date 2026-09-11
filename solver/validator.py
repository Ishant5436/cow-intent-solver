"""Settlement Invariant and Constraint Validator.

Verifies that proposed batch auction settlement solutions strictly satisfy:
1. Limit price invariant (no trader receives less than signed minimum).
2. Non-zero uniform clearing prices for all traded assets.
3. Valid execution bounds (executed <= order sell amount).
"""

from collections import defaultdict
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

        # Track cumulative executed amount per order across all trades
        executed_per_order: dict[str, int] = defaultdict(int)

        for trade in solution.trades:
            order = order_map.get(trade.order_uid)
            if not order:
                errors.append(f"Trade references unknown order UID: {trade.order_uid}")
                continue

            if trade.executed_amount <= 0:
                errors.append(f"Invalid non-positive executed amount: {trade.executed_amount}")
                continue

            executed_per_order[trade.order_uid] += trade.executed_amount

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

        # 1. Enforce cumulative execution bound per order against authorized sell_amount
        for uid, total_exec in executed_per_order.items():
            order = order_map.get(uid)
            if order and total_exec > order.sell_amount:
                errors.append(
                    f"Order {uid} over-executed: "
                    f"total executed {total_exec} > authorized sell amount {order.sell_amount}"
                )

        # 2. Independent token balance conservation:
        # Contract solvency guarantees that total delivered outflow cannot exceed
        # authorized signed inflow deposited by traders.
        authorized_inflow: dict[str, int] = defaultdict(int)
        token_outflow: dict[str, int] = defaultdict(int)

        for uid, total_exec in executed_per_order.items():
            order = order_map.get(uid)
            if order:
                authorized_inflow[order.sell_token] += min(order.sell_amount, total_exec)

        for trade in solution.trades:
            order = order_map.get(trade.order_uid)
            if not order:
                continue
            s_price = solution.prices.get(order.sell_token)
            b_price = solution.prices.get(order.buy_token)
            if not s_price or not b_price:
                continue

            buy_amt = int(Decimal(trade.executed_amount) * Decimal(s_price) / Decimal(b_price))
            token_outflow[order.buy_token] += buy_amt

        for token in set(authorized_inflow) | set(token_outflow):
            if token_outflow[token] > authorized_inflow[token]:
                errors.append(
                    f"Token conservation deficit for {token}: "
                    f"outflow {token_outflow[token]} > authorized inflow {authorized_inflow[token]}"
                )

        return ValidationResult(is_valid=(len(errors) == 0), errors=errors)

