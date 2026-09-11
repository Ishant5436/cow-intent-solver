"""Coincidence-of-Wants (CoW) Bipartite Matching Engine.

Identifies counter-directional order pairs (e.g. Token A -> Token B and Token B -> Token A),
determines valid uniform clearing prices within their overlapping limit bounds,
and constructs zero-slippage settlement solutions without requiring external AMM liquidity.
"""

from collections import defaultdict
from decimal import Decimal

from solver.models import AuctionInstance, Order, Solution, TradeExecution


class CoWMatcher:
    """Matches peer-to-peer orders directly within batch auctions."""

    def __init__(self, price_base: int = 1_000_000_000):
        self.price_base = price_base

    def match_auction(self, auction: AuctionInstance) -> Solution:
        """Find Coincidence-of-Wants crossings in the given auction instance."""
        order_book: dict[tuple[str, str], list[Order]] = defaultdict(list)
        for order in auction.orders:
            order_book[(order.sell_token, order.buy_token)].append(order)

        prices: dict[str, int] = {}
        trades: list[TradeExecution] = []
        total_surplus: int = 0
        matched_uids: set[str] = set()
        seen_pairs: set[frozenset[str]] = set()

        for (token_a, token_b), orders_a_to_b in list(order_book.items()):
            pair_key = frozenset([token_a, token_b])
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            orders_b_to_a = order_book.get((token_b, token_a), [])
            if not orders_b_to_a:
                continue

            pair_trades, pair_prices, pair_surplus = self._match_bilateral_pair(
                token_a, token_b, orders_a_to_b, orders_b_to_a, matched_uids, prices
            )
            if pair_trades:
                trades.extend(pair_trades)
                prices.update(pair_prices)
                total_surplus += pair_surplus

        return Solution(prices=prices, trades=trades, score=total_surplus)

    def _match_bilateral_pair(
        self,
        token_a: str,
        token_b: str,
        orders_a: list[Order],
        orders_b: list[Order],
        matched_uids: set[str],
        global_prices: dict[str, int],
    ) -> tuple[list[TradeExecution], dict[str, int], int]:
        """Match two sets of counter-directional orders."""
        matched_trades: list[TradeExecution] = []
        prices: dict[str, int] = {}
        total_surplus: int = 0

        for order_a in orders_a:
            if order_a.uid in matched_uids:
                continue
            min_r_a = Decimal(order_a.buy_amount) / Decimal(order_a.sell_amount)

            for order_b in orders_b:
                if order_b.uid in matched_uids:
                    continue
                max_r_b = Decimal(order_b.sell_amount) / Decimal(order_b.buy_amount)

                # Check if prices cross (spread is non-negative)
                if min_r_a > max_r_b:
                    continue

                clearing_r = (min_r_a + max_r_b) / Decimal(2)
                scale = Decimal(10**18)

                # Maintain consistent global price vector
                if token_a in global_prices and token_b in global_prices:
                    price_a = global_prices[token_a]
                    price_b = global_prices[token_b]
                    existing_r = Decimal(price_a) / Decimal(price_b)
                    # Stale price check: existing ratio MUST fall within [min_r_a, max_r_b]
                    if not (min_r_a <= existing_r <= max_r_b):
                        continue
                elif token_a in global_prices and token_b not in global_prices:
                    price_a = global_prices[token_a]
                    price_b = max(1, int(Decimal(price_a) / clearing_r))
                elif token_b in global_prices and token_a not in global_prices:
                    price_b = global_prices[token_b]
                    price_a = max(1, int(Decimal(price_b) * clearing_r))
                else:
                    if clearing_r <= 1:
                        price_b = int(scale)
                        price_a = max(1, int(scale * clearing_r))
                    else:
                        price_a = int(scale)
                        price_b = max(1, int(scale / clearing_r))

                # Calculate mutually balanced execution amounts ensuring zero deficit
                # Option 1: Bound by Order A volume
                cand_exec_a = order_a.sell_amount
                cand_exec_b = int(
                    Decimal(cand_exec_a) * Decimal(price_a) / Decimal(price_b)
                )

                required_b_for_order_b = int(
                    Decimal(order_b.buy_amount)
                    * Decimal(cand_exec_b)
                    / Decimal(order_b.sell_amount)
                )

                if (
                    cand_exec_b <= order_b.sell_amount
                    and cand_exec_b >= order_a.buy_amount
                    and cand_exec_a >= required_b_for_order_b
                ):
                    exec_a = cand_exec_a
                    exec_b = cand_exec_b
                else:
                    # Option 2: Bound by Order B volume
                    cand_exec_b = order_b.sell_amount
                    cand_exec_a = int(
                        Decimal(cand_exec_b) * Decimal(price_b) / Decimal(price_a)
                    )
                    required_b_for_order_a = int(
                        Decimal(order_a.buy_amount)
                        * Decimal(cand_exec_a)
                        / Decimal(order_a.sell_amount)
                    )

                    if (
                        cand_exec_a <= order_a.sell_amount
                        and cand_exec_a >= order_b.buy_amount
                        and cand_exec_b >= required_b_for_order_a
                    ):
                        exec_a = cand_exec_a
                        exec_b = cand_exec_b
                    else:
                        continue

                # Mark both order UIDs as matched to prevent double fills
                matched_uids.add(order_a.uid)
                matched_uids.add(order_b.uid)

                matched_trades.append(
                    TradeExecution(order_uid=order_a.uid, executed_amount=exec_a)
                )
                matched_trades.append(
                    TradeExecution(order_uid=order_b.uid, executed_amount=exec_b)
                )

                prices[token_a] = price_a
                prices[token_b] = price_b

                # Calculate user surplus in buy units
                surplus_a = exec_b - order_a.buy_amount
                surplus_b = exec_a - order_b.buy_amount
                total_surplus += max(0, surplus_a) + max(0, surplus_b)
                break

        return matched_trades, prices, total_surplus
