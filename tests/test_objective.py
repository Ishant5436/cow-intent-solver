"""Unit tests for CoW Protocol Objective and Surplus Calculator."""

from solver.models import AuctionInstance, Order, Solution, TokenMetadata, TradeExecution
from solver.objective import CoWObjectiveCalculator

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def test_calculate_order_surplus():
    """Verify surplus correctly calculates execution amount above limit amount."""
    calc = CoWObjectiveCalculator()
    # Order: Sell 1 WETH for >= 3100 USDC (3_100_000_000 units)
    order = Order(
        uid="order_alice",
        sell_token=WETH,
        buy_token=USDC,
        sell_amount=1_000_000_000_000_000_000,
        buy_amount=3_100_000_000,
    )
    # Execution: gets 3150 USDC
    executed_buy_amount = 3_150_000_000
    surplus = calc.calculate_order_surplus(order, executed_buy_amount)
    assert surplus == 50_000_000  # 50 USDC surplus


def test_score_solution_evaluates_total_batch_surplus():
    """Verify full batch solution scoring calculates combined surplus across all orders."""
    auction = AuctionInstance(
        id="batch_surplus_1",
        tokens={
            WETH: TokenMetadata(decimals=18, reference_price=3150000000),
            USDC: TokenMetadata(decimals=6, reference_price=1000000),
        },
        orders=[
            Order(
                uid="order_alice",
                sell_token=WETH,
                buy_token=USDC,
                sell_amount=1_000_000_000_000_000_000,
                buy_amount=3_100_000_000,
            )
        ],
    )

    # Solution clearing prices:
    # 1 WETH (10**18 atoms) trades for 3,150 USDC (3,150,000,000 atoms)
    # Conservation of value: 10**18 * P_WETH = 3.15e9 * P_USDC
    # => P_WETH = 3_150_000_000, P_USDC = 1_000_000_000_000_000_000 (10**18)
    solution = Solution(
        prices={WETH: 3_150_000_000, USDC: 1_000_000_000_000_000_000},
        trades=[TradeExecution(order_uid="order_alice", executed_amount=1_000_000_000_000_000_000)],
    )

    calc = CoWObjectiveCalculator()
    score = calc.score_solution(auction, solution)

    # Alice receives 3,150 USDC vs 3,100 limit = 50 USDC surplus
    assert score > 0
    assert score == 50_000_000
