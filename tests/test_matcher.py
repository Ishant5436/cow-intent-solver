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


def test_double_fill_prevention_competing_orders():
    """Verify that multiple orders on side A cannot double-fill a single counter-order on side B."""
    auction = AuctionInstance(
        id="test_competing_orders",
        tokens={},
        orders=[
            Order(uid="a1", sell_token=WETH, buy_token=USDC, sell_amount=100, buy_amount=100),
            Order(uid="a2", sell_token=WETH, buy_token=USDC, sell_amount=100, buy_amount=100),
            Order(uid="b1", sell_token=USDC, buy_token=WETH, sell_amount=100, buy_amount=100),
        ],
    )

    matcher = CoWMatcher()
    solution = matcher.match_auction(auction)

    b1_trades = [t for t in solution.trades if t.order_uid == "b1"]
    total_b1_executed = sum(t.executed_amount for t in b1_trades)

    # b1 must be executed at most once, and total executed must not exceed authorized 100
    assert len(b1_trades) == 1
    assert total_b1_executed == 100


def test_stale_transitive_price_rejected_when_limits_violated():
    """Verify matcher does not execute trades when transitively implied prices violate limits."""
    TOKEN_A = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    TOKEN_B = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    TOKEN_C = "0xcccccccccccccccccccccccccccccccccccccccc"

    # Pair A/B clears at 1:1, setting P_A = P_B
    # Pair B/C clears at ~2.1:1, setting P_C = P_B / 2.1
    # Transitively, P_A / P_C ≈ 2.1
    # Orders A2/C2 signed limits around 1:1 (buy_amount 90 for sell_amount 100)
    auction = AuctionInstance(
        id="stale_price_test",
        tokens={},
        orders=[
            Order(uid="a1", sell_token=TOKEN_A, buy_token=TOKEN_B, sell_amount=100, buy_amount=100),
            Order(uid="b1", sell_token=TOKEN_B, buy_token=TOKEN_A, sell_amount=100, buy_amount=100),
            Order(uid="b2", sell_token=TOKEN_B, buy_token=TOKEN_C, sell_amount=100, buy_amount=200),
            Order(uid="c1", sell_token=TOKEN_C, buy_token=TOKEN_B, sell_amount=220, buy_amount=100),
            Order(uid="a2", sell_token=TOKEN_A, buy_token=TOKEN_C, sell_amount=100, buy_amount=90),
            Order(uid="c2", sell_token=TOKEN_C, buy_token=TOKEN_A, sell_amount=100, buy_amount=90),
        ],
    )

    matcher = CoWMatcher()
    solution = matcher.match_auction(auction)

    # A2 and C2 must not be matched because the transitively fixed prices violate limits
    ac_trades = [t for t in solution.trades if t.order_uid in ("a2", "c2")]
    assert len(ac_trades) == 0


