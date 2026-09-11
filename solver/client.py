"""CoW Protocol Driver HTTP Client and Batch Auction Poller.

Communicates with CoW Protocol public auction endpoints and driver settlement APIs.
"""

from typing import Any

import httpx

from solver.models import AuctionInstance, Solution


class CoWDriverClient:
    """Async client for fetching auction instances and submitting settlement solutions."""

    def __init__(self, base_url: str = "https://barn.api.cow.fi", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=timeout)

    async def fetch_current_auction(self, network: str = "mainnet") -> AuctionInstance | None:
        """Fetch the currently open batch auction instance from CoW Protocol."""
        url = f"{self.base_url}/{network}/api/v1/auction"
        try:
            resp = await self.client.get(url)
            if resp.status_code in (404, 204):
                return None
            if resp.status_code != 200:
                raise RuntimeError(f"Auction fetch failed with status {resp.status_code}")

            data = resp.json()
            if "tokens" not in data and "prices" in data:
                data["tokens"] = data["prices"]
            return AuctionInstance.model_validate(data)
        except httpx.HTTPError as err:
            raise RuntimeError(f"HTTP error connecting to CoW auction API: {err}") from err

    async def submit_solution(
        self,
        auction_id: str,
        solution: Solution,
        driver_url: str | None = None,
    ) -> dict[str, Any]:
        """Submit settlement solution to the CoW Protocol driver."""
        url = driver_url or f"{self.base_url}/mainnet/api/v1/solver/{auction_id}/solution"
        payload = solution.model_dump()
        resp = await self.client.post(url, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Solution submission failed ({resp.status_code}): {resp.text}")
        return resp.json()

    async def close(self) -> None:
        """Close HTTP client connection pool."""
        await self.client.aclose()
