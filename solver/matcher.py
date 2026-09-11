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
        # Group orders by directed token pair: (sell_token, buy_token)
        order_book: dict[tuple[str, str], list[Order]] = defaultdict(list)
        for order in auction.orders:
            order_book[(order.sell_token, order.buy_token)].append(order)

        prices: dict[str, int] = {}
        trades: list[TradeExecution] = []
        total_surplus: int = 0

        # Set default reference prices from tokens metadata if available
        for token_addr, meta in auction.tokens.items():
            if meta.reference_price:
                prices[token_addr] = meta.reference_price

        # Search for bilateral pairs: (A -> B) and (B -> A)
        seen_pairs: set[frozenset[str]] = set()

        for (token_a, token_b), orders_a_to_b in list(order_book.items()):
            pair_key = frozenset([token_a, token_b])
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            orders_b_to_a = order_book.get((token_b, token_a), [])
            if not orders_b_to_a:
                continue

            # Attempt to match bilateral orders
            pair_trades, pair_prices, pair_surplus = self._match_bilateral_pair(
                token_a, token_b, orders_a_to_b, orders_b_to_a
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
    ) -> tuple[list[TradeExecution], dict[str, int], int]:
        """Match two sets of counter-directional orders."""
        matched_trades: list[TradeExecution] = []
        prices: dict[str, int] = {}
        total_surplus: int = 0

        for order_a in orders_a:
            # Order A: Sell A for B
            # Minimum B per atom of A = buy_amount / sell_amount
            min_r_a = Decimal(order_a.buy_amount) / Decimal(order_a.sell_amount)

            for order_b in orders_b:
                # Order B: Sell B for A
                # Maximum B willing to give per atom of A = sell_amount / buy_amount
                max_r_b = Decimal(order_b.sell_amount) / Decimal(order_b.buy_amount)

                # Check if prices cross (spread is non-negative)
                if min_r_a <= max_r_b:
                    # Valid clearing exchange rate R = Price(A) / Price(B)
                    clearing_r = (min_r_a + max_r_b) / Decimal(2)

                    # Establish uniform prices with dynamic 10**18 scale to prevent truncation
                    scale = Decimal(10**18)
                    if clearing_r <= 1:
                        price_b = int(scale)
                        price_a = max(1, int(scale * clearing_r))
                    else:
                        price_a = int(scale)
                        price_b = max(1, int(scale / clearing_r))

                    prices[token_a] = price_a
                    prices[token_b] = price_b

                    # Execute full amounts if volume aligns
                    matched_trades.append(
                        TradeExecution(
                            order_uid=order_a.uid,
                            executed_amount=order_a.sell_amount,
                        )
                    )
                    matched_trades.append(
                        TradeExecution(
                            order_uid=order_b.uid,
                            executed_amount=order_b.sell_amount,
                        )
                    )

                    # Calculate surplus for score
                    surplus_a = int(
                        Decimal(order_a.sell_amount) * clearing_r - Decimal(order_a.buy_amount)
                    )
                    surplus_b = int(
                        Decimal(order_b.sell_amount) - Decimal(order_b.buy_amount) * clearing_r
                    )
                    total_surplus += max(0, surplus_a) + max(0, surplus_b)
                    break

        return matched_trades, prices, total_surplus
