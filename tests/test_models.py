"""Unit tests for CoW Protocol data models and JSON serialization."""

from solver.models import (
    AuctionInstance,
    Order,
    OrderKind,
    Solution,
    TradeExecution,
)


def test_order_deserialization():
    """Verify Order correctly validates and parses JSON order data."""
    data = {
        "uid": "0x111111111111111111111111111111111111111111111111",
        "sell_token": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "buy_token": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "sell_amount": 1000000000000000000,
        "buy_amount": 3150000000,
        "kind": "sell",
        "partially_fillable": False,
    }
    order = Order.model_validate(data)
    assert order.uid == data["uid"]
    assert order.sell_token == data["sell_token"].lower()
    assert order.buy_token == data["buy_token"].lower()
    assert order.sell_amount == 1000000000000000000
    assert order.buy_amount == 3150000000
    assert order.kind == OrderKind.SELL
    assert not order.partially_fillable


def test_auction_instance_parsing():
    """Verify AuctionInstance parses tokens map and order list."""
    data = {
        "id": "1049281",
        "tokens": {
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": {
                "decimals": 18,
                "reference_price": 3200000000,
            },
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": {
                "decimals": 6,
                "reference_price": 1000000,
            },
        },
        "orders": [
            {
                "uid": "0xorder1",
                "sell_token": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "buy_token": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                "sell_amount": 1000000000000000000,
                "buy_amount": 3150000000,
                "kind": "sell",
            }
        ],
    }
    auction = AuctionInstance.model_validate(data)
    assert auction.id == "1049281"
    assert len(auction.tokens) == 2
    assert len(auction.orders) == 1
    assert auction.tokens["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"].decimals == 18


def test_solution_serialization():
    """Verify Solution serializes correctly for driver submission."""
    solution = Solution(
        prices={
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": 3200000000,
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": 1000000,
        },
        trades=[TradeExecution(order_uid="0xorder1", executed_amount=1000000000000000000)],
        score=50000000,
    )
    dumped = solution.model_dump()
    assert dumped["score"] == 50000000
    assert len(dumped["trades"]) == 1
    assert "prices" in dumped
