"""Unit tests for CoW Protocol Driver HTTP Client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from solver.client import CoWDriverClient
from solver.models import Solution


@pytest.mark.asyncio
async def test_fetch_current_auction_parses_response():
    """Verify client fetches and parses batch auction from CoW API."""
    mock_payload = {
        "id": "1049281",
        "tokens": {
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": {
                "decimals": 18,
                "reference_price": 3200000000,
            }
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

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        client = CoWDriverClient()
        auction = await client.fetch_current_auction()
        await client.close()

    assert auction is not None
    assert auction.id == "1049281"
    assert len(auction.orders) == 1


@pytest.mark.asyncio
async def test_fetch_current_auction_handles_404_empty_batch():
    """Verify client returns None when no batch is active (HTTP 404 or empty)."""
    mock_resp = AsyncMock()
    mock_resp.status_code = 404

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        client = CoWDriverClient()
        auction = await client.fetch_current_auction()
        await client.close()

    assert auction is None


@pytest.mark.asyncio
async def test_submit_solution_formats_driver_payload():
    """Verify client posts valid JSON solution to CoW driver."""
    solution = Solution(
        prices={"0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": 3200000000},
        trades=[],
        score=1000,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "accepted"}

    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp
    ) as mock_post:
        client = CoWDriverClient()
        res = await client.submit_solution("1049281", solution)
        await client.close()

    assert res == {"status": "accepted"}
    mock_post.assert_called_once()
