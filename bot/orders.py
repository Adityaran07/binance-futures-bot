"""
Order placement logic — sits between the CLI and the raw BinanceClient.

Responsibilities:
- Validate all inputs via validators.py
- Build the correct parameter dict per order type
- Delegate to BinanceClient.place_order()
- Return a clean OrderResult dataclass
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .client import BinanceClient
from .logging_config import get_logger
from .validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

logger = get_logger(__name__)


@dataclass
class OrderResult:
    """Structured representation of a placed order response."""

    order_id: int
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    status: str
    time_in_force: str
    price: str
    raw: Dict[str, Any] = field(repr=False)

    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> "OrderResult":
        return cls(
            order_id=data.get("orderId", 0),
            client_order_id=data.get("clientOrderId", ""),
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type=data.get("type", ""),
            orig_qty=data.get("origQty", "0"),
            executed_qty=data.get("executedQty", "0"),
            avg_price=data.get("avgPrice", "0"),
            status=data.get("status", ""),
            time_in_force=data.get("timeInForce", ""),
            price=data.get("price", "0"),
            raw=data,
        )

    def summary(self) -> str:
        lines = [
            "┌─────────────────────────────────────────┐",
            "│           ORDER CONFIRMATION            │",
            "├─────────────────────────────────────────┤",
            f"│  Order ID      : {self.order_id:<23} │",
            f"│  Symbol        : {self.symbol:<23} │",
            f"│  Side          : {self.side:<23} │",
            f"│  Type          : {self.order_type:<23} │",
            f"│  Quantity      : {self.orig_qty:<23} │",
            f"│  Price         : {self.price:<23} │",
            f"│  Executed Qty  : {self.executed_qty:<23} │",
            f"│  Avg Price     : {self.avg_price:<23} │",
            f"│  Status        : {self.status:<23} │",
            f"│  Time-in-Force : {self.time_in_force:<23} │",
            "└─────────────────────────────────────────┘",
        ]
        return "\n".join(lines)


class OrderManager:
    """High-level order placement interface."""

    def __init__(self, client: BinanceClient) -> None:
        self._client = client

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
    ) -> OrderResult:
        """Place a MARKET order."""
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        quantity = validate_quantity(quantity)
        validate_price(None, "MARKET")

        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
        }
        logger.debug("Market order params: %s", params)
        response = self._client.place_order(**params)
        return OrderResult.from_response(response)

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        price: str,
        time_in_force: str = "GTC",
    ) -> OrderResult:
        """Place a LIMIT order (Good-Till-Cancelled by default)."""
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        quantity = validate_quantity(quantity)
        price_str = validate_price(price, "LIMIT")

        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "quantity": quantity,
            "price": price_str,
            "timeInForce": time_in_force,
        }
        logger.debug("Limit order params: %s", params)
        response = self._client.place_order(**params)
        return OrderResult.from_response(response)

    def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        stop_price: str,
    ) -> OrderResult:
        """
        Place a STOP_MARKET order (bonus order type).
        Triggers a market order when the stop price is reached.
        """
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        quantity = validate_quantity(quantity)
        stop_price_str = validate_stop_price(stop_price, "STOP_MARKET")

        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "quantity": quantity,
            "stopPrice": stop_price_str,
        }
        logger.debug("Stop-Market order params: %s", params)
        response = self._client.place_order(**params)
        return OrderResult.from_response(response)
