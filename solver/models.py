"""CoW Protocol Data Models and Schemas.

Pydantic v2 schemas representing batch auctions, orders, token metadata,
and solver settlement solutions according to the CoW Protocol specification.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderKind(StrEnum):
    SELL = "sell"
    BUY = "buy"


class TokenMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decimals: int
    reference_price: int | None = None


class Order(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    uid: str
    sell_token: str = Field(..., validation_alias="sellToken", alias="sell_token")
    buy_token: str = Field(..., validation_alias="buyToken", alias="buy_token")
    sell_amount: int = Field(..., validation_alias="sellAmount", alias="sell_amount")
    buy_amount: int = Field(..., validation_alias="buyAmount", alias="buy_amount")
    kind: OrderKind = OrderKind.SELL
    partially_fillable: bool = Field(
        False, validation_alias="partiallyFillable", alias="partially_fillable"
    )
    fee_amount: int = Field(0, validation_alias="feeAmount", alias="fee_amount")

    @field_validator("sell_token", "buy_token", mode="before")
    @classmethod
    def normalize_address(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.lower()
        return str(v).lower()


class AuctionInstance(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    tokens: dict[str, TokenMetadata] = Field(default_factory=dict)
    orders: list[Order] = Field(default_factory=list)

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, v: Any) -> str:
        return str(v)

    @field_validator("tokens", mode="before")
    @classmethod
    def normalize_token_keys(cls, v: Any, info: Any) -> dict[str, Any]:
        if isinstance(v, dict):
            res = {}
            for k, val in v.items():
                if isinstance(val, TokenMetadata):
                    res[k.lower()] = val
                elif isinstance(val, dict):
                    res[k.lower()] = TokenMetadata(**val)
                else:
                    # e.g. reference price string
                    res[k.lower()] = TokenMetadata(decimals=18, reference_price=int(val))
            return res
        return {}


class TradeExecution(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_uid: str
    executed_amount: int


class Solution(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prices: dict[str, int]
    trades: list[TradeExecution]
    score: int = 0

    @field_validator("prices", mode="before")
    @classmethod
    def normalize_price_keys(cls, v: Any) -> dict[str, int]:
        if isinstance(v, dict):
            return {k.lower(): int(val) for k, val in v.items()}
        return v
