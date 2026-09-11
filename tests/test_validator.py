"""Unit tests for CoW Protocol Settlement Invariant Validator."""

from solver.models import AuctionInstance, Order, Solution, TokenMetadata, TradeExecution
from solver.validator import SettlementValidator

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def test_validator_passes_valid_settlement():
    """Verify validator accepts a settlement satisfying all invariants."""
    auction = AuctionInstance(
        id="valid_batch_1",
        tokens={
            WETH: TokenMetadata(decimals=18, reference_price=3150000000),
            USDC: TokenMetadata(decimals=6, reference_price=1000000),
        },
        orders=[
            # Alice: 1 WETH -> >= 3100 USDC
            Order(
                uid="order_alice",
                sell_token=WETH,
                buy_token=USDC,
                sell_amount=1_000_000_000_000_000_000,
                buy_amount=3_100_000_000,
            ),
            # Bob: 3150 USDC -> >= 0.99 WETH
            Order(
                uid="order_bob",
                sell_token=USDC,
                buy_token=WETH,
                sell_amount=3_150_000_000,
                buy_amount=990_000_000_000_000_000,
            ),
        ],
    )

    # 10**18 WETH <-> 3.15e9 USDC
    solution = Solution(
        prices={WETH: 3_150_000_000, USDC: 1_000_000_000_000_000_000},
        trades=[
            TradeExecution(order_uid="order_alice", executed_amount=1_000_000_000_000_000_000),
            TradeExecution(order_uid="order_bob", executed_amount=3_150_000_000),
        ],
        score=50000,
    )

    validator = SettlementValidator()
    result = validator.validate(auction, solution)
    assert result.is_valid
    assert len(result.errors) == 0


def test_validator_rejects_limit_price_violation():
    """Verify validator rejects a solution where user receives less than limit."""
    auction = AuctionInstance(
        id="invalid_limit_batch",
        tokens={
            WETH: TokenMetadata(decimals=18),
            USDC: TokenMetadata(decimals=6),
        },
        orders=[
            # Alice wants 3200 USDC
            Order(
                uid="order_alice",
                sell_token=WETH,
                buy_token=USDC,
                sell_amount=1_000_000_000_000_000_000,
                buy_amount=3_200_000_000,
            )
        ],
    )

    # Solution only clears at 3100 USDC (P_WETH = 3.10e9)
    solution = Solution(
        prices={WETH: 3_100_000_000, USDC: 1_000_000_000_000_000_000},
        trades=[TradeExecution(order_uid="order_alice", executed_amount=1_000_000_000_000_000_000)],
    )

    validator = SettlementValidator()
    result = validator.validate(auction, solution)
    assert not result.is_valid
    assert any("Limit price violated" in err for err in result.errors)


def test_validator_rejects_missing_price():
    """Verify validator rejects a solution missing clearing price for traded token."""
    auction = AuctionInstance(
        id="missing_price_batch",
        tokens={WETH: TokenMetadata(decimals=18), USDC: TokenMetadata(decimals=6)},
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

    # Missing USDC price
    solution = Solution(
        prices={WETH: 3_150_000_000},
        trades=[TradeExecution(order_uid="order_alice", executed_amount=1_000_000_000_000_000_000)],
    )

    validator = SettlementValidator()
    result = validator.validate(auction, solution)
    assert not result.is_valid
    assert any("Missing clearing price" in err for err in result.errors)
