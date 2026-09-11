"""Unit tests for Coincidence-of-Wants (CoW) graph matching engine."""

from solver.matcher import CoWMatcher
from solver.models import AuctionInstance, Order, TokenMetadata

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def test_bilateral_cow_match_exact_crossing():
    """Verify matcher crosses counter-directional orders with price overlap."""
    auction = AuctionInstance(
        id="test_batch_1",
        tokens={
            WETH: TokenMetadata(decimals=18, reference_price=3150000000),
            USDC: TokenMetadata(decimals=6, reference_price=1000000),
        },
        orders=[
            # Alice: Sell 1 WETH for >= 3100 USDC
            Order(
                uid="order_alice",
                sell_token=WETH,
                buy_token=USDC,
                sell_amount=1_000_000_000_000_000_000,
                buy_amount=3_100_000_000,
            ),
            # Bob: Sell 3200 USDC for >= 1 WETH
            Order(
                uid="order_bob",
                sell_token=USDC,
                buy_token=WETH,
                sell_amount=3_200_000_000,
                buy_amount=1_000_000_000_000_000_000,
            ),
        ],
    )

    matcher = CoWMatcher()
    solution = matcher.match_auction(auction)

    assert solution is not None
    assert len(solution.trades) == 2
    executed_uids = {t.order_uid for t in solution.trades}
    assert "order_alice" in executed_uids
    assert "order_bob" in executed_uids

    # Verify uniform prices exist
    assert WETH in solution.prices
    assert USDC in solution.prices
    assert solution.prices[WETH] > 0
    assert solution.prices[USDC] > 0
    assert solution.score > 0


def test_no_cow_match_when_spread_is_disjoint():
    """Verify matcher does not execute trades when limit prices cannot cross."""
    auction = AuctionInstance(
        id="test_batch_no_cross",
        tokens={
            WETH: TokenMetadata(decimals=18, reference_price=3000000000),
            USDC: TokenMetadata(decimals=6, reference_price=1000000),
        },
        orders=[
            # Alice wants 4,000 USDC for 1 WETH
            Order(
                uid="order_alice",
                sell_token=WETH,
                buy_token=USDC,
                sell_amount=1_000_000_000_000_000_000,
                buy_amount=4_000_000_000,
            ),
            # Bob only offers 3,000 USDC for 1 WETH
            Order(
                uid="order_bob",
                sell_token=USDC,
                buy_token=WETH,
                sell_amount=3_000_000_000,
                buy_amount=1_000_000_000_000_000_000,
            ),
        ],
    )

    matcher = CoWMatcher()
    solution = matcher.match_auction(auction)

    assert solution is not None
    assert len(solution.trades) == 0
    assert solution.score == 0


def test_matched_uids_not_reused():
    """Verify that an order matched in one pair is not executed again in another pair."""
    DAI = "0x6b175474e89094c44da98b954eedeac495271d0f"
    auction = AuctionInstance(
        id="test_batch_dedup",
        tokens={
            WETH: TokenMetadata(decimals=18, reference_price=3150000000),
            USDC: TokenMetadata(decimals=6, reference_price=1000000),
            DAI: TokenMetadata(decimals=18, reference_price=1000000),
        },
        orders=[
            # Alice: Sell 1 WETH for USDC
            Order(
                uid="order_alice",
                sell_token=WETH,
                buy_token=USDC,
                sell_amount=1_000_000_000_000_000_000,
                buy_amount=3_100_000_000,
            ),
            # Bob: Sell USDC for WETH
            Order(
                uid="order_bob",
                sell_token=USDC,
                buy_token=WETH,
                sell_amount=3_200_000_000,
                buy_amount=1_000_000_000_000_000_000,
            ),
            # Charlie: Also tries to match with Alice's WETH by selling USDC
            Order(
                uid="order_charlie",
                sell_token=USDC,
                buy_token=WETH,
                sell_amount=3_300_000_000,
                buy_amount=1_000_000_000_000_000_000,
            ),
        ],
    )

    matcher = CoWMatcher()
    solution = matcher.match_auction(auction)

    # Alice should be matched at most once
    alice_matches = [t for t in solution.trades if t.order_uid == "order_alice"]
    assert len(alice_matches) == 1

