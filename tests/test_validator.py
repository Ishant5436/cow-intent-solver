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


def test_validator_rejects_token_conservation_deficit():
    """Verify validator flags any settlement where token outflow exceeds inflow."""
    auction = AuctionInstance(
        id="deficit_batch",
        tokens={WETH: TokenMetadata(decimals=18), USDC: TokenMetadata(decimals=6)},
        orders=[
            Order(
                uid="order_alice",
                sell_token=WETH,
                buy_token=USDC,
                sell_amount=1_000_000_000_000_000_000,
                buy_amount=3_100_000_000,
            ),
            Order(
                uid="order_bob",
                sell_token=USDC,
                buy_token=WETH,
                sell_amount=3_150_000_000,
                buy_amount=990_000_000_000_000_000,
            ),
        ],
    )

    # Imbalance: Alice trades 1 WETH at clearing price, Bob trades only 2000 USDC -> USDC deficit
    solution = Solution(
        prices={WETH: 3_150_000_000, USDC: 1_000_000_000_000_000_000},
        trades=[
            TradeExecution(order_uid="order_alice", executed_amount=1_000_000_000_000_000_000),
            TradeExecution(order_uid="order_bob", executed_amount=2_000_000_000),
        ],
    )

    validator = SettlementValidator()
    result = validator.validate(auction, solution)
    assert not result.is_valid
    assert any("Token conservation deficit" in err for err in result.errors)


def test_validator_rejects_cumulative_over_execution():
    """Verify validator flags order whose cumulative execution exceeds sell_amount."""
    auction = AuctionInstance(
        id="over_exec_batch",
        tokens={WETH: TokenMetadata(decimals=18), USDC: TokenMetadata(decimals=6)},
        orders=[
            Order(
                uid="order_bob",
                sell_token=USDC,
                buy_token=WETH,
                sell_amount=100,
                buy_amount=100,
            ),
        ],
    )

    # Bob authorized 100, but solution includes two trades of 60 each (total 120)
    solution = Solution(
        prices={WETH: 1_000_000_000_000_000_000, USDC: 1_000_000_000_000_000_000},
        trades=[
            TradeExecution(order_uid="order_bob", executed_amount=60),
            TradeExecution(order_uid="order_bob", executed_amount=60),
        ],
    )

    validator = SettlementValidator()
    result = validator.validate(auction, solution)
    assert not result.is_valid
    expected_err = "Order order_bob over-executed: total executed 120 > authorized sell amount 100"
    assert any(expected_err in err for err in result.errors)


def test_validator_rejects_double_fill_conservation_deficit():
    """Verify validator independent conservation check catches double-fill deficits."""
    TOKEN_A = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    TOKEN_B = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

    auction = AuctionInstance(
        id="double_fill_deficit_test",
        tokens={},
        orders=[
            Order(uid="a1", sell_token=TOKEN_A, buy_token=TOKEN_B, sell_amount=100, buy_amount=100),
            Order(uid="a2", sell_token=TOKEN_A, buy_token=TOKEN_B, sell_amount=100, buy_amount=100),
            Order(uid="b1", sell_token=TOKEN_B, buy_token=TOKEN_A, sell_amount=100, buy_amount=100),
        ],
    )

    # Rogue solution executing b1 twice to satisfy both a1 and a2
    solution = Solution(
        prices={TOKEN_A: 1_000_000_000_000_000_000, TOKEN_B: 1_000_000_000_000_000_000},
        trades=[
            TradeExecution(order_uid="a1", executed_amount=100),
            TradeExecution(order_uid="b1", executed_amount=100),
            TradeExecution(order_uid="a2", executed_amount=100),
            TradeExecution(order_uid="b1", executed_amount=100),
        ],
    )

    validator = SettlementValidator()
    result = validator.validate(auction, solution)
    assert not result.is_valid
    # Must flag both over-execution AND token conservation deficit
    assert any("Order b1 over-executed" in err for err in result.errors)
    assert any(f"Token conservation deficit for {TOKEN_B}" in err for err in result.errors)


